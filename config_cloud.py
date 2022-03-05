from os import path
from typing import List

import toml

from const import downloads_dir
from data_struct import ConfigInterface
from download import download_github_raw_content
from log import logger
from util import async_call, try_except


# 远程配置，方便动态调整部分配置
class ConfigCloud(ConfigInterface):
    def __init__(self):
        # 是否已经从配置文件中加载
        self.loaded = False

        # 新增的服务器IP列表
        self.server_ip_list: List[str] = []


# 配置保存路径
save_dir = downloads_dir
# 配置文件名
cloud_config_filename = "config.cloud.toml"

g_config_cloud = ConfigCloud()


# 获取远程配置，首次调用时会触发加载
def config_cloud() -> ConfigCloud:
    if not g_config_cloud.loaded:
        logger.info("配置尚未加载，需要初始化")
        load_config_cloud()

    return g_config_cloud


# 读取远程config
def load_config_cloud():
    global g_config_cloud

    # 尝试读取远程配置
    try:
        raw_config = toml.load(path.join(save_dir, cloud_config_filename))
        g_config_cloud.auto_update_config(raw_config)
    except Exception as e:
        logger.debug("读取远程配置失败", exc_info=e)

    # 尝试异步从github下载最新的远程配置，供下次读取使用（主要是为了避免影响其他流程）
    async_update_config_cloud()

    # 标记为已经初始化完毕
    g_config_cloud.loaded = True


@try_except()
def async_update_config_cloud():
    async_call(download_github_raw_content, cloud_config_filename, save_dir)


if __name__ == '__main__':
    load_config_cloud()
    logger.info(f"{g_config_cloud}")

    from util import pause

    pause()
