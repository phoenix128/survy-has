#!/usr/bin/env python3

import sys
sys.path.insert(0, '../')

from survy.core.signal import SignalManager
from survy.core.client import Client
from survy.core.intercom import Message

client = Client()
print(client.send(Message.INTERCOM_RECIPIENT_BROADCAST+'/'+SignalManager.INTERCOM_MESSAGE_DO_LEARN, {
    'device': sys.argv[1],
    'sub': sys.argv[2]
}))
