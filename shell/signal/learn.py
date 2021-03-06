#!/usr/bin/env python3

import argparse
import sys
sys.path.insert(0, '../../')

from survy.core.signal import SignalManager
from survy.core.client import Client

parser = argparse.ArgumentParser()
parser.add_argument("device", help="Task to run")
parser.add_argument("sub", help="Json Payload")

args = parser.parse_args()

client = Client()
res = client.send(
    message_type=SignalManager.INTERCOM_MESSAGE_DO_LEARN,
    message_payload={
        'device': args.device,
        'sub': args.sub
    },
    expect=[
        SignalManager.INTERCOM_MESSAGE_EVENT_LEARN_END,
        SignalManager.INTERCOM_MESSAGE_EVENT_LEARN_FAIL
    ]
)

if (res is None) or (res['message'] == SignalManager.INTERCOM_MESSAGE_EVENT_LEARN_FAIL):
    print("Learn failed")
    sys.exit(-1)

print("Learn OK")
sys.exit(0)
