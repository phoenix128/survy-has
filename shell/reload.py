#!/usr/bin/env python3

import sys
sys.path.insert(0, '../')

from survy.core.client import Client
from survy.core.component import Component
from survy.core.intercom import Message

client = Client()
print(client.send(Message.INTERCOM_RECIPIENT_BROADCAST+'/'+Component.INTERCOM_MESSAGE_DO_RELOAD, {}))
