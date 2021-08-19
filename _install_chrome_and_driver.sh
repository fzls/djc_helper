#!/bin/bash

sudo dpkg -i google-chrome*.deb
sudo apt-get install -f
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

google-chrome --version
chromedriver --version
