import copy
import re
import threading

import time
import yaml

from survy.core.app import App
from survy.core.component import Component
from survy.core.intercom import Reply, Message
from survy.core.log import Log
from survy.core.utils import Utils


class RuleManager(Component):
    pass


class Event(Message):
    pass


class Rule:
    pass


class Event(Message):
    message = None

    @classmethod
    def create_from_message(cls, message: Message) -> Event:
        event = Event(
            message_type=message.message_type,
            message_from=message.message_from,
            message_to=message.message_to,
            message_payload=message.message_payload
        )

        event.message = message
        return event

    def matches(self, other: Event):
        """
        Check if event matches and return a dict of variables or False on failure
        :param other:
        :return:
        """
        matching_vars = {}

        if other.message_type != self.message_type:
            return False

        other_payload = other.message_payload
        if other_payload is None:
            other_payload = {}

        payload = Utils.replace_variables_dict(self.message_payload)
        for k, v in payload.items():
            if k not in other_payload:
                return False

            if isinstance(v, list):
                check_type = v[0]
                check_values = v[1:]
            else:
                check_type = 'ieq'
                check_values = [v]

            res = Utils.complex_match(
                check_type=check_type,
                check_value=check_values,
                value=other_payload[k]
            )

            # Need strict check here
            if res is False:
                return False

            matching_vars.update(res)

        return matching_vars


class Condition:
    _condition_payload = None

    def __init__(self, condition_payload):
        self.set_condition_payload(condition_payload)

    def set_condition_payload(self, value):
        self._condition_payload = value

    def get_condition_payload(self):
        return self._condition_payload

    def matches(self):
        other_payload = App.get_variables()
        payload = Utils.replace_variables_dict(self.get_condition_payload())

        for k, v in payload.items():
            if k not in other_payload:
                return False

            if isinstance(v, list):
                check_type = v[0]
                check_values = v[1:]
            else:
                check_type = 'ieq'
                check_values = [v]

            if Utils.complex_match(
                check_type=check_type,
                check_value=check_values,
                value=other_payload[k]
            ) is False:
                return False

        return True


class Action(Message):
    _async = False
    _delay = 0

    def __init__(self, message_from, message_to, message_type,
                 action_async=False, action_delay=0, message_payload=None):

        Message.__init__(
            self,
            message_from=message_from,
            message_to=message_to,
            message_type=message_type,
            message_payload=message_payload
        )

        self.async = action_async
        self.delay = action_delay

    @property
    def async(self):
        return self._async

    @async.setter
    def async(self, value):
        self._async = int(value)

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, value):
        self._delay = int(value)

    def fire(self, variables):
        if self.async:
            threading.Thread(target=self._fire, kwargs={
                'variables': variables,
                'delay': self.delay
            }).start()

        else:
            self._fire(
                variables=variables,
                delay=self.delay
            )

    def _fire(self, variables, delay=0):
        time.sleep(delay)
        Log.info('Firing action "' + self.message_type + '"')

        message_to_send = self.copy()

        payload = message_to_send.message_payload
        new_payload = Utils.replace_variables_dict(payload, variables)

        message_to_send.message_payload = new_payload
        return message_to_send.send()


class Rule:
    _code = None
    name = None
    actions = None
    events = None
    conditions = None

    def __init__(self, code, name, actions, events, conditions):
        self.code = code
        self.name = name
        self.actions = actions
        self.events = events
        self.conditions = conditions

    @property
    def code(self):
        if self._code is None and self.name is not None:
            self.code = self.name

        return self._code

    @code.setter
    def code(self, value):
        if value is not None:
            value = re.sub(r'[\W\s]+', '_', value.lower())

        self._code = value

    def match_event(self, search_event: Event):
        """
        Check if rules events match and return a dict of variables or False on failure
        :param search_event:
        :return:
        """
        events = self.events
        for event in events:
            res = event.matches(search_event)
            if res is not False:
                conditions = self.conditions

                if len(conditions) == 0:
                    return res

                for condition in conditions:
                    if condition.matches():
                        return res

        return False

    def fire_actions(self, variables):
        actions = self.actions
        for action in actions:
            action.fire(variables)


class RuleRepo:
    _rules = []

    @classmethod
    def _get_rules_file(cls):
        return App.get_settings_path() + '/rules.yml'

    @classmethod
    def load(cls):
        """
        Load YML rules file
        """
        cls._rules = []

        rules_file = cls._get_rules_file()
        try:
            rules = yaml.load(open(rules_file, 'r'))
            Log.info("Loading rules information from " + rules_file)
        except:
            Log.error("Loading rules information failed from " + rules_file)
            return

        for rule_code, rule_info in rules.items():

            event_instances = []
            action_instances = []
            condition_instances = []

            for event in rule_info['events']:
                if 'type' not in event:
                    Log.error('Missing "type" for event on rule "' + rule_code + '"')
                    continue

                payload = {}
                if 'payload' in event:
                    payload = event['payload']

                component = None
                if 'component_from' in event:
                    component = event['component_from']

                event_instances.append(Event(
                    message_from=component,
                    message_to='',
                    message_type=event['type'],
                    message_payload=payload
                ))

            for action in rule_info['actions']:
                if 'type' not in action:
                    Log.error('Missing "type" for action on rule "' + rule_code + '"')
                    continue

                payload = {}
                if 'payload' in action:
                    payload = action['payload']

                component = '_all'
                if 'component_to' in action:
                    component = action['component_to']

                async = False
                if 'async' in action:
                    async = action['async']

                delay = False
                if 'delay' in action:
                    delay = action['delay']

                action_instances.append(Action(
                    message_to=component,
                    message_from=RuleManager.get_instance().get_code(),
                    message_type=action['type'],
                    message_payload=payload,
                    action_async=async,
                    action_delay=delay
                ))

            if 'conditions' in rule_info:
                for condition in rule_info['conditions']:
                    if 'payload' in condition:
                        payload = condition['payload']
                        condition_instance = Condition(
                            condition_payload=payload
                        )
                        condition_instances.append(condition_instance)

            if 'name' not in rule_info:
                rule_info['name'] = rule_code

            rule = Rule(
                code=rule_code,
                name=rule_info['name'],
                events=event_instances,
                actions=action_instances,
                conditions=condition_instances
            )

            cls._rules.append(rule)

    @classmethod
    def get_rules(cls):
        return cls._rules


class RuleManager(Component):
    COMPONENT_TYPE = 'rule-manager'

    INTERCOM_MESSAGE_RULE_TRIGGERED_PREFIX = 'rule-triggered-'

    def _trigger_rule_event(self, rule: Rule, message: Message):
        self.send_intercom_message(
            self.INTERCOM_MESSAGE_RULE_TRIGGERED_PREFIX + rule.code, message.message_payload)

    def _on_intercom_message(self, message: Message) -> Reply:
        event = Event.create_from_message(message)

        all_rules = RuleRepo.get_rules()
        for rule in all_rules:
            res = rule.match_event(event)
            if res is not False:
                Log.info('Triggering rule: ' + rule.code)

                variables = copy.deepcopy(message.message_payload)
                variables.update(res)

                threading.Thread(target=rule.fire_actions, kwargs={
                    'variables': variables
                }).start()

                threading.Thread(target=self._trigger_rule_event, kwargs={
                    'rule': rule,
                    'message': message
                }).start()

        return Component._on_intercom_message(self, message)

    def _reload(self):
        RuleRepo.load()
        return True

    def start(self):
        Component.start(self)
        RuleRepo.load()
