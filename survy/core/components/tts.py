import os
import re

import subprocess

from survy.core.component import Component
from survy.core.intercom import Reply, Message


class TtsManager(Component):
    COMPONENT_TYPE = 'tts-manager'

    INTERCOM_MESSAGE_DO_SAY = 'tts-do-say'

    _sp = None

    def _on_say_text(self, message: Message):
        payload = message.get_message_payload()

        params_fail = self.check_required_parameters(payload, ['text'])
        if params_fail:
            return params_fail

        self.say_text(payload['text'])
        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _on_intercom_message(self, message: Message) -> Reply:
        if message == self.INTERCOM_MESSAGE_DO_SAY:
            return self._on_say_text(message)

        return Component._on_intercom_message(self, message)

    def command(self, cmd):
        self._sp.stdin.write(cmd+"\n")
        self._sp.stdin.flush()

    def say_text(self, text):
        text = re.sub(r'[^\w\,\.\!\s]+', ' ', text)
        message = '(SayText "'+text+'")'

        self.command(message)

    def start(self):
        Component.start(self)

        # Raise volume
        os.system("/usr/bin/amixer set PCM -- 90%")

        self._sp = subprocess.Popen(self._params['festival_bin'],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   universal_newlines=True)

        self.command('(' + self._params['voice'] + ')')
