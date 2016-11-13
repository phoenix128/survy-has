import re
import threading
from threading import Lock

import os
import telegram
import time
import yaml

from telegram.bot import Bot
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler, Filters
from telegram.ext.updater import Updater
from telegram.update import Update

from survy.core.app import App
from survy.core.component import Component
from survy.core.components.cam import CamManager, CamRepo, Cam
from survy.core.intercom import Message, Reply
from survy.core.log import Log


class TelegramManager(Component):
    INTERCOM_MESSAGE_EVENT_CHAT_START = 'telegram-event-chat-start'
    INTERCOM_MESSAGE_EVENT_CHAT_MESSAGE = 'telegram-event-chat-message'

    INTERCOM_MESSAGE_DO_VIDEO_MESSAGE = 'telegram-do-video-message'
    INTERCOM_MESSAGE_DO_PHOTO_MESSAGE = 'telegram-do-photo-message'
    INTERCOM_MESSAGE_DO_DOCUMENT_MESSAGE = 'telegram-do-document-message'

    INTERCOM_MESSAGE_DO_CHAT_MESSAGE = 'telegram-do-chat-message'
    INTERCOM_MESSAGE_DO_SEND_CAM_SNAPSHOT = 'telegram-do-send-cam-snapshot'
    INTERCOM_MESSAGE_DO_SEND_CAM_VIDEO = 'telegram-do-send-cam-video'

    _allowed_users = []
    _token = None
    _current_token = None
    _updater = None
    _bot = None

    _runtime_file_mutex = Lock()

    _chat_ids = {}

    def _get_settings_file(cls):
        return App.get_settings_path() + '/telegram.yml'

    def _get_runtime_file(cls):
        return App.get_settings_path() + '/telegram_runtime.yml'

    def _load_runtime(self):
        self._chat_ids = {}

        runtime_file = self._get_runtime_file()
        try:
            runtime = yaml.load(open(runtime_file, 'r'))
            Log.info("Loading runtime from " + runtime_file)
        except:
            Log.error("Loading runtime failed from " + runtime_file)
            return

        self._chat_ids = runtime['chat_ids']

    def _save_runtime(self):
        runtime_file = self._get_runtime_file()

        runtime = {
            'chat_ids': self._chat_ids
        }

        self._runtime_file_mutex.acquire()
        yaml.dump(runtime, open(runtime_file, 'w'), default_flow_style=False)
        self._runtime_file_mutex.release()

    def _add_chat_id(self, user, chat_id):
        must_save = (user not in self._chat_ids or self._chat_ids[user] != chat_id)
        self._chat_ids[user] = chat_id

        if must_save:
            self._save_runtime()

    def get_variables(self):
        if self.get_bot() is not None:

            return {
                'telegram_bot_name': self.get_bot().username,
                'telegram_bot_first_name': self.get_bot().first_name,
                'telegram_bot_last_name': self.get_bot().last_name,
            }
        else:
            return {}

    def load_settings(self):
        self._allowed_users = []

        settings_file = self._get_settings_file()
        try:
            settings = yaml.load(open(settings_file, 'r'))
            Log.info("Loading settings from " + settings_file)
        except:
            Log.error("Loading settings failed from " + settings_file)
            return

        self._token = settings['token']
        self._allowed_users = settings['users']

    def get_is_allowed_message(self, update: Update):
        """
        Return true if user is allowed to send messages
        :param update:
        :return:
        """
        return update.message.from_user.username in self._allowed_users

    def get_bot(self) -> Bot:
        return self._bot

    def get_chat_id(self, username):
        if username not in self._chat_ids:
            return None

        return self._chat_ids[username]

    def send_message(self, text, recipients=None):
        if recipients is None:
            recipients = self._allowed_users

        for recipient in recipients:
            chat_id = self.get_chat_id(recipient)
            if chat_id is not None:
                self.get_bot().sendMessage(chat_id, text)
            else:
                Log.error('Unknown chat ID for user ' + recipient + ', please send a message to this bot')

    def send_picture(self, file_name, caption=None, recipients=None):
        if file_name is None:
            return

        try:
            if recipients is None:
                recipients = self._allowed_users

            for recipient in recipients:
                chat_id = self.get_chat_id(recipient)
                if chat_id is not None:
                    self.get_bot().sendPhoto(
                        chat_id=chat_id,
                        photo=open(file_name, 'rb'),
                        caption=caption
                    )
                else:
                    Log.error('Unknown chat ID for user ' + recipient + ', please send a message to this bot')
        except telegram.error.BadRequest:
            pass

        except FileNotFoundError:
            Log.error('File ' + file_name + ' not found')

    def send_video(self, file, caption=None, recipients=None):
        if file is None:
            return

        try:
            if recipients is None:
                recipients = self._allowed_users

            for recipient in recipients:
                chat_id = self.get_chat_id(recipient)
                if chat_id is not None:
                    self.get_bot().sendDocument(
                        chat_id=chat_id,
                        document=open(file, 'rb'),
                        filename=os.path.basename(file),
                        caption=caption
                    )
                else:
                    Log.error('Unknown chat ID for user ' + recipient + ', please send a message to this bot')
        except telegram.error.BadRequest:
            pass

        except FileNotFoundError:
            Log.error('File ' + file + ' not found')

    send_document = send_video

    def _on_intercom_message_send_chat(self, message: Message) -> Reply:
        payload = message.message_payload

        recipients = None
        if 'to' in payload:
            recipients = re.split(r'\s*,\s*', payload['to'])

        self.send_message(text=payload['text'], recipients=recipients)
        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _send_cam_snapshot(self, cam: Cam, recipients):
        cam_snapshot = self.send_intercom_message(CamManager.INTERCOM_MESSAGE_DO_SNAPSHOT, {
            'cam': cam
        })

        if cam_snapshot != Reply.INTERCOM_STATUS_SUCCESS:
            return

        caption = CamRepo.get_by_code(cam).name

        reply_payload = cam_snapshot.get_payload()
        for from_component, component_payload in reply_payload.items():
            if component_payload['status'] == Reply.INTERCOM_STATUS_SUCCESS and \
                            from_component == CamManager.get_instance().get_code():

                file_name = component_payload['payload']['filename']

                # Async upload
                threading.Thread(target=self.send_picture, kwargs={
                    'file_name': file_name,
                    'caption': caption,
                    'recipients': recipients,
                }).start()

    def _send_cam_video(self, cam: Cam, recipients, duration):
        res = self.send_intercom_message(CamManager.INTERCOM_MESSAGE_DO_VIDEO_START, {
            'cam': cam
        })

        if res != Reply.INTERCOM_STATUS_SUCCESS:
            return

        time.sleep(duration)

        res = self.send_intercom_message(CamManager.INTERCOM_MESSAGE_DO_VIDEO_STOP, {
            'cam': cam
        })

        if res != Reply.INTERCOM_STATUS_SUCCESS:
            return

        caption = CamRepo.get_by_code(cam).name

        reply_payload = res.get_payload()
        for from_component, component_payload in reply_payload.items():
            if component_payload['status'] == Reply.INTERCOM_STATUS_SUCCESS and \
                            from_component == CamManager.get_instance().get_code():
                file_name = component_payload['payload']['filename']

                # Async upload
                threading.Thread(target=self.send_video, kwargs={
                    'file_name': file_name,
                    'caption': caption,
                    'recipients': recipients,
                }).start()

    def _on_cam_action(self, message: Message) -> Reply:
        payload = message.message_payload

        cams = payload['cam'].split(',')
        for cam in cams:
            recipients = None
            if 'to' in payload:
                recipients = re.split(r'\s*,\s*', payload['to'])

            if message == self.INTERCOM_MESSAGE_DO_SEND_CAM_SNAPSHOT:
                self._send_cam_snapshot(
                    cam=cam,
                    recipients=recipients
                )

            elif message == self.INTERCOM_MESSAGE_DO_SEND_CAM_VIDEO:
                duration = 10
                if 'duration' in message.message_payload:
                    duration = message.message_payload['duration']

                self._send_cam_video(
                    cam=cam,
                    recipients=recipients,
                    duration=duration
                )

        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _on_intercom_message_cam_action(self, message: Message) -> Reply:
        payload = message.message_payload

        cams = payload['cam'].split(',')
        for cam in cams:
            recipients = None
            if 'to' in payload:
                recipients = re.split(r'\s*,\s*', payload['to'])

            # Async images send
            threading.Thread(target=self._on_cam_action, kwargs={
                'cam': cam,
                'recipients': recipients
            }).start()

        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _on_intercom_message_complex_message(self, message: Message) -> Reply:
        payload = message.message_payload

        filename = message.message_payload['filename']
        if not os.path.isfile(filename) or not App.can_access_file(filename):
            return Reply(Reply.INTERCOM_STATUS_NON_BLOCKING_FAILURE)

        caption = os.path.basename()
        if 'caption' in message.message_payload:
            caption = message.message_payload[filename]

        recipients = None
        if 'to' in payload:
            recipients = re.split(r'\s*,\s*', payload['to'])

        if message == self.INTERCOM_MESSAGE_DO_PHOTO_MESSAGE:
            self.send_picture(file_name=filename, caption=caption, recipients=recipients)

        elif message == self.INTERCOM_MESSAGE_DO_VIDEO_MESSAGE:
            self.send_video(file=filename, caption=caption, recipients=recipients)

        elif message == self.INTERCOM_MESSAGE_DO_DOCUMENT_MESSAGE:
            self.send_video(file=filename, caption=caption, recipients=recipients)

        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _on_intercom_message(self, message: Message) -> Reply:
        if message == self.INTERCOM_MESSAGE_DO_CHAT_MESSAGE:
            return self._on_intercom_message_send_chat(message)

        if message in [self.INTERCOM_MESSAGE_DO_SEND_CAM_SNAPSHOT, self.INTERCOM_MESSAGE_DO_SEND_CAM_VIDEO]:
            return self._on_cam_action(message)

        if message in [
            self.INTERCOM_MESSAGE_DO_PHOTO_MESSAGE,
            self.INTERCOM_MESSAGE_DO_VIDEO_MESSAGE,
            self.INTERCOM_MESSAGE_DO_DOCUMENT_MESSAGE
        ]:
            return self._on_intercom_message_complex_message(message)

        return Component._on_intercom_message(self, message)

    def _get_update_info_for_payload(self, update: Update):
        return {
            'from': update.message.from_user.username,
            'from_first_name': update.message.from_user.first_name,
            'from_last_name': update.message.from_user.last_name,
            'text': update.message.text,
        }

    def _on_command_start(self, bot: Bot, update: Update):
        self._add_chat_id(update.message.from_user.username, update.message.chat_id)

        if self.get_is_allowed_message(update):
            self.send_intercom_message(
                self.INTERCOM_MESSAGE_EVENT_CHAT_START,
                self._get_update_info_for_payload(update)
            )

    def _on_message(self, bot: Bot, update: Update):
        self._add_chat_id(update.message.from_user.username, update.message.chat_id)

        if self.get_is_allowed_message(update):
            self.send_intercom_message(
                self.INTERCOM_MESSAGE_EVENT_CHAT_MESSAGE,
                self._get_update_info_for_payload(update)
            )

    def _start_bot(self):
        self._updater = Updater(token=self._token)
        self._bot = self._updater.bot
        self._updater.dispatcher.add_handler(CommandHandler('start', self._on_command_start))
        self._updater.dispatcher.add_handler(MessageHandler([Filters.text], self._on_message))
        self._updater.start_polling()

    def _stop_bot(self):
        if self._updater is not None:
            self._updater.stop()
            del self._updater

    def _reload(self):
        self.load_settings()

        if self._current_token != self._token:
            self._current_token = self._token

            self._stop_bot()
            self._load_runtime()
            self._start_bot()

        return True

    def start(self):
        Component.start(self)
        self.reload()

