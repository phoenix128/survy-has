import importlib
import os
import re
import threading
import collections

import time
from threading import Lock
from time import strftime, localtime

import numpy
import yaml
import cv2

from survy.core.app import App
from survy.core.component import Component
from survy.core.intercom import Message, Reply
from survy.core.log import Log
from survy.core.utils import Utils


class CamManager:
    pass


class Cam:
    CAM_RECONNECT_TIMEOUT = 10

    _stop = False
    _code = None
    _timelapse = None
    name = None
    url = None
    type = None
    params = None
    adapter = None

    cam_is_online = False

    _current_url = None
    _current_type = None

    _frames_history = 0
    _old_frames_collection = None

    _capture = None
    _image = None
    _new_frame = False

    _current_video = None
    _recording_video = False
    _current_video_file_name = None

    _lock = None

    _timelapse_video = None

    def __init__(self, code, name, cam_type, params, timelapse, frames_history=0):
        self._old_frames_collection = collections.deque(maxlen=frames_history)
        self.code = code
        self.name = name
        self.type = cam_type
        self.params = params
        self.timelapse = timelapse
        self.frames_history = frames_history

        self._lock = Lock()

    @property
    def url(self):
        if self.adapter is None:
            return None

        return self.adapter.get_streaming_url()

    @property
    def timelapse(self):
        return int(self._timelapse)

    @timelapse.setter
    def timelapse(self, value):
        self._timelapse = int(value)

    @property
    def frames_history(self):
        return int(self._frames_history)

    @frames_history.setter
    def frames_history(self, value):
        self._frames_history = int(value)

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, value):
        value = re.sub(r'[\W\s]+', '_', value.lower())
        self._code = value

    def get_manager(self) -> CamManager:
        return CamManager.get_instance()

    def get_capture_file(self, template):
        template = Utils.replace_variables_text(template, {
            'code': self.code
        })

        res = self.get_manager().get_capture_path() + '/' + template
        os.makedirs(os.path.dirname(res), 0o750, True)
        return res

    def on_cam_command(self, message: Message) -> Reply:
        if self.adapter is None:
            print("NO adapter")
            return Reply(Reply.INTERCOM_STATUS_NOT_FOUND)

        return self.adapter.on_cam_command(message)

    def snapshot(self):
        """
        Take snapshot from cam
        :return:
        """

        if self.image is None:
            return None

        self._lock.acquire()
        file_name = self.get_capture_file(self.get_manager().get_snapshot_file_template())
        Log.info('Taking snapshot from "' + self.code + '": ' + file_name)

        cv2.imwrite(file_name, self.image)

        self.get_manager().send_intercom_message(CamManager.INTERCOM_MESSAGE_EVENT_SNAPSHOT, {
            'filename': file_name
        })
        self._lock.release()

        return file_name

    def video_start(self):
        """
        Start recording video
        :return:
        """
        if not self._recording_video:
            self._lock.acquire()
            image = self.image

            if image is not None:
                height, width, layers = image.shape

                file_name = self.get_capture_file(self.get_manager().get_video_file_template())
                self._current_video_file_name = file_name
                Log.info('Starting video for "' + self.code + '": ' + file_name)

                fourcc = cv2.VideoWriter_fourcc(*self.get_manager().get_video_fourcc())
                fps = self._capture.get(cv2.CAP_PROP_FPS)
                self._current_video = cv2.VideoWriter(file_name, fourcc, fps, (width, height))

                for old_img in self._old_frames_collection:
                    self._current_video.write(old_img)

                self._recording_video = True

                self.get_manager().send_intercom_message(CamManager.INTERCOM_MESSAGE_EVENT_VIDEO_START, {
                    'filename': file_name
                })

            self._lock.release()

        return self._current_video_file_name

    def video_stop(self):
        """
        Stop recording video
        :return:
        """
        if self._recording_video:
            self._lock.acquire()
            Log.info('Stopping video for "' + self.code + '"')

            file_name = self._current_video_file_name

            self._recording_video = False
            self._current_video_file_name = None
            self._current_video.release()

            self.get_manager().send_intercom_message(CamManager.INTERCOM_MESSAGE_EVENT_VIDEO_STOP, {
                'filename': file_name
            })
            self._lock.release()

            return file_name

        return None

    def decorate_image(self, img):
        height, width, layers = img.shape

        if not self.cam_is_online:
            rectangle = numpy.array([[0, 0], [width, 0], [width, height], [0, height]], numpy.int32)
            cv2.fillPoly(img, [rectangle], 1)

            cv2.putText(img, 'NO-SIGNAL',
                        (15, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        else:
            rectangle = numpy.array([[0, height - 20], [0, height], [width, height], [width, height - 20]], numpy.int32)
            cv2.fillPoly(img, [rectangle], 1)

        cv2.putText(img, self.name,
                    (10, height - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        cv2.putText(img, strftime("%Y/%m/%d %H:%M:%S", localtime()),
                    (width - 155, height - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    def start_timelapse(self):
        last_file_name = None

        while not self._stop:
            if self.timelapse > 0:
                img = self.image

                if img is not None:
                    self._lock.acquire()
                    file_name = self.get_capture_file(self.get_manager().get_timelapse_file_template())

                    if file_name != last_file_name:
                        if self._timelapse_video is not None:
                            self._timelapse_video.release()

                        height, width, layers = img.shape
                        fourcc = cv2.VideoWriter_fourcc(*self.get_manager().get_video_fourcc())

                        Log.info('Starting new timelapse record for "' + self.code + '": ' + file_name)
                        self._timelapse_video = cv2.VideoWriter(file_name, fourcc, 30, (width, height))

                    self._timelapse_video.write(img)

                    last_file_name = file_name
                    self._lock.release()

                time.sleep(self.timelapse)

            else:
                time.sleep(1)

    def _restart(self):
        self._lock.acquire()

        self._current_url = self.url
        self._current_type = self.type
        self._old_frames_collection.clear()

        self.adapter = CamManager.get_instance().create_adapter_class(cam=self)
        if self.adapter is None:
            self._lock.release()
            return

        if self._capture is not None:
            self._capture.release()

        self._capture = cv2.VideoCapture(self.url)
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 5)

        self._lock.release()

    def restart(self):
        """
        Try to restart camera
        :return:
        """
        if not self.cam_is_online:
            self._restart()

    def reload(self):
        """
        Reload camera settings trying to not break existing stream
        :return:
        """
        if self._current_url != self.url or self._current_type != self.type:
            self._restart()

    @property
    def image(self):
        if self.cam_is_online and self._new_frame:
            self._new_frame = False
            rc, img = self._capture.retrieve()
            if rc and img is not None:
                self.decorate_image(img)
                self._image = img

        return self._image

    def start_grabber(self):
        """
        Main frames grabbing cycle
        :return:
        """
        while not self._stop:
            self.restart()

            while not self._stop:
                rc = self._capture.grab()
                if not rc:
                    if self.cam_is_online:
                        self.cam_is_online = False
                        if self._image is not None:
                            self.decorate_image(self._image)
                        Log.error("Cam " + self.code + " off-line")
                    break

                self._new_frame = True

                if self._recording_video:
                    self._lock.acquire()

                    if self._recording_video:
                        self._current_video.write(self.image)

                    self._lock.release()

                if not self.cam_is_online:
                    self.cam_is_online = True
                    Log.info("Cam " + self.code + " on-line")

            self.cam_is_online = False
            if not self._stop:
                time.sleep(self.CAM_RECONNECT_TIMEOUT)

    def start(self):
        if self.timelapse > 0:
            threading.Thread(target=self.start_timelapse).start()

        threading.Thread(target=self.start_grabber).start()

    def stop(self):
        Log.info('Stopping cam ' + self.code)

        self.video_stop()

        self._lock.acquire()
        self._stop = True
        if self._timelapse_video is not None:
            self._timelapse_video.release()
        if self._capture is not None:
            self._capture.release()
        self._lock.release()


class CamManager(Component):
    COMPONENT_TYPE = 'cam-manager'

    INTERCOM_MESSAGE_DO_SNAPSHOT = 'cam-do-snapshot'
    INTERCOM_MESSAGE_DO_VIDEO_START = 'cam-do-video-start'
    INTERCOM_MESSAGE_DO_VIDEO_STOP = 'cam-do-video-stop'

    INTERCOM_MESSAGE_DO_COMMAND_PREFIX = 'cam-command-'
    INTERCOM_MESSAGE_DO_COMMAND_GO_PRESET = 'cam-command-go-preset'

    INTERCOM_MESSAGE_EVENT_SNAPSHOT = 'cam-event-snapshot'
    INTERCOM_MESSAGE_EVENT_VIDEO_START = 'cam-event-video-start'
    INTERCOM_MESSAGE_EVENT_VIDEO_STOP = 'cam-event-video-stop'

    def _on_cam_action(self, message: Message) -> Reply:
        payload = message.message_payload

        cam = CamRepo.get_by_code(payload['cam'])
        if cam is None:
            return Reply(Reply.INTERCOM_STATUS_NOT_FOUND)

        if message == self.INTERCOM_MESSAGE_DO_SNAPSHOT:
            return Reply(Reply.INTERCOM_STATUS_SUCCESS, {
                'filename': cam.snapshot()
            })
        elif message == self.INTERCOM_MESSAGE_DO_VIDEO_START:
            return Reply(Reply.INTERCOM_STATUS_SUCCESS, {
                'filename': cam.video_start()
            })
        elif message == self.INTERCOM_MESSAGE_DO_VIDEO_STOP:
            return Reply(Reply.INTERCOM_STATUS_SUCCESS, {
                'filename': cam.video_stop()
            })

        if self.INTERCOM_MESSAGE_DO_COMMAND_PREFIX in message.message_type:
            return cam.on_cam_command(message)

        return Reply(Reply.INTERCOM_STATUS_NOT_FOUND)

    def _on_intercom_message(self, message: Message) -> Reply:
        if (message in [
            self.INTERCOM_MESSAGE_DO_SNAPSHOT,
            self.INTERCOM_MESSAGE_DO_VIDEO_START,
            self.INTERCOM_MESSAGE_DO_VIDEO_STOP
        ]) or (self.INTERCOM_MESSAGE_DO_COMMAND_PREFIX in message.message_type):
            return self._on_cam_action(message)

        return Component._on_intercom_message(self, message)

    def get_capture_path(self):
        os.makedirs(self._params['capture_path'], 0o750, True)
        return self._params['capture_path']

    def get_video_file_template(self):
        return self._params['video_file']

    def get_snapshot_file_template(self):
        return self._params['snapshot_file']

    def get_timelapse_file_template(self):
        return self._params['timelapse_file']

    def get_video_fourcc(self):
        return self._params['video_fourcc']

    def create_adapter_class(self, cam):
        if cam.type not in self._params['adapters']:
            return None

        adapter_info = self._params['adapters'][cam.type]
        module_name, class_name = adapter_info.split('/', 2)

        module = importlib.import_module(module_name)
        adapter_class = getattr(module, class_name)

        return adapter_class(cam)

    def _reload(self):
        CamRepo.load()
        return True

    def start(self):
        Component.start(self)
        CamRepo.load()


class CamRepo:
    cams = {}
    _load_lock = Lock()

    @classmethod
    def _get_cams_file(cls):
        return App.get_settings_path() + '/cams.yml'

    @classmethod
    def load(cls):
        """
        Load YML signals file
        """

        cls._load_lock.acquire()
        cams_file = cls._get_cams_file()

        try:
            cams = yaml.load(open(cams_file, 'r'))
            Log.info("Loading cams information from " + cams_file)
        except:
            Log.error("Loading cams information failed from " + cams_file)
            return

        # Update / Create cams
        new_codes = []
        for cam_code, cam_info in cams.items():
            if 'frames_history' in cam_info:
                frames_history = int(cam_info['frames_history'])
            else:
                frames_history = 0

            # New cam
            if cam_code not in cls.cams:
                cam = Cam(
                    code=cam_code,
                    name=cam_info['name'],
                    cam_type=cam_info['type'],
                    params=cam_info['params'],
                    timelapse=cam_info['timelapse'],
                    frames_history=frames_history
                )
                threading.Thread(target=cam.start).start()
                cls.cams[cam.code] = cam

            # Existing cam
            else:
                cam = cls.cams[cam_code]
                cam.name = cam_info['name']
                cam.params = cam_info['params']
                cam.type = cam_info['type']
                cam.timelapse = cam_info['timelapse']
                cam.frames_history = cam_info['frames_history']
                cam.reload()

            new_codes.append(cam.code)

        # Delete old cams
        cams_to_delete = []
        for cam_code, cam in cls.cams.items():
            if cam_code not in new_codes:
                cam.stop()
                cams_to_delete.append(cam_code)

        for cam_code in cams_to_delete:
            del cls.cams[cam_code]

        cls._load_lock.release()

    @classmethod
    def get_by_code(cls, code) -> Cam:
        if code in cls.cams:
            return cls.cams[code]

        return None


class CamAdapter:
    TYPE = 'unknown'
    cam = None

    def __init__(self, cam: Cam):
        self.cam = cam

    def get_cam_params(self):
        return self.cam.params

    def get_streaming_url(self):
        return None

    def on_cam_command(self, message: Message) -> Reply:
        return Reply(Reply.INTERCOM_STATUS_NOT_FOUND)
