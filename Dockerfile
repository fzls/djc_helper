# syntax=docker/dockerfile:1

FROM ubuntu:20.04

# 安装python3.8
RUN apt-get update \
    && apt-get install -y python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /djc_helper

## 下载chrome和driver
COPY _ubuntu_download_and_install_chrome_and_driver.sh _ubuntu_download_chrome_and_driver.sh _ubuntu_install_chrome_and_driver.sh ./
RUN apt-get update \
    && apt-get install -y sudo \
    && rm -rf /var/lib/apt/lists/*
RUN bash _ubuntu_download_and_install_chrome_and_driver.sh

# 安装依赖
COPY requirements_docker.txt requirements_z_base.txt ./
RUN python3 -m pip install --no-cache-dir -i https://pypi.doubanio.com/simple --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir -i https://pypi.doubanio.com/simple -r requirements_docker.txt

# 可通过以下两种方式传入配置
# 1. 环境变量（正式环境推荐该方式）
## 若对应环境支持配置多行的环境变量，可直接将toml文件的内容设置到DJC_HELPER_CONFIG_TOML
## 否则，可以选择将toml内容转化为base64或者单行的json后再传入后面两个变量中对应的那个
## 若同时设置，则按下面顺序取第一个非空的环境变量作为配置
#docker run --env DJC_HELPER_CONFIG_TOML="$DJC_HELPER_CONFIG_TOML" djc_helper
ENV DJC_HELPER_CONFIG_TOML=""
ENV DJC_HELPER_CONFIG_BASE64=""
ENV DJC_HELPER_CONFIG_JSON=""

# 2. 映射本地配置文件到容器中（调试时可以使用这个）
# docker run -v D:\_codes\Python\djc_helper_public\config.toml:/djc_helper/config.toml fzls/djc_helper:master

# 复制源码（最常改动的内容放到最后，确保修改代码后仅这部分内容会变动，其他层不变）
COPY . .

CMD [ "python3", "-u", "main.py"]
