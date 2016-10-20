#!/usr/bin/env python3

import argparse
import sys

sys.path.insert(0, '../../')

from survy.core.intercom import Reply
from survy.core.signal import SignalManager
from survy.core.client import Client

parser = argparse.ArgumentParser()
parser.add_argument("device", help="Task to run")
parser.add_argument("sub", help="Json Payload")

args = parser.parse_args()

client = Client()
res = client.send(
    message_type=SignalManager.INTERCOM_MESSAGE_DO_FIRE,
    message_payload={
        'device': args.device,
        'sub': args.sub
    }
)

if (res is None) or (res['status'] == Reply.INTERCOM_STATUS_FAILURE):
    print("Unknown signal")
    sys.exit(-1)

print("Signal sent")
sys.exit(0)
