#!/usr/bin/env python3

import argparse
import json

from survy.core.client import Client


parser = argparse.ArgumentParser()
parser.add_argument("task", help="Task to run")
parser.add_argument("--payload", help="Json Payload")

args = parser.parse_args()

if args.task is None:
    parser.print_help()
else:
    client = Client()

    if args.payload is None:
        res = client.send(args.task)

    else:
        res = client.send(args.task, json.loads(args.payload))

    print(res)
