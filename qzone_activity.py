import datetime
import json
import random

import requests

from config import AccountConfig
from dao import RoleInfo, DnfWarriorsCallInfo
from log import logger, color
from network import process_result, try_request
from qq_login import LoginResult
from setting import *
from sign import getACSRFTokenForAMS
from urls import Urls
from util import uin2qq


class QzoneActivity:
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
        self.zzconfig = djc_helper.zzconfig  # type: ArkLotteryZzConfig

        self.g_tk = getACSRFTokenForAMS(lr.p_skey)
        self.urls = Urls()
        # 使用QQ空间登录态进行抽卡活动
        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; MIX 2 Build/PKQ1.190118.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045332 Mobile Safari/537.36 V1_AND_SQ_8.4.8_1492_YYB_D QQ/8.4.8.4810 NetType/WIFI WebP/0.3.0 Pixel/1080 StatusBarHeight/76 SimpleUISwitch/0 QQTheme/1000 InMagicWin/0",
            "Cookie": "p_uin={p_uin}; p_skey={pskey}; ".format(p_uin=self.lr.uin, pskey=self.lr.p_skey),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

    # ----------------- 集卡活动 ----------------------

    def ark_lottery(self):
        if self.roleinfo is None:
            logger.warning("未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定，否则每日登录游戏和幸运勇士的增加抽卡次数将无法成功进行。")

        # 增加次数
        self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日登陆页面（本次似乎没启用这个，所以会提示没资格）", self.zzconfig.rules.loginPage)
        self.do_ark_lottery("v2/fcg_yvip_game_pull_flow", "增加抽卡次数-每日登陆游戏", self.zzconfig.rules.login, query="0", act_name=self.zzconfig.loginActId)
        self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日分享", self.zzconfig.rules.share)
        self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日观看直播", self.zzconfig.rules.video)

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

        self.do_ark_lottery("v2/fcg_yvip_game_pull_flow", "增加抽卡次数-幸运勇士", self.zzconfig.rules.imback, query="0", act_name=self.zzconfig.backActId,
                            area=server_id, partition=server_id, roleid=roleid)

        # 抽卡
        count = self.remaining_lottery_times()
        logger.info("上述操作完毕后，最新抽卡次数为{}，将全部用来抽卡".format(count))
        for idx in range(count):
            self.do_ark_lottery("fcg_qzact_lottery", "抽卡-第{}次".format(idx + 1), self.zzconfig.rules.lottery)

        # # 领取集卡奖励
        if self.cfg.ark_lottery.need_take_awards:
            take_awards = parse_prize_list(self.zzconfig)

            for award in take_awards:
                for idx in range(award.count):
                    api = "fcg_receive_reward"
                    if int(award.ruleid) == self.zzconfig.prizeGroups.group4.rule:
                        # 至尊礼包的接口与其他奖励接口不一样
                        api = "fcg_prize_lottery"
                    self.do_ark_lottery(api, award.name, award.ruleid, gameid=self.zzconfig.gameid)
        else:
            logger.warning("未配置领取集卡礼包奖励，如果账号【{}】不是小号的话，建议去配置文件打开领取功能【need_take_awards】~".format(self.cfg.name))

        # 消耗卡片来抽奖
        self.try_lottery_using_cards()

    def try_lottery_using_cards(self, print_warning=True):
        if self.enable_cost_all_cards_and_do_lottery():
            if print_warning: logger.warning(color("fg_bold_cyan") + "已开启抽卡活动({})消耗所有卡片来抽奖的功能，若尚未兑换完所有奖励，不建议开启这个功能".format(self.zzconfig.actid))
            card_counts = self.get_card_counts()
            for name, count in card_counts.items():
                self.lottery_using_cards(name, count)
        else:
            if print_warning: logger.warning(color("fg_bold_cyan") + "尚未开启抽卡活动({})消耗所有卡片来抽奖的功能，建议所有礼包都兑换完成后开启该功能，从而充分利用卡片。".format(self.zzconfig.actid))

    def enable_cost_all_cards_and_do_lottery(self):
        return self.cfg.ark_lottery.act_id_to_cost_all_cards_and_do_lottery.get(self.zzconfig.actid, False)

    def lottery_using_cards(self, card_name, count=1):
        if count <= 0:
            return

        logger.info("尝试消耗{}张卡片【{}】来进行抽奖".format(count, card_name))

        card_info_map = parse_card_group_info_map(self.zzconfig)
        ruleid = card_info_map[card_name].lotterySwitchId
        for idx in range(count):
            # 消耗卡片获得抽奖资格
            self.do_ark_lottery("fcg_qzact_present", "增加抽奖次数-消耗卡片({})".format(card_name), ruleid)

            # 抽奖
            self.do_ark_lottery("fcg_prize_lottery", "进行卡片抽奖", self.zzconfig.rules.lotteryByCard, gameid=self.zzconfig.gameid)

    def fetch_lottery_data(self):
        self.lottery_data = self.fetch_data(self.urls.ark_lottery_page)

    def remaining_lottery_times(self):
        self.fetch_lottery_data()

        return self.lottery_data["actCount"]["rule"][str(self.zzconfig.rules.lottery)]["count"][0]['left']

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
        return self.do_qzone_activity(self.zzconfig.actid, api, ctx, ruleid, query, act_name, gameid, area, partition, roleid, pretty, print_res)

    # ----------------- 阿拉德勇士征集令 ----------------------

    def dnf_warriors_call(self):
        # 预取相关数据
        self.fetch_dnf_warriors_call_data()

        zz = self.zz()

        # 抽象一些方法
        def gamePullFlow(ctx):
            return self.do_dnf_warriors_call("v2/fcg_yvip_game_pull_flow", ctx, "", query="0", gameid=zz.gameid, act_name=zz.gameActName)

        def lottery(ctx):
            return self.do_dnf_warriors_call("fcg_prize_lottery", ctx, zz.actbossRule.lottery, gameid=zz.gameid)

        def getPresent(ctx, ruleid):
            return self.do_dnf_warriors_call("fcg_qzact_present", ctx, ruleid)

        def getPrize(ctx, ruleid):
            return self.do_dnf_warriors_call("fcg_receive_reward", ctx, ruleid, gameid=zz.gameid)

        # 实际业务逻辑
        rule = zz.actbossRule

        getPresent("分享成功领取奖励", rule.share1)

        getPrize("报名礼包", rule.registerPackage)

        getPrize("购买vip奖励", rule.buyVipPrize)

        remaining_lottery_times = self.dnf_warriors_call_data.boss.left.get(str(zz.actbossZige.lottery), 0)
        logger.info("剩余抽奖次数为{}次\n(ps: 每周通关两次希洛克可分别获取2次抽奖次数；每天通关一次深渊，可以获得1次抽奖次数)".format(remaining_lottery_times))
        for i in range(remaining_lottery_times):
            lottery("抽奖-第{}次".format(i + 1))

        logger.warning("只处理大家都能领到的普发奖励，像周赛决赛之类的奖励请自行领取")
        getPrize("1. 智慧的引导礼包", rule.pfPrize1)
        getPrize("2. 单人希洛克通关礼包", rule.pfPrize2)

        logger.warning("绑定跨区请自行完成")
        gamePullFlow("1.每日游戏在线30分钟（3分）")
        getPrize("2.特权网吧登陆游戏（1分）", rule.wangba)
        # 刷新一下积分数据
        self.fetch_dnf_warriors_call_data()
        logger.info(color("fg_bold_cyan") + "当前助力积分为{}".format(self.dnf_warriors_call_get_score()))

        if datetime.datetime.now() >= datetime.datetime.strptime('2020-12-26', "%Y-%m-%d"):
            level = self.dnf_warriors_call_get_level()
            if level > 0:
                getPrize("领取宝箱", zz.actbossRule.__getattribute__("getBox{}".format(level)))
                getPrize("开宝箱", zz.actbossRule.__getattribute__("box{}".format(level)))
        else:
            logger.warning("12月26日开始领取宝箱和开宝箱")
        logger.warning("冠军大区奖励请自行领取")

    def dnf_warriors_call_get_level(self):
        score = self.dnf_warriors_call_get_score()

        if score >= 61:
            level = 5
        elif score >= 45:
            level = 4
        elif score >= 31:
            level = 3
        elif score >= 21:
            level = 2
        elif score >= 1:
            level = 1
        else:
            level = 0

        return level

    def dnf_warriors_call_get_score(self):
        return self.dnf_warriors_call_data.boss.left.get(str(self.zz().actbossZige.score), 0)

    def zz(self):
        return self.dnf_warriors_call_data.zz

    def fetch_dnf_warriors_call_data(self):
        self.dnf_warriors_call_raw_data = self.fetch_data(self.urls.dnf_warriors_call_page)
        self.dnf_warriors_call_data = DnfWarriorsCallInfo().auto_update_config(self.dnf_warriors_call_raw_data)

    def do_dnf_warriors_call(self, api, ctx, ruleid, query="", act_name="", gameid="", area="", partition="", roleid="", pretty=False, print_res=True):
        # 活动id为self.dnf_warriors_call_data.zz.actid=4117
        return self.do_qzone_activity(self.zz().actid, api, ctx, ruleid, query, act_name, gameid, area, partition, roleid, pretty, print_res)

    # ----------------- QQ空间活动通用逻辑 ----------------------

    def fetch_data(self, activity_page_url):
        data_prefix = "window.syncData = "
        data_suffix = ";\n</script>"

        def request_fn():
            return requests.post(activity_page_url, headers=self.headers, timeout=self.djc_helper.common_cfg.http_timeout)

        def check_fn(response: requests.Response):
            return data_prefix not in response.text

        res = try_request(request_fn, self.djc_helper.common_cfg.retry)
        page_html = res.text

        prefix_idx = page_html.index(data_prefix) + len(data_prefix)
        suffix_idx = page_html.index(data_suffix, prefix_idx)

        return json.loads(page_html[prefix_idx:suffix_idx])

    def do_qzone_activity(self, actid, api, ctx, ruleid, query="", act_name="", gameid="", area="", partition="", roleid="", pretty=False, print_res=True):
        url = self.urls.qzone_activity.format(
            api=api,
            g_tk=self.g_tk,
            rand=random.random(),
        )
        if self.roleinfo is not None:
            area = area or self.roleinfo.serviceID
            partition = partition or self.roleinfo.serviceID
            roleid = roleid or self.roleinfo.roleCode

        raw_data = self.urls.qzone_activity_raw_data.format(
            actid=actid,
            ruleid=ruleid,
            area=area,
            partition=partition,
            roleid=roleid,
            query=query,
            act_name=act_name,
            gameid=gameid,
            uin=uin2qq(self.lr.uin),
        )

        request_fn = lambda: requests.post(url, raw_data, headers=self.headers, timeout=self.djc_helper.common_cfg.http_timeout)
        res = try_request(request_fn, self.djc_helper.common_cfg.retry)
        logger.debug("{}".format(raw_data))
        return process_result(ctx, res, pretty, print_res)
