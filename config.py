import re
from multiprocessing import cpu_count

from const import *
from data_struct import to_raw_type
from log import *
from sign import getACSRFTokenForAMS, getDjcSignParams
from util import *

encoding_error_str = "Found invalid character in key name: '#'. Try quoting the key name. (line 1 column 2 char 1)"


class AccountInfoConfig(ConfigInterface):
    default_uin = "o123456789"

    def __init__(self):
        # 手动登录需要设置的信息
        self.uin = self.default_uin
        self.skey = "@a1b2c3d4e"

        # 自动登录需要设置的信息
        self.account = "123456789"
        self.password = "使用账号密码自动登录有风险_请理解这个功能到底如何使用你的账号密码后再决定是否使用"

    def has_login(self) -> bool:
        return self.uin != self.default_uin


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
        self.count = 0


class DnfHelperChronicleExchangeItemConfig(ConfigInterface):
    def __init__(self):
        self.sLbcode = "ex_0003"
        self.sName = "装备提升礼盒*1"
        self.count = 3


class FirecrackersExchangeItemConfig(ConfigInterface):
    def __init__(self):
        self.index = 6
        self.name = "灿烂的徽章自选礼盒*1"
        self.need_points = 120
        self.count = 1


class XinYueOperationConfig(ConfigInterface):
    def __init__(self):
        self.iFlowId = "512411"
        self.package_id = ""  # 仅礼包兑换需要这个参数，如兑换【勇者宝库】的【装备提升礼盒】的package_id为702218
        self.sFlowName = "输出我的任务积分"
        self.count = 1

    def unique_key(self) -> str:
        return f"{self.iFlowId}_{self.package_id}"


class XinYueAppOperationConfig(ConfigInterface):
    def __init__(self):
        # 操作名称
        self.name = "兑换复活币"
        # 抓包获取的加密http请求体。
        # 获取方式，抓包获取http body。如fiddler，抓包，找到对应请求（body大小为150的请求），右侧点Inspector/HexView，选中Http Body部分的字节码（未标蓝部分），右击Copy/Copy as 0x##，然后粘贴出来，将其中的bytes复制到下列对应数组位置
        self.encrypted_raw_http_body = [0x58, 0x59, 0x01, 0x00, 0x00, 0x01, 0x61, 0x0A, 0x01, 0x01, 0x2B, 0x10, 0x02, 0x3D, 0x00, 0x00, 0x10, 0xE5, 0xF7, 0x11, 0x0E, 0xF8, 0x2F, 0x1B, 0x13, 0x10, 0x6E, 0xA5, 0xF7, 0xE2, 0x7B, 0xD3, 0x58,
                                        0x0B, 0x1D, 0x00, 0x01, 0x01, 0x41, 0x28, 0x52, 0x61, 0x09, 0x86, 0x2C, 0x45, 0x32, 0x20, 0x87, 0xBA, 0xAE, 0xDF, 0x03, 0x34, 0x24, 0x68, 0x75, 0x65, 0x58, 0xDF, 0xC1, 0x61, 0x95, 0x7F, 0xAD, 0x9D,
                                        0xD3, 0x8E, 0x1E, 0x04, 0x5F, 0x68, 0xB2, 0xFA, 0x7A, 0x64, 0x77, 0x99, 0xCA, 0x36, 0x3D, 0xB9, 0x71, 0xF1, 0x80, 0x13, 0xAE, 0xCA, 0xBE, 0xF5, 0x26, 0x99, 0xB6, 0x6F, 0x93, 0xFD, 0xA0, 0x5C, 0x22,
                                        0xF5, 0x11, 0x21, 0xD2, 0x11, 0xE6, 0x0B, 0x39, 0xE2, 0xB8, 0xB0, 0x05, 0x8A, 0xA7, 0x76, 0xD7, 0xF4, 0x22, 0xA4, 0x24, 0x0F, 0xB5, 0xD2, 0x12, 0xAF, 0x09, 0xD8, 0xA0, 0x1C, 0x23, 0x0D, 0x75, 0xF0,
                                        0x68, 0x09, 0x6A, 0x2E, 0xEF, 0x6A, 0x76, 0x49, 0x5A, 0x6B, 0x78, 0xAA, 0xE2, 0x69, 0xE9, 0x31, 0x92, 0xB7, 0x21, 0x7C, 0xD9, 0x6E, 0x8C, 0x1E, 0x0D, 0xE6, 0xE0, 0xC0, 0x10, 0xDF, 0x95, 0x8E, 0x55,
                                        0xFC, 0x64, 0x21, 0x27, 0xA7, 0x87, 0x1E, 0x2B, 0x58, 0xBD, 0x84, 0x4F, 0xE3, 0xC2, 0xC4, 0xB4, 0x23, 0x79, 0x45, 0x57, 0x94, 0xFD, 0x2D, 0xD3, 0xA1, 0x09, 0x04, 0x86, 0xB7, 0xAC, 0xC5, 0x56, 0xB4,
                                        0xEF, 0xA2, 0x3A, 0xF2, 0x41, 0x16, 0x14, 0x02, 0xC4, 0xB2, 0x00, 0x5E, 0xD5, 0x0C, 0x9B, 0x5E, 0x0A, 0xFD, 0x1C, 0x75, 0xEC, 0xB1, 0x50, 0x7A, 0x4E, 0x6C, 0x78, 0xF9, 0xC4, 0x58, 0x7E, 0x73, 0xB6,
                                        0xA8, 0xB0, 0x91, 0xCE, 0x0D, 0xBA, 0xF8, 0xFC, 0x82, 0x81, 0xE6, 0xA8, 0x97, 0x75, 0x5F, 0x8B, 0x5A, 0x4B, 0xEB, 0x59, 0x45, 0x7F, 0x26, 0x57, 0x16, 0x4C, 0x84, 0x6A, 0x50, 0xF8, 0x95, 0x8F, 0x4C,
                                        0x85, 0x2D, 0xA1, 0x88, 0x81, 0xA8, 0xFF, 0x4D, 0x69, 0xEC, 0x6D, 0xC8, 0x05, 0xA0, 0xE0, 0x8F, 0x7D, 0x9C, 0x37, 0xCD, 0xB3, 0x0B, 0x05, 0xFD, 0xF0, 0x52, 0xB2, 0x86, 0x0D, 0x36, 0x27, 0x8B, 0xDF,
                                        0x34, 0x01, 0xA2, 0xC2, 0x01, 0xA8, 0x7F, 0xC9, 0x2F, 0xFA, 0x44, 0x1F, 0xBA, 0x81, 0x73, 0xF6, 0xD0, 0xAC, 0x5D, 0xA4, 0xED, 0x1F, 0xDB, 0x1D, 0xF8, 0x10, 0x97, 0x7E, 0x3F, 0xC3, 0x21, 0x08, 0x8D,
                                        0xB9, 0xCD, 0x82, 0x74, 0x1A, 0xE5, 0x8A, 0x39, 0x67, 0x3C, 0x26, 0x18, 0x53, 0xFC, 0xC4, 0x22, 0xAF, 0x83, 0x2F, 0x06, 0x13, 0xAB, 0xCF, 0x56, 0xF6, 0x42, 0x7D, 0x52, 0xD8, 0x62]


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

    def update(self, name, ruleid):
        self.name = name
        self.ruleid = ruleid

        return self


