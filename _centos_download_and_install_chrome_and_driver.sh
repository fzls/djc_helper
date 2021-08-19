#!/bin/bash

sudo yum install unzip -y
92.0.4515.159-1
wget -N https://dl.google.com/linux/chrome/rpm/stable/x86_64/google-chrome-stable-92.0.4515.159-1.x86_64.rpm
wget -N https://chromedriver.storage.googleapis.com/92.0.4515.107/chromedriver_linux64.zip
unzip -o chromedriver_linux64.zip

sudo yum localinstall google-chrome*.rpm -y
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

google-chrome --version
chromedriver --version
