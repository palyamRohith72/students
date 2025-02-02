#!/bin/bash
apt-get update
apt-get install -y cmake build-essential libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev libswscale-dev libboost-all-dev
pip install -r requirements.txt