class ArkLotteryConfig(ConfigInterface):
    def __init__(self):
        # 用于完成幸运勇士的区服ID和角色ID，若服务器ID留空，则使用道聚城绑定的dnf角色信息
        self.lucky_dnf_server_id = ""  # 区服id可查阅utils/reference_data/dnf_server_list.js，具体值为每一个服务器配置中的v字段，如{t: "广东三区", v: "22"}表示广东三区的区服ID为"22"
        self.lucky_dnf_role_id = ""  # 角色ID，不知道时可以填写区服ID，该数值留空，这样处理到抽卡的时候会用黄色字体打印出来信息
        # 是否领取礼包（建议仅大号开启这个功能）
        self.need_take_awards = False

        # 是否展示在概览界面
        self.show_status = True
        # 卡牌数目使用特定的颜色
        self.show_color = ""

        # 活动ID => 是否消耗所有卡牌来抽奖（建议在兑换完所有礼包后再开启这个功能）
        self.act_id_to_cost_all_cards_and_do_lottery = {}  # type: Dict[int, bool]

    def fields_to_fill(self):
        return [
            ('take_awards', ArkLotteryAwardConfig),
        ]

    def on_config_update(self, raw_config: dict):
        self.act_id_to_cost_all_cards_and_do_lottery = {int(k): bool(v) for k, v in self.act_id_to_cost_all_cards_and_do_lottery.items()}


class VipMentorConfig(ConfigInterface):
    def __init__(self):
        # 领取第几个关怀礼包，可填1/2/3，一般是第二个最好
        self.take_index = 2
        # 用于完成关怀礼包的区服ID和角色ID，若服务器ID留空，则使用道聚城绑定的dnf角色信息
        self.guanhuai_dnf_server_id = ""  # 区服id可查阅utils/reference_data/dnf_server_list.js，具体值为每一个服务器配置中的v字段，如{t: "广东三区", v: "22"}表示广东三区的区服ID为"22"
        self.guanhuai_dnf_role_id = ""  # 角色ID，不知道时可以填写区服ID，该数值留空，这样处理到抽卡的时候会用黄色字体打印出来信息


class DnfHelperInfoConfig(ConfigInterface):
    def __init__(self):
        # userId/nickName的获取方式为，点开dnf助手中点开右下角的【我的】，然后点击右上角的【编辑】按钮，则社区ID即为userId，昵称即为nickname，如我的这俩值为504051073、风之凌殇
        # 社区ID
        self.userId = ""
        # 昵称
        self.nickName = ""
        # 登录票据，目前需手动更新。
        # 流程：
        #   1. 打开dnf助手并确保已登录账户，点击活动，找到【艾丽丝的密室，塔罗牌游戏】并点开，点击右上角分享，选择QQ好友，发送给【我的电脑】。
        #   2. 在我的电脑聊天框中的链接中找到请求中的token（形如&serverId=11&token=6C6bNrA4&isMainRole=0&subGameId=10014，因为&是参数分隔符，所以token部分为token=6C6bNrA4，所以token为6C6bNrA4, ps: 如果参数形如&serverId=&token=&isMainRole=&subGameId=，那么token部分参数为token=，说明这个活动助手没有把token放到链接里，需要尝试下一个），将其进行更新到配置文件中【dnf助手信息】配置中
        #
        # ps: 如果有多个账号需要领取这个，请不要在手机上依次登入登出执行上述步骤来获取token，因为你在登陆下一个账号的时候，之前的账号的token就因为登出而失效了
        #       有这个需求的话，请使用安卓模拟器的多开功能来多开dnf助手去登陆各个账号。如果手机支持多开app，也可以使用对应功能。具体多开流程请自行百度搜索： 手机 app 多开
        self.token = ""
        # 唯一角色ID，与token的获取方式完全一致，只是要找的参数从token变成了uniqueRoleId
        # 需要确保助手里配置的编年史领奖角色和道聚城里的一致，否则这个值会对不上
        self.uniqueRoleId = ""

        # dnf助手编年史是否开启抽奖
        self.chronicle_lottery = False
        # dnf助手编年史兑换道具信息，其他奖励信息可查阅utils/reference_data/dnf助手编年史活动_可兑换奖励列表.json
        self.chronicle_exchange_items = []  # type: List[DnfHelperChronicleExchangeItemConfig]

    def fields_to_fill(self):
        return [
            ('chronicle_exchange_items', DnfHelperChronicleExchangeItemConfig),
        ]

    def on_config_update(self, raw_config: dict):
        if len(self.token) != 0 and len(self.token) != 8:
            async_message_box(f"{self.nickName} 对应的token({self.token}) 必定是错误的，因为token的长度只可能是8位，而你填的token长度为{len(self.token)}", "token长度不对")


