from __future__ import annotations

import datetime
import json
import math
import os
import random
import time
from typing import Any, Callable
from urllib.parse import quote_plus, unquote_plus

import requests

from config import AccountConfig, CommonConfig, config, load_config
from const import cached_dir, guanjia_skey_version
from dao import (
    AmesvrCommonModRet,
    AmesvrQueryFriendsInfo,
    AmesvrQueryRole,
    AmsActInfo,
    BuyInfo,
    DnfCollectionInfo,
    GuanjiaNewLotteryResult,
    GuanjiaNewQueryLotteryInfo,
    GuanjiaNewRequest,
    HuyaActTaskInfo,
    HuyaUserTaskInfo,
    IdeActInfo,
    LuckyUserInfo,
    LuckyUserTaskConf,
    MoJieRenInfo,
    MyHomeFarmInfo,
    MyHomeFriendDetail,
    MyHomeFriendList,
    MyHomeGift,
    MyHomeGiftList,
    MyHomeInfo,
    MyHomeValueGift,
    RankUserInfo,
    RoleInfo,
    SailiyamWorkInfo,
    SpringFuDaiInfo,
    TemporaryChangeBindRoleInfo,
    VoteEndWorkInfo,
    VoteEndWorkList,
    XinyueCatInfo,
    XinyueCatInfoFromApp,
    XinyueCatMatchResult,
    XinyueCatUserInfo,
    XinyueFinancingInfo,
    XinyueWeeklyGiftInfo,
    XinyueWeeklyGPointsInfo,
    parse_amesvr_common_info,
)
from data_struct import to_raw_type
from db import DianzanDB, FireCrackersDB
from djc_helper import DjcHelper
from first_run import is_daily_first_run, is_first_run, is_weekly_first_run
from log import color, logger
from network import check_tencent_game_common_status_code, extract_qq_video_message
from qq_login import LoginResult, QQLogin
from qzone_activity import QzoneActivity
from setting import parse_card_group_info_map, zzconfig
from sign import getACSRFTokenForAMS, getMillSecondsUnix
from urls import get_act_url, get_not_ams_act, search_act
from urls_tomb import UrlsTomb
from usage_count import increase_counter
from util import (
    async_message_box,
    base64_str,
    format_time,
    get_now_unix,
    get_today,
    json_compact,
    md5,
    now_after,
    now_in_range,
    parse_time,
    parse_url_param,
    range_from_one,
    show_end_time,
    show_head_line,
    tableify,
    try_except,
    uin2qq,
    use_by_myself,
    wait_for,
)


