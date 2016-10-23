import yaml

from survy.core.app import App
from survy.core.component import Component
from survy.core.intercom import Message, Reply
from survy.core.log import Log


class RunlevelManager(Component):
    COMPONENT_TYPE = 'runlevel-manager'

    INTERCOM_MESSAGE_EVENT_RUNLEVEL_CHANGE = 'runlevel-event-change'
    INTERCOM_MESSAGE_DO_RUNLEVEL_CHANGE = 'runlevel-do-change'

    runlevel = None

    def get_variables(self):
        return {
            'runlevel': self.runlevel
        }

    def _get_runlevel_file(self):
        return App.get_settings_path() + '/runlevel.yml'

    def _on_set_runlelvel(self, message: Message) -> Reply:
        payload = message.message_payload

        params_fail = self.check_required_parameters(payload, ['runlevel'])
        if params_fail:
            return params_fail

        self.set_current(payload['runlevel'])
        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _on_intercom_message(self, message: Message) -> Reply:
        if message == self.INTERCOM_MESSAGE_DO_RUNLEVEL_CHANGE:
            return self._on_set_runlelvel(message)

        return Component._on_intercom_message(self, message)

    def load(self):
        runlevel_file = self._get_runlevel_file()
        try:
            runlevel = yaml.load(open(runlevel_file, 'r'))

            Log.info("Loading runlevel information from " + runlevel_file)
            self.runlevel = runlevel['runlevel']

        except:
            Log.warn("Loading runlevel information failed from " + runlevel_file)

            self.runlevel = 'default'
            self.save()

    def save(self):
        runlevel_file = self._get_runlevel_file()
        yaml.dump({'runlevel': self.runlevel}, open(runlevel_file, 'w'), default_flow_style=False)

    def get_current(self):
        return self.runlevel

    def set_current(self, runlevel):
        if self.get_current() != runlevel:
            self.send_intercom_message(self.INTERCOM_MESSAGE_EVENT_RUNLEVEL_CHANGE, {
                'runlevel': runlevel
            })

            self.runlevel = runlevel
            self.save()

    def start(self):
        Component.start(self)
        self.load()

