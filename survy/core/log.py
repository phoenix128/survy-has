import inspect
import logging
import sys

from logging.handlers import RotatingFileHandler




class Log:
    FACILITY = 'survy-has'
    FORMAT = '%(asctime)-15s [%(levelname)-6s] %(class)-20s: %(message)s'

    init_done = False

    @classmethod
    def _init(cls):
        if not cls.init_done:
            cls.init_done = True

            logging.basicConfig(level=logging.INFO)

            formatter = logging.Formatter(cls.FORMAT)

            file_handler = RotatingFileHandler(
                filename='/var/log/survy.log',
                mode='a',
                backupCount=10,
                maxBytes=1000000)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            cls._get_logger().addHandler(file_handler)

            # stdout_handler = logging.StreamHandler(stream=sys.stdout)
            # stdout_handler.setLevel(logging.DEBUG)
            # stdout_handler.setFormatter(formatter)
            # cls._get_logger().addHandler(stdout_handler)

    @classmethod
    def _get_logger(cls):
        return logging.getLogger(cls.FACILITY)

    @classmethod
    def _get_caller(cls):
        l = inspect.stack()[2][0].f_locals

        if 'self' in l.keys():
            return inspect.stack()[2][0].f_locals["self"].__class__.__name__

        if 'cls' in inspect.stack()[2][0].f_locals:
            return inspect.stack()[2][0].f_locals["cls"].__name__

        return inspect.stack()[2][0].f_locals['__file__']

    @classmethod
    def debug(cls, msg):
        cls._init()

        cls._get_logger().debug(msg, extra={'class': cls._get_caller()})

    @classmethod
    def info(cls, msg):
        cls._init()
        cls._get_logger().info(msg, extra={'class': cls._get_caller()})

    @classmethod
    def warn(cls, msg):
        cls._init()
        cls._get_logger().warn(msg, extra={'class': cls._get_caller()})

    @classmethod
    def error(cls, msg):
        cls._init()
        cls._get_logger().error(msg, extra={'class': cls._get_caller()})
