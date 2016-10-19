import urllib.parse
import urllib.request

from survy.core.components.cam import CamAdapter, CamManager
from survy.core.intercom import Reply, Message


class FoscamMjpegAdapter(CamAdapter):
    def get_streaming_url(self):
        params = self.get_cam_params()

        url_values = urllib.parse.urlencode({
            'user': params['user'],
            'pwd': params['pass'],
        })

        return 'http://' + params['host'] + '/videostream.cgi?' + url_values + '&.mjpg'

    def _decoder_control_command(self, command):
        params = self.get_cam_params()

        data = {
            'user': params['user'],
            'pwd': params['pass'],
            'command': str(command)
        }

        url = 'http://' + params['host'] + '/decoder_control.cgi?' + urllib.parse.urlencode(data)
        req = urllib.request.Request(url)
        res = urllib.request.urlopen(req).read().decode("utf-8")

        if 'ok.' in res:
            return Reply(Reply.INTERCOM_STATUS_SUCCESS)

        return Reply(Reply.INTERCOM_STATUS_FAILURE)

    def _on_cam_command_go_preset(self, message: Message) -> Reply:
        payload = message.message_payload

        position = 1
        if 'position' in payload:
            position = int(payload['position'])

        command_no = 31 + max(0, position-1) * 2

        return self._decoder_control_command(command_no)

    def on_cam_command(self, message: Message) -> Reply:
        if message == CamManager.INTERCOM_MESSAGE_DO_COMMAND_GO_PRESET:
            return self._on_cam_command_go_preset(message)

        return CamAdapter.on_cam_command(self, message)


class FoscamH264Adapter(CamAdapter):
    def get_streaming_url(self):
        params = self.get_cam_params()

        return 'rtsp://' + params['user'] + ':' + params['pass'] + '@' + params['host'] + '/videoMain'