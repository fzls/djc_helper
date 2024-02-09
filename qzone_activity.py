import datetime
import json
import random
import time
from typing import Optional

import requests

from config import AccountConfig, CommonConfig
from dao import DnfWarriorsCallInfo, GuanhuaiActInfo, RoleInfo
from log import color, logger
from network import process_result, try_request
from qq_login import LoginResult
from setting import parse_card_group_info_map, parse_prize_list
from setting_def import ArkLotteryZzConfig
from sign import getACSRFTokenForAMS
from urls import Urls, get_not_ams_act
from util import format_now, format_time, parse_time, uin2qq


class QzoneActivity:
    def __init__(self, djc_helper, lr: LoginResult):
        """
        :type djc_helper: DjcHelper
        :type lr: LoginResult
        """
        # 即使没绑定dnf角色，也放行，方便领取分享奖励
        roleinfo: Optional[RoleInfo] = None
        try:
            if "dnf" in djc_helper.bizcode_2_bind_role_map:
                roleinfo = djc_helper.bizcode_2_bind_role_map["dnf"].sRoleInfo
        except Exception:
            pass
        self.roleinfo: Optional[RoleInfo] = roleinfo

        self.djc_helper = djc_helper
        self.lr = lr

        self.cfg: AccountConfig = djc_helper.cfg
        self.common_cfg: CommonConfig = djc_helper.common_cfg
        self.zzconfig: ArkLotteryZzConfig = djc_helper.zzconfig

        self.g_tk = getACSRFTokenForAMS(lr.p_skey)
        self.urls = Urls()
        # 使用QQ空间登录态进行抽卡活动
        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; MIX 2 Build/PKQ1.190118.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045332 Mobile Safari/537.36 V1_AND_SQ_8.4.8_1492_YYB_D QQ/8.4.8.4810 NetType/WIFI WebP/0.3.0 Pixel/1080 StatusBarHeight/76 SimpleUISwitch/0 QQTheme/1000 InMagicWin/0",
            "Cookie": f"p_uin={self.lr.uin}; p_skey={self.lr.p_skey}; ",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

    # ----------------- 集卡活动 ----------------------

    def ark_lottery(self):
        if self.roleinfo is None:
            logger.warning(
                "未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定，否则每日登录游戏和幸运勇士的增加抽卡次数将无法成功进行。"
            )

        # 增加次数
        self.add_ark_lottery_times()

        # 抽卡
        self.draw_ark_lottery()

        # 领取集卡奖励
        self.take_ark_lottery_awards()

        # 消耗卡片来抽奖
        self.try_lottery_using_cards()

    def add_ark_lottery_times(self):
        if self.zzconfig.rules.loginPage != 0:
            self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日登陆页面", self.zzconfig.rules.loginPage)
        self.do_ark_lottery(
            "v2/fcg_yvip_game_pull_flow",
            "增加抽卡次数-每日登陆游戏",
            self.zzconfig.rules.login,
            query="0",
            act_name=self.zzconfig.loginActId,
        )
        self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日分享", self.zzconfig.rules.share)
        if self.zzconfig.rules.video != 0:
            self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日观看直播", self.zzconfig.rules.video)

        # 幸运勇士
        server_id, roleid = "", ""
        if self.cfg.ark_lottery.lucky_dnf_server_id == "":
            logger.warning("未配置抽卡的幸运勇士的区服和角色信息，将使用道聚城绑定的角色信息")
        else:
            if self.cfg.ark_lottery.lucky_dnf_role_id == "":
                logger.warning(
                    f"配置了抽卡幸运勇士的区服ID为{self.cfg.ark_lottery.lucky_dnf_server_id}，但未配置角色ID，将打印该服所有角色信息如下，请将合适的角色ID填到配置表"
                )
                self.djc_helper.query_dnf_rolelist(self.cfg.ark_lottery.lucky_dnf_server_id)
            else:
                logger.info("使用配置的区服和角色信息来进行幸运勇士加次数")
                cfg = self.cfg.ark_lottery
                server_id, roleid = cfg.lucky_dnf_server_id, cfg.lucky_dnf_role_id

        self.do_ark_lottery(
            "v2/fcg_yvip_game_pull_flow",
            "增加抽卡次数-幸运勇士",
            self.zzconfig.rules.imback,
            query="0",
            act_name=self.zzconfig.backActId,
            area=server_id,
            partition=server_id,
            roleid=roleid,
        )

    def draw_ark_lottery(self):
        count = self.remaining_lottery_times()
        logger.info(f"上述操作完毕后，最新抽卡次数为{count}，并开始抽卡~")
        for idx in range(count):
            self.do_ark_lottery("fcg_qzact_lottery", f"抽卡-第{idx + 1}次", self.zzconfig.rules.lottery)

    def take_ark_lottery_awards(self, print_warning=True):
        if self.cfg.ark_lottery.need_take_awards:
            take_awards = parse_prize_list(self.zzconfig)

            for award in take_awards:
                for _idx in range(award.count):
                    api = "fcg_receive_reward"
                    if int(award.ruleid) == self.zzconfig.prizeGroups.group4.rule:
                        # 至尊礼包的接口与其他奖励接口不一样
                        api = "fcg_prize_lottery"
                    self.do_ark_lottery(api, award.name, award.ruleid, gameid=self.zzconfig.gameid)
        else:
            if print_warning:
                logger.warning(
                    f"未配置领取集卡礼包奖励，如果账号【{self.cfg.name}】不是小号的话，建议去配置文件打开领取功能【need_take_awards】~"
                )

    def try_lottery_using_cards(self, print_warning=True):
        if self.enable_cost_all_cards_and_do_lottery():
            if print_warning:
                logger.warning(
                    color("fg_bold_cyan")
                    + f"已开启抽卡活动({self.zzconfig.actid})消耗所有卡片来抽奖的功能，若尚未兑换完所有奖励，不建议开启这个功能"
                )
            if self.roleinfo is None:
                if print_warning:
                    logger.warning(
                        color("fg_bold_cyan") + f"账号 【{self.cfg.name}】 未在道聚城绑定DNF角色信息，无法进行集卡抽奖"
                    )
                return

            card_counts = self.get_card_counts()
            for name, count in card_counts.items():
                self.lottery_using_cards(name, count)
        else:
            if print_warning:
                logger.warning(
                    color("fg_bold_cyan")
                    + f"尚未开启抽卡活动({self.zzconfig.actid})消耗所有卡片来抽奖的功能，建议所有礼包都兑换完成后开启该功能，从而充分利用卡片。"
                )

    def enable_cost_all_cards_and_do_lottery(self):
        if self.common_cfg.cost_all_cards_and_do_lottery_on_last_day and self.is_last_day():
            logger.info("已是最后一天，且配置在最后一天将全部卡片抽掉，故而将开始消耗卡片抽奖~")
            return True

        return self.cfg.ark_lottery.act_id_to_cost_all_cards_and_do_lottery.get(self.zzconfig.actid, False)

    def is_last_day(self) -> bool:
        act_info = get_not_ams_act("集卡")
        day_fmt = "%Y-%m-%d"
        return format_time(parse_time(act_info.dtEndTime), day_fmt) == format_now(day_fmt)

    def lottery_using_cards(self, card_name, count=1):
        if count <= 0:
            return

        logger.info(f"尝试消耗{count}张卡片【{card_name}】来进行抽奖")

        card_info_map = parse_card_group_info_map(self.zzconfig)
        ruleid = card_info_map[card_name].lotterySwitchId
        for _idx in range(count):
            # 消耗卡片获得抽奖资格
            self.do_ark_lottery("fcg_qzact_present", f"增加抽奖次数-消耗卡片({card_name})", ruleid)

            # 抽奖
            self.do_ark_lottery(
                "fcg_prize_lottery", "进行卡片抽奖", self.zzconfig.rules.lotteryByCard, gameid=self.zzconfig.gameid
            )

    def fetch_lottery_data(self):
        self.lottery_data = self.fetch_data(self.urls.ark_lottery_page)

    def remaining_lottery_times(self):
        self.fetch_lottery_data()

        return self.lottery_data["actCount"]["rule"][str(self.zzconfig.rules.lottery)]["count"][0]["left"]

    def get_card_counts(self):
        self.fetch_lottery_data()

        card_counts = {}

        count_map = {}
        if "rule" in self.lottery_data["actCount"]:
            count_map = self.lottery_data["actCount"]["rule"]

        for _group_name, group_info in self.lottery_data["zzconfig"]["cardGroups"].items():
            for cardinfo in group_info["cardList"]:
                ruleid, count_id, name = str(cardinfo["lotterySwitchId"]), cardinfo["id"], cardinfo["name"]

                card_counts[name] = 0
                if ruleid not in count_map:
                    continue

                for count_info in count_map[ruleid]["count"]:
                    if count_info["countid"] == count_id:
                        left = count_info["left"]
                        card_counts[name] = left

        return card_counts

    def get_prize_counts(self):
        self.fetch_lottery_data()

        prize_counts = {}

        count_map = {}
        if "rule" in self.lottery_data["actCount"]:
            count_map = self.lottery_data["actCount"]["rule"]

        for _group_name, group_info in self.lottery_data["zzconfig"]["prizeGroups"].items():
            ruleid, count_id, name = str(group_info["rule"]), group_info["qual"], group_info["title"]

            prize_counts[name] = 0
            if ruleid not in count_map:
                continue

            for count_info in count_map[ruleid]["count"]:
                if count_info["countid"] == count_id:
                    left = count_info["left"]
                    prize_counts[name] = left

        return prize_counts

    def do_ark_lottery(
        self,
        api,
        ctx,
        ruleid,
        query="",
        act_name="",
        gameid="",
        area="",
        partition="",
        roleid="",
        pretty=False,
        print_res=True,
    ):
        return self.do_qzone_activity(
            self.zzconfig.actid,
            api,
            ctx,
            ruleid,
            query,
            act_name,
            gameid,
            area,
            partition,
            roleid,
            "",
            pretty,
            print_res,
        )

    # ----------------- 阿拉德勇士征集令 ----------------------

    def dnf_warriors_call(self):
        # 预取相关数据
        self.fetch_dnf_warriors_call_data()

        zz = self.zz()

        # 抽象一些方法
        def gamePullFlow(ctx):
            return self.do_dnf_warriors_call(
                "v2/fcg_yvip_game_pull_flow", ctx, "", query="0", gameid=zz.gameid, act_name=zz.gameActName
            )

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
        logger.info(
            f"剩余抽奖次数为{remaining_lottery_times}次\n(ps: 每周通关两次希洛克可分别获取2次抽奖次数；每天通关一次深渊，可以获得1次抽奖次数)"
        )
        for i in range(remaining_lottery_times):
            lottery(f"抽奖-第{i + 1}次")

        logger.warning("只处理大家都能领到的普发奖励，像周赛决赛之类的奖励请自行领取")
        getPrize("1. 智慧的引导礼包", rule.pfPrize1)
        getPrize("2. 单人希洛克通关礼包", rule.pfPrize2)

        logger.warning("绑定跨区请自行完成")
        gamePullFlow("1.每日游戏在线30分钟（3分）")
        getPrize("2.特权网吧登陆游戏（1分）", rule.wangba)
        # 刷新一下积分数据
        self.fetch_dnf_warriors_call_data()
        logger.info(color("fg_bold_cyan") + f"当前助力积分为{self.dnf_warriors_call_get_score()}")

        if datetime.datetime.now() >= datetime.datetime.strptime("2020-12-26", "%Y-%m-%d"):
            level = self.dnf_warriors_call_get_level()
            if level > 0:
                getPrize("领取宝箱", zz.actbossRule.__getattribute__(f"getBox{level}"))
                getPrize("开宝箱", zz.actbossRule.__getattribute__(f"box{level}"))
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

    def do_dnf_warriors_call(
        self,
        api,
        ctx,
        ruleid,
        query="",
        act_name="",
        gameid="",
        area="",
        partition="",
        roleid="",
        pretty=False,
        print_res=True,
    ):
        # 活动id为self.dnf_warriors_call_data.zz.actid=4117
        return self.do_qzone_activity(
            self.zz().actid, api, ctx, ruleid, query, act_name, gameid, area, partition, roleid, "", pretty, print_res
        )

    # ----------------- 会员关怀 ----------------------

    # note: 2.0 搜索 actId 确定活动id
    vip_mentor_actId = 4438

    def vip_mentor(self):
        # 当过期的时候，可以去找找看是不是有新的出来了
        #
        # note: 会员关怀接入方式：
        #   1. 浏览器打开活动页面 get_act_url("会员关怀")
        #   2. Sources 中找到 https://qzonestyle.gtimg.cn/qzone/qzact/act/xcube/6865x93954/index.js

        # note: 2.1 搜索 gameAward 定位 j_widget_4/5/6的onclick 领取回归礼包的ruleid和actname
        guanhuai_gifts = [
            GuanhuaiActInfo("", "31264"),
            GuanhuaiActInfo("", "31265"),  # 一般是这个最好
            GuanhuaiActInfo("", "31263"),
        ]
        guanhuai_gift = guanhuai_gifts[self.cfg.vip_mentor.take_index - 1]

        # note: 2.1.1 搜索 distinctActive 看该值为 1 还是 0， 将决定后续流程具体使用什么接口
        guanhuai_distinctActive = "0"

        # note: 2.2 搜索 act_dnf_huoyue_ 定位 增加抽奖次数的ruleid和actname
        add_lottery_times_act_info = GuanhuaiActInfo("act_dnf_huoyue_2", "31267")

        # note: 2.3 搜索 asyncBudget 定位 剩余抽奖次数的countid
        query_lottery_times_countid = "120720"

        # note: 2.4 搜索 gameDraw 定位 抽奖的ruleid
        lottery_ruleid = "31266"

        # note: 2.5.1 将活动添加到实际运行队列中
        # note: 2.5.2 fetch_pskey 中取消注释该开关
        # note: 2.5.3 调整 urls 中活动的时间
        # note: 2.5.4 调整 config_ui.py 中的开关

        def take_guanhuai_gift(ctx):
            cfg = self.cfg.vip_mentor

            # 确认使用的角色
            server_id, roleid = "", ""
            if cfg.guanhuai_dnf_server_id == "":
                logger.warning("未配置会员关怀礼包的区服和角色信息，将使用道聚城绑定的角色信息")
                logger.warning(
                    color("bold_cyan")
                    + "如果大号经常玩，建议去其他跨区建一个小号，然后不再登录，这样日后的关怀活动和集卡活动都可以拿这个来获取回归相关的领取资格"
                )
            else:
                if cfg.guanhuai_dnf_role_id == "":
                    logger.warning(
                        f"配置了会员关怀礼包的区服ID为{cfg.guanhuai_dnf_server_id}，但未配置角色ID，将打印该服所有角色信息如下，请将合适的角色ID填到配置表"
                    )
                    self.djc_helper.query_dnf_rolelist(cfg.guanhuai_dnf_server_id)
                else:
                    logger.info("使用配置的区服和角色信息来进行领取会员关怀礼包")
                    server_id, roleid = cfg.guanhuai_dnf_server_id, cfg.guanhuai_dnf_role_id

            if guanhuai_distinctActive == "0":
                logger.warning(
                    color("bold_cyan")
                    + "本次会员关怀活动不允许获取资格和领取奖励的账号不同，因此若当前QQ未被判定为幸运玩家，则不会领取成功~"
                )

            return _game_award(
                ctx, guanhuai_gift.act_name, guanhuai_gift.ruleid, area=server_id, partition=server_id, roleid=roleid
            )

        def addLotteryTimes(ctx):
            return _game_award(ctx, add_lottery_times_act_info.act_name, add_lottery_times_act_info.ruleid)

        def _game_award(ctx, act_name, ruleid, area="", partition="", roleid=""):
            if guanhuai_distinctActive == "1":
                return self.do_vip_mentor(
                    "v2/fcg_yvip_game_pull_flow",
                    ctx,
                    ruleid,
                    query="0",
                    gameid="dnf",
                    act_name=act_name,
                    area=area,
                    partition=partition,
                    roleid=roleid,
                )
            else:
                return self.do_vip_mentor(
                    "fcg_receive_reward", ctx, ruleid, gameid="dnf", partition=partition, roleid=roleid
                )

        def queryLotteryTimes(ctx):
            res = self.do_vip_mentor("fcg_qzact_count", ctx, "", countid=query_lottery_times_countid, print_res=False)
            countInfo = res["data"]["count"][query_lottery_times_countid]
            return countInfo["left"], countInfo["used"], countInfo["add"]

        def lottery(ctx):
            self.do_vip_mentor("fcg_prize_lottery", ctx, lottery_ruleid, gameid="dnf")
            return

        take_guanhuai_gift(f"尝试领取第{self.cfg.vip_mentor.take_index}个关怀礼包")

        addLotteryTimes("每日登录游戏(+2抽奖机会)")

        left, used, total = queryLotteryTimes("查询抽奖次数信息")
        logger.info(f"剩余抽奖次数={left}，已抽奖次数={used}，累积获取抽奖次数={total}")

        for idx in range(left):
            lottery(f"第{idx + 1}次抽奖，并等待一会")
            time.sleep(5)

    def do_vip_mentor(
        self,
        api,
        ctx,
        ruleid,
        query="",
        act_name="",
        gameid="",
        area="",
        partition="",
        roleid="",
        countid="",
        pretty=False,
        print_res=True,
    ):
        return self.do_qzone_activity(
            self.vip_mentor_actId,
            api,
            ctx,
            ruleid,
            query,
            act_name,
            gameid,
            area,
            partition,
            roleid,
            countid,
            pretty,
            print_res,
        )

    # ----------------- QQ空间活动通用逻辑 ----------------------

    def fetch_data(self, activity_page_url):
        data_prefix = "window.syncData = "
        data_suffix = ";\n</script>"

        def request_fn():
            return requests.post(
                activity_page_url, headers=self.headers, timeout=self.djc_helper.common_cfg.http_timeout
            )

        def check_fn(response: requests.Response):
            return data_prefix not in response.text

        retry_cfg = self.djc_helper.common_cfg.retry
        for _i in range(retry_cfg.max_retry_count):
            try:
                res = try_request(request_fn, self.djc_helper.common_cfg.retry)
                page_html = res.text

                prefix_idx = page_html.index(data_prefix) + len(data_prefix)
                suffix_idx = page_html.index(data_suffix, prefix_idx)

                return json.loads(page_html[prefix_idx:suffix_idx])
            except Exception as e:
                logger.debug("出错了", exc_info=e)
                time.sleep(retry_cfg.retry_wait_time)

        raise Exception("无法正常获取QQ空间活动数据")

    def do_qzone_activity(
        self,
        actid,
        api,
        ctx,
        ruleid,
        query="",
        act_name="",
        gameid="",
        area="",
        partition="",
        roleid="",
        countid="",
        pretty=False,
        print_res=True,
    ):
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
            countid=countid,
        )

        def request_fn():
            return requests.post(url, raw_data, headers=self.headers, timeout=self.djc_helper.common_cfg.http_timeout)

        res = try_request(request_fn, self.djc_helper.common_cfg.retry)
        logger.debug(f"{raw_data}")
        return process_result(ctx, res, pretty, print_res)
