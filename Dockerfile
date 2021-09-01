# syntax=docker/dockerfile:1

FROM ubuntu:20.04

# 设置时区
ENV TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

RUN set -x \
    && apt update \
    && apt install -y tzdata \
    && ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

# 安装python3.8
RUN set -x \
    && apt-get update \
    && apt-get install -y python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /djc_helper

## 下载chrome和driver
COPY _ubuntu_download_and_install_chrome_and_driver.sh _ubuntu_download_chrome_and_driver.sh _ubuntu_install_chrome_and_driver.sh ./
RUN set -x \
    && apt-get update \
    && apt-get install -y sudo \
    && rm -rf /var/lib/apt/lists/*
RUN bash _ubuntu_download_and_install_chrome_and_driver.sh

# 安装依赖
ARG pip_index_url=https://pypi.org/simple
#ARG pip_index_url=https://pypi.doubanio.com/simple
COPY requirements_docker.txt requirements_z_base.txt ./
RUN set -x \
    && PATH="$PATH:$HOME/.local/bin" \
    && python3 -m pip install -i $pip_index_url --no-cache-dir --user --upgrade pip setuptools wheel \
    && pip3 install -i $pip_index_url --no-cache-dir -r requirements_docker.txt

# 可通过以下两种方式传入配置
# 1. 环境变量（正式环境推荐该方式）
#   支持通过下列环境变量来传递配置信息。若同时设置，则按下面顺序取第一个非空的环境变量作为配置
# 示例：docker run --env DJC_HELPER_CONFIG_TOML="$DJC_HELPER_CONFIG_TOML" djc_helper
# toml配置
ENV DJC_HELPER_CONFIG_TOML=""
# toml配置编码为base64
ENV DJC_HELPER_CONFIG_BASE64=""
# toml配置先通过lzma压缩，然后编码为base64
ENV DJC_HELPER_CONFIG_LZMA_COMPRESSED_BASE64=""
# toml配置解析后再序列化为单行的JSON配置
ENV DJC_HELPER_CONFIG_SINGLE_LINE_JSON=""

# 2. 映射本地配置文件到容器中（调试时可以使用这个）
# docker run -v D:\_codes\Python\djc_helper_public\config.toml:/djc_helper/config.toml fzls/djc_helper:master

# 复制源码（最常改动的内容放到最后，确保修改代码后仅这部分内容会变动，其他层不变）
COPY . .

# 使用非root账户来调用小助手，确保在腾讯云环境下也能正常调用chrome，否则会报 selenium.common.exceptions.WebDriverException: Message: unknown error: DevToolsActivePort file doesn't exist
# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN groupadd -r -g 999 fzls && useradd -r -g fzls -u 999 fzls

RUN set -eux; \
	apt-get update; \
	apt-get install -y gosu; \
	rm -rf /var/lib/apt/lists/*; \
    # verify that the binary works
	gosu nobody true

RUN chown fzls:fzls /djc_helper /usr/local/bin /usr/bin
CMD ["gosu", "fzls", "python3", "-u", "main.py"]
