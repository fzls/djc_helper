# syntax=docker/dockerfile:1

FROM ubuntu:20.04

# 安装python3.8
RUN apt-get update && apt-get install -y python3 python3-pip

# 复制源码
WORKDIR /djc_helper
COPY . .

## 下载chrome和driver
RUN apt-get update && apt-get install -y sudo
RUN bash _ubuntu_download_and_install_chrome_and_driver.sh

# 安装依赖
RUN python3 -m pip install -i https://pypi.doubanio.com/simple --upgrade pip setuptools wheel
RUN pip3 install -i https://pypi.doubanio.com/simple -r requirements_linux.txt

# 可通过该环境变量传入配置信息
## 设置配置文件信息到环境变量
#read -r -d '' DJC_HELPER_CONFIG_TOML << EOF
#
#这里填入config.toml的配置内容
#
#EOF
#
## 在运行docker时传入该环境变量
#docker run --env DJC_HELPER_CONFIG_TOML="$DJC_HELPER_CONFIG_TOML" djc_helper
ARG DJC_HELPER_CONFIG_TOML
ENV DJC_HELPER_CONFIG_TOML=""

CMD [ "python3", "main.py"]