class HelloVoiceInfoConfig(ConfigInterface):
    def __init__(self):
        # hello语音的用户ID
        # 获取方式：打开hello语音，点击右下角【我的】tab，在最上方头像框的右侧，昵称下方，有形如【ID：XXXXXX】的字样，其中ID后面这串数字就是用户ID
        self.hello_id = ""


class FirecrackersConfig(ConfigInterface):
    def __init__(self):
        # 是否开启抽奖，建议兑换完所有道具后再开启
        self.enable_lottery = False
        # 兑换道具信息
        self.exchange_items = []  # type: List[FirecrackersExchangeItemConfig]

    def fields_to_fill(self):
        return [
            ('exchange_items', FirecrackersExchangeItemConfig),
        ]


class FunctionSwitchesConfig(ConfigInterface):
    def __init__(self):
        # ------------ 全局禁用开关 ------------
        # 是否禁用各种活动，供小号使用，这样新增的各种活动都将被禁用
        # 例外情况：道聚城、许愿、心悦特权专区、集卡这四个活动不受该配置项影响
        # 如果想要单独设置各个活动的开关，请不要设置这个配置项，否则各个新活动都会被禁用
        self.disable_most_activities = False

        # 是否禁用分享功能
        self.disable_share = False

        # ------------ 普通skey（需要登录 炎炎夏日 活动页面 获取） ------------
        # 是否领取道聚城
        self.get_djc = True
        # 是否启用许愿功能，用于完成《有理想》。目前仅限安卓版本道聚城上绑定王者荣耀时可使用
        self.make_wish = True
        # 是否领取心悦特权专区
        self.get_xinyue = True
        # 是否领取腾讯游戏信用相关礼包
        self.get_credit_xinyue_gift = True
        # 是否领取每月黑钻等级礼包
        self.get_heizuan_gift = True
        # 是否领取DNF进击吧赛利亚活动
        self.get_xinyue_sailiyam = True
        # 是否领取wegame国庆活动
        self.get_wegame_guoqing = True
        # 是否领取史诗之路来袭活动合集活动
        self.get_dnf_1224 = True
        # 是否领取DNF闪光杯第三期活动
        self.get_dnf_shanguang = True
        # 是否领取qq视频活动
        self.get_qq_video = True
        # 是否领取10月女法师三觉活动
        self.get_dnf_female_mage_awaken = True
        # 是否领取DNF助手排行榜活动，额外需要助手userId和token
        self.get_dnf_rank = True
        # 是否领取dnf助手编年史活动，额外需要助手userId
        self.get_dnf_helper_chronicle = True
        # 是否启用hello语音奖励兑换功能，额外需要hello语音的用户ID
        self.get_hello_voice = True
        # 是否领取2020DNF嘉年华页面主页面签到活动
        self.get_dnf_carnival = True
        # 是否领取2020DNF嘉年华直播活动
        self.get_dnf_carnival_live = True
        # 是否DNF共创投票
        self.get_dnf_dianzan = True
        # 是否领取DNF福利中心兑换
        self.get_dnf_welfare = True
        # 是否领取心悦app理财礼卡
        self.get_xinyue_financing = True
        # 是否领取心悦猫咪
        self.get_xinyue_cat = True
        # 是否领取心悦app周礼包
        self.get_xinyue_weekly_gift = True
        # 是否领取dnf漂流瓶
        self.get_dnf_drift = True
        # 是否领取DNF马杰洛的规划
        self.get_majieluo = True
        # 是否领取dnf助手活动，额外需要助手userId和token
        self.get_dnf_helper = True
        # 是否领取暖冬好礼活动
        self.get_warm_winter = True
        # 是否领取qq视频-AME活动
        self.get_qq_video_amesvr = True
        # 是否进行dnf论坛签到
        self.get_dnf_bbs_signin = True
        # 是否领取 DNF落地页 活动
        self.get_dnf_luodiye = True
        # 是否领取 WeGame 活动
        self.get_dnf_wegame = True
        # 是否领取 新春福袋大作战 活动
        self.get_spring_fudai = True
        # 是否领取 DNF福签大作战 活动
        self.get_dnf_fuqian = True
        # 是否领取 DNF集合站 活动
        self.get_dnf_collection = True
        # 是否领取 燃放爆竹 活动
        self.get_firecrackers = True
        # 是否领取 DNF奥兹玛竞速 活动
        self.get_dnf_ozma = True
        # 是否自动进行colg每日签到和积分领取（其他需自行操作~）
        self.get_colg_signin = True
        # 是否进行 心悦app 相关操作
        self.get_xinyue_app = True
        # 是否领取 DNF格斗大赛 活动
        self.get_dnf_pk = True
        # 是否领取 心悦 活动
        self.get_dnf_xinyue = True
        # 是否领取 DNF强者之路 活动
        self.get_dnf_strong = True
        # 是否领取 DNF漫画 活动
        self.get_dnf_comic = True
        # 是否领取 DNF十三周年庆 活动
        self.get_dnf_13 = True
        # 是否领取 我的dnf13周年活动 活动
        self.get_dnf_my_story = True
        # 是否领取 刃影预约活动 活动
        self.get_dnf_reserve = True
        # 是否领取 DNF周年庆登录活动 活动
        self.get_dnf_anniversary = True
        # 是否领取 KOL 活动
        self.get_dnf_kol = True
        # 是否领取 勇士的冒险补给 活动
        self.get_maoxian = True
        # 是否领取 小酱油周礼包和生日礼包 活动
        self.get_xiaojiangyou = True

        # ------------ QQ空间pskey（需要登录 QQ空间 获取） ------------
        # 是否启用 集卡 功能
        self.get_ark_lottery = True
        # 是否启用 阿拉德勇士征集令 活动
        self.get_dnf_warriors_call = True
        # 是否启用 会员关怀 活动
        self.get_vip_mentor = True
        # 是否启用 超级会员 活动
        self.get_dnf_super_vip = True
        # 是否启用 黄钻 活动
        self.get_dnf_yellow_diamond = True

        # ------------ 安全管家pskey（需要登录 安全管家 获取） ------------
        # 是否领取 管家蚊子腿 活动
        self.get_guanjia = True


