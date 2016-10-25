import copy
import time

from survy.core.signal import SignalManagerTTY, Signal


class SignalManagerUsbOOK(SignalManagerTTY):
    _last_confirmed_codes = {}  # Avoids to trigger the same signal twice in a short period
    _last_received_codes = {}  # Confirm signal only if received twice

    def _parse_cli_message(self, message):
        try:
            signal_code, signal_dump = message.split(':')
        except ValueError:
            return False

        now = time.time()

        # Clear old codes
        codes = copy.deepcopy(self._last_confirmed_codes)
        for k in list(codes):
            if now - self._last_confirmed_codes[k] > float(self._params['debounce-interval']):
                del self._last_confirmed_codes[k]

        codes = copy.deepcopy(self._last_received_codes)
        for k in list(codes):
            if now - self._last_received_codes[k] > float(self._params['signals-confirmation-interval']):
                del self._last_received_codes[k]

        # Check if we received the same signal in the "signals-confirmation-interval" interval
        if signal_code in self._last_received_codes:
            # Check if we already triggered this confirmed message
            if (signal_code not in self._last_confirmed_codes) or self.is_learning():
                signal = Signal(manager=self, code=signal_code, dump=signal_dump)
                self._on_signal(signal)

            # Mark signal as confirmed
            self._last_confirmed_codes[signal_code] = now

        self._last_received_codes[signal_code] = now
        return True

    def _fire(self, signal: Signal):
        self.send(signal.get_dump())
        return True
