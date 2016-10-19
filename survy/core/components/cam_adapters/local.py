from survy.core.components.cam import CamAdapter


class LocalAdapter(CamAdapter):
    def get_streaming_url(self):
        params = self.get_cam_params()
        return params['device']
