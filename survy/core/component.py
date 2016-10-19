import traceback

from survy.core.collection import Collection
from survy.core.intercom import Reply, Message
from survy.core.log import Log


class ComponentCollection(Collection):
    pass


class Component:
    COMPONENT_TYPE = 'generic'
    COMPONENT_SINGLETON = True

    INTERCOM_MESSAGE_DO_RELOAD = 'reload'

    _instance_code = None

    _code = None
    _name = None
    _params = None

    def __init__(self, code, name, params=None):
        if params is None:
            params = {}

        if self.COMPONENT_SINGLETON:
            if self.__class__.get_instance() is not None:
                Log.error(self.__class__.__name__ + ' cannot be allocated more than once')
                raise Exception(self.__class__.__name__ + ' cannot be allocated more than once')

        self._code = code
        self._name = name
        self._params = params

        Log.info('Daemon ' + self.get_code() + ' loaded')

    def get_variables(self):
        return {}

    @classmethod
    def set_instance_code(cls, code):
        if cls._instance_code is None:
            cls._instance_code = code

    @classmethod
    def get_instance(cls):
        from survy.core.app import App
        return App.components.get(cls._instance_code)

    def get_code(self):
        return self._code

    def get_name(self):
        return self._name

    def create_intercom_message(self, component_to, message_type, message_payload) -> Message:
        return Message(
            message_from=self.get_code(),
            message_to=component_to,
            message_type=message_type,
            message_payload=message_payload
        )

    def send_intercom_message(self, message_type, message_payload=None) -> Reply:
        return self.create_intercom_message(Message.INTERCOM_RECIPIENT_BROADCAST, message_type, message_payload).send()

    @classmethod
    def check_required_parameters(cls, payload, required_params):
        """
        Check a list of parameters that must be defined in payload.

        :param payload: Payload to be verified
        :param required_params: A list of required parameters name
        :return: False on success or a list of errors
        """
        for required_param in required_params:
            if required_param not in payload:
                return Reply(Reply.INTERCOM_STATUS_FAILURE, {
                    'Missing ' + required_param + ' parameter'
                })

        return False

    def _reload(self):
        return None

    def reload(self):
        """
        Reload settings
        :return:
        """
        if self._reload() is True:
            return Reply(Reply.INTERCOM_STATUS_SUCCESS)

        elif self._reload() is False:
            return Reply(Reply.INTERCOM_STATUS_FAILURE)

        return None

    def _on_intercom_message(self, message: Message) -> Reply:
        """
        Internally handle an incoming message. Protected method to be overridden.

        :param message: Message to be sent
        :return: Message reply
        """

        if message == self.INTERCOM_MESSAGE_DO_RELOAD:
            return self.reload()

        return Reply(Reply.INTERCOM_STATUS_NOT_FOUND, {
            'message': 'Task not found in this component'
        })

    def handle_intercom_message(self, message: Message) -> Reply:
        """
        Handle an incoming message from another component

        :param message: Message to be sent
        :return: Message reply
        """
        try:
            return self._on_intercom_message(message)
        except Exception as e:
            Log.error(
                "Intercom message " + message.message_type + " failed:" + traceback.format_exc())
            return Reply(Reply.INTERCOM_STATUS_FAILURE, {'message': str(e)})

    def start(self):
        """
        Start component
        """
        Log.info('Daemon ' + self.get_code() + ' started')