class AccountConfig(ConfigInterface):
    def __init__(self):
        # 是否启用该账号
        self.enable = True
        # 是否在github action模式下启用
        self.enable_in_github_action = True
        # 是否处于安全模式，也就是登录的时候需要滑动验证码或者发送短信
        self.in_safe_mode = False
        # 账号名称，仅用于区分不同账号
        self.name = "默认账号名-1"
        # 登录模式
        # by_hand：      手动登录，在skey无效的情况下会弹出活动界面，自行登录后将cookie中uin和skey提取到下面的配置处
        # qr_login：     二维码登录，每次运行时若本地缓存的.skey文件中存储的skey过期了，则弹出登录页面，扫描二维码后将自动更新skey，进行后续操作
        # auto_login：   自动登录，每次运行若本地缓存的.skey文件中存储的skey过期了，根据填写的账密信息，自动登录来获取uin和skey，无需手动操作
        self.login_mode = "qr_login"
        # 是否无法在道聚城绑定dnf，比如被封禁或者是朋友的QQ（主要用于小号，被风控不能注册dnf账号，但是不影响用来当抽卡等活动的工具人）
        self.cannot_bind_dnf = False
        # 漂流瓶每日邀请列表，最多可填8个（不会实际发消息）
        self.drift_send_qq_list = []  # type: List[str]
        # dnf13周年邀请列表，最多可填3个（不会实际发消息）
        self.dnf_13_send_qq_list = []  # type: List[str]
        # 新春福袋大作战邀请列表（会实际发消息）
        self.spring_fudai_receiver_qq_list = []  # type: List[str]
        # 燃放爆竹活动是否尝试邀请好友（不会实际发消息）
        self.enable_firecrackers_invite_friend = False
        # 马杰洛活动是否尝试黑钻送好友（不会实际发消息）
        self.enable_majieluo_invite_friend = False
        # 不参与奥兹玛竞速活动切换角色的角色名列表（如果某些号确定不打奥兹玛的，可以把名字加到这里，从而跳过尝试这个角色）
        # eg. ["卢克奶妈一号", "卢克奶妈二号", "卢克奶妈三号"]
        self.ozma_ignored_rolename_list = []  # type: List[str]
        # dnf论坛签到formhash
        self.dnf_bbs_formhash = ""
        # dnf论坛cookie
        self.dnf_bbs_cookie = ""
        # colg cookie
        self.colg_cookie = ""
        # 漫画活动是否自动抽奖（建议手动领完需要的活动后开启该开关）
        self.comic_lottery = False
        # 腾讯系网页登录通用账号凭据与token
        self.account_info = AccountInfoConfig()
        # 各功能开关
        self.function_switches = FunctionSwitchesConfig()
        # 完成《礼包达人》任务所需的手游的名称信息
        self.mobile_game_role_info = MobileGameRoleInfoConfig()
        # 兑换道具信息
        self.exchange_items = []  # type: List[ExchangeItemConfig]
        # 心悦相关操作信息
        self.xinyue_operations = []  # type: List[XinYueOperationConfig]
        # 心悦app相关操作
        self.xinyue_app_operations = []  # type: List[XinYueAppOperationConfig]
        # 抽卡相关配置
        self.ark_lottery = ArkLotteryConfig()
        # 会员关怀相关配置
        self.vip_mentor = VipMentorConfig()
        # wegame国庆活动兑换道具
        self.wegame_guoqing_exchange_items = []  # type: List[WegameGuoqingExchangeItemConfig]
        # dnf助手信息
        self.dnf_helper_info = DnfHelperInfoConfig()
        # hello语音相关信息
        self.hello_voice = HelloVoiceInfoConfig()
        # 燃放爆竹相关配置
        self.firecrackers = FirecrackersConfig()

    def fields_to_fill(self):
        return [
            ('exchange_items', ExchangeItemConfig),
            ('xinyue_operations', XinYueOperationConfig),
            ('xinyue_app_operations', XinYueAppOperationConfig),
            ('wegame_guoqing_exchange_items', WegameGuoqingExchangeItemConfig),
        ]

    def is_enabled(self):
        if self.in_safe_mode and not config().common.enable_in_safe_mode_accounts:
            # 若账号处于安全模式，且当前不启用处于安全模式的账号，则视为未启用当前账号
            return False

        if is_run_in_github_action() and not self.enable_in_github_action:
            # 若当前在github action环境中运行，且设定为不在该环境中使用该QQ，则认为未启用
            logger.warning(f"账号 {self.name} 设定为不在github action中运行，将跳过，如需启用请修改 enable_in_github_action 配置")
            return False

        return self.enable

    def on_config_update(self, raw_config: dict):
        self.sDeviceID = self.getSDeviceID()
        self.aes_key = "84e6c6dc0f9p4a56"
        self.rsa_public_key_file = "utils/reference_data/public_key.der"

        self.updateUinSkey(self.account_info.uin, self.account_info.skey)

        self.drift_send_qq_list = [str(qq) for qq in self.drift_send_qq_list]
        self.dnf_13_send_qq_list = [str(qq) for qq in self.dnf_13_send_qq_list]
        self.spring_fudai_receiver_qq_list = [str(qq) for qq in self.spring_fudai_receiver_qq_list]

        if not self.check_role_id("集卡", self.ark_lottery.lucky_dnf_role_id):
            self.ark_lottery.lucky_dnf_role_id = ""

        if not self.check_role_id("关怀活动", self.vip_mentor.guanhuai_dnf_role_id):
            self.vip_mentor.guanhuai_dnf_role_id = ""

    def check_role_id(self, ctx, role_id) -> bool:
        if len(role_id) != 0 and not role_id.isdigit():
            async_message_box(f"账号 {self.name} 的{ctx}幸运角色ID似乎填的是昵称（{role_id}），这里需要填的是角色id，形如1282822。本次配置将置空，如需使用该功能，请在配置工具中将该字段清空，然后按照显示出来的提示操作", "配置有误")
            return False

        return True

    def updateUinSkey(self, uin, skey):
        self.account_info.uin = uin
        self.account_info.skey = skey

        self.g_tk = str(getACSRFTokenForAMS(self.account_info.skey))
        self.sDjcSign = getDjcSignParams(self.aes_key, self.rsa_public_key_file, uin2qq(self.account_info.uin), self.sDeviceID, appVersion)

    def getSDeviceID(self):
        sDeviceIdFileName = os.path.join(cached_dir, f".sDeviceID.{self.name}.txt")

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

    def get_exchange_item_by_iGoodsId(self, iGoodsId: str) -> Optional[ExchangeItemConfig]:
        for exchange_item in self.exchange_items:
            if exchange_item.iGoodsId == iGoodsId:
                return exchange_item

        return None

    def get_xinyue_exchange_item_by_unique_key(self, unique_key: str) -> Optional[XinYueOperationConfig]:
        for exchange_item in self.xinyue_operations:
            if exchange_item.unique_key() == unique_key:
                return exchange_item

        return None

    def get_xinyue_app_operation_by_name(self, name: str) -> Optional[XinYueAppOperationConfig]:
        for operation in self.xinyue_app_operations:
            if operation.name == name:
                return operation

        return None

    def qq(self) -> str:
        return uin2qq(self.account_info.uin)

    def is_xinyue_app_operation_not_set(self) -> bool:
        for op in self.xinyue_app_operations:
            if len(op.encrypted_raw_http_body) != 0:
                return False

        return True


