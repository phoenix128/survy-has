from survy.core.app import App
from survy.core.component import Component


class AppManager(Component):
    """
    Simple class to forward intercom messages to app
    """
    def _reload(self):
        return App.reload()
