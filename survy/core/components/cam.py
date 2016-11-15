import glob
import importlib
import os
import re
import threading

from threading import Lock

import time

import sys
import yaml

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

    _current_params = {}
    _current_type = None

    def __init__(self, code, name, cam_type, params, timelapse):
        self.code = code
        self.name = name
        self.type = cam_type
        self.params = params
        self.timelapse = timelapse

        self._lock = Lock()

    @property
    def timelapse(self):
        return int(self._timelapse)

    @timelapse.setter
    def timelapse(self, value):
        self._timelapse = int(value)

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, value):
        value = re.sub(r'[\W\s]+', '_', value.lower())
        self._code = value

    def get_manager(self) -> CamManager:
        return CamManager.get_instance()

    def get_capture_file(self, template, params=None):
        res = self.get_file_template(template, params)
        os.makedirs(os.path.dirname(res), 0o750, True)
        return res

    def get_file_template(self, template, params=None):
        if params is None:
            params = {}

        params['code'] = self.code

        template = Utils.replace_variables_text(template, params)

        return self.get_manager().get_capture_path() + '/' + template

    def on_cam_command(self, message: Message) -> Reply:
        if self.adapter is None:
            return Reply(Reply.INTERCOM_STATUS_NOT_FOUND)

        return self.adapter.on_cam_command(message)

    def snapshot(self):
        """
        Take snapshot from cam
        :return:
        """

        file_name = self.get_capture_file(self.get_manager().get_snapshot_file_template())
        Log.info('Taking snapshot from "' + self.code + '": ' + file_name)

        self.adapter.do_snapshot(file_name)

        self.get_manager().send_intercom_message(CamManager.INTERCOM_MESSAGE_EVENT_SNAPSHOT, {
            'filename': file_name
        })

        return file_name

    def video_start(self):
        """
        Start recording video
        :return:
        """
        pass

    def video_stop(self):
        """
        Stop recording video
        :return:
        """
        pass

    def _create_tl_videos(self):
        path = self.get_file_template(self.get_manager().get_timelapse_snap_glob_template())
        timelapses_path = glob.glob(path)

        avconv = self.get_manager().get_avconv()

        for tl_path in timelapses_path:
            current_tl_file_name = self.get_capture_file(self.get_manager().get_timelapse_snap_template())
            current_tl_path = os.path.dirname(current_tl_file_name)

            if os.path.isdir(tl_path) and tl_path != current_tl_path:
                Log.info('Creating timelapse for "' + current_tl_path + '"')
                os.system(avconv + ' -y -r 10 -i ' + tl_path + '/%06d.jpg -q:v 0 ' + tl_path + '.avi')
                os.system('rm -Rf ' + tl_path)

    def start_timelapse(self):
        last_file_name = None
        n = 0

        while not self._stop:
            if self.timelapse > 0:
                file_name = self.get_capture_file(self.get_manager().get_timelapse_snap_template())

                if file_name != last_file_name:
                    n = 0
                    Log.info('Starting new timelapse record for "' + self.code + '": ' + file_name)

                    threading.Thread(target=self._create_tl_videos).start()

                last_file_name = file_name

                snapshot_file_name = None
                while True:
                    snapshot_file_name = self.get_capture_file(self.get_manager().get_timelapse_snap_template(), {
                        'n': str(n).zfill(6)
                    })

                    if os.path.exists(snapshot_file_name):
                        n += 1
                    else:
                        break

                self.adapter.do_snapshot(snapshot_file_name)

                time.sleep(self.timelapse)
                n += 1
            else:
                time.sleep(1)

    def restart(self):
        """
        Try to restart camera
        :return:
        """
        self.adapter = CamManager.get_instance().create_adapter_class(cam=self)

    def reload(self):
        """
        Reload camera settings trying to not break existing stream
        :return:
        """
        if \
            self._current_type != self.type or \
                len(self._current_params) != len(self.params) or \
                len(set(self._current_params.items()) & set(self.params.items())) != len(self.params.items()):

            self.restart()

    def start(self):
        self.reload()

        if self.timelapse > 0:
            threading.Thread(target=self.start_timelapse).start()

    def stop(self):
        Log.info('Stopping cam ' + self.code)

        self.video_stop()
        self._stop = True


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

    # Do not change
    TEMPLATE_SNAPSHOT_FILE = '%time_day%/snap_%code%_%time_ts%.jpg'
    TEMPLATE_VIDEO_FILE = '%time_day%/video_%code%_%time_ts%.avi'
    TEMPLATE_TL_VIDEO = '%time_day%/timelapse/%code%_%time_day%_%time_hour%.avi'
    TEMPLATE_TL_SNAP = '%time_day%/timelapse/%code%_%time_day%_%time_hour%/%n%.jpg'

    TEMPLATE_TL_SNAP_PATHS_GLOB = '%time_day%/timelapse/%code%_*'

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
        return self.TEMPLATE_VIDEO_FILE

    def get_snapshot_file_template(self):
        return self.TEMPLATE_SNAPSHOT_FILE

    def get_timelapse_video_template(self):
        return self.TEMPLATE_TL_VIDEO

    def get_timelapse_snap_template(self):
        return self.TEMPLATE_TL_SNAP

    def get_timelapse_snap_glob_template(self):
        return self.TEMPLATE_TL_SNAP_PATHS_GLOB

    def get_avconv(self):
        return self._params['avconv']

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
            # New cam
            if cam_code not in cls.cams:
                cam = Cam(
                    code=cam_code,
                    name=cam_info['name'],
                    cam_type=cam_info['type'],
                    params=cam_info['params'],
                    timelapse=cam_info['timelapse']
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

    def do_snapshot(self, file_name):
        return None

    def on_cam_command(self, message: Message) -> Reply:
        return Reply(Reply.INTERCOM_STATUS_NOT_FOUND)
