import uuid
from typing import List
from urllib.parse import quote

import toml

from const import *
from data_struct import ConfigInterface
from log import *
from sign import getACSRFTokenForAMS, getDjcSignParams

encoding_error_str = "Found invalid character in key name: '#'. Try quoting the key name. (line 1 column 2 char 1)"


class AccountInfoConfig(ConfigInterface):
    def __init__(self):
        # 手动登录需要设置的信息
        self.uin = "o123456789"
        self.skey = "@a1b2c3d4e"

        # 自动登录需要设置的信息
        self.account = "123456789"
        self.password = "使用账号密码自动登录有风险_请审慎决定"


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
        # 手游名称，目前支持下面几种
        # none： 无，则不启用完成礼包达人任务
        # jx3：  剑网3：指尖江湖
        self.game_name = "jx3"
        self.area = 2  # QQ，其他渠道的id可查阅reference_data/jx3_server_list.js的 STD_CHANNEL_DATA中对应渠道的v
        self.platid = 1  # 安卓，其他系统的id可查阅reference_data/jx3_server_list.js的 STD_SYSTEM_DATA中对应系统的v
        self.partition = 20001  # 手Q1区，其他区服的id可查阅reference_data/jx3_server_list.js的 STD_DATA中对应服务器的v
        self.roleid = "指尖江湖角色ID"
        self.rolename = "指尖江湖玩家名"

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        self.rolename = quote(self.rolename)

    def enabled(self):
        return self.game_name != "none"


class ExchangeItemConfig(ConfigInterface):
    def __init__(self):
        self.iGoodsId = "753"
        self.sGoodsName = "装备品级调整箱（5个）"
        self.count = 2


class AccountConfig(ConfigInterface):
    def __init__(self):
        # 是否启用该账号
        self.enable = True
        # 账号名称，仅用于区分不同账号
        self.name = "默认账号"
        # 运行模式
        # pre_run:      指引获取uin、skey，以及如何获取角色信息
        # normal:       走正常流程，执行签到、完成任务、领奖、兑换等流程
        self.run_mode = "pre_run"
        # 登录模式
        # by_hand：      手动登录，在skey无效的情况下会弹出活动界面，自行登录后将cookie中uin和skey提取到下面的配置处
        # qr_login：     二维码登录，每次运行时若本地缓存的.skey文件中存储的skey过期了，则弹出登录页面，扫描二维码后将自动更新skey，进行后续操作
        # auto_login：   自动登录，每次运行若本地缓存的.skey文件中存储的skey过期了，根据填写的账密信息，自动登录来获取uin和skey，无需手动操作
        self.login_mode = "by_hand"
        # 腾讯系网页登录通用账号凭据与token
        self.account_info = AccountInfoConfig()
        # 兑换dnf道具所需的dnf区服和角色信息
        self.exchange_role_info = ExchangeRoleInfoConfig()
        # 完成《礼包达人》任务所需的剑网3:指尖江湖手游的区服和角色信息
        self.mobile_game_role_info = MobileGameRoleInfoConfig()
        # 兑换道具信息
        self.exchange_items = []  # type: List[ExchangeItemConfig]

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        if 'exchange_items' in raw_config:
            self.exchange_items = []
            for cfg in raw_config["exchange_items"]:
                ei = ExchangeItemConfig()
                ei.auto_update_config(cfg)
                self.exchange_items.append(ei)

        self.on_config_update(raw_config)

    def on_config_update(self, raw_config: dict):
        self.sDeviceID = self.getSDeviceID()
        self.aes_key = "84e6c6dc0f9p4a56"
        self.rsa_public_key_file = "public_key.der"

        self.updateUinSkey(self.account_info.uin, self.account_info.skey)

    def updateUinSkey(self, uin, skey):
        self.account_info.uin = uin
        self.account_info.skey = skey

        self.g_tk = str(getACSRFTokenForAMS(self.account_info.skey))
        self.sDjcSign = getDjcSignParams(self.aes_key, self.rsa_public_key_file, self.account_info.uin[1:], self.sDeviceID, appVersion)

    def getSDeviceID(self):
        sDeviceIdFileName = os.path.join(cached_dir, ".sDeviceID.{}.txt".format(self.name))

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