class LoginConfig(ConfigInterface):
    def __init__(self):
        # 重试次数
        self.max_retry_count = 6
        # 重试间隔时间（秒）
        self.retry_wait_time = 1200
        # 打开网页后等待时长
        self.open_url_wait_time = 3
        # 加载页面的超时时间，以登录按钮出现为完成标志
        self.load_page_timeout = 15
        # 点击登录按钮后的超时时间，加载登录iframe，以其显示出来为完成标志
        self.load_login_iframe_timeout = 8
        # 登录的超时时间，从登录界面显示为开始，以用户完成登录为结束标志
        self.login_timeout = 60
        # 等待登录完成的超时时间，以活动结束的按钮弹出来标志
        self.login_finished_timeout = 60

        # 自动处理滑动验证码
        self.auto_resolve_captcha = True
        # 每次尝试滑动验证码的偏移值，为相对值，填倍数，表示相当于该倍数的滑块宽度
        self.move_captcha_delta_width_rate = 0.2

        # 推荐登录重试间隔变化率r。新的推荐值 = (1-r)*旧的推荐值 + r*本次成功重试的间隔
        self.recommended_retry_wait_time_change_rate = 0.125


class RetryConfig(ConfigInterface):
    def __init__(self):
        # 每次兑换请求之间的间隔时间（秒），避免请求过快而报错，目前测试1s正好不会报错~
        self.request_wait_time = 2
        # 当提示【"msg": "系统繁忙，请稍候再试。", "ret": "-9905"】时的最大重试次数
        self.max_retry_count = 3
        # 上述情况下的重试间隔时间（秒）
        self.retry_wait_time = 5


class XinYueConfig(ConfigInterface):
    def __init__(self):
        # 在每日几点后才尝试提交心悦的成就点任务，避免在没有上游戏时执行心悦成就点任务，导致高成就点的任务没法完成，只能完成低成就点的
        self.submit_task_after = 0


class MajieluoConfig(ConfigInterface):
    def __init__(self):
        # 大号在配置中的账号序号
        self.dahao_index = ""
        # 小号序号列表，最多3个
        self.xiaohao_indexes = []
        # 小号QQ号列表，最多3个
        self.xiaohao_qq_list = []
        # SCode 1
        self.scode_1 = ""
        # SCode 2
        self.scode_2 = ""
        # SCode 3
        self.scode_3 = ""

    def on_config_update(self, raw_config: dict):
        self.xiaohao_indexes = [str(index) for index in self.xiaohao_indexes]
        self.xiaohao_qq_list = [str(qq) for qq in self.xiaohao_qq_list]


