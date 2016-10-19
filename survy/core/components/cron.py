import time
import datetime
from survy.core.component import Component
from time import strftime, localtime


class CronManager(Component):
    INTERCOM_MESSAGE_EVENT_CRON = 'cron-event'

    def get_variables(self):
        return {
            'time_ts': strftime("%Y%m%d%H%M%S", localtime()),
            'time_day': strftime("%Y%m%d", localtime()),
            'time_hour': strftime("%H", localtime()),
            'time_minute': strftime("%M", localtime()),
            'time_second': strftime("%S", localtime()),
            'time_dow': strftime("%w", localtime()),
            'time_time': strftime("%H%M%S", localtime())
        }

    def start(self):
        Component.start(self)

        while True:
            now = datetime.datetime.now()

            if now.second == 0:
                dow = str(now.isoweekday())

                self.send_intercom_message(self.INTERCOM_MESSAGE_EVENT_CRON, {
                    'dow': dow,
                    'hour': now.hour,
                    'minute': now.minute,
                })

            time.sleep(1)
