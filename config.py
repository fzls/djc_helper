import re
import uuid
from typing import List

import toml

from const import *
from data_struct import ConfigInterface
from log import *
from sign import getACSRFTokenForAMS, getDjcSignParams
from util import *

encoding_error_str = "Found invalid character in key name: '#'. Try quoting the key name. (line 1 column 2 char 1)"


class AccountInfoConfig(ConfigInterface):
    def __init__(self):
        # 手动登录需要设置的信息
        self.uin = "o123456789"
        self.skey = "@a1b2c3d4e"

        # 自动登录需要设置的信息
        self.account = "123456789"
        self.password = "使用账号密码自动登录有风险_请审慎决定"


class MobileGameRoleInfoConfig(ConfigInterface):
    def __init__(self):
        # 手游名称: 无/任意手游/剑网3:指尖江湖/和平精英/王者荣耀/QQ飞车手游/天天酷跑/其他任意游戏，可参考djc_biz_list.json获取完整列表
        self.game_name = "任意手游"

    def enabled(self):
        return self.game_name not in ["无", "none"]

    def use_any_binded_mobile_game(self):
        return self.game_name in ["任意手游"]


class ExchangeItemConfig(ConfigInterface):
    def __init__(self):
        self.iGoodsId = "753"
        self.sGoodsName = "装备品级调整箱（5个）"
        self.count = 2


class XinYueOperationConfig(ConfigInterface):
    def __init__(self):
        self.iFlowId = "512411"
        self.package_id = ""  # 仅礼包兑换需要这个参数，如兑换【勇者宝库】的【装备提升礼盒】的package_id为702218
        self.sFlowName = "输出我的任务积分"
        self.count = 1


class WegameGuoqingExchangeItemConfig(ConfigInterface):
    def __init__(self):
        self.iFlowId = "703514"
        self.sGoodsName = "强化器-4分"
        self.count = 1


class ArkLotteryAwardConfig(ConfigInterface):
    def __init__(self):
        self.name = "勇士归来礼包"
        self.ruleid = 25947
        self.count = 1


class ArkLotteryConfig(ConfigInterface):
    def __init__(self):
        # 用于完成幸运勇士的区服ID和角色ID，若服务器ID留空，则使用道聚城绑定的dnf角色信息
        self.lucky_dnf_server_id = ""  # 区服id可查阅reference_data/dnf_server_list.js
        self.lucky_dnf_role_id = ""  # 角色ID，不知道时可以填写区服ID，该数值留空，这样处理到抽卡的时候会用黄色字体打印出来信息
        # 尝试使用卡牌抽奖的次数
        self.lottery_using_cards_count = 0
        # 尝试领取礼包的次数：勇士归来礼包=25947，超低门槛=25948，人人可玩=25966，幸运礼包=25939
        self.take_awards = []  # type: List[ArkLotteryAwardConfig]

        # 是否展示在概览界面
        self.show_status = True
        # 卡牌数目使用特定的颜色
        self.show_color = ""

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        if 'take_awards' in raw_config:
            self.take_awards = []
            for cfg in raw_config["take_awards"]:
                ei = ArkLotteryAwardConfig()
                ei.auto_update_config(cfg)
                self.take_awards.append(ei)

class FunctionSwitchesConfig(ConfigInterface):
    def __init__(self):
        # 是否领取每月黑钻等级礼包
        self.get_heizuan_gift = True
        # 是否领取心悦国庆活动
        self.get_xinyue_guoqing = True
        # 是否领取wegame国庆活动
        self.get_wegame_guoqing = True
        # 是否领取阿拉德集合站活动
        self.get_dnf_922 = True
        # 是否领取2020DNF闪光杯返场赛活动
        self.get_dnf_shanguang = True
        # 是否领取qq视频活动
        self.get_qq_video = True
        # 是否领取9月希洛克攻坚战活动
        self.get_dnf_hillock = True


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
        # 各功能开关
        self.function_switches = FunctionSwitchesConfig()
        # 腾讯系网页登录通用账号凭据与token
        self.account_info = AccountInfoConfig()
        # 完成《礼包达人》和《有理想》任务所需的手游的名称信息
        self.mobile_game_role_info = MobileGameRoleInfoConfig()
        # 兑换道具信息
        self.exchange_items = []  # type: List[ExchangeItemConfig]
        # 心悦相关操作信息
        self.xinyue_operations = []  # type: List[XinYueOperationConfig]
        # 抽卡相关配置
        self.ark_lottery = ArkLotteryConfig()
        # wegame国庆活动兑换道具，具体道具的iFlowId和描述可参考reference_data/wegame国庆活动.json
        self.wegame_guoqing_exchange_items = []  # type: List[WegameGuoqingExchangeItemConfig]

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        if 'exchange_items' in raw_config:
            self.exchange_items = []
            for cfg in raw_config["exchange_items"]:
                ei = ExchangeItemConfig()
                ei.auto_update_config(cfg)
                self.exchange_items.append(ei)

        if 'xinyue_operations' in raw_config:
            self.xinyue_operations = []
            for cfg in raw_config["xinyue_operations"]:
                ei = XinYueOperationConfig()
                ei.auto_update_config(cfg)
                self.xinyue_operations.append(ei)

        if 'wegame_guoqing_exchange_items' in raw_config:
            self.wegame_guoqing_exchange_items = []
            for cfg in raw_config["wegame_guoqing_exchange_items"]:
                ei = WegameGuoqingExchangeItemConfig()
                ei.auto_update_config(cfg)
                self.wegame_guoqing_exchange_items.append(ei)

        self.on_config_update(raw_config)

    def enable_and_normal_run(self):
        return self.enable and self.run_mode == "normal"

    def on_config_update(self, raw_config: dict):
        self.sDeviceID = self.getSDeviceID()
        self.aes_key = "84e6c6dc0f9p4a56"
        self.rsa_public_key_file = "public_key.der"

        self.updateUinSkey(self.account_info.uin, self.account_info.skey)

    def updateUinSkey(self, uin, skey):
        self.account_info.uin = uin
        self.account_info.skey = skey

        self.g_tk = str(getACSRFTokenForAMS(self.account_info.skey))
        self.sDjcSign = getDjcSignParams(self.aes_key, self.rsa_public_key_file, uin2qq(self.account_info.uin), self.sDeviceID, appVersion)

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