class FixedTeamConfig(ConfigInterface):
    reg_qq = r'\d+'

    def __init__(self):
        # 是否启用该固定队
        self.enable = False
        # 固定队伍id，仅用于本地区分用
        self.id = "1"
        # 固定队成员，必须是两个，则必须都配置在本地的账号列表中了，否则将报错，不生效
        self.members = ["小队第一个账号的QQ号", "小队第二个账号的QQ号"]

    def on_config_update(self, raw_config: dict):
        # 由于经常会有人填写成数字，如[123, 456]，导致后面从各个dict中取值时出错（dict中都默认QQ为str类型，若传入int类型，会取不到对应的值）
        # 所以这里做下兼容，强制转换为str
        self.members = [str(qq) for qq in self.members]

    def check(self) -> bool:
        if len(self.members) != 2:
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
        # 仅运行首个账户（调试用）
        self.run_first_account_only = False
        # 账号数目，将在读取完配置后动态设定为当前设置的账号数目
        self.account_count = 1
        # 测试模式，若开启，则一些实验性功能将会启用
        self.test_mode = False
        # 是否启用处于安全模式的账号
        self.enable_in_safe_mode_accounts = False
        # 是否展示小助手的累积使用情况
        self._show_usage = False
        # 配置工具是否启用高DPI模式（4k屏幕建议启用该选项）
        self.config_ui_enable_high_dpi = False
        # 是否无视系统代理（VPN）
        self.bypass_proxy = True
        # 是否禁用cmd命令行的快速编辑模式，从而鼠标点选时不会暂停，避免误触而不知所措
        self.disable_cmd_quick_edit = True
        # 是否修改命令行缓存大小，以避免运行日志被截断
        self.enable_change_cmd_buffer = True
        # 是否最大化窗口
        self.enable_max_console = True
        # 是否最小化窗口
        self.enable_min_console = False
        # 是否启用多进程功能
        self.enable_multiprocessing = True
        # 是否启用超快速模式，若开启，则将并行运行所有账号的所有活动。仅在多进程功能启用或仅单个账号时生效。
        self.enable_super_fast_mode = True
        # 进程池大小，若为0，则默认为当前cpu核心数，若为-1，则在未开启超快速模式时为当前账号数，开启时为4*当前cpu核心数
        self.multiprocessing_pool_size = -1
        # 是否强制使用打包附带的便携版chrome
        self.force_use_portable_chrome = False
        # 强制使用特定大版本的chrome，默认为0，表示使用小助手默认设定的版本。
        self.force_use_chrome_major_version = 0
        # http(s)请求超时时间(秒)
        self.http_timeout = 10
        # 是否展示chrome的debug日志，如DevTools listening，Bluetooth等
        self._debug_show_chrome_logs = False
        # 自动登录模式是否不显示浏览器界面
        self.run_in_headless_mode = False
        # 日志等级, 级别从低到高依次为 "debug", "info", "warning", "error", "critical"
        self.log_level = "info"
        # 日志目录最大允许大小（单位为MiB），当超出该大小时将进行清理
        self.max_logs_size = 1024
        # 日志目录保留大小（单位为Mib），每次清理时将按时间顺序清理日志，直至剩余日志大小不超过该值
        self.keep_logs_size = 512
        # 是否在程序启动时手动检查更新
        self.check_update_on_start = True
        # 是否在程序结束时手动检查更新
        self.check_update_on_end = False
        self.readme_page = "https://github.com/fzls/djc_helper/blob/master/README.MD"
        self.changelog_page = "https://github.com/fzls/djc_helper/blob/master/CHANGELOG.MD"
        # 自动更新dlc购买地址
        self.auto_updater_dlc_purchase_url = "https://www.kuaifaka.net/purchasing?link=auto-updater"
        # 按月付费购买地址
        self.pay_by_month_purchase_url = "https://www.kuaifaka.net/purchasing?link=pay-by-month"
        # 网盘地址
        self.netdisk_link = "https://fzls.lanzoui.com/s/djc-helper"
        # QQ群
        self.qq_group = 553925117
        # 是否启用自动更新功能
        self.auto_update_on_start = True
        # 是否仅允许单个运行实例
        self.allow_only_one_instance = True
        # 是否尝试自动绑定新活动
        self.try_auto_bind_new_activity = True
        # 是否强制与道聚城的绑定角色同步，也就是说当活动角色与道聚城绑定角色不一致时，将强制修改为道聚城绑定的角色。
        # 开启后可以实现在道聚城修改绑定角色后，所有其他自动绑定的活动也将同步修改为该角色
        self.force_sync_bind_with_djc = True
        # 提前多少天提示付费过期
        self.notify_pay_expired_in_days = 7
        # 马杰洛新春版本赠送卡片目标QQ
        self.majieluo_send_card_target_qq = ""
        # 抽卡汇总展示色彩
        self.ark_lottery_summary_show_color = ""
        # 是否在活动最后一天消耗所有卡牌来抽奖（若还有卡）
        self.cost_all_cards_and_do_lottery_on_last_day = False
        # 调整日志等级对应颜色，颜色表可以运行log.py获取
        self.log_colors = {}  # type: Dict[str, str]
        # 自动赠送卡片的目标QQ数组，这些QQ必须是配置的账号之一，若配置则会在程序结束时尝试从其他小号赠送卡片给这些账号，且这些账号不会赠送卡片给其他账号，若不配置则不启用。
        # 赠送策略为：如果该QQ仍有可兑换奖励，将赠送目标QQ最需要的卡片；否则将赠送目标QQ其他QQ最富余的卡片
        self.auto_send_card_target_qqs = []  # type: List[str]
        # 接受福签赠送的scode列表，点赠送后查看链接中的sCode参数可知
        self.scode_list_accept_give = []
        # 接受福签索要的scode列表，点索要后查看链接中的sCode参数可知
        self.scode_list_accept_ask = []
        # 马杰洛赠送礼包inviteUin列表，点赠送后查看链接中的inviteUin参数可知
        self.majieluo_invite_uin_list = []  # type: List[str]
        # 登录各个阶段的最大等待时间，单位秒（仅二维码登录和自动登录需要配置，数值越大容错性越好）
        self.login = LoginConfig()
        # 各种操作的通用重试配置
        self.retry = RetryConfig()
        # 心悦相关配置
        self.xinyue = XinYueConfig()
        # 固定队相关配置。用于本地两个号来组成一个固定队伍，完成心悦任务。
        self.fixed_teams = []  # type: List[FixedTeamConfig]
        # 赛利亚活动拜访目标QQ列表
        self.sailiyam_visit_target_qqs = []  # type: List[str]
        # 马杰洛相关配置
        self.majieluo = MajieluoConfig()

    def fields_to_fill(self):
        return [
            ('fixed_teams', FixedTeamConfig),
        ]

    def on_config_update(self, raw_config: dict):
        log_level = self.log_level_map[self.log_level]
        consoleHandler.setLevel(log_level)

        try:
            from lanzou.api.utils import logger as lanzou_logger

            # 将lanzou的日志也显示
            lanzou_logger.setLevel(log_level)
        except Exception:
            pass
        if type(self.log_colors) is dict:
            for level, log_color in self.log_colors.items():
                consoleLogFormatter.log_colors[level] = log_color

        # 由于经常会有人填写成数字的列表，如[123, 456]，导致后面从各个dict中取值时出错（dict中都默认QQ为str类型，若传入int类型，会取不到对应的值）
        # 所以这里做下兼容，强制转换为str
        self.auto_send_card_target_qqs = [str(qq) for qq in self.auto_send_card_target_qqs]
        self.sailiyam_visit_target_qqs = [str(qq) for qq in self.sailiyam_visit_target_qqs]

        url_config_filepath = "utils/url.toml"
        if os.path.isfile(url_config_filepath):
            try:
                with open(url_config_filepath, 'r', encoding='utf-8-sig') as url_config_file:
                    url_config = toml.load(url_config_file)
                    if 'pay_by_month_purchase_url' in url_config:
                        self.pay_by_month_purchase_url = url_config['pay_by_month_purchase_url']
                    if 'netdisk_link' in url_config:
                        self.netdisk_link = url_config['netdisk_link']
            except:
                pass


