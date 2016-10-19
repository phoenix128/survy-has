#!/usr/bin/env bash

apt-get update
apt-get upgrade

apt-get install python3 python3-yaml screen python-opencv festival festvox-italp16k festvox-itapc16k
pip3 install pyserial
pip3 install imutils
pip3 install PySocks
pip3 install python-telegram-bot
pip3 install python-telegram-bot --upgrade

useradd survy

usermod -a -G dialout survy