# 将几乎可以确定不再会重新上线的活动代码挪到这里，从而减少 djc_helper.py 的行数
class DjcHelperTomb:
    local_saved_guanjia_openid_file = os.path.join(cached_dir, ".saved_guanjia_openid.{}.json")

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
        self.urls = UrlsTomb()

        self.user_buy_info = user_buy_info

        self.zzconfig = zzconfig()

    def expired_activities(self) -> list[tuple[str, Callable]]:
        # re: 记得过期活动全部添加完后，一个个确认下确实过期了
        return [
            ("qq会员杯", self.dnf_club_vip),
            ("集卡_旧版", self.ark_lottery),
            ("qq视频-AME活动", self.qq_video_amesvr),
            ("DNF十三周年庆活动", self.dnf_13),
            ("管家蚊子腿", self.guanjia),
            ("管家蚊子腿", self.guanjia_new),
            ("管家蚊子腿", self.guanjia_new_dup),
            ("DNF强者之路", self.dnf_strong),
            ("会员关怀", self.vip_mentor),
            ("会员关怀", self.dnf_vip_mentor),
            ("DNF福签大作战", self.dnf_fuqian),
            ("燃放爆竹活动", self.firecrackers),
            ("新春福袋大作战", self.spring_fudai),
            ("史诗之路来袭活动合集", self.dnf_1224),
            ("暖冬好礼活动", self.warm_winter),
            ("dnf漂流瓶", self.dnf_drift),
            ("阿拉德勇士征集令", self.dnf_warriors_call),
            ("DNF进击吧赛利亚", self.xinyue_sailiyam),
            ("2020DNF嘉年华页面主页面签到", self.dnf_carnival),
            ("dnf助手排行榜", self.dnf_rank),
            ("10月女法师三觉", self.dnf_female_mage_awaken),
            ("微信签到", self.wx_checkin),
            ("wegame国庆活动【秋风送爽关怀常伴】", self.wegame_guoqing),
            ("虎牙", self.huya),
            ("命运的抉择挑战赛", self.dnf_mingyun_jueze),
            ("轻松之路", self.dnf_relax_road),
            ("WeGameDup", self.dnf_wegame_dup),
            ("qq视频蚊子腿", self.qq_video),
            ("DNF名人堂", self.dnf_vote),
            ("DNF记忆", self.dnf_memory),
            ("关怀活动", self.dnf_guanhuai),
            ("DNF公会活动", self.dnf_gonghui),
            ("WeGame活动_新版", self.wegame_new),
            ("新职业预约活动", self.dnf_reserve),
            ("组队拜年", self.team_happy_new_year),
            ("hello语音（皮皮蟹）网页礼包兑换", self.hello_voice),
            ("翻牌活动", self.dnf_card_flip),
            ("DNF共创投票", self.dnf_dianzan),
            ("DNF互动站", self.dnf_interactive),
            ("心悦猫咪", self.xinyue_cat),
            ("黄钻", self.dnf_yellow_diamond),
            ("KOL", self.dnf_kol),
            ("幸运勇士", self.dnf_lucky_user),
            ("DNF集合站_ide", self.dnf_collection_ide),
            ("我的小屋", self.dnf_my_home),
            ("超享玩", self.super_core),
            ("DNF冒险家之路", self.dnf_maoxian_road),
            ("DNF闪光杯", self.dnf_shanguang),
            ("心悦app周礼包", self.xinyue_weekly_gift),
            ("dnf助手活动Dup", self.dnf_helper_dup),
            ("DNF集合站", self.dnf_collection),
            ("魔界人探险记", self.mojieren),
            ("巴卡尔大作战", self.dnf_bakaer_fight),
            ("巴卡尔对战地图", self.dnf_bakaer_map_ide),
            ("和谐补偿活动", self.dnf_compensate),
            ("DNF巴卡尔竞速", self.dnf_bakaer),
            ("冒险的起点", self.maoxian_start),
            ("心悦app理财礼卡", self.xinyue_financing),
            ("dnf周年拉好友", self.dnf_anniversary_friend),
        ]

    # --------------------------------------------dnf周年拉好友--------------------------------------------
    @try_except()
    def dnf_anniversary_friend(self):
        show_head_line("dnf周年拉好友")
        self.show_amesvr_act_info(self.dnf_anniversary_friend_op)

        if not self.cfg.function_switches.get_dnf_anniversary_friend or self.disable_most_activities():
            logger.warning("未启用领取dnf周年拉好友功能，将跳过")
            return

        self.check_dnf_anniversary_friend()

        self.dnf_anniversary_friend_op("分享领黑钻", "951475")

        self.dnf_anniversary_friend_op("开启新旅程-领取同行奖励（主态）", "952931")

        self.dnf_anniversary_friend_op("抽取光环", "952651")

        self.dnf_anniversary_friend_op("每日任务-通关任意难度【110级地下城】1次", "951752")
        self.dnf_anniversary_friend_op("每日任务-通关任意难度【110级地下城】3次", "952159")
        self.dnf_anniversary_friend_op("每周任务-累计地下城获得【Lv105史诗装备】5件", "952160")

        max_try_count = 4
        for idx in range_from_one(max_try_count):
            res = self.dnf_anniversary_friend_op(f"[{idx}/{max_try_count}] 抽奖", "952537")
            if res["ret"] != "0":
                break

        self.dnf_anniversary_friend_op("随机点亮勇士印记", "952041")

    def check_dnf_anniversary_friend(self):
        self.check_bind_account(
            "dnf周年拉好友",
            get_act_url("dnf周年拉好友"),
            activity_op_func=self.dnf_anniversary_friend_op,
            query_bind_flowid="951473",
            commit_bind_flowid="951472",
        )

    def dnf_anniversary_friend_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_anniversary_friend
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("dnf周年拉好友"),
            **extra_params,
        )

    # --------------------------------------------心悦app理财礼卡--------------------------------------------
    @try_except()
    def xinyue_financing(self):
        show_head_line("心悦app理财礼卡")
        self.show_amesvr_act_info(self.xinyue_financing_op)

        if not self.cfg.function_switches.get_xinyue_financing:
            logger.warning("未启用领取心悦app理财礼卡活动合集功能，将跳过")
            return

        selectedCards = ["升级版月卡", "体验版月卡", "升级版周卡", "体验版周卡"]
        logger.info(color("fg_bold_green") + f"当前设定的理财卡优先列表为: {selectedCards}")

        type2name = {
            "type1": "体验版周卡",
            "type2": "升级版周卡",
            "type3": "体验版月卡",
            "type4": "升级版月卡",
        }

        # ------------- 封装函数 ----------------

        def query_card_taken_map():
            res = AmesvrCommonModRet().auto_update_config(
                self.xinyue_financing_op("查询G分", "409361", print_res=False)["modRet"]
            )
            statusList = res.sOutValue3.split("|")

            cardTakenMap = {}
            for i in range(1, 4 + 1):
                name = type2name[f"type{i}"]
                if int(statusList[i]) > 0:
                    taken = True
                else:
                    taken = False

                cardTakenMap[name] = taken

            return cardTakenMap

        def show_financing_info():
            info_map = get_financing_info_map()

            heads = ["理财卡名称", "当前状态", "累计收益", "剩余天数", "结束日期"]
            colSizes = [10, 8, 8, 8, 10]
            logger.info(color("bold_green") + tableify(heads, colSizes))
            for name, info in info_map.items():
                if name not in selectedCards:
                    # 跳过未选择的卡
                    continue

                if info.buy:
                    status = "已购买"
                else:
                    status = "未购买"

                logger.info(
                    color("fg_bold_cyan")
                    + tableify([name, status, info.totalIncome, info.leftTime, info.endTime], colSizes)
                )

        def get_financing_info_map():
            financingInfoMap: dict = json.loads(
                self.xinyue_financing_op("查询各理财卡信息", "409714", print_res=False)["modRet"]["jData"]["arr"]
            )
            financingTimeInfoMap: dict = json.loads(
                self.xinyue_financing_op("查询理财礼卡天数信息", "409396", print_res=False)["modRet"]["jData"]["arr"]
            )

            info_map = {}
            for typ, financingInfo in financingInfoMap.items():
                info = XinyueFinancingInfo()

                info.name = type2name[typ]
                if financingInfo["status"] == 0:
                    info.buy = False
                else:
                    info.buy = True
                info.totalIncome = financingInfo["totalIncome"]

                if typ in financingTimeInfoMap["alltype"]:
                    info.leftTime = financingTimeInfoMap["alltype"][typ]["leftime"]
                if "opened" in financingTimeInfoMap and typ in financingTimeInfoMap["opened"]:
                    info.endTime = financingTimeInfoMap["opened"][typ]["endtime"]

                info_map[info.name] = info

            return info_map

        # ------------- 正式逻辑 ----------------
        gPoints = self.query_gpoints()
        startPoints = gPoints
        logger.info(f"当前G分为{startPoints}")

        # 活动规则
        # 1、购买理财礼卡：每次购买理财礼卡成功后，当日至其周期结束，每天可以领取相应的收益G分，当日如不领取，则视为放弃
        # 2、购买限制：每个帐号仅可同时拥有两种理财礼卡，到期后则可再次购买
        # ps：推荐购买体验版月卡和升级版月卡
        financingCardsToBuyAndMap = {
            # 名称   购买价格   购买FlowId    领取FlowId
            "体验版周卡": (20, "408990", "507439"),  # 5分/7天/35-20=15/2分收益每天
            "升级版周卡": (80, "409517", "507441"),  # 20分/7天/140-80=60/8.6分收益每天
            "体验版月卡": (300, "409534", "507443"),  # 25分/30天/750-300=450/15分收益每天
            "升级版月卡": (600, "409537", "507444"),  # 60分/30天/1800-600=1200/40分收益每天
        }

        cardInfoMap = get_financing_info_map()
        cardTakenMap = query_card_taken_map()
        for cardName in selectedCards:
            if cardName not in financingCardsToBuyAndMap:
                logger.warning(f"没有找到名为【{cardName}】的理财卡，请确认是否配置错误")
                continue

            buyPrice, buyFlowId, takeFlowId = financingCardsToBuyAndMap[cardName]
            cardInfo = cardInfoMap[cardName]
            taken = cardTakenMap[cardName]
            # 如果尚未购买（或过期），则购买
            if not cardInfo.buy:
                if gPoints >= buyPrice:
                    self.xinyue_financing_op(f"购买{cardName}", buyFlowId)
                    gPoints -= buyPrice
                else:
                    logger.warning(f"积分不够，将跳过购买~，购买{cardName}需要{buyPrice}G分，当前仅有{gPoints}G分")
                    continue

            # 此处以确保购买，尝试领取
            if taken:
                logger.warning(f"今日已经领取过{cardName}了，本次将跳过")
            else:
                self.xinyue_financing_op(f"领取{cardName}", takeFlowId)

        newGPoints = self.query_gpoints()
        delta = newGPoints - startPoints
        logger.warning("")
        logger.warning(
            color("fg_bold_yellow")
            + f"账号 {self.cfg.name} 本次心悦理财礼卡操作共获得 {delta} G分（ {startPoints} -> {newGPoints} ）"
        )
        logger.warning("")

        show_financing_info()

        logger.warning(
            color("fg_bold_yellow")
            + "这个是心悦的活动，不是小助手的剩余付费时长，具体查看方式请读一遍付费指引/付费指引.docx"
        )

    @try_except(return_val_on_except=0, show_exception_info=False)
    def query_gpoints(self):
        res = AmesvrCommonModRet().auto_update_config(
            self.xinyue_financing_op("查询G分", "409361", print_res=False)["modRet"]
        )
        return int(res.sOutValue2)

    def xinyue_financing_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_xinyue_financing

        plat = 3  # app
        extraStr = quote_plus('"mod1":"1","mod2":"0","mod3":"x27"')

        return self.amesvr_request(
            ctx,
            "comm.ams.game.qq.com",
            "xinyue",
            "tgclub",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("心悦app理财礼卡"),
            plat=plat,
            extraStr=extraStr,
            **extra_params,
        )

    # --------------------------------------------冒险的起点--------------------------------------------
    @try_except()
    def maoxian_start(self):
        show_head_line("冒险的起点")
        self.show_amesvr_act_info(self.maoxian_start_op)

        if not self.cfg.function_switches.get_maoxian_start or self.disable_most_activities():
            logger.warning("未启用领取冒险的起点功能，将跳过")
            return

        self.maoxian_start_op("1", "919254")
        self.maoxian_start_op("2", "919256")
        self.maoxian_start_op("3", "919257")
        self.maoxian_start_op("4", "919258")
        self.maoxian_start_op("5", "919259")
        self.maoxian_start_op("6", "919260")
        self.maoxian_start_op("7", "919261")

    def check_maoxian(self):
        self.check_bind_account(
            "冒险的起点",
            get_act_url("冒险的起点"),
            activity_op_func=self.maoxian_start_op,
            query_bind_flowid="919251",
            commit_bind_flowid="919250",
        )

    def maoxian_start_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_maoxian_start
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("冒险的起点"),
            **extra_params,
        )

    # --------------------------------------------DNF巴卡尔竞速--------------------------------------------
    @try_except()
    def dnf_bakaer(self):
        show_head_line("DNF巴卡尔竞速")
        self.show_amesvr_act_info(self.dnf_bakaer_op)

        if not self.cfg.function_switches.get_dnf_bakaer or self.disable_most_activities():
            logger.warning("未启用领取DNF巴卡尔竞速活动合集功能，将跳过")
            return

        self.check_dnf_bakaer()

        def query_info() -> tuple[int, int]:
            res = self.dnf_bakaer_op("查询信息", "928267", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            totat_lottery, current_lottery = raw_info.sOutValue3.split("|")

            return int(totat_lottery), int(current_lottery)

        async_message_box(
            "请手动前往 巴卡尔竞速赛 活动页面进行报名~",
            "巴卡尔竞赛报名",
            open_url=get_act_url("DNF巴卡尔竞速"),
            show_once=True,
        )

        today = get_today()
        self.dnf_bakaer_op(f"7天签到 - {today}", "928281", today=today)

        self.dnf_bakaer_op("见面礼", "928270")
        self.dnf_bakaer_op("回流礼", "928446")
        self.dnf_bakaer_op("心悦专属礼", "929712")

        self.dnf_bakaer_op("绑定送竞猜票", "929213")

        # 投票时间：3月3日0:00-3月17日23:59
        if now_in_range("2023-03-03 00:00:00", "2023-03-10 00:00:00"):
            async_message_box(
                "当前处于巴卡尔竞速赛投票前半段时间，可手动前往活动页面选择你认为会是对应跨区冠军的主播或玩家。若未选择，将会在后半段投票时间随机投票",
                "巴卡尔竞速赛投票提示",
                open_url=get_act_url("DNF巴卡尔竞速"),
                show_once=True,
            )
        elif now_in_range("2023-03-10 00:00:00", "2023-03-17 23:59:59"):
            vote_id_name_list = [
                # 斗鱼主播
                (1, "银雪"),
                (2, "亭宝"),
                (3, "墨羽狼"),
                (4, "素颜"),
                (5, "泣雨"),
                (6, "CEO"),
                (7, "似雨幽离"),
                (8, "丛雨"),
                # 虎牙主播
                (9, "狂人"),
                (10, "小古子"),
                (11, "小炜"),
                (12, "云彩上的翅膀"),
                (13, "东二梦想"),
                (14, "猪猪侠神之手"),
                (15, "仙哥哥"),
                (16, "小勇"),
                # 游戏家俱乐部
                (17, "夜茶会"),
                (18, "清幽茶语"),
                (19, "今夕何年"),
                (20, "黑色恋人"),
                (21, "星梦"),
                (22, "朝九晚五"),
                (23, "天使赞歌"),
                (24, "挚友"),
            ]
            id, name = random.choice(vote_id_name_list)
            logger.info(f"当前到达投票后半段时间，将尝试自动随机投一个 {id} {name}")
            self.dnf_bakaer_op("竞猜", "928617", anchor=id)

        # 领取时间：3月20日10:00~3月22日23:59
        if now_in_range("2023-03-20 00:00:00", "2023-03-22 23:59:59"):
            self.dnf_bakaer_op("竞猜礼包", "928628")

        self.dnf_bakaer_op("登录DNF客户端", "928277")
        self.dnf_bakaer_op("登录心悦俱乐部App", "928559")
        self.dnf_bakaer_op("DNF在线时长30分钟", "928563")
        self.dnf_bakaer_op("分享活动页面", "928570")
        self.dnf_bakaer_op("进入活动页面", "928606")

        totat_lottery, current_lottery = query_info()
        logger.info(f"当前有{current_lottery}张抽奖券, 累积获得 {totat_lottery}")
        for idx in range(current_lottery):
            self.dnf_bakaer_op(f"第{idx + 1}/{current_lottery}次抽奖", "928273")
            if idx != current_lottery:
                time.sleep(5)

    def check_dnf_bakaer(self, roleinfo=None, roleinfo_source="道聚城所绑定的角色"):
        self.check_bind_account(
            "DNF巴卡尔竞速",
            get_act_url("DNF巴卡尔竞速"),
            activity_op_func=self.dnf_bakaer_op,
            query_bind_flowid="928266",
            commit_bind_flowid="928265",
            roleinfo=roleinfo,
            roleinfo_source=roleinfo_source,
        )

    def dnf_bakaer_op(self, ctx, iFlowId, weekDay="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_bakaer

        return self.amesvr_request(
            ctx,
            "act.game.qq.com",
            "xinyue",
            "tgclub",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF巴卡尔竞速"),
            **extra_params,
        )

    # --------------------------------------------和谐补偿活动--------------------------------------------
    @try_except()
    def dnf_compensate(self):
        show_head_line("和谐补偿活动")

        if not self.cfg.function_switches.get_dnf_compensate or self.disable_most_activities():
            logger.warning("未启用领取和谐补偿活动功能，将跳过")
            return

        self.show_amesvr_act_info(self.dnf_compensate_op)

        begin_time = "2023-02-23 10:00:00"
        if now_after(begin_time):
            res = self.dnf_compensate_op("初始化", "929083", print_res=False)
            info = parse_amesvr_common_info(res)

            if info.sOutValue1 != "1":
                self.dnf_compensate_op("补偿奖励", "929042")
            else:
                logger.warning("已经领取过了，不再尝试")
        else:
            logger.warning(f"尚未到补偿领取时间 {begin_time}")

    def dnf_compensate_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_compensate

        roleinfo = self.get_dnf_bind_role()
        checkInfo = self.get_dnf_roleinfo()

        checkparam = quote_plus(quote_plus(checkInfo.checkparam))

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("和谐补偿活动"),
            sRoleId=roleinfo.roleCode,
            sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
            sArea=roleinfo.serviceID,
            sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
            ams_md5str=checkInfo.md5str,
            ams_checkparam=checkparam,
            **extra_params,
        )

    # --------------------------------------------巴卡尔对战地图--------------------------------------------
    @try_except()
    def dnf_bakaer_map_ide(self):
        show_head_line("巴卡尔对战地图")
        self.show_not_ams_act_info("巴卡尔对战地图")

        if not self.cfg.function_switches.get_dnf_bakaer_map or self.disable_most_activities():
            logger.warning("未启用领取 巴卡尔对战地图 功能，将跳过")
            return

        self.check_dnf_bakaer_map_ide()

        self.dnf_bakaer_map_ide_op("领取登录礼包", "164862")
        self.dnf_bakaer_map_ide_op("领取新春地下城礼包", "164879")

    def check_dnf_bakaer_map_ide(self, **extra_params):
        return self.ide_check_bind_account(
            "巴卡尔对战地图",
            get_act_url("巴卡尔对战地图"),
            activity_op_func=self.dnf_bakaer_map_ide_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_bakaer_map_ide_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_bakaer_map

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("巴卡尔对战地图"),
            **extra_params,
        )

    # --------------------------------------------巴卡尔大作战--------------------------------------------
    @try_except()
    def dnf_bakaer_fight(self):
        show_head_line("巴卡尔大作战")
        self.show_amesvr_act_info(self.dnf_bakaer_fight_op)

        if not self.cfg.function_switches.get_dnf_bakaer_fight or self.disable_most_activities():
            logger.warning("未启用领取巴卡尔大作战功能，将跳过")
            return

        self.check_dnf_bakaer_fight()

        boss_info_list = [
            ("邪龙", 1),
            ("狂龙", 3),
            ("冰龙", 2),
            # ("巴卡尔", 4),
        ]
        self.dnf_bakaer_fight_op("选取boss - 优先尝试巴卡尔", "917673", bossId="4")
        # 然后打乱顺序，依次尝试选取各个boss
        random.shuffle(boss_info_list)
        for name, id in boss_info_list:
            time.sleep(3)
            self.dnf_bakaer_fight_op(f"选取boss - {name}", "917673", bossId=id)

        # 个人任务
        self.dnf_bakaer_fight_op("完成登录游戏任务击杀boss", "918026")
        self.dnf_bakaer_fight_op("消耗疲劳值击杀boss", "918098")
        self.dnf_bakaer_fight_op("每日通关推荐地下城", "918099")
        self.dnf_bakaer_fight_op("在线30分钟", "918100")

        # 组队任务
        self.dnf_bakaer_fight_op("组队--分享任务", "918108")
        self.dnf_bakaer_fight_op("组队通关-毁坏的寂静城", "918109")
        self.dnf_bakaer_fight_op("组队通关-天界实验室", "918110")
        self.dnf_bakaer_fight_op("组队通关-110级副本", "918111")

        self.dnf_bakaer_fight_op("掉落邪龙", "918119")
        self.dnf_bakaer_fight_op("掉落冰龙", "918120")
        self.dnf_bakaer_fight_op("掉落狂龙", "918121")
        self.dnf_bakaer_fight_op("掉落巴卡尔", "918122")

        # 奖励提示自行领取
        async_message_box(
            (
                "巴卡尔大作战活动请自行创建攻坚队，或者加入他人的攻坚队，来完成初始流程，否则活动不能正常操作\n"
                "另外，该活动的兑换商店中的奖励请在活动末期自行兑换（小助手会完成领取任务奖励、攻坚成功奖励等操作）\n"
            ),
            "巴卡尔大作战活动提示",
            show_once=True,
            open_url=get_act_url("巴卡尔大作战"),
        )
        # self.dnf_bakaer_fight_op("兑换-第一阶段（加入或创建队伍）", "917672")
        # self.dnf_bakaer_fight_op("兑换-第二阶段（打败任意小boss）", "918113")
        # self.dnf_bakaer_fight_op("兑换-第三阶段（打败所有小boss/解锁大boss）", "918116")
        # self.dnf_bakaer_fight_op("兑换-第四阶段（打败大boss）", "918117")

        act_info = self.dnf_bakaer_fight_op("获取活动信息", "", get_act_info_only=True)
        act_endtime = get_today(parse_time(act_info.dtEndTime))
        logger.info(f"act_endtime={act_endtime}")

        if get_today() == act_endtime:
            async_message_box(
                "当前已是巴卡尔大作战活动最后一天，请在稍后打开的活动页面中自行完成兑换操作",
                "巴卡尔大作战兑换提醒-最后一天",
                open_url=get_act_url("巴卡尔大作战"),
            )

    def check_dnf_bakaer_fight(self):
        self.check_bind_account(
            "巴卡尔大作战",
            get_act_url("巴卡尔大作战"),
            activity_op_func=self.dnf_bakaer_fight_op,
            query_bind_flowid="916892",
            commit_bind_flowid="916891",
        )

    def dnf_bakaer_fight_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_bakaer_fight
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("巴卡尔大作战"),
            **extra_params,
        )

    # --------------------------------------------魔界人探险记--------------------------------------------
    @try_except()
    def mojieren(self):
        # note: 对接新版活动时，记得前往 urls.py 调整活动时间
        show_head_line("魔界人探险记")
        self.show_not_ams_act_info("魔界人探险记")

        if not self.cfg.function_switches.get_mojieren or self.disable_most_activities():
            logger.warning("未启用领取魔界人探险记活动功能，将跳过")
            return

        # re: 根据本次检查绑定具体使用的活动体系决定使用哪个函数
        # check_func = self.check_mojieren
        check_func = self.check_mojieren_amesvr

        @try_except(return_val_on_except=0)
        def query_info() -> MoJieRenInfo:
            wait_for("查询信息", 5)
            raw_res = self.mojieren_op("查询信息(初始化)", "166441", print_res=False)

            return MoJieRenInfo().auto_update_config(raw_res["jData"])

        check_func()

        self.mojieren_op("获取魔方（每日登录）", "165340")
        self.mojieren_op("幸运勇士魔方", "165341")

        for _ in range(10):
            info = query_info()
            logger.info(
                color("bold_green")
                + f"当前位于 第 {info.iCurrRound} 轮 {info.iCurrPos} 格，剩余探索次数为 {info.iMagic}"
            )
            if int(info.iMagic) <= 0:
                break

            self.mojieren_op("开始探险", "165349")

            # self.mojieren_op("更换当前任务", "166416")
            self.mojieren_op("尝试完成任务", "166355")

        info = query_info()

        lottery_times = int(info.iTreasure)
        logger.info(color("bold_cyan") + f"当前剩余夺宝次数为 {lottery_times}")
        for idx in range_from_one(lottery_times):
            self.mojieren_op(f"{idx}/{lottery_times} 奇兵夺宝", "165342")

        logger.info(color("bold_cyan") + f"当前累计完成 {int(info.iCurrRound) - 1} 轮冒险")
        self.mojieren_op("累计完成1轮冒险", "165344")
        self.mojieren_op("累计完成2轮冒险", "165345")
        self.mojieren_op("累计完成3轮冒险", "165346")
        self.mojieren_op("累计完成30次挑战", "165348")

        # logger.info(color("bold_cyan") + f"当前累计完成 {info.iCurrRound} 轮冒险， {info.iExploreTimes} 次探险")
        # accumulative_award_info = [
        #     ("116436", "累计完成1轮冒险", info.jHolds.hold_total_round_1.iLeftNum, int(info.iCurrRound), 1),
        #     ("116437", "累计完成2轮冒险", info.jHolds.hold_total_round_2.iLeftNum, int(info.iCurrRound), 2),
        #     ("116458", "累计完成3轮冒险", info.jHolds.hold_total_round_3.iLeftNum, int(info.iCurrRound), 3),
        #     ("116459", "累计完成30次挑战", info.jHolds.hold_total_adventure.iLeftNum, int(info.iExploreTimes), 30 - 1),
        # ]
        #
        # for flowid, name, iLeftNum, current_val, bounds_val in accumulative_award_info:
        #     if iLeftNum < 1 or current_val <= bounds_val:
        #         logger.warning(f"{name} 条件不满足，当前进度为 {current_val}，剩余领取次数为 {iLeftNum}，需要进度大于 {bounds_val}且有剩余领取次数，将跳过")
        #         continue
        #
        #     self.mojieren_op(name, flowid)

        logger.warning("分享给流失好友可以获取额外夺宝次数，请自行手动完成")
        # self.mojieren_op("关系链数据脱敏", "115858")
        # self.mojieren_op("发送好友ark消息", "115872")
        # self.mojieren_op("接受邀请", "115853")

    def check_mojieren(self, **extra_params):
        return self.ide_check_bind_account(
            "魔界人探险记",
            get_act_url("魔界人探险记"),
            activity_op_func=self.mojieren_op,
            sAuthInfo="SJTZ",
            sActivityInfo="SJTZ",
        )

    def mojieren_op(
        self,
        ctx: str,
        iFlowId: str,
        cardType="",
        inviteId="",
        sendName="",
        receiveUin="",
        receiver="",
        receiverName="",
        receiverUrl="",
        giftNum="",
        p_skey="",
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_mojieren

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("魔界人探险记"),
            cardType=cardType,
            inviteId=inviteId,
            sendName=sendName,
            receiveUin=receiveUin,
            receiver=receiver,
            receiverName=receiverName,
            receiverUrl=receiverUrl,
            giftNum=giftNum,
            **extra_params,
            extra_cookies=f"p_skey={p_skey}",
        )

    def check_mojieren_amesvr(self, **extra_params):
        """有时候马杰洛活动可能绑定走amesvr系统，活动内容走ide，这里做下特殊处理"""
        self.check_bind_account(
            "魔界人探险记",
            get_act_url("魔界人探险记"),
            activity_op_func=self.mojieren_amesvr_op,
            query_bind_flowid="917061",
            commit_bind_flowid="917060",
            **extra_params,
        )

    def mojieren_amesvr_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_mojieren

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("魔界人探险记"),
            **extra_params,
        )

    # --------------------------------------------DNF集合站--------------------------------------------
    @try_except()
    def dnf_collection(self):
        show_head_line("DNF集合站")
        self.show_amesvr_act_info(self.dnf_collection_op)

        if not self.cfg.function_switches.get_dnf_collection or self.disable_most_activities():
            logger.warning("未启用领取DNF集合站功能，将跳过")
            return

        self.check_dnf_collection()

        def query_signin_days() -> int:
            res = self.dnf_collection_op("查询签到天数-condOutput", "916408", print_res=False)
            return self.parse_condOutput(res, "a684eceee76fc522773286a895bc8436")

        def take_return_user_gifts(take_lottery_count_role_info: RoleInfo) -> bool:
            self.dnf_collection_op("回归礼包", "916402")
            time.sleep(5)

            return True

        self.try_do_with_lucky_role_and_normal_role("领取回归礼包", self.check_dnf_collection, take_return_user_gifts)

        self.dnf_collection_op("全民礼包", "916403")

        self.dnf_collection_op("每日在线礼包", "916404")
        # logger.info(color("fg_bold_cyan") + f"当前已累积签到 {query_signin_days()} 天")

        self.dnf_collection_op("签到3天礼包", "916405")
        self.dnf_collection_op("签到7天礼包", "916406")
        self.dnf_collection_op("签到15天礼包", "916407")

    def check_dnf_collection(self, **extra_params):
        self.check_bind_account(
            "DNF集合站",
            get_act_url("DNF集合站"),
            activity_op_func=self.dnf_collection_op,
            query_bind_flowid="916401",
            commit_bind_flowid="916400",
            **extra_params,
        )

    def dnf_collection_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_collection
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF集合站"),
            **extra_params,
        )

    @try_except()
    def dnf_helper_dup(self):
        show_head_line("dnf助手活动Dup")

        if not self.cfg.function_switches.get_dnf_helper or self.disable_most_activities():
            logger.warning("未启用领取dnf助手活动功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.show_amesvr_act_info(self.dnf_helper_dup_op)

        if self.cfg.dnf_helper_info.token == "":
            extra_msg = "未配置dnf助手相关信息，无法进行dnf助手相关活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(
                extra_msg, show_message_box_once_key=f"dnf_helper_{get_act_url('dnf助手活动Dup')}"
            )
            return

        # re: 有些助手活动可能需要绑定流程，有些不需要，看情况来决定下面这句话是否要注释
        # self.check_dnf_helper_dup()

        self.dnf_helper_dup_op("110级普通地下城数据", "919560")
        self.dnf_helper_dup_op("查看贵族机要数据", "919562")
        self.dnf_helper_dup_op("查看毁坏的寂静城数据", "919563")
        self.dnf_helper_dup_op("查看机械七站神实验室数据", "919564")
        self.dnf_helper_dup_op("查看伊斯大陆数据", "919565")
        self.dnf_helper_dup_op("查看趣味数据", "919566")

        self.dnf_helper_dup_op("分享-1", "921006")
        self.dnf_helper_dup_op("分享-2", "919567")

        async_message_box(
            "有兴趣的话，可在助手打开稍后出现的网页，来查看2022年在DNF里的相关数据，比如捡了多少金币，使用了多少金绿柱石",
            "年终总结",
            show_once=True,
            open_url=get_act_url("dnf助手活动Dup"),
        )

    def check_dnf_helper_dup(self):
        self.check_bind_account(
            "dnf助手活动Dup",
            get_act_url("dnf助手活动Dup"),
            activity_op_func=self.dnf_helper_dup_op,
            query_bind_flowid="846972",
            commit_bind_flowid="846971",
        )

    def dnf_helper_dup_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_helper_dup

        roleinfo = self.get_dnf_bind_role()
        qq = self.qq()
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(
            ctx,
            "comm.ams.game.qq.com",
            "group_k",
            "bb",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("dnf助手活动Dup"),
            sArea=roleinfo.serviceID,
            serverId=roleinfo.serviceID,
            sRoleId=roleinfo.roleCode,
            sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
            uin=qq,
            skey=self.cfg.account_info.skey,
            nickName=quote_plus(quote_plus(dnf_helper_info.nickName)),
            userId=dnf_helper_info.userId,
            token=quote_plus(quote_plus(dnf_helper_info.token)),
            **extra_params,
        )

        # 1000017016: 登录态失效,请重新登录
        if (
            res is not None
            and type(res) is dict
            and res["flowRet"]["iRet"] == "700"
            and "登录态失效" in res["flowRet"]["sMsg"]
        ):
            extra_msg = "dnf助手的登录态已过期，目前需要手动更新，具体操作流程如下"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_helper_expired_" + get_today())

            raise RuntimeError("dnf助手token过期，请重试获取")

        return res

    # --------------------------------------------心悦app周礼包--------------------------------------------
    @try_except()
    def xinyue_weekly_gift(self):
        show_head_line("心悦app周礼包")
        self.show_amesvr_act_info(self.xinyue_weekly_gift_op)

        if not self.cfg.function_switches.get_xinyue_weekly_gift:
            logger.warning("未启用领取心悦app周礼包活动合集功能，将跳过")
            return

        def query_info():
            res = self.xinyue_weekly_gift_op("查询信息", "484520", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = XinyueWeeklyGiftInfo()
            info.qq = raw_info.sOutValue1
            info.iLevel = int(raw_info.sOutValue2)
            info.sLevel = raw_info.sOutValue3
            info.tTicket = int(raw_info.sOutValue4) + int(raw_info.sOutValue5)
            info.gift_got_list = raw_info.sOutValue6.split("|")

            return info

        def query_gpoints_info():
            res = self.xinyue_weekly_gift_op("查询G分信息", "603392", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = XinyueWeeklyGPointsInfo()
            info.nickname = unquote_plus(raw_info.sOutValue1)
            info.gpoints = int(raw_info.sOutValue2)

            return info

        @try_except()
        def take_all_gifts():
            # note: 因为已经有一键领取的接口，暂不接入单个领取的接口
            # self.xinyue_weekly_gift_op("领取单个周礼包", "508441", PackId="1")

            self.xinyue_weekly_gift_op("一键领取周礼包", "508440")
            logger.info(
                "这个一键领取接口似乎有时候请求会提示仅限心悦用户参与，实际上任何级别都可以的，一周总有一次会成功的-。-"
            )

        old_gpoints_info = query_gpoints_info()

        take_all_gifts()

        info = query_info()
        logger.info(f"当前剩余免G分抽奖券数目为{info.tTicket}")
        for idx in range(info.tTicket):
            self.xinyue_weekly_gift_op(f"第{idx + 1}/{info.tTicket}次免费抽奖并等待五秒", "603340")
            if idx != info.tTicket - 1:
                time.sleep(5)

        new_gpoints_info = query_gpoints_info()

        delta = new_gpoints_info.gpoints - old_gpoints_info.gpoints
        logger.warning("")
        logger.warning(
            color("fg_bold_yellow")
            + f"账号 {self.cfg.name} 本次心悦周礼包操作共免费抽奖{info.tTicket}次，共获得 {delta} G分（ {old_gpoints_info.gpoints} -> {new_gpoints_info.gpoints} ）"
        )
        logger.warning("")

    def xinyue_weekly_gift_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_xinyue_weekly_gift

        extraStr = quote_plus('"mod1":"1","mod2":"4","mod3":"x48"')

        return self.amesvr_request(
            ctx,
            "act.game.qq.com",
            "xinyue",
            "tgclub",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("心悦app周礼包"),
            extraStr=extraStr,
            **extra_params,
        )

    # --------------------------------------------DNF闪光杯第四期--------------------------------------------
    @try_except()
    def dnf_shanguang(self):
        show_head_line("DNF闪光杯")
        self.show_amesvr_act_info(self.dnf_shanguang_op)

        if not self.cfg.function_switches.get_dnf_shanguang or self.disable_most_activities():
            logger.warning("未启用领取DNF闪光杯活动合集功能，将跳过")
            return

        self.check_dnf_shanguang()

        def check_in():
            today = get_today()
            # last_day = get_today(get_now() - datetime.timedelta(days=1))
            # the_day_before_last_day = get_today(get_now() - datetime.timedelta(days=2))
            self.dnf_shanguang_op(f"签到-{today}", "863326", weekDay=today)
            # self.dnf_shanguang_op(f"补签-{last_day}", "863327", weekDay=last_day)
            # wait_for("等待一会", 5)
            # self.dnf_shanguang_op(f"补签-{the_day_before_last_day}", "863327", weekDay=the_day_before_last_day)

        def query_luck_coin() -> int:
            res = self.dnf_shanguang_op("查询积分", "903560", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue3)

        # --------------------------------------------------------------------------------

        # self.dnf_shanguang_op("报名礼", "724862")
        # self.dnf_shanguang_op("报名礼包", "903566")
        # self.dnf_shanguang_op("app专属礼", "903585")
        async_message_box(
            "请手动前往网页手动报名以及前往心悦app领取一次性礼包",
            f"DNF闪光杯奖励提示_{get_act_url('DNF闪光杯')}",
            show_once=True,
        )

        # # 签到
        # check_in()

        # 周赛奖励
        # week_4 = get_today(get_this_thursday_of_dnf())
        # week_4_to_flowid = {
        #     "20220623": "864758",
        #     "20220630": "864759",
        #     "20220707": "864760",
        # }
        #
        # if week_4 in week_4_to_flowid:
        #     flow_id = week_4_to_flowid[week_4]
        #     self.dnf_shanguang_op(f"领取本周的爆装奖励 - {week_4}", flow_id)
        #     time.sleep(5)

        # act_cycle_list = [
        #     (1, "20221201", "904587"),
        #     (2, "20221208", "906983"),
        #     (3, "20221215", "906997"),
        # ]
        # for week_index, pass_date, settle_flow_id in act_cycle_list:
        #     date = parse_time(pass_date, "%Y%m%d")
        #     if get_now() < date:
        #         logger.warning(f"尚未到 {pass_date}，跳过这部分")
        #         continue
        #
        #     self.dnf_shanguang_op(f"{pass_date} 查询结算结果第 {week_index} 周", settle_flow_id)
        #
        #     for level in range_from_one(10):
        #         res = self.dnf_shanguang_op(
        #             f"{pass_date} 通关难度 {level} 奖励", "907026", **{"pass": level}, pass_date="20221201"
        #         )
        #         if int(res["ret"]) == -1:
        #             break
        #         time.sleep(3)

        awards = [
            # ("2022-11-30 23:59:59", "爆装奖励第1期", "907092"),
            # ("2022-12-07 23:59:59", "爆装奖励第2期", "907095"),
            # ("2022-12-14 23:59:59", "爆装奖励第3期", "907096"),
            ("2022-11-30 23:59:59", "排行榜奖励第1期", "907160"),
            ("2022-12-07 23:59:59", "排行榜奖励第2期", "907161"),
            ("2022-12-14 23:59:59", "排行榜奖励第3期", "907162"),
        ]
        for endtime, name, flowid in awards:
            if not now_after(endtime):
                logger.info(f"{name} 尚未结算，在 {endtime} 之后才能领取，先跳过")
                continue
            self.dnf_shanguang_op(f"{name}", flowid)
            time.sleep(5)

        # 抽奖
        # self.dnf_shanguang_op("每日登录游戏", "903657")
        # self.dnf_shanguang_op("每日登录App", "903665")
        coin = query_luck_coin()
        lottery_count = coin // 10
        logger.info(f"当前积分为 {coin}，可抽奖 {lottery_count} 次")
        for idx in range_from_one(lottery_count):
            res = self.dnf_shanguang_op(f"抽奖 - {idx}", "903590")
            if int(res["ret"]) != 0:
                break
            time.sleep(5)

    def check_dnf_shanguang(self):
        self.check_bind_account(
            "DNF闪光杯",
            get_act_url("DNF闪光杯"),
            activity_op_func=self.dnf_shanguang_op,
            query_bind_flowid="884251",
            commit_bind_flowid="884250",
        )

    def dnf_shanguang_op(self, ctx, iFlowId, weekDay="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_shanguang

        return self.amesvr_request(
            ctx,
            "act.game.qq.com",
            "xinyue",
            "tgclub",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF闪光杯"),
            weekDay=weekDay,
            **extra_params,
        )

    # --------------------------------------------DNF冒险家之路--------------------------------------------
    @try_except()
    def dnf_maoxian_road(self):
        show_head_line("DNF冒险家之路")
        self.show_amesvr_act_info(self.dnf_maoxian_road_op)

        if not self.cfg.function_switches.get_dnf_maoxian_road or self.disable_most_activities():
            logger.warning("未启用领取DNF冒险家之路功能，将跳过")
            return

        self.check_dnf_maoxian_road()

        def query_info() -> tuple[bool, int]:
            res = self.dnf_maoxian_road_op("查询信息", "891421", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            is_lucky_user = raw_info.sOutValue1 != "0"

            temp = raw_info.sOutValue8.split("|")
            ticket = int(temp[0] or 0)

            return is_lucky_user, ticket

        self.dnf_maoxian_road_op("非冒险家一天验证一次", "892232")
        self.dnf_maoxian_road_op("幸运冒险家礼包", "890939")

        is_lucky_user, _ = query_info()
        if not is_lucky_user:
            logger.warning("未抽取到幸运资格，将跳过后续流程")
            return

        # 完成任务
        tasks = [
            # 每日任务
            ("核心用户完成每日任务4 - 通关任意高级地下城1次 - 3图章", "890898"),
            ("核心用户完成每日任务3 - 消耗疲劳值30点 - 2图章", "890897"),
            ("核心用户完成每日任务2 - 通关任意推荐地下城3次 - 2图章", "890888"),
            ("核心用户完成每日任务1 - 游戏在线15分钟 - 1图章", "890887"),
            ("次核心用户完成每日任务4 - 通关任意推荐地下城5次 - 3图章", "890919"),
            ("次核心用户完成每日任务3 - 消耗疲劳值10点 - 2图章", "890918"),
            ("次核心用户完成每日任务2 - 累计在线15分钟 - 2图章", "890907"),
            ("次核心用户完成每日任务1 - 登录游戏 - 1图章", "890906"),
            ("外围用户完成每日任务4 - 消耗疲劳值15点 - 3图章", "890936"),
            ("外围用户完成每日任务3 - 通过任意推荐地下城1次 - 2图章", "890935"),
            ("外围用户完成每日任务2 - 累计在线10分钟 - 2图章", "890923"),
            ("外围用户完成每日任务1 - 登录游戏 - 1图章", "890920"),
            # 累计任务
            ("核心累计进行属性成长/传送/转移10次", "891112"),
            ("核心累计通关任意难度高级地下城3次", "891113"),
            ("核心累计在地下城中获取Lv105史诗装备10件", "891272"),
            ("核心累计通关任意难度高级地下城3天", "891276"),
            ("次核心累计进行属性成长/传送/转移8", "891278"),
            ("次核心累计通关任意难度高级地下城2天", "891279"),
            ("次核心累计通关任意难度110级地下城20次", "891281"),
            ("次核心累计通关任意难度110及地下城3天", "891282"),
            ("外围累计进行属性成长/传送/转移5", "891283"),
            ("外围累计在地下城中获取Lv105史诗装备5", "891284"),
            ("外围累计通关任意难度110级地下城15", "891285"),
            ("外围累计通关任意难度地下城3天", "891287"),
        ]
        for task_name, flowid in tasks:
            self.dnf_maoxian_road_op(task_name, flowid)

        _, ticket = query_info()
        logger.info(color("bold_green") + f"{self.cfg.name} 冒险家之路 当前图章={ticket}")

        awards = [
            ("兑换5—装备提升礼盒—3图章（限2次）", "891293", 5),
            ("兑换1—灿烂的徽章神秘礼盒—25图章（限1次）", "891293", 1),
            ("兑换2—+7装备增幅券—15图章（限1次）", "891293", 2),
            ("兑换6—装备品级调整箱礼盒—3图章（限3次）", "891293", 6),
            # ("兑换3—华丽的徽章神秘礼盒—15图章（限2次）", "891293", 3),
            # ("兑换4—王者契约（1天）—10图章（限2次）", "891293", 4),
            ("兑换1—一次性材质转换器—3图章", "891388", 1),
            # ("兑换2—一次性继承装置—2图章", "891388", 2),
            # ("兑换3—黑钻会员1天—2图章", "891388", 3),
            # ("兑换4—复活币礼盒（1个）—1图章", "891388", 4),
            # ("兑换5—宠物饲料礼袋（10个）—1图章", "891388", 5),
            # ("兑换6—闪亮的雷米援助礼盒—1图章", "891388", 6),
        ]
        for award_name, flowid, exchangeId in awards:
            res = self.dnf_maoxian_road_op(award_name, flowid, exchangeId=exchangeId)
            code = int(res["ret"])
            if code == 700:
                logger.info("当前积分不足以兑换该奖励，将跳过尝试后续优先级更低的奖励")
                break

    def check_dnf_maoxian_road(self):
        self.check_bind_account(
            "DNF冒险家之路",
            get_act_url("DNF冒险家之路"),
            activity_op_func=self.dnf_maoxian_road_op,
            query_bind_flowid="890886",
            commit_bind_flowid="890885",
        )

    def dnf_maoxian_road_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_maoxian_road

        act_url = get_act_url("DNF冒险家之路")
        sChannel = parse_url_param(act_url, "sChannel")

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            act_url,
            **extra_params,
            sChannel=sChannel,
        )

    # --------------------------------------------超享玩--------------------------------------------
    # re: 搜 wpe类活动的接入办法为
    @try_except()
    def super_core(self):
        show_head_line("超享玩")
        self.show_not_ams_act_info("超享玩")

        if not self.cfg.function_switches.get_super_core or self.disable_most_activities():
            logger.warning("未启用领取超享玩功能，将跳过")
            return

        lr = self.fetch_supercore_login_info("获取超享玩所需的access_token")
        self.super_core_set_openid_accesstoken(lr.common_openid, lr.common_access_token)

        self.super_core_op("发送邀约", 40968)
        self.super_core_op("领取邀请奖励", 40979)

        self.super_core_op("解锁进阶战令", 40980)

        return_user_flows = [
            ("我要回归", 44198),
            ("领取回归福利", 40973),
            ("回归玩家解锁进阶战令", 40995),
        ]
        for name, flowid in return_user_flows:
            self.super_core_op(name, flowid)
            time.sleep(3)

        self.super_core_op("每日签到（立即探索）", 40987)

        sign_flows = {
            "普通战令": [
                (1, 40996),
                (3, 41833),
                (5, 41834),
                (7, 41835),
                (10, 41844),
                (12, 41850),
                (14, 41851),
            ],
            "进阶战令": [
                (1, 40993),
                (2, 41837),
                (4, 41838),
                (6, 41840),
                (8, 41857),
                (9, 41860),
                (13, 41890),
                (15, 41893),
            ],
        }
        for bp_name, flow_configs in sign_flows.items():
            for count, flowid in flow_configs:
                res = self.super_core_op(f"尝试领取 {bp_name} 探索 {count} 次 奖励", flowid)
                time.sleep(1)

                if res["msg"] == "探索次数未满足":
                    break

        self.super_core_op("每充值100元获取一把冒险要是", 42322)
        self.super_core_op("抽奖", 42468)

    def super_core_set_openid_accesstoken(self, openid: str, access_token: str):
        self.super_core_extra_headers = {
            "t-account-type": "qc",
            "t-mode": "true",
            "t-appid": "101813972",
            "t-openid": openid,
            "t-access-token": access_token,
        }

    def super_core_op(self, ctx: str, flow_id: int, print_res=True, **extra_params):
        roleinfo = self.get_dnf_bind_role()
        qq = self.qq()

        json_data = {
            "biz_id": "supercore",
            "act_id": 11055,
            "flow_id": flow_id,
            "role": {
                "game_open_id": self.qq(),
                "game_app_id": "",
                "area_id": int(roleinfo.serviceID),
                "plat_id": 2,
                "partition_id": int(roleinfo.serviceID),
                "partition_name": base64_str(roleinfo.serviceName),
                "role_id": roleinfo.roleCode,
                "role_name": base64_str(roleinfo.roleName),
                "device": "pc",
            },
            "data": '{"ceiba_plat_id":"android","user_attach":"{\\"nickName\\":\\"'
            + qq
            + '\\",\\"avatar\\":\\"http://thirdqq.qlogo.cn/g?b=oidb&k=NYXdjtYL9USNU6UZ6QAiapw&s=40&t=1556477786\\"}","cExtData":{}}',
        }

        return self.post(
            ctx,
            self.urls.super_core_api,
            json=json_data,
            print_res=print_res,
            flowId=flow_id,
            extra_headers=self.super_core_extra_headers,
        )

    def fetch_supercore_login_info(self, ctx) -> LoginResult:
        if self.cfg.function_switches.disable_login_mode_supercore:
            logger.warning(f"禁用了爱玩登录模式，将不会尝试更新爱玩 access_token: {ctx}")
            return LoginResult()

        def is_login_info_valid(lr: LoginResult) -> bool:
            self.super_core_set_openid_accesstoken(lr.common_openid, lr.common_access_token)

            # {"data": {}, "msg": "login status verification failed: access token check failed", "ret": 7001}
            res = self.super_core_op(
                "检测access token过期",
                40968,
                print_res=False,
            )
            return res["ret"] != 7001

        return self.fetch_login_result(
            ctx, QQLogin.login_mode_supercore, cache_max_seconds=-1, cache_validate_func=is_login_info_valid
        )

    # --------------------------------------------我的小屋--------------------------------------------
    @try_except()
    def dnf_my_home(self, run_notify_only: bool = False):
        # note: 对接新版活动时，记得前往 urls.py 调整活动时间
        show_head_line("我的小屋")
        self.show_not_ams_act_info("我的小屋")

        if not self.cfg.function_switches.get_dnf_my_home or self.disable_most_activities():
            logger.warning("未启用领取我的小屋活动功能，将跳过")
            return

        self.check_dnf_my_home()

        def query_gifts() -> list[MyHomeGift]:
            raw_res = self.dnf_my_home_op("获取本身小屋宝箱道具", "145628", print_res=False)
            gifts = MyHomeGiftList().auto_update_config(raw_res)

            return gifts.jData

        def query_friend_list(iPage: int) -> MyHomeFriendList:
            raw_res = self.dnf_my_home_op("好友小屋列表", "145827", iPage=iPage, print_res=False)

            return MyHomeFriendList().auto_update_config(raw_res["jData"])

        def query_friend_gift_info(sUin: str) -> list[MyHomeGift]:
            raw_res = self.dnf_my_home_op("好友小屋道具信息", "145664", sUin=sUin, print_res=False)
            if raw_res["ret"] != 0:
                return []

            gifts = MyHomeGiftList().auto_update_config(raw_res)

            return gifts.jData

        def get_friend_detail_list(query_farm_info=True) -> list[MyHomeFriendDetail]:
            friend_detail_list: list[MyHomeFriendDetail] = []

            logger.info("开始查询各个好友的具体信息，方便后续使用")
            # share_p_skey = self.fetch_share_p_skey("我的小屋查询好友", cache_max_seconds=600)
            for friend_page in range_from_one(1000):
                friend_list = query_friend_list(friend_page)
                logger.info(f"开始查看 第 {friend_page}/{friend_list.total} 页的好友的宝箱信息~")
                for friend_info in friend_list.list:
                    detail = MyHomeFriendDetail()
                    detail.page = friend_page
                    detail.info = friend_info
                    detail.gifts = query_friend_gift_info(friend_info.sUin)
                    if query_farm_info:
                        detail.farm_dict = query_friend_farm_dict(friend_info.description(), friend_info.sUin)

                    friend_detail_list.append(detail)

                    time.sleep(0.1)

                if friend_page >= int(friend_list.total):
                    # 已是最后一页
                    break

            logger.info(f"总计获取到 {len(friend_detail_list)} 个好友的小屋信息")

            return friend_detail_list

        @try_except()
        def steal_friend_rice(points: int, friend_detail_list: list[MyHomeFriendDetail]):
            logger.info(
                "去好友的菜地里看看是否可以偷水稻，目前仅偷下列两种\n1. 小号\n2. 没有开满8个田地的，确保不会影响到正常参与的好友"
            )

            myhome_steal_xiaohao_qq_list = self.cfg.myhome_steal_xiaohao_qq_list

            water_reach_max = False
            steal_reach_max = False

            for detail in friend_detail_list:
                for index, farm_info in detail.farm_dict.items():
                    if not farm_info.is_mature():
                        # 未成熟，尝试浇水，方便多偷一次
                        # 规则：6）单账号每日最多可采摘好友水稻3+1次（其中3次每日自动获得，剩下1次通过当日给好友水稻浇水获得），次数与账号绑定；
                        if points >= 10 and not water_reach_max:
                            res = self.dnf_my_home_op(
                                f"尝试帮 好友({detail.info.description()}) 浇水，从而增加一次偷水稻的机会",
                                "145467",
                                sRice=farm_info.sFarmland,
                            )
                            if res["ret"] == 10003:
                                water_reach_max = True
                    else:
                        # 仅尝试偷自己的小号或者未开满八块地的好友
                        if detail.get_qq() not in myhome_steal_xiaohao_qq_list or len(detail.farm_dict) < 8:
                            continue

                        # 已成熟，如果还能被偷，就尝试偷一下
                        if int(farm_info.iNum) >= 6 and not steal_reach_max:
                            res = self.dnf_my_home_op(
                                f"尝试偷 好友({detail.info.description()}) 的水稻",
                                "145489",
                                fieldId=index,
                                sRice=farm_info.sFarmland,
                            )
                            if res["ret"] == 10003:
                                steal_reach_max = True

        def notify_valuable_gifts(current_points: int, valuable_gifts: list[MyHomeValueGift]):
            if len(valuable_gifts) == 0:
                return

            # 按照折扣排序
            def sort_by_discount(value_gift: MyHomeValueGift) -> int:
                return int(value_gift.gift.discount)

            valuable_gifts.sort(key=sort_by_discount)

            gift_desc_list = []
            for g in valuable_gifts:
                gift_desc_list.append(
                    " " * 4
                    + f"第 {g.page} 页 {g.owner} 的宝箱: {g.gift.sPropName} {g.gift.price_after_discount()}({g.gift.format_discount()})"
                )
            gift_descs = "\n".join(gift_desc_list)

            async_message_box(
                (
                    f"{self.cfg.name} 当前拥有积分为 {current_points}，足够兑换下列稀有道具了~\n"
                    f"{gift_descs}\n"
                    "\n"
                    f"如果需要兑换，请使用手机打开稍后的网页，自行兑换~"
                ),
                "我的小屋兑换提示",
                open_url=get_act_url("我的小屋"),
            )

        def try_add_valuable_gift(
            current_points: int,
            valuable_gifts: list[MyHomeValueGift],
            gift: MyHomeGift,
            owner: str,
            page: int,
            s_uin: str,
        ):
            # 提示以下情况的奖励
            # 1. 稀有奖励
            # 2. 额外配置想要的的奖励
            want = gift.is_valuable_gift() or gift.is_extra_wanted(self.cfg.myhome_extra_wanted_gift_name_list)
            if not want:
                return

            if int(gift.iUsedNum) >= int(gift.iTimes):
                # 已超过兑换次数
                return

            # 打印下有稀有奖励的好友的信息，方便分享给别人
            logger.info(
                f"第 {page} 页 可分享小屋 {gift.sPropName}({gift.price_after_discount()}, {gift.format_discount()})({gift.iUsedNum}/{gift.iTimes}) {owner} {s_uin}"
            )

            if gift.is_valuable_gift():
                # 增加上报下稀有小屋信息，活动快结束了，还没兑换的可能不会换了，改为新建一个帖子分享出去
                increase_counter(
                    ga_category=f"小屋分享-v6-{gift.sPropName}",
                    name=f"{gift.format_discount()} {gift.price_after_discount()} {s_uin} ({gift.iUsedNum}/{gift.iTimes}) {owner} ",
                )

            if current_points < gift.price_after_discount():
                # 积分不够
                logger.warning(
                    f"{self.cfg.name} {owner} 的宝箱中有 {gift.sPropName}({gift.price_after_discount()}, {gift.format_discount()}), 但当前积分只有 {current_points}，不够兑换-。-"
                )
                return

            valuable_gifts.append(MyHomeValueGift(page, owner, gift))

        @try_except()
        def notify_exchange_valuable_gift(current_points: int, friend_detail_list: list[MyHomeFriendDetail]):
            # 需要提醒的稀有奖励列表
            valuable_gifts: list[MyHomeValueGift] = []

            # 先看看自己的稀有奖励
            logger.info("今日的宝箱如下:")
            my_gifts = query_gifts()
            for gift in my_gifts:
                logger.info(f"{gift.sPropName}\t{gift.iPoints} 积分")

                try_add_valuable_gift(current_points, valuable_gifts, gift, "自己", 0, "")

            # 然后看看好友的稀有奖励
            logger.info("开始看看好友的小屋里是否有可以兑换的好东西")
            for detail in friend_detail_list:
                for gift in detail.gifts:
                    try_add_valuable_gift(
                        current_points,
                        valuable_gifts,
                        gift,
                        f"{detail.info.sNick}({detail.info.iUin})",
                        detail.page,
                        detail.info.sUin,
                    )

            # 提醒兑换奖励
            notify_valuable_gifts(current_points, valuable_gifts)

        def query_farm_dict() -> dict[str, MyHomeFarmInfo]:
            res = self.dnf_my_home_op("农田初始化(查询信息）", "145364", print_res=False)

            return parse_farm_dict(res)

        def query_friend_farm_dict(friend: str, suin: str) -> dict[str, MyHomeFarmInfo]:
            res = self.dnf_my_home_op(f"查询好友 {friend} 的农田", "149975", sUin=suin, print_res=False)

            return parse_farm_dict(res)

        def parse_farm_dict(raw_res: dict) -> dict[str, MyHomeFarmInfo]:
            data = raw_res["jData"]["list"]

            # 在低于8个田时，返回的是dict，满了的时候是list，所以这里需要特殊处理下
            farm_list: dict[str, MyHomeFarmInfo] = {}
            if type(data) is dict:
                for index, value in data.items():
                    farm_list[str(index)] = MyHomeFarmInfo().auto_update_config(value)
            else:
                for index, value in enumerate(data):
                    farm_list[str(index)] = MyHomeFarmInfo().auto_update_config(value)

            return farm_list

        # 初始化
        info = self.my_home_query_info()
        if int(info.isUser) != 1:
            self.dnf_my_home_op("开通农场", "145251")

        if run_notify_only:
            # 供特别版本使用的特殊流程
            logger.info(color("bold_yellow") + "当前为小屋特别版本，将仅运行提示兑换部分")

            # 预先查询好友信息，方便后续使用
            friend_detail_list = get_friend_detail_list(query_farm_info=False)

            # 统计最新信息
            rice_count = self.my_home_query_rice()
            logger.info(color("bold_yellow") + f"当前稻谷数为 {rice_count}")

            # 提示兑换道具
            notify_exchange_valuable_gift(rice_count, friend_detail_list)
            return

        # 每日任务
        tasks = [
            ("每日登录礼包", "145178"),
            ("分享礼包", "145236"),
            ("在线时长礼包", "145232"),
            ("通关推荐地下城", "145237"),
            ("疲劳消耗礼包", "145245"),
        ]
        for name, flowid in tasks:
            self.dnf_my_home_op(name, flowid)
            time.sleep(5)

        points = self.my_home_query_integral()
        logger.info(color("bold_yellow") + f"当前积分为 {points}")

        # 种田
        # 解锁
        farm_dict = query_farm_dict()
        for iFarmland in range(0, 7 + 1):
            id = str(iFarmland)
            if id not in farm_dict:
                self.dnf_my_home_op(f"尝试解锁农田 - {iFarmland}", "145278", iFarmland=iFarmland)

        # 尝试浇水和收割
        farm_dict = query_farm_dict()
        MAX_FARM_FIELD_COUNT = 8

        for iFarmland in range(0, 7 + 1):
            id = str(iFarmland)
            if id not in farm_dict:
                continue
            fData = farm_dict[id]

            logger.info(f"第 {iFarmland} 块田地成熟时间为 {fData.mature_time()} （是否已成熟: {fData.is_mature()}）")

            if not fData.is_mature():
                # 如果所有田地都已经解锁，此时积分只能用来浇水了
                if len(farm_dict) >= MAX_FARM_FIELD_COUNT and points >= 100:
                    # 保留一定的积分用于给他人浇水，可以多偷一次
                    logger.info(f"尝试给第 {iFarmland} 个田里的水稻浇水")
                    self.dnf_my_home_op(f"尝试给第 {iFarmland} 个田里的水稻浇水", "145398", sRice=fData.sFarmland)
            else:
                self.dnf_my_home_op(
                    f"尝试采摘第 {iFarmland} 个田里的水稻", "145472", fieldId=iFarmland, sRice=fData.sFarmland
                )

        # 邀请好友可以获取刷新次数，这里就不弄了
        # self.dnf_my_home_op("邀请好友开通农场", "145781")
        # self.dnf_my_home_op("接受好友邀请", "145784")
        # self.dnf_my_home_op("待邀请好友列表", "145695")
        # self.dnf_my_home_op("好友已开通农场列表", "145827")

        # 预先查询好友信息，方便后续使用
        friend_detail_list = get_friend_detail_list()

        # 去偷菜
        points = self.my_home_query_integral()
        steal_friend_rice(points, friend_detail_list)

        # 统计最新信息
        rice_count = self.my_home_query_rice()
        logger.info(color("bold_yellow") + f"当前稻谷数为 {rice_count}")

        # 提示兑换道具
        notify_exchange_valuable_gift(rice_count, friend_detail_list)

        act_endtime = parse_time(get_not_ams_act("我的小屋").dtEndTime)
        lastday = get_today(act_endtime)
        if is_weekly_first_run("我的小屋每周兑换提醒") or get_today() == lastday:
            async_message_box(
                "我的小屋活动的兑换选项较多，所以请自行前往网页（手机打开）按需兑换（可以看看自己或者好友的小屋的宝箱，选择需要的东西进行兑换",
                "我的小屋兑换提醒-每周一次或最后一天",
                open_url=get_act_url("我的小屋"),
            )
        # self.dnf_my_home_op("兑换商城道具", "145644")
        # self.dnf_my_home_op("兑换好友商城道具", "145665")

        # 本期不是好友不能添加，所以这个没多大意义了-。-没必要发帖了
        # if use_by_myself():
        #     # re: 最后五天的时候提醒自己建个帖子，开始共享尚未兑换的稀有道具，方便大家都换到自己想要的
        #     #  往上搜索： 小屋分享- 可找到新的谷歌分析的关键词
        #     now = get_now()
        #     if act_endtime - datetime.timedelta(days=5) <= now <= act_endtime:
        #         async_message_box(
        #             (
        #                 "活动最后五天了，像之前一样：\n"
        #                 "1. 发个帖子，介绍进入他人小屋的办法（在 进入小屋 的按钮上右键得到新的代码）\n"
        #                 "2. 发个公告，提前更新文档时间，让大家自行取用\n"
        #                 "2. 这几天每晚10点更新上次那个在线文档，共享上报的稀有道具\n"
        #             ),
        #             "（仅自己可见）参照之前例子，我的小屋发个共享帖子和公告",
        #             open_url="https://bbs.colg.cn/thread-8521654-1-1.html",
        #             show_once_daily=True,
        #         )

        # 抽天3
        res = self.dnf_my_home_op("幸运大奖抽奖", "146374")
        packge_id = int(res["jData"]["iPackageId"] or -1)
        if packge_id == 3486107:
            info = self.my_home_query_info()
            async_message_box(
                f"{self.cfg.name} 抽到了 天3套装礼盒 的兑换资格，可用2000稻谷进行兑换，当前拥有 {info.iRice} 个",
                "抽到大奖了",
            )
        self.dnf_my_home_op("兑换幸运大奖", "146392")

        # 增加数据统计，看看有没有人抽到
        increase_counter(
            ga_category="小屋抽天3套装结果",
            name=str(packge_id),
        )

    def my_home_query_info(self) -> MyHomeInfo:
        raw_res = self.dnf_my_home_op("个人信息", "145985", print_res=False)

        return MyHomeInfo().auto_update_config(raw_res["jData"])

    @try_except(return_val_on_except=0, show_exception_info=False)
    def my_home_query_integral(self) -> int:
        info = self.my_home_query_info()

        return int(info.iTask)

    @try_except(return_val_on_except=0, show_exception_info=False)
    def my_home_query_rice(self) -> int:
        info = self.my_home_query_info()

        return int(info.iRice)

    def check_dnf_my_home(self, **extra_params):
        return self.ide_check_bind_account(
            "我的小屋",
            get_act_url("我的小屋"),
            activity_op_func=self.dnf_my_home_op,
            sAuthInfo="WDXW",
            sActivityInfo="469853",
        )

    def dnf_my_home_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_my_home

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("我的小屋"),
            **extra_params,
        )

    # --------------------------------------------DNF集合站_ide--------------------------------------------
    @try_except()
    def dnf_collection_ide(self):
        show_head_line("DNF集合站_ide")
        self.show_not_ams_act_info("DNF集合站_ide")

        if not self.cfg.function_switches.get_dnf_collection or self.disable_most_activities():
            logger.warning("未启用领取DNF集合站功能，将跳过")
            return

        self.check_dnf_collection_ide()

        self.dnf_collection_ide_op("全民参与礼包", "145889")
        self.dnf_collection_ide_op("幸运party礼包", "145832")

        self.dnf_collection_ide_op("每日在线赢好礼", "145801")

        for count in [3, 7, 15]:
            self.dnf_collection_ide_op(f"累计签到 {count} 天", "146052", dayNum=count)

    def check_dnf_collection_ide(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF集合站_ide",
            get_act_url("DNF集合站_ide"),
            activity_op_func=self.dnf_collection_ide_op,
            sAuthInfo="WDXW",
            sActivityInfo="469853",
        )

    def dnf_collection_ide_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_collection

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF集合站_ide"),
            **extra_params,
        )

    # --------------------------------------------幸运勇士--------------------------------------------
    @try_except()
    def dnf_lucky_user(self):
        show_head_line("幸运勇士")
        self.show_not_ams_act_info("幸运勇士")

        if not self.cfg.function_switches.get_dnf_lucky_user or self.disable_most_activities():
            logger.warning("未启用领取幸运勇士功能，将跳过")
            return

        def query_info() -> LuckyUserInfo:
            res = self.dnf_lucky_user_op("查询信息", "getActConf", print_res=False)

            info = LuckyUserInfo().auto_update_config(res["jData"])

            return info

        def get_task_point(task: LuckyUserTaskConf) -> int:
            # 协调结晶体往后放
            for replace_with_point, not_want in [
                (-2, "闪耀的协调结晶体"),
                (-1, "王者契约"),
            ]:
                if not_want in task.iconName:
                    return replace_with_point

            return int(task.point)

        roleinfo = self.get_dnf_bind_role()

        # 绑定角色
        self.dnf_lucky_user_op("绑定角色", "setRole", iAreaId=roleinfo.serviceID, iRoleId=roleinfo.roleCode)

        # 签到
        self.dnf_lucky_user_op("签到", "doSign")

        # 领取任务奖励
        info = query_info()
        # 优先尝试积分多的
        info.taskConf.sort(key=lambda conf: get_task_point(conf), reverse=True)
        for task in info.taskConf:
            time.sleep(5)
            self.dnf_lucky_user_op(
                f"领取任务奖励 {task.title} {task.iconName} {task.point}积分", "doTask", taskId=task.id
            )

        # 领取积分奖励
        for point in info.pointConf:
            time.sleep(5)
            self.dnf_lucky_user_op(f"领取积分奖励 {point.sGroupName} {point.iconName}", "doPoint", point=point.point)

        # 打印当前信息
        info = query_info()
        logger.info(color("bold_yello") + f"幸运勇士当前积分为 {info.point}, 已签到{info.totalSignNum}天")

    def dnf_lucky_user_op(self, ctx: str, api: str, **params):
        return self.get(
            ctx,
            self.urls.lucky_user,
            api=api,
            randomSeed=math.ceil(random.random() * 10000000),
            **params,
        )

    # --------------------------------------------KOL--------------------------------------------
    @try_except()
    def dnf_kol(self):
        show_head_line("KOL")
        self.show_amesvr_act_info(self.dnf_kol_op)

        if not self.cfg.function_switches.get_dnf_kol or self.disable_most_activities():
            logger.warning("未启用领取KOL功能，将跳过")
            return

        self.check_dnf_kol()

        def query_energy() -> tuple[int, int]:
            res = self.dnf_kol_op("查询信息", "862612", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            total, left = raw_info.sOutValue1.split("|")
            return int(total), int(left)

        # 领取能量值
        self.dnf_kol_op("账号为幸运回归玩家-回流（幸运）玩家主动领取", "863482")
        self.dnf_kol_op("每日登录进入DNF游戏-每日登录", "859926")
        self.dnf_kol_op("每日通关任意地下城3次", "860218")
        self.dnf_kol_op("每日在线", "860216")
        self.dnf_kol_op("每日完成游戏内任意一个任务", "860229")

        for pilao in [50, 100]:
            self.dnf_kol_op(f"每日消耗疲劳点-{pilao}点", "860221", countsInfo=pilao)

        total_energy, left_energy = query_energy()
        logger.info(f"当前累计获得 {total_energy}，剩余票数 {left_energy}")
        for energy in [20, 40, 80, 140, 280, 400]:
            if total_energy >= energy:
                self.dnf_kol_op(f"累积能力值领取礼包 - {energy}", "860366", power=energy)
                time.sleep(5)

        # 邀请回归玩家
        logger.warning("邀请幸运玩家的部分请自行玩家~")
        # self.dnf_kol_op("累积邀请回归用户领取礼包", "861459", inviteNum=1)

        # 能量收集站
        logger.warning("没有大量邀请回归基本不可能领取到排行礼包，请自行完成~")
        # self.dnf_kol_op("领取排行礼包", "863366")

        # 投票
        logger.warning("投票似乎没有奖励，同时为了避免影响原来的分布，请自行按照喜好投票给对应kol")

    def check_dnf_kol(self):
        self.check_bind_account(
            "KOL",
            get_act_url("KOL"),
            activity_op_func=self.dnf_kol_op,
            query_bind_flowid="859628",
            commit_bind_flowid="859627",
        )

    def dnf_kol_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_kol
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("KOL"),
            **extra_params,
        )

    # --------------------------------------------QQ空间黄钻--------------------------------------------
    # note：对接流程与上方 超级会员 dnf_super_vip 完全一致，参照其流程即可
    @try_except()
    def dnf_yellow_diamond(self):
        get_act_url("黄钻")
        show_head_line("QQ空间黄钻")
        self.show_not_ams_act_info("黄钻")

        if not self.cfg.function_switches.get_dnf_yellow_diamond or self.disable_most_activities():
            logger.warning("未启用领取QQ空间黄钻功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.fetch_pskey()
        if self.lr is None:
            return

        lucky_act_id = "66613_2fd7e98b"
        meet_act_id = "66614_23246ef1"
        share_to_other_act_id = "66615_9132410d"
        share_gift_act_id = "66616_44f492ad"

        self.qzone_act_op("幸运勇士礼包 - 当前角色", lucky_act_id)
        self.qzone_act_op(
            "幸运勇士礼包 - 集卡幸运角色",
            lucky_act_id,
            act_req_data=self.try_make_lucky_user_req_data(
                "集卡", self.cfg.ark_lottery.lucky_dnf_server_id, self.cfg.ark_lottery.lucky_dnf_role_id
            ),
        )

        self.qzone_act_op("勇士见面礼", meet_act_id)

        if not self.cfg.function_switches.disable_share and is_first_run(
            f"dnf_yellow_diamond_{get_act_url('黄钻')}_分享_{self.uin()}"
        ):
            self.qzone_act_op(
                "分享给自己",
                share_to_other_act_id,
                act_req_data={
                    "receivers": [
                        self.qq(),
                    ]
                },
            )
        self.qzone_act_op("分享领取礼包", share_gift_act_id)

    # --------------------------------------------心悦猫咪--------------------------------------------
    @try_except()
    def xinyue_cat(self):
        show_head_line("心悦猫咪")
        self.show_amesvr_act_info(self.xinyue_cat_op)

        if not self.cfg.function_switches.get_xinyue_cat:
            logger.warning("未启用领取心悦猫咪活动合集功能，将跳过")
            return

        # --------------- 封装接口 ---------------

        def queryUserInfo():
            res = self.xinyue_cat_op("查询用户信息", "449169", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = XinyueCatUserInfo()
            info.name = unquote_plus(raw_info.sOutValue1.split("|")[0])
            info.gpoints = int(raw_info.sOutValue2)
            info.account = raw_info.sOutValue4
            info.vipLevel = int(raw_info.sOutValue6)
            info.has_cat = raw_info.sOutValue8 == "1"

            return info

        def getPetFinghtInfo():
            res = self.xinyue_cat_op("查询心悦猫咪信息", "532974", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = XinyueCatInfo()
            info.fighting_capacity = int(raw_info.sOutValue1)
            info.yuanqi = int(raw_info.sOutValue2)

            return info

        def get_skin_list():
            return self.xinyue_cat_app_op("查询心悦猫咪皮肤列表", api="get_skin_list")

        def use_skin(skin_id):
            return self.xinyue_cat_app_op("使用皮肤", api="use_skin", skin_id=skin_id)

        def get_decoration_list():
            return self.xinyue_cat_app_op("查询心悦猫咪装饰列表", api="get_decoration_list")

        def use_decoration(decoration_id):
            return self.xinyue_cat_app_op("使用装饰", api="use_decoration", decoration_id=decoration_id)

        def make_money_new(uin, adLevel, adPower):
            return self.xinyue_cat_app_op("历练", api="make_money_new", uin=uin, adLevel=adLevel, adPower=adPower)

        def queryCatInfoFromApp():
            res = self.xinyue_cat_app_op("从app接口查询心悦猫咪信息", api="get_user", print_res=False)
            info = XinyueCatInfoFromApp().auto_update_config(res["data"])

            return info

        def queryPetId():
            return queryCatInfoFromApp().pet_id

        def fight(ctx, username):
            res = self.xinyue_cat_op(f"{ctx}-匹配", "471145")
            wait()

            result = XinyueCatMatchResult().auto_update_config(res["modRet"]["jData"])
            if result.ending == 1:
                self.xinyue_cat_op(f"{ctx}-结算-胜利", "508006", username=quote_plus(username))
            else:
                self.xinyue_cat_op(f"{ctx}-结算-失败", "471383", username=quote_plus(username))

            wait()

        def wait():
            time.sleep(5)

        def get_skin_flowid(skin_id: str) -> str:
            special_skin_id_to_flowid_map = {
                "23": "732492",  # 牛气冲天
                "24": "739668",  # 粉红喵酱
            }

            return special_skin_id_to_flowid_map.get(skin_id, "507986")

        # --------------- 正式逻辑 ---------------

        old_user_info = queryUserInfo()
        old_pet_info = getPetFinghtInfo()

        # 查询相关信息
        if not old_user_info.has_cat:
            self.xinyue_cat_op("领取猫咪", "532871")
        else:
            logger.info("已经领取过猫咪，无需再次领取")

        # 领取历练奖励
        self.xinyue_cat_op("每日首次进入页面增加元气值", "497774")
        self.xinyue_cat_op("领取历练奖励", "532968")

        # 妆容和装饰（小橘子和贤德昭仪）
        petId = queryPetId()
        # skin_id, skin_name = ("24", "粉红喵酱") # 只能领取一次，不再尝试
        skin_id, skin_name = ("8", "贤德昭仪")

        decoration_id, decoration_name = ("7", "小橘子")

        # 尝试购买
        self.xinyue_cat_op(f"G分购买猫咪皮肤-{skin_name}", get_skin_flowid(skin_id), petId=petId, skin_id=skin_id)
        wait()
        self.xinyue_cat_op(f"G分购买装饰-{decoration_name}", "508072", petId=petId, decoration_id=decoration_id)
        wait()

        # 尝试穿戴妆容和装饰
        use_skin(skin_id)
        wait()
        use_decoration(decoration_id)
        wait()

        # 战斗
        pet_info = getPetFinghtInfo()
        total_fight_times = pet_info.yuanqi // 20
        logger.warning(color("fg_bold_yellow") + f"当前元气为{pet_info.yuanqi}，共可进行{total_fight_times}次战斗")
        for i in range(total_fight_times):
            fight(f"第{i + 1}/{total_fight_times}次战斗", old_user_info.name)

        # 历练
        user_info = queryUserInfo()
        pet_info = getPetFinghtInfo()
        for adLevel in [4, 3, 2, 1]:
            make_money_new(user_info.account, adLevel, pet_info.fighting_capacity)

        new_user_info = queryUserInfo()
        new_pet_info = getPetFinghtInfo()

        delta = new_user_info.gpoints - old_user_info.gpoints
        fc_delta = new_pet_info.fighting_capacity - old_pet_info.fighting_capacity
        logger.warning("")
        logger.warning(
            color("fg_bold_yellow")
            + (
                f"账号 {self.cfg.name} 本次心悦猫咪操作共获得 {delta} G分（ {old_user_info.gpoints} -> {new_user_info.gpoints} ）"
                f"，战力增加 {fc_delta}（ {old_pet_info.fighting_capacity} -> {new_pet_info.fighting_capacity} ）"
            )
        )
        logger.warning("")

    def xinyue_cat_app_op(self, ctx, api, skin_id="", decoration_id="", uin="", adLevel="", adPower="", print_res=True):
        return self.get(
            ctx,
            self.urls.xinyue_cat_api,
            api=api,
            skin_id=skin_id,
            decoration_id=decoration_id,
            uin=uin,
            adLevel=adLevel,
            adPower=adPower,
            print_res=print_res,
        )

    def xinyue_cat_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_xinyue_cat

        extraStr = quote_plus('"mod1":"1","mod2":"0","mod3":"x42"')

        return self.amesvr_request(
            ctx,
            "act.game.qq.com",
            "xinyue",
            "tgclub",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("心悦猫咪"),
            extraStr=extraStr,
            **extra_params,
        )

    # --------------------------------------------DNF互动站--------------------------------------------
    @try_except()
    def dnf_interactive(self):
        show_head_line("DNF互动站")
        self.show_amesvr_act_info(self.dnf_interactive_op)

        if not self.cfg.function_switches.get_dnf_interactive or self.disable_most_activities():
            logger.warning("未启用领取DNF互动站功能，将跳过")
            return

        self.check_dnf_interactive()

        if now_after("2022-06-15 20:00:00"):
            self.dnf_interactive_op("TVC（988529）", "859942")
            self.dnf_interactive_op("生日会（988566）", "859976")
            self.dnf_interactive_op("希曼畅玩（988567）", "859977")
            self.dnf_interactive_op("社区（988570）", "859980")
            self.dnf_interactive_op("DNF_IP（988571）", "859982")

        self.dnf_interactive_op("周年庆大礼包（988169）", "859603")

        async_message_box(
            "DNF互动站分享奖励请自行领取，可领一个装备提升礼盒-。-",
            "22.6互动站-分享",
            open_url=get_act_url("DNF互动站"),
            show_once=True,
        )

    def check_dnf_interactive(self):
        self.check_bind_account(
            "DNF互动站",
            get_act_url("DNF互动站"),
            activity_op_func=self.dnf_interactive_op,
            query_bind_flowid="858981",
            commit_bind_flowid="858980",
        )

    def dnf_interactive_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_interactive
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF互动站"),
            **extra_params,
        )

    # --------------------------------------------DNF共创投票--------------------------------------------
    @try_except()
    def dnf_dianzan(self):
        show_head_line("DNF共创投票")
        self.show_amesvr_act_info(self.dnf_dianzan_op)

        if not self.cfg.function_switches.get_dnf_dianzan or self.disable_most_activities():
            logger.warning("未启用领取DNF共创投票活动功能，将跳过")
            return

        self.check_dnf_dianzan()

        def query_info() -> tuple[int, int, int]:
            res = self.dnf_dianzan_op("查询信息", "860276", print_res=False)
            info = parse_amesvr_common_info(res)

            loginGame, playRaid, loginPage, drawTimes = info.sOutValue1.split("|")

            voteTickets, totalGetTickets = info.sOutValue2.split("|")
            voteTimes = int(totalGetTickets) - int(voteTickets)

            return int(voteTickets), int(voteTimes), int(drawTimes)

        def query_work_info_list() -> list[VoteEndWorkInfo]:
            res = self.dnf_dianzan_op("查询投票列表", "860311", print_res=False)
            info = VoteEndWorkList().auto_update_config(res["modRet"]["jData"])

            work_info_list: list[VoteEndWorkInfo] = []
            for workId, tickets in info.data.items():
                work_info = VoteEndWorkInfo()
                work_info.workId = workId
                work_info.tickets = int(tickets)

                work_info_list.append(work_info)

            return work_info_list

        self.dnf_dianzan_op("登陆游戏获取票数（988902）", "860275")
        self.dnf_dianzan_op("通关副本（988956）", "860326")
        self.dnf_dianzan_op("分享（988959）", "860331")

        voteTickets, voteTimes, _ = query_info()
        logger.info(f"已拥有投票次数：{voteTickets} 已完成投票次数：{voteTimes}")
        if voteTickets > 0:
            all_work_info = query_work_info_list()
            work_info_list = random.sample(all_work_info, voteTickets)
            logger.info(f"随机从 {len(all_work_info)} 个最终投票中选 {voteTickets} 个进行投票")

            for work_info in work_info_list:
                self.dnf_dianzan_op(
                    f"投票 - {work_info.workId} (已有投票: {work_info.tickets})", "860300", workId=work_info.workId
                )
                time.sleep(5)

        self.dnf_dianzan_op("投票3次领取（988964）", "860336")

        _, voteTimes, drawTimes = query_info()
        remaining_draw_times = voteTimes - drawTimes
        logger.info(f"累计获得抽奖资格：{voteTimes}次，剩余抽奖次数：{remaining_draw_times}")
        for idx in range_from_one(remaining_draw_times):
            self.dnf_dianzan_op(f"{idx}/{remaining_draw_times} 转盘（988974）", "860346")
            time.sleep(5)

    def check_dnf_dianzan(self):
        self.check_bind_account(
            "DNF共创投票",
            get_act_url("DNF共创投票"),
            activity_op_func=self.dnf_dianzan_op,
            query_bind_flowid="860273",
            commit_bind_flowid="860272",
        )

    def dnf_dianzan_op(self, ctx, iFlowId, sContent="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_dianzan

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF共创投票"),
            **extra_params,
        )

    def old_version_dianzan(self):
        db = DianzanDB().load()
        account_db = DianzanDB().with_context(self.cfg.get_account_cache_key()).load()

        def query_dnf_dianzan():
            res = self.dnf_dianzan_op("查询点赞信息", "725348", print_res=False)
            info = parse_amesvr_common_info(res)

            return int(info.sOutValue1), info.sOutValue2

        # 投票
        def today_dianzan():
            today = get_today()

            if today not in account_db.day_to_dianzan_count:
                account_db.day_to_dianzan_count[today] = 0

            dianzanSuccessCount = account_db.day_to_dianzan_count[today]
            if dianzanSuccessCount >= 20:
                logger.info("今日之前的运行中，已经完成20次点赞了，本次将不执行")
                return

            for contentId in get_dianzan_contents_with_cache():
                # 不论投票是否成功，都标记为使用过的内容
                account_db.used_content_ids.append(contentId)
                if dianzan(dianzanSuccessCount + 1, contentId):
                    dianzanSuccessCount += 1
                    if dianzanSuccessCount >= 20:
                        logger.info("今日已经累计点赞20个，将停止点赞")
                        break

            account_db.day_to_dianzan_count[today] = dianzanSuccessCount

            account_db.save()

        def get_dianzan_contents_with_cache():
            usedContentIds = account_db.used_content_ids

            def filter_used_contents(contentIds):
                validContentIds = []
                for contentId in contentIds:
                    if contentId not in usedContentIds:
                        validContentIds.append(contentId)

                logger.info(validContentIds)

                return validContentIds

            contentIds = db.content_ids

            validContentIds = filter_used_contents(contentIds)

            if len(validContentIds) >= 20:
                # 本地仍有不少于20个内容可供点赞，直接使用本地内容
                return validContentIds

            return filter_used_contents(get_dianzan_contents())

        def get_dianzan_contents():
            logger.info("本地无点赞目标，或缓存的点赞目标均已点赞过，需要重新拉取，请稍后~")
            contentIds = []

            for iCategory2 in range(1, 8 + 1):
                newContentIds, total = getWorksData(iCategory2, 1)
                contentIds.extend(newContentIds)

                # 获取剩余页面
                totalPage = math.ceil(total / 10)
                for page in range(2, totalPage):
                    newContentIds, _ = getWorksData(iCategory2, page)
                    contentIds.extend(newContentIds)

            logger.info(f"获取所有内容ID共计{len(contentIds)}个，将保存到本地，具体如下：{contentIds}")

            def _update_db(var: DianzanDB):
                var.content_ids = contentIds

            db.update(_update_db)

            return contentIds

        def getWorksData(iCategory2, page):
            ctx = f"查询点赞内容-{iCategory2}-{page}"
            res = self.get(
                ctx,
                self.urls.query_dianzan_contents,
                iCategory1=20,
                iCategory2=iCategory2,
                page=page,
                pagesize=10,
                is_jsonp=True,
                is_normal_jsonp=True,
            )
            return [v["iContentId"] for v in res["jData"]["data"]], int(res["jData"]["total"])

        def dianzan(idx, iContentId) -> bool:
            res = self.get(
                f"今日第{idx}次投票，目标为{iContentId}",
                self.urls.dianzan,
                iContentId=iContentId,
                is_jsonp=True,
                is_normal_jsonp=True,
            )
            return int(res["iRet"]) == 0

        totalDianZanCount, _ = query_dnf_dianzan()
        if totalDianZanCount < 200:
            # 进行今天剩余的点赞操作
            today_dianzan()
        else:
            logger.warning("累积投票已经超过200次，无需再投票")

        # 查询点赞信息
        totalDianZanCount, rewardTakenInfo = query_dnf_dianzan()
        logger.warning(
            color("fg_bold_yellow") + f"DNF共创投票活动当前已投票{totalDianZanCount}次，奖励领取状态为{rewardTakenInfo}"
        )

        # 领取点赞奖励
        self.dnf_dianzan_op("累计 10票", "725276")
        self.dnf_dianzan_op("累计 25票", "725340")
        self.dnf_dianzan_op("累计100票", "725341")
        self.dnf_dianzan_op("累计200票", "725342")

    # --------------------------------------------翻牌活动--------------------------------------------
    @try_except()
    def dnf_card_flip(self):
        show_head_line("翻牌活动")
        self.show_amesvr_act_info(self.dnf_card_flip_op)

        if not self.cfg.function_switches.get_dnf_card_flip or self.disable_most_activities():
            logger.warning("未启用领取翻牌活动功能，将跳过")
            return

        self.check_dnf_card_flip()

        def query_info() -> tuple[int, int, int, int]:
            res = self.dnf_card_flip_op("查询信息", "849400", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            integral = int(raw_info.sOutValue1)
            times = int(raw_info.sOutValue2)
            sign = int(raw_info.sOutValue3)

            invited_points = int(raw_info.sOutValue5)

            return integral, times, sign, invited_points

        def query_integral() -> int:
            return query_info()[0]

        def query_times() -> int:
            return query_info()[1]

        def query_signin_days() -> int:
            return query_info()[2]

        def query_card_status() -> list[int]:
            res = self.dnf_card_flip_op("卡片翻转状态", "849048", print_res=False)
            raw_res = parse_amesvr_common_info(res)

            status_list = [int(status) for status in raw_res.sOutValue1.split(",")]

            return status_list

        self.dnf_card_flip_op("每日登录游戏", "849439")
        self.dnf_card_flip_op("每日分享", "849443")

        logger.warning("邀请好友相关内容请自行完成")
        # self.dnf_card_flip_op("允许授权", "849495")
        # self.dnf_card_flip_op("取消授权", "849500")
        # self.dnf_card_flip_op("获取好友列表数据", "849501")
        # self.dnf_card_flip_op("发送好友消息", "849524")
        # self.dnf_card_flip_op("获取邀请积分", "849543")

        integral = query_integral()
        can_change_times = integral // 2
        logger.info(f"当前拥有积分 {integral}， 可兑换翻牌次数 {can_change_times}")
        for idx in range_from_one(can_change_times):
            self.dnf_card_flip_op(f"{idx}/{can_change_times} 积分兑换次数", "849407")

        status_list = query_card_status()
        times = query_times()
        logger.info(f"当前翻牌次数为 {times}")
        if times > 0:
            for idx, status in enumerate(status_list):
                if status == 1:
                    continue

                self.dnf_card_flip_op(f"翻牌 - 第 {idx + 1} 张牌", "848911", iNum=idx + 1)

                times -= 1
                if times <= 0:
                    break

        status_list = query_card_status()
        logger.info(f"最新翻牌状况为 {status_list}")

        self.dnf_card_flip_op("第1行奖励", "849071")
        self.dnf_card_flip_op("第2行奖励", "849170")
        self.dnf_card_flip_op("第3行奖励", "849251")
        self.dnf_card_flip_op("第4行奖励", "849270")
        self.dnf_card_flip_op("第一列奖励", "849284")
        self.dnf_card_flip_op("第二列奖励", "849285")
        self.dnf_card_flip_op("第三列奖励", "849288")
        self.dnf_card_flip_op("第四列奖励", "849289")
        self.dnf_card_flip_op("终极大奖", "849301")

        self.dnf_card_flip_op("每日签到", "849353")
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {query_signin_days()} 天")
        self.dnf_card_flip_op("累计签到3天", "849381")
        self.dnf_card_flip_op("累计签到7天", "849384")
        self.dnf_card_flip_op("累计签到10天", "849385")
        self.dnf_card_flip_op("累计签到15天", "849386")

    def check_dnf_card_flip(self):
        self.check_bind_account(
            "qq视频-翻牌活动",
            get_act_url("翻牌活动"),
            activity_op_func=self.dnf_card_flip_op,
            query_bind_flowid="848910",
            commit_bind_flowid="848909",
        )

    def dnf_card_flip_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_card_flip
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("翻牌活动"),
            **extra_params,
        )

    # --------------------------------------------hello语音（皮皮蟹）奖励兑换--------------------------------------------
    @try_except()
    def hello_voice(self):
        # （从hello语音app中兑换奖励页点开网页）
        show_head_line("hello语音（皮皮蟹）奖励兑换功能（仅兑换，不包含获取奖励的逻辑）")
        self.show_amesvr_act_info(self.hello_voice_op)

        if not self.cfg.function_switches.get_hello_voice or self.disable_most_activities():
            logger.warning("未启用hello语音（皮皮蟹）奖励兑换功能，将跳过")
            return

        if self.cfg.hello_voice.hello_id == "":
            logger.warning("未配置hello_id，若需要该功能，请前往配置文件查看说明并添加该配置")
            return

        self.check_hello_voice()

        def query_coin():
            res = self.hello_voice_op("hello贝查询", "828451", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue1)

        def query_ticket():
            res = self.hello_voice_op("兑换券查询", "828450", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            ticket = sum(int(x) for x in raw_info.sOutValue1.split(","))

            return ticket

        # ------ 专属福利区 ------
        # Hello见面礼
        self.hello_voice_op("hello见面礼包", "828466")
        # hello专属周礼包
        self.hello_voice_op("hello专属周礼包", "828467")
        # hello专属月礼包
        self.hello_voice_op("hello专属月礼包", "828468")
        # hello专属特权礼包
        self.hello_voice_op("兑换券月限礼包_专属特权礼包-1", "828470", "1917676")

        # ------ Hello贝兑换区 ------
        # Hello贝兑换
        logger.info(color("bold_green") + "下面Hello贝可兑换的内容已写死，如需调整，请自行修改源码")
        # self.hello_voice_op("神秘契约礼盒(1天)(150Hello贝)(日限1)", "828469", "1917677")
        # self.hello_voice_op("宠物饲料礼袋(10个)(150Hello贝)(日限1)", "828469", "1917678")
        # self.hello_voice_op("裂缝注视者通行证(150Hello贝)(日限1)", "828469", "1917679")
        # self.hello_voice_op("本职业符文神秘礼盒(高级~稀有)(600Hello贝)(周限1)", "828471", "1917680")
        # self.hello_voice_op("黑钻3天(550Hello贝)(周限1)", "828471", "1917681")
        # self.hello_voice_op("抗疲劳秘药(5点)(300Hello贝)(周限1)", "828471", "1917682")
        # self.hello_voice_op("升级券(550Hello贝)(月限1)", "828472", "1917684")
        self.hello_voice_op("灿烂的徽章神秘礼盒(2000Hello贝)(月限1)", "828472", "1917683")

        # 活动奖励兑换
        logger.info(color("bold_green") + "开始尝试兑换 活动奖励的各个兑换券")
        self.hello_voice_op("时间引导石*20", "828475", "1917685")
        self.hello_voice_op("黑钻3天", "828474", "1917686")
        self.hello_voice_op("复活币礼盒 (1个)", "828475", "1917687")
        self.hello_voice_op("装备品级调整箱礼盒 (1个)", "828540", "1917688")
        self.hello_voice_op("高级材料礼盒", "828475", "1917689")
        self.hello_voice_op("升级券(Lv50~99)", "828475", "1917690")
        self.hello_voice_op("华丽的徽章神秘礼盒", "828475", "1917691")
        self.hello_voice_op("神器护石神秘礼盒", "828475", "1917692")
        self.hello_voice_op("高级装扮兑换券礼盒(无期限)", "828470", "1917693")
        self.hello_voice_op("hello语音专属光环", "828473", "1917694")
        self.hello_voice_op("hello语音专属称号", "828473", "1917695")
        self.hello_voice_op("hello语音专属宠物", "828473", "1917696")

        # 打印最新信息
        logger.info(color("bold_yellow") + f"Hello贝：{query_coin()}    兑换券：{query_ticket()}")

        logger.info(
            color("bold_cyan")
            + "小助手只进行hello语音（皮皮蟹）的奖励领取流程，具体活动任务的完成请手动完成或者使用autojs脚本来实现自动化嗷"
        )

    def check_hello_voice(self):
        self.check_bind_account(
            "hello语音（皮皮蟹）奖励兑换",
            get_act_url("hello语音网页礼包兑换"),
            activity_op_func=self.hello_voice_op,
            query_bind_flowid="828456",
            commit_bind_flowid="828455",
        )

    def hello_voice_op(self, ctx, iFlowId, prize="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_hello_voice

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            "http://dnf.qq.com/cp/a20210312hello/",
            hello_id=self.cfg.hello_voice.hello_id,
            prize=prize,
            **extra_params,
        )

    # --------------------------------------------组队拜年--------------------------------------------
    @try_except()
    def team_happy_new_year(self):
        show_head_line("组队拜年")
        self.show_amesvr_act_info(self.team_happy_new_year_op)

        if not self.cfg.function_switches.get_team_happy_new_year or self.disable_most_activities():
            logger.warning("未启用领取组队拜年功能，将跳过")
            return

        self.check_team_happy_new_year()

        def query_fuqi() -> tuple[int, int]:
            res = self.team_happy_new_year_op("查询信息", "828372", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            personal_fuqi = int(raw_info.sOutValue2)
            team_fuqi = int(raw_info.sOutValue3)

            return personal_fuqi, team_fuqi

        async_message_box(
            "组队拜年活动请自行手动完成组队和邀请回归玩家部分",
            "22组队拜年",
            show_once=True,
        )
        self.team_happy_new_year_op("角色相关信息", "828051")
        # self.team_happy_new_year_op("允许授权", "828055")
        # self.team_happy_new_year_op("取消授权", "828056")
        #
        # self.team_happy_new_year_op("好友列表", "828513")
        # self.team_happy_new_year_op("创建队伍", "828098")
        # self.team_happy_new_year_op("加入队伍", "828147")
        # self.team_happy_new_year_op("加入幸运回归队伍", "828160")
        self.team_happy_new_year_op("拜年队伍信息", "828178")
        self.team_happy_new_year_op("幸运队伍信息", "828181")
        # self.team_happy_new_year_op("邀请幸运队伍", "828319")

        self.team_happy_new_year_op("吉运求签", "827985")
        self.team_happy_new_year_op("吉运福袋", "827995")

        self.team_happy_new_year_op("每日分享", "828009")
        self.team_happy_new_year_op("每日在线30分钟", "828010")
        self.team_happy_new_year_op("每日通关10次地下城", "828013")
        self.team_happy_new_year_op("每日消耗80疲劳", "828019")
        self.team_happy_new_year_op("每日消耗156疲劳", "828020")

        self.team_happy_new_year_op("发送队伍福气", "832768")

        personal_fuqi, team_fuqi = query_fuqi()
        logger.info(color("bold_cyan") + f"当前个人福气为{personal_fuqi}, 队伍福气为 {team_fuqi}")

        remaining_lottery_count = personal_fuqi // 3
        logger.info(f"可进行 {remaining_lottery_count} 次开红包")
        for idx in range_from_one(remaining_lottery_count):
            self.team_happy_new_year_op(f"{idx}/{remaining_lottery_count} 福气红包", "827988")

        team_fuqi_awards = [
            ("828000", 20),
            ("828004", 40),
            ("828005", 60),
            ("828006", 100),
            ("828007", 200),
            ("828008", 300),
        ]
        for flowid, require_count in team_fuqi_awards:
            if team_fuqi >= require_count:
                self.team_happy_new_year_op(f"聚宝盆 {require_count} 福气", flowid)
            else:
                logger.warning(f"当前队伍福气低于 {require_count}，将跳过尝试该奖励")

        self.team_happy_new_year_op("铁蛋（1位）", "828021")
        self.team_happy_new_year_op("铜蛋（2位）", "828022")
        self.team_happy_new_year_op("银蛋（3位）", "828024")
        self.team_happy_new_year_op("金蛋（4位）", "828025")
        self.team_happy_new_year_op("彩蛋（5位）", "828026")
        self.team_happy_new_year_op("喜蛋（6位）", "828027")

    def check_team_happy_new_year(self):
        self.check_bind_account(
            "组队拜年",
            get_act_url("组队拜年"),
            activity_op_func=self.team_happy_new_year_op,
            query_bind_flowid="827994",
            commit_bind_flowid="827993",
        )

    def team_happy_new_year_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_team_happy_new_year
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("组队拜年"),
            **extra_params,
        )

    # --------------------------------------------新职业预约活动--------------------------------------------
    @try_except()
    def dnf_reserve(self):
        show_head_line("新职业预约活动")

        if not self.cfg.function_switches.get_dnf_reserve or self.disable_most_activities():
            logger.warning("未启用领取新职业预约活动功能，将跳过")
            return

        self.show_amesvr_act_info(self.dnf_reserve_op)

        self.check_dnf_reserve()

        act_url = get_act_url("新职业预约活动")
        async_message_box(
            "合金战士的预约礼包需要手动在网页上输入手机号和验证码来进行预约，请手动在稍后弹出的网页上进行~",
            f"手动预约_{act_url}",
            open_url=act_url,
            show_once=True,
        )

        if now_after("2021-12-30 12:00:00"):
            self.dnf_reserve_op("领取预约限定装扮", "820562")

    def check_dnf_reserve(self):
        self.check_bind_account(
            "新职业预约活动",
            get_act_url("新职业预约活动"),
            activity_op_func=self.dnf_reserve_op,
            query_bind_flowid="820923",
            commit_bind_flowid="820922",
        )

    def dnf_reserve_op(self, ctx, iFlowId, p_skey="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_reserve

        roleinfo = self.get_dnf_bind_role()
        checkInfo = self.get_dnf_roleinfo()

        checkparam = quote_plus(quote_plus(checkInfo.checkparam))

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("新职业预约活动"),
            sArea=roleinfo.serviceID,
            sPartition=roleinfo.serviceID,
            sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
            sRoleId=roleinfo.roleCode,
            sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
            md5str=checkInfo.md5str,
            ams_checkparam=checkparam,
            checkparam=checkparam,
            **extra_params,
            extra_cookies=f"p_skey={p_skey}",
        )

    # --------------------------------------------WeGame活动_新版--------------------------------------------
    @try_except()
    def wegame_new(self):
        show_head_line("WeGame活动_新版")
        self.show_not_ams_act_info("WeGame活动_新版")

        if not self.cfg.function_switches.get_wegame_new or self.disable_most_activities():
            logger.warning("未启用领取WeGame活动_新版功能，将跳过")
            return

        if is_daily_first_run("WeGame活动_新版_提示手动领取"):
            async_message_box(
                "新的wegame活动无法自动完成，请每天手动点一点-。- 或者放弃\n"
                + "（此消息每天弹出一次，不想看到的话请把该活动关闭 - WeGame活动_新版）\n",
                "请手动领取",
                open_url="https://act.wegame.com.cn/wand/danji/a20211201DNFCarnival/",
            )

        # self.wegame_new_op_post("测试POST", "Wand-20211206100115-Fde55ab61e52f", json={"url_param": "", "checkLogin": True, "needLogin": False})
        # self.wegame_new_op("测试GET", "Wand-20211208111014-F6568800dd5fb")
        # self.wegame_new_op("测试GET", "Wand-20211208111042-F17b841c3d68e")

    def wegame_new_op(self, ctx: str, flow_id: str, print_res=True, **extra_params):
        api_path = self.format(self.urls.wegame_new_api, flow_id=flow_id)
        sign_content = f"{api_path}&appkey={self.urls.wegame_new_appkey}"
        sign = md5(sign_content)

        signed_url = f"{self.urls.wegame_new_host}{api_path}&s={sign}"
        # note: 有两个参数无法获取，太麻烦了，先不弄了，wand_safecode_str 和 wand_safecode_ticket
        return self.get(
            ctx,
            signed_url,
            print_res=print_res,
            flow_id=flow_id,
            extra_cookies=f"p_uin={self.uin()}; p_skey={self.lr.p_skey}; ",
        )

    def wegame_new_op_post(self, ctx: str, flow_id: str, json=None, print_res=True, **extra_params):
        api_path = self.format(self.urls.wegame_new_api, flow_id=flow_id)
        sign_content = f"{api_path}&appkey={self.urls.wegame_new_appkey}"
        sign = md5(sign_content)

        signed_url = f"{self.urls.wegame_new_host}{api_path}&s={sign}"
        return self.post(
            ctx,
            signed_url,
            json=json,
            print_res=print_res,
            flow_id=flow_id,
            extra_cookies=f"p_uin={self.uin()}; p_skey={self.lr.p_skey};",
        )

    # --------------------------------------------DNF公会活动--------------------------------------------
    @try_except()
    def dnf_gonghui(self):
        show_head_line("DNF公会活动功能")
        self.show_amesvr_act_info(self.dnf_gonghui_op)

        if not self.cfg.function_switches.get_dnf_gonghui or self.disable_most_activities():
            logger.warning("未启用DNF公会活动功能，将跳过")
            return

        self.check_dnf_gonghui()

        def query_huoyue() -> int:
            return int(_query_info().sOutValue2)

        def query_score() -> int:
            return int(_query_info().sOutValue3)

        def _query_info() -> AmesvrCommonModRet:
            res = self.dnf_gonghui_op("查询数据", "814697", print_res=False)
            return parse_amesvr_common_info(res)

        self.dnf_gonghui_op("验证公会信息", "813948")
        self.dnf_gonghui_op("工会验证礼包", "813940")
        # self.dnf_gonghui_op("会长创群礼包", "813943", iQQGroup="iQQGroup")

        self.dnf_gonghui_op("每日分享礼包", "813980")
        self.dnf_gonghui_op("每日在线30分钟礼包", "814012")
        self.dnf_gonghui_op("每日通关10次推荐地下城", "814017")
        self.dnf_gonghui_op("每日消耗100疲劳", "814053")
        self.dnf_gonghui_op("每日消耗156疲劳", "814063")

        logger.info(color("bold_yellow") + f"{self.cfg.name} 当前活跃度为 {query_huoyue()}")
        self.dnf_gonghui_op("活跃值礼包-25", "813951")
        self.dnf_gonghui_op("活跃值礼包-50", "813973")
        self.dnf_gonghui_op("活跃值礼包-75", "813974")
        self.dnf_gonghui_op("活跃值礼包-100", "813975")
        self.dnf_gonghui_op("活跃值礼包-125", "813976")
        self.dnf_gonghui_op("活跃值礼包-150", "813977")
        self.dnf_gonghui_op("活跃值礼包-175", "813978")

        # 兑换奖励
        def exchange_awards():
            awards = [
                ("灿烂的徽章自选礼盒-300 积分", "814067", 1),
                ("次元玄晶碎片礼袋(5个)-180 积分", "814080", 2),
                ("装备提升礼盒-30 积分", "814679", 10),
                ("抗疲劳秘药 (20点)-30 积分", "814675", 5),
                ("抗疲劳秘药 (50点)-180 积分", "814672", 2),
                ("一次性继承装置-80 积分", "814674", 5),
                ("宠物饲料礼袋 (10个)-10 积分", "814682", 30),
                ("华丽的徽章神秘礼盒-10 积分", "814681", 10),
                ("华丽的徽章自选礼盒-80 积分", "814673", 1),
                ("本职业稀有符文神秘礼盒-30 积分", "814677", 8),
                ("裂缝注视者通行证-30 积分", "814678", 10),
                ("复活币礼盒 (1个)-30 积分", "814680", 30),
            ]
            for name, flowid, count in awards:
                for idx in range_from_one(count):
                    ctx = f"第{idx}/{count}次 尝试兑换 {name}"
                    res = self.dnf_gonghui_op(ctx, flowid)
                    msg = res["flowRet"]["sMsg"]
                    if "已经领取过" in msg:
                        break
                    elif "没有足够的积分" in msg:
                        logger.warning(f"当前积分不足以兑换 {name}，将停止尝试后续兑换")
                        return

        total_score = query_score()
        logger.info(color("bold_yellow") + f"当前拥有积分： {total_score}")

        logger.info("先尝试抽奖（若开启）")
        if self.cfg.function_switches.dnf_gonghui_enable_lottery:
            # 每次抽奖需要消耗的10积分
            total_lottery_count = total_score // 10
            logger.info(color("bold_yellow") + f"当前可抽奖次数为： {total_lottery_count}（单次需要10积分）")

            for idx in range_from_one(total_lottery_count):
                self.dnf_gonghui_op(f"第 {idx}/{total_lottery_count} 积分抽奖", "814683")
        else:
            logger.warning("当前未开启积分抽奖，若需要的奖励均已兑换完成，可以打开这个开关")

        logger.info("然后开始尝试按优先级兑换道具")
        exchange_awards()

        # 邀请好友
        async_message_box("工会活动的邀请三个好友并让对方接受邀请，请自行完成，或放弃", "工会活动邀请", show_once=True)
        self.dnf_gonghui_op("信息授权", "814700")
        # self.dnf_gonghui_op("更新邀请登录状态", "817085", sCode="sCode")
        self.dnf_gonghui_op("领取邀请三次好友的盲盒", "814684")

        # if not self.cfg.function_switches.disable_share and is_daily_first_run(f"工会活动邀请_{self.uin()}"):
        #     share_pskey = self.fetch_share_p_skey("工会活动邀请")
        #     extra_cookies = f"p_skey={share_pskey}"
        #
        #     # 这个似乎是固定的，所以直接自己发送吧
        #     self.dnf_gonghui_op("发送邀请信息", "814696", sCode="QQ号码", sNick=quote_plus("QQ昵称"), extra_cookies=extra_cookies)

    def check_dnf_gonghui(self, **extra_params):
        self.check_bind_account(
            "DNF公会活动",
            get_act_url("DNF公会活动"),
            activity_op_func=self.dnf_gonghui_op,
            query_bind_flowid="813939",
            commit_bind_flowid="813938",
            **extra_params,
        )

    def dnf_gonghui_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_gonghui

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF公会活动"),
            **extra_params,
        )

    def old_version_gonghui(self):
        def is_current_bind_character_guild_chairman() -> bool:
            res = self.dnf_gonghui_op("验证公会信息-是否会长", "797992", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue2) == 0

        def guild_chairman_operations(take_lottery_count_role_info: RoleInfo) -> bool:
            if not is_current_bind_character_guild_chairman():
                logger.info(f"角色 {take_lottery_count_role_info.roleName} 不是会长，尝试下一个")
                return True

            self.dnf_gonghui_op("会长三选一", "798256", iGiftID="2")
            self.dnf_gonghui_op("会长每日登陆", "798797")
            self.dnf_gonghui_op("会长次日登录", "798810", iGiftID="2")

            # share_pskey = self.fetch_share_p_skey("领取分享奖励")
            # self.dnf_gonghui_op("发送邀请信息", "798757", sCode=self.qq(), extra_cookies=f"p_skey={share_pskey}")
            self.dnf_gonghui_op("会长邀请三个用户奖励", "798826")

            current_bind_role = self.get_dnf_bind_role_copy()
            if take_lottery_count_role_info.roleCode != current_bind_role.roleCode and is_weekly_first_run(
                "公会活动-会长"
            ):
                async_message_box(
                    f"账号 {self.cfg.name} 由于当前绑定角色 {current_bind_role.roleName} 是普通会员（或未加入公会），不是会长（只有会长角色可以领取这部分奖励，普通会员角色不行），因此临时选择了 {take_lottery_count_role_info.roleName} 来进行领取会长活动的奖励，请自行登录该角色去邮箱领取相应奖励",
                    "领奖通知",
                )

            # 如果这个领取的角色不是道聚城设定的绑定角色，则继续尝试其他的，从而确保所有非绑定角色中符合条件的都会被尝试，这样只要随便从中挑一个来完成对应条件即可
            need_continue = take_lottery_count_role_info.roleCode != current_bind_role.roleCode
            return need_continue

        def guild_member_operations(take_lottery_count_role_info: RoleInfo) -> bool:
            if is_current_bind_character_guild_chairman():
                logger.info(f"角色 {take_lottery_count_role_info.roleName} 不是公会会员，尝试下一个")
                return True

            self.dnf_gonghui_op("会员集结礼包", "798876")
            self.dnf_gonghui_op("会员每日在线30分钟", "798877")
            self.dnf_gonghui_op("会员每日通关3次推荐地下城", "798878")
            self.dnf_gonghui_op("会员消耗疲劳156点", "798879")
            self.dnf_gonghui_op("会员次日登录", "798880")
            self.dnf_gonghui_op("会员分享奖励", "798881")

            current_bind_role = self.get_dnf_bind_role_copy()
            if take_lottery_count_role_info.roleCode != current_bind_role.roleCode and is_weekly_first_run(
                "公会活动-会员"
            ):
                async_message_box(
                    f"账号 {self.cfg.name} 由于当前绑定角色 {current_bind_role.roleName} 是会长（或未加入公会），不是公会会员（只有普通会员角色可以领取这部分奖励，会长角色不行），因此临时选择了 {take_lottery_count_role_info.roleName} 来进行领取公会会员活动的奖励，请自行登录该角色去邮箱领取相应奖励",
                    "领奖通知",
                )

            # 如果这个领取的角色不是道聚城设定的绑定角色，则继续尝试其他的，从而确保所有非绑定角色中符合条件的都会被尝试，这样只要随便从中挑一个来完成对应条件即可
            need_continue = take_lottery_count_role_info.roleCode != current_bind_role.roleCode
            return need_continue

        # 会员活动
        self.temporary_change_bind_and_do(
            "从当前服务器选择一个公会会员角色参与公会会员活动（优先当前绑定角色）",
            self.query_dnf_rolelist_for_temporary_change_bind(role_name=self.cfg.gonghui_rolename_huiyuan),
            self.check_dnf_gonghui,
            guild_member_operations,
            need_try_func=None,
        )

        # 会长活动
        self.temporary_change_bind_and_do(
            "从当前服务器选择一个会长角色参与会长活动（优先当前绑定角色）",
            self.query_dnf_rolelist_for_temporary_change_bind(role_name=self.cfg.gonghui_rolename_huizhang),
            self.check_dnf_gonghui,
            guild_chairman_operations,
            need_try_func=None,
        )

    # --------------------------------------------关怀活动--------------------------------------------
    @try_except()
    def dnf_guanhuai(self):
        show_head_line("关怀活动")
        self.show_amesvr_act_info(self.dnf_guanhuai_op)

        if not self.cfg.function_switches.get_dnf_guanhuai or self.disable_most_activities():
            logger.warning("未启用领取关怀活动功能，将跳过")
            return

        self.check_dnf_guanhuai()

        def take_gifts(take_lottery_count_role_info: RoleInfo) -> bool:
            self.dnf_guanhuai_op("关怀礼包1领取", "813599")
            self.dnf_guanhuai_op("关怀礼包2领取", "813601")
            self.dnf_guanhuai_op("关怀礼包3领取", "813602")

            return True

        self.try_do_with_lucky_role_and_normal_role("领取关怀礼包", self.check_dnf_guanhuai, take_gifts)

        self.dnf_guanhuai_op("领取每日抽奖次数", "813603")
        for idx in range_from_one(2):
            self.dnf_guanhuai_op(f"{idx}/2 关怀抽奖", "813605")

    def check_dnf_guanhuai(self, **extra_params):
        self.check_bind_account(
            "关怀活动",
            get_act_url("关怀活动"),
            activity_op_func=self.dnf_guanhuai_op,
            query_bind_flowid="813595",
            commit_bind_flowid="813594",
            **extra_params,
        )

    def dnf_guanhuai_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_guanhuai
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("关怀活动"),
            **extra_params,
        )

    # --------------------------------------------DNF记忆--------------------------------------------
    @try_except()
    def dnf_memory(self):
        show_head_line("DNF记忆")
        self.show_amesvr_act_info(self.dnf_memory_op)

        if not self.cfg.function_switches.get_dnf_memory or self.disable_most_activities():
            logger.warning("未启用领取DNF记忆功能，将跳过")
            return

        self.check_dnf_memory()

        self.dnf_memory_op("查询数据", "821806")
        self.dnf_memory_op("领取奖励", "821721")

    def check_dnf_memory(self):
        self.check_bind_account(
            "DNF记忆",
            get_act_url("DNF记忆"),
            activity_op_func=self.dnf_memory_op,
            query_bind_flowid="821683",
            commit_bind_flowid="821682",
        )

    def dnf_memory_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_memory
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF记忆"),
            **extra_params,
        )

    # --------------------------------------------DNF名人堂--------------------------------------------
    @try_except()
    def dnf_vote(self):
        show_head_line("DNF名人堂")
        self.show_amesvr_act_info(self.dnf_vote_op)

        if not self.cfg.function_switches.get_dnf_vote or self.disable_most_activities():
            logger.warning("未启用领取DNF名人堂功能，将跳过")
            return

        def query_total_votes() -> int:
            raw_res = self.dnf_vote_op("查询总投票数和是否已经领取奖励", "819043", print_res=False)
            info = parse_amesvr_common_info(raw_res)

            return int(info.sOutValue1)

        votes = [
            (
                "赛事名人堂投票",
                "819048",
                "iMatchId",
                [
                    ("吴琪", "7"),
                    ("丁雪晴", "8"),
                    ("堕落", "9"),
                    ("狗二", "10"),
                    ("庄健", "11"),
                    ("夏法", "12"),
                    ("啊嘟嘟", "13"),
                    ("A酱", "14"),
                ],
            ),
            (
                "游戏名人堂投票",
                "819049",
                "iGameId",
                [
                    ("猪猪侠神之手", "7"),
                    ("银樰不是银雪", "10"),
                    ("晴子", "3"),
                    ("一笑zy", "4"),
                    ("小古子", "1"),
                    ("仙哥哥", "2"),
                    ("dnf冷寨主", "6"),
                    ("杰哥哥", "8"),
                ],
            ),
            (
                "IP名人堂投票",
                "819050",
                "iIPId",
                [
                    ("猪猪侠神之手", "21"),
                    ("快乐游戏酱", "22"),
                    ("美少女希曼", "23"),
                    ("骑乌龟的蜗牛z", "24"),
                    ("聪明的翔老板", "1"),
                    ("巴啦啦暴龙兽", "2"),
                    ("Zimuoo梓陌", "3"),
                    ("爱学习的学习", "4"),
                ],
            ),
        ]

        for vote_name, vote_flowid, vote_id_key, vote_target_info_list in votes:
            for vote_target_name, vote_target_id in vote_target_info_list:
                self.dnf_vote_op(f"{vote_name}-{vote_target_name}", vote_flowid, **{vote_id_key: vote_target_id})

        vote_awards = [
            (48, "819132", "黑钻3天"),
            (96, "819165", "黑钻7天"),
            (144, "819166", "黑钻15天"),
        ]

        total_votes = query_total_votes()
        logger.info(color("bold_yellow") + f"当前累计投票数为 {total_votes}")

        for require_count, flowid, award_name in vote_awards:
            if total_votes >= require_count:
                self.dnf_vote_op(f"投票总次数达到 {require_count} 次，尝试领取 {award_name}", flowid)
            else:
                logger.warning(f"当前投票数未达到 {require_count}, 将不尝试领取 {award_name}")

    def dnf_vote_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_vote
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF名人堂"),
            **extra_params,
        )

    # --------------------------------------------qq视频活动--------------------------------------------
    # note: 接入新qq视频活动的流程如下
    #   1. chrome打开devtools，激活手机模式，并在过滤栏中输入 option=100
    #   2. 打开活动页面 get_act_url("qq视频蚊子腿")
    #   3. 点击任意按钮，从query_string中获取最新的act_id (其实就是上面 magic-act/ 和 /index.html 中间这一串字符
    qq_video_act_id = "yauhs87ql00t63xttwkas8papl"

    #   undone: 如果某个请求的type和option参数不是默认值，也需要专门调整对应值
    qq_video_default_type = "100160"
    qq_video_default_option = "100"

    #   note:4. 依次点击下面各个行为对应的按钮，从query_string中获取最新的module_id
    qq_video_module_id_lucky_user = "xdz8y4sjta4kui1sagp5xzr3qe"  # 幸运勇士礼包
    # qq_video_module_id_first_meet_gift = "zjyk7dlgj23jk7egsofqaj3hk9"  # 勇士见面礼-礼包
    # qq_video_module_id_first_meet_token = "4c43cws9i4721uq01ghu02l3fl"  # 勇士见面礼-令牌
    qq_video_module_id_lottery = "9fi2o28r621y1t78l8oyoefzr9"  # 每日抽奖1次(需在活动页面开通QQ视频会员)
    qq_video_module_id_online_30_minutes = "93fas34ug2wo36oce0a9el97au"  # 在线30分钟
    qq_video_module_id_online_3_days = "wwq8suj7d9qi7ee9gcy89r3d2e"  # 累积3天
    qq_video_module_id_online_7_days = "jsk57d87y5ap3wto879g8jpslu"  # 累积7天
    qq_video_module_id_online_15_days = "wtckr8zcrk6egcc9iq5lygq98l"  # 累积15天

    qq_video_module_id_card_gift_list = [
        # ID | 描述 | 兑换次数
        ("e9goi51gh5tgww9kkhtcw2ft21", "使用 6 张卡兑换奖励", 1),
        ("2gu4g11pj9freyx94ad7hyi3t9", "使用 4 张卡兑换奖励", 10),
        ("dasw19eds0fjxaew64pxc2sgt9", "使用 2 张卡兑换奖励", 10),
    ]

    #   note:6. 以下的请求则是根据现有的代码中对应参数，刷新页面过滤出对应请求
    qq_video_module_id_query_card_info = "h4y1k5ggeecx9whygr72eutfle"  # 查询卡片信息

    qq_video_module_id_enter_page = "f2e07oo7faaidezzgo5cs25pce"  # 首次进入页面
    qq_video_module_id_take_enter_page_card = "r9c9zkrg272f0ttsyp9groiy5u"  # 领取进入页面的卡片

    @try_except()
    def qq_video(self):
        show_head_line("qq视频活动")
        self.show_not_ams_act_info("qq视频蚊子腿")

        if not self.cfg.function_switches.get_qq_video or self.disable_most_activities():
            logger.warning("未启用领取qq视频活动功能，将跳过")
            return

        self.check_qq_video()

        @try_except()
        def query_card_info(ctx):
            show_head_line(ctx, msg_color=color("bold_cyan"))

            res = self.qq_video_op(
                "查询卡片信息",
                self.qq_video_module_id_query_card_info,
                option="111",
                type="71",
                is_prepublish="0",
                print_res=False,
            )

            heads = ["名称", "数目"]
            colSizes = [20, 4]
            logger.info(tableify(heads, colSizes))
            for card in res["do_act"]["score_list"]:
                cols = [card["score_name"], card["score_num"]]
                logger.info(tableify(cols, colSizes))

        # 正式逻辑
        self.qq_video_op("首次进入页面", self.qq_video_module_id_enter_page, type="51", option="1", task="51")
        self.qq_video_op("领取页面卡片", self.qq_video_module_id_take_enter_page_card, type="59", option="1")

        self.qq_video_op("幸运勇士礼包", self.qq_video_module_id_lucky_user)
        logger.info(
            color("bold_cyan")
            + "上面的这个幸运角色可以使用其他区服的回归角色进行领取，不过这样的话其实也只有黑钻可以被当前角色用到-。-所以有兴趣的就自己去页面上操作下吧，这里就不额外做了（懒。。。"
        )

        # self.qq_video_op("勇士见面礼-礼包", self.qq_video_module_id_first_meet_gift)
        # self.qq_video_op("勇士见面礼-令牌", self.qq_video_module_id_first_meet_token)

        self.qq_video_op("每日抽奖1次(需在活动页面开通QQ视频会员)", self.qq_video_module_id_lottery, type="100143")

        self.qq_video_op("在线30分钟", self.qq_video_module_id_online_30_minutes)
        self.qq_video_op("累积3天", self.qq_video_module_id_online_3_days)
        self.qq_video_op("累积7天", self.qq_video_module_id_online_7_days, type="100143")
        self.qq_video_op("累积10天", self.qq_video_module_id_online_15_days, type="100143")

        logger.warning(
            "如果【在线30分钟】提示你未在线30分钟，但你实际已在线超过30分钟，也切换过频道了，不妨试试退出游戏，有时候在退出游戏的时候才会刷新这个数据"
        )

        # 首先尝试按照优先级领取
        for module_id, gift_name, exchange_count in self.qq_video_module_id_card_gift_list:
            res = self.qq_video_op(f"{gift_name}（限 {exchange_count} 次）", module_id)
            # -904 条件不满足
            # -903 已经领了没有资格再领了
            if res["ret"] == -904:
                logger.info(f"尚未兑换 {gift_name}，先跳过其他礼包")
                break

        # 如果到了最后一天，就尝试领取所有可以领取的奖励
        actInfo = get_not_ams_act("qq视频蚊子腿")
        if format_time(parse_time(actInfo.dtEndTime), "%Y%m%d") == get_today():
            logger.info("已到活动最后一天，尝试领取所有可以领取的奖励")
            for module_id, gift_name, exchange_count in self.qq_video_module_id_card_gift_list:
                for idx in range_from_one(exchange_count):
                    res = self.qq_video_op(f"[{idx}/{exchange_count}] {gift_name}", module_id)
                    if res["ret"] != 0:
                        break

        # 查询一遍集卡信息
        query_card_info("最新卡片信息")

    def check_qq_video(self):
        while True:
            res = self.qq_video_op("幸运勇士礼包", self.qq_video_module_id_lucky_user, print_res=True)
            if res["ret"] == -904 and res["msg"] == "您当前还未绑定游戏帐号，请先绑定哦~":
                self.guide_to_bind_account("qq视频蚊子腿", get_act_url("qq视频蚊子腿"), activity_op_func=None)
                continue

            return res

    def qq_video_op(self, ctx, module_id, option="", type="", task="", is_prepublish="", print_res=True):
        # 设置下默认值
        option = option or self.qq_video_default_option
        type = type or self.qq_video_default_type

        res = self._qq_video_op(ctx, type, option, module_id, task, is_prepublish, print_res)

        if (
            "data" in res
            and int(res["data"].get("sys_code", res["ret"])) == -1010
            and extract_qq_video_message(res) == "系统错误"
        ):
            msg = "【需要修复这个】不知道为啥这个操作失败了，试试连上fiddler然后手动操作看看请求哪里对不上"
            logger.warning(color("fg_bold_yellow") + msg)

        return res

    def _qq_video_op(self, ctx, type, option, module_id, task, is_prepublish, print_res=True):
        extra_cookies = "; ".join(
            [
                "",
                "appid=3000501",
                "main_login=qq",
                f"vuserid={self.get_vuserid()}",
            ]
        )
        return self.get(
            ctx,
            self.urls.qq_video,
            type=type,
            option=option,
            act_id=self.qq_video_act_id,
            module_id=module_id,
            task=task,
            is_prepublish=is_prepublish,
            print_res=print_res,
            extra_cookies=extra_cookies,
        )

    # --------------------------------------------WeGame活动--------------------------------------------
    @try_except()
    def dnf_wegame_dup(self):
        show_head_line("WeGameDup")
        self.show_amesvr_act_info(self.dnf_wegame_dup_op)

        if not self.cfg.function_switches.get_dnf_wegame or self.disable_most_activities():
            logger.warning("未启用领取WeGame活动功能，将跳过")
            return

        self.check_dnf_wegame_dup()

        # def query_signin_days():
        #     res = self.dnf_wegame_dup_op("查询签到天数-condOutput", "808092", print_res=False)
        #     info = parse_amesvr_common_info(res)
        #     # "sOutValue1": "e0c747b4b51392caf0c99162e69125d8:iRet:0|b1ecb3ecd311175835723e484f2d8d88:iRet:0",
        #     parts = info.sOutValue1.split('|')[0].split(':')
        #     days = int(parts[2])
        #     return days

        def query_lottery_times(count_id: int):
            res = self.dnf_wegame_dup_op("查询抽奖次数-jifenOutput", "808091", print_res=False)
            return self.parse_jifenOutput(res, str(count_id))

        self.dnf_wegame_dup_op("惊喜见面礼", "808069")

        self.dnf_wegame_dup_op("页面签到获取盲盒", "808073")
        self.dnf_wegame_dup_op("在线30分钟获得盲盒", "808074")
        self.dnf_wegame_dup_op("通关奥兹玛团本获得盲盒", "808075")
        self.dnf_wegame_dup_op("wegame专区关注主播", "808082")
        self.dnf_wegame_dup_op("wegame专区关注作者", "808083")
        totalLotteryTimes, remainingLotteryTimes = query_lottery_times(362)
        logger.info(
            color("bold_yellow")
            + f"累计获得{totalLotteryTimes}次吹蜡烛次数，目前剩余{remainingLotteryTimes}次吹蜡烛次数"
        )
        for i in range(remainingLotteryTimes):
            self.dnf_wegame_dup_op(f"第{i + 1}次 盲盒抽奖", "808072")

        self.dnf_wegame_dup_op("观看视频抽奖", "808071")
        self.dnf_wegame_dup_op("wegame启动游戏获得抽奖券", "808079")
        self.dnf_wegame_dup_op("通关3次裂缝副本获得抽奖券", "808080")
        self.dnf_wegame_dup_op("通关命运抉择5-5", "808081")
        totalLotteryTimes, remainingLotteryTimes = query_lottery_times(363)
        logger.info(
            color("bold_yellow") + f"累计获得{totalLotteryTimes}次抽奖次数，目前剩余{remainingLotteryTimes}次抽奖次数"
        )
        for i in range(remainingLotteryTimes):
            self.dnf_wegame_dup_op(f"第{i + 1}次每日抽奖(惊喜转盘)", "808084")

        def take_award_with_34c(role: RoleInfo) -> bool:
            self.dnf_wegame_dup_op("34C满级奖励", "808076")
            self.dnf_wegame_dup_op("34C通关希洛克奖励", "808265")
            self.dnf_wegame_dup_op("34C通关奥兹玛奖励", "808266")

            return True

        if self.cfg.take_award_34c_server_id != "" and self.cfg.take_award_34c_role_id != "":
            change_bind_role = TemporaryChangeBindRoleInfo()
            change_bind_role.serviceID = self.cfg.take_award_34c_server_id
            change_bind_role.roleCode = self.cfg.take_award_34c_role_id

            self.temporary_change_bind_and_do(
                "使用配置的34C领取奖励", [change_bind_role], self.check_dnf_wegame_dup, take_award_with_34c
            )
        else:
            logger.info("未配置34C的角色ID或区服id")
            if is_weekly_first_run(f"配置34C_{self.cfg.name}") and not use_by_myself():
                title = "提示"
                msg = f"账号 {self.cfg.name} 未配置34C的角色ID，将不会领取wegame活动的34C奖励。请前往配置工具的 账号配置/其他 选择34c角色信息"
                async_message_box(msg, title)

    def check_dnf_wegame_dup(self, **extra_params):
        self.check_bind_account(
            "WeGame活动",
            get_act_url("WeGameDup"),
            activity_op_func=self.dnf_wegame_dup_op,
            query_bind_flowid="808066",
            commit_bind_flowid="808065",
            **extra_params,
        )

    def dnf_wegame_dup_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_wegame_dup
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("WeGameDup"),
            **extra_params,
        )

    # --------------------------------------------轻松之路--------------------------------------------
    @try_except()
    def dnf_relax_road(self):
        show_head_line("轻松之路")
        self.show_amesvr_act_info(self.dnf_relax_road_op)

        if not self.cfg.function_switches.get_dnf_relax_road or self.disable_most_activities():
            logger.warning("未启用领取轻松之路功能，将跳过")
            return

        self.check_dnf_relax_road()

        self.dnf_relax_road_op("登录送抽奖1次", "799120")
        for xiaohao in self.common_cfg.majieluo.xiaohao_qq_list:
            self.dnf_relax_road_op(f"分享给 {xiaohao} 送抽奖1次", "799121", iInviter=xiaohao)
        for _i in range(2):
            self.dnf_relax_road_op("抽奖", "798858")

    def check_dnf_relax_road(self):
        self.check_bind_account(
            "轻松之路",
            get_act_url("轻松之路"),
            activity_op_func=self.dnf_relax_road_op,
            query_bind_flowid="799024",
            commit_bind_flowid="799023",
        )

    def dnf_relax_road_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_relax_road
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("轻松之路"),
            **extra_params,
        )

    # --------------------------------------------命运的抉择挑战赛--------------------------------------------
    @try_except()
    def dnf_mingyun_jueze(self):
        show_head_line("命运的抉择挑战赛功能")
        self.show_amesvr_act_info(self.dnf_mingyun_jueze_op)

        if not self.cfg.function_switches.get_dnf_mingyun_jueze or self.disable_most_activities():
            logger.warning("未启用命运的抉择挑战赛功能，将跳过")
            return

        self.check_dnf_mingyun_jueze()

        def query_ticket_count():
            res = self.dnf_mingyun_jueze_op("查询数据", "796751", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue1)

        self.dnf_mingyun_jueze_op("领取报名礼包", "796752")
        self.dnf_mingyun_jueze_op("领取排行礼包", "796753")

        self.dnf_mingyun_jueze_op("每日在线30分钟", "796755")
        self.dnf_mingyun_jueze_op("每日通关", "796756")
        self.dnf_mingyun_jueze_op("每日特权网吧登陆", "796757")

        ticket = query_ticket_count()
        logger.info(color("bold_cyan") + f"当前剩余抽奖券数目为：{ticket}")
        for idx in range_from_one(ticket):
            self.dnf_mingyun_jueze_op(f"[{idx}/{ticket}]幸运夺宝", "796754")
            if idx != ticket:
                time.sleep(5)

        self.dnf_mingyun_jueze_op("决赛普发礼包", "796767")
        self.dnf_mingyun_jueze_op("决赛冠军礼包", "796768")
        self.dnf_mingyun_jueze_op("决赛普发礼包", "796769")

    def check_dnf_mingyun_jueze(self):
        self.check_bind_account(
            "命运的抉择挑战赛",
            get_act_url("命运的抉择挑战赛"),
            activity_op_func=self.dnf_mingyun_jueze_op,
            query_bind_flowid="796750",
            commit_bind_flowid="796749",
        )

    def dnf_mingyun_jueze_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_mingyun_jueze

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("命运的抉择挑战赛"),
            **extra_params,
        )

    # -------------------------------------------- 虎牙 --------------------------------------------
    @try_except()
    def huya(self):
        show_head_line("虎牙")

        if not self.cfg.function_switches.get_huya:
            logger.warning("未启用虎牙功能，将跳过")
            return

        if self.cfg.huya_cookie == "":
            logger.warning(
                "未配置虎牙的cookie，将跳过。请去虎牙活动页面绑定角色后并在小助手配置cookie后再使用（相关的配置会配置就配置，不会就不要配置，我不会回答关于这玩意如何获取的问题）"
            )
            return

        logger.info(color("bold_yellow") + "虎牙的cookie似乎一段时间后就会过期，因此不建议设置-。-想做的话直接手动领吧")

        huya_headers = {
            "referer": "https://www.huya.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
            "cookie": self.cfg.huya_cookie,
        }

        def _get(ctx, url: str, print_res=True):
            return self.get(
                ctx, url, extra_headers=huya_headers, is_jsonp=True, is_normal_jsonp=True, print_res=print_res
            )

        def query_act_tasks_dict(component_id: int, act_id: int) -> dict[int, HuyaActTaskInfo]:
            raw_res = _get(
                "查询活动任务信息",
                f"https://activityapi.huya.com/cache/acttask/getActTaskDetail?callback=getActTaskDetail_matchComponent{component_id}&actId={act_id}&platform=1",
                print_res=False,
            )

            task_id_to_info = {}
            for raw_task_info in raw_res["data"]:
                task_info = HuyaActTaskInfo().auto_update_config(raw_task_info)
                task_id_to_info[task_info.taskId] = task_info

            return task_id_to_info

        def query_user_tasks_list(component_id: int, act_id: int) -> list[HuyaUserTaskInfo]:
            raw_res = _get(
                "查询玩家任务信息",
                f"https://activityapi.huya.com/acttask/getActUserTaskDetail?callback=getUserTasks_matchComponent{component_id}&actId={act_id}&platform=1&_={getMillSecondsUnix()}",
                print_res=False,
            )

            task_list = []
            for raw_task_info in raw_res["data"]:
                task_info = HuyaUserTaskInfo().auto_update_config(raw_task_info)
                task_list.append(task_info)

            return task_list

        def take_award(component_id: int, act_id: int, task_id: int, task_name: str):
            _get(
                f"领取奖励 - {task_name}",
                f"https://activityapi.huya.com/acttask/receivePrize?callback=getTaskAward_matchComponent{component_id}&taskId={task_id}&actId={act_id}&source=1199546566130&platform=1&_={getMillSecondsUnix}",
            )

        def take_awards(component_id: int, act_id: int):
            tasks_dict = query_act_tasks_dict(component_id, act_id)
            user_tasks_list = query_user_tasks_list(component_id, act_id)

            for task_status in user_tasks_list:
                task_info = tasks_dict.get(task_status.taskId)
                if task_status.taskStatus == 0:
                    logger.warning(f"任务 {task_info.taskName} 尚未完成")
                    continue
                if task_status.prizeStatus == 1:
                    logger.info(f"任务 {task_info.taskName} 已经领取过")
                    continue

                take_award(component_id, act_id, task_status.taskId, task_info.taskName)

        def draw_lottery(ctx, component_id: int, cid: int) -> dict:
            return _get(
                ctx,
                f"https://activity.huya.com/randomlottery/index.php?m=Lottery&do=lottery&callback=openBox_matchComponent{component_id}&cid={cid}&platform=1&_={getMillSecondsUnix}",
            )

        # ------------- 玩家见面礼 -------------
        take_awards(4, 4210)

        # ------------- 福利宝箱 -------------
        take_awards(5, 4208)

        for idx in range_from_one(3):
            res = draw_lottery(f"[{idx}/3] 抽奖", 5, 2499)
            if res.get("status") != 200:
                break

    # --------------------------------------------wegame国庆活动【秋风送爽关怀常伴】--------------------------------------------
    def wegame_guoqing(self):
        show_head_line("wegame国庆活动【秋风送爽关怀常伴】")
        self.show_amesvr_act_info(self.wegame_op)

        if not self.cfg.function_switches.get_wegame_guoqing or self.disable_most_activities():
            logger.warning("未启用领取wegame国庆活动功能，将跳过")
            return

        self.check_wegame_guoqing()

        # 一次性奖励
        self.wegame_op("金秋有礼抽奖", "703512")

        # 阿拉德智慧星-答题
        self.wegame_op("答题左上", "703514")
        self.wegame_op("答题左下", "703515")
        self.wegame_op("答题右上", "703516")
        self.wegame_op("答题右下", "703517")

        # 阿拉德智慧星-兑换奖励
        star_count, _ = self.get_wegame_star_count_lottery_times()
        logger.info(color("fg_bold_cyan") + f"即将进行兑换道具，当前剩余智慧星为{star_count}")
        self.wegame_exchange_items()

        # 签到抽大奖
        self.wegame_op("抽奖资格-每日签到（在WeGame启动DNF）", "703519")
        self.wegame_op("抽奖资格-30分钟签到（游戏在线30分钟）", "703527")
        _, lottery_times = self.get_wegame_star_count_lottery_times()
        logger.info(color("fg_bold_cyan") + f"即将进行抽奖，当前剩余抽奖资格为{lottery_times}")
        for _i in range(lottery_times):
            res = self.wegame_op("抽奖", "703957")
            if res.get("ret", "0") == "600":
                # {"ret": "600", "msg": "非常抱歉，您的资格已经用尽！", "flowRet": {"iRet": "600", "sLogSerialNum": "AMS-DNF-1031000622-s0IQqN-331515-703957", "iAlertSerial": "0", "sMsg": "非常抱歉！您的资格已用尽！"}, "failedRet": {"762140": {"iRuleId": "762140", "jRuleFailedInfo": {"iFailedRet": 600}}}}
                break

        # 在线得好礼
        self.wegame_op("累计在线30分钟签到", "703529")
        check_days = self.get_wegame_checkin_days()
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {check_days} 天")
        self.wegame_op("签到3天礼包", "703530")
        self.wegame_op("签到5天礼包", "703531")
        self.wegame_op("签到7天礼包", "703532")
        self.wegame_op("签到10天礼包", "703533")
        self.wegame_op("签到15天礼包", "703534")

    def get_wegame_star_count_lottery_times(self):
        res = self.wegame_op("查询剩余抽奖次数", "703542", print_res=False)
        # "sOutValue1": "239:16:4|240:8:1",
        val = res["modRet"]["sOutValue1"]
        star_count, lottery_times = (int(jifen.split(":")[-1]) for jifen in val.split("|"))
        return star_count, lottery_times

    def get_wegame_checkin_days(self):
        res = self.wegame_op("查询签到信息", "703539")
        return res["modRet"]["total"]

    def wegame_exchange_items(self):
        for ei in self.cfg.wegame_guoqing_exchange_items:
            for i in range(ei.count):
                # 700-幸运星数目不足，600-已经达到最大兑换次数
                res = self.wegame_op(f"兑换 {ei.sGoodsName}", ei.iFlowId)
                if res["ret"] == "700":
                    # 默认先兑换完前面的所有道具的最大上限，才会尝试兑换后面的道具
                    logger.warning(
                        f"兑换第{i + 1}个【{ei.sGoodsName}】的时候幸运星剩余数量不足，将停止兑换流程，从而确保排在前面的兑换道具达到最大兑换次数后才尝试后面的道具"
                    )
                    return

    def check_wegame_guoqing(self):
        self.check_bind_account(
            "wegame国庆",
            get_act_url("wegame国庆活动【秋风送爽关怀常伴】"),
            activity_op_func=self.wegame_op,
            query_bind_flowid="703509",
            commit_bind_flowid="703508",
        )

    def wegame_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_wegame_guoqing

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("wegame国庆活动【秋风送爽关怀常伴】"),
            **extra_params,
        )

    # --------------------------------------------微信签到--------------------------------------------
    def wx_checkin(self):
        # 目前通过autojs实现
        return

    # --------------------------------------------10月女法师三觉活动--------------------------------------------
    def dnf_female_mage_awaken(self):
        show_head_line("10月女法师三觉")
        self.show_amesvr_act_info(self.dnf_female_mage_awaken_op)

        if not self.cfg.function_switches.get_dnf_female_mage_awaken or self.disable_most_activities():
            logger.warning("未启用领取10月女法师三觉活动合集功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        if self.cfg.dnf_helper_info.token == "":
            extra_msg = (
                f"账号 {self.cfg.name} 未配置dnf助手相关信息，无法进行10月女法师三觉相关活动，请按照下列流程进行配置"
            )
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_female_mage_awaken")
            return

        self.dnf_female_mage_awaken_op("时间的引导石 * 10", "712951")
        self.dnf_female_mage_awaken_op("魂灭结晶礼盒 (200个)", "712970")
        self.dnf_female_mage_awaken_op("神秘契约礼盒 (1天)", "712971")
        self.dnf_female_mage_awaken_op("抗疲劳秘药 (10点)", "712972")
        self.dnf_female_mage_awaken_op("装备品级调整箱礼盒 (1个)", "712973")
        self.dnf_female_mage_awaken_op("复活币礼盒 (1个)", "712974")
        self.dnf_female_mage_awaken_op("神秘的符文原石", "712975")
        self.dnf_female_mage_awaken_op("成长胶囊 (50百分比) (Lv50~99)", "712977")
        self.dnf_female_mage_awaken_op("黑钻(3天)", "712978")
        self.dnf_female_mage_awaken_op("本职业稀有护石神秘礼盒", "712981")

        self.dnf_female_mage_awaken_op("每周签到3/5/7次时获得娃娃机抽奖次数", "713370")
        self.dnf_female_mage_awaken_op("娃娃机抽奖", "712623")

        self.dnf_female_mage_awaken_op("回归礼包", "710474")

    def dnf_female_mage_awaken_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_female_mage_awaken

        roleinfo = self.get_dnf_bind_role()
        qq = self.qq()
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(
            ctx,
            "comm.ams.game.qq.com",
            "group_k",
            "bb",
            iActivityId,
            iFlowId,
            print_res,
            "http://mwegame.qq.com/act/dnf/mageawaken/index1/",
            sArea=roleinfo.serviceID,
            serverId=roleinfo.serviceID,
            sRoleId=roleinfo.roleCode,
            sRoleName=quote_plus(roleinfo.roleName),
            uin=qq,
            skey=self.cfg.account_info.skey,
            nickName=quote_plus(dnf_helper_info.nickName),
            userId=dnf_helper_info.userId,
            token=quote_plus(dnf_helper_info.token),
            **extra_params,
        )

        # 1000017016: 登录态失效,请重新登录
        if (
            res is not None
            and type(res) is dict
            and res["flowRet"]["iRet"] == "700"
            and "登录态失效" in res["flowRet"]["sMsg"]
        ):
            extra_msg = "dnf助手的登录态已过期，目前需要手动更新，具体操作流程如下"
            self.show_dnf_helper_info_guide(
                extra_msg, show_message_box_once_key="dnf_female_mage_awaken_expired_" + get_today()
            )

        return res

    # --------------------------------------------dnf助手排行榜活动--------------------------------------------
    def dnf_rank(self):
        show_head_line("dnf助手排行榜")

        if not self.cfg.function_switches.get_dnf_rank or self.disable_most_activities():
            logger.warning("未启用领取dnf助手排行榜活动合集功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        if self.cfg.dnf_helper_info.token == "":
            extra_msg = "未配置dnf助手相关信息，无法进行dnf助手排行榜相关活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_rank")
            return

        # note: 获取鲜花（使用autojs去操作）
        logger.warning("获取鲜花请使用auto.js等自动化工具来模拟打开助手去执行对应操作")

        # 赠送鲜花
        self.dnf_rank_send_score()

        # 领取黑钻
        if self.dnf_rank_get_user_info().canGift == 0:
            logger.warning("12月5日开放黑钻奖励领取~")
        else:
            self.dnf_rank_receive_diamond("3天", "7020")
            self.dnf_rank_receive_diamond("7天", "7021")
            self.dnf_rank_receive_diamond("15天", "7022")
            # 新的黑钻改为使用amesvr去发送，且阉割为只有一个奖励了
            self.dnf_rank_receive_diamond_amesvr("7天黑钻")

        # 结束时打印下最新状态
        self.dnf_rank_get_user_info(print_res=True)

    def dnf_rank_send_score(self):
        id = 7  # 大硕
        name = "疯奶丶大硕"
        total_score = int(self.dnf_rank_get_user_info().score)
        ctx = f"给{id}({name})打榜{total_score}鲜花"
        if total_score <= 0:
            logger.info(f"{ctx} 没有多余的鲜花，暂时不能进行打榜~")
            return

        return self.dnf_rank_op(ctx, self.urls.rank_send_score, id=id, score=total_score)

    @try_except(return_val_on_except=RankUserInfo())
    def dnf_rank_get_user_info(self, print_res=False):
        res = self.dnf_rank_op("查询信息", self.urls.rank_user_info, print_res=print_res)

        return RankUserInfo().auto_update_config(res["data"])

    def dnf_rank_receive_diamond(self, gift_name, gift_id):
        return self.dnf_rank_op(f"领取黑钻-{gift_name}", self.urls.rank_receive_diamond, gift_id=gift_id)

    @try_except()
    def dnf_rank_receive_diamond_amesvr(self, ctx, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_rank
        iFlowId = "723192"

        roleinfo = self.get_dnf_bind_role()
        qq = self.qq()
        dnf_helper_info = self.cfg.dnf_helper_info

        return self.amesvr_request(
            ctx,
            "comm.ams.game.qq.com",
            "group_k",
            "bb",
            iActivityId,
            iFlowId,
            True,
            get_act_url("dnf助手排行榜"),
            sArea=roleinfo.serviceID,
            serverId=roleinfo.serviceID,
            areaId=roleinfo.serviceID,
            sRoleId=roleinfo.roleCode,
            sRoleName=quote_plus(roleinfo.roleName),
            uin=qq,
            skey=self.cfg.account_info.skey,
            nickName=quote_plus(dnf_helper_info.nickName),
            userId=dnf_helper_info.userId,
            token=quote_plus(dnf_helper_info.token),
            **extra_params,
        )

    def dnf_rank_op(self, ctx, url, **params):
        qq = self.qq()
        info = self.cfg.dnf_helper_info
        return self.get(ctx, url, uin=qq, userId=info.userId, token=quote_plus(info.token), **params)

    # --------------------------------------------2020DNF嘉年华页面主页面签到--------------------------------------------
    def dnf_carnival(self):
        show_head_line("2020DNF嘉年华页面主页面签到")
        self.show_amesvr_act_info(self.dnf_carnival_op)

        if not self.cfg.function_switches.get_dnf_carnival or self.disable_most_activities():
            logger.warning("未启用领取2020DNF嘉年华页面主页面签到活动合集功能，将跳过")
            return

        self.check_dnf_carnival()

        self.dnf_carnival_op("12.11-12.14 阶段一签到", "721945")
        self.dnf_carnival_op("12.15-12.18 阶段二签到", "722198")
        self.dnf_carnival_op("12.19-12.26 阶段三与全勤", "722199")

    def check_dnf_carnival(self):
        self.check_bind_account(
            "2020DNF嘉年华页面主页面签到",
            get_act_url("2020DNF嘉年华页面主页面签到"),
            activity_op_func=self.dnf_carnival_op,
            query_bind_flowid="722055",
            commit_bind_flowid="722054",
        )

    def dnf_carnival_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_carnival

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("2020DNF嘉年华页面主页面签到"),
            **extra_params,
        )

    # --------------------------------------------2020DNF嘉年华直播--------------------------------------------
    def dnf_carnival_live(self):
        if not self.common_cfg.test_mode:
            # 仅限测试模式运行
            return

        show_head_line("2020DNF嘉年华直播")
        self.show_amesvr_act_info(self.dnf_carnival_live_op)

        if not self.cfg.function_switches.get_dnf_carnival_live or self.disable_most_activities():
            logger.warning("未启用领取2020DNF嘉年华直播活动合集功能，将跳过")
            return

        self.check_dnf_carnival_live()

        def query_watch_time():
            res = self.dnf_carnival_live_op("查询观看时间", "722482", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue3)

        def watch_remaining_time():
            self.dnf_carnival_live_op("记录完成一分钟观看", "722476")

            current_watch_time = query_watch_time()
            remaining_time = 15 * 8 - current_watch_time
            logger.info(f"账号 {self.cfg.name} 当前已观看{current_watch_time}分钟，仍需观看{remaining_time}分钟")

        def query_used_lottery_times():
            res = self.dnf_carnival_live_op("查询获奖次数", "725567", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue1)

        def lottery_remaining_times():
            total_lottery_times = query_watch_time() // 15
            used_lottery_times = query_used_lottery_times()
            remaining_lottery_times = total_lottery_times - used_lottery_times
            logger.info(
                f"账号 {self.cfg.name} 抽奖次数信息：总计={total_lottery_times} 已使用={used_lottery_times} 剩余={remaining_lottery_times}"
            )
            if remaining_lottery_times == 0:
                logger.warning("没有剩余次数，将不进行抽奖")
                return

            for i in range(remaining_lottery_times):
                res = self.dnf_carnival_live_op(f"{i + 1}. 抽奖", "722473")
                if res["ret"] != "0":
                    logger.warning(f"出错了，停止抽奖，剩余抽奖次数为{remaining_lottery_times - i}")
                    break

        watch_remaining_time()
        lottery_remaining_times()

    def check_dnf_carnival_live(self):
        self.check_bind_account(
            "2020DNF嘉年华直播",
            get_act_url("2020DNF嘉年华页面主页面签到"),
            activity_op_func=self.dnf_carnival_live_op,
            query_bind_flowid="722472",
            commit_bind_flowid="722471",
        )

    def dnf_carnival_live_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_carnival_live

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("2020DNF嘉年华页面主页面签到"),
            **extra_params,
        )

    # DNF进击吧赛利亚
    def xinyue_sailiyam(self):
        show_head_line("DNF进击吧赛利亚")
        self.show_amesvr_act_info(self.xinyue_sailiyam_op)

        def sleep_to_avoid_ban():
            logger.info("等待五秒，防止提示操作太快")
            time.sleep(5)

        for dzid in self.common_cfg.sailiyam_visit_target_qqs:
            if dzid == self.qq():
                continue
            self.xinyue_sailiyam_op(f"拜访好友-{dzid}", "714307", dzid=dzid)
            sleep_to_avoid_ban()

        if not self.cfg.function_switches.get_xinyue_sailiyam or self.disable_most_activities():
            logger.warning("未启用领取DNF进击吧赛利亚活动功能，将跳过")
            return

        self.check_xinyue_sailiyam()
        self.show_xinyue_sailiyam_kouling()
        self.xinyue_sailiyam_op("清空工作天数", "715579")

        sleep_to_avoid_ban()
        self.xinyue_sailiyam_op("领取蛋糕", "714230")
        self.xinyue_sailiyam_op("投喂蛋糕", "714251")

        logger.info(
            "ps：打工在运行结束的时候统一处理，这样可以确保处理好各个其他账号的拜访，从而有足够的心情值进行打工"
        )

    @try_except(return_val_on_except="")
    def get_xinyue_sailiyam_package_id(self):
        res = self.xinyue_sailiyam_op("打工显示", "715378", print_res=False)
        return res["modRet"]["jData"]["roleinfor"]["iPackageId"]

    @try_except(return_val_on_except="")
    def get_xinyue_sailiyam_workinfo(self):
        res = self.xinyue_sailiyam_op("打工显示", "715378", print_res=False)
        workinfo = SailiyamWorkInfo().auto_update_config(res["modRet"]["jData"]["roleinfor"])

        work_message = ""

        if workinfo.status == 2:
            nowtime = get_now_unix()
            fromtimestamp = datetime.datetime.fromtimestamp
            if workinfo.endTime > nowtime:
                lefttime = int(workinfo.endTime - nowtime)
                hour, minute, second = lefttime // 3600, lefttime % 3600 // 60, lefttime % 60
                work_message += f"赛利亚打工倒计时：{hour:02d}:{minute:02d}:{second:02d}"
            else:
                work_message += "赛利亚已经完成今天的工作了"

            work_message += f"。开始时间为{fromtimestamp(workinfo.startTime)}，结束时间为{fromtimestamp(workinfo.endTime)}，奖励最终领取时间为{fromtimestamp(workinfo.endLQtime)}"
        else:
            work_message += "赛利亚尚未出门工作"

        return work_message

    @try_except(return_val_on_except="")
    def get_xinyue_sailiyam_status(self):
        res = self.xinyue_sailiyam_op("查询状态", "714738", print_res=False)
        modRet = parse_amesvr_common_info(res)
        lingqudangao, touwei, _, baifang = modRet.sOutValue1.split("|")
        dangao = modRet.sOutValue2
        xinqingzhi = modRet.sOutValue3
        qiandaodate = modRet.sOutValue4
        return f"领取蛋糕：{lingqudangao == '1'}, 投喂蛋糕: {touwei == '1'}, 已拜访次数: {baifang}/5, 剩余蛋糕: {dangao}, 心情值: {xinqingzhi}/100, 已连续签到: {qiandaodate}次"

    @try_except()
    def show_xinyue_sailiyam_work_log(self):
        res = self.xinyue_sailiyam_op("日志列表", "715201", print_res=False)
        logContents = {
            "2168440": "遇到需要紧急处理的工作，是时候证明真正的技术了，启动加班模式！工作时长加1小时；",
            "2168439": "愉快的一天又开始了，是不是该来一杯咖啡？",
            "2168442": "给流浪猫咪喂吃的导致工作迟到，奖励虽然下降 ，但是撸猫的心情依然美好；",
            "2168441": "工作效率超高，能力超强，全能MVP，优秀的你，当然需要发奖金啦，奖励up；",
        }
        logs = res["modRet"]["jData"]["loglist"]["list"]
        if len(logs) != 0:
            logger.info("赛利亚打工日志如下")
            for log in logs:
                month, day, message = log[0][:2], log[0][2:], logContents[log[2]]
                logger.info(f"{month}月{day}日：{message}")

    def show_xinyue_sailiyam_kouling(self):
        res = self.xinyue_sailiyam_op("输出项", "714618", print_res=False)
        if "modRet" in res:
            logger.info(f"分享口令为： {res['modRet']['sOutValue2']}")

    def check_xinyue_sailiyam(self):
        self.check_bind_account(
            "DNF进击吧赛利亚",
            get_act_url("DNF进击吧赛利亚"),
            activity_op_func=self.xinyue_sailiyam_op,
            query_bind_flowid="714234",
            commit_bind_flowid="714233",
        )

    def xinyue_sailiyam_op(self, ctx, iFlowId, dzid="", iPackageId="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_xinyue_sailiyam

        return self.amesvr_request(
            ctx,
            "act.game.qq.com",
            "xinyue",
            "tgclub",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF进击吧赛利亚"),
            dzid=dzid,
            page=1,
            iPackageId=iPackageId,
            **extra_params,
        )

    # --------------------------------------------阿拉德勇士征集令--------------------------------------------
    @try_except()
    def dnf_warriors_call(self):
        show_head_line("阿拉德勇士征集令")

        if not self.cfg.function_switches.get_dnf_warriors_call or self.disable_most_activities():
            logger.warning("未启用领取阿拉德勇士征集令功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.fetch_pskey()
        if self.lr is None:
            return

        qa = QzoneActivity(self, self.lr)
        qa.dnf_warriors_call()

    # --------------------------------------------dnf漂流瓶--------------------------------------------
    @try_except()
    def dnf_drift(self):
        show_head_line("dnf漂流瓶")
        self.show_amesvr_act_info(self.dnf_drift_op)

        if not self.cfg.function_switches.get_dnf_drift or self.disable_most_activities():
            logger.warning("未启用领取dnf漂流瓶活动功能，将跳过")
            return

        self.check_dnf_drift()

        def send_friend_invitation(typStr, flowid, dayLimit):
            send_count = 0
            for sendQQ in self.cfg.drift_send_qq_list:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)
                res = self.dnf_drift_op(f"发送{typStr}好友邀请-{sendQQ}赠送2积分", flowid, sendQQ=sendQQ, moduleId="2")

                send_count += 1
                if int(res["ret"]) != 0 or send_count >= dayLimit:
                    logger.warning(f"已达到本日邀请上限({dayLimit})，将停止邀请")
                    return

        def take_friend_awards(typStr, type, moduleId, take_points_flowid):
            page = 1
            while True:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)

                queryRes = self.dnf_drift_op(f"拉取接受的{typStr}好友列表", "725358", page=str(page), type=type)
                if int(queryRes["ret"]) != 0 or queryRes["modRet"]["jData"]["iTotal"] == 0:
                    logger.warning("没有更多接收邀请的好友了，停止领取积分")
                    return

                for friend_info in queryRes["modRet"]["jData"]["jData"]:
                    takeRes = self.dnf_drift_op(
                        f"邀请人领取{typStr}邀请{friend_info['iUin']}的积分",
                        take_points_flowid,
                        acceptId=friend_info["id"],
                        moduleId=moduleId,
                    )
                    if int(takeRes["ret"]) != 0:
                        logger.warning("似乎已达到今日上限，停止领取")
                        return
                    if takeRes["modRet"]["iRet"] != 0:
                        logger.warning("出错了，停止领取，具体原因请看上一行的sMsg")
                        return

                page += 5

        # 01 这一切都是命运的选择
        # 礼包海
        self.dnf_drift_op("捞一个", "725715")
        # 丢礼包，日限8次
        send_friend_invitation("普通", "725819", 8)
        take_friend_awards("普通", "1", "4", "726267")

        # 02 承认吧，这是友情的羁绊
        # 那些年错过的他，日限5次
        send_friend_invitation("流失", "726069", 5)
        take_friend_awards("流失", "2", "6", "726269")
        # 礼包领取站
        self.dnf_drift_op("流失用户领取礼包", "727230")

        # 03 来吧，吾之宝藏
        # 积分夺宝
        totalPoints, remainingPoints = self.query_dnf_drift_points()
        remainingLotteryTimes = remainingPoints // 4
        logger.info(
            color("bold_yellow")
            + f"当前积分为{remainingPoints}，总计可进行{remainingLotteryTimes}次抽奖。历史累计获取积分数为{totalPoints}"
        )
        for i in range(remainingLotteryTimes):
            self.dnf_drift_op(f"开始夺宝 - 第{i + 1}次", "726379")

        # 04 在线好礼站
        self.dnf_drift_op("在线30min", "725675", moduleId="2")
        self.dnf_drift_op("累计3天礼包", "725699", moduleId="0", giftId="1437440")
        self.dnf_drift_op("累计7天礼包", "725699", moduleId="0", giftId="1437441")
        self.dnf_drift_op("累计15天礼包", "725699", moduleId="0", giftId="1437442")

        # 分享
        self.dnf_drift_op("分享领取礼包", "726345")

    def query_dnf_drift_points(self):
        res = self.dnf_drift_op("查询基础信息", "726353", print_res=False)
        info = parse_amesvr_common_info(res)
        total, remaining = int(info.sOutValue2), int(info.sOutValue2) - int(info.sOutValue1) * 4
        return total, remaining

    def check_dnf_drift(self):
        typ = random.choice([1, 2])
        activity_url = f"{get_act_url('dnf漂流瓶')}?sId=0252c9b811d66dc1f0c9c6284b378e40&type={typ}"

        self.check_bind_account(
            "dnf漂流瓶",
            activity_url,
            activity_op_func=self.dnf_drift_op,
            query_bind_flowid="725357",
            commit_bind_flowid="725356",
        )

        if is_first_run("check_dnf_drift"):
            msg = "求帮忙做一下邀请任务0-0  只用在点击确定按钮后弹出的活动页面中点【确认接受邀请】就行啦（这条消息只会出现一次）"
            async_message_box(msg, "帮忙接受一下邀请0-0", open_url=activity_url)

    def dnf_drift_op(
        self,
        ctx,
        iFlowId,
        page="",
        type="",
        moduleId="",
        giftId="",
        acceptId="",
        sendQQ="",
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.iActivityId_dnf_drift

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("dnf漂流瓶"),
            page=page,
            type=type,
            moduleId=moduleId,
            giftId=giftId,
            acceptId=acceptId,
            sendQQ=sendQQ,
            **extra_params,
        )

    # --------------------------------------------暖冬好礼活动--------------------------------------------
    @try_except()
    def warm_winter(self):
        show_head_line("暖冬好礼活动")
        self.show_amesvr_act_info(self.warm_winter_op)

        if not self.cfg.function_switches.get_warm_winter or self.disable_most_activities():
            logger.warning("未启用领取暖冬好礼活动功能，将跳过")
            return

        self.check_warm_winter()

        def get_lottery_times():
            res = self.warm_winter_op("查询剩余抽奖次数", "728476", print_res=False)
            # "sOutValue1": "279:2:1",
            val = res["modRet"]["sOutValue1"]
            jfId, total, remaining = (int(v) for v in val.split(":"))
            return total, remaining

        def get_checkin_days():
            res = self.warm_winter_op("查询签到信息", "723178")
            return int(res["modRet"]["total"])

        # 01 勇士齐聚阿拉德
        self.warm_winter_op("四个礼盒随机抽取", "723167")

        # 02 累计签到领豪礼
        self.warm_winter_op("签到礼包", "723165")
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {get_checkin_days()} 天")
        self.warm_winter_op("签到3天礼包", "723170")
        self.warm_winter_op("签到5天礼包", "723171")
        self.warm_winter_op("签到7天礼包", "723172")
        self.warm_winter_op("签到10天礼包", "723173")
        self.warm_winter_op("签到15天礼包", "723174")

        # 03 累计签到抽大奖
        self.warm_winter_op("1.在WeGame启动DNF", "723175")
        self.warm_winter_op("2.游戏在线30分钟", "723176")
        total_lottery_times, lottery_times = get_lottery_times()
        logger.info(
            color("fg_bold_cyan")
            + f"即将进行抽奖，当前剩余抽奖资格为{lottery_times}，累计获取{total_lottery_times}次抽奖机会"
        )
        for _i in range(lottery_times):
            res = self.warm_winter_op("每日抽奖", "723177")
            if res.get("ret", "0") == "600":
                # {"ret": "600", "msg": "非常抱歉，您的资格已经用尽！", "flowRet": {"iRet": "600", "sLogSerialNum": "AMS-DNF-1031000622-s0IQqN-331515-703957", "iAlertSerial": "0", "sMsg": "非常抱歉！您的资格已用尽！"}, "failedRet": {"762140": {"iRuleId": "762140", "jRuleFailedInfo": {"iFailedRet": 600}}}}
                break

    def check_warm_winter(self):
        self.check_bind_account(
            "暖冬好礼",
            get_act_url("暖冬好礼活动"),
            activity_op_func=self.warm_winter_op,
            query_bind_flowid="723162",
            commit_bind_flowid="723161",
        )

    def warm_winter_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_warm_winter

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("暖冬好礼活动"),
            **extra_params,
        )

    # --------------------------------------------史诗之路来袭活动合集--------------------------------------------
    @try_except()
    def dnf_1224(self):
        show_head_line("史诗之路来袭活动合集")
        self.show_amesvr_act_info(self.dnf_1224_op)

        if not self.cfg.function_switches.get_dnf_1224 or self.disable_most_activities():
            logger.warning("未启用领取史诗之路来袭活动合集功能，将跳过")
            return

        self.check_dnf_1224()

        self.dnf_1224_op("勇士礼包", "730665")

        self.dnf_1224_op("30分签到礼包", "730666")
        check_days = self.get_dnf_1224_checkin_days()
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {check_days} 天")
        self.dnf_1224_op("3日礼包", "730663")
        self.dnf_1224_op("7日礼包", "730667")
        self.dnf_1224_op("15日礼包", "730668")

    def get_dnf_1224_checkin_days(self):
        res = self.dnf_1224_op("查询签到信息", "730670", print_res=False)
        return int(res["modRet"]["total"])

    def check_dnf_1224(self):
        self.check_bind_account(
            "qq视频-史诗之路来袭活动合集",
            get_act_url("史诗之路来袭活动合集"),
            activity_op_func=self.dnf_1224_op,
            query_bind_flowid="730660",
            commit_bind_flowid="730659",
        )

    def dnf_1224_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_1224
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("史诗之路来袭活动合集"),
            **extra_params,
        )

    # --------------------------------------------新春福袋大作战--------------------------------------------
    @try_except()
    def spring_fudai(self):
        show_head_line("新春福袋大作战")
        self.show_amesvr_act_info(self.spring_fudai_op)

        if not self.cfg.function_switches.get_spring_fudai or self.disable_most_activities():
            logger.warning("未启用领取新春福袋大作战功能，将跳过")
            return

        self.check_spring_fudai()

        inviter_sid = "0252c9b811d66dc1f0c9c6284b378e40"
        if is_first_run("fudai_invite"):
            msg = (
                "Hello~，可否在稍后弹出的福袋大作战活动页面点一下确认接收哇（不会损失任何东西）\n"
                "(〃'▽'〃)"
                "（本消息只会弹出一次）\n"
            )
            async_message_box(msg, "帮忙点一点", open_url=f"{get_act_url('新春福袋大作战')}?type=2&sId={inviter_sid}")

        def query_info():
            # {"sOutValue1": "1|1|0", "sOutValue2": "1", "sOutValue3": "0", "sOutValue4": "0",
            # "sOutValue5": "0252c9b811d66dc1f0c9c6284b378e40", "sOutValue6": "", "sOutValue7": "0", "sOutValue8": "4"}
            res = self.spring_fudai_op("查询各种数据", "733432", print_res=False)
            raw_info = parse_amesvr_common_info(res)
            info = SpringFuDaiInfo()

            temp = raw_info.sOutValue1.split("|")
            info.today_has_take_fudai = temp[0] == "1"
            info.fudai_count = int(raw_info.sOutValue4)
            info.has_take_bind_award = raw_info.sOutValue2 == "1"
            info.invited_ok_liushi_friends = int(raw_info.sOutValue7)
            info.has_take_share_award = temp[1] == "1"
            info.total_lottery_times = int(raw_info.sOutValue3)
            info.lottery_times = info.total_lottery_times - int(temp[2])
            info.date_info = int(raw_info.sOutValue8)

            return info

        info = query_info()

        def send_friend_invitation(typStr, flowid, dayLimit):
            if len(self.cfg.spring_fudai_receiver_qq_list) == 0:
                return

            spring_fudai_pskey = self.fetch_share_p_skey("赠送福袋")

            send_count = 0
            for sendQQ in self.cfg.spring_fudai_receiver_qq_list:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)
                res = self.spring_fudai_op(
                    f"发送{typStr}好友邀请-{sendQQ}赠送2积分",
                    flowid,
                    sendQQ=sendQQ,
                    dateInfo=str(info.date_info),
                    p_skey=spring_fudai_pskey,
                )

                send_count += 1
                if int(res["ret"]) != 0 or send_count >= dayLimit:
                    logger.warning(f"已达到本日邀请上限({dayLimit})，将停止邀请")
                    return

        def take_friend_awards(typStr, type, take_points_flowid):
            page = 1
            while True:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)

                queryRes = self.spring_fudai_op(f"拉取接受的{typStr}好友列表", "733413", page=str(page), type=type)
                if int(queryRes["ret"]) != 0 or queryRes["modRet"]["jData"]["iTotal"] == 0:
                    logger.warning("没有更多接收邀请的好友了，停止领取积分")
                    return

                for friend_info in queryRes["modRet"]["jData"]["jData"]:
                    takeRes = self.spring_fudai_op(
                        f"邀请人领取{typStr}邀请{friend_info['iUin']}的积分",
                        take_points_flowid,
                        acceptId=friend_info["id"],
                        needADD="2",
                    )
                    if int(takeRes["ret"]) != 0:
                        logger.warning("似乎已达到今日上限，停止领取")
                        return
                    if takeRes["modRet"]["iRet"] != 0:
                        logger.warning("出错了，停止领取，具体原因请看上一行的sMsg")
                        return

                page += 5

        if not info.has_take_share_award:
            self.spring_fudai_op("分享领取礼包", "733412")

        # 邀请普通玩家（福袋）
        if not info.has_take_bind_award:
            self.spring_fudai_op("绑定大区获得1次获取福袋机会", "732406")
        if not info.today_has_take_fudai:
            self.spring_fudai_op("打开一个福袋", "732405")

        self.spring_fudai_op(f"赠送好友福袋-{inviter_sid}", "733380", sId=inviter_sid)

        send_friend_invitation("普通", "732407", 8)
        take_friend_awards("普通", "1", "732550")
        self.spring_fudai_op("普通好友接受邀请", "732548", sId=inviter_sid)
        # 更新下数据
        info = query_info()
        logger.info(color("bold_yellow") + f"当前拥有{info.fudai_count}个福袋")

        # 邀请流失玩家和领奖
        self.spring_fudai_op("流失用户领取礼包", "732597")
        self.spring_fudai_op("流失好友接受邀请", "732635", sId=inviter_sid)
        for num in range(1, 6 + 1):
            self.spring_fudai_op(f"邀请人领取邀请{num}个流失用户的接受礼包", "733369", userNum=str(num))
        # 更新下数据
        info = query_info()
        logger.info(color("bold_yellow") + f"已成功邀请{info.invited_ok_liushi_friends}个流失好友")

        # 抽奖
        logger.info(
            color("bold_yellow")
            + f"当前共有{info.lottery_times}抽奖积分，历史累计获取数目为{info.total_lottery_times}抽奖积分"
        )
        for i in range(info.lottery_times):
            self.spring_fudai_op(f"第{i + 1}次积分抽奖", "733411")

        # 签到
        self.spring_fudai_op("在线30min礼包", "732400", needADD="1")
        self.spring_fudai_op("累计3天礼包", "732404", giftId="1470919")
        self.spring_fudai_op("累计7天礼包", "732404", giftId="1470920")
        self.spring_fudai_op("累计15天礼包", "732404", giftId="1470921")

    def check_spring_fudai(self):
        self.check_bind_account(
            "新春福袋大作战",
            get_act_url("新春福袋大作战"),
            activity_op_func=self.spring_fudai_op,
            query_bind_flowid="732399",
            commit_bind_flowid="732398",
        )

    def spring_fudai_op(
        self,
        ctx,
        iFlowId,
        needADD="0",
        page="",
        type="",
        dateInfo="",
        sendQQ="",
        sId="",
        acceptId="",
        userNum="",
        giftId="",
        p_skey="",
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.iActivityId_spring_fudai
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("新春福袋大作战"),
            needADD=needADD,
            page=page,
            type=type,
            dateInfo=dateInfo,
            sendQQ=sendQQ,
            sId=sId,
            acceptId=acceptId,
            userNum=userNum,
            giftId=giftId,
            **extra_params,
            extra_cookies=f"p_skey={p_skey}",
        )

    # --------------------------------------------燃放爆竹活动--------------------------------------------
    @try_except()
    def firecrackers(self):
        show_head_line("燃放爆竹活动")
        self.show_amesvr_act_info(self.firecrackers_op)

        if not self.cfg.function_switches.get_firecrackers or self.disable_most_activities():
            logger.warning("未启用领取燃放爆竹活动功能，将跳过")
            return

        self.check_firecrackers()

        def query_count():
            res = self.firecrackers_op("查询剩余爆竹数", "733395", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue1)

        def today_has_invite_friend():
            res = self.firecrackers_op("查询各个任务状态", "733392", print_res=False)
            raw_info = parse_amesvr_common_info(res)
            taskStatus = raw_info.sOutValue1.split(",")

            return int(taskStatus[3]) >= 1

        @try_except(return_val_on_except=[])
        def query_invited_friends():
            res = self.firecrackers_op("查询成功邀请好友列表", "735412", print_res=False)

            invited_friends = []
            for info in res["modRet"]["jData"]["jData"]:
                invited_friends.append(info["sendToQQ"])

            return invited_friends

        account_db = FireCrackersDB().with_context(self.cfg.get_account_cache_key()).load()

        def qeury_not_invited_friends_with_cache():
            invited_friends = query_invited_friends()

            def filter_not_invited_friends(friendQQs):
                validFriendQQs = []
                for friendQQ in friendQQs:
                    if friendQQ not in invited_friends:
                        validFriendQQs.append(friendQQ)

                return validFriendQQs

            friendQQs = account_db.friend_qqs

            validFriendQQs = filter_not_invited_friends(friendQQs)

            if len(validFriendQQs) > 0:
                return validFriendQQs

            return filter_not_invited_friends(qeury_not_invited_friends())

        def qeury_not_invited_friends():
            logger.info("本地无好友名单，或缓存的好友均已邀请过，需要重新拉取，请稍后~")
            friendQQs = []

            page = 1
            page_size = 4
            while True:
                info = query_friends(page, page_size)
                if len(info.list) == 0:
                    # 没有未邀请的好友了
                    break
                for friend in info.list:
                    friendQQs.append(str(friend.uin))

                page += 1

            logger.info(f"获取好友名单共计{len(friendQQs)}个，将保存到本地，具体如下：{friendQQs}")

            def _update_db(db: FireCrackersDB):
                db.friend_qqs = friendQQs

            account_db.update(_update_db)

            return friendQQs

        def query_friends(page, page_size):
            res = self.firecrackers_op(
                "查询好友列表", "735262", pageNow=str(page), pageSize=str(page_size), print_res=True
            )
            info = AmesvrQueryFriendsInfo().auto_update_config(res["modRet"]["jData"])
            return info

        def get_one_not_invited_friend():
            friends = qeury_not_invited_friends_with_cache()
            if len(friends) == 0:
                return None

            return friends[0]

        def invite_one_friend():
            friendQQ = get_one_not_invited_friend()
            if friendQQ is None:
                logger.warning("没有更多未邀请过的好友了=、=每个好友目前限制只能邀请一次")
                return
            self.firecrackers_op(f"发送好友邀请给{friendQQ}", "735263", receiveUin=str(friendQQ))

        # 完成 分享好友 任务
        if self.cfg.enable_firecrackers_invite_friend:
            if not today_has_invite_friend():
                logger.info("尝试挑选一个未邀请过的好友进行邀请~")
                invite_one_friend()
            else:
                logger.info("今日已经邀请过好友，不必再次进行")
        else:
            logger.info("未启用燃放爆竹邀请好友功能，将跳过~")

        # 完成任务获取爆竹
        self.firecrackers_op("获取爆竹*1-今日游戏在线", "733098")
        self.firecrackers_op("获取爆竹*1-累计在线30分钟", "733125")
        self.firecrackers_op("获取爆竹*2-通关推荐副本2次", "733127")
        self.firecrackers_op("获取爆竹*1-每日分享好友", "733129")

        firecrackers_count = query_count()
        logger.info(color("bold_cyan") + f"经过上述操作，当前爆竹数目为{firecrackers_count}个")
        for i in range(firecrackers_count):
            self.firecrackers_op(f"第{i + 1}次燃放鞭炮获取积分，并等待一秒", "733132")
            time.sleep(1)

        show_end_time("2021-02-23 00:00:00")

        # 积分兑换奖励
        points = self.query_firecrackers_points()
        points_to_120_need_days = (120 - points + 4) // 5
        logger.info(
            color("bold_cyan") + f"当前积分为{points}，距离兑换自选灿烂所需120预计还需要{points_to_120_need_days}天"
        )

        if len(self.cfg.firecrackers.exchange_items) != 0:
            logger.info("将尝试按照配置的优先级兑换奖励")
            for ei in self.cfg.firecrackers.exchange_items:
                res = self.firecrackers_op(f"道具兑换-{ei.need_points}积分-{ei.name}", "733133", index=str(ei.index))
                if res["ret"] == "700" and res["flowRet"]["iCondNotMetId"] == "1432184":
                    logger.warning("当前奖励积分不够，将跳过后续奖励")
                    break
        else:
            logger.info("当前未配置兑换道具，请根据需要自行配置需要兑换的道具列表")

        # 积分抽奖
        if self.cfg.firecrackers.enable_lottery:
            points = self.query_firecrackers_points()
            logger.info(color("bold_cyan") + f"当前积分为{points}，将进行{points // 2}次抽奖")
            for i in range(points // 2):
                self.firecrackers_op(f"第{i + 1}次积分抽奖，并等待五秒", "733134")
                time.sleep(5)
        else:
            logger.info(color("bold_green") + "如果已经兑换完所有奖励，建议开启使用积分抽奖功能")

    @try_except(return_val_on_except=0)
    def query_firecrackers_points(self):
        res = self.firecrackers_op("查询剩余积分数", "733396", print_res=False)
        raw_info = parse_amesvr_common_info(res)

        return int(raw_info.sOutValue1)

    def check_firecrackers(self):
        self.check_bind_account(
            "燃放爆竹活动",
            get_act_url("燃放爆竹活动"),
            activity_op_func=self.firecrackers_op,
            query_bind_flowid="733400",
            commit_bind_flowid="733399",
        )

    def firecrackers_op(self, ctx, iFlowId, index="", pageNow="", pageSize="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_firecrackers
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("燃放爆竹活动"),
            index=index,
            pageNow=pageNow,
            pageSize=pageSize,
            **extra_params,
        )

    # --------------------------------------------DNF福签大作战--------------------------------------------
    @try_except()
    def dnf_fuqian(self):
        show_head_line("DNF福签大作战")
        self.show_amesvr_act_info(self.dnf_fuqian_op)

        if not self.cfg.function_switches.get_dnf_fuqian or self.disable_most_activities():
            logger.warning("未启用领取DNF福签大作战功能，将跳过")
            return

        self.check_dnf_fuqian()

        def query_info():
            res = self.dnf_fuqian_op("查询资格", "742112", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = DnfCollectionInfo()
            info.has_init = raw_info.sOutValue2 != "0"
            info.send_total = int(raw_info.sOutValue3)
            info.total_page = math.ceil(info.send_total / 6)
            info.luckyCount = int(raw_info.sOutValue5)
            info.scoreCount = int(raw_info.sOutValue6)
            info.openLuckyCount = int(raw_info.sOutValue7)

            return info

        def take_invite_awards():
            act_info = search_act(self.urls.iActivityId_dnf_fuqian)
            is_last_day = False
            if act_info is not None and act_info.is_last_day():
                is_last_day = True

            if not is_last_day and not is_weekly_first_run(
                f"fuqian_take_invite_awards_{self.cfg.get_account_cache_key()}"
            ):
                logger.warning("本周已运行过领取邀请奖励，暂不继续领取~")
                return

            info = query_info()
            for page in range(1, info.total_page + 1):
                res = self.dnf_fuqian_op(
                    f"查询第{page}/{info.total_page}页邀请成功的列表", "744443", sendPage=str(page)
                )
                data = res["modRet"]["jData"]
                logger.info(data["iTotal"])
                if data["iTotal"] > 0:
                    for invite_info in data["jData"]:
                        if invite_info["iGet"] == "0":
                            uin = invite_info["iUin2"]
                            iId = invite_info["iId"]
                            self.dnf_fuqian_op(f"领取第{page}页积分奖励-{uin}", "743861", iId=iId)
                else:
                    logger.info("没有更多已邀请好友了，将跳过~")
                    return

        # 正式逻辑如下

        info = query_info()
        if not info.has_init:
            self.dnf_fuqian_op("初次赠送一个福签积分", "742513")
        self.dnf_fuqian_op("随机抽一个福签", "742491")

        self.dnf_fuqian_op("幸运玩家礼包领取", "742315")

        for sCode in [
            "4f739a998cb44201484a8fa7d4e9eaed58e1576e312b70a2cbf17214e19a2ec0",
            "c79fd5c303d0d9a8421a427badae87fd58e1576e312b70a2cbf17214e19a2ec0",
            *self.common_cfg.scode_list_accept_give,
        ]:
            self.dnf_fuqian_op(
                "接受福签赠送", "742846", sCode=sCode, sNickName=quote_plus(quote_plus(quote_plus("小号")))
            )
        for sCode in [
            "f3256878f5744a90d9efe0ee6f4d3c3158e1576e312b70a2cbf17214e19a2ec0",
            "f43f1d4d525f55ccd88ff03b60638e0058e1576e312b70a2cbf17214e19a2ec0",
            *self.common_cfg.scode_list_accept_ask,
        ]:
            self.dnf_fuqian_op("接受福签索要", "742927", sCode=sCode)

        if len(self.cfg.spring_fudai_receiver_qq_list) != 0:
            share_pskey = self.fetch_share_p_skey("福签赠送")
            for qq in self.cfg.spring_fudai_receiver_qq_list:
                self.dnf_fuqian_op(f"福签赠送-{qq}", "742115", fuin=str(qq), extra_cookies=f"p_skey={share_pskey}")
                self.dnf_fuqian_op(f"福签索要-{qq}", "742824", fuin=str(qq), extra_cookies=f"p_skey={share_pskey}")
        else:
            logger.warning(color("bold_yellow") + "未配置新春福袋大作战邀请列表, 将跳过赠送福签")

        take_invite_awards()

        self.dnf_fuqian_op("福签累计奖励1", "742728")
        self.dnf_fuqian_op("福签累计奖励2", "742732")
        self.dnf_fuqian_op("福签累计奖励3", "742733")
        self.dnf_fuqian_op("福签累计奖励4", "742734")
        self.dnf_fuqian_op("福签累计奖励5", "742735")
        self.dnf_fuqian_op("福签累计奖励6", "742736")
        self.dnf_fuqian_op("福签累计奖励7", "742737")
        self.dnf_fuqian_op("福签累计奖励20", "742738")

        info = query_info()
        logger.info(color("bold_cyan") + f"当前共有{info.scoreCount}个积分")
        for idx in range(info.scoreCount):
            self.dnf_fuqian_op(f"第{idx + 1}次积分夺宝并等待5秒", "742740")
            time.sleep(5)

        self.dnf_fuqian_op("分享奖励", "742742")

    def check_dnf_fuqian(self):
        self.check_bind_account(
            "DNF福签大作战",
            get_act_url("DNF福签大作战"),
            activity_op_func=self.dnf_fuqian_op,
            query_bind_flowid="742110",
            commit_bind_flowid="742109",
        )

    def dnf_fuqian_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_fuqian
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF福签大作战"),
            **extra_params,
        )

    # --------------------------------------------会员关怀--------------------------------------------
    @try_except()
    def vip_mentor(self):
        show_head_line("会员关怀")
        self.show_not_ams_act_info("会员关怀")

        if not self.cfg.function_switches.get_vip_mentor or self.disable_most_activities():
            logger.warning("未启用领取会员关怀功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.fetch_pskey()
        if self.lr is None:
            return

        qa = QzoneActivity(self, self.lr)
        qa.vip_mentor()

    # --------------------------------------------QQ空间 新版回归关怀--------------------------------------------
    # note：对接流程与上方黄钻完全一致，参照其流程即可
    @try_except()
    def dnf_vip_mentor(self):
        get_act_url("会员关怀")
        show_head_line("QQ空间会员关怀")
        self.show_not_ams_act_info("会员关怀")

        if not self.cfg.function_switches.get_vip_mentor or self.disable_most_activities():
            logger.warning("未启用领取QQ空间会员关怀功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.fetch_pskey()
        if self.lr is None:
            return

        # 礼包二
        lucky_act_id = "67613_73c7557f"
        self.qzone_act_op("关怀礼包 - 当前角色", lucky_act_id)
        self.qzone_act_op(
            "关怀礼包 - 尝试使用配置关怀角色",
            lucky_act_id,
            act_req_data=self.try_make_lucky_user_req_data(
                "关怀", self.cfg.vip_mentor.guanhuai_dnf_server_id, self.cfg.vip_mentor.guanhuai_dnf_role_id
            ),
        )

        self.qzone_act_op("每日登录游戏增加两次抽奖机会", "67615_38806738")
        for idx in range_from_one(10):
            res = self.qzone_act_op(f"尝试第{idx}次抽奖", "67616_c33730b6")
            if res.get("Data", "") == "":
                break

    # --------------------------------------------DNF强者之路--------------------------------------------
    @try_except()
    def dnf_strong(self):
        show_head_line("DNF强者之路功能")
        self.show_amesvr_act_info(self.dnf_strong_op)

        if not self.cfg.function_switches.get_dnf_strong or self.disable_most_activities():
            logger.warning("未启用DNF强者之路功能，将跳过")
            return

        self.check_dnf_strong()

        def query_ticket_count():
            res = self.dnf_strong_op("查询数据", "747206", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue2)

        self.dnf_strong_op("领取报名礼包", "747207")
        self.dnf_strong_op("领取排行礼包", "747208")

        self.dnf_strong_op("每日在线30分钟", "747222")
        self.dnf_strong_op("通关一次强者之路 （试炼模式）", "747227")
        self.dnf_strong_op("每日特权网吧登陆", "747228")

        ticket = query_ticket_count()
        logger.info(color("bold_cyan") + f"当前剩余抽奖券数目为：{ticket}")
        for idx in range_from_one(ticket):
            self.dnf_strong_op(f"[{idx}/{ticket}]幸运夺宝", "747209")
            if idx != ticket:
                time.sleep(5)

        self.dnf_strong_op("决赛普发礼包", "761894")
        self.dnf_strong_op("决赛冠军礼包", "761893")

    def check_dnf_strong(self):
        self.check_bind_account(
            "DNF强者之路",
            get_act_url("DNF强者之路"),
            activity_op_func=self.dnf_strong_op,
            query_bind_flowid="747146",
            commit_bind_flowid="747145",
        )

    def dnf_strong_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_strong

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF强者之路"),
            **extra_params,
        )

    # --------------------------------------------管家蚊子腿--------------------------------------------
    # note: 管家活动接入流程：
    #   1. 打开新活动的页面 get_act_url("管家蚊子腿-旧版")
    #   2. 按F12，在Console中输入 console.log(JSON.stringify(GLOBAL_AMP_CONFIG))，将结果复制到 format_json.json 中格式化，方便查看
    #   3. 在json中搜索 comGifts，定位到各个礼包的信息，并将下列变量的数值更新为新版本
    guanjia_common_gifts_act_id = "1160"  # 礼包活动ID
    guanjia_gift_id_special_rights = "7761"  # 电脑管家特权礼包
    guanjia_gift_id_sign_in_2_days = "7762"  # 连续签到2天礼包
    guanjia_gift_id_return_user = "7763"  # 幸运勇士礼包
    guanjia_gift_id_download_and_login_this_version_guanjia = "7764"  # 下载登录管家任务
    guanjia_gift_id_game_online_30_minutes = "7765"  # 每日游戏在线30分钟任务
    guanjia_gift_id_sign_in = "7766"  # 每日签到任务
    # note: 4. 在json中搜索 lotGifts，定位到抽奖的信息，并将下列变量的数值更新为新版本
    guanjia_lottery_gifts_act_id = "1159"  # 抽奖活动ID

    # note: 5. 启用时取消注释fetch_guanjia_openid中开关，废弃时则注释掉
    # note: 6. 调整urls中管家蚊子腿的起止时间
    # note: 7. 调整config_ui中管家开关
    # note: 8. 修改qq_login中管家活动的url（搜索 /act/cop 即可，共两处，login函数和实际跳转处）

    @try_except()
    def guanjia(self):
        show_head_line("管家蚊子腿")
        self.show_not_ams_act_info("管家蚊子腿")

        if not self.cfg.function_switches.get_guanjia or self.disable_most_activities():
            logger.warning("未启用领取管家蚊子腿活动合集功能，将跳过")
            return

        lr = self.fetch_guanjia_openid()
        if lr is None:
            return
        self.guanjia_lr = lr
        # 等一会，避免报错
        time.sleep(self.common_cfg.retry.request_wait_time)

        self.guanjia_common_gifts_op("电脑管家特权礼包", giftId=self.guanjia_gift_id_special_rights)
        self.guanjia_common_gifts_op("连续签到2天礼包", giftId=self.guanjia_gift_id_sign_in_2_days)
        self.guanjia_common_gifts_op("幸运勇士礼包", giftId=self.guanjia_gift_id_return_user)

        self.guanjia_common_gifts_op(
            "下载安装并登录电脑管家", giftId=self.guanjia_gift_id_download_and_login_this_version_guanjia
        )

        self.guanjia_common_gifts_op("每日游戏在线30分钟", giftId=self.guanjia_gift_id_game_online_30_minutes)
        self.guanjia_common_gifts_op("每日签到任务", giftId=self.guanjia_gift_id_sign_in)

        for _i in range(10):
            res = self.guanjia_lottery_gifts_op("抽奖")
            # {"code": 4101, "msg": "积分不够", "result": []}
            if res["code"] != 0:
                break
            time.sleep(self.common_cfg.retry.request_wait_time)

    def guanjia_common_gifts_op(self, ctx, giftId="", print_res=True):
        return self.guanjia_op(ctx, "comjoin", self.guanjia_common_gifts_act_id, giftId=giftId, print_res=print_res)

    def guanjia_lottery_gifts_op(self, ctx, print_res=True):
        return self.guanjia_op(ctx, "lottjoin", self.guanjia_lottery_gifts_act_id, print_res=print_res)

    def guanjia_op(self, ctx, api_name, act_id, giftId="", print_res=True):
        api = f"{api_name}_{act_id}"
        roleinfo = self.get_dnf_bind_role()
        extra_cookies = f"__qc__openid={self.guanjia_lr.qc_openid}; __qc__k={self.guanjia_lr.qc_k};"
        return self.get(
            ctx,
            self.urls.guanjia,
            api=api,
            giftId=giftId,
            area_id=roleinfo.serviceID,
            charac_no=roleinfo.roleCode,
            charac_name=quote_plus(roleinfo.roleName),
            extra_cookies=extra_cookies,
            is_jsonp=True,
            is_normal_jsonp=True,
            print_res=print_res,
        )

    # --------------------------------------------新管家蚊子腿--------------------------------------------
    # note: 新管家活动接入流程：
    #   1. 打开新活动的页面 get_act_url("管家蚊子腿")
    #   2. 按F12，输入过滤关键词为 -speed -pv? -cap_ -white
    #   3. 随便点个活动按钮，点开过滤出的请求，其中的aid就是活动id
    guanjia_new_act_id = "2022011118372511947"  # 活动ID
    # note: 4. 按照下面的顺序依次点击对应活动按钮，最后按顺序将请求中的lid复制出来
    guanjia_new_gift_id_special_rights = "48"  # 电脑管家特权礼包
    guanjia_new_gift_id_sign_in_2_days = "50"  # 连续签到2天礼包
    guanjia_new_gift_id_return_user = "16"  # 幸运勇士礼包
    guanjia_new_gift_id_download_and_login_this_version_guanjia = "60"  # 下载登录管家任务
    guanjia_new_gift_id_game_online_30_minutes = "58"  # 每日游戏在线30分钟任务
    guanjia_new_gift_id_sign_in = "59"  # 每日签到任务
    # note: 4. 在json中搜索 lotGifts，定位到抽奖的信息，并将下列变量的数值更新为新版本
    guanjia_new_lottery_gifts_act_id = "75"  # 抽奖活动ID

    # note: 5. 调整urls中 管家蚊子腿 的起止时间
    # note: 6. 修改qq_login中管家活动的url（搜索 /act/cop 即可，共两处，login函数和实际跳转处）
    @try_except()
    def guanjia_new(self):
        show_head_line("管家蚊子腿")
        self.show_not_ams_act_info("管家蚊子腿")

        if not self.cfg.function_switches.get_guanjia or self.disable_most_activities():
            logger.warning("未启用领取管家蚊子腿活动合集功能，将跳过")
            return

        logger.warning("管家的活动只负责领取奖励，具体任务条件，如登录管家、签到等请自行完成")

        lr = self.fetch_guanjia_openid()
        if lr is None:
            return
        self.guanjia_lr = lr
        # 等一会，避免报错
        time.sleep(self.common_cfg.retry.request_wait_time)

        def receive(ctx, lid):
            return self.guanjia_new_op(ctx, "pc_sdi_receive/receive", lid)

        def add_draw_pool(ctx, lid):
            return self.guanjia_new_op(ctx, "pc_sdi_receive/add_draw_pool", lid)

        def take_unclaimed_awards():
            raw_res = self.guanjia_new_op(
                "查询领奖信息",
                "lottery.do?method=myNew",
                "",
                page_index=1,
                page_size=1000,
                domain_name="sdi.3g.qq.com",
                print_res=False,
            )
            info = GuanjiaNewQueryLotteryInfo().auto_update_config(raw_res)
            for lr in info.result:
                if lr.has_taken():
                    continue

                # 之前抽奖了，但未领奖
                _take_lottery_award(f"补领取奖励-{lr.drawLogId}-{lr.presentId}-{lr.comment}", lr.drawLogId)

        def lottery(ctx) -> bool:
            lottrey_raw_res = self.guanjia_new_op(
                f"{ctx}-抽奖阶段", "sdi_lottery/lottery", self.guanjia_new_lottery_gifts_act_id
            )
            lottery_res = GuanjiaNewLotteryResult().auto_update_config(lottrey_raw_res)
            success = lottery_res.success == 0
            if success:
                data = lottery_res.data
                _take_lottery_award(f"{ctx}-领奖阶段-{data.drawLogId}-{data.presentId}-{data.comment}", data.drawLogId)

            return success

        def _take_lottery_award(ctx: str, draw_log_id: int):
            self.guanjia_new_op(
                ctx,
                "lottery.do?method=take",
                self.guanjia_new_lottery_gifts_act_id,
                draw_log_id=draw_log_id,
                domain_name="sdi.3g.qq.com",
            )

        receive("电脑管家特权礼包", self.guanjia_new_gift_id_special_rights)
        receive("连续签到2天礼包", self.guanjia_new_gift_id_sign_in_2_days)
        receive("幸运勇士礼包", self.guanjia_new_gift_id_return_user)

        add_draw_pool("下载安装并登录电脑管家", self.guanjia_new_gift_id_download_and_login_this_version_guanjia)

        add_draw_pool("每日游戏在线30分钟", self.guanjia_new_gift_id_game_online_30_minutes)
        add_draw_pool("每日签到任务", self.guanjia_new_gift_id_sign_in)

        for _i in range(10):
            success = lottery("抽奖")
            if not success:
                break
            time.sleep(self.common_cfg.retry.request_wait_time)

        # 补领取之前未领取的奖励
        take_unclaimed_awards()

    # note: 新管家活动接入流程：
    #   1. 打开新活动的页面 get_act_url("管家蚊子腿")
    #   2. 按F12，输入过滤关键词为 -speed -pv? -cap_ -white
    #   3. 随便点个活动按钮，点开过滤出的请求，其中的aid就是活动id
    guanjia_new_dup_act_id = "2021090614400611010"  # 活动ID
    # note: 4. 按照下面的顺序依次点击对应活动按钮，最后按顺序将请求中的lid复制出来
    guanjia_new_dup_gift_id_special_rights = "48"  # 电脑管家特权礼包
    guanjia_new_dup_gift_id_sign_in_2_days = "50"  # 连续签到2天礼包
    guanjia_new_dup_gift_id_return_user = "16"  # 幸运勇士礼包
    guanjia_new_dup_gift_id_download_and_login_this_version_guanjia = "60"  # 下载登录管家任务
    guanjia_new_dup_gift_id_game_online_30_minutes = "58"  # 每日游戏在线30分钟任务
    guanjia_new_dup_gift_id_sign_in = "59"  # 每日签到任务
    # note: 4. 在json中搜索 lotGifts，定位到抽奖的信息，并将下列变量的数值更新为新版本
    guanjia_new_dup_lottery_gifts_act_id = "75"  # 抽奖活动ID

    # note: 5. 调整urls中 管家蚊子腿 的起止时间
    # note: 6. 修改qq_login中管家活动的url（搜索 /act/cop 即可，共两处，login函数和实际跳转处）
    @try_except()
    def guanjia_new_dup(self):
        show_head_line("管家蚊子腿")
        self.show_not_ams_act_info("管家蚊子腿")

        if not self.cfg.function_switches.get_guanjia or self.disable_most_activities():
            logger.warning("未启用领取管家蚊子腿活动合集功能，将跳过")
            return

        logger.warning("管家的活动只负责领取奖励，具体任务条件，如登录管家、签到等请自行完成")

        lr = self.fetch_guanjia_openid()
        if lr is None:
            return
        self.guanjia_lr = lr
        # 等一会，避免报错
        time.sleep(self.common_cfg.retry.request_wait_time)

        def receive(ctx, lid):
            return self.guanjia_new_dup_op(ctx, "pc_sdi_receive/receive", lid)

        def add_draw_pool(ctx, lid):
            return self.guanjia_new_dup_op(ctx, "pc_sdi_receive/add_draw_pool", lid)

        def take_unclaimed_awards():
            raw_res = self.guanjia_new_dup_op(
                "查询领奖信息",
                "lottery.do?method=myNew",
                "",
                page_index=1,
                page_size=1000,
                domain_name="sdi.3g.qq.com",
                print_res=False,
            )
            info = GuanjiaNewQueryLotteryInfo().auto_update_config(raw_res)
            for lr in info.result:
                if lr.has_taken():
                    continue

                # 之前抽奖了，但未领奖
                _take_lottery_award(f"补领取奖励-{lr.drawLogId}-{lr.presentId}-{lr.comment}", lr.drawLogId)

        def lottery(ctx) -> bool:
            lottrey_raw_res = self.guanjia_new_dup_op(
                f"{ctx}-抽奖阶段", "sdi_lottery/lottery", self.guanjia_new_dup_lottery_gifts_act_id
            )
            lottery_res = GuanjiaNewLotteryResult().auto_update_config(lottrey_raw_res)
            success = lottery_res.success == 0
            if success:
                data = lottery_res.data
                _take_lottery_award(f"{ctx}-领奖阶段-{data.drawLogId}-{data.presentId}-{data.comment}", data.drawLogId)

            return success

        def _take_lottery_award(ctx: str, draw_log_id: int):
            self.guanjia_new_dup_op(
                ctx,
                "lottery.do?method=take",
                self.guanjia_new_dup_lottery_gifts_act_id,
                draw_log_id=draw_log_id,
                domain_name="sdi.3g.qq.com",
            )

        receive("电脑管家特权礼包", self.guanjia_new_dup_gift_id_special_rights)
        receive("连续签到2天礼包", self.guanjia_new_dup_gift_id_sign_in_2_days)
        receive("幸运勇士礼包", self.guanjia_new_dup_gift_id_return_user)

        add_draw_pool("下载安装并登录电脑管家", self.guanjia_new_dup_gift_id_download_and_login_this_version_guanjia)

        add_draw_pool("每日游戏在线30分钟", self.guanjia_new_dup_gift_id_game_online_30_minutes)
        add_draw_pool("每日签到任务", self.guanjia_new_dup_gift_id_sign_in)

        for _i in range(10):
            success = lottery("抽奖")
            if not success:
                break
            time.sleep(self.common_cfg.retry.request_wait_time)

        # 补领取之前未领取的奖励
        take_unclaimed_awards()

    def guanjia_new_op(
        self,
        ctx: str,
        api_name: str,
        lid: str,
        draw_log_id=0,
        page_index=1,
        page_size=1000,
        domain_name="sdi.m.qq.com",
        print_res=True,
    ):
        return self._guanjia_new_op(
            self.guanjia_new_act_id, ctx, api_name, lid, draw_log_id, page_index, page_size, domain_name, print_res
        )

    def guanjia_new_dup_op(
        self,
        ctx: str,
        api_name: str,
        lid: str,
        draw_log_id=0,
        page_index=1,
        page_size=1000,
        domain_name="sdi.m.qq.com",
        print_res=True,
    ):
        return self._guanjia_new_op(
            self.guanjia_new_dup_act_id, ctx, api_name, lid, draw_log_id, page_index, page_size, domain_name, print_res
        )

    def _guanjia_new_op(
        self,
        act_id: str,
        ctx: str,
        api_name: str,
        lid: str,
        draw_log_id=0,
        page_index=1,
        page_size=1000,
        domain_name="sdi.m.qq.com",
        print_res=True,
    ):
        roleinfo = self.get_dnf_bind_role()

        openid = self.guanjia_lr.qc_openid
        nickname = self.guanjia_lr.qc_nickname
        key = self.guanjia_lr.qc_access_token

        extra_cookies = f"__qc__openid={self.guanjia_lr.qc_openid}; __qc__k={self.guanjia_lr.qc_k};"

        req = GuanjiaNewRequest()
        req.aid = req.bid = act_id
        req.lid = lid
        req.openid = req.account = req.gjid = openid
        req.nickname = nickname
        req.key = req.accessToken = req.token = key
        req.accessToken = "QQ"
        req.loginType = "qq"
        req.outVeri = 1
        req.roleArea = req.area = str(roleinfo.serviceID)
        req.roleid = str(roleinfo.roleCode)
        req.check = 0
        req.drawLogId = draw_log_id
        req.pageIndex = page_index
        req.pageSize = page_size

        return self.post(
            ctx,
            self.urls.guanjia_new,
            domain_name=domain_name,
            api=api_name,
            json=to_raw_type(req),
            extra_cookies=extra_cookies,
            print_res=print_res,
        )

    def fetch_guanjia_openid(self, print_warning=True):
        # 检查当前是否管家活动在生效中
        enabled_payed_act_funcs = [func for name, func in self.payed_activities()]
        if (
            self.guanjia not in enabled_payed_act_funcs
            and self.guanjia_new not in enabled_payed_act_funcs
            and self.guanjia_new_dup not in enabled_payed_act_funcs
        ):
            logger.debug("管家活动当前未生效，无需尝试更新p_skey")
            return

        # 检查是否启用管家相关活动
        any_enabled = False
        for activity_enabled in [
            self.cfg.function_switches.get_guanjia and not self.disable_most_activities(),
        ]:
            if activity_enabled:
                any_enabled = True
        if not any_enabled:
            if print_warning:
                logger.warning("未启用管家相关活动，将跳过尝试更新管家p_skey流程")
            return

        if self.cfg.function_switches.disable_login_mode_guanjia:
            logger.warning("已禁用管家登录模式，将跳过尝试更新管家信息流程")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            if print_warning:
                logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # 仅支持扫码登录和自动登录
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            if print_warning:
                logger.warning("目前仅支持扫码登录和自动登录，请修改登录方式，否则将跳过该功能")
            return None

        cached_guanjia_login_result = self.load_guanjia_login_result()
        need_update = (
            cached_guanjia_login_result is None
            or self.is_guanjia_openid_expired(cached_guanjia_login_result)
            or cached_guanjia_login_result.guanjia_skey_version != guanjia_skey_version
        )

        if need_update:
            logger.warning("管家openid需要更新，将尝试重新登录电脑管家网页获取并保存到本地")
            logger.warning(
                color("bold_cyan")
                + "如果一直卡在管家登录流程，可能是你网不行，建议多试几次，真不行就关闭管家活动的开关~"
            )
            # 重新获取
            ql = QQLogin(self.common_cfg)
            if self.cfg.login_mode == "qr_login":
                # 扫码登录
                lr = ql.qr_login(ql.login_mode_guanjia, name=self.cfg.name, account=self.cfg.account_info.account)
            else:
                # 自动登录
                lr = ql.login(
                    self.cfg.account_info.account,
                    self.cfg.account_info.password,
                    ql.login_mode_guanjia,
                    name=self.cfg.name,
                )
            # 保存
            self.save_guanjia_login_result(lr)
        else:
            lr = cached_guanjia_login_result

        return lr

    def is_guanjia_openid_expired(self, cached_guanjia_login_result: LoginResult):
        if cached_guanjia_login_result is None:
            return True

        self.guanjia_lr = cached_guanjia_login_result

        # 这些算已过期
        # {"code": 29, "msg": "请求包参数错误", "result": []}
        # {"code": 7004, "msg": "获取openid失败", "result": []}
        # {"code": 7005, "msg": "获取accToken失败", "result": []}
        # {"code": 29, "msg": "请求包参数错误", "result": []}
        # {"message": "", "success": -100}

        # 这些不算
        # {"message": "您已领取过", "success": -110}
        # {"message": "活动已结束", "success": -105}

        # res = self.guanjia_common_gifts_op("每日签到任务", giftId=self.guanjia_gift_id_sign_in, print_res=False)
        # return res["code"] in [7004, 7005, 29]

        res = self.guanjia_new_op(
            "每日签到任务", "pc_sdi_receive/add_draw_pool", self.guanjia_new_gift_id_sign_in, print_res=False
        )
        # res = self.guanjia_new_dup_op("每日签到任务", "pc_sdi_receive/add_draw_pool", self.guanjia_new_dup_gift_id_sign_in, print_res=False)
        return res["success"] in [-100]

    def save_guanjia_login_result(self, lr: LoginResult):
        # 本地缓存
        lr.guanjia_skey_version = guanjia_skey_version
        lr.save_to_json_file(self.get_local_saved_guanjia_openid_file())
        logger.debug(f"本地保存管家openid信息，具体内容如下：{lr}")

    def load_guanjia_login_result(self) -> LoginResult | None:
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return None

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_guanjia_openid_file()):
            return None

        with open(self.get_local_saved_guanjia_openid_file(), encoding="utf-8") as f:
            raw_loginResult = json.load(f)
            loginResult = LoginResult().auto_update_config(raw_loginResult)
            logger.debug(f"读取本地缓存的管家openid信息，具体内容如下：{loginResult}")
            return loginResult

    def get_local_saved_guanjia_openid_file(self):
        return self.local_saved_guanjia_openid_file.format(self.cfg.name)

    # --------------------------------------------DNF十三周年庆活动--------------------------------------------
    @try_except()
    def dnf_13(self):
        show_head_line("DNF十三周年庆活动")
        self.show_amesvr_act_info(self.dnf_13_op)

        if not self.cfg.function_switches.get_dnf_13 or self.disable_most_activities():
            logger.warning("未启用领取DNF十三周年庆活动功能，将跳过")
            return

        self.check_dnf_13()

        def query_lottery_count():
            res = self.dnf_13_op("查询剩余抽奖次数", "772683", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue1)

        for idx in range_from_one(5):
            self.dnf_13_op(f"点击第{idx}个icon，领取抽奖机会", "769465", index=idx)

        send_list = self.cfg.dnf_13_send_qq_list
        if len(send_list) == 0:
            logger.info("在配置工具中添加13周年赠送QQ列表（最多三个），可额外领取抽奖次数")
        elif len(send_list) > 3:
            send_list = self.cfg.dnf_13_send_qq_list[:3]

        if not self.cfg.function_switches.disable_share:
            for qq in send_list:
                self.dnf_13_op(f"发送分享消息，额外增加抽奖机会-{qq}", "771230", receiveUin=qq)

        lc = query_lottery_count()
        logger.info(f"当前剩余抽奖次数为{lc}次")
        for idx in range_from_one(lc):
            self.dnf_13_op(f"第{idx}/{lc}次抽奖", "771234")

    def check_dnf_13(self):
        self.check_bind_account(
            "qq视频-DNF十三周年庆活动",
            get_act_url("DNF十三周年庆活动"),
            activity_op_func=self.dnf_13_op,
            query_bind_flowid="768385",
            commit_bind_flowid="768384",
        )

    def dnf_13_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_13
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF十三周年庆活动"),
            **extra_params,
        )

    # --------------------------------------------qq视频-AME活动--------------------------------------------
    @try_except()
    def qq_video_amesvr(self):
        show_head_line("qq视频-AME活动")
        self.show_amesvr_act_info(self.qq_video_amesvr_op)

        if not self.cfg.function_switches.get_qq_video_amesvr or self.disable_most_activities():
            logger.warning("未启用领取qq视频-AME活动活动合集功能，将跳过")
            return

        self.check_qq_video_amesvr()

        def query_signin_days():
            res = self.qq_video_amesvr_op("查询签到状态", "789433", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue1)

        self.qq_video_amesvr_op("验证幸运用户", "789422")
        self.qq_video_amesvr_op("幸运用户礼包", "789425")
        self.qq_video_amesvr_op("勇士见面礼包", "789439")
        self.qq_video_amesvr_op("分享领取", "789437")

        self.qq_video_amesvr_op("在线30分钟礼包", "789429")
        logger.warning(color("bold_yellow") + f"累计已签到{query_signin_days()}天")
        self.qq_video_amesvr_op("签到3天礼包", "789430")
        self.qq_video_amesvr_op("签到7天礼包", "789431")
        self.qq_video_amesvr_op("签到15天礼包", "789432")

    def check_qq_video_amesvr(self):
        self.check_bind_account(
            "qq视频-AME活动",
            get_act_url("qq视频-AME活动"),
            activity_op_func=self.qq_video_amesvr_op,
            query_bind_flowid="789417",
            commit_bind_flowid="789416",
        )

    def qq_video_amesvr_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_qq_video_amesvr

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("qq视频-AME活动"),
            **extra_params,
        )

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

    def get_dnf_bind_role(self) -> RoleInfo | None:
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

    def post(
        self,
        ctx,
        url,
        data=None,
        json=None,
        pretty=False,
        print_res=True,
        is_jsonp=False,
        is_normal_jsonp=False,
        need_unquote=True,
        extra_cookies="",
        check_fn: Callable[[requests.Response], Exception | None] | None = check_tencent_game_common_status_code,
        extra_headers: dict[str, str] | None = None,
        disable_retry=False,
        use_this_cookies="",
        prefix_to_remove="",
        suffix_to_remove="",
        **params,
    ) -> dict:
        return {}

    def qq(self) -> str:
        return uin2qq(self.uin())

    def fetch_club_vip_p_skey(self, param):
        pass

    def get_qzone_act_req_data(self, act_req_data, extra_act_req_data):
        pass

    def show_amesvr_act_info(self, activity_op_func):
        pass

    def check_bind_account(
        self,
        activity_name,
        activity_url,
        activity_op_func,
        query_bind_flowid,
        commit_bind_flowid,
        try_auto_bind=True,
        roleinfo: RoleInfo | None = None,
        roleinfo_source="道聚城所绑定的角色",
        act_can_change_bind=True,
    ):
        pass

    def amesvr_request(
        self,
        ctx,
        amesvr_host,
        sServiceDepartment,
        sServiceType,
        iActivityId,
        iFlowId,
        print_res,
        eas_url: str,
        extra_cookies="",
        show_info_only=False,
        get_act_info_only=False,
        append_raw_data="",
        **data_extra_params,
    ) -> dict | AmsActInfo | None:
        return {}

    def payed_activities(self) -> list[tuple[str, Callable]]:
        return []

    def qzone_act_op(self, ctx, sub_act_id, act_req_data=None, extra_act_req_data: dict | None = None, print_res=True):
        return {}

    def try_make_lucky_user_req_data(
        self, act_name: str, lucky_dnf_server_id: str, lucky_dnf_role_id: str
    ) -> dict | None:
        return {}

    def fetch_share_p_skey(self, ctx: str, cache_max_seconds: int = 600) -> str:
        return ""

    def show_dnf_helper_info_guide(self, extra_msg="", show_message_box_once_key="", always_show_message_box=False):
        pass

    def parse_jifenOutput(self, res: dict, count_id: str) -> tuple[int, int]:
        return 0, 0

    def temporary_change_bind_and_do(
        self,
        ctx: str,
        change_bind_role_infos: list[TemporaryChangeBindRoleInfo],
        check_func: Callable,
        callback_func: Callable[[RoleInfo], bool],
        need_try_func: Callable[[RoleInfo], bool] | None = None,
    ):
        return

    def guide_to_bind_account(
        self,
        activity_name,
        activity_url,
        activity_op_func=None,
        query_bind_flowid="",
        commit_bind_flowid="",
        try_auto_bind=False,
        bind_reason="未绑定角色",
        roleinfo: RoleInfo | None = None,
        roleinfo_source="道聚城所绑定的角色",
    ):
        pass

    def get_vuserid(self) -> str:
        return getattr(self, "vuserid", "")

    def try_do_with_lucky_role_and_normal_role(
        self, ctx: str, check_role_func: Callable, action_callback: Callable[[RoleInfo], bool]
    ):
        pass

    def get_dnf_bind_role_copy(self) -> RoleInfo:
        return self.get_dnf_bind_role().clone()

    def query_dnf_rolelist_for_temporary_change_bind(
        self, base_force_name="", role_name=""
    ) -> list[TemporaryChangeBindRoleInfo]:
        return []

    def format(self, url, **params):
        return ""

    def uin(self) -> str:
        return self.cfg.account_info.uin

    def get_dnf_roleinfo(self, roleinfo: RoleInfo | None = None):
        return AmesvrQueryRole()

    def ide_check_bind_account(
        self,
        activity_name: str,
        activity_url: str,
        activity_op_func: Callable,
        sAuthInfo: str,
        sActivityInfo: str,
        roleinfo: RoleInfo | None = None,
        roleinfo_source="道聚城所绑定的角色",
    ):
        pass

    def ide_request(
        self,
        ctx: str,
        ide_host: str,
        iActivityId: str,
        iFlowId: str,
        print_res: bool,
        eas_url: str,
        extra_cookies="",
        show_info_only=False,
        get_act_info_only=False,
        sIdeToken="",
        **data_extra_params,
    ) -> dict | IdeActInfo | None:
        return {}

    def fetch_login_result(
        self,
        ctx: str,
        login_mode: str,
        cache_max_seconds: int = 0,
        cache_validate_func: Callable[[Any], bool] | None = None,
        print_warning=True,
    ) -> LoginResult:
        return LoginResult()

    def parse_condOutput(self, res: dict, cond_id: str) -> int:
        return 0


def watch_live():
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    RunAll = True
    indexes = [1]
    if RunAll:
        indexes = [i + 1 for i in range(len(cfg.account_configs))]

    totalTime = 2 * 60 + 5  # 为了保险起见，多执行5分钟
    logger.info(f"totalTime={totalTime}")

    for t in range(totalTime):
        timeStart = datetime.datetime.now()
        logger.info(color("bold_yellow") + f"开始执行第{t + 1}分钟的流程")
        for idx in indexes:  # 从1开始，第i个
            account_config = cfg.account_configs[idx - 1]
            if not account_config.is_enabled() or account_config.cannot_bind_dnf_v2:
                logger.warning("账号被禁用或无法绑定DNF，将跳过")
                continue

            djcHelper = DjcHelper(account_config, cfg.common)
            djcHelper.check_skey_expired()

            djcHelper.dnf_carnival_live()

        totalUsed = (datetime.datetime.now() - timeStart).total_seconds()
        if totalUsed < 60:
            waitTime = 60.1 - totalUsed
            logger.info(color("bold_cyan") + f"本轮累积用时{totalUsed}秒，将休息{waitTime}秒")
            time.sleep(waitTime)
