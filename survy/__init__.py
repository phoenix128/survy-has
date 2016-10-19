#!/usr/bin/env python

import os

from survy.core.app import App

CONFIG_FILE = 'config.yml'
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

App.setup(BASE_PATH, CONFIG_FILE)
