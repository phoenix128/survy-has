import threading

import serial
import select
import re

import time
import yaml

from survy.core.app import App
from survy.core.component import Component
from survy.core.intercom import Message, Reply
from survy.core.log import Log


class Signal:
    pass


class SignalManager(Component):
    COMPONENT_TYPE = 'signal-manager'

    INTERCOM_MESSAGE_EVENT_SIGNAL_RECEIVED = 'signal-event-received'
    INTERCOM_MESSAGE_EVENT_SIGNAL_RECOGNIZED = 'signal-event-recognized'
    INTERCOM_MESSAGE_EVENT_LEARN_START = 'signal-event-learn-start'
    INTERCOM_MESSAGE_EVENT_LEARN_NEW_SIGNAL = 'signal-event-learn-new-signal'
    INTERCOM_MESSAGE_EVENT_LEARN_END = 'signal-event-learn-end'
    INTERCOM_MESSAGE_DO_LEARN = 'signal-do-learn'

    SIGNAL_RELAX_TIME = .1

    _learning_signal = None
    _last_learning_signal = None

    _free_channel_ts = None

    def _can_send_message(self):
        return self._free_channel_ts is None or self._free_channel_ts < time.time()

    def _delay_signal(self):
        self._free_channel_ts = time.time() + float(self._params['signals-interval'])

    def _on_signal(self, signal: Signal):
        Log.info("Received signal: " + str(signal))

        self._delay_signal()

        if self.is_learning():
            if signal == self._last_learning_signal:
                self._learn_signal(signal)

            self._last_learning_signal = signal

        else:
            self.send_intercom_message(SignalManager.INTERCOM_MESSAGE_EVENT_SIGNAL_RECEIVED, signal.to_dict())

            recognized_signal = SignalRepo.get_by_signal(signal)
            if recognized_signal is not None:
                Log.info("Recognized signal: " + str(recognized_signal))
                self.send_intercom_message(SignalManager.INTERCOM_MESSAGE_EVENT_SIGNAL_RECOGNIZED,
                                           recognized_signal.to_dict())

    def _learn_signal(self, signal: Signal):
        Log.info("Learning signal " + str(signal))

        self._learning_signal.set_manager(signal.get_manager())
        self._learning_signal.set_code(signal.get_code())
        self._learning_signal.set_dump(signal.get_dump())

        SignalRepo.add(self._learning_signal)

        self.send_intercom_message(self.INTERCOM_MESSAGE_EVENT_LEARN_NEW_SIGNAL, signal.to_dict())
        self.send_intercom_message(self.INTERCOM_MESSAGE_EVENT_LEARN_END)

    def is_learning(self):
        return self._learning_signal is not None

    def _on_learn_start(self, message: Message) -> Reply:
        payload = message.get_message_payload()

        self._last_learning_signal = None
        params_fail = self.check_required_parameters(payload, ['device', 'sub'])
        if params_fail:
            return params_fail

        self._learning_signal = Signal(
            code='',
            manager=None,
            device_name=payload['device'],
            sub_name=payload['sub'],
        )

        Log.info("Learning start: " + str(self._learning_signal))
        self.send_intercom_message(self.INTERCOM_MESSAGE_EVENT_LEARN_START, self._learning_signal.to_dict())

        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _on_learn_end(self):
        Log.info("Exiting learning mode")

        self._learning_signal = None
        return Reply(Reply.INTERCOM_STATUS_SUCCESS)

    def _on_intercom_message(self, message: Message) -> Reply:
        if message == self.INTERCOM_MESSAGE_DO_LEARN:
            return self._on_learn_start(message)

        if message == self.INTERCOM_MESSAGE_EVENT_LEARN_END:
            return self._on_learn_end()

        return Component._on_intercom_message(self, message)

    def fire(self, signal: Signal):
        t = threading.Thread(target=self._fire_delayed, args=(signal, ))
        t.start()

    def _fire_delayed(self, signal: Signal):
        Log.info('Queuing signal: ' + str(signal))
        while not self._can_send_message():
            time.sleep(self.SIGNAL_RELAX_TIME)

        Log.info('Firing signal: ' + str(signal))
        self._delay_signal()
        self._fire(signal)

    def _fire(self, signal: Signal):
        pass

    def start(self):
        Component.start(self)
        SignalRepo.lazy_load()


