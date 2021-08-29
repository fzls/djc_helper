#!/bin/bash

sudo dpkg -i google-chrome*.deb
sudo apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -f -y \
  && rm -rf /var/lib/apt/lists/*

sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

google-chrome --version
chromedriver --version

rm -rf ./google-chrome*.deb
rm -rf ./chromedriver_linux64.zip
