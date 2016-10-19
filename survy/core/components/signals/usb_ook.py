import time

from survy.core.signal import SignalManagerTTY, Signal


class SignalManagerUsbOOK(SignalManagerTTY):
    _last_codes = {}

    def _parse_cli_message(self, message):
        try:
            signal_code, signal_dump = message.split(':')
        except ValueError:
            return False

        now = time.time()

        # Clear old codes
        codes = self._last_codes
        for k in list(codes):
            if now - self._last_codes[k] > int(self._params['anti-jamming-interval']):
                del self._last_codes[k]

        if (signal_code not in self._last_codes) or self.is_learning():
            signal = Signal(manager=self, code=signal_code, dump=signal_dump)
            self._on_signal(signal)

        self._last_codes[signal_code] = now
        return True

    def _fire(self, signal: Signal):
        self.send(signal.get_dump())
        return True