class LoginTimeoutsConfig(ConfigInterface):
    def __init__(self):
        # 打开网页后等待时长
        self.open_url_wait_time = 3
        # 加载页面，以登录按钮出现为完成标志
        self.load_page = 60
        # 点击登录按钮后，加载登录iframe，以其显示出来为完成标志
        self.load_login_iframe = 5
        # 登录，从登录界面显示为开始，以用户完成登录为结束标志
        self.login = 600
        # 等待登录完成，以活动结束的按钮弹出来标志
        self.login_finished = 60


class ExchangeItemsCommonConfig(ConfigInterface):
    def __init__(self):
        # 每次兑换请求之间的间隔时间（秒），避免请求过快而报错，目前测试1s正好不会报错~
        self.request_wait_time = 1
        # 当提示【"msg": "系统繁忙，请稍候再试。", "ret": "-9905"】时的最大重试次数
        self.max_retry_count = 3
        # 上述情况下的重试间隔时间（秒）
        self.retry_wait_time = 1


class CommonConfig(ConfigInterface):
    log_level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(self):
        # 测试用开关，将仅运行首个账号配置
        self._debug_run_first_only = False
        # 是否强制使用打包附带的便携版chrome
        self.force_use_portable_chrome = False
        # 是否展示chrome的debug日志，如DevTools listening，Bluetooth等
        self._debug_show_chrome_logs = False
        # 日志等级, 级别从低到高依次为 "debug", "info", "warning", "error", "critical"
        self.log_level = "info"
        # 是否检查更新
        self.check_update_on_start = True
        self.readme_page = "https://github.com/fzls/djc_helper/blob/master/README.MD"
        self.changelog_page = "https://github.com/fzls/djc_helper/blob/master/CHANGELOG.MD"
        # 登录各个阶段的最大等待时间，单位秒（仅二维码登录和自动登录需要配置，数值越大容错性越好）
        self.login_timeouts = LoginTimeoutsConfig()
        # 兑换道具时的一些行为配置
        self.exchange_items = ExchangeItemsCommonConfig()

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        consoleHandler.setLevel(self.log_level_map[self.log_level])


class Config(ConfigInterface):
    def __init__(self):
        # 所有账号共用的配置
        self.common = CommonConfig()
        # 兑换道具信息
        self.account_configs = []  # type: List[AccountConfig]

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        if 'account_configs' in raw_config:
            self.account_configs = []
            for cfg in raw_config["account_configs"]:
                ei = AccountConfig()
                ei.auto_update_config(cfg)
                self.account_configs.append(ei)

        if not self.check():
            logger.error("配置有误，请根据提示信息修改")
            exit(-1)

    def check(self) -> bool:
        name2index = {}
        for _idx, account in enumerate(self.account_configs):
            idx = _idx + 1

            # 检查是否填写名称
            if len(account.name) == 0:
                logger.error("第{}个账号未设置名称，请确保已填写对应账号配置的name".format(idx))
                return False

            # 检查名称是否重复
            if account.name in name2index:
                logger.error("第{}个账号的名称 {} 与第{}个账号的名称重复，请调整为不同的名字".format(idx, account.name, name2index[account.name]))
                return False
            name2index[account.name] = idx

        return True


g_config = Config()


# 读取程序config
def load_config(config_path="config.toml", local_config_path="config.toml.local"):
    global g_config
    # 首先尝试读取config.toml（受版本管理系统控制）
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

    # 然后尝试读取本地文件（不受版本管理系统控制）
    try:
        raw_config = toml.load(local_config_path)
        g_config.auto_update_config(raw_config)
    except Exception as e:
        pass


def config():
    return g_config


if __name__ == '__main__':
    load_config("config.toml", "config.toml.local")
    logger.info(config())