class LoginConfig(ConfigInterface):
    def __init__(self):
        # 重试次数
        self.max_retry_count = 3
        # 重试间隔时间（秒）
        self.retry_wait_time = 1
        # 打开网页后等待时长
        self.open_url_wait_time = 3
        # 加载页面的超时时间，以登录按钮出现为完成标志
        self.load_page_timeout = 60
        # 点击登录按钮后的超时时间，加载登录iframe，以其显示出来为完成标志
        self.load_login_iframe_timeout = 5
        # 登录的超时时间，从登录界面显示为开始，以用户完成登录为结束标志
        self.login_timeout = 600
        # 等待登录完成的超时时间，以活动结束的按钮弹出来标志
        self.login_finished_timeout = 60


class RetryConfig(ConfigInterface):
    def __init__(self):
        # 每次兑换请求之间的间隔时间（秒），避免请求过快而报错，目前测试1s正好不会报错~
        self.request_wait_time = 1
        # 当提示【"msg": "系统繁忙，请稍候再试。", "ret": "-9905"】时的最大重试次数
        self.max_retry_count = 3
        # 上述情况下的重试间隔时间（秒）
        self.retry_wait_time = 1


class XinYueConfig(ConfigInterface):
    def __init__(self):
        # 在每日几点后才尝试提交心悦的成就点任务，避免在没有上游戏时执行心悦成就点任务，导致高成就点的任务没法完成，只能完成低成就点的
        self.submit_task_after = 0


class FixedTeamConfig(ConfigInterface):
    reg_qq = r'\d+'

    def __init__(self):
        # 是否启用该固定队
        self.enable = False
        # 固定队伍id，仅用于本地区分用
        self.id = "1"
        # 固定队成员，必须是三个，则必须都配置在本地的账号列表中了，否则将报错，不生效
        self.members = ["小队第一个账号的QQ号", "小队第二个账号的QQ号", "小队第三个账号的QQ号"]

    def check(self) -> bool:
        if len(self.members) != 3:
            return False

        for qq in self.members:
            if re.fullmatch(self.reg_qq, qq) is None:
                return False

        return True


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
        # http(s)请求超时时间(秒)
        self.http_timeout = 10
        # 是否展示chrome的debug日志，如DevTools listening，Bluetooth等
        self._debug_show_chrome_logs = False
        # 自动登录模式是否不显示浏览器界面
        self.run_in_headless_mode = False
        # 日志等级, 级别从低到高依次为 "debug", "info", "warning", "error", "critical"
        self.log_level = "info"
        # 是否检查更新
        self.check_update_on_start = True
        self.readme_page = "https://github.com/fzls/djc_helper/blob/master/README.MD"
        self.changelog_page = "https://github.com/fzls/djc_helper/blob/master/CHANGELOG.MD"
        # 正式模式运行成功时是否弹出打赏图片
        self.show_support_pic = True
        # 登录各个阶段的最大等待时间，单位秒（仅二维码登录和自动登录需要配置，数值越大容错性越好）
        self.login = LoginConfig()
        # 各种操作的通用重试配置
        self.retry = RetryConfig()
        # 心悦相关配置
        self.xinyue = XinYueConfig()
        # 固定队相关配置。用于本地三个号来组成一个固定队伍，完成心悦任务。
        self.fixed_teams = []  # type: List[FixedTeamConfig]

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        if 'fixed_teams' in raw_config:
            self.fixed_teams = []
            for cfg in raw_config["fixed_teams"]:
                ei = FixedTeamConfig()
                ei.auto_update_config(cfg)
                self.fixed_teams.append(ei)

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
