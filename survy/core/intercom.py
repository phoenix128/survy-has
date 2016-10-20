import copy
import re

from survy.core.log import Log


class Reply:
    INTERCOM_MESSAGE_REPLY = 'reply'

    INTERCOM_STATUS_NOT_FOUND = 'not-found'
    INTERCOM_STATUS_SUCCESS = 'success'
    INTERCOM_STATUS_FAILURE = 'failure'
    INTERCOM_STATUS_NON_BLOCKING_FAILURE = 'non-blocking-failure'

    _status = None
    _payload = None

    def __init__(self, status, payload=None):
        self.set_status(status)
        self.set_payload(payload)

    def set_status(self, value):
        self._status = value

    def set_payload(self, value):
        self._payload = value

    def get_status(self):
        return self._status

    def get_http_status(self):
        if self.get_status() == self.INTERCOM_STATUS_NOT_FOUND:
            return 404

        if self.get_status() == self.INTERCOM_STATUS_SUCCESS:
            return 200

        return 500

    def get_payload(self):
        return self._payload

    def to_dict(self):
        return {
            'message': self.INTERCOM_MESSAGE_REPLY,
            'status': self.get_status(),
            'payload': self.get_payload(),
        }

    def __eq__(self, other):
        return other == self.get_status()


class Message:
    INTERCOM_RECIPIENT_BROADCAST = '_all'
    INTERCOM_RECIPIENT_TYPE_BROADCAST = '_type'

    message_from = None
    message_to = None
    message_type = None
    message_payload = None

    def __init__(self, message_from, message_to, message_type, message_payload=None):
        self.message_from = message_from
        self.message_to = message_to
        self.message_type = message_type
        self.message_payload = message_payload

    def to_dict(self):
        return {
            'message': self.message_type,
            'from': self.message_from,
            'to': self.message_to,
            'payload': self.message_payload,
        }

    def copy(self):
        return Message(
            message_from=self.message_from,
            message_to=self.message_to,
            message_type=self.message_type,
            message_payload=copy.deepcopy(self.message_payload)
        )

    def get_recipients(self):
        """
        Get a list of recipient components
        :return: A list of components code
        """
        from survy.core.app import App

        if isinstance(self.message_to, list):
            return self.message_to

        if self.message_to == self.INTERCOM_RECIPIENT_BROADCAST:
            return App.components.get_list()

        # Type broadcast
        m = re.search('^' + self.INTERCOM_RECIPIENT_TYPE_BROADCAST + r':(?P<type>.+)$', self.get_message_to())
        if m:
            return App.components.get_list(m.group('type'))

        return [self.message_to]

    def __eq__(self, other):
        return other == self.message_type

    def send(self) -> Reply:
        """
        Send a message to intercom channel
        :return: Message reply
        """
        from survy.core.app import App

        found = False
        res = {}
        status = Reply.INTERCOM_STATUS_SUCCESS

        recipients = self.get_recipients()
        for component in recipients:
            component_instance = App.components.get(component)

            if component_instance is not None:
                reply = component_instance.handle_intercom_message(self)

                if reply is not None:
                    if reply != Reply.INTERCOM_STATUS_NOT_FOUND:
                        # At least one component can handle our message
                        found = True

                        if reply == Reply.INTERCOM_STATUS_FAILURE:
                            # Set failure when at least one component replies with failure
                            status = Reply.INTERCOM_STATUS_FAILURE

                        res[component] = reply.to_dict()

            else:
                Log.error('Unknown component: ' + component)

        if not found:
            return Reply(Reply.INTERCOM_STATUS_NOT_FOUND)

        return Reply(status, res)
