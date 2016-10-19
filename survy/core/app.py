import copy
import importlib
import os

import yaml
import threading

from survy.core.component import ComponentCollection
from survy.core.log import Log


class App:
    config = None
    components = None
    allowed_paths = []
    cli_tasks = None
    base_path = None
    variables = {}

    @classmethod
    def load_variables(cls):
        variable_file = cls.get_settings_path() + '/variables.yml'

        cls.variables = {}
        try:
            cls.variables = yaml.load(open(variable_file, 'r'))
            Log.info('Variables loaded from ' + variable_file)
        except:
            pass

        if cls.variables is None:
            cls.variables = {}

    @classmethod
    def load_components(cls):
        Log.info("Loading components")
        cls.components = ComponentCollection()

        for k in cls.config['components'].keys():
            component_info = cls.config['components'][k]

            module_name, class_name = component_info['class'].split('/', 2)

            module = importlib.import_module(module_name)
            component_class = getattr(module, class_name)

            component_name = component_info['name']
            if 'params' in component_info:
                component_params = component_info['params']
            else:
                component_params = {}

            component = component_class(k, component_name, component_params)
            component_class.set_instance_code(k)

            cls.components.add(k, component, component.COMPONENT_TYPE)

        cls.allowed_paths = []
        if 'allowed_paths' in cls.config:
            cls.allowed_paths = cls.config['allowed_paths']

    @classmethod
    def can_access_file(cls, filename):
        """
        Return false if survy cannot access given file
        :param filename:
        :return:
        """

        for p in cls.allowed_paths:
            try:
                if os.path.dirname(filename).index(p) == 0:
                    return True
            except ValueError:
                pass

        return False

    @classmethod
    def get_base_path(cls):
        return cls.base_path

    @classmethod
    def get_settings_path(cls):
        return cls.get_base_path() + '/settings'

    @classmethod
    def get_sys_path(cls):
        return cls.get_base_path() + '/sys'

    @classmethod
    def start_components(cls):
        Log.info("Starting components")
        components_list = cls.components.get_list()
        for code in components_list:
            threading.Thread(target=cls.components.get(code).start).start()

    @classmethod
    def get_variables(cls):
        out = cls.variables

        components_list = cls.components.get_list()
        for code in components_list:
            out.update(copy.deepcopy(App.components.get(code).get_variables()))

        return out

    @classmethod
    def setup(cls, base_path, config_file):
        cls.config = yaml.load(open(config_file, 'r'))
        cls.base_path = base_path

    @classmethod
    def reload(cls):
        cls.load_variables()
        return True

    @classmethod
    def start(cls):
        cls.load_variables()
        cls.load_components()
        cls.start_components()

        Log.info("Engine started")

