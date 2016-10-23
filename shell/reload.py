#!/usr/bin/env python3

import sys
sys.path.insert(0, '../')

from survy.core.client import Client
from survy.core.component import Component

client = Client()
client.send(
    message_type=Component.INTERCOM_MESSAGE_DO_RELOAD,
    message_payload={}
)
