import urllib
import urllib.request
import urllib.parse

from survy.core.component import Component
from survy.core.intercom import Reply, Message


class WebClientManager(Component):
    COMPONENT_TYPE = 'webclient-manager'

    INTERCOM_MESSAGE_DO_GET = 'webclient-do-get'
    INTERCOM_MESSAGE_DO_POST = 'webclient-do-post'

    def _run_client(self, message: Message) -> Reply:
        payload = message.message_payload
        url = payload['url']

        data = None
        if 'data' in payload:
            data = payload['data']

        # Post request
        if 'method' in payload and payload['method'].lower() == 'post':
            if data is not None:
                data = {}
            req = urllib.request.Request(url, data)

        # Get request
        else:
            if data is not None:
                url += '?' + urllib.parse.urlencode(data)
            req = urllib.request.Request(url)

        urllib.request.urlopen(req).read()

        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _on_intercom_message(self, message: Message) -> Reply:
        if message in [self.INTERCOM_MESSAGE_DO_GET, self.INTERCOM_MESSAGE_DO_POST]:
            return self._run_client(message)

        return Component._on_intercom_message(self, message)
