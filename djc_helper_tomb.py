from __future__ import annotations

import json
from typing import Callable
from urllib.parse import quote_plus

import requests

from config import AccountConfig, CommonConfig
from dao import BuyInfo
from log import logger
from network import check_tencent_game_common_status_code
from qq_login import LoginResult
from qzone_activity import QzoneActivity
from setting import parse_card_group_info_map, zzconfig
from sign import getACSRFTokenForAMS
from urls import Urls, get_act_url
from util import base64_str, json_compact, range_from_one, show_head_line, try_except


# 将几乎可以确定不再会重新上线的活动代码挪到这里，从而减少 djc_helper.py 的行数
class DjcHelperTomb:
    def __init__(self, account_config, common_config, user_buy_info: BuyInfo | None = None):
        self.cfg: AccountConfig = account_config
        self.common_cfg: CommonConfig = common_config

        # 初始化部分字段
        self.lr: LoginResult | None = None

        # 配置加载后，尝试读取本地缓存的skey
        self.local_load_uin_skey()

        # 初始化网络相关设置
        self.init_network()

        # 相关链接
        self.urls = Urls()

        self.user_buy_info = user_buy_info

        self.zzconfig = zzconfig()

    def expired_activities(self) -> list[tuple[str, Callable]]:
        # re: 记得过期活动全部添加完后，一个个确认下确实过期了
        return [
            ("qq会员杯", self.dnf_club_vip),
            ("集卡_旧版", self.ark_lottery),
        ]

    # -------------------------------------------- qq会员杯 --------------------------------------------
    # note: 适配流程如下
    #   0. 打开对应活动页面
    #   1. 获取子活动id   搜索 tianxuan = ，找到各个活动的id
    #   2. 填写新链接和活动时间   在 urls.py 中，替换get_act_url("qq会员杯")的值为新的网页链接，并把活动时间改为最新
    #   3. 重新启用代码 将调用处从 expired_activities 移到 payed_activities
    @try_except()
    def dnf_club_vip(self):
        get_act_url("qq会员杯")
        show_head_line("qq会员杯")
        self.show_not_ams_act_info("qq会员杯")

        if not self.cfg.function_switches.get_dnf_club_vip or self.disable_most_activities():
            logger.warning("未启用领取qq会员杯功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.lr = self.fetch_club_vip_p_skey("club.vip")
        if self.lr is None:
            return

        # self.club_qzone_act_op("开通会员-openSvip", "11997_5450c859")
        # self.club_qzone_act_op("领取开通奖励-receiveRewards", "12001_a24bdb71")
        self.club_qzone_act_op("报名并领取奖励-signUp", "12002_262a3b1d")
        # self.club_qzone_act_op("邀请好友-invitation", "12153_257cd052")
        # self.club_qzone_act_op("接受邀请-receiveInvitation", "12168_73c057d6")
        self.club_qzone_act_op("通关一次命运的抉择-helpClearanceOnce", "12154_0dcd2046")
        self.club_qzone_act_op("20分钟内通关命运的抉择-helpClearanceLimitTime", "12155_b1bae685")
        self.club_qzone_act_op("游戏在线30分钟-gameOnline", "12004_757ee8c2")
        self.club_qzone_act_op("通关一次【命运的抉择】-clearanceOnce", "12379_37ef2682")
        self.club_qzone_act_op("特权网吧登录-privilegeBar", "12006_deddc48a")
        # self.club_qzone_act_op("抽奖次数?-luckyNum", "12042_187645f2")
        for idx in range_from_one(2):
            self.club_qzone_act_op(f"[{idx}/2] 抽奖-lucky", "12003_404fde87")

    def club_qzone_act_op(
        self, ctx, sub_act_id, act_req_data=None, extra_act_req_data: dict | None = None, print_res=True
    ):
        # 另一类qq空间系活动，需要特殊处理
        # https://club.vip.qq.com/qqvip/api/tianxuan/access/execAct?g_tk=502405433&isomorphism-args=W3siU3ViQWN0SWQiOiIxMjAwNl9kZWRkYzQ4YSIsIkFjd .......

        # 首先构造普通的请求body
        body = {
            "SubActId": sub_act_id,
            "ActReqData": json_compact(self.get_qzone_act_req_data(act_req_data, extra_act_req_data)),
            "ClientPlat": 2,
        }

        # 然后外面套一层列表
        list_body = [body]

        # 再序列化为json（不出现空格）
        json_str = json.dumps(list_body, separators=(",", ":"))

        # 之后转化为base64编码
        b64_str = base64_str(json_str)

        # 然后进行两次URL编码，作为 isomorphism-args 参数
        isomorphism_args = quote_plus(quote_plus(b64_str))

        extra_cookies = f"p_skey={self.lr.p_skey};"
        self.get(
            ctx,
            self.urls.qzone_activity_club_vip,
            g_tk=getACSRFTokenForAMS(self.lr.p_skey),
            isomorphism_args=isomorphism_args,
            extra_cookies=extra_cookies,
            print_res=print_res,
        )

    # --------------------------------------------QQ空间集卡--------------------------------------------
    @try_except()
    def ark_lottery(self):
        # note: 启用和废弃抽卡活动的流程如下
        #   1. 启用
        #   1.0 电脑chrome中设置Network conditions中的User agent为手机QQ的： Mozilla/5.0 (Linux; U; Android 5.0.2; zh-cn; X900 Build/CBXCNOP5500912251S) AppleWebKit/533.1 (KHTML, like Gecko)Version/4.0 MQQBrowser/5.4 TBS/025489 Mobile Safari/533.1 V1_AND_SQ_6.0.0_300_YYB_D QQ/6.0.0.2605 NetType/WIFI WebP/0.3.0 Pixel/1440
        #   1.1 获取新配置   chrome设置为手机qq UA后，登录抽卡活动页面 get_act_url("集卡") ，然后打开主页源代码，从中搜索【window.syncData】找到逻辑数据和配置，将其值复制到【setting/ark_lottery.py】中，作为setting变量的值
        #   1.2 填写新链接   在 urls.py 中，替换self.ark_lottery_page 的值为新版抽卡活动的链接（理论上应该只有 zz 和 verifyid 参数的值会变动，而且大概率是+1）
        #   1.3 重新启用代码
        #   1.3.1 在 djc_helper.py 中将 ark_lottery 的调用处从 expired_activities 移到 payed_activities
        #   1.3.2 在 config.toml 和 config.example.toml 中 act_id_to_cost_all_cards_and_do_lottery 中增加新集卡活动的默认开关
        #   1.4 更新 urls.py 中 not_ams_activities 中集卡活动的时间
        #
        # hack:
        #   2. 废弃
        #   2.1 在 djc_helper.py 中将 ark_lottery 的调用处从 normal_run 移到 expired_activities

        # get_act_url("集卡")
        show_head_line(f"QQ空间集卡 - {self.zzconfig.actid}_{self.zzconfig.actName}")
        self.show_not_ams_act_info("集卡")

        if not self.cfg.function_switches.get_ark_lottery:
            logger.warning("未启用领取QQ空间集卡功能，将跳过")
            return

        self.fetch_pskey()
        if self.lr is None:
            return

        qa = QzoneActivity(self, self.lr)
        qa.ark_lottery()

    def ark_lottery_query_left_times(self, to_qq):
        ctx = f"查询 {to_qq} 的剩余被赠送次数"
        res = self.get(
            ctx, self.urls.ark_lottery_query_left_times, to_qq=to_qq, actName=self.zzconfig.actName, print_res=False
        )
        # # {"13320":{"data":{"uAccuPoint":4,"uPoint":3},"ret":0,"msg":"成功"},"ecode":0,"ts":1607934735801}
        if res["13320"]["ret"] != 0:
            return 0
        return res["13320"]["data"]["uPoint"]

    def send_card(self, card_name: str, cardId: str, to_qq: str, print_res=False) -> dict:
        from_qq = self.qq()

        ctx = f"{from_qq} 赠送卡片 {card_name}({cardId}) 给 {to_qq}"
        return self.get(
            ctx,
            self.urls.ark_lottery_send_card,
            cardId=cardId,
            from_qq=from_qq,
            to_qq=to_qq,
            actName=self.zzconfig.actName,
            print_res=print_res,
        )
        # # {"13333":{"data":{},"ret":0,"msg":"成功"},"ecode":0,"ts":1607934736057}

    def send_card_by_name(self, card_name, to_qq):
        card_info_map = parse_card_group_info_map(self.zzconfig)
        return self.send_card(card_name, card_info_map[card_name].id, to_qq, print_res=True)

    # note: 以下这部分都是仅用来占位的，方便搬过来的过时代码不提示错误

    def local_load_uin_skey(self):
        pass

    def init_network(self):
        pass

    def show_not_ams_act_info(self, act_name: str):
        pass

    def disable_most_activities(self):
        return False

    def get_dnf_bind_role(self):
        pass

    def fetch_pskey(self):
        pass

    def get(
        self,
        ctx,
        url,
        pretty=False,
        print_res=True,
        is_jsonp=False,
        is_normal_jsonp=False,
        need_unquote=True,
        extra_cookies="",
        check_fn: Callable[[requests.Response], Exception | None] | None = check_tencent_game_common_status_code,
        extra_headers: dict[str, str] | None = None,
        use_this_cookies="",
        prefix_to_remove="",
        suffix_to_remove="",
        **params,
    ) -> dict:
        return {}

    def qq(self):
        pass

    def fetch_club_vip_p_skey(self, param):
        pass

    def get_qzone_act_req_data(self, act_req_data, extra_act_req_data):
        pass
