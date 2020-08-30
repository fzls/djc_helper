import os
import uuid
from urllib.parse import quote

import toml

from const import *
from data_struct import ConfigInterface
from log import *
from sign import getACSRFTokenForAMS, getDjcSignParams

encoding_error_str = "Found invalid character in key name: '#'. Try quoting the key name. (line 1 column 2 char 1)"

class AccountInfoConfig(ConfigInterface):
    def __init__(self):
        self.uin = "o123456789"
        self.skey = "@a1b2c3d4e"
class ExchangeRoleInfoConfig(ConfigInterface):
    def __init__(self):
        self.iZone = "11"  # 浙江一区，其他区服id可查阅reference_data/dnf_server_list.js
        self.lRoleId = "DNF角色ID"
        self.rolename = quote("DNF角色名")

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        self.rolename = quote(self.rolename)

class MobileGameRoleInfoConfig(ConfigInterface):
    def __init__(self):
        self.area = 2  # QQ
        self.platid = 1  # 安卓
        self.partition = 20001  # 手Q1区，其他区服的id可查阅reference_data/jx3_server_list.js
        self.roleid = "指尖江湖角色ID"
        self.rolename = "指尖江湖玩家名"

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        self.rolename = quote(self.rolename)


class Config(ConfigInterface):
    log_level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(self):
        # 日志等级, 级别从低到高依次为 "debug", "info", "warning", "error", "critical"
        self.log_level = "info"
        # 是否检查更新
        self.check_update_on_start = True
        # 腾讯系网页登录通用账号凭据与token
        self.account_info = AccountInfoConfig()
        # 兑换dnf道具所需的dnf区服和角色信息
        self.exchange_role_info = ExchangeRoleInfoConfig()
        # 完成《礼包达人》任务所需的剑网3:指尖江湖手游的区服和角色信息
        self.mobile_game_role_info = MobileGameRoleInfoConfig()


    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)
        self.on_config_update(raw_config)

    def on_config_update(self, raw_config: dict):
        consoleHandler.setLevel(self.log_level_map[self.log_level])

        self.sDeviceID = self.getSDeviceID()
        self.aes_key = "84e6c6dc0f9p4a56"
        self.rsa_public_key_file = "public_key.der"

        self.g_tk = str(getACSRFTokenForAMS(self.account_info.skey))
        self.sDjcSign = getDjcSignParams(self.aes_key, self.rsa_public_key_file, self.account_info.uin[1:], self.sDeviceID, appVersion)

    def getSDeviceID(self):
        sDeviceIdFileName = ".sDeviceID.txt"

        if os.path.isfile(sDeviceIdFileName):
            with open(sDeviceIdFileName, "r", encoding="utf-8") as file:
                sDeviceID = file.read()
                if len(sDeviceID) == 36:
                    # print("use cached sDeviceID", sDeviceID)
                    return sDeviceID

        sDeviceID = str(uuid.uuid1())
        # print("create new sDeviceID", sDeviceID, len(sDeviceID))

        with open(sDeviceIdFileName, "w", encoding="utf-8") as file:
            file.write(sDeviceID)

        return sDeviceID


g_config = Config()


# 读取程序config
def load_config(config_path="config.toml"):
    global g_config
    try:
        raw_config = toml.load(config_path)
        g_config.auto_update_config(raw_config)
    except UnicodeDecodeError as error:
        logger.error("{}的编码格式有问题，应为utf-8，如果使用系统自带记事本的话，请下载vscode或notepad++等文本编辑器\n错误信息：{}\n".format(config_path, error))
        sys.exit(0)
    except Exception as error:
        if encoding_error_str in str(error):
            logger.error("{}的编码格式有问题，应为utf-8，如果使用系统自带记事本的话，请下载vscode或notepad++等文本编辑器\n错误信息：{}\n".format(config_path, error))
            sys.exit(0)

        logger.error("读取{}文件出错，是否直接在压缩包中打开了？\n具体出错为：{}".format(config_path, error))
        sys.exit(-1)


def config():
    return g_config


if __name__ == '__main__':
    load_config("config.toml")
    logger.info(config())

