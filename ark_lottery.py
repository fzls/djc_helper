import json
import random

import requests

from config import AccountConfig
from dao import RoleInfo
from log import logger, color
from network import process_result
from qq_login import LoginResult
from sign import getACSRFTokenForAMS
from urls import Urls
from util import uin2qq


class ArkLottery:
    def __init__(self, djc_helper, lr):
        """
        :type djc_helper: DjcHelper
        :type lr: LoginResult
        :type roleinfo: RoleInfo
        """
        # 即使没绑定dnf角色，也放行，方便领取分享奖励
        roleinfo = None
        try:
            if 'dnf' in djc_helper.bizcode_2_bind_role_map:
                roleinfo = djc_helper.bizcode_2_bind_role_map['dnf'].sRoleInfo
        except:
            pass
        self.roleinfo = roleinfo

        self.djc_helper = djc_helper
        self.lr = lr

        self.cfg = djc_helper.cfg  # type: AccountConfig

        self.g_tk = getACSRFTokenForAMS(lr.p_skey)
        self.urls = Urls()
        # 使用QQ空间登录态进行抽卡活动
        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; MIX 2 Build/PKQ1.190118.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045332 Mobile Safari/537.36 V1_AND_SQ_8.4.8_1492_YYB_D QQ/8.4.8.4810 NetType/WIFI WebP/0.3.0 Pixel/1080 StatusBarHeight/76 SimpleUISwitch/0 QQTheme/1000 InMagicWin/0",
            "Cookie": "p_uin={p_uin}; p_skey={pskey}; ".format(p_uin=self.lr.uin, pskey=self.lr.p_skey),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

    def ark_lottery(self):
        if self.roleinfo is None:
            logger.warning("未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定，否则每日登录游戏和幸运勇士的增加抽卡次数将无法成功进行。")

        # 增加次数
        self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日登陆页面", 25970)
        self.do_ark_lottery("v2/fcg_yvip_game_pull_flow", "增加抽卡次数-每日登陆游戏", 25968, query="0", act_name="act_dnf_ark9")
        self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日分享", 25938)

        # 幸运勇士
        server_id, roleid = "", ""
        if self.cfg.ark_lottery.lucky_dnf_server_id == "":
            logger.warning("未配置抽卡的幸运勇士的区服和角色信息，将使用道聚城绑定的角色信息")
        else:
            if self.cfg.ark_lottery.lucky_dnf_role_id == "":
                logger.warning("配置了抽卡幸运勇士的区服ID为{}，但未配置角色ID，将打印该服所有角色信息如下，请将合适的角色ID填到配置表".format(self.cfg.ark_lottery.lucky_dnf_server_id))
                self.djc_helper.query_dnf_rolelist(self.cfg.ark_lottery.lucky_dnf_server_id)
            else:
                logger.info("使用配置的区服和角色信息来进行幸运勇士加次数")
                cfg = self.cfg.ark_lottery
                server_id, roleid = cfg.lucky_dnf_server_id, cfg.lucky_dnf_role_id

        self.do_ark_lottery("v2/fcg_yvip_game_pull_flow", "增加抽卡次数-幸运勇士", 25969, query="0", act_name="act_dnf_xinyun3",
                            area=server_id, partition=server_id, roleid=roleid)

        # 抽卡
        count = self.remaining_lottery_times()
        logger.info("上述操作完毕后，最新抽卡次数为{}，将全部用来抽卡".format(count))
        for idx in range(count):
            self.do_ark_lottery("fcg_qzact_lottery", "抽卡-第{}次".format(idx + 1), "25940")

        # # 领取集卡奖励
        if len(self.cfg.ark_lottery.take_awards) != 0:
            for award in self.cfg.ark_lottery.take_awards:
                for idx in range(award.count):
                    api = "fcg_receive_reward"
                    if int(award.ruleid) == 25939:
                        # 至尊礼包的接口与其他奖励接口不一样
                        api = "fcg_prize_lottery"
                    self.do_ark_lottery(api, award.name, award.ruleid, gameid="dnf")
        else:
            logger.warning("未设置领取集卡礼包奖励，也许是小号，请记得定期手动登录小号来给大号赠送缺失的卡")

        # 消耗卡片来抽奖
        self.try_lottery_using_cards()

    def try_lottery_using_cards(self, print_warning=True):
        if self.cfg.ark_lottery.cost_all_cards_and_do_lottery:
            card_counts = self.get_card_counts()
            for name, count in card_counts.items():
                self.lottery_using_cards(name, count)
        else:
            if print_warning: logger.warning(color("fg_bold_cyan") + "尚未开启消耗所有卡片来抽奖功能，建议所有礼包都兑换完成后开启该功能，从而充分利用卡片")

    def lottery_using_cards(self, card_name, count=1):
        if count <= 0:
            return

        logger.info("尝试消耗{}张卡片【{}】来进行抽奖".format(count, card_name))

        card_name_to_ruleid = {
            "多人配合新挑战": "25961", "丰富机制闯难关": "25960", "新剧情视听盛宴": "25959", "单人成团战不停": "25958",
            "回归奖励大升级": "25957", "秒升Lv96刷深渊": "25956", "灿烂自选回归领": "25955", "告别酱油变大佬": "25954",
            "单人爽刷新玩法": "25953", "独立成团打副本": "25952", "海量福利金秋享": "25951", "超强奖励等你拿": "25950",
        }
        ruleid = card_name_to_ruleid[card_name]
        for idx in range(count):
            # 消耗卡片获得抽奖资格
            self.do_ark_lottery("fcg_qzact_present", "增加抽奖次数-消耗卡片({})".format(card_name), ruleid)

            # 抽奖
            self.do_ark_lottery("fcg_prize_lottery", "进行卡片抽奖", "25949", gameid="dnf")

    def fetch_lottery_data(self):
        res = requests.post(self.urls.ark_lottery_page, headers=self.headers)
        page_html = res.text

        data_prefix = "window.syncData = "
        data_suffix = ";\n</script>"

        prefix_idx = page_html.index(data_prefix) + len(data_prefix)
        suffix_idx = page_html.index(data_suffix, prefix_idx)

        self.lottery_data = json.loads(page_html[prefix_idx:suffix_idx])

    def remaining_lottery_times(self):
        self.fetch_lottery_data()

        return self.lottery_data["actCount"]["rule"]["25940"]["count"][0]['left']

    def get_card_counts(self):
        self.fetch_lottery_data()

        card_counts = {}

        count_map = self.lottery_data["actCount"]["rule"]
        for group_name, group_info in self.lottery_data["zzconfig"]["cardGroups"].items():
            for cardinfo in group_info["cardList"]:
                ruleid = cardinfo["lotterySwitchId"]
                count_id = cardinfo["id"]
                for count_info in count_map[str(ruleid)]["count"]:
                    if count_info["countid"] == count_id:
                        name, left = cardinfo["name"], count_info["left"]
                        card_counts[name] = left

        return card_counts

    def get_prize_counts(self):
        self.fetch_lottery_data()

        prize_counts = {}

        count_map = self.lottery_data["actCount"]["rule"]
        for group_name, group_info in self.lottery_data["zzconfig"]["prizeGroups"].items():
            ruleid = group_info["rule"]
            count_id = group_info["qual"]
            for count_info in count_map[str(ruleid)]["count"]:
                if count_info["countid"] == count_id:
                    name, left = group_info["title"], count_info["left"]
                    prize_counts[name] = left

        return prize_counts

    def do_ark_lottery(self, api, ctx, ruleid, query="", act_name="", gameid="", area="", partition="", roleid="", pretty=False, print_res=True):
        url = self.urls.ark_lottery.format(
            api=api,
            g_tk=self.g_tk,
            rand=random.random(),
        )
        if self.roleinfo is not None:
            area = area or self.roleinfo.serviceID
            partition = partition or self.roleinfo.serviceID
            roleid = roleid or self.roleinfo.roleCode

        raw_data = self.urls.ark_lottery_raw_data.format(
            actid=3886,
            ruleid=ruleid,
            area=area,
            partition=partition,
            roleid=roleid,
            query=query,
            act_name=act_name,
            gameid=gameid,
            uin=uin2qq(self.lr.uin),
        )

        res = requests.post(url, raw_data, headers=self.headers)
        return process_result(ctx, res, pretty, print_res)