class Signal:
    _manager = None
    _code = None
    _dump = None
    _device_name = None
    _sub_name = None
    _device_code = None
    _sub_code = None

    def __init__(self, manager, code, dump=None, device_name=None, sub_name=None, device_code=None, sub_code=None):
        self.set_manager(manager)
        self.set_code(code)
        self.set_dump(dump)
        self.set_device_name(device_name)
        self.set_device_code(device_code)
        self.set_sub_name(sub_name)
        self.set_sub_code(sub_code)

    def set_manager(self, value: SignalManager):
        self._manager = value

    def set_device_name(self, value):
        self._device_name = value

    def set_sub_name(self, value):
        self._sub_name = value

    def set_device_code(self, value):
        if value is not None:
            value = re.sub(r'[\W\s]+', '_', value.lower())
        self._device_code = value

    def set_sub_code(self, value):
        if value is not None:
            value = re.sub(r'[\W\s]+', '_', value.lower())
        self._sub_code = value

    def set_code(self, value):
        self._code = value

    def set_dump(self, value):
        self._dump = value

    def get_manager_code(self):
        if self.get_manager() is None:
            return ''

        return self.get_manager().get_code()

    def get_manager(self) -> SignalManager:
        return self._manager

    def get_device_name(self):
        return self._device_name

    def get_sub_name(self):
        return self._sub_name

    def get_device_code(self):
        if self._device_code is None and self._device_name is not None:
            self.set_device_code(self.get_device_name())

        return self._device_code

    def get_sub_code(self):
        if self._sub_code is None and self._sub_name is not None:
            self.set_sub_code(self.get_sub_name())

        return self._sub_code

    def get_code(self):
        return self._code

    def get_dump(self):
        return self._dump

    def to_dict(self):
        return {
            'manager': self.get_manager_code(),
            'code': self.get_code(),
            'dump': self.get_dump(),
            'device_code': self.get_device_code(),
            'device_name': self.get_device_name(),
            'sub_code': self.get_sub_code(),
            'sub_name': self.get_sub_name(),
        }

    def fire(self):
        self.get_manager().fire(self)

    @classmethod
    def create_from_dict(cls, dict_info):
        """
        Create a signal object from dict representation
        :param dict_info: Dict representation
        :return: Newly created signal
        """
        return Signal(
            manager=dict_info['manager'],
            code=dict_info['code'],
            dump=dict_info['dump'],
            device_code=dict_info['device_code'],
            device_name=dict_info['device_name'],
            sub_code=dict_info['sub_code'],
            sub_name=dict_info['sub_name'],
        )

    def __eq__(self, other):
        return \
            isinstance(other, Signal) and \
            other.get_code() == self.get_code() and \
            other.get_manager_code() == self.get_manager_code()

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        res = ''

        if self.get_code() is not None:
            res = self.get_manager_code() + '/' + self.get_code()

        if self.get_device_name() is not None:
            if res != '':
                res += ': '

            res += self.get_device_name() + ' / ' + self.get_sub_name()

        if res == '':
            res = 'Unknown'

        return res


class SignalRepo:
    _signals = None

    @classmethod
    def _get_signals_file(cls):
        return App.get_settings_path() + '/signals.yml'

    @classmethod
    def lazy_load(cls):
        if cls._signals is None:
            cls.load()

    @classmethod
    def load(cls):
        """
        Load YML signals file
        """

        cls._signals = []

        signals_file = cls._get_signals_file()
        try:
            signals = yaml.load(open(signals_file, 'r'))
            Log.info("Loading signals information from " + signals_file)
        except:
            Log.error("Loading signals information failed from " + signals_file)
            return

        for device_code, device_info in signals.items():
            for sub_code, sub_info in device_info['subs'].items():
                signal = Signal(
                    manager=App.components.get(sub_info['manager']),
                    code=sub_info['code'],
                    dump=sub_info['dump'],
                    device_code=device_code,
                    device_name=device_info['name'],
                    sub_code=sub_code,
                    sub_name=sub_info['name'],
                )

                cls._signals.append(signal)

    @classmethod
    def get_by_code(cls, device_code, sub_code) -> Signal:
        """
        Return a signal from repo identified by device and sub codes

        :param device_code: Device code
        :param sub_code: Sub code
        :return: Identified signal from repo
        """

        cls.lazy_load()
        for s in cls._signals:
            if s.get_device_code() == device_code and s.get_sub_code() == sub_code:
                return s

        return None

    @classmethod
    def get_by_signal(cls, signal: Signal) -> Signal:
        """
        Return a matching signal from repo

        :param signal: Signal to be identified
        :return: Identified signal from repo
        """

        cls.lazy_load()
        for s in cls._signals:
            if s == signal:
                return s

        return None

    @classmethod
    def get_by_dict(cls, dict_repr) -> Signal:
        """
        Get signal from dict representation

        :param dict_repr: Dict representation
        :return: Identified signal
        """

        signal = Signal.create_from_dict(dict_repr)
        return cls.get_by_signal(signal)

    @classmethod
    def add(cls, signal: Signal):
        """
        Add a signal to collection
        :param signal: Signal to be added
        """

        cls.load()
        cls._signals.append(signal)
        cls._save()

    @classmethod
    def _save(cls):
        """
        Save signals configuration to YML file
        """
        signals_file = cls._get_signals_file()

        signals_yaml = {}
        for signal in cls._signals:
            device_code = signal.get_device_code()
            sub_code = signal.get_sub_code()

            if device_code not in signals_yaml:
                signals_yaml[device_code] = {
                    'name': signal.get_device_name(),
                    'subs': {}
                }

            if sub_code not in signals_yaml[device_code]['subs']:
                signals_yaml[device_code]['subs'][sub_code] = {
                    'name': signal.get_sub_name(),
                }

            signals_yaml[device_code]['subs'][sub_code]['manager'] = signal.get_manager_code()
            signals_yaml[device_code]['subs'][sub_code]['code'] = signal.get_code()
            signals_yaml[device_code]['subs'][sub_code]['dump'] = signal.get_dump()

        yaml.dump(signals_yaml, open(signals_file, 'w'), default_flow_style=False)


class SignalManagerTTY(SignalManager):
    _serial = None
    _tty_port = None

    SELECT_TIMEOUT = 60000

    def _parse_cli_message(self, message):
        """
        Parse an incoming CLI message. Method to be overridden

        :param message: message line
        """
        pass

    def _send(self, message):
        self._serial.write(bytes(message + "\n", 'utf-8'))

    def send(self, message):
        """
        Send a TTY message
        :param message: message to be sent
        """
        self._send(message)

    def start(self):
        SignalManager.start(self)

        self._serial = serial.Serial(self._params['serial'], self._params['baud'])

        # Flush garbage
        while self._serial.inWaiting():
            self._serial.read(self._serial.inWaiting())

        while True:
            ready, _, _ = select.select([self._serial.fileno()], [], [], self.SELECT_TIMEOUT)

            if ready:
                while self._serial.inWaiting() > 0:
                    message = self._serial.readline().strip().decode('utf-8')
                    message = re.sub(r'[\n\r]+', '', message)

                    if len(message) > 0:
                        self._parse_cli_message(message)
