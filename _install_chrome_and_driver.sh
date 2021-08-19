#!/bin/bash
apt-get install unzip

wget http://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_92.0.4515.159-1_amd64.deb
wget https://chromedriver.storage.googleapis.com/92.0.4515.107/chromedriver_linux64.zip
unzip chromedriver_linux64.zip

sudo dpkg -i google-chrome*.deb
sudo apt-get install -f
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

google-chrome --version
chromedriver --version