class Config(ConfigInterface):
    def __init__(self):
        # 是否已经从配置文件中加载
        self.loaded = False
        # 所有账号共用的配置
        self.common = CommonConfig()
        # 兑换道具信息
        self.account_configs = []  # type: List[AccountConfig]

    def fields_to_fill(self):
        return [
            ('account_configs', AccountConfig),
        ]

    def on_config_update(self, raw_config: dict):
        if not self.check():
            logger.error("配置有误，请根据提示信息修改")
            exit(-1)

        if len(self.account_configs) != 0 and self.common.run_first_account_only:
            logger.warning(color("bold_yellow") + f"当前是调试模式，仅处理第一个账号，并关闭多进程和超快速功能")
            self.account_configs = self.account_configs[:1]
            self.common.enable_multiprocessing = False
            self.common.enable_super_fast_mode = False

        self.common.account_count = len(self.account_configs)
        if len(self.account_configs) == 1:
            if self.common.enable_super_fast_mode:
                # 单角色时，当启用了超快速模式，则强制开启多进程模式
                self.common.enable_multiprocessing = True
                logger.info(color("bold_green") + "当前仅有一个账号，因为已经开启超快速模式，将强制开启多进程模式~")
            elif self.common.enable_multiprocessing and not os.path.isfile("config.toml.local"):
                # 当同时满足以下条件时，强制关闭多进程功能
                #   1. 仅有一个账号
                #   2. 启用了多进程功能
                #   3. 未启用超快速模式
                #   4. 不存在config.toml.local文件
                logger.info(color("bold_green") + "当前仅有一个账号，没必要开启多进程模式，且未开启超快速模式，将关闭多进程模式~")
                self.common.enable_multiprocessing = False

    def check(self) -> bool:
        name2index = {}
        for _idx, account in enumerate(self.account_configs):
            idx = _idx + 1

            # 检查是否填写名称
            if len(account.name) == 0:
                logger.error(color("fg_bold_red") + f"第{idx}个账号未设置名称，请确保已填写对应账号配置的name")
                return False

            # 检查名称是否重复
            if account.name in name2index:
                logger.error(color("fg_bold_red") + f"第{idx}个账号的名称 {account.name} 与第{name2index[account.name]}个账号的名称重复，请调整为不同的名字")
                return False
            name2index[account.name] = idx

            # 检查dnf助手的userId是否误填为了昵称
            dhi = account.dnf_helper_info
            if dhi.userId != "":
                try:
                    int(dhi.userId)
                except ValueError:
                    logger.error(color("fg_bold_red") + (
                        f"第{idx}个账号配置的dnf助手信息的社区ID(userId)=[{dhi.userId}]似乎为昵称，请仔细检查是否与昵称(nickName)=[{dhi.nickName}]的值填反了？"
                        "id应该类似[504051073]，而昵称则形如[风之凌殇]"
                    ))
                    return False

        return True

    def is_all_account_auto_login(self) -> bool:
        for account in self.account_configs:
            if account.login_mode != "auto_login":
                return False

        return True

    def has_any_account_auto_login(self) -> bool:
        for account in self.account_configs:
            if account.login_mode == "auto_login":
                return True

        return False

    def get_pool_size(self) -> int:
        if not self.common.enable_multiprocessing:
            return 0

        final_pool_size = 0

        pool_size = self.common.multiprocessing_pool_size
        if pool_size == 0:
            # 若为0，则默认为当前cpu核心数
            final_pool_size = cpu_count()
        elif pool_size == -1:
            # 若为-1，则在未开启超快速模式时为当前账号数，开启时为4*当前cpu核心数
            if self.common.enable_super_fast_mode:
                final_pool_size = 4 * cpu_count()
            else:
                final_pool_size = len(self.account_configs)
        else:
            final_pool_size = pool_size

        if platform.system() == "Windows":
            # https://bugs.python.org/issue26903
            # windows下有限制，最多只能设置pool为60
            max_pool_size_in_windows = 60
            if final_pool_size > max_pool_size_in_windows:
                final_pool_size = max_pool_size_in_windows

        return final_pool_size

    def get_account_config_by_name(self, name: str) -> Optional[AccountConfig]:
        for account_config in self.account_configs:
            if account_config.name == name:
                return account_config

        return None

    def get_qq_accounts(self) -> List[str]:
        return list([uin2qq(account_cfg.account_info.uin) for account_cfg in self.account_configs if account_cfg.enable])

    def get_any_enabled_account(self) -> Optional[AccountConfig]:
        for account_config in self.account_configs:
            if account_config.is_enabled():
                return account_config

        return None


g_config = Config()


# 读取程序config
def load_config(config_path="config.toml", local_config_path="config.toml.local", reset_before_load=False):
    global g_config

    if reset_before_load:
        # 先重置
        g_config = Config()

    # 首先尝试读取config.toml（受版本管理系统控制）
    try:
        raw_config = toml.load(config_path)
        g_config.auto_update_config(raw_config)
    except UnicodeDecodeError as error:
        logger.error(color("fg_bold_yellow") + f"{config_path}的编码格式有问题，应为utf-8，如果使用系统自带记事本的话，请下载vscode或notepad++等文本编辑器\n错误信息：{error}\n")
        raise error
    except Exception as error:
        if encoding_error_str in str(error):
            logger.error(color("fg_bold_yellow") + f"{config_path}的编码格式有问题，应为utf-8，如果使用系统自带记事本的话，请下载vscode或notepad++等文本编辑器\n错误信息：{error}\n")
            raise error

        logger.error(color("fg_bold_red") + f"读取{config_path}文件出错，是否直接在压缩包中打开了或者toml语法有问题？\n具体出错为：{error}\n" +
                     color("fg_bold_yellow") + "若未完整解压，请先解压。否则请根据上面的英文报错信息，自行百度学习toml的基本语法，然后处理对应行的语法错误（看不懂的话自行用百度翻译或有道翻译）")
        raise error

    # 然后尝试读取本地文件（不受版本管理系统控制）
    try:
        if local_config_path != "":
            raw_config = toml.load(local_config_path)
            g_config.auto_update_config(raw_config)
    except Exception:
        pass

    # 最后尝试从环境变量获取配置，主要用于github action自动运行
    if is_run_in_github_action():
        logger.info("当前在github action环境下运行，将从环境变量中读取配置信息强制覆盖~")
        raw_config = toml.loads(get_config_from_env())
        g_config.auto_update_config(raw_config)

    # 标记为已经初始化完毕
    g_config.loaded = True


