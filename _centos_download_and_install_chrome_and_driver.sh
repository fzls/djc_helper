#!/bin/bash

sudo yum install unzip -y
# 从_ubuntu_download_chrome_and_driver.sh 获取对应版本号，替换到下面即可
wget -N https://dl.google.com/linux/chrome/rpm/stable/x86_64/google-chrome-stable-94.0.4606.81-1.x86_64.rpm
wget -N https://chromedriver.storage.googleapis.com/94.0.4606.61/chromedriver_linux64.zip
unzip -o chromedriver_linux64.zip

sudo yum localinstall google-chrome*.rpm -y
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

google-chrome --version
chromedriver --version