def gen_config_for_github_action():
    # 读取配置
    load_config()
    cfg = config()

    # 检查是否所有账号都是账密登录，不是则抛异常退出
    for account_cfg in cfg.account_configs:
        if account_cfg.login_mode != "auto_login":
            raise Exception("github action专用配置应全部使用账密自动登录模式，请修改~")

    # note: 做一些github action上专门的改动
    # 不打开浏览器（因为没有显示器可以看<_<)
    cfg.common.run_in_headless_mode = True
    # 不显示使用情况
    cfg.common._show_usage = False
    # 强制使用便携版（因为必定没有安装chrome）
    cfg.common.force_use_portable_chrome = True
    # 展示chrome调试日志
    cfg.common._debug_show_chrome_logs = True
    # 设置日志级别为log，方便查问题
    cfg.common.log_level = "debug"
    # 不必检查更新，必定是最新版本
    cfg.common.check_update_on_start = False
    cfg.common.check_update_on_end = False
    # 不必自动更新，同理
    cfg.common.auto_update_on_start = False

    # 保存到专门配置文件
    show_config_size(cfg, "精简前")

    # 一些字段设置为默认值
    cfg.loaded = False

    dc = CommonConfig()
    cfg.common.account_count = dc.account_count
    cfg.common.test_mode = dc.test_mode
    cfg.common.config_ui_enable_high_dpi = dc.config_ui_enable_high_dpi
    cfg.common.disable_cmd_quick_edit = dc.disable_cmd_quick_edit
    cfg.common.enable_min_console = dc.enable_min_console
    cfg.common.log_colors = dc.log_colors
    cfg.common.login = dc.login
    cfg.common.http_timeout = dc.http_timeout
    cfg.common.majieluo = dc.majieluo

    for account_cfg in cfg.account_configs:
        df = AccountConfig()
        account_cfg.drift_send_qq_list = df.drift_send_qq_list
        account_cfg.dnf_13_send_qq_list = df.dnf_13_send_qq_list
        account_cfg.spring_fudai_receiver_qq_list = df.spring_fudai_receiver_qq_list
        account_cfg.enable_firecrackers_invite_friend = df.enable_firecrackers_invite_friend
        account_cfg.enable_majieluo_invite_friend = df.enable_majieluo_invite_friend
        account_cfg.ozma_ignored_rolename_list = df.ozma_ignored_rolename_list

    # hack: 官方文档写secrets最多64KB，实测最多45022个字符。
    #  https://docs.github.com/en/actions/reference/encrypted-secrets#limits-for-secrets
    #  因此这里特殊处理一些账号级别开关，若配置与默认配置相同，或者是空值，则直接从配置文件中移除~
    remove_unnecessary_configs(cfg.common.login, LoginConfig())
    remove_unnecessary_configs(cfg.common.retry, RetryConfig())
    remove_unnecessary_configs(cfg.common.xinyue, XinYueConfig())
    remove_unnecessary_configs(cfg.common.majieluo, XinYueConfig())
    remove_unnecessary_configs(cfg.common, CommonConfig())
    for account_cfg in cfg.account_configs:
        remove_unnecessary_configs(account_cfg.account_info, AccountInfoConfig())
        remove_unnecessary_configs(account_cfg.function_switches, FunctionSwitchesConfig())
        remove_unnecessary_configs(account_cfg.mobile_game_role_info, MobileGameRoleInfoConfig())
        remove_unnecessary_configs(account_cfg.ark_lottery, ArkLotteryConfig())
        remove_unnecessary_configs(account_cfg.vip_mentor, VipMentorConfig())
        remove_unnecessary_configs(account_cfg.dnf_helper_info, DnfHelperInfoConfig())
        remove_unnecessary_configs(account_cfg.hello_voice, HelloVoiceInfoConfig())
        remove_unnecessary_configs(account_cfg.firecrackers, FirecrackersConfig())
        remove_unnecessary_configs(account_cfg, AccountConfig())

    show_config_size(cfg, "精简后")

    save_filename = 'config.toml.github_action'
    save_config(cfg, save_filename)
    logger.info(f"已经保存到 {save_filename}")


def show_config_size(cfg: Config, ctx):
    data_to_save = json.loads(json.dumps(to_raw_type(cfg)))
    toml_str = toml.dumps(data_to_save)
    total_size = len(toml_str)
    total_lines = toml_str.count('\n')
    logger.info(f"{ctx} 生成配置文件大小为{total_size}，总行数为{total_lines}")


def remove_unnecessary_configs(cfg, default_cfg):
    attrs_to_remove = []

    for attr, value in cfg.__dict__.items():
        # 1. 移除动态参数
        # 2. 移除与默认配置一致的参数
        # 3. 移除没有任何子字段的实现配置接口的字段
        if not hasattr(default_cfg, attr) or getattr(default_cfg, attr) == value or (isinstance(value, ConfigInterface) and value.__dict__ == {}):
            attrs_to_remove.append(attr)

    for attr in attrs_to_remove:
        delattr(cfg, attr)


def save_config(cfg: Config, config_path="config.toml"):
    with open(config_path, 'w', encoding='utf-8') as save_file:
        data_to_save = json.loads(json.dumps(to_raw_type(cfg)))
        toml.dump(data_to_save, save_file)


def config():
    if not g_config.loaded:
        logger.info("配置尚未加载，需要初始化")
        load_config("config.toml", "config.toml.local")

    return g_config


if __name__ == '__main__':
    load_config("config.toml", "config.toml.local")
    logger.info(config().common.account_count)

    cfg = config()
    print(cfg.common.auto_updater_dlc_purchase_url)
    print(cfg.common.pay_by_month_purchase_url)
    print(cfg.common.netdisk_link)
    print(cfg.common.qq_group)

    # cfg.common.auto_update_on_start = True
    # save_config(cfg)

    gen_config_for_github_action()
    gen_config_for_github_action_base64()
