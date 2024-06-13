from __future__ import annotations

import datetime
import functools
import json
import math
import os
import random
import re
import string
import time
import uuid
from multiprocessing import Pool
from typing import Any, Callable
from urllib import parse
from urllib.parse import parse_qsl, quote, quote_plus, unquote_plus, urlparse

import requests

import json_parser
from black_list import check_in_black_list
from config import AccountConfig, CommonConfig, ExchangeItemConfig, XinYueOperationConfig, config, load_config
from const import appVersion, cached_dir, guanjia_skey_version, sVersionName, vscode_online_url
from dao import (
    XIN_YUE_MIN_LEVEL,
    AmesvrCommonModRet,
    AmesvrQueryFriendsInfo,
    AmesvrQueryRole,
    AmesvrUserBindInfo,
    BuyInfo,
    ColgBattlePassInfo,
    ColgBattlePassQueryInfo,
    ComicDataList,
    DnfChronicleMatchServerAddUserRequest,
    DnfChronicleMatchServerCommonResponse,
    DnfChronicleMatchServerRequestUserRequest,
    DnfChronicleMatchServerRequestUserResponse,
    DnfCollectionInfo,
    DnfHelperChronicleBasicAwardInfo,
    DnfHelperChronicleBasicAwardList,
    DnfHelperChronicleBindInfo,
    DnfHelperChronicleExchangeGiftInfo,
    DnfHelperChronicleExchangeList,
    DnfHelperChronicleLotteryList,
    DnfHelperChronicleSignGiftInfo,
    DnfHelperChronicleSignList,
    DnfHelperChronicleUserActivityTopInfo,
    DnfHelperChronicleUserTaskList,
    DnfRoleInfo,
    DnfRoleInfoList,
    GameRoleInfo,
    GoodsInfo,
    GuanjiaNewLotteryResult,
    GuanjiaNewQueryLotteryInfo,
    GuanjiaNewRequest,
    HuyaActTaskInfo,
    HuyaUserTaskInfo,
    IdeActInfo,
    LuckyUserInfo,
    LuckyUserTaskConf,
    MaJieLuoInfo,
    MobileGameGiftInfo,
    MoJieRenInfo,
    MyHomeFarmInfo,
    MyHomeFriendDetail,
    MyHomeFriendList,
    MyHomeGift,
    MyHomeGiftList,
    MyHomeInfo,
    MyHomeValueGift,
    NewArkLotteryAgreeRequestCardResult,
    NewArkLotteryCardCountInfo,
    NewArkLotteryLotteryCountInfo,
    NewArkLotteryRequestCardResult,
    NewArkLotterySendCardResult,
    RankUserInfo,
    RoleInfo,
    SailiyamWorkInfo,
    ShenJieGrowUpCurStageData,
    ShenJieGrowUpInfo,
    ShenJieGrowUpStagePack,
    ShenJieGrowUpTaskData,
    SpringFuDaiInfo,
    TemporaryChangeBindRoleInfo,
    VoteEndWorkInfo,
    VoteEndWorkList,
    XiaojiangyouInfo,
    XiaojiangyouPackageInfo,
    XinYueBattleGroundWpeBindRole,
    XinYueBattleGroundWpeGetBindRoleResult,
    XinYueBgwUserInfo,
    XinyueCatInfo,
    XinyueCatInfoFromApp,
    XinyueCatMatchResult,
    XinyueCatUserInfo,
    XinyueFinancingInfo,
    XinYueInfo,
    XinYueMatchServerAddTeamRequest,
    XinYueMatchServerCommonResponse,
    XinYueMatchServerRequestTeamRequest,
    XinYueMatchServerRequestTeamResponse,
    XinYueMyTeamInfo,
    XinYueSummaryTeamInfo,
    XinYueTeamAwardInfo,
    XinYueTeamGroupInfo,
    XinyueWeeklyGiftInfo,
    XinyueWeeklyGPointsInfo,
    parse_amesvr_common_info,
)
from data_struct import to_raw_type
from db import (
    CacheDB,
    CacheInfo,
    DianzanDB,
    DnfHelperChronicleExchangeListDB,
    DnfHelperChronicleUserActivityTopInfoDB,
    FireCrackersDB,
    WelfareDB,
)
from encrypt import make_dnf_helper_signature, make_dnf_helper_signature_data
from exceptions_def import (
    ArkLotteryTargetQQSendByRequestReachMaxCount,
    DnfHelperChronicleTokenExpiredOrWrongException,
    GithubActionLoginException,
    SameAccountTryLoginAtMultipleThreadsException,
)
from first_run import is_daily_first_run, is_first_run, is_monthly_first_run, is_weekly_first_run, reset_first_run
from game_info import get_game_info, get_game_info_by_bizcode
from log import color, logger
from network import Network, check_tencent_game_common_status_code, extract_qq_video_message, jsonp_callback_flag
from qq_login import LoginResult, QQLogin
from qzone_activity import QzoneActivity
from server import get_match_server_api
from setting import dnf_server_id_to_area_info, dnf_server_id_to_name, parse_card_group_info_map, zzconfig
from sign import getACSRFTokenForAMS, getMillSecondsUnix
from urls import (
    Urls,
    get_act_url,
    get_ams_act,
    get_ams_act_desc,
    get_ide_act,
    get_ide_act_desc,
    get_not_ams_act,
    get_not_ams_act_desc,
    not_know_end_time____,
    search_act,
)
from usage_count import increase_counter
from util import (
    async_message_box,
    base64_str,
    double_quote,
    double_unquote,
    extract_between,
    filter_unused_params_catch_exception,
    format_now,
    format_time,
    get_first_exists_dict_value,
    get_last_week_monday_datetime,
    get_logger_func,
    get_meaningful_call_point_for_log,
    get_month,
    get_now,
    get_now_unix,
    get_this_thursday_of_dnf,
    get_this_week_monday_datetime,
    get_today,
    get_week,
    is_act_expired,
    json_compact,
    md5,
    message_box,
    now_after,
    now_before,
    now_in_range,
    padLeftRight,
    parse_time,
    parse_url_param,
    pause,
    pause_and_exit,
    post_json_to_data,
    range_from_one,
    remove_suffix,
    show_end_time,
    show_head_line,
    show_quick_edit_mode_tip,
    start_and_end_date_of_a_month,
    tableify,
    triple_quote,
    try_except,
    uin2qq,
    use_by_myself,
    utf8len,
    wait_for,
    will_act_expired_in,
    with_cache,
    with_retry,
)


# DNF蚊子腿小助手
class DjcHelper:
    local_saved_skey_file = os.path.join(cached_dir, ".saved_skey.{}.json")
    local_saved_pskey_file = os.path.join(cached_dir, ".saved_pskey.{}.json")
    local_saved_guanjia_openid_file = os.path.join(cached_dir, ".saved_guanjia_openid.{}.json")

    local_saved_teamid_file = os.path.join(cached_dir, ".teamid_v2.{}.json")

    def __init__(self, account_config, common_config, user_buy_info: BuyInfo | None = None):
        self.cfg: AccountConfig = account_config
        self.common_cfg: CommonConfig = common_config

        self.zzconfig = zzconfig()

        # 初始化部分字段
        self.lr: LoginResult | None = None

        # 配置加载后，尝试读取本地缓存的skey
        self.local_load_uin_skey()

        # 初始化网络相关设置
        self.init_network()

        # 相关链接
        self.urls = Urls()

        self.user_buy_info = user_buy_info

    # --------------------------------------------一些辅助函数--------------------------------------------

    def init_network(self):
        self.network = Network(self.cfg.sDeviceID, self.uin(), self.cfg.account_info.skey, self.common_cfg)

    def check_skey_expired(self, window_index=1):
        # note: 使用一些长期有效的活动（如旧版心悦战场、福利中心）的接口来判断skey是否过期
        #   未过期:
        #       {"flowRet": {...}, "modRet": {...}, "ret": "0", "msg": ""}
        #       {"ret": "-1", "msg": "目前访问人数过多！请稍后再试！谢谢！", "flowRet": {...}}
        #   已过期:
        #     {"ret": "101", "msg": "非常抱歉，请先登录！", "flowRet": ...}
        # re:
        #   活动本身结束，无法判断skey是否过期
        #     {"ret": "301", "msg": "非常抱歉，该活动已经结束！", "flowRet": ...}
        # res = self.xinyue_battle_ground_op("判断skey是否过期", "767160", print_res=False)
        # res = self.dnf_welfare_op("判断skey是否过期", "649261", print_res=False)

        res = self.dnf_comic_ide_op("判断skey是否过期", "248455", print_res=False)

        if use_by_myself():
            if str(res["ret"]) == "301":
                async_message_box(
                    "用于判断skey是否过期的活动本身已经结束，需要看下是否需要换个新活动来判断",
                    "(仅自己可见)skey活动结束",
                )

        if str(res["ret"]) != "101":
            # skey尚未过期，则重新刷一遍，主要用于从qq空间获取的情况
            account_info = self.cfg.account_info
            self.save_uin_skey(account_info.uin, account_info.skey, self.get_vuserid())
        else:
            # 已过期，更新skey
            logger.info("")
            logger.warning(f"账号({self.cfg.name})的skey已过期，即将尝试更新skey")
            self.update_skey(window_index=window_index)

        # skey获取完毕后，检查是否在黑名单内
        check_in_black_list(self.uin())

    def update_skey(self, window_index=1):
        if self.cfg.function_switches.disable_login_mode_normal:
            logger.warning("禁用了普通登录模式，将不会尝试更新skey")
            return

        login_mode_dict: dict[str, Callable[[int], None]] = {
            "by_hand": self.update_skey_by_hand,
            "qr_login": self.update_skey_qr_login,
            "auto_login": self.update_skey_auto_login,
        }
        login_mode_dict[self.cfg.login_mode](window_index)

    def update_skey_by_hand(self, window_index=1):
        js_code = """cookies=Object.fromEntries(document.cookie.split(/; */).map(cookie => cookie.split('=', 2)));console.log("uin="+cookies.uin+"\\nskey="+cookies.skey+"\\n");"""
        fallback_js_code = """document.cookie.split(/; */);"""
        logger.error(
            "skey过期，请按下列步骤获取最新skey并更新到配置中\n"
            "1. 在本脚本自动打开的活动网页中使用通用登录组件完成登录操作\n"
            "   1.1 指点击（亲爱的玩家，请【登录】）中的登录按钮，并完成后续登录操作\n"
            "2. 点击F12，将默认打开DevTools（开发者工具界面）的Console界面\n"
            "       如果默认不是该界面，则点击上方第二个tab（Console）（中文版这个tab的名称可能是命令行？）\n"
            "3. 在下方输入区输入下列内容来从cookie中获取uin和skey（或者直接粘贴，默认已复制到系统剪贴板里了）\n"
            f"       {js_code}\n"
            "-- 如果上述代码执行报错，可能是因为浏览器不支持，这时候可以复制下面的代码进行上述操作\n"
            "  执行后，应该会显示一个可点开的内容，戳一下会显示各个cookie的内容，然后手动在里面查找uin和skey即可\n"
            f"       {fallback_js_code}\n"
            "3. 将uin/skey的值分别填写到config.toml中对应配置的值中即可\n"
            "4. 填写dnf的区服和手游的区服信息到config.toml中\n"
            "5. 正常使用还需要填写完成后再次运行脚本，获得角色相关信息，并将信息填入到config.toml中\n"
            "\n"
            f"具体信息为可见前面的日志"
        )
        # 打开配置界面
        cfgFile = "./config.toml"
        localCfgFile = "./config.toml.local"
        if os.path.isfile(localCfgFile):
            cfgFile = localCfgFile
        async_message_box(
            f"请使用网页版vscode或者下载个本地版的vscode打开【{cfgFile}】文件 第53行 来自行修改~",
            "提示",
            open_url=vscode_online_url,
        )
        # # 复制js代码到剪贴板，方便复制
        # pyperclip.copy(js_code)
        # 打开活动界面
        os.popen("start https://dnf.qq.com/lbact/a20200716wgmhz/index.html?wg_ad_from=loginfloatad")
        # 提示
        input("\n完成上述操作后点击回车键即可退出程序，重新运行即可...")
        pause_and_exit(-1)

    def update_skey_qr_login(self, window_index=1):
        qqLogin = QQLogin(self.common_cfg, window_index=window_index)
        loginResult = qqLogin.qr_login(
            QQLogin.login_mode_normal, name=self.cfg.name, account=self.cfg.account_info.account
        )
        self.save_uin_skey(loginResult.uin, loginResult.skey, loginResult.vuserid)

    def update_skey_auto_login(self, window_index=1):
        qqLogin = QQLogin(self.common_cfg, window_index=window_index)
        ai = self.cfg.account_info
        loginResult = qqLogin.login(ai.account, ai.password, QQLogin.login_mode_normal, name=self.cfg.name)
        self.save_uin_skey(loginResult.uin, loginResult.skey, loginResult.vuserid)

    def save_uin_skey(self, uin, skey, vuserid):
        self.memory_save_uin_skey(uin, skey)

        self.local_save_uin_skey(uin, skey, vuserid)

    def local_save_uin_skey(self, uin, skey, vuserid):
        # 本地缓存
        self.set_vuserid(vuserid)
        with open(self.get_local_saved_skey_file(), "w", encoding="utf-8") as sf:
            loginResult = {
                "uin": str(uin),
                "skey": str(skey),
                "vuserid": str(vuserid),
            }
            json.dump(loginResult, sf)
            logger.debug(f"本地保存skey信息，具体内容如下：{loginResult}")

        logger.debug("同时由于在pskey的缓存中也有一份skey数据, 去读取过来更新这部分字段，确保两边最终一致")
        cached_pskey = self.load_uin_pskey()
        if cached_pskey is not None:
            self.save_uin_pskey(
                cached_pskey["p_uin"],
                cached_pskey["p_skey"],
                skey,
                vuserid,
            )

    def local_load_uin_skey(self):
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_skey_file()):
            return

        with open(self.get_local_saved_skey_file(), encoding="utf-8") as f:
            try:
                loginResult = json.load(f)
            except json.decoder.JSONDecodeError:
                logger.error(f"账号 {self.cfg.name} 的skey缓存已损坏，将视为已过期")
                return

            self.memory_save_uin_skey(loginResult["uin"], loginResult["skey"])
            self.set_vuserid(loginResult.get("vuserid", ""))
            logger.debug(f"读取本地缓存的skey信息，具体内容如下：{loginResult}")

    def get_local_saved_skey_file(self):
        return self.local_saved_skey_file.format(self.cfg.name)

    def memory_save_uin_skey(self, uin, skey):
        # 保存到内存中
        self.cfg.updateUinSkey(uin, skey)

        # uin, skey更新后重新初始化网络相关
        self.init_network()

    def set_vuserid(self, vuserid: str):
        self.vuserid = vuserid

    def get_vuserid(self) -> str:
        return getattr(self, "vuserid", "")

    # --------------------------------------------获取角色信息和游戏信息--------------------------------------------

    @with_retry(max_retry_count=3)
    def get_bind_role_list(self, print_warning=True):
        self.fetch_djc_login_info("获取绑定角色列表", print_warning)

        # 查询全部绑定角色信息
        res = self.get(
            "获取道聚城各游戏的绑定角色列表",
            self.urls.query_bind_role_list,
            print_res=False,
            use_this_cookies=self.djc_custom_cookies,
        )

        roleinfo_list = res.get("data", [])

        db = CacheInfo()
        db.with_context(f"绑定角色缓存/{self.cfg.get_account_cache_key()}").load()
        if len(roleinfo_list) != 0:
            # 成功请求时，保存一份数据到本地
            db.value = roleinfo_list
            db.save()
        else:
            get_logger_func(print_warning)("获取绑定角色失败了，尝试使用本地缓存的角色信息")
            logger.debug(f"缓存的信息为 {db.value}")
            roleinfo_list = db.value or []

        self.bizcode_2_bind_role_map = {}
        for roleinfo_dict in roleinfo_list:
            role_info = GameRoleInfo().auto_update_config(roleinfo_dict)
            self.bizcode_2_bind_role_map[role_info.sBizCode] = role_info

    def get_dnf_bind_role_copy(self) -> RoleInfo:
        return self.get_dnf_bind_role().clone()

    def get_dnf_bind_role(self) -> RoleInfo | None:
        roleinfo = None

        if self.cfg.bind_role.has_config():
            # 如果配置了绑定角色，则优先使用这个
            server_id, role_id = self.cfg.bind_role.dnf_server_id, self.cfg.bind_role.dnf_role_id

            role_info_from_web = self.query_dnf_role_info_by_serverid_and_roleid(server_id, role_id)
            server_name = dnf_server_id_to_name(server_id)
            area_info = dnf_server_id_to_area_info(server_id)

            # 构造一份道聚城绑定角色信息，简化改动
            djc_role_info = RoleInfo()
            djc_role_info.roleCode = role_id
            djc_role_info.roleName = role_info_from_web.rolename
            djc_role_info.serviceID = server_id
            djc_role_info.serviceName = server_name
            djc_role_info.areaID = area_info.v
            djc_role_info.areaName = area_info.t

            logger.debug("使用本地配置的角色来领奖")
            roleinfo = djc_role_info
        else:
            # 否则尝试使用道聚城绑定的角色信息
            game_name = "dnf"
            if game_name in self.bizcode_2_bind_role_map:
                roleinfo = self.bizcode_2_bind_role_map[game_name].sRoleInfo

        return roleinfo

    def get_fz_bind_role(self) -> RoleInfo | None:
        """
        获取命运方舟的绑定角色信息
        """
        roleinfo = None

        game_name = "fz"
        if game_name in self.bizcode_2_bind_role_map:
            roleinfo = self.bizcode_2_bind_role_map[game_name].sRoleInfo

        return roleinfo

    def get_mobile_game_info(self):
        # 如果游戏名称设置为【任意手游】，则从绑定的手游中随便挑一个
        if self.cfg.mobile_game_role_info.use_any_binded_mobile_game():
            found_binded_game = False
            for _bizcode, bind_role_info in self.bizcode_2_bind_role_map.items():
                if bind_role_info.is_mobile_game():
                    self.cfg.mobile_game_role_info.game_name = bind_role_info.sRoleInfo.gameName
                    found_binded_game = True
                    logger.warning(
                        f"当前手游名称配置为任意手游，将从道聚城已绑定的手游中随便选一个，挑选为：{self.cfg.mobile_game_role_info.game_name}"
                    )
                    break

            if not found_binded_game:
                return None

        return get_game_info(self.cfg.mobile_game_role_info.game_name)

    # --------------------------------------------各种操作--------------------------------------------
    def run(self, user_buy_info: BuyInfo):
        self.normal_run(user_buy_info)

    # 预处理阶段
    def check_djc_role_binding(self) -> bool:
        # 指引获取uin/skey/角色信息等
        self.check_skey_expired()

        # 尝试获取绑定的角色信息
        self.get_bind_role_list()

        # 检查绑定信息
        binded = True
        if self.cfg.function_switches.get_djc:
            # 检查道聚城是否已绑定dnf角色信息，若未绑定则警告（这里不停止运行是因为可以不配置领取dnf的道具）
            if not self.cfg.cannot_bind_dnf_v2 and "dnf" not in self.bizcode_2_bind_role_map:
                logger.warning(
                    color("fg_bold_yellow") + "未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定"
                )
                binded = False

            # if self.cfg.mobile_game_role_info.enabled() and not self.check_mobile_game_bind():
            #     logger.warning(color("fg_bold_green") + "！！！请注意，我说的是手游，不是DNF！！！")
            #     logger.warning(color("fg_bold_green") + "如果不需要做道聚城的手游任务和许愿任务（不做会少豆子），可以在配置工具里将手游名称设为无")
            #     binded = False

        if binded:
            if self.cfg.function_switches.get_djc:
                # 打印dnf和手游的绑定角色信息
                logger.info("已获取道聚城目前绑定的角色信息如下")
                games = []
                if "dnf" in self.bizcode_2_bind_role_map:
                    games.append("dnf")
                # if self.cfg.mobile_game_role_info.enabled():
                #     games.append(self.get_mobile_game_info().bizCode)

                for bizcode in games:
                    roleinfo = self.bizcode_2_bind_role_map[bizcode].sRoleInfo
                    logger.info(
                        f"{roleinfo.gameName}: ({roleinfo.serviceName}-{roleinfo.roleName}-{roleinfo.roleCode})"
                    )
            else:
                logger.warning("当前账号未启用道聚城相关功能")

        if self.cfg.bind_role.has_config():
            # 若本地配置了领奖角色，则强制认为已绑定
            binded = True

        return binded

    def check_mobile_game_bind(self):
        # 检查配置的手游是否有效
        gameinfo = self.get_mobile_game_info()
        if gameinfo is None:
            logger.warning(
                color("fg_bold_yellow")
                + "当前手游名称配置为【任意手游】，但未在道聚城找到任何绑定的手游，请前往道聚城绑定任意一个手游，如王者荣耀"
            )
            return False

        # 检查道聚城是否已绑定该手游的角色，若未绑定则警告并停止运行
        bizcode = gameinfo.bizCode
        if bizcode not in self.bizcode_2_bind_role_map:
            logger.warning(
                color("fg_bold_yellow")
                + f"未在道聚城绑定手游【{get_game_info_by_bizcode(bizcode).bizName}】的角色信息，请前往道聚城app进行绑定。"
            )
            logger.warning(
                color("fg_bold_cyan")
                + "若想绑定其他手游则调整【配置工具】配置的手游名称，"
                + color("fg_bold_blue")
                + "若不启用则将手游名称调整为无"
            )
            return False

        # 检查这个游戏是否是手游
        role_info = self.bizcode_2_bind_role_map[bizcode]
        if not role_info.is_mobile_game():
            logger.warning(
                color("fg_bold_yellow") + f"【{get_game_info_by_bizcode(bizcode).bizName}】是端游，不是手游。"
            )
            logger.warning(
                color("fg_bold_cyan")
                + "若想绑定其他手游则调整【配置工具】配置的手游名称，"
                + color("fg_bold_blue")
                + "若不启用则将手游名称调整为无"
            )
            return False

        return True

    # 正式运行阶段
    def normal_run(self, user_buy_info: BuyInfo):
        # 检查skey是否过期
        self.check_skey_expired()

        # 获取dnf和手游的绑定信息
        self.get_bind_role_list()

        # 运行活动
        activity_funcs_to_run = self.get_activity_funcs_to_run(user_buy_info)

        for _act_name, activity_func in activity_funcs_to_run:
            activity_func()

        # # 以下为并行执行各个活动的调用方式
        # # 由于下列原因，该方式基本确定不会再使用
        # # 1. amesvr活动服务器会限制调用频率，如果短时间内请求过快，会返回401，并提示请求过快
        # #    而多进程处理活动的时候，会非常频繁的触发这种情况，感觉收益不大。另外频繁触发这个警报，感觉也有可能会被腾讯风控，到时候就得不偿失了
        # # 2. python的multiprocessing.pool.Pool不支持在子进程中再创建新的子进程
        # #    因此在不同账号已经在不同的进程下运行的前提下，子进程下不能再创建新的子进程了
        # async_run_all_act(self.cfg, self.common_cfg, activity_funcs_to_run)

    def get_activity_funcs_to_run(self, user_buy_info: BuyInfo) -> list[tuple[str, Callable]]:
        activity_funcs_to_run = []
        activity_funcs_to_run.extend(self.free_activities())
        if user_buy_info.is_active():
            # 付费期间将付费活动也加入到执行列表中
            activity_funcs_to_run.extend(self.payed_activities())

        return activity_funcs_to_run

    @try_except(show_exception_info=False)
    def show_activities_summary(self, user_buy_info: BuyInfo):
        # 需要运行的活动
        free_activities = self.free_activities()
        paied_activities = self.payed_activities()

        # 展示活动的信息
        def get_activities_summary(categray: str, activities: list) -> str:
            activities_summary = ""
            if len(activities) != 0:
                activities_summary += f"\n目前的{categray}活动如下："

                heads = ["序号", "活动名称", "结束于", "剩余天数", "活动链接为"]
                colSizes = [4, 24, 12, 8, 50]

                activities_summary += "\n" + color("bold_green") + tableify(heads, colSizes)
                for idx, name_and_func in enumerate(activities):
                    act_name, act_func = name_and_func

                    op_func_name = act_func.__name__ + "_op"

                    end_time = parse_time(not_know_end_time____)
                    # 可能是非ams活动
                    act_info = None
                    try:
                        act_info = get_not_ams_act(act_name)
                        if act_info is None and hasattr(self, op_func_name):
                            # 可能是ams或ide活动
                            act_info = getattr(self, op_func_name)("获取活动信息", "", get_act_info_only=True)
                    except Exception as e:
                        logger.debug(f"请求{act_name} 出错了", exc_info=e)

                    if act_info is not None:
                        end_time = parse_time(act_info.get_endtime())

                    line_color = "bold_green"
                    if is_act_expired(format_time(end_time)):
                        line_color = "bold_black"

                    end_time_str = format_time(end_time, "%Y-%m-%d")
                    remaining_days = (end_time - get_now()).days
                    print_act_name = padLeftRight(act_name, colSizes[1], mode="left", need_truncate=True)
                    act_url = padLeftRight(get_act_url(act_name), colSizes[-1], mode="left")

                    # activities_summary += with_color(line_color, f'\n    {idx + 1:2d}. {print_act_name} 将结束于{end_time_str}(剩余 {remaining_days:3d} 天)，活动链接为： {act_url}')
                    activities_summary += (
                        "\n"
                        + color(line_color)
                        + tableify(
                            [idx + 1, print_act_name, end_time_str, remaining_days, act_url],
                            colSizes,
                            need_truncate=False,
                        )
                    )
            else:
                activities_summary += f"\n目前尚无{categray}活动，当新的{categray}活动出现时会及时加入~"

            return activities_summary

        # 提示如何复制
        if self.common_cfg.disable_cmd_quick_edit:
            show_quick_edit_mode_tip()

        # 免费活动信息
        free_activities_summary = get_activities_summary("长期免费", free_activities)
        show_head_line("以下为免费的长期活动", msg_color=color("bold_cyan"))
        logger.info(free_activities_summary)

        # 付费活动信息
        paied_activities_summary = get_activities_summary("短期付费", paied_activities)
        show_head_line("以下为付费期间才会运行的短期活动", msg_color=color("bold_cyan"))

        if not user_buy_info.is_active():
            if user_buy_info.total_buy_month != 0:
                msg = f"账号{user_buy_info.qq}的付费内容已到期，到期时间点为{user_buy_info.expire_at}。"
            else:
                msg = f"账号{user_buy_info.qq}未购买付费内容。"
            msg += "\n因此2021-02-06之后添加的短期新活动将被跳过，如果想要启用该部分内容，可查看目录中的【付费指引/付费指引.docx】，目前定价为5元每月。"
            msg += "\n2021-02-06之前添加的所有活动不受影响，仍可继续使用。"
            msg += "\n具体受影响的活动内容如下"

            logger.warning(color("bold_yellow") + msg)

        logger.info(paied_activities_summary)

    def free_activities(self) -> list[tuple[str, Callable]]:
        return [
            ("道聚城", self.djc_operations),
            ("DNF地下城与勇士心悦特权专区", self.xinyue_battle_ground),
            ("心悦app", self.xinyue_app_operations),
            ("dnf论坛签到", self.dnf_bbs),
            ("小酱油周礼包和生日礼包", self.xiaojiangyou),
            ("DNF福利中心兑换", self.dnf_welfare),
        ]

    def payed_activities(self) -> list[tuple[str, Callable]]:
        # re: 更新新的活动时记得更新urls.py的 not_ams_activities
        # ? NOTE: 同时顺带更新 配置工具功能开关列表 act_category_to_act_desc_switch_list
        # undone: 常用过滤词 -aegis -beacon -log?sCloudApiName -.png -.jpg -.gif -.js -.css  -.ico -data:image -.mp4 -pingfore.qq.com -.mp3 -.wav -logs.game.qq.com -fx_fe_report -trace.qq.com -.woff2 -.TTF -.otf -snowflake.qq.com -vd6.l.qq.com -doGPMReport -wuji/object -thumbplayer -get_video_mark_all
        return [
            ("DNF助手编年史", self.dnf_helper_chronicle),
            ("绑定手机活动", self.dnf_bind_phone),
            ("DNF漫画预约活动", self.dnf_comic),
            ("DNF神界成长之路", self.dnf_shenjie_grow_up),
            ("DNF神界成长之路二期", self.dnf_shenjie_grow_up_v2),
            ("DNF落地页活动_ide", self.dnf_luodiye_ide),
            ("DNF周年庆登录活动", self.dnf_anniversary),
            ("超级会员", self.dnf_super_vip),
            ("集卡", self.dnf_ark_lottery),
            ("DNF卡妮娜的心愿摇奖机", self.dnf_kanina),
        ]

    def expired_activities(self) -> list[tuple[str, Callable]]:
        # re: 记得过期活动全部添加完后，一个个确认下确实过期了
        return [
            ("DNF落地页活动_ide_dup", self.dnf_luodiye_ide_dup),
            ("colg每日签到", self.colg_signin),
            ("勇士的冒险补给", self.maoxian),
            ("DNFxSNK", self.dnf_snk),
            ("9163补偿", self.dnf_9163_apologize),
            ("超核勇士wpe", self.dnf_chaohe_wpe),
            ("DNF年货铺", self.dnf_nianhuopu),
            ("DNF心悦wpe", self.dnf_xinyue_wpe),
            ("dnf助手活动wpe", self.dnf_helper_wpe),
            ("colg其他活动", self.colg_other_act),
            ("拯救赛利亚", self.dnf_save_sailiyam),
            ("WeGame活动", self.dnf_wegame),
            ("DNF马杰洛的规划", self.majieluo),
            ("神界预热", self.dnf_shenjie_yure),
            ("qq视频蚊子腿-爱玩", self.qq_video_iwan),
            ("DNF落地页活动", self.dnf_luodiye),
            ("DNF预约", self.dnf_reservation),
            ("DNF娱乐赛", self.dnf_game),
            ("dnf助手活动", self.dnf_helper),
            ("腾讯游戏信用礼包", self.get_credit_xinyue_gift),
            ("黑钻礼包", self.get_heizuan_gift),
            ("DNF心悦", self.dnf_xinyue),
            ("DNF心悦Dup", self.dnf_xinyue_dup),
            ("dnf周年拉好友", self.dnf_anniversary_friend),
            ("心悦app理财礼卡", self.xinyue_financing),
            ("冒险的起点", self.maoxian_start),
            ("DNF巴卡尔竞速", self.dnf_bakaer),
            ("和谐补偿活动", self.dnf_compensate),
            ("巴卡尔对战地图", self.dnf_bakaer_map_ide),
            ("巴卡尔大作战", self.dnf_bakaer_fight),
            ("魔界人探险记", self.mojieren),
            ("DNF集合站", self.dnf_collection),
            ("dnf助手活动Dup", self.dnf_helper_dup),
            ("心悦app周礼包", self.xinyue_weekly_gift),
            ("DNF闪光杯", self.dnf_shanguang),
            ("DNF冒险家之路", self.dnf_maoxian_road),
            ("超享玩", self.super_core),
            ("我的小屋", self.dnf_my_home),
            ("DNF集合站_ide", self.dnf_collection_ide),
            ("幸运勇士", self.dnf_lucky_user),
            ("会员关怀", self.dnf_vip_mentor),
            ("KOL", self.dnf_kol),
            ("黄钻", self.dnf_yellow_diamond),
            ("心悦猫咪", self.xinyue_cat),
            ("DNF互动站", self.dnf_interactive),
            ("DNF格斗大赛", self.dnf_pk),
            ("DNF共创投票", self.dnf_dianzan),
            ("翻牌活动", self.dnf_card_flip),
            ("hello语音（皮皮蟹）网页礼包兑换", self.hello_voice),
            ("管家蚊子腿", self.guanjia_new),
            ("组队拜年", self.team_happy_new_year),
            ("新职业预约活动", self.dnf_reserve),
            ("WeGame活动_新版", self.wegame_new),
            ("DNF公会活动", self.dnf_gonghui),
            ("关怀活动", self.dnf_guanhuai),
            ("DNF记忆", self.dnf_memory),
            ("DNF名人堂", self.dnf_vote),
            ("qq视频蚊子腿", self.qq_video),
            ("WeGameDup", self.dnf_wegame_dup),
            ("轻松之路", self.dnf_relax_road),
            ("命运的抉择挑战赛", self.dnf_mingyun_jueze),
            ("管家蚊子腿", self.guanjia_new_dup),
            ("虎牙", self.huya),
            ("wegame国庆活动【秋风送爽关怀常伴】", self.wegame_guoqing),
            ("微信签到", self.wx_checkin),
            ("10月女法师三觉", self.dnf_female_mage_awaken),
            ("dnf助手排行榜", self.dnf_rank),
            ("2020DNF嘉年华页面主页面签到", self.dnf_carnival),
            ("DNF进击吧赛利亚", self.xinyue_sailiyam),
            ("阿拉德勇士征集令", self.dnf_warriors_call),
            ("dnf漂流瓶", self.dnf_drift),
            ("暖冬好礼活动", self.warm_winter),
            ("史诗之路来袭活动合集", self.dnf_1224),
            ("新春福袋大作战", self.spring_fudai),
            ("燃放爆竹活动", self.firecrackers),
            ("DNF福签大作战", self.dnf_fuqian),
            ("会员关怀", self.vip_mentor),
            ("DNF强者之路", self.dnf_strong),
            ("管家蚊子腿", self.guanjia),
            ("DNF十三周年庆活动", self.dnf_13),
            ("集卡_旧版", self.ark_lottery),
            ("qq视频-AME活动", self.qq_video_amesvr),
            ("qq会员杯", self.dnf_club_vip),
        ]

    # --------------------------------------------道聚城--------------------------------------------
    @try_except()
    def djc_operations(self):
        show_head_line("开始道聚城相关操作")
        self.show_not_ams_act_info("道聚城")

        if not self.cfg.function_switches.get_djc:
            logger.warning("未启用领取道聚城功能，将跳过")
            return

        self.fetch_djc_login_info("获取道聚城登录信息")

        # ------------------------------初始工作------------------------------
        old_allin, old_balance = self.query_balance("1. 操作前：查询余额")
        # self.query_money_flow("1.1 操作前：查一遍流水")

        # ------------------------------核心逻辑------------------------------
        # 自动签到
        self.sign_in_and_take_awards()

        # 完成任务
        self.complete_tasks()

        # 领取奖励并兑换道具
        self.take_task_awards_and_exchange_items()

        # ------------------------------清理工作------------------------------
        new_allin, new_balance = self.query_balance("5. 操作全部完成后：查询余额")
        # self.query_money_flow("5.1 操作全部完成后：查一遍流水")

        delta = new_allin - old_allin
        logger.warning(
            color("fg_bold_yellow")
            + f"账号 {self.cfg.name} 本次道聚城操作共获得 {delta} 个豆子（历史总获取： {old_allin} -> {new_allin}  余额： {old_balance} -> {new_balance} ）"
        )

    @try_except(return_val_on_except=(0, 0))
    def query_balance(self, ctx, print_res=True) -> tuple[int, int]:
        res = self.raw_query_balance(ctx, print_res)

        if int(res["ret"]) != 0:
            logger.warning(color("bold_cyan") + f"查询聚豆余额异常，返回结果为 {res}")
            return 0, 0

        info = res["data"]
        allin, balance = int(info["allin"]), int(info["balance"])
        return allin, balance

    def raw_query_balance(self, ctx, print_res=True):
        return self.get(ctx, self.urls.balance, print_res=print_res, use_this_cookies=self.djc_custom_cookies)

    def query_money_flow(self, ctx):
        return self.get(ctx, self.urls.money_flow)

    # urls.sign签到接口偶尔会报 401 Unauthorized，因此需要加一层保护，确保不影响其他流程
    @try_except()
    def sign_in_and_take_awards(self):
        self.get("2.1.2 发送app登录事件", self.urls.user_login_event, use_this_cookies=self.djc_custom_cookies)

        total_try = self.common_cfg.retry.max_retry_count
        for try_idx in range_from_one(total_try):
            try:
                # 签到
                # note: 如果提示下面这行这样的日志，则尝试下载最新apk包，解包后确认下 aes_key 与 djc_rsa_public_key_new.der 是否有变动，若有变动，则替换为新的
                #   目前访问人数过多！请稍后再试！谢谢！
                # note:
                #   aes_key: 用 jadx-gui 反编译apk包后，搜索 sDjcSign，在这行里那个字符串就是
                #   djc_rsa_public_key_new.der: 解压apk包后，在 assets 目录里可以找到这个，用 HxD 等二进制对比工具看看是否与 utils/reference_data/public_key.der 的目录一直
                #
                # 签到流程@see assets/homepage_recommend_follow.js 搜索 自动签到的workflow
                self.post("2.2 签到", self.urls.sign, self.sign_flow_data("96939"))
                self.post("2.3 领取签到赠送的聚豆", self.urls.sign, self.sign_flow_data("324410"))

                # 尝试领取自动签到的奖励
                # 查询本月签到的日期列表
                res = self.post("查询签到", self.urls.sign, self.sign_flow_data("321961"), print_res=False)
                month_total_signed_days = int(res["modRet"]["jData"]["monthNum"])
                logger.info(f"本月签到次数为 {month_total_signed_days}")

                # 根据本月已签到数，领取符合条件的每月签到若干日的奖励（也就是聚豆页面最上面的那个横条）

                sign_reward_rule_list = [
                    ("累计3天领取5聚豆", "322021"),
                    ("累计7天领取15聚豆", "322036"),
                    ("累计10天领取20聚豆", "322037"),
                    ("累计15天领取25聚豆", "322038"),
                    ("累计20天领取30聚豆", "322039"),
                    ("累计25天领取50聚豆", "322040"),
                    ("累计签到整月-全勤奖", "881740"),
                ]
                for ctx, iFlowId in sign_reward_rule_list:
                    res = self.post(ctx, self.urls.sign, self.sign_flow_data(iFlowId))
                    # 你的签到次数不够，请继续努力哦~
                    if "签到次数不够" in res["flowRet"]["sMsg"]:
                        break
                break
            except json.decoder.JSONDecodeError as e:
                logger.error(f"第 {try_idx}/{total_try} 次尝试道聚城签到相关操作失败了，等待一会重试", exc_info=e)
                if try_idx != total_try:
                    wait_for("道聚城签到操作失败", self.common_cfg.retry.retry_wait_time)

    def sign_flow_data(self, iFlowId):
        return self.format(self.urls.sign_raw_data, iFlowId=iFlowId)

    def djc_operations_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_djc_operations

        return self.amesvr_request(
            ctx,
            "comm.ams.game.qq.com",
            "djc",
            "dj",
            iActivityId,
            iFlowId,
            print_res,
            "",
            **extra_params,
        )

    def complete_tasks(self):
        # 完成《打卡活动中心》 @see assets\activity_home.js 搜索 activity_center
        self.get(
            "3.1 模拟点开活动中心",
            self.urls.task_report,
            task_type="activity_center",
            use_this_cookies=self.djc_custom_cookies,
        )

        if self.cfg.mobile_game_role_info.enabled():
            # 完成《礼包达人》
            self.take_mobile_game_gift()
        else:
            async_message_box(
                f"账号 {self.cfg.name} 未启用自动完成《礼包达人》任务功能，如需启用，请配置道聚城的手游名称。不配置，则每日任务的豆子会领不全",
                "道聚城参数未配置",
                show_once=True,
            )

        if self.cfg.function_switches.make_wish:
            # todo: 完成《有理想》
            self.make_wish()
        else:
            async_message_box(
                f"账号 {self.cfg.name} 未启用自动完成《有理想》任务功能，如需启用，请打开道聚城许愿功能。不配置，则每日任务的豆子会领不全",
                "道聚城参数未配置",
                show_once=True,
            )

        # todo: 浏览3个活动

    @try_except()
    def take_mobile_game_gift(self):
        game_info = self.get_mobile_game_info()
        role_info = self.bizcode_2_bind_role_map[game_info.bizCode].sRoleInfo

        giftInfos = self.get_mobile_game_gifts()
        if len(giftInfos) == 0:
            logger.warning(f"未找到手游【{game_info.bizName}】的有效七日签到配置，请换个手游，比如王者荣耀")
            return

        dayIndex = datetime.datetime.now().weekday()  # 0-周一...6-周日，恰好跟下标对应
        giftInfo = giftInfos[dayIndex]

        # 很抱歉，您的请求签名校验未通过，请稍后再试哦！
        # fixme: 这个会提示签名不对，但是看了代码，暂时没发现是为啥，先不管了，以后能弄懂再解决这个
        self.get(
            f"3.2 一键领取{role_info.gameName}日常礼包-{giftInfo.sTask}",
            self.urls.receive_game_gift,
            bizcode=game_info.bizCode,
            iruleId=giftInfo.iRuleId,
            systemID=role_info.systemID,
            sPartition=role_info.areaID,
            channelID=role_info.channelID,
            channelKey=role_info.channelKey,
            roleCode=role_info.roleCode,
            sRoleName=quote_plus(role_info.roleName),
            use_this_cookies=self.djc_custom_cookies,
        )

    @try_except()
    def make_wish(self):
        bizCode = "yxzj"
        if bizCode not in self.bizcode_2_bind_role_map:
            logger.warning(
                color("fg_bold_cyan")
                + "未在道聚城绑定王者荣耀，将跳过许愿功能。建议使用安卓模拟器下载道聚城，在上面绑定王者荣耀"
            )
            return

        roleModel = self.bizcode_2_bind_role_map[bizCode].sRoleInfo
        if "苹果" in roleModel.channelKey:
            logger.warning(
                color("fg_bold_cyan")
                + f"ios端不能许愿手游，建议使用安卓模拟器下载道聚城，在上面绑定王者荣耀。roleModel={roleModel}"
            )
            return

        # 查询许愿道具信息
        query_wish_item_list_res = self.get(
            "3.3.0  查询许愿道具",
            self.urls.query_wish_goods_list,
            plat=roleModel.systemID,
            biz=roleModel.bizCode,
            print_res=False,
        )
        if "data" not in query_wish_item_list_res or len(query_wish_item_list_res["data"]) == 0:
            logger.warning(
                f"在{roleModel.systemKey}上游戏【{roleModel.gameName}】暂不支持许愿，query_wish_item_list_res={query_wish_item_list_res}"
            )
            return

        # 查询许愿列表
        wish_list_res = self.get(
            "3.3.1 查询许愿列表",
            self.urls.query_wish,
            appUid=self.qq(),
            use_this_cookies=self.djc_custom_cookies,
            print_res=False,
        )

        # 删除已经许愿的列表，确保许愿成功
        for wish_info in wish_list_res["data"]["list"]:
            ctx = f"3.3.2 删除已有许愿-{wish_info['bizName']}-{wish_info['sGoodsName']}"
            self.get(ctx, self.urls.delete_wish, sKeyId=wish_info["sKeyId"], use_this_cookies=self.djc_custom_cookies)

        for raw_propModel in query_wish_item_list_res["data"]["goods"]:
            propModel = GoodsInfo()
            propModel.auto_update_config(raw_propModel)

            # 许愿
            param = {
                "iActionId": propModel.type,
                "iGoodsId": propModel.valiDate[0].code,
                "sBizCode": roleModel.bizCode,
            }
            if roleModel.type == "0":
                # 端游
                if roleModel.serviceID != "":
                    param["iZoneId"] = roleModel.serviceID
                else:
                    param["iZoneId"] = roleModel.areaID
                param["sZoneDesc"] = quote_plus(roleModel.serviceName)
            else:
                # 手游
                if roleModel.serviceID != "" and roleModel.serviceID != "0":
                    param["partition"] = roleModel.serviceID
                elif roleModel.areaID != "" and roleModel.areaID != "0":
                    param["partition"] = roleModel.areaID
                param["iZoneId"] = roleModel.channelID
                if int(roleModel.systemID) < 0:
                    param["platid"] = 0
                else:
                    param["platid"] = roleModel.systemID
                param["sZoneDesc"] = quote_plus(roleModel.serviceName)

            if roleModel.bizCode == "lol" and roleModel.accountId != "":
                param["sRoleId"] = roleModel.accountId
            else:
                param["sRoleId"] = roleModel.roleCode

            param["sRoleName"] = quote_plus(roleModel.roleName)
            param["sGetterDream"] = quote_plus("不要888！不要488！9.98带回家")

            wish_res = self.get(
                "3.3.3 完成许愿任务", self.urls.make_wish, **param, use_this_cookies=self.djc_custom_cookies
            )

            # 检查许愿结果
            ret = wish_res["ret"]
            # 部分情况需要继续尝试下一个
            if ret in ["-6114"]:
                # {"ret": "-6114", "msg": "您在该区服下未拥有对应英雄，无法购买[露娜-霜月吟]皮肤，如已购买英雄，请等待5分钟再购买皮肤！"}
                logger.info(f"游戏【{roleModel.gameName}】当前道具 {propModel.propName} 不满足许愿条件，尝试下一个")
                continue

            # 其他情况则不再尝试后续的
            if ret == "-8735":
                # {"ret": "-8735", "msg": "该业务暂未开放许愿", "sandbox": false, "serverTime": 1601375249, "event_id": "DJC-DJ-0929182729-P8DDy9-3-534144", "data": []}
                logger.warning(
                    f"游戏【{roleModel.gameName}】暂未开放许愿，请换个道聚城许愿界面中支持的游戏来进行许愿哦，比如王者荣耀~"
                )

            break

    @try_except()
    def take_task_awards_and_exchange_items(self):
        # 领取奖励
        # 领取《礼包达人》
        self.take_task_award("4.1.1", "100066", "礼包达人")
        # 领取《绝不错亿》
        self.take_task_award("4.1.2", "100040", "绝不错亿")
        # 领取《有理想》
        self.take_task_award("4.1.3", "302124", "有理想")
        # 领取《活跃度银宝箱》
        self.take_task_award("4.1.4", "100001", "活跃度银宝箱")
        # 领取《活跃度金宝箱》
        self.take_task_award("4.1.5", "100002", "活跃度金宝箱")

        self.take_djc_boxes("兑换道具前先尝试领取一次宝箱")

        # 兑换所需道具
        self.exchange_djc_items()

        # 领取《兑换有礼》
        self.take_task_award("4.3.1", "327091", "兑换有礼")

        self.take_djc_boxes("兑换道具前后再尝试一次")

    @try_except()
    def take_djc_boxes(self, ctx):
        logger.info(color("bold_green") + ctx)

        # 领取《活跃度银宝箱》
        self.take_task_award("4.1.4", "100001", "活跃度银宝箱")
        # 领取《活跃度金宝箱》
        self.take_task_award("4.1.5", "100002", "活跃度金宝箱")

    @try_except()
    def take_task_award(self, prefix, iRuleId, taskName=""):
        ctx = f"{prefix} 领取任务-{taskName}-奖励"
        self.get(ctx, self.urls.take_task_reward, iruleId=iRuleId)

    # 尝试领取每日任务奖励
    def can_take_task_award(self, taskinfo, iRuleId):
        opt_tasks = taskinfo["data"]["list"]["day"].copy()
        for _id, task in taskinfo["data"]["chest_list"].items():
            opt_tasks.append(task)
        for tinfo in opt_tasks:
            if int(iRuleId) == int(tinfo["iruleId"]):
                return int(tinfo["iCurrentNum"]) >= int(tinfo["iCompleteNum"])

        return False

    @try_except()
    def exchange_djc_items(self):
        if len(self.cfg.exchange_items) == 0:
            logger.warning("未配置兑换道具，跳过该流程")
            return

        for ei in self.cfg.exchange_items:
            self.exchange_one_type_of_djc_item(ei)

    @try_except()
    def exchange_one_type_of_djc_item(self, ei: ExchangeItemConfig):
        retryCfg = self.common_cfg.retry
        for _i in range(ei.count):
            for try_index in range(retryCfg.max_retry_count):
                res = self.exchange_djc_item(f"4.2 兑换 【{ei.get_biz_name()}】 {ei.sGoodsName}", ei)
                if res is None:
                    # 如果对应角色不存在，则跳过本道具
                    logger.info(f"【{ei.get_biz_name()}】未绑定角色，无法领取 {ei.sGoodsName} 将尝试下一个")
                    return

                if int(res.get("ret", "0")) == -9905:
                    logger.warning(
                        f"兑换 {ei.sGoodsName} 时提示 {res.get('msg')} ，等待{retryCfg.retry_wait_time}s后重试（{try_index + 1}/{retryCfg.max_retry_count})"
                    )
                    time.sleep(retryCfg.retry_wait_time)
                    continue

                logger.debug(f"领取 {ei.sGoodsName} ok，等待{retryCfg.request_wait_time}s，避免请求过快报错")
                time.sleep(retryCfg.request_wait_time)
                break

    @try_except()
    def exchange_djc_item(self, ctx: str, ei: ExchangeItemConfig):
        iGoodsSeqId, iActionId, iActionType, bizcode, sGoodsName = (
            ei.iGoodsId,
            ei.iActionId,
            ei.iType,
            ei.sBizCode,
            ei.sGoodsName,
        )

        if bizcode == "dnf":
            # note: dnf仍使用旧的兑换接口，目前仍可用，没必要切换为下面新的，真不能用时再改成用下面的接口
            roleinfo = self.get_dnf_bind_role()

            # 检查是否已在道聚城绑定
            if roleinfo is None:
                async_message_box(
                    f"账号 {self.cfg.name} 未在道聚城绑定dnf角色信息，却配置了兑换dnf道具({sGoodsName})，请移除配置或前往绑定",
                    "道聚城兑换未绑定对应游戏角色",
                )
                return

            return self.get(
                ctx,
                self.urls.exchangeItems,
                iGoodsSeqId=iGoodsSeqId,
                rolename=quote_plus(roleinfo.roleName),
                lRoleId=roleinfo.roleCode,
                iZone=roleinfo.serviceID,
            )

        elif bizcode == "fz":
            roleinfo = self.get_fz_bind_role()

            # 命运方舟的兑换功能仅在付费期间可以使用
            if not self.user_buy_info.is_active():
                async_message_box(
                    f"目前小助手的命运方舟兑换功能仅在付费期间可使用，目前已过期或未付费。账号 {self.cfg.name} 配置了兑换命运方舟道具({sGoodsName})，请移除配置或购买按月付费",
                    "仅付费期间可兑换命运方舟",
                    open_url="https://docs.qq.com/doc/DYkFReHNvVkFEYXJk",
                )
                return

            if is_first_run("仅运行命运方舟提示"):
                async_message_box(
                    (
                        "观察到你配置了命运方舟的道具兑换，因此弹出下面这个提示\n"
                        "部分朋友可能不玩DNF，只想运行命运方舟相关的部分，如有此需求，请点击确认，查看弹出的在线文档中的【仅运行命运方舟相关内容（可选）】节内容进行配置"
                    ),
                    "仅运行命运方舟的提示",
                    show_once=True,
                    open_url="https://docs.qq.com/doc/DYkFReHNvVkFEYXJk",
                )

            # 检查是否已在道聚城绑定
            if roleinfo is None:
                async_message_box(
                    f"账号 {self.cfg.name} 未在道聚城绑定命运方舟角色信息，却配置了兑换命运方舟道具({sGoodsName})，请移除配置或前往绑定",
                    "道聚城兑换未绑定对应游戏角色",
                    open_url="https://docs.qq.com/doc/DYkFReHNvVkFEYXJk",
                )
                return

            return self.get(
                ctx,
                self.urls.new_exchangeItems,
                iGoodsSeqId=iGoodsSeqId,
                iActionId=iActionId,
                iActionType=iActionType,
                bizcode=bizcode,
                platid=roleinfo.platid,
                iZone=roleinfo.area,
                partition=roleinfo.partition,
                lRoleId=roleinfo.roleCode,
                rolename=quote_plus(roleinfo.roleName),
                use_this_cookies=self.djc_custom_cookies,
            )

    def query_all_extra_info(self, dnfServerId: str):
        """
        已废弃，不再需要手动查询该信息
        """
        # 获取玩家的dnf角色列表
        self.query_dnf_rolelist(dnfServerId)
        # 获取玩家的手游角色列表
        self.query_mobile_game_rolelist()

        # # 显示所有可以兑换的道具列表，note：当不知道id时调用
        # self.query_game_gifts("dnf")

    def query_dnf_rolelist(self, dnfServerId: str, need_print=True) -> list[DnfRoleInfo]:
        """
        使用原来的查询接口名称，但内部改为使用缓存，避免短时间内每次调用都实际发送请求，而导致服务器返回请求过于频繁
        """
        warapped_role_info_list: DnfRoleInfoList = with_cache(
            "查询角色列表",
            f"query_dnf_rolelist_{dnfServerId}_{self.cfg.get_account_cache_key()}",
            cache_miss_func=functools.partial(self.query_dnf_rolelist_without_cache_wrapped, dnfServerId, need_print),
            cache_validate_func=lambda role_info_list: len(role_info_list.role_list) != 0,
            cache_max_seconds=60 * 60,
            cache_value_unmarshal_func=DnfRoleInfoList().auto_update_config,
        )

        # 由于缓存时为了方便序列化，套了一层，这里解除这层
        return warapped_role_info_list.role_list

    def query_dnf_rolelist_without_cache_wrapped(self, dnfServerId: str, need_print=True) -> DnfRoleInfoList:
        """
        多套一层这个，方便在缓存时使用 ConfigInterface 提供的序列化功能
        """
        warapped_role_info_list = DnfRoleInfoList()
        warapped_role_info_list.role_list = self.query_dnf_rolelist_without_cache(dnfServerId, need_print)

        return warapped_role_info_list

    def query_dnf_rolelist_without_cache(self, dnfServerId: str, need_print=True) -> list[DnfRoleInfo]:
        """
        向腾讯服务器查询dnf角色列表
        """
        ctx = f"获取账号({self.cfg.name})在服务器({dnf_server_id_to_name(dnfServerId)})的dnf角色列表"
        game_info = get_game_info("地下城与勇士")

        # 做个保底，偶尔这个接口可能会不返回角色信息，比如下面这样
        #   {"version": "V1.0.20210818110349", "retCode": "-1", "serial_num": "AMS-DNF-1024030706-0aZzJ5-980901-5381", "data": "", "msg": "�ǳ���Ǹ�����ڲ����û����࣬�����Ժ��������룬�����������㾴���½�", "checkparam": "", "md5str": "", "infostr": "", "checkstr": "", "user_id_in_game": ""}
        roleLists = []
        for _i in range(3):
            roleListJsonRes = self.get(
                ctx,
                self.urls.get_game_role_list,
                game=game_info.gameCode,
                sAMSTargetAppId=game_info.wxAppid,
                area=dnfServerId,
                platid="",
                partition="",
                is_jsonp=True,
                print_res=False,
            )
            roleLists = json_parser.parse_role_list(roleListJsonRes)
            if len(roleLists) != 0:
                break

            time.sleep(5)

        if need_print:
            lines = []
            lines.append("")
            lines.append("+" * 40)
            lines.append(ctx)
            if len(roleLists) != 0:
                for idx, role in enumerate(roleLists):
                    formatted_force_name = padLeftRight(role.get_force_name(), 10, mode="left")
                    formatted_role_name = padLeftRight(role.rolename, 26, mode="left")
                    lines.append(
                        f"\t第{idx + 1:2d}个角色信息：\tid = {role.roleid:10s} \t名字 = {formatted_role_name} \t职业 = {formatted_force_name} \t等级 = {role.level:3d}"
                    )
            else:
                async_message_box(
                    f"\t未查到dnf服务器({dnf_server_id_to_name(dnfServerId)})上的角色信息，请确认选择了正确的服务器或者在对应区服已创建角色",
                    "提示",
                )
            lines.append("+" * 40)
            logger.info(get_meaningful_call_point_for_log() + "\n".join(lines))

        return roleLists

    def query_dnf_rolelist_for_temporary_change_bind(
        self, base_force_name="", role_name=""
    ) -> list[TemporaryChangeBindRoleInfo]:
        djc_roleinfo = self.get_dnf_bind_role()

        temp_change_bind_roles = []

        roles = self.query_dnf_rolelist(djc_roleinfo.serviceID)
        for role in roles:
            if base_force_name != "" and role.get_force_name() != base_force_name:
                # 若有基础职业限制，则跳过与职业不符合的角色
                continue
            if role_name != "" and role.rolename != role_name:
                # 若指定了名称，则跳过其他角色
                continue

            change_bind_role = TemporaryChangeBindRoleInfo()
            change_bind_role.serviceID = djc_roleinfo.serviceID
            change_bind_role.roleCode = role.roleid

            if role.roleid != djc_roleinfo.roleCode:
                temp_change_bind_roles.append(change_bind_role)
            else:
                # 将当前绑定角色放到最前面
                temp_change_bind_roles.insert(0, change_bind_role)

        return temp_change_bind_roles

    def query_dnf_role_info_by_serverid_and_roleid(self, server_id: str, role_id: str) -> DnfRoleInfo | None:
        logger.debug(f"查询dnf角色信息，server_id={server_id} role_id={role_id}")
        for role in self.query_dnf_rolelist(server_id, False):
            if role.roleid == role_id:
                return role

        return None

    def query_mobile_game_rolelist(self):
        """
        已废弃，不再需要手动查询该信息
        """
        cfg = self.cfg.mobile_game_role_info
        game_info = self.get_mobile_game_info()
        ctx = f"获取账号({self.cfg.name})的{cfg.game_name}角色列表"
        if not cfg.enabled():
            logger.info("未启用自动完成《礼包达人》任务功能")
            return

        roleListJsonRes = self.get(
            ctx,
            self.urls.get_game_role_list,
            game=game_info.gameCode,
            sAMSTargetAppId=game_info.wxAppid,
            area=cfg.area,
            platid=cfg.platid,
            partition=cfg.partition,
            is_jsonp=True,
            print_res=False,
        )
        roleList = json_parser.parse_mobile_game_role_list(roleListJsonRes)
        lines = []
        lines.append("")
        lines.append("+" * 40)
        lines.append(ctx)
        if len(roleList) != 0:
            for idx, role in enumerate(roleList):
                lines.append(f"\t第{idx + 1:2d}个角色信息：\tid = {role.roleid}\t 名字 = {role.rolename}")
        else:
            lines.append(
                f"\t未查到{cfg.game_name} 平台={cfg.platid} 渠道={cfg.area} 区服={cfg.partition}上的角色信息，请确认这些信息已填写正确或者在对应区服已创建角色"
            )
            lines.append(
                f"\t上述id的列表可查阅稍后自动打开的server_list_{game_info.bizName}.js，详情参见config.toml的对应注释"
            )
            lines.append(
                f"\t渠道(area)的id可运行程序在自动打开的utils/reference_data/server_list_{game_info.bizName}.js或手动打开这个文件， 查看 STD_CHANNEL_DATA中对应渠道的v"
            )
            lines.append(
                f"\t平台(platid)的id可运行程序在自动打开的utils/reference_data/server_list_{game_info.bizName}.js或手动打开这个文件， 查看 STD_SYSTEM_DATA中对应平台的v"
            )
            lines.append(
                f"\t区服(partition)的id可运行程序在自动打开的utils/reference_data/server_list_{game_info.bizName}.js或手动打开这个文件， 查看 STD_DATA中对应区服的v"
            )
            self.open_mobile_game_server_list()
        lines.append("+" * 40)
        logger.info("\n".join(lines))

    def open_mobile_game_server_list(self):
        game_info = self.get_mobile_game_info()
        res = requests.get(self.urls.query_game_server_list.format(bizcode=game_info.bizCode), timeout=10)
        server_list_file = f"utils/reference_data/server_list_{game_info.bizName}.js"
        with open(server_list_file, "w", encoding="utf-8") as f:
            f.write(res.text)
        async_message_box(
            f"请使用网页版vscode或者下载个本地版的vscode打开【{server_list_file}】文件来查看手游的相关信息~",
            "提示",
            open_url=vscode_online_url,
        )

    def query_game_gifts(self, biz_code="dnf"):
        self.get(f"查询 {biz_code} 可兑换道具列表", self.urls.show_exchange_item_list, bizcode=biz_code)

    def get_mobile_game_gifts(self):
        game_info = self.get_mobile_game_info()
        data = self.get(
            f"查询 {game_info.bizName} 礼包信息",
            self.urls.query_game_gift_bags,
            bizcode=game_info.bizCode,
            print_res=False,
            use_this_cookies=self.djc_custom_cookies,
        )

        if int(data["ret"]) != 0:
            logger.warning(f"查询 {game_info.bizName} 礼包信息失败，res=\n{data}")
            return []

        sign_in_gifts = []
        for raw_gift in data["data"]["list"]["data"]:
            # iCategory 0-普通礼包 1- 签到礼包 2 -等级礼包  3-登录礼包 4- 任务礼包 5-新版本福利 6-新手礼包 7-道聚城专属礼包 9-抽奖礼包 10-新版签到礼包（支持聚豆补签、严格对应周一到周日）11-好友助力礼包 12-预约中的礼包 13-上线后的礼包
            if int(raw_gift["iCategory"]) == 10:
                sign_in_gifts.append(raw_gift)
        sign_in_gifts.sort(key=lambda gift: gift["iSort"])

        gifts = []
        for gift in sign_in_gifts:
            gifts.append(MobileGameGiftInfo(gift["sTask"], gift["iruleId"]))
        return gifts

    def bind_dnf_role(
        self,
        areaID="30",
        areaName="浙江",
        serviceID="11",
        serviceName="浙江一区",
        roleCode="22370088",
        roleName="∠木星新、",
    ):
        roleInfo = {
            "areaID": areaID,
            "areaName": areaName,
            "bizCode": "dnf",
            "channelID": "",
            "channelKey": "",
            "channelName": "",
            "gameName": "地下城与勇士",
            "isHasService": 1,
            "roleCode": roleCode,
            "roleName": roleName,
            "serviceID": serviceID,
            "serviceName": serviceName,
            "systemID": "",
            "systemKey": "",
            "type": "0",
        }

        self.get(
            f"绑定账号-{serviceName}-{roleName}",
            self.urls.bind_role,
            role_info=json.dumps(roleInfo, ensure_ascii=False),
            is_jsonp=True,
        )

    # --------------------------------------------心悦dnf游戏特权--------------------------------------------
    @try_except()
    def xinyue_battle_ground(self):
        """
        根据配置进行心悦相关操作
        具体活动信息可以查阅 config.example.toml 中 xinyue_operations_v2
        """
        show_head_line("DNF地下城与勇士心悦特权专区")
        self.show_not_ams_act_info("DNF地下城与勇士心悦特权专区")

        if not self.cfg.function_switches.get_xinyue:
            logger.warning("未启用领取心悦特权专区功能，将跳过")
            return

        self.prepare_wpe_act_openid_accesstoken("心悦战场wpe")

        # 查询成就点信息
        old_info = self.query_xinyue_info("6.1 操作前查询成就点信息")

        default_xinyue_operations = [
            (131143, "尝试领取可领的返利勇士币"),
        ]

        # 尝试根据心悦级别领取对应周期礼包
        if old_info.xytype < XIN_YUE_MIN_LEVEL or old_info.is_special_member:
            default_xinyue_operations.extend(
                [
                    (130718, "周礼包_特邀会员"),
                    (130745, "月礼包_特邀会员"),
                ]
            )
        elif old_info.is_xinyue_level(1):
            default_xinyue_operations.extend(
                [
                    (130742, "周礼包_心悦会员1"),
                    (130746, "月礼包_心悦会员1"),
                ]
            )
        elif old_info.is_xinyue_level(2, 3):
            default_xinyue_operations.extend(
                [
                    (130743, "周礼包_心悦会员2-3"),
                    (130785, "月礼包_心悦会员2-3"),
                ]
            )
        elif old_info.is_xinyue_level(4, 5):
            default_xinyue_operations.extend(
                [
                    (130744, "周礼包_心悦会员4-5"),
                    (130786, "月礼包_心悦会员4-5"),
                ]
            )

        xinyue_operations = []
        op_set = set()

        def try_add_op(op: XinYueOperationConfig):
            op_key = f"{op.iFlowId} {op.sFlowName}"
            if op_key in op_set:
                return

            xinyue_operations.append(op)
            op_set.add(op_key)

        for gift in default_xinyue_operations:
            op = XinYueOperationConfig()
            op.iFlowId, op.sFlowName = gift
            op.count = 1
            try_add_op(op)

        # 与配置文件中配置的去重后叠加
        for op in self.cfg.xinyue_operations_v2:
            try_add_op(op)

        # 进行相应的心悦操作
        for op in xinyue_operations:
            self.do_xinyue_battle_ground_wpe_op(op)

        # ------------ 荣耀镖局 -----------------
        # 尝试完成运镖任务
        async_message_box(
            (
                "荣耀镖局的中级和高级任务里的消耗疲劳是只计算绑定的角色当天消耗的疲劳，其他角色不计入。\n"
                "所以如果绑定的是小号的话，建议去道聚城调整下，改成绑定每天刷深渊的大号，这样可以确保任务完成，不会坑到队友\n"
            ),
            "荣耀镖局任务条件",
            show_once=True,
        )
        self.xinyue_battle_ground_wpe_op("开始高级运镖（消耗疲劳100点）（成就点*20，抽奖券*3）", 131323)
        self.xinyue_battle_ground_wpe_op("开始中级运镖（消耗疲劳50点）（成就点*15，抽奖券*2）", 131322)
        self.xinyue_battle_ground_wpe_op("开始初级运镖（在线30分钟）（成就点*10，抽奖券*1）", 131305)

        self.xinyue_battle_ground_wpe_op("领取队伍3次运镖幸运加成", 131432)

        # 然后尝试抽奖
        info = self.query_xinyue_info("查询抽奖次数", print_res=False)
        logger.info(color("bold_yellow") + f"当前剩余抽奖次数为 {info.ticket}")
        for idx in range(info.ticket):
            self.xinyue_battle_ground_wpe_op(f"第{idx + 1}次抽奖券抽奖", 131324)
            time.sleep(3)

        # 再次查询成就点信息，展示本次操作得到的数目
        new_info = self.query_xinyue_info("6.3 操作完成后查询成就点信息")
        delta = new_info.score - old_info.score
        logger.warning(
            color("fg_bold_yellow")
            + f"账号 {self.cfg.name} 本次心悦相关操作共获得 {delta} 个成就点（ {old_info.score} -> {new_info.score} ）"
        )
        logger.warning(
            color("fg_bold_yellow")
            + f"账号 {self.cfg.name} 当前是 {new_info.xytype_str} , 最新勇士币数目为 {new_info.ysb}"
        )

        # 查询下心悦组队进度
        teaminfo = self.query_xinyue_teaminfo()
        if teaminfo.is_team_full():
            logger.warning(
                color("fg_bold_yellow")
                + f"账号 {self.cfg.name} 当前队伍奖励概览 {self.query_xinyue_team_this_week_award_summary()}"
            )
        else:
            logger.warning(
                color("fg_bold_yellow")
                + f"账号 {self.cfg.name} 当前尚无有效心悦队伍，可考虑加入或查看文档使用本地心悦组队功能"
            )

    @try_except()
    def do_xinyue_battle_ground_wpe_op(self, op: XinYueOperationConfig):
        """
        执行具体的心悦战场相关的领奖或兑换操作
        """
        retryCfg = self.common_cfg.retry
        # 设置最少等待时间
        wait_time = max(retryCfg.request_wait_time, 10)
        retry_wait_time = max(retryCfg.retry_wait_time, 5)

        def _try_exchange(ctx: str, pNum: int):
            for _try_index in range(retryCfg.max_retry_count):
                res = self.xinyue_battle_ground_wpe_op(ctx, op.iFlowId, pNum=pNum)
                if op.count > 1:
                    # fixme: 下面的流程暂时注释掉，等后面实际触发后，再根据实际的回复结果适配
                    # hack: 这俩变量先留着，这样引用一下避免 linter 报错
                    _ = res
                    _ = retry_wait_time
                    # {"ret": 0, "msg": "...", "data": "{...}", "serialId": "..."}
                    # if res["ret"] == "700" and "操作过于频繁" in res["flowRet"]["sMsg"]:
                    #     logger.warning(f"心悦操作 {op.sFlowName} 操作过快，可能是由于其他并行运行的心悦活动请求过多而引起，等待{retry_wait_time}s后重试")
                    #     time.sleep(retry_wait_time)
                    #     continue
                    #
                    # if res["ret"] != "0" or res["modRet"]["iRet"] != 0:
                    #     logger.warning(f"{ctx} 出错了，停止尝试剩余次数")
                    #     return
                    pass

                logger.debug(f"心悦操作 {op.sFlowName} ok，等待{wait_time}s，避免请求过快报错")
                time.sleep(wait_time)
                break

        flow_id_to_max_batch_exchange_count: dict[int, int] = {
            130788: 100,  # 复活币礼盒（1个）-（每日100次）-1勇士币
            130820: 20,  # 神秘契约礼包-（每日20次）-10勇士币
            130821: 20,  # 装备提升礼盒-（每日20次）-30勇士币
        }
        if op.iFlowId not in flow_id_to_max_batch_exchange_count:
            # 不支持批量兑换，一个个兑换
            for idx in range_from_one(op.count):
                ctx = f"6.2 心悦操作： {op.sFlowName}({idx}/{op.count})"
                _try_exchange(ctx, 1)
        else:
            # 如果是支持批量兑换的道具，则特殊处理下
            max_batch_exchange_count = flow_id_to_max_batch_exchange_count[op.iFlowId]

            exchange_count = op.count
            if exchange_count > max_batch_exchange_count:
                exchange_count = max_batch_exchange_count
                logger.warning(
                    f"{op.sFlowName} 配置了兑换{op.count}个， 最多支持批量兑换{max_batch_exchange_count}个，且期限内总上限也为该数值，将仅尝试批量兑换该数目"
                )

            ctx = f"6.2 心悦操作： {op.sFlowName} 批量兑换 {exchange_count}个"
            _try_exchange(ctx, exchange_count)

    @try_except(show_exception_info=False)
    def try_join_xinyue_team(self, user_buy_info: BuyInfo):
        # 检查是否有固定队伍
        group_info = self.get_xinyue_team_group_info(user_buy_info)

        if group_info.team_name == "":
            logger.warning("未找到本地固定队伍信息，且不符合自动匹配的条件，将跳过自动组队相关流程")
            return

        logger.info(f"当前账号的队伍组队配置为{group_info}")

        # # 检查角色绑定
        self.prepare_wpe_act_openid_accesstoken("心悦战场wpe-自动组队", replace_if_exists=False)

        # 检查当前是否已有队伍
        teaminfo = self.query_xinyue_teaminfo(print_res=True)
        team_id = self.query_xinyue_my_team_id()
        if team_id != "":
            logger.info(f"目前已有队伍={teaminfo} team_id={team_id}")
            # 本地保存一下
            self.save_teamid(group_info.team_name, team_id)

            self.try_report_xinyue_remote_teamid_to_server("早已创建的队伍，但仍为单人", group_info, teaminfo, team_id)
            increase_counter(ga_category="xinyue_team_auto_match", name="report_again")
            return

        # 尝试从本地或者远程服务器获取一个远程队伍ID
        remote_teamid = ""
        if group_info.is_local:
            logger.info(color("bold_cyan") + "当前是 本地固定队伍 模式，将尝试从本地缓存查找当前本地队伍的远程队伍ID")
            remote_teamid = self.load_teamid(group_info.team_name)
        else:
            logger.info(
                color("bold_cyan") + "当前是 自动匹配组队 模式，将尝试从匹配服务器获取一个其他人创建的远程队伍ID"
            )
            remote_teamid = self.get_xinyue_remote_teamid_from_server()

        # 尝试加入远程队伍
        if remote_teamid != "":
            logger.info(f"尝试加入远程队伍id={remote_teamid}")
            summary_teaminfo = self.query_xinyue_summary_team_info_by_id(remote_teamid)
            # 如果队伍仍有效则加入
            if summary_teaminfo.teamCode == remote_teamid:
                remote_summary_teaminfo = self.join_xinyue_team(remote_teamid)
                if remote_summary_teaminfo is not None:
                    logger.info(f"成功加入远程队伍，队伍信息为{remote_summary_teaminfo}")

                    if not group_info.is_local:
                        increase_counter(ga_category="xinyue_team_auto_match", name="join_ok")

                    return

            logger.info(f"远程队伍={remote_teamid}已失效，应该是新的一周自动解散了，将重新创建队伍")

        # 尝试创建小队并保存到本地
        teaminfo = self.create_xinyue_team()
        team_id = self.query_xinyue_my_team_id()
        self.save_teamid(group_info.team_name, team_id)
        logger.info(f"{self.cfg.name} 创建小队并保存到本地成功，队伍信息={teaminfo}, team_id={team_id}")

        self.try_report_xinyue_remote_teamid_to_server("新创建的队伍", group_info, teaminfo, team_id)
        increase_counter(ga_category="xinyue_team_auto_match", name="report_first")

    def get_xinyue_team_group_info(self, user_buy_info: BuyInfo) -> XinYueTeamGroupInfo:
        # 初始化
        group_info = XinYueTeamGroupInfo()
        group_info.team_name = ""

        # 先尝试获取本地固定队伍信息
        for team in self.common_cfg.fixed_teams:
            if not team.enable:
                continue
            if self.qq() not in team.members:
                continue
            if not team.check():
                msg = f"本地固定队伍={team.id}的队伍成员({team.members})不符合要求，请确保是队伍成员数目为2，且均是有效的qq号（心悦专区改版后队伍成员数目不再是3个，而是2个）"
                title = "心悦队伍配置错误"
                async_message_box(msg, title, show_once_daily=True)
                continue

            group_info.team_name = team.id
            group_info.is_local = True
            break

        # 如果符合自动匹配条件，则替换为自动匹配的信息
        can_match = self.can_auto_match_xinyue_team(user_buy_info)
        if can_match:
            group_info.team_name = f"auto_match_{self.qq()}"
            group_info.is_local = False

        increase_counter(ga_category="xinyue_team_can_auto_match", name=can_match)

        return group_info

    def can_auto_match_xinyue_team(self, user_buy_info: BuyInfo, print_waring=True) -> bool:
        # 在按月付费期间
        if not user_buy_info.is_active(bypass_run_from_src=False):
            if print_waring:
                async_message_box(
                    (
                        f"{self.cfg.name} 未付费，将不会尝试自动匹配心悦队伍\n"
                        "\n"
                        "重新充值小助手后，且满足其余条件，则下次运行时可以参与自动匹配心悦队伍\n"
                        "\n"
                        "若无需心悦自动匹配功能，可前往当前账号的配置tab，取消勾选 心悦组队/自动匹配 即可\n"
                    ),
                    "心悦战场无法自动匹配（每周弹一次）",
                    show_once_weekly=True,
                    open_url=get_act_url("DNF地下城与勇士心悦特权专区"),
                )
            return False

        # 当前QQ是特邀会员或者心悦会员
        xinyue_info = self.query_xinyue_info("查询心悦信息-心悦自动组队", print_res=False)
        if not xinyue_info.is_xinyue_or_special_member():
            if print_waring:
                logger.warning(f"{self.cfg.name} 不是特邀会员或心悦会员，将不会尝试自动匹配心悦队伍")
            return False

        # 开启了本开关
        if not self.cfg.enable_auto_match_xinyue_team:
            if print_waring:
                async_message_box(
                    f"{self.cfg.name} 未开启自动匹配心悦组队开关，将不会尝试自动匹配~ ", "心悦组队提示", show_once=True
                )
            return False

        # 上周心悦战场派遣赛利亚打工并成功领取工资 3 次
        # note: 由于心悦战场于2023.12.21改版，因此先在改版后的3周内，不检查领取次数的条件，之后强制要求这个
        take_award_count = self.query_last_week_xinyue_team_take_award_count()
        if take_award_count < 3:
            if print_waring:
                async_message_box(
                    (
                        f"{self.cfg.name} 上周领取奖励次数为 {take_award_count}，少于需求的三次，将不会尝试自动匹配心悦队伍\n"
                        "\n"
                        "本周请自行前往心悦特权专区加入队伍并完成三次任务的条件（当日完成条件后小助手会自动帮你领取），下周即可重新自动匹配\n"
                        "\n"
                        "若无需心悦自动匹配功能，可前往当前账号的配置tab，取消勾选 心悦组队/自动匹配 即可\n"
                    ),
                    "心悦战场上周未完成三次任务（每周弹一次）",
                    show_once_weekly=True,
                    open_url=get_act_url("DNF地下城与勇士心悦特权专区"),
                )
            return False

        return True

    def query_last_week_xinyue_team_take_award_count(self) -> int:
        last_week_awards = self.query_last_week_xinyue_team_awards()

        take_count = 0
        for award in last_week_awards:
            # 判断是否是运镖令奖励
            # 初级运镖令奖励   4748214
            # 中级运镖令奖励   4748279
            # 高级运镖令奖励   4748280
            if award.gift_id in ["4748214", "4748279", "4748280"] or "运镖令" in award.gift_name:
                take_count += 1

        return take_count

    def query_last_week_xinyue_team_awards(self) -> list[XinYueTeamAwardInfo]:
        # 假设过去两周每天兑换40个道具（比如装备提升礼盒），每页为10个
        page_size = 10
        two_week_max_page = 40 * 7 * 2 // page_size

        last_monday = get_last_week_monday_datetime()
        this_monday = get_this_week_monday_datetime()

        last_week_awards = []
        for page in range_from_one(two_week_max_page):
            awards = self.query_xinyue_team_awards(page, page_size)
            if len(awards) == 0:
                break

            for award in awards:
                take_at = parse_time(award.gift_time)
                if take_at >= this_monday:
                    # 跳过本周的
                    continue
                elif take_at >= last_monday:
                    # 上周的结果
                    last_week_awards.append(award)
                else:
                    # 从这开始是上周之前的，不必再额外处理，可以直接返回了
                    return last_week_awards

        return last_week_awards

    @try_except(return_val_on_except=[])
    def query_xinyue_team_awards(self, iPageNow: int, iPageSize: int) -> list[XinYueTeamAwardInfo]:
        self.prepare_wpe_act_openid_accesstoken("查询心悦组队奖励记录", replace_if_exists=False, print_res=False)

        json_data = {
            "game_code": "dnf",
            "page_size": iPageSize,
            "page_index": iPageNow,
            "activity_id": "15488",
            "business_id": "tgclub",
        }

        raw_res = self.post(
            f"查询心悦组队奖励-{iPageNow}-{iPageSize}",
            self.urls.dnf_xinyue_query_gift_record_api,
            json=json_data,
            print_res=False,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
        )

        awards: list[XinYueTeamAwardInfo] = []
        if raw_res["ret"] == 0:
            for raw_award in raw_res["records"]:
                award = XinYueTeamAwardInfo().auto_update_config(raw_award)
                awards.append(award)

        return awards

    @try_except(return_val_on_except="获取失败")
    def query_xinyue_team_this_week_award_summary(self) -> str:
        def _query_task_finsihed(task_flow_id: int) -> bool:
            res = self.xinyue_battle_ground_wpe_op(f"查询队伍任务状态-{task_flow_id}", task_flow_id, print_res=False)
            raw_info = json.loads(res["data"])

            return raw_info["ret"] == 0 and raw_info["remain"] > 0

        def _query_member_task_list_summary(tasks: list[tuple[str, int]]) -> str:
            task_state_list = []
            for task_name, flow_id in tasks:
                finished = _query_task_finsihed(flow_id)
                if finished:
                    task_state_list.append(task_name)

            return "".join(task_state_list)

        self.prepare_wpe_act_openid_accesstoken(
            "查询新版心悦战场队伍任务状态", replace_if_exists=False, print_res=False
        )

        mine_tasks = [
            ("初", 131664),
            ("中", 131665),
            ("高", 131666),
        ]
        teammate_flow_ids = [
            ("初", 131667),
            ("中", 131669),
            ("高", 131670),
        ]

        mine_summary = _query_member_task_list_summary(mine_tasks)
        teammate_summary = _query_member_task_list_summary(teammate_flow_ids)

        return f"{mine_summary}|{teammate_summary}"

    @try_except(return_val_on_except="")
    def query_xinyue_my_team_id(self) -> str:
        res = self.xinyue_battle_ground_wpe_op("查询我的心悦队伍ID", 131104, print_res=False)

        code = ""

        # 正常结果：{"ret": 0, "msg": "", "data": "{\"ret\":0,\"errCode\":0,\"code\":\"DNF1704679425RLDV6I\"}", "serialId": "..."}
        # 没有队伍（如到第二周了队伍解散、尚未创建队伍等）：{"ret":50003,"msg":"网络繁忙，请稍后再试","data":"","serialId":"..."}
        if res["ret"] == 0:
            raw_data = json.loads(res["data"])
            code = raw_data["code"]

        return code

    @try_except(return_val_on_except=XinYueMyTeamInfo())
    def query_xinyue_teaminfo(self, print_res=False) -> XinYueMyTeamInfo:
        if self.cfg.function_switches.disable_login_mode_xinyue:
            get_logger_func(print_res)("已禁用心悦登录模式，将直接返回默认值")
            return XinYueMyTeamInfo()

        res = self.xinyue_battle_ground_wpe_op("查询我的心悦队伍信息", 131111, print_res=print_res)

        team_info = XinYueMyTeamInfo()

        if res["ret"] == 0:
            raw_data = json.loads(res["data"])
            team_info.auto_update_config(raw_data)

        return team_info

    @try_except(return_val_on_except=XinYueSummaryTeamInfo())
    def query_xinyue_summary_team_info_by_id(self, remote_teamid: str) -> XinYueSummaryTeamInfo:
        # 传入小队ID查询队伍信息
        res = self.xinyue_battle_ground_wpe_op(
            "查询特定id的心悦队伍信息", 131114, extra_data={"teamCode": remote_teamid}
        )

        one_team_info = XinYueSummaryTeamInfo()

        # 正常结果：{"ret":0,"msg":"","data":"{\"ret\":0,\"teamInfo\":{\"teamCode\":\"DNF1703518043CC8D6Z\",\"teamName\":\"%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87\",\"teamLimit\":2,\"teamMemberNum\":2}}","serialId":"..."}
        # 找不到队伍信息时（如到第二周了）：{"ret":50003,"msg":"网络繁忙，请稍后再试","data":"","serialId":"..."}
        if res["ret"] == 0:
            raw_data = json.loads(res["data"])
            one_team_info.auto_update_config(raw_data["teamInfo"])

        return one_team_info

    def join_xinyue_team(self, remote_teamid: str) -> XinYueSummaryTeamInfo | None:
        # 加入小队
        res = self.xinyue_battle_ground_wpe_op("尝试加入小队", 131113, extra_data={"invitationCode": remote_teamid})

        one_team_info = None

        if res["ret"] == 0:
            raw_data = json.loads(res["data"])

            one_team_info = XinYueSummaryTeamInfo()
            one_team_info.auto_update_config(raw_data["teamInfo"])
        else:
            # 小队已经解散
            pass

        return one_team_info

    def create_xinyue_team(self) -> XinYueMyTeamInfo:
        # 创建小队
        roleinfo = self.get_dnf_bind_role()
        self.xinyue_battle_ground_wpe_op("尝试创建小队", 131103, extra_data={"team_name": roleinfo.roleName})

        return self.query_xinyue_teaminfo()

    def save_teamid(self, fixed_teamid: str, remote_teamid: str):
        fname = self.local_saved_teamid_file.format(fixed_teamid)
        with open(fname, "w", encoding="utf-8") as sf:
            teamidInfo = {
                "fixed_teamid": fixed_teamid,
                "remote_teamid": remote_teamid,
            }
            json.dump(teamidInfo, sf)
            logger.debug(f"本地保存固定队信息，具体内容如下：{teamidInfo}")

    def load_teamid(self, fixed_teamid: str) -> str:
        fname = self.local_saved_teamid_file.format(fixed_teamid)

        if not os.path.isfile(fname):
            return ""

        with open(fname, encoding="utf-8") as f:
            teamidInfo = json.load(f)
            logger.debug(f"读取本地缓存的固定队信息，具体内容如下：{teamidInfo}")
            return teamidInfo["remote_teamid"]

    @try_except(return_val_on_except=XinYueInfo())
    def query_xinyue_info(self, ctx, print_res=True, use_new_version=True) -> XinYueInfo:
        if use_new_version:
            return self._new_query_xinyue_info(ctx, print_res)
        else:
            return self._old_query_xinyue_info(ctx, print_res)

    def _old_query_xinyue_info(self, ctx, print_res=True) -> XinYueInfo:
        """已废弃"""
        res = self.xinyue_battle_ground_op(ctx, "767160", print_res=print_res)
        raw_info = parse_amesvr_common_info(res)

        info = XinYueInfo()

        xytype = int(raw_info.sOutValue1)

        info.xytype = xytype
        info.xytype_str = info.level_to_name[xytype]

        info.is_special_member = int(raw_info.sOutValue2) == 1
        if info.is_special_member:
            info.xytype_str = "特邀会员"
        info.ysb, info.score, info.ticket = (int(val) for val in raw_info.sOutValue3.split("|"))
        info.username, info.usericon = raw_info.sOutValue4.split("|")
        info.username = unquote_plus(info.username)
        info.login_qq = raw_info.sOutValue5

        work_status, work_end_time, take_award_end_time = raw_info.sOutValue6.split("|")
        info.work_status = int(work_status or "0")
        info.work_end_time = int(work_end_time or "0")
        info.take_award_end_time = int(take_award_end_time or "0")

        return info

    def _new_query_xinyue_info(self, ctx, print_res=True) -> XinYueInfo:
        @try_except(return_val_on_except=0)
        def _query_xytype() -> int:
            res = self.xinyue_battle_ground_wpe_op(f"{ctx}-查询心悦会员类型", 131053, print_res=print_res)

            count = 0

            if res["ret"] == 0:
                raw_info = json.loads(res["data"])
                count = raw_info["value"]

            return count

        @try_except(return_val_on_except=0)
        def _query_ysb() -> int:
            res = self.xinyue_battle_ground_wpe_op(f"{ctx}-查询勇士币", 131050, print_res=print_res)

            count = 0

            if res["ret"] == 0:
                raw_info = json.loads(res["data"])
                count = raw_info["remain"]

            return count

        @try_except(return_val_on_except=0)
        def _query_score() -> int:
            res = self.xinyue_battle_ground_wpe_op(f"{ctx}-查询成就点", 131049, print_res=print_res)

            count = 0

            if res["ret"] == 0:
                raw_info = json.loads(res["data"])
                count = raw_info["remain"]

            return count

        @try_except(return_val_on_except=0)
        def _query_ticket() -> int:
            res = self.xinyue_battle_ground_wpe_op(f"{ctx}-查询抽奖次数", 131051, print_res=print_res)

            count = 0

            if res["ret"] == 0:
                raw_info = json.loads(res["data"])
                count = raw_info["remain"]

            return count

        # 实际逻辑

        if self.cfg.function_switches.disable_login_mode_xinyue:
            get_logger_func(print_res)("已禁用心悦登录模式，将直接返回默认值")
            return XinYueInfo()

        # 确保请求所需参数已准备好
        self.prepare_wpe_act_openid_accesstoken("查询新版心悦战场信息", replace_if_exists=False, print_res=print_res)

        info = XinYueInfo()

        xytype = _query_xytype()

        info.xytype = xytype
        info.xytype_str = info.level_to_name[xytype]

        info.is_special_member = xytype == info.SPECIAL_MEMBER_LEVEL
        if info.is_special_member:
            info.xytype_str = "特邀会员"

        info.ysb, info.score, info.ticket = _query_ysb(), _query_score(), _query_ticket()
        # info.username, info.usericon = raw_info.sOutValue4.split("|")
        # info.username = unquote_plus(info.username)
        # info.login_qq = raw_info.sOutValue5

        # work_status, work_end_time, take_award_end_time = raw_info.sOutValue6.split("|")
        # info.work_status = int(work_status or "0")
        # info.work_end_time = int(work_end_time or "0")
        # info.take_award_end_time = int(take_award_end_time or "0")

        return info

    def try_report_xinyue_remote_teamid_to_server(
        self, ctx: str, group_info: XinYueTeamGroupInfo, teaminfo: XinYueMyTeamInfo, team_code: str
    ):
        # 只有远程匹配模式需要尝试上报
        if group_info.is_local:
            return

        # 如果已达到人数上限，也不需要匹配
        if teaminfo.is_team_full():
            return

        logger.info(f"因为 {ctx}，将尝试上报 {self.cfg.name} 创建的心悦远程队伍 {team_code} 到服务器")

        self.report_xinyue_remote_teamid_to_server(team_code)

    @try_except()
    def report_xinyue_remote_teamid_to_server(self, remote_team_id: str):
        req = XinYueMatchServerAddTeamRequest()
        req.leader_qq = self.qq()
        req.team_id = remote_team_id

        self.post("上报心悦队伍信息", get_match_server_api("/add_team"), json=to_raw_type(req), disable_retry=True)

    @try_except(return_val_on_except="")
    def get_xinyue_remote_teamid_from_server(self) -> str:
        req = XinYueMatchServerRequestTeamRequest()
        req.request_qq = self.qq()

        raw_res = self.post(
            "请求获取一个心悦队伍", get_match_server_api("/req_team"), json=to_raw_type(req), disable_retry=True
        )
        res = XinYueMatchServerCommonResponse()
        res.data = XinYueMatchServerRequestTeamResponse()
        res.auto_update_config(raw_res)

        increase_counter(ga_category="xinyue_team_auto_match", name="request_teamid")
        increase_counter(ga_category="xinyue_team_request_teamid", name=res.data.team_id != "")

        return res.data.team_id

    def check_xinyue_battle_ground(self):
        self.check_bind_account(
            "心悦战场",
            get_act_url("DNF地下城与勇士心悦特权专区"),
            activity_op_func=self.xinyue_battle_ground_op,
            query_bind_flowid="748044",
            commit_bind_flowid="748043",
        )

    def xinyue_battle_ground_op(
        self, ctx, iFlowId, package_id="", print_res=True, lqlevel=1, teamid="", **extra_params
    ):
        return self.xinyue_op(
            ctx,
            self.urls.iActivityId_xinyue_battle_ground,
            iFlowId,
            package_id,
            print_res,
            lqlevel,
            teamid,
            **extra_params,
        )

    def xinyue_op(self, ctx, iActivityId, iFlowId, package_id="", print_res=True, lqlevel=1, teamid="", **extra_params):
        # 网站上特邀会员不论是游戏家G几，调用doAction(flowId,level)时level一律传1，而心悦会员则传入实际的567对应心悦123
        if lqlevel < XIN_YUE_MIN_LEVEL:
            lqlevel = 1

        return self.amesvr_request(
            ctx,
            "act.game.qq.com",
            "xinyue",
            "xinyue",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF地下城与勇士心悦特权专区"),
            package_id=package_id,
            lqlevel=lqlevel,
            teamid=teamid,
            **extra_params,
        )

    def check_xinyue_battle_ground_wpe(self) -> XinYueBattleGroundWpeBindRole:
        """检查心悦战场的绑定信息，并返回绑定信息"""
        # 运行期间仅尝试获取一次
        if not hasattr(self, "dnf_xinyue_wpe_bind_role"):
            # 查询心悦的绑定信息
            bind_role = self.xinyue_battle_ground_wpe_query_bind_role()
            if bind_role is None:
                # 若未绑定，则尝试使用道聚城的绑定角色进行绑定
                ok = self.xinyue_battle_ground_wpe_bind_role()
                logger.info(f"心悦战场未绑定角色，将使用道聚城的绑定角色，绑定角色结果={ok}")

                # 绑定完后再次尝试查询
                bind_role = self.xinyue_battle_ground_wpe_query_bind_role()

            # 将查询结果保存到内存中，方便后续使用
            self.dnf_xinyue_wpe_bind_role = bind_role

        return self.dnf_xinyue_wpe_bind_role

    def xinyue_battle_ground_wpe_query_bind_role(self) -> XinYueBattleGroundWpeBindRole | None:
        """查询心悦战场的绑定信息"""
        json_data = {
            "game_code": "dnf",
            "device": "pc",
            "scene": "tgclub_act_15488"
        }

        raw_res = self.post(
            "查询心悦绑定信息",
            self.urls.dnf_xinyue_wpe_get_bind_role_api,
            json=json_data,
            print_res=False,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
            # check_fn=_check_fn,
        )

        res = XinYueBattleGroundWpeGetBindRoleResult()
        res.auto_update_config(raw_res)

        # {"ret": 300015, "msg": "无绑定区服或最近登陆的区服信息", "roles": [], "next_page_no": -1, "game_info": null}
        # {"ret": 0, "msg": "", "roles": [{...}], "next_page_no": -1, "game_info": null}
        if res.ret != 0 or len(res.roles) == 0:
            return None

        return res.roles[0]


    def xinyue_battle_ground_wpe_bind_role(self) -> bool:
        """绑定心悦战场为道聚城的绑定角色"""
        # 使用道聚城的绑定信息去绑定心悦战场
        roleinfo = self.get_dnf_bind_role()

        json_data = {
            "game_code": "dnf",
            "device": "pc",
            "scene": "tgclub_act_15488",
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
        }

        raw_res = self.post(
            "心悦战场绑定角色",
            self.urls.dnf_xinyue_wpe_bind_role_api,
            json=json_data,
            print_res=False,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
            # check_fn=_check_fn,
        )

        return raw_res["ret"] == 0

    # re: 搜 wpe类活动的接入办法为
    def xinyue_battle_ground_wpe_op(
        self, ctx: str, flow_id: int, print_res=True, extra_data: dict | None = None, pNum: int = 1, **extra_params
    ):
        # 该类型每个请求之间需要间隔一定时长，否则会请求失败
        # note: 心悦这个大部分查询接口是不需要，部分接口（如组队相关的）在下方特判进行处理，并在返回请求过快的情况下，等待一会再重试
        wait_time = 2 + 1 * random.random()
        # logger.debug(f"心悦战场请求 {ctx} 先随机等待 {wait_time:.2f} 秒，避免请求过快")
        # time.sleep(wait_time)

        need_wait_flow_ids = {
            131104,  # 查询我的心悦队伍ID
            131114,  # 查询特定id的心悦队伍信息
        }
        if flow_id in need_wait_flow_ids:
            # note: 部分接口有调用频率限制
            logger.debug(f"心悦战场请求 {ctx} {flow_id} 有调用频率限制，等待 {wait_time:.2f} 秒后再尝试请求")
            time.sleep(wait_time)

        act_id = "15488"

        djc_roleinfo = self.get_dnf_bind_role()
        roleinfo = self.check_xinyue_battle_ground_wpe()

        if extra_data is None:
            extra_data = {}

        json_data = {
            "biz_id": "tgclub",
            "act_id": act_id,
            "flow_id": int(flow_id),
            "role": to_raw_type(roleinfo),
            "data": json.dumps(
                {
                    "pNum": pNum,
                    "ceiba_plat_id": "ios",
                    "user_attach": json.dumps(
                        {
                            "nickName": quote(djc_roleinfo.roleName),
                            # # fixme: 这里还有个avatar，通过下面两个接口应该都能获得，暂时先不弄，后面如果必须要的话再处理
                            # #   https://ams.game.qq.com/ams/userLoginSvr?callback=jsonp93&acctype=qc&appid=101478665&openid=...&access_token=...&game=xinyue
                            # #   https://bgw.xinyue.qq.com/website/website/user/info
                            # "avatar": "http://thirdqq.qlogo.cn/ek_qqapp/.../40",
                        }
                    ),
                    "cExtData": {},
                    **extra_data,
                }
            ),
        }

        def _check_fn(response: requests.Response) -> Exception | None:
            """
            检查是否属于腾讯游戏接口返回请求过快的情况
            """
            res = response.json()

            if res["msg"] == "操作过于频繁，请稍后再试":
                # re: 使用flowid=131104测试发现，这里的请求过快判定时间似乎是1.8秒，在这种情况下，放宽一点，等待2-3秒
                # {"ret": 0, "msg": "操作过于频繁，请稍后再试", "data": "{\"msg\":\"操作过于频繁，请稍后再试\",\"ret\":40006}", "serialId": "..."}
                #
                # note: 下面这个虽然看起来很像是请求过快，实际并不是这个含义，似乎是对应数据不存在的情况下返回，这里备注下
                #           比如本周还未创建队伍，也未加入队伍的情况下，尝试查询自己的队伍ID
                # {"ret": 50003, "msg": "网络繁忙，请稍后再试", "data": "", "serialId": "..."}

                logger.warning(get_meaningful_call_point_for_log() + f"请求过快，等待 {wait_time:.2f} 秒后重试")
                time.sleep(wait_time)
                return Exception("请求过快")

            return check_tencent_game_common_status_code(response)

        return self.post(
            ctx,
            self.urls.dnf_xinyue_wpe_api,
            json=json_data,
            print_res=print_res,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
            check_fn=_check_fn,
        )

    @try_except(return_val_on_except=XinYueBgwUserInfo())
    def query_xinyue_bgw_user_info(self, ctx: str, print_res=False) -> XinYueBgwUserInfo:
        def _do_query() -> XinYueBgwUserInfo:
            lr = self.fetch_xinyue_login_info(f"获取 {ctx} 所需的access_token", print_res=print_res)

            raw_res = self.get(
                ctx,
                self.urls.dnf_xinyue_bgw_user_info_api,
                print_res=print_res,
                use_this_cookies=f"acctype=qc; appid=101478665; openid={lr.openid}; access_token={lr.xinyue_access_token}; ",
            )

            user_info = XinYueBgwUserInfo()
            user_info.auto_update_config(raw_res["data"])

            return user_info

        meaingful_caller = get_meaningful_call_point_for_log()

        return with_cache(
            "查询心悦用户信息",
            self.cfg.get_account_cache_key(),
            cache_miss_func=_do_query,
            cache_max_seconds=24 * 60 * 60,
            cache_value_unmarshal_func=XinYueBgwUserInfo().auto_update_config,
            cache_hit_func=lambda lr: get_logger_func(print_res, logger.info)(
                meaingful_caller + f"使用缓存的心悦用户信息: {lr}"
            ),
        )

    # --------------------------------------------心悦app--------------------------------------------
    @try_except()
    def xinyue_app_operations(self):
        """
        根据配置进行心悦app相关操作
        """
        show_head_line("心悦app")
        self.show_not_ams_act_info("心悦app")

        if not self.cfg.function_switches.get_xinyue_app:
            logger.warning("未启用领取心悦app功能，将跳过")
            return

        if self.cfg.is_xinyue_app_operation_not_set():
            logger.warning(
                "未配置心悦app相关操作，将跳过。如需使用，请打开config.example.toml搜索 心悦app相关操作 查看示例配置和说明，然后手动填写到config.toml中对应位置(如果搞不来，就请手动操作~)"
            )
            return

        lr = self.fetch_xinyue_login_info("心悦app")
        access_token = lr.xinyue_access_token
        openid = lr.openid
        if access_token == "" or openid == "":
            logger.warning(f"心悦app的票据未能成功获取。access_token={access_token}, openid={openid}")
            return

        # 请求体目前看来每次请求包可以保持一致
        # note：获取方式，抓包获取http body。如fiddler，抓包，找到对应请求（body大小为150的请求），右侧点Inspector/HexView，选中Http Body部分的字节码（未标蓝部分），右击Copy/Copy as 0x##，然后粘贴出来，将其中的bytes复制到下列对应数组位置

        url = "https://a.xinyue.qq.com/"
        headers = {
            "Cookie": f"xyapp_login_type=qc;access_token={access_token};openid={openid};appid=101484782",
            "Accept": "application/json",
            "Referer": "http://apps.game.qq.com/php/tgclub/v2/",
            "User-Agent": "tgclub/5.7.6.81(Xiaomi MIX 2;android 9;Scale/440;android;865737030437124)",
            "Charset": "UTF-8",
            "Accept-Language": "zh-Hans-US;q=1,en-US;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        old_gpoints = self.query_gpoints()

        for op in self.cfg.xinyue_app_operations:
            res = requests.post(url, bytes(op.encrypted_raw_http_body), headers=headers, timeout=10)  # type: ignore
            logger.info(f"心悦app操作：{op.name} 返回码={res.status_code}, 请求结果={res.content!r}")

        new_gpoints = self.query_gpoints()

        logger.info(
            color("bold_yellow")
            + f"兑换前G分为{old_gpoints}， 兑换后G分为{new_gpoints}，差值为{old_gpoints - new_gpoints}，请自行前往心悦app确认是否兑换成功"
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

    # --------------------------------------------黑钻--------------------------------------------
    @try_except()
    def get_heizuan_gift(self):
        show_head_line("黑钻礼包")
        self.show_not_ams_act_info("黑钻礼包")

        if not self.cfg.function_switches.get_heizuan_gift or self.disable_most_activities():
            logger.warning("未启用领取每月黑钻等级礼包功能，将跳过")
            return

        while True:
            res = self.get("领取每月黑钻等级礼包", self.urls.heizuan_gift)
            # note: 黑钻的活动页面不见了，现在没法手动绑定了，不再增加这个提示
            # # 如果未绑定大区，提示前往绑定 "iRet": -50014, "sMsg": "抱歉，请先绑定大区后再试！"
            # if res["iRet"] == -50014:
            #     self.guide_to_bind_account("每月黑钻等级礼包", get_act_url("黑钻礼包"), activity_op_func=None)
            #     continue

            return res

    # --------------------------------------------信用礼包--------------------------------------------
    @try_except()
    def get_credit_xinyue_gift(self):
        show_head_line("腾讯游戏信用相关礼包")
        self.show_not_ams_act_info("腾讯游戏信用礼包")

        if not self.cfg.function_switches.get_credit_xinyue_gift or self.disable_most_activities():
            logger.warning("未启用领取腾讯游戏信用相关礼包功能，将跳过")
            return

        self.get("每月信用星级礼包", self.urls.credit_gift)
        try:
            self.get("腾讯游戏信用-高信用即享礼包", self.urls.credit_xinyue_gift, gift_group=1)
            # 等待一会
            time.sleep(self.common_cfg.retry.request_wait_time)
            self.get("腾讯游戏信用-高信用&游戏家即享礼包", self.urls.credit_xinyue_gift, gift_group=2)
        except Exception as e:
            logger.exception("腾讯游戏信用这个经常挂掉<_<不过问题不大，反正每月只能领一次", exc_info=e)

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

    def fetch_pskey(self, force=False, window_index=1):
        self.lr = None

        # 如果未启用qq空间相关的功能，则不需要这个
        any_enabled = False
        for activity_enabled in [
            self.cfg.function_switches.get_ark_lottery,
            # self.cfg.function_switches.get_dnf_warriors_call and not self.disable_most_activities(),
            self.cfg.function_switches.get_vip_mentor and not self.disable_most_activities(),
        ]:
            if activity_enabled:
                any_enabled = True
        if not force and not any_enabled:
            logger.warning("未启用领取QQ空间相关的功能，将跳过尝试更新QQ空间的p_skey的流程")
            return

        if self.cfg.function_switches.disable_login_mode_qzone:
            logger.warning("已禁用QQ空间登录模式，将跳过尝试更新p_skey流程")
            return

        # 仅支持扫码登录和自动登录
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            logger.warning("抽卡功能目前仅支持扫码登录和自动登录，请修改登录方式，否则将跳过该功能")
            return

        cached_pskey = self.load_uin_pskey()
        need_update = self.is_pskey_expired(cached_pskey)

        # qq空间登录也需要获取skey后，若是旧版本存档，视作已过期
        if not need_update and (cached_pskey is None or "skey" not in cached_pskey or "vuserid" not in cached_pskey):
            logger.warning("qq空间登录改版后，需要有skey和vuserid。当前为旧版本cache，需要重新拉取")
            need_update = True

        if need_update:
            # 抽卡走的账号体系是使用pskey的，不与其他业务共用登录态，需要单独获取QQ空间业务的p_skey。参考链接：https://cloud.tencent.com/developer/article/1008901
            logger.warning("pskey需要更新，将尝试重新登录QQ空间获取并保存到本地")
            # 重新获取
            ql = QQLogin(self.common_cfg, window_index=window_index)
            try:
                if self.cfg.login_mode == "qr_login":
                    # 扫码登录
                    lr = ql.qr_login(ql.login_mode_qzone, name=self.cfg.name, account=self.cfg.account_info.account)
                else:
                    # 自动登录
                    lr = ql.login(
                        self.cfg.account_info.account,
                        self.cfg.account_info.password,
                        ql.login_mode_qzone,
                        name=self.cfg.name,
                    )
            except GithubActionLoginException:
                logger.error(
                    "在github action环境下qq空间登录失败了，很大可能是因为该网络环境与日常环境不一致导致的（qq空间检查的很严），只能将qq空间相关配置禁用咯"
                )
                self.cfg.function_switches.get_ark_lottery = False
                self.cfg.function_switches.get_dnf_warriors_call = False
                self.cfg.function_switches.get_vip_mentor = False
                return

            # 保存
            self.save_uin_pskey(lr.uin, lr.p_skey, lr.skey, lr.vuserid)
        else:
            lr = LoginResult(
                uin=cached_pskey["p_uin"],
                p_skey=cached_pskey["p_skey"],
                skey=cached_pskey["skey"],
                vuserid=cached_pskey["vuserid"],
            )

        if lr.skey != "" and lr.vuserid != "":
            self.memory_save_uin_skey(lr.uin, lr.skey)
            self.set_vuserid(lr.vuserid)

        self.lr = lr
        return lr

    @try_except(extra_msg="检查p_skey是否过期失败，视为已过期", return_val_on_except=True)
    def is_pskey_expired(self, cached_pskey) -> bool:
        if cached_pskey is None:
            return True

        lr = LoginResult(uin=cached_pskey["p_uin"], p_skey=cached_pskey["p_skey"])

        # 特判一些可以直接判定为过期的情况
        if lr.uin == "" or lr.p_skey == "":
            return True

        # QQ空间集卡系活动
        # pskey过期提示：{'code': -3000, 'subcode': -4001, 'message': '请登录', 'notice': 0, 'time': 1601004332, 'tips': 'EE8B-284'}
        # 由于活动过期的判定会优先于pskey判定，需要需要保证下面调用的是最新的活动~

        def check_by_ark_lottery() -> bool:
            al = QzoneActivity(self, lr)
            res = al.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日登陆页面", 25970, print_res=False)
            return res["code"] == -3000 and res["subcode"] == -4001

        def check_by_warriors_call() -> bool:
            qa = QzoneActivity(self, lr)
            qa.fetch_dnf_warriors_call_data()
            res = qa.do_dnf_warriors_call(
                "fcg_receive_reward",
                "测试pskey是否过期",
                qa.zz().actbossRule.buyVipPrize,
                gameid=qa.zz().gameid,
                print_res=False,
            )
            return res["code"] == -3000 and res["subcode"] == -4001

        # QQ空间新版活动
        # pskey过期提示：分享领取礼包	{"code": -3000, "message": "未登录"}
        # 这个活动优先判定pskey

        def check_by_super_vip() -> bool:
            self.lr = lr
            res = self.qzone_act_op("幸运勇士礼包", "5353_75244d03", print_res=False)
            return res.get("code", 0) in [-3000, 403]

        def check_by_yellow_diamond() -> bool:
            self.lr = lr
            res = self.qzone_act_op("幸运勇士礼包", "5328_63fbbb7d", print_res=False)
            return res.get("code", 0) in [-3000, 403]

        # 用于按顺序检测p_skey是否过期的函数列表
        check_p_skey_expired_func_list = [
            check_by_super_vip,
            check_by_yellow_diamond,
            check_by_warriors_call,
            check_by_ark_lottery,
        ]

        for check_func in check_p_skey_expired_func_list:
            try:
                is_expired = check_func()
                return is_expired
            except Exception as e:
                # 如果这个活动挂了，就打印日志后，尝试下一个
                logFunc = logger.debug
                if use_by_myself():
                    logFunc = logger.warning
                logFunc(f"{check_func.__name__} 活动似乎挂了，将尝试使用下一个活动来判定，异常为 {e}")

        return True

    def save_uin_pskey(self, uin, pskey, skey, vuserid):
        # 本地缓存
        with open(self.get_local_saved_pskey_file(), "w", encoding="utf-8") as sf:
            loginResult = {
                "p_uin": str(uin),
                "p_skey": str(pskey),
                "skey": str(skey),
                "vuserid": str(vuserid),
            }
            json.dump(loginResult, sf)
            logger.debug(f"本地保存pskey信息，具体内容如下：{loginResult}")

    @try_except()
    def load_uin_pskey(self):
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_pskey_file()):
            return

        with open(self.get_local_saved_pskey_file(), encoding="utf-8") as f:
            loginResult = json.load(f)
            logger.debug(f"读取本地缓存的pskey信息，具体内容如下：{loginResult}")
            return loginResult

    def get_local_saved_pskey_file(self):
        return self.local_saved_pskey_file.format(self.cfg.name)

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

    # --------------------------------------------QQ空间超级会员--------------------------------------------
    # note：对接流程与下方黄钻完全一致，参照其流程即可
    @try_except()
    def dnf_super_vip(self):
        get_act_url("超级会员")
        show_head_line("QQ空间超级会员")
        self.show_not_ams_act_info("超级会员")

        if not self.cfg.function_switches.get_dnf_super_vip or self.disable_most_activities():
            logger.warning("未启用领取QQ空间超级会员功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.fetch_pskey()
        if self.lr is None:
            return

        lucky_act_id = "108950_c9642198"
        self.qzone_act_op("幸运勇士礼包 - 当前角色", lucky_act_id)
        self.qzone_act_op(
            "幸运勇士礼包 - 集卡幸运角色",
            lucky_act_id,
            act_req_data=self.try_make_lucky_user_req_data(
                "集卡", self.cfg.ark_lottery.lucky_dnf_server_id, self.cfg.ark_lottery.lucky_dnf_role_id
            ),
        )

        self.qzone_act_op("勇士见面礼", "108951_e97c298f")

        self.qzone_act_op("签到", "108958_e94aed5e")
        self.qzone_act_op("累计签到1天", "108953_be8ca73e")
        self.qzone_act_op("累计签到3天", "108954_c68b71b5")
        self.qzone_act_op("累计签到7天", "108955_2b7866d9")
        self.qzone_act_op("累计签到14天", "108956_aa6e02ba")

        # if not self.cfg.function_switches.disable_share and is_first_run(
        #     f"dnf_super_vip_{get_act_url('超级会员')}_分享_{self.uin()}"
        # ):
        #     self.qzone_act_op(
        #         "分享给自己",
        #         "73043_c6fd6bf4",
        #         act_req_data={
        #             "receivers": [
        #                 self.qq(),
        #             ]
        #         },
        #     )
        # self.qzone_act_op("分享领取礼包", "73044_fb4771e1")

    # --------------------------------------------QQ空间黄钻--------------------------------------------
    # note: 适配流程如下
    #   0. 电脑chrome中设置Network conditions中的User agent为手机QQ的： Mozilla/5.0 (Linux; U; Android 5.0.2; zh-cn; X900 Build/CBXCNOP5500912251S) AppleWebKit/533.1 (KHTML, like Gecko)Version/4.0 MQQBrowser/5.4 TBS/025489 Mobile Safari/533.1 V1_AND_SQ_6.0.0_300_YYB_D QQ/6.0.0.2605 NetType/WIFI WebP/0.3.0 Pixel/1440
    #   1. 获取子活动id   chrome设置为手机qq UA后，登录活动页面 get_act_url("黄钻") ，然后在幸运勇士、勇士见面礼等按钮上右键Inspect，然后在Sources中搜索其vt-itemid(如xcubeItem_4)，
    #       在结果中双击main.bundle.js结果，点击格式化后搜索【default.methods.xcubeItem_4=】(其他按钮的替换为对应值），其下方的subActId的值替换到下方代码处即可
    #   2. 填写新链接和活动时间   在 urls.py 中，替换get_act_url("黄钻")的值为新的网页链接，并把活动时间改为最新
    #   3. 重新启用代码 将调用处从 expired_activities 移到 payed_activities
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
        self.qzone_act_op("幸运勇士礼包 - 当前角色", lucky_act_id)
        self.qzone_act_op(
            "幸运勇士礼包 - 集卡幸运角色",
            lucky_act_id,
            act_req_data=self.try_make_lucky_user_req_data(
                "集卡", self.cfg.ark_lottery.lucky_dnf_server_id, self.cfg.ark_lottery.lucky_dnf_role_id
            ),
        )
        self.qzone_act_op("勇士见面礼", "66614_23246ef1")
        if not self.cfg.function_switches.disable_share and is_first_run(
            f"dnf_yellow_diamond_{get_act_url('黄钻')}_分享_{self.uin()}"
        ):
            self.qzone_act_op(
                "分享给自己",
                "66615_9132410d",
                act_req_data={
                    "receivers": [
                        self.qq(),
                    ]
                },
            )
        self.qzone_act_op("分享领取礼包", "66616_44f492ad")

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

    # --------------------------------------------QQ空间 新版 集卡--------------------------------------------
    def is_new_version_ark_lottery(self) -> bool:
        """是否是新版集卡活动"""
        enabled_payed_act_funcs = [func for name, func in self.payed_activities()]
        return self.dnf_ark_lottery in enabled_payed_act_funcs

    def is_ark_lottery_enabled(self) -> bool:
        """当前生效的付费活动中是否包含集卡活动，用于判断主流程中是否需要进行自动赠送卡片以及展示集卡信息等流程"""
        enabled_payed_act_funcs = [func for name, func in self.payed_activities()]
        return self.dnf_ark_lottery in enabled_payed_act_funcs or self.ark_lottery in enabled_payed_act_funcs

    # note: 需要先在 https://act.qzone.qq.com/ 中选一个活动登陆后，再用浏览器抓包

    # note: 以下几个页面右键点击对应按钮即可，与上方黄钻完全一致，参照其流程即可
    ark_lottery_sub_act_id_login = "108898_92a8b20b"  # 增加抽卡次数-每日登陆游戏
    ark_lottery_sub_act_id_share = "108892_b1953027"  # 增加抽卡次数-每日活动分享
    ark_lottery_sub_act_id_lucky = "108893_487cfc0d"  # 增加抽卡次数-幸运勇士
    ark_lottery_sub_act_id_draw_card = "108894_1aa762dd"  # 抽卡
    ark_lottery_sub_act_id_award_1 = "108895_76bfc70d"  # 领取奖励-第一排
    ark_lottery_sub_act_id_award_2 = "108896_165559cb"  # 领取奖励-第二排
    ark_lottery_sub_act_id_award_3 = "108897_35d11133"  # 领取奖励-第三排
    ark_lottery_sub_act_id_award_all = "108900_ea724d2d"  # 领取奖励-十二张
    ark_lottery_sub_act_id_lottery = "108899_f41907a4"  # 消耗卡片来抽奖

    # note: 清空抓包数据，按f5刷新后，搜索  QueryItems  (hack: 其实就是活动链接的 最后一部分)
    ark_lottery_packet_id_card = "50140_591877ab"  # 查询当前卡片数目

    # note: xxx. 修改 urls.py 中的 pesudo_ark_lottery_act_id ，将其加一即可

    # re: 除此之外有一些额外的部分，参照旧版集卡 def ark_lottery(self): 的操作指引
    @try_except()
    def dnf_ark_lottery(self):
        get_act_url("集卡")
        show_head_line("QQ空间集卡")
        self.show_not_ams_act_info("集卡")

        if not self.cfg.function_switches.get_ark_lottery:
            logger.warning("未启用领取QQ空间集卡功能，将跳过")
            return

        self.fetch_pskey()
        if self.lr is None:
            return

        if self.get_dnf_bind_role() is None:
            logger.warning(
                "未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定，否则每日登录游戏和幸运勇士的增加抽卡次数将无法成功进行。"
            )

        # hack: 两个集卡版本时间重叠时的临时补丁
        if now_before("2024-04-20 23:59:59"):
            async_message_box(
                "新的集卡活动与上次的集卡活动在4.18到4.20这三天重叠了，上传了一个仅包含旧版本集卡活动的特别版本到群里了，请各位自行去下载过来，放到小助手目录里每天手动点击运行一下即可，21号及以后就不需要运行了",
                "集卡时间重叠",
                show_once_daily=True,
            )
            pass

        # 增加次数
        self.dnf_ark_lottery_add_ark_lottery_times()

        # 抽卡
        self.dnf_ark_lottery_draw_ark_lottery()

        # 领取集卡奖励
        self.dnf_ark_lottery_take_ark_lottery_awards()

        # 消耗卡片来抽奖
        self.dnf_ark_lottery_try_lottery_using_cards()

    def dnf_ark_lottery_add_ark_lottery_times(self):
        self.qzone_act_op("增加抽卡次数-每日登陆游戏", self.ark_lottery_sub_act_id_login)

        # 先尝试直接领取活动分享的次数
        self.qzone_act_op("增加抽卡次数-每日活动分享（不实际发送请求）", self.ark_lottery_sub_act_id_share)
        # 然后尝试发送给自己来领取
        if not self.cfg.function_switches.disable_share:
            async_message_box(
                "这次的集卡需要实际发送分享请求才能领取2次抽卡次数，这里尝试给自己发送分享链接，自己会收到自己发的一条卡片消息。如果无法忍受这个，可以去 配置工具/当前账号配置/活动开关/禁用分享功能 ，勾选这个就不会再尝试实际发送分享请求了，但代价是可能领不到这两次-。-",
                "集卡分享提示",
                show_once=True,
            )
            self.qzone_act_op(
                "增加抽卡次数-每日活动分享（给自己）",
                self.ark_lottery_sub_act_id_share,
                act_req_data={
                    "receivers": [
                        self.qq(),
                    ],
                    "send_type": 0,
                },
            )

        self.qzone_act_op(
            "增加抽卡次数-幸运勇士-尝试使用配置的幸运角色",
            self.ark_lottery_sub_act_id_lucky,
            act_req_data=self.try_make_lucky_user_req_data(
                "集卡", self.cfg.ark_lottery.lucky_dnf_server_id, self.cfg.ark_lottery.lucky_dnf_role_id
            ),
        )
        self.qzone_act_op("增加抽卡次数-幸运勇士-尝试使用当前角色", self.ark_lottery_sub_act_id_lucky)

    def dnf_ark_lottery_draw_ark_lottery(self):
        left, total = self.dnf_ark_lottery_remaining_lottery_times()
        logger.info(
            color("bold_green") + f"上述操作完毕后，历史累计获得次数为{total}，最新抽卡次数为{left}，并开始抽卡~"
        )
        for idx in range(left):
            self.qzone_act_op(f"抽卡-第{idx + 1}次", self.ark_lottery_sub_act_id_draw_card)

    def dnf_ark_lottery_take_ark_lottery_awards(self, print_warning=True):
        if self.cfg.ark_lottery.need_take_awards:
            self.qzone_act_op(f"{self.cfg.name} 领取奖励-第一排", self.ark_lottery_sub_act_id_award_1)
            self.qzone_act_op(f"{self.cfg.name} 领取奖励-第二排", self.ark_lottery_sub_act_id_award_2)
            self.qzone_act_op(f"{self.cfg.name} 领取奖励-第三排", self.ark_lottery_sub_act_id_award_3)
            self.qzone_act_op(f"{self.cfg.name} 领取奖励-十二张", self.ark_lottery_sub_act_id_award_all)
        else:
            if print_warning:
                logger.warning(
                    f"未配置领取集卡礼包奖励，如果账号【{self.cfg.name}】不是小号的话，建议去配置文件打开领取功能【need_take_awards】~"
                )

    def dnf_ark_lottery_try_lottery_using_cards(self, print_warning=True):
        if self.enable_cost_all_cards_and_do_lottery():
            if print_warning:
                logger.warning(
                    color("fg_bold_cyan") + "已开启消耗所有卡片来抽奖的功能，若尚未兑换完所有奖励，不建议开启这个功能"
                )
            if self.get_dnf_bind_role() is None:
                if print_warning:
                    logger.warning(
                        color("fg_bold_cyan") + f"账号 【{self.cfg.name}】 未在道聚城绑定DNF角色信息，无法进行集卡抽奖"
                    )
                return

            card_counts = self.dnf_ark_lottery_get_card_counts()
            max_count = max(card_counts.values())
            logger.info(
                color("bold_cyan") + f"将尝试均匀抽掉各个卡片，最多的卡片数目为 {max_count}，完整数目为 {card_counts}"
            )
            for lottery_idx in range_from_one(max_count):
                logger.info(color("bold_green") + f"----- 开始第 {lottery_idx}/{max_count} 轮 抽奖 -----")
                for card_id, count in card_counts.items():
                    if count >= lottery_idx:
                        res = self.lottery_using_card(f"{lottery_idx}/{count}", card_id)
                        # 中了用户总限制
                        # 中了用户日限制
                        if "限制" in res.get("Msg", ""):
                            logger.warning("当前已达到最大抽奖次数上限，将停止抽奖~")
                            return
        else:
            if print_warning:
                logger.warning(
                    color("fg_bold_cyan")
                    + f"尚未开启抽卡活动({self.urls.pesudo_ark_lottery_act_id})消耗所有卡片来抽奖的功能，建议所有礼包都兑换完成后开启该功能，从而充分利用卡片。"
                )
                logger.warning(
                    color("fg_bold_cyan")
                    + f"也可以选择开启最后一天自动抽奖功能（配置工具：公共配置/集卡/最后一天消耗全部卡片抽奖）。目前开关状态为：{self.common_cfg.cost_all_cards_and_do_lottery_on_last_day}"
                )

    def enable_cost_all_cards_and_do_lottery(self):
        if self.common_cfg.cost_all_cards_and_do_lottery_on_last_day and self.is_last_day():
            logger.info("已是最后一天，且配置在最后一天将全部卡片抽掉，故而将开始消耗卡片抽奖~")
            return True

        return self.cfg.ark_lottery.act_id_to_cost_all_cards_and_do_lottery.get(
            self.urls.pesudo_ark_lottery_act_id, False
        )

    def is_last_day(self) -> bool:
        act_info = get_not_ams_act("集卡")
        day_fmt = "%Y-%m-%d"
        return format_time(parse_time(act_info.dtEndTime), day_fmt) == format_now(day_fmt)

    def lottery_using_card(self, ctx: str, card_id: str) -> dict:
        return self.qzone_act_op(
            f"{ctx} 消耗卡片({card_id})来抽奖",
            self.ark_lottery_sub_act_id_lottery,
            extra_act_req_data={
                "items": json_compact(
                    [
                        {
                            "id": f"{card_id}",
                            "num": 1,
                        }
                    ]
                ),
            },
        )

    def dnf_ark_lottery_send_card(
        self, card_id: str, target_qq: str, card_count: int = 1, target_djc_helper: DjcHelper | None = None
    ) -> bool:
        url = self.urls.qzone_activity_new_send_card.format(g_tk=getACSRFTokenForAMS(self.lr.p_skey))
        # note: 这个packet id需要 抓手机包获取
        body = {
            "packetID": self.ark_lottery_packet_id_card,
            "items": [
                {
                    "id": card_id,
                    "num": card_count,
                }
            ],
            "uid": target_qq,
            "uidType": 1,
            "r": random.random(),
        }

        raw_res = self._qzone_act_op(f"{self.cfg.name} 赠送卡片 {card_id} 给 {target_qq}", url, body)

        # {"code": 0, "message": "succ", "data": {}}
        # {"code": 0, "message": "succ", "data": {"code": 999, "message": "用户1054073896已达到每日单Q上限"}}
        res = NewArkLotterySendCardResult().auto_update_config(raw_res)

        if not res.is_ok() and target_djc_helper is not None and self.common_cfg.enable_send_card_by_request:
            logger.warning(
                "赠送失败，可能是达到每日赠送上限，尝试使用索取功能来赠送(可通过 配置工具/公共配置/集卡/索取 开关来关闭)"
            )
            return self.dnf_ark_lottery_send_card_by_request(card_id, target_djc_helper, card_count)

        return res.is_ok()

    def dnf_ark_lottery_send_card_by_request(
        self, card_id: str, target_djc_helper: DjcHelper, card_count: int = 1
    ) -> bool:
        token = self.dnf_ark_lottery_send_card_by_request_step_request_card(card_id, target_djc_helper, card_count)
        if token == "":
            logger.warning(f"未能索取卡片 {card_id}")
            return False

        return self.dnf_ark_lottery_send_card_by_request_step_agree_request_card(token, card_id, target_djc_helper)

    def dnf_ark_lottery_send_card_by_request_step_request_card(
        self, card_id: str, target_djc_helper: DjcHelper, card_count: int = 1
    ) -> str:
        self_name, self_qq, _ = self.cfg.name, self.qq(), self.lr.p_skey
        target_name, target_qq, target_pskey = (
            target_djc_helper.cfg.name,
            target_djc_helper.qq(),
            target_djc_helper.lr.p_skey,
        )

        # 使用 目标账号 向 当前账号 发起 索取请求
        url = self.urls.qzone_activity_new_request_card.format(g_tk=getACSRFTokenForAMS(target_pskey))
        # note: 这个packet id需要 抓手机包获取
        body = {
            "packetID": self.ark_lottery_packet_id_card,
            "items": [
                {
                    "id": card_id,
                    "num": card_count,
                }
            ],
            "uid": self_qq,
            "uidType": 1,
            "r": random.random(),
        }

        ctx = f"{target_name}({target_qq}) 向 {self_name}({self_qq}) 请求卡片 {card_id}"
        raw_res = target_djc_helper._qzone_act_op(ctx, url, body)

        # {"code":0,"message":"succ","data":{"token":"7533_13e52f700103200619aSabcd"}}
        res = NewArkLotteryRequestCardResult().auto_update_config(raw_res)

        return res.data.token

    def dnf_ark_lottery_send_card_by_request_step_agree_request_card(
        self, token: str, card_id: str, target_djc_helper: DjcHelper
    ) -> bool:
        lr = self.fetch_club_vip_p_skey("集卡同意索取", cache_max_seconds=600)

        self_name, self_qq, self_pskey = self.cfg.name, self.qq(), lr.p_skey
        target_name, target_qq, _ = (
            target_djc_helper.cfg.name,
            target_djc_helper.qq(),
            target_djc_helper.lr.p_skey,
        )

        # 当前账号同意索取
        url = self.urls.qzone_activity_new_agree_request_card.format(
            token=token, g_tk=getACSRFTokenForAMS(self_pskey), rand=random.random()
        )

        ctx = f"{self_name}({self_qq}) 同意 {target_name}({target_qq}) 的 索取卡片 {card_id} 的请求，token={token}"
        raw_res = self._qzone_act_get_op(
            ctx,
            url,
            p_skey=self_pskey,
            extra_headers={
                "Content-Type": "application/json",
            },
        )

        # {"code":0,"message":"succ","data":{}}
        # {"code":0,"message":"succ","data":{"code":999,"message":"数量不足，不能进行赠送，索要"}}
        # {"code": 0, "message": "succ", "data": {"code": 999, "message": "用户1054073896已达到每日可被赠送上限"}}
        # {"code": 0, "message": "succ", "data": {"code": 999, "message": "用户1054073896已达到活动可被赠送上限"}}
        res = NewArkLotteryAgreeRequestCardResult().auto_update_config(raw_res)

        # 特殊处理目标QQ被赠送次数达到上限的情况，方便外面停止该流程
        if res.data.message in [f"用户{target_qq}已达到每日可被赠送上限", f"用户{target_qq}已达到活动可被赠送上限"]:
            raise ArkLotteryTargetQQSendByRequestReachMaxCount(res.data.message)

        return res.is_ok()

    @try_except(return_val_on_except=(0, 0))
    def dnf_ark_lottery_remaining_lottery_times(self) -> tuple[int, int]:
        """
        返回 剩余卡片数，总计获得卡片数
        """
        res = self.qzone_act_query_op("查询抽卡次数", self.ark_lottery_sub_act_id_draw_card, print_res=False)
        raw_data = json.loads(get_first_exists_dict_value(res, "data", "Data"))

        info = NewArkLotteryLotteryCountInfo().auto_update_config(
            raw_data["check_rule"]["prefer_rule_group"]["coins"][0]
        )

        return info.left, info.add

    @try_except(return_val_on_except={})
    def dnf_ark_lottery_get_card_counts(self) -> dict[str, int]:
        url = self.urls.qzone_activity_new_query_card.format(
            packetID=self.ark_lottery_packet_id_card,
            g_tk=getACSRFTokenForAMS(self.lr.p_skey),
        )
        body: dict = {}

        res = self._qzone_act_op("查询卡片", url, body, print_res=False)

        card_counts = {}
        # 初始化，确保每个卡片都有值
        for card_id in range_from_one(12):
            card_counts[str(card_id)] = 0

        # 填充实际值
        for item in res["data"].get("items", []):
            info = NewArkLotteryCardCountInfo().auto_update_config(item)

            card_counts[info.id] = info.num

        return card_counts

    def dnf_ark_lottery_get_prize_counts(self) -> dict[str, int]:
        # 新版本集卡无法查询奖励剩余兑换次数，因此直接写死，从而可以兼容旧版本代码
        return {
            "第一排": 1,
            "第二排": 1,
            "第三排": 1,
            "十二张": 10,
        }

    def dnf_ark_lottery_get_prize_names(self) -> list[str]:
        return list(self.dnf_ark_lottery_get_prize_counts().keys())

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

    def try_make_lucky_user_req_data(
        self, act_name: str, lucky_dnf_server_id: str, lucky_dnf_role_id: str
    ) -> dict | None:
        # 确认使用的角色
        server_id, roleid = "", ""
        if lucky_dnf_server_id == "":
            logger.warning(f"未配置{act_name}礼包的区服和角色信息，将使用道聚城绑定的角色信息")
            logger.warning(
                color("bold_cyan")
                + f"如果大号经常玩，建议去其他跨区建一个小号，然后不再登录，这样日后的{act_name}活动可以拿这个来获取回归相关的领取资格"
            )
        else:
            if lucky_dnf_role_id == "":
                logger.warning(
                    f"配置了{act_name}礼包的区服ID为{lucky_dnf_server_id}，但未配置角色ID，将打印该服所有角色信息如下，请将合适的角色ID填到配置表"
                )
                self.query_dnf_rolelist(lucky_dnf_server_id)
            else:
                logger.info(f"使用配置的区服和角色信息来进行领取{act_name}礼包")
                server_id, roleid = lucky_dnf_server_id, lucky_dnf_role_id

        # 如果设置了幸运角色，则构建幸运角色请求数据
        lucky_req_data = None
        if server_id != "" and roleid != "":
            # 如果配置了幸运角色，则使用配置的幸运角色来领取
            lucky_req_data = {
                "role_info": {
                    "area": server_id,
                    "partition": server_id,
                    "role": roleid,
                    "clientPlat": 3,
                    "game_id": "dnf",
                }
            }

        return lucky_req_data

    def qzone_act_op(self, ctx, sub_act_id, act_req_data=None, extra_act_req_data: dict | None = None, print_res=True):
        g_tk = getACSRFTokenForAMS(self.lr.p_skey)
        url = self.urls.qzone_activity_new.format(g_tk=g_tk)
        body = {
            "SubActId": sub_act_id,
            "ActReqData": json.dumps(self.get_qzone_act_req_data(act_req_data, extra_act_req_data)),
            "g_tk": g_tk,
        }

        return self._qzone_act_op(ctx, url, body, print_res)

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

    def get_qzone_act_req_data(self, act_req_data=None, extra_act_req_data: dict | None = None) -> dict:
        if act_req_data is None:
            roleinfo = RoleInfo()
            roleinfo.roleCode = "123456"
            try:
                _v = self.get_dnf_bind_role()
                assert _v is not None
                roleinfo = _v
            except Exception:
                pass
            act_req_data = {
                "role_info": {
                    "area": roleinfo.serviceID,
                    "partition": roleinfo.serviceID,
                    "role": roleinfo.roleCode,
                    "clientPlat": 3,
                    "game_id": "dnf",
                }
            }
        if extra_act_req_data is not None:
            act_req_data = {
                **act_req_data,
                **extra_act_req_data,
            }

        return act_req_data

    def qzone_act_query_op(self, ctx: str, sub_act_id: str, print_res=True):
        g_tk = getACSRFTokenForAMS(self.lr.p_skey)
        url = self.urls.qzone_activity_new_query.format(g_tk=g_tk)
        body = {
            "Id": sub_act_id,
            "g_tk": g_tk,
            "ExtInfo": {"0": ""},
        }

        return self._qzone_act_op(ctx, url, body, print_res)

    def _qzone_act_op(self, ctx: str, url: str, body: dict, print_res=True) -> dict:
        extra_cookies = f"p_skey={self.lr.p_skey}; "

        return self.post(ctx, url, json=body, extra_cookies=extra_cookies, print_res=print_res)

    def _qzone_act_get_op(self, ctx: str, url: str, p_skey: str = "", print_res=True, **params):
        p_skey = p_skey or self.lr.p_skey
        extra_cookies = f"p_skey={p_skey}; "

        return self.get(ctx, url, extra_cookies=extra_cookies, print_res=print_res, **params)

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

    # --------------------------------------------DNF漫画预约活动--------------------------------------------
    @try_except()
    def dnf_comic(self):
        show_head_line("DNF漫画预约活动")
        self.show_not_ams_act_info("DNF漫画预约活动")

        if not self.cfg.function_switches.get_dnf_comic or self.disable_most_activities():
            logger.warning("未启用领取DNF漫画预约活动功能，将跳过")
            return

        self.check_dnf_comic_ide()

        def query_comic_data() -> ComicDataList:
            def _do_query() -> ComicDataList:
                res = self.get(
                    "查询漫画更新数据",
                    self.urls.dnf_comic_update_api,
                    print_res=False,
                    prefix_to_remove="var DNF_2023COMIC_DATA=",
                    suffix_to_remove=";",
                )

                comic_data_list = ComicDataList()
                comic_data_list.auto_update_config({"comic_list": res})

                return comic_data_list

            return with_cache(
                "账号共用缓存",
                "查询漫画更新数据",
                cache_miss_func=_do_query,
                cache_max_seconds=24 * 60 * 60,
                cache_value_unmarshal_func=ComicDataList().auto_update_config,
            )

        # self.dnf_comic_ide_op("发送短信验证码（绑定）", "248526")
        # self.dnf_comic_ide_op("绑定手机，领取预约礼包", "248528")
        # self.dnf_comic_ide_op("发送短信验证码（解绑）", "248830")
        # self.dnf_comic_ide_op("解绑手机", "248941")
        # async_message_box(
        #     "漫画预约活动需要绑定手机验证码才能领取，可获得3天黑钻和一个增肥器，有兴趣的朋友请在稍后打开的页面中自行绑定",
        #     "漫画预约",
        #     open_url=get_act_url("DNF漫画预约活动"),
        #     show_once=True,
        # )

        self.dnf_comic_ide_op("抽奖（13件福利任抽）", "248953")
        time.sleep(1)
        self.dnf_comic_ide_op("每周在线礼包", "248990")
        time.sleep(1)

        comic_data_list: ComicDataList = query_comic_data()

        current_updated = comic_data_list.get_current_update_progress()
        total_episodes = len(comic_data_list.comic_list)
        logger.info(
            color("bold_cyan")
            + f"当前预计更新到 第{current_updated}/{total_episodes} 集，开始尝试领取（已更新的每集每周最多尝试领取1次）"
        )

        for idx, comic_data in enumerate(comic_data_list.comic_list):
            if not comic_data.has_updated():
                logger.info(
                    color("bold_yellow") + f"当前活动页面更新至第 {current_updated} 集，不执行后续部分，避免被钓鱼<_<"
                )

                # 目前是假设集数升序，且必定前面的前半部分是已更新，后续则全是未更新，为避免后续数据调整，这里检查下，不符合假设时给自己个提示
                if use_by_myself():
                    for other_idx, other_comic_data in enumerate(comic_data_list.comic_list):
                        if other_idx <= idx:
                            continue

                        if other_comic_data.has_updated():
                            async_message_box(
                                "漫画活动在首个未更新集数后面出现了已更新的数据，不符合预期，需要调整下写法",
                                "漫画活动数据不符合预期",
                            )

                break

            if is_weekly_first_run(f"comic_watch_{self.uin()}_{comic_data.id}"):
                self.dnf_comic_ide_op(f"观看漫画，领取星星 第 {comic_data.id} 集", "248950", index=comic_data.id)
                time.sleep(1)

        # 需要观看（也就是领取一集漫画的星星）后才能领取，所以放到领取星星之后
        self.dnf_comic_ide_op("领取观看礼包", "248947")

        star_count = self.query_dnf_comic_star_count()
        msg = f"账号 {self.cfg.name} 当前共有{star_count}颗星星"
        logger.info(color("bold_yellow") + msg)

        # 兑换道具
        star_not_enough = self.comic_exchange_items()
        logger.info(f"道具兑换完毕，是否是因星星不足而中断: {star_not_enough}")

        if self.cfg.comic.enable_lottery:
            logger.info("已开启自动抽奖，将开始抽奖流程~")
            for idx in range_from_one(star_count):
                self.dnf_comic_ide_op(f"第{idx}/{star_count}次星星夺宝", "248988")
                time.sleep(3)
        elif not star_not_enough:
            # 如果兑换道具不是因为星星不够而停止的，那么若还有星星，则尝试提示下
            star_count = self.query_dnf_comic_star_count()
            if star_count > 0:
                msg = f"账号 {self.cfg.name} 已配置的兑换道具操作完后，仍有{star_count}颗星星，可考虑打开配置工具【漫画】，设置更多兑换道具，或打开抽奖开关，启用自动抽奖功能~"
                async_message_box(
                    msg,
                    f"{self.cfg.name}_漫画活动_提示抽奖",
                    open_url=get_act_url("DNF漫画预约活动"),
                    show_once_monthly=True,
                )

    @try_except(return_val_on_except=0)
    def query_dnf_comic_star_count(self) -> int:
        res = self.dnf_comic_ide_op("查询星星数目", "248455", print_res=False)

        star_count = int(res["jData"]["starNum"])
        return star_count

    @try_except()
    def comic_exchange_items(self) -> bool:
        retryCfg = self.common_cfg.retry
        # 设置最少等待时间
        wait_time = max(retryCfg.request_wait_time, 10)
        retry_wait_time = max(retryCfg.retry_wait_time, 5)

        star_not_enough = False

        for ei in self.cfg.comic.exchange_items:
            # 是否立即尝试下一个道具
            try_next_item_now = False

            for progress in range_from_one(ei.count):
                ctx = f"漫画兑换 {ei.name}({progress}/{ei.count})"

                for _try_index in range(retryCfg.max_retry_count):
                    res = self.dnf_comic_ide_op(ctx, "249077", index=ei.index)

                    ret = res["ret"]
                    # sMsg = res["sMsg"]

                    if ret == 400001:
                        # { "ret": 400001, "iRet":400001, "sMsg": "抱歉，您当前剩余的星星数量不足", ...}
                        logger.info("当前星星不够，不再尝试兑换后续道具")
                        star_not_enough = True
                        return star_not_enough
                    elif ret == 100001:
                        # 次数上限
                        logger.info("兑换次数已达上限，尝试下一个道具")
                        try_next_item_now = True
                        break
                    elif ret != 0:
                        if use_by_myself():
                            async_message_box(
                                f"【仅自己可见】漫画活动 ret={ret}, 增加处理下这种情况，具体res如下\n{res}",
                                "漫画兑换其他错误码",
                            )

                        _ = retry_wait_time
                        try_next_item_now = True
                        break

                    # 成功 {"ret": 0, "iRet": 0, "sMsg": "ok", ...}
                    logger.debug(f"漫画兑换 {ei.name} ok，等待{wait_time}s，避免请求过快报错")
                    time.sleep(wait_time)
                    break

                if try_next_item_now:
                    time.sleep(wait_time)
                    break

        return star_not_enough

    def check_dnf_comic(self):
        self.check_bind_account(
            "qq视频-DNF漫画预约活动",
            get_act_url("DNF漫画预约活动"),
            activity_op_func=self.dnf_comic_op,
            query_bind_flowid="774762",
            commit_bind_flowid="774761",
        )

    def dnf_comic_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_comic
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF漫画预约活动"),
            **extra_params,
        )

    def check_dnf_comic_ide(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF漫画预约活动",
            get_act_url("DNF漫画预约活动"),
            activity_op_func=self.dnf_comic_ide_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_comic_ide_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_comic

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF漫画预约活动"),
            **extra_params,
        )

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

    # --------------------------------------------qq视频蚊子腿-爱玩--------------------------------------------
    # note: 接入流程
    #   1. 浏览器使用 手机QQ UA 打开活动页面
    #   2. 在下面对应的 各个按钮 上右键查看元素，复制其中的 single_task_id 的值
    #   3. 更新 url 和 活动时间
    @try_except()
    def qq_video_iwan(self):
        show_head_line("qq视频蚊子腿-爱玩")
        self.show_not_ams_act_info("qq视频蚊子腿-爱玩")

        if not self.cfg.function_switches.get_qq_video or self.disable_most_activities():
            logger.warning("未启用领取qq视频蚊子腿-爱玩功能，将跳过")
            return

        if self.cfg.login_mode != self.cfg.login_mode_auto_login:
            async_message_box(
                "新版QQ视频需要额外获取一些登陆票据，因此将弹出一个登录框。小号似乎不能参与这个活动，会一直提示【登陆态失效，请重新登录！】。因此有号不能完成登录的，可以自行将qq视频蚊子腿的开关先关闭（下次有新的qq视频蚊子腿的时候记得打开）。",
                "qq视频蚊子腿-爱玩-登录提示",
                show_once=True,
            )

        lr = self.fetch_iwan_login_info("获取openid和access_token")
        access_token = lr.iwan_access_token
        openid = lr.iwan_openid
        if access_token == "" or openid == "":
            logger.warning(
                f"openid和access_token未能成功获取，将无法领取qq视频蚊子腿。access_token={access_token}, openid={openid}"
            )
            return

        self.qq_appid = "101489622"
        self.qq_access_token = access_token
        self.qq_openid = openid

        # -----------------------------------------------

        logger.warning(
            color("bold_yellow")
            + "如果下面的请求提示 【登陆态失效，请重新登录！】，很有可能是你的号不能参与这个活动。手动登录这个活动的网页，然后点击领取，应该也会弹相同的提示"
        )

        self.qq_video_iwan_op("幸运勇士礼包", "xjN0qL0uZE")
        # self.qq_video_iwan_op("全民大礼包", "2hiHF_yAf")
        self.qq_video_iwan_op("勇士见面礼", "a69YMxiANa")
        # self.qq_video_iwan_op("每日抽奖（需要在页面开视频会员）", "fj174odxr")
        # self.qq_video_iwan_op("在线30分钟签到", "1X7VUbqgr")
        # self.qq_video_iwan_op("累计 3 天", "ql8qD9_NH")
        # self.qq_video_iwan_op("累计 7 天", "jyi3LQ9bo")
        # self.qq_video_iwan_op("累计 10 天", "uBiO594xn")
        # self.qq_video_iwan_op("累计 15 天", "U4urMEDRr")

        # act_url = get_act_url("qq视频蚊子腿-爱玩")
        # async_message_box(
        #     "QQ视频活动有个专属光环和其他道具可以兑换，不过至少得在页面上充值两个月的QQ视频会员。各位如有需求，可以自行前往活动页面进行购买与兑换~",
        #     f"QQ视频活动-光环-{act_url}",
        #     open_url=act_url,
        #     show_once=True,
        # )

    def qq_video_iwan_op(self, ctx: str, missionId: str, qq_access_token="", qq_openid="", qq_appid="", print_res=True):
        role = self.get_dnf_bind_role_copy()

        qq_access_token = qq_access_token or self.qq_access_token
        qq_openid = qq_openid or self.qq_openid
        qq_appid = qq_appid or self.qq_appid

        extra_cookies = "; ".join(
            [
                f"vqq_vuserid={self.get_vuserid()}",
                f"vqq_appid={qq_appid}",
                f"vqq_access_token={qq_access_token}",
                f"vqq_openid={qq_openid}",
                "main_login=qq",
            ]
        )

        return self.get(
            ctx,
            self.urls.qq_video_iwan,
            missionId=missionId,
            serverId=role.serviceID,
            sRoleId=role.roleCode,
            print_res=print_res,
            extra_cookies=extra_cookies,
        )

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

    def show_dnf_helper_info_guide(self, extra_msg="", show_message_box_once_key="", always_show_message_box=False):
        if extra_msg != "":
            logger.warning(color("fg_bold_green") + extra_msg)

        tips = "\n".join(
            [
                extra_msg,
                "",
                f"账号 {self.cfg.name} 助手token已过期或者未填写，请打开【使用教程/使用文档.docx】，查看其中的【获取助手token】章节的说明",
            ]
        )

        logger.warning("\n" + color("fg_bold_yellow") + tips)
        # 首次在对应场景时弹窗
        if always_show_message_box or (
            show_message_box_once_key != ""
            and is_first_run(self.get_show_dnf_helper_info_guide_key(show_message_box_once_key))
        ):
            async_message_box(tips, "助手信息获取指引", print_log=False)

    def reset_show_dnf_helper_info_guide_key(self, show_message_box_once_key: str):
        reset_first_run(self.get_show_dnf_helper_info_guide_key(show_message_box_once_key))

    def get_show_dnf_helper_info_guide_key(self, show_message_box_once_key: str) -> str:
        return f"show_dnf_helper_info_guide_{self.cfg.get_account_cache_key()}_{show_message_box_once_key}"

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

    # --------------------------------------------dnf助手活动(后续活动都在这个基础上改)--------------------------------------------
    # note: 接入流程说明
    #   1. 助手app分享活动页面到qq，发送到电脑
    #   2. 电脑在chrome打开链接，并将 useragent 调整为 Mozilla/5.0 (Linux; Android 9; MIX 2 Build/PKQ1.190118.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045714 Mobile Safari/537.36 GameHelper_1006/2103060508
    #   3. 过滤栏输入 -webvitals -.png -speed? -.js -.jpg -data: -analysis -eas.php -pingd? -log? -pv? -favicon.ico -performance? -whitelist? -asynccookie
    #   4. 在页面上按正常流程点击，然后通过右键/copy/copy as cURL(bash)来保存对应请求的信息
    #   5. 实现自定义的部分流程（非ams的部分）
    @try_except()
    def dnf_helper(self):
        show_head_line("dnf助手")

        if not self.cfg.function_switches.get_dnf_helper or self.disable_most_activities():
            logger.warning("未启用领取dnf助手活动功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.show_amesvr_act_info(self.dnf_helper_op)

        if self.cfg.dnf_helper_info.token == "":
            extra_msg = "未配置dnf助手相关信息，无法进行dnf助手相关活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(
                extra_msg, show_message_box_once_key=f"dnf_helper_{get_act_url('dnf助手活动')}"
            )
            return

        # re: 根据本次是否需要手动绑定决定是否需要下面这行
        # self.check_dnf_helper()

        def query_heart() -> tuple[int, int]:
            res = self.dnf_helper_op("查询", "977070", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            remaining, total = raw_info.sOutValue3.split(";")

            return int(remaining), int(total)

        self.dnf_helper_op("加好友-关注老搬", "977071")

        self.dnf_helper_op("20000", "977045")
        self.dnf_helper_op("50000", "977066")
        self.dnf_helper_op("120000", "977067")
        self.dnf_helper_op("200000", "977068")
        self.dnf_helper_op("400000", "977069")

        self.dnf_helper_op("浏览作品", "977603")
        self.dnf_helper_op("浏览动态", "977604")
        self.dnf_helper_op("发帖", "977605")
        self.dnf_helper_op("分享", "977606")

        self.dnf_helper_op("浏览老搬作品", "977599")
        self.dnf_helper_op("浏览老搬动态", "977600")
        self.dnf_helper_op("老搬宠粉发帖", "977601")
        self.dnf_helper_op("分享此活动", "977602")
        self.dnf_helper_op("绑定50爱心-邀请流失勇士关注老搬", "982386")

        remaining, total = query_heart()
        logger.info(f"爱心目前拥有：{remaining}，总计 {total}")
        for idx in range_from_one(remaining):
            self.dnf_helper_op(f"{idx}/{remaining} 献出爱心&返回排名", "977789")
            time.sleep(3)

    def check_dnf_helper(self):
        self.check_bind_account(
            "dnf助手活动",
            get_act_url("dnf助手活动"),
            activity_op_func=self.dnf_helper_op,
            query_bind_flowid="929705",
            commit_bind_flowid="929704",
        )

    # def dnf_helper_format_url(self, api: str) -> str:
    #     dnf_helper_info = self.cfg.dnf_helper_info
    #     roleinfo = self.get_dnf_bind_role()
    #
    #     url = self.format(
    #         self.urls.dnf_helper,
    #         api=api,
    #         roleId=roleinfo.roleCode,
    #         uniqueRoleId=dnf_helper_info.uniqueRoleId,
    #         serverName=quote_plus(roleinfo.serviceName),
    #         toUin=self.qq(),
    #         userId=dnf_helper_info.userId,
    #         serverId=roleinfo.serviceID,
    #         token=dnf_helper_info.token,
    #         areaId=roleinfo.areaID,
    #         areaName=quote_plus(roleinfo.areaName),
    #         roleJob="",
    #         nickname=quote_plus(dnf_helper_info.nickName),
    #         roleName=quote_plus(roleinfo.roleName),
    #         uin=self.qq(),
    #         roleLevel="100",
    #     )
    #
    #     return url

    def dnf_helper_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_helper

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
            get_act_url("dnf助手活动"),
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

    # --------------------------------------------dnf助手活动wpe--------------------------------------------
    # re: 搜 wpe类活动的接入办法为
    @try_except()
    def dnf_helper_wpe(self):
        show_head_line("dnf助手活动wpe")
        self.show_not_ams_act_info("dnf助手活动wpe")

        if not self.cfg.function_switches.get_dnf_helper_wpe or self.disable_most_activities():
            logger.warning("未启用领取dnf助手活动wpe功能，将跳过")
            return

        self.prepare_wpe_act_openid_accesstoken("dnf助手活动wpe")

        self.dnf_helper_wpe_op("扬帆见面礼", 143111)
        self.dnf_helper_wpe_op("幸运见面礼", 143100)

        self.dnf_helper_wpe_op("每周登录领取-1", 144574)
        self.dnf_helper_wpe_op("每周登录领取-2", 144745)
        self.dnf_helper_wpe_op("每周登录领取-3", 144746)
        self.dnf_helper_wpe_op("每周登录领取-4", 144747)

        act_info = get_not_ams_act("dnf助手活动wpe")
        async_message_box(
            (
                "助手活动扬帆苍穹之上活动邀请回归玩家可以获得印记，用于领取+10增幅券（需邀请3个回归才能解锁），同时每周登录4次也可以领取一个印记\n"
                f"为了避免影响想邀请回归领取+10券的朋友，同时不做这部分的也不会浪费，小助手将会在活动最后一天({act_info.get_endtime()})自动抽奖，所以请想要做的朋友在最后一天前完成兑换，避免被自动抽掉"
            ),
            "助手专属活动邀请回归玩家",
            show_once=True,
            open_url=get_act_url("dnf助手活动wpe"),
        )
        if not act_info.is_last_day():
            logger.warning(f"当前未到活动最后一天({act_info.get_endtime()})，将不会尝试自动抽奖")
        else:
            logger.warning(f"当前是活动最后一天({act_info.get_endtime()})，将尝试自动抽奖，避免印记被浪费掉")
            for idx in range_from_one(30):
                # note: 对应搜索 lotteryFlowID
                res = self.dnf_helper_wpe_op(f"立即抽奖-{idx}", 143109)
                if "消耗殆尽" in res["msg"] or "已用完" in res["msg"] or "不足" in res["msg"]:
                    break
                time.sleep(5)

        self.dnf_helper_wpe_op("回归-今日登录游戏", 143093)
        self.dnf_helper_wpe_op("回归-今日在线60分钟", 144510)
        self.dnf_helper_wpe_op("回归-通关推荐地下城3次", 144511)
        self.dnf_helper_wpe_op("回归-消耗100点疲劳", 144512)
        self.dnf_helper_wpe_op("回归-今日通关巴卡尔副本1次", 144515)

    def dnf_helper_wpe_op(self, ctx: str, flow_id: int, print_res=True, **extra_params):
        # 该类型每个请求之间需要间隔一定时长，否则会请求失败
        time.sleep(3)

        roleinfo = self.get_dnf_bind_role()

        act_id = 16096

        json_data = {
            "biz_id": "bb",
            "act_id": act_id,
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
            "data": json.dumps(
                {
                    "num": 1,
                    "ceiba_plat_id": "ios",
                    "user_attach": json.dumps({"nickName": quote(roleinfo.roleName)}),
                    "cExtData": {},
                }
            ),
        }

        return self.post(
            ctx,
            self.urls.dnf_helper_wpe_api,
            flowId=flow_id,
            actId=act_id,
            json=json_data,
            print_res=print_res,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
        )

    # --------------------------------------------超核勇士wpe--------------------------------------------
    # re: 搜 wpe类活动的接入办法为
    @try_except()
    def dnf_chaohe_wpe(self):
        show_head_line("超核勇士wpe")
        self.show_not_ams_act_info("超核勇士wpe")

        if not self.cfg.function_switches.get_dnf_chaohe_wpe or self.disable_most_activities():
            logger.warning("未启用领取超核勇士wpe功能，将跳过")
            return

        self.prepare_wpe_act_openid_accesstoken("超核勇士wpe")

        def query_count(ctx: str, flow_id: int) -> tuple[int, int]:
            res = self.dnf_chaohe_wpe_op(ctx, flow_id, print_res=False)
            data = json.loads(res["data"])

            remain = data["remain"]
            total = data["total"]

            return remain, total

        def query_is_chaohe() -> bool:
            # {"data": {}, "ret": 7001, "msg": "login status verification failed: 参数无效，检查请求参数"}
            # {"ret": 0, "msg": "抱歉，仅限已添加管家闪闪的DNF超核玩家才可参与活动哦。", "data": "{\"msg\":\"抱歉，仅限已添加管家闪闪的DNF超核玩家才可参与活动哦。\",\"ret\":40006}", "serialId": "ceiba-supercore-16726-157132-1709393654494-8ea5639454"}
            res = self.dnf_chaohe_wpe_op("尝试请求，判断是否是超核玩家", 157132)

            is_chaohe = not (
                (res["ret"] == 0 and res["msg"] == "抱歉，仅限已添加管家闪闪的DNF超核玩家才可参与活动哦。")  # 不是超核
                or (
                    res["ret"] == 7001 and res["msg"] == "login status verification failed: 参数无效，检查请求参数"
                )  # 登录参数有误
            )
            return is_chaohe

        is_chaohe = query_is_chaohe()
        if not is_chaohe:
            logger.warning(color("bold_yellow") + "当前账号不是超核玩家，将跳过超核勇士wpe活动")
            return

        # 成长系列任务
        self.dnf_chaohe_wpe_op("1、活动期间累积登录游戏3天（超能积分+50） ", 157132)
        self.dnf_chaohe_wpe_op("2、活动期间累积登录游戏6天（超能积分+50）", 157133)
        self.dnf_chaohe_wpe_op("3、活动期间累积登录游戏12天（超能积分+100）", 157134)
        self.dnf_chaohe_wpe_op("4、活动期间累积登录游戏18天（超能积分+200）", 157135)
        self.dnf_chaohe_wpe_op("5、活动期间累积登录游戏24天（超能积分+400）", 157136)
        self.dnf_chaohe_wpe_op("6、活动期间强化或增幅成功装备≥3次（超能积分+100）", 157137)
        self.dnf_chaohe_wpe_op("7、活动期间强化或增幅成功装备≥6次（超能积分+200）", 157138)
        self.dnf_chaohe_wpe_op("8、活动期间强化或增幅成功装备≥9次（超能积分+300）", 157139)
        self.dnf_chaohe_wpe_op("9、激战均衡仲裁者系列任务当月通关100次（超能积分+300）", 157140)
        self.dnf_chaohe_wpe_op("10、激战均衡仲裁者系列任务当月通关200次（超能积分+600）", 157141)
        self.dnf_chaohe_wpe_op("11、挑战幽暗岛系列任务当月通关4次（超能积分+1000）", 157142)
        self.dnf_chaohe_wpe_op("12、盖波加系列任务当月通关4次（超能积分+500）", 157143)
        self.dnf_chaohe_wpe_op("13、巴卡尔系列任务当月通关4次（超能积分+800）", 157144)

        # 挑战系列任务
        self.dnf_chaohe_wpe_op("1、活动期间账号内1个角色达到5.3万名望（超能积分+600）", 157145)
        self.dnf_chaohe_wpe_op("2、活动期间账号内2个角色达到5.3万名望（超能积分+600）", 157146)
        self.dnf_chaohe_wpe_op("3、活动期间账号内3个角色达到5.3万名望（超能积分+600）", 157147)
        self.dnf_chaohe_wpe_op("4、活动期间帐号充值点券数量≥100000（超能积分+500）", 157148)
        self.dnf_chaohe_wpe_op("5、活动期间帐号充值点券数量≥200000（超能积分+500）", 157149)
        self.dnf_chaohe_wpe_op("6、活动期间帐号充值点券数量≥300000（超能积分+500）", 157150)
        self.dnf_chaohe_wpe_op("7、活动期间帐号充值点券数量≥400000（超能积分+500）", 157151)
        self.dnf_chaohe_wpe_op("8、活动期间帐号充值点券数量≥500000（超能积分+500）", 157152)
        self.dnf_chaohe_wpe_op("9、活动期间帐号充值点券数量≥1000000（超能积分+1000）", 157153)
        self.dnf_chaohe_wpe_op("10、活动期间帐号充值点券数量≥2000000（超能积分+2000）", 157154)

        # 超能成长礼
        remain_point, total_point = query_count("查询 当前已获得超能积分", 157131)
        logger.info(f"超能积分 目前剩余：{remain_point}，累计获得 {total_point}")

        self.dnf_chaohe_wpe_op("雏鹰勇士 1500积分", 158781)
        self.dnf_chaohe_wpe_op("潜能勇士 3000积分", 158788)
        self.dnf_chaohe_wpe_op("飞升勇士 4500积分", 158789)
        self.dnf_chaohe_wpe_op("领航勇士 6000积分", 158790)
        self.dnf_chaohe_wpe_op("缔造勇士 7500积分", 158791)
        self.dnf_chaohe_wpe_op("光辉勇士 9000积分", 158792)
        self.dnf_chaohe_wpe_op("圣光勇士 10500积分", 158793)
        self.dnf_chaohe_wpe_op("神迹勇士 12000积分", 158794)
        self.dnf_chaohe_wpe_op("传奇勇士 13500积分", 158795)

        # 超能幸运礼
        remain_lottery_times, total_lottery_times = query_count("查询 当前已获得抽奖次数", 158867)
        logger.info(f"抽奖次数 目前剩余：{remain_lottery_times}，累计获得 {total_lottery_times}")
        for idx in range_from_one(remain_lottery_times):
            self.dnf_chaohe_wpe_op(f"[{idx}/{remain_lottery_times}] 开启礼盒", 158877)
            time.sleep(3)

        # 超能聚宝阁
        remain_exchange_point, total_exchange_point = query_count("查询 当前已获得兑换积分", 158876)
        logger.info(f"兑换积分 目前剩余：{remain_exchange_point}，累计获得 {total_exchange_point}")
        if remain_exchange_point > 0:
            async_message_box(
                f"当前拥有兑换积分 {remain_exchange_point}，可点击确认前往活动页面兑换 +11增幅券（6000积分）、梦想白金（6000积分）等道具",
                "超核勇士活动兑换道具",
                show_once_weekly=True,
                open_url=get_act_url("超核勇士wpe"),
            )

    def dnf_chaohe_wpe_op(self, ctx: str, flow_id: int, print_res=True, **extra_params):
        # 该类型每个请求之间需要间隔一定时长，否则会请求失败
        time.sleep(3)

        roleinfo = self.get_dnf_bind_role()

        act_id = 16726

        json_data = {
            "biz_id": "supercore",
            "act_id": act_id,
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
            "data": json.dumps(
                {
                    "ceiba_plat_id": "ios",
                    "gid": "1",
                    "c_bind_club_id": "",
                    "user_attach": json.dumps({"nickName": quote(roleinfo.roleName)}),
                    "cExtData": {},
                }
            ),
        }

        return self.post(
            ctx,
            self.urls.dnf_chaohe_wpe_api,
            flowId=flow_id,
            actId=act_id,
            json=json_data,
            print_res=print_res,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
        )

    # --------------------------------------------dnf助手编年史活动--------------------------------------------
    # note: 测试流程
    #   1. 使用手机抓包编年史页面，获取带各种校验参数的链接，并分享到电脑（或者直接在 https://mwegame.qq.com/fe/dnf/calculation/? 后面加上从生日活动获得的参数也可以）
    #   2. 电脑使用chrome打开上述链接，并设置为手机模式，ua则使用 上面抓包得到的，或者： Mozilla/5.0 (Linux; Android 9; MIX 2 Build/PKQ1.190118.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045714 Mobile Safari/537.36 GameHelper_1006/2103060508
    #   3. 在活动页面或者其他页面完成登陆后，即可正常测试
    #   4. 脚本信息
    #   4.1 入口：umi.{xxxx}.js
    #   4.2 可用chrome格式化后，按照下列方式定位相关代码
    #   4.3 参数信息：可搜索 common_params 中的对应key
    #   4.4 接口代码：搜索 对应接口的api名称，如 list/exchange
    @try_except()
    def dnf_helper_chronicle(self, take_task_award_only=False):  # noqa: C901
        # dnf助手左侧栏
        show_head_line("dnf助手编年史")
        self.show_not_ams_act_info("DNF助手编年史")

        if not self.cfg.function_switches.get_dnf_helper_chronicle or self.disable_most_activities():
            logger.warning("未启用领取dnf助手编年史活动功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # 为了不与其他函数名称冲突，且让函数名称短一些，写到函数内部~
        dnf_helper_info = self.cfg.dnf_helper_info
        roleinfo = self.get_dnf_bind_role()
        partition = roleinfo.serviceID
        roleid = roleinfo.roleCode

        common_params = {
            "userId": dnf_helper_info.userId,
            "sPartition": partition,
            "sRoleId": roleid,
            "print_res": False,
            "uin": self.qq(),
            "toUin": self.qq(),
            "token": dnf_helper_info.token,
            "uniqueRoleId": dnf_helper_info.uniqueRoleId,
        }

        hmac_sha1_secret = "nKJH89hh@8yoHJ98y&IOhIUt9hbOh98ht"

        # ------ 封装通用接口 ------
        def append_signature_to_data(
            data: dict[str, Any],
            http_method: str,
            api_path: str,
        ):
            # 补充参数
            data["tghappid"] = "1000045"
            data["cRand"] = get_millsecond_timestamps()

            # 构建用于签名的请求字符串
            post_data = make_dnf_helper_signature_data(data)

            # 计算签名
            signature = make_dnf_helper_signature(http_method, api_path, post_data, hmac_sha1_secret)

            # 添加签名
            data["sig"] = signature
            return

        def try_fetch_xinyue_openid_access_token():
            nonlocal common_params

            if not self.cfg.dnf_helper_info.disable_fetch_access_token:
                # 这里理论上要使用助手的appid 1105742785，但是似乎使用心悦app的好像也可以-。-就直接用心悦的咯
                appid = "101484782"

                lr = self.fetch_xinyue_login_info("借用心悦app的accessToken来完成编年史所需参数")
                access_token = lr.xinyue_access_token
                openid = lr.openid

                common_params = {
                    **common_params,
                    "appid": appid,
                    "appOpenid": openid,
                    "accessToken": access_token,
                }

        def get_millsecond_timestamps() -> int:
            return int(datetime.datetime.now().timestamp() * 1000)

        def get_api_path(url_template: str, **params) -> str:
            full_url = self.format(url_template, **params)
            api_path = urlparse(full_url).path

            return api_path

        def get_url_query_data(url_template: str, **params) -> dict[str, str]:
            full_url = self.format(url_template, **params)
            query_string = urlparse(full_url).query

            query_data = dict(parse_qsl(query_string, keep_blank_values=True))

            return query_data

        def wang_get(ctx: str, api: str, **extra_params) -> dict:
            data = {
                **common_params,
                **extra_params,
            }
            api_path = get_api_path(self.urls.dnf_helper_chronicle_wang_xinyue, api=api, **data)
            actual_query_data = get_url_query_data(self.urls.dnf_helper_chronicle_wang_xinyue, api=api, **data)

            append_signature_to_data(actual_query_data, "GET", api_path)

            res = self.get(
                ctx,
                self.urls.dnf_helper_chronicle_wang_xinyue,
                api=api,
                **{
                    **data,
                    **actual_query_data,
                },
            )
            return res

        def wegame_post(ctx: str, api: str, **extra_params) -> dict:
            data = {
                **common_params,
                **extra_params,
            }
            api_path = get_api_path(self.urls.dnf_helper_chronicle_mwegame, api=api, **data)
            append_signature_to_data(data, "POST", api_path)

            res = self.post(
                ctx,
                self.urls.dnf_helper_chronicle_mwegame,
                api=api,
                **data,
            )
            return res

        def yoyo_post(ctx: str, api: str, **extra_params) -> dict:
            data = {
                **common_params,
                **extra_params,
            }
            api_path = get_api_path(self.urls.dnf_helper_chronicle_yoyo, api=api)
            append_signature_to_data(data, "POST", api_path)

            res = self.post(
                ctx,
                self.urls.dnf_helper_chronicle_yoyo,
                api=api,
                data=post_json_to_data(data),
            )
            return res

        # ------ 自动绑定 ------
        @try_except(return_val_on_except=None)
        def try_auto_bind() -> DnfHelperChronicleUserTaskList | None:
            task_info = None

            partner_user_id = ""
            partner_name = ""
            is_auto_match = False

            # --------------------- 获取队友信息 ---------------------
            # 固定队友
            if dnf_helper_info.pUserId != "":
                partner_user_id = dnf_helper_info.pUserId
                partner_name = dnf_helper_info.pNickName
                logger.info(color("bold_cyan") + f"当前尚无搭档，但是配置了固定搭档信息 - {partner_user_id}")

            # 自动匹配
            if dnf_helper_info.enable_auto_match_dnf_chronicle:
                logger.info(color("bold_yellow") + "当前尚无搭档，但是配置了自动匹配功能，将尝试自动匹配")
                if self.check_dnf_helper_chronicle_auto_match(self.user_buy_info):
                    is_auto_match = True

                    # 尝试从服务器匹配一个编年史用户
                    partner_user_id = get_chronicle_user_id_from_server(dnf_helper_info.userId, self.qq())
                    partner_name = "自动绑定"
                    logger.info(f"自动匹配的搭档为 {partner_user_id}")
                else:
                    logger.info("不符合自动匹配条件，将跳过~")

            # --------------------- 尝试绑定 ---------------------
            if partner_user_id != "":
                partner_desc = f"{partner_name}({partner_user_id})"
                logger.info(color("bold_cyan") + f"将尝试绑定 {partner_desc}")
                bind_user_partner(f"绑定搭档 - {partner_desc}", partner_user_id)

                task_info = getUserTaskList()

            # --------------------- 尝试加入匹配队列 ---------------------
            if is_auto_match:
                matched = True
                if task_info is None:
                    # 未匹配到其他用户，大概率是匹配队列为空
                    matched = False
                elif not task_info.hasPartner:
                    # 匹配到了用户，但是未绑定成功
                    matched = False

                if not matched:
                    # 如果符合自动匹配条件，且未自动绑定成功，则加入服务器端的匹配队列
                    logger.info(
                        f"未匹配到其他用户，或者未绑定成功。将尝试上报 {self.cfg.name} 的dnf编年史信息 {dnf_helper_info.userId} 到服务器"
                    )
                    report_chronicle_user_id_to_server(dnf_helper_info.userId, self.qq())

            # --------------------- 返回可能更新后的task_info ---------------------
            return task_info

        @try_except()
        def report_chronicle_user_id_to_server(user_id: str, qq: str):
            req = DnfChronicleMatchServerAddUserRequest()
            req.user_id = user_id
            req.qq = qq

            self.post(
                "上报编年史匹配信息", get_match_server_api("/add_user"), json=to_raw_type(req), disable_retry=True
            )

        @try_except(return_val_on_except="")
        def get_chronicle_user_id_from_server(user_id: str, qq: str) -> str:
            req = DnfChronicleMatchServerRequestUserRequest()
            req.request_user_id = user_id
            req.request_qq = qq

            raw_res = self.post(
                "请求获取一个编年史用户信息",
                get_match_server_api("/req_user"),
                json=to_raw_type(req),
                disable_retry=True,
            )
            res = DnfChronicleMatchServerCommonResponse()
            res.data = DnfChronicleMatchServerRequestUserResponse()
            res.auto_update_config(raw_res)

            increase_counter(ga_category="chronicle_auto_match", name="request_chronicle_user_id")
            increase_counter(ga_category="chronicle_request_user_id", name=res.data.user_id != "")

            return res.data.user_id

        # ------ 绑定搭档 ------
        def bind_user_partner(ctx: str, partner_user_id: str, isBind="1"):
            res = wegame_post(
                ctx,
                "bindUserPartner",
                pUserId=partner_user_id,
                isBind=isBind,
            )
            logger.info(color("bold_green") + f"{ctx} 结果为: {res}")

        # ------ 检查是否绑定QQ ------
        @try_except()
        def check_bind_qq():
            bind_info = query_bind_qq_info()
            if bind_info.is_need_transfer:
                logger.warning(f"{self.cfg.name} 本月的编年史尚未与当前QQ绑定，将尝试自动绑定")
                bind_ok = bind_qq()
                if not bind_ok:
                    extra_msg = "编年史未与QQ号进行绑定，且自动绑定流程失败了。请前往道聚城编年史页面手动进行绑定（进入后会见到形如 【账号确认 你是否将 XXX 作为本期参与编年活动的唯一账号 ... 】，使用正确的QQ登陆后，点击确认即可）"
                    self.show_dnf_helper_info_guide(
                        extra_msg, show_message_box_once_key=f"dnf_helper_chronicle_bind_qq_{get_month()}"
                    )

        def query_bind_qq_info() -> DnfHelperChronicleBindInfo:
            raw_res = yoyo_post(
                "查询助手与QQ绑定信息",
                "getcheatguardbinding",
                gameId=10014,
            )

            return DnfHelperChronicleBindInfo().auto_update_config(raw_res.get("data", {}))

        @try_except(return_val_on_except=False)
        def bind_qq() -> bool:
            current_qq = self.qq()
            raw_res = yoyo_post(
                f"{self.cfg.name} 将编年史与当前QQ({current_qq})绑定",
                "bindcheatguard",
                gameId=10014,
                bindUin=current_qq,
            )

            # {"result":0,"returnCode":0,"returnMsg":""}
            return raw_res.get("returnCode", -1) == 0

        # ------ 查询各种信息 ------
        def exchange_list() -> DnfHelperChronicleExchangeList:
            res = wang_get("可兑换道具列表", "list/exchange")
            return DnfHelperChronicleExchangeList().auto_update_config(res)

        def basic_award_list() -> DnfHelperChronicleBasicAwardList:
            res = wang_get("基础奖励与搭档奖励", "list/basic")
            return DnfHelperChronicleBasicAwardList().auto_update_config(res)

        def lottery_list() -> DnfHelperChronicleLotteryList:
            res = wang_get("碎片抽奖奖励", "lottery/receive")
            return DnfHelperChronicleLotteryList().auto_update_config(res)

        def getUserActivityTopInfo() -> DnfHelperChronicleUserActivityTopInfo:
            res = wegame_post("活动基础状态信息", "getUserActivityTopInfo")
            return DnfHelperChronicleUserActivityTopInfo().auto_update_config(res.get("data", {}))

        def _getUserTaskList() -> dict:
            result = wegame_post("任务信息", "getUserTaskList")
            return result

        def getUserTaskList() -> DnfHelperChronicleUserTaskList:
            res = _getUserTaskList()
            return DnfHelperChronicleUserTaskList().auto_update_config(res.get("data", {}))

        def sign_gifts_list() -> DnfHelperChronicleSignList:
            res = wang_get("连续签到奖励列表", "list/sign")
            return DnfHelperChronicleSignList().auto_update_config(res)

        # ------ 领取各种奖励 ------
        extra_msg = color("bold_green") + "很可能是编年史尚未正式开始，导致无法领取游戏内奖励~"

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def takeTaskAwards():
            taskInfo = getUserTaskList()

            # 如果未绑定搭档，且设置了固定搭档id，则先尝试自动绑定
            if not taskInfo.hasPartner:
                latest_task_info = try_auto_bind()
                if latest_task_info is not None:
                    taskInfo = latest_task_info

            # 根据是否有搭档，给予不同提示
            if taskInfo.hasPartner:
                logger.info(f"搭档为{taskInfo.pUserId}")
            else:
                logger.warning(
                    "目前尚无搭档，建议找一个，可以多领点东西-。-。\n"
                    "如果找到了固定的队友，推荐将其userid填写到配置工具中，这样以后每期都会自动绑定~\n"
                    "如果上期已经达到满级，且小助手的按月付费未过期，可尝试打开配置工具中当前账号的自动匹配编年史开关，将自动与其他符合该条件的小助手用户匹配到一起~\n"
                )

            logger.info("首先尝试完成接到身上的任务")
            normal_tasks = set()

            logger.info("先尝试领取自己的任务经验")
            for task in taskInfo.taskList:
                takeTaskAward_op("自己", task.name, task.mActionId, task.mStatus, task.mExp)
                normal_tasks.add(task.mActionId)

            logger.info(
                "然后尝试领取队友的任务经验（因为部分任务只有在自己的完成后，队友的才会显示为已完成状态，所以需要重新查询一次）"
            )
            taskInfo = getUserTaskList()
            for task in taskInfo.taskList:
                if taskInfo.hasPartner:
                    takeTaskAward_op("队友", task.name, task.pActionId, task.pStatus, task.pExp)
                    normal_tasks.add(task.pActionId)

            logger.info(
                "与心悦战场类似，即使未展示在接取列表内的任务，只要满足条件就可以领取奖励。因此接下来尝试领取其余任务(ps：这种情况下日志提示未完成也有可能是因为已经领取过~）"
            )
            logger.warning(
                "曾经可以尝试未接到身上的任务，好像现在不可以了-。-，日后可以再试试，暂时先不尝试了 @2022.4.14"
            )
            all_task: tuple[tuple[str, int, str, int, str]] = (  # type: ignore
                # ("001", 8, "013", 4, "DNF助手签到"),
                # ("002", 11, "014", 6, "浏览资讯详情页"),
                # ("003", 9, "015", 5, "浏览动态详情页"),
                # ("004", 11, "016", 6, "浏览视频详情页"),
                # ("005", 17, "017", 10, "登陆游戏"),
                # ("007", 15, "019", 8, "进入游戏30分钟"),
                # ("008", 17, "020", 10, "分享助手周报"),
                # ("011", 20, "023", 9, "进入游戏超过1小时"),
                # ("036", 7, "037", 7, "完成勇士知道活动"),
            )
            for mActionId, mExp, pActionId, pExp, name in all_task:
                if mActionId not in normal_tasks:
                    takeTaskAward_op("自己", name, mActionId, 0, mExp)
                if taskInfo.hasPartner and pActionId not in normal_tasks:
                    takeTaskAward_op("队友", name, pActionId, 0, pExp)

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def takeTaskAward_op(suffix, taskName, actionId, status, exp):
            actionName = f"[{taskName}-{suffix}]"

            if status in [0, 2]:
                # 0-未完成，2-已完成未领取，但是助手签到任务在未完成的时候可以直接领取，所以这俩一起处理，在内部根据回包进行区分
                doActionIncrExp(actionName, actionId, exp)
            else:
                # 1 表示已经领取过
                logger.info(f"{actionName}已经领取过了")

        def doActionIncrExp(actionName, actionId, exp):
            res = yoyo_post("领取任务经验", "doactionincrexp", gameId=1006, actionId=actionId)

            data = res.get("data", 0)
            if data != 0:
                logger.info(f"领取{actionName}-{actionId}，获取经验为{exp}，回包data={data}")
            else:
                logger.warning(f"{actionName}尚未完成，无法领取哦~")

            if dnf_helper_info.token != "":
                # "returnCode": -30003, "returnMsg": "登录态失效，请重新登录"
                show_message_box_once_key = "编年史token过期_" + get_week()
                if res.get("returnCode", 0) == -30003:
                    extra_msg = "dnf助手的登录态已过期，导致编年史相关操作无法执行，目前需要手动更新，具体操作流程如下"
                    self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key=show_message_box_once_key)
                else:
                    self.reset_show_dnf_helper_info_guide_key(show_message_box_once_key)

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def take_continuous_signin_gifts():
            signGiftsList = sign_gifts_list()
            hasTakenAnySignGift = False
            for signGift in signGiftsList.gifts:
                # 2-未完成，0-已完成未领取，1-已领取
                if signGift.status in [0]:
                    # 0-已完成未领取
                    take_continuous_signin_gift_op(signGift)
                    hasTakenAnySignGift = True
                else:
                    # 2-未完成，1-已领取
                    pass
            if not hasTakenAnySignGift:
                logger.info("连续签到均已领取")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def take_continuous_signin_gift_op(giftInfo: DnfHelperChronicleSignGiftInfo):
            res = wang_get(
                f"领取 {giftInfo.sDays} 签到奖励",
                "send/sign",
                amsid="",
                date_chronicle_sign_in=giftInfo.date,
                num=1,
            )
            logger.info(f"领取连续签到 {giftInfo.date} 的奖励: {res}")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def take_basic_awards():
            listOfBasicList = get_awards()
            not_taken_awards = get_not_taken_awards(listOfBasicList)

            take_all_not_taken_awards(not_taken_awards)

            if len(not_taken_awards) == 0:
                logger.info("目前没有新的可以领取的基础奖励，只能等升级咯~")
            elif dnf_helper_info.token == "":
                prompt_take_awards()

        def get_awards() -> list[tuple[bool, list[DnfHelperChronicleBasicAwardInfo]]]:
            listOfBasicList = []

            basicAwardList = basic_award_list()

            listOfBasicList.append((True, basicAwardList.basic1List))
            if basicAwardList.hasPartner:
                listOfBasicList.append((False, basicAwardList.basic2List))

            return listOfBasicList

        def get_not_taken_awards(
            listOfBasicList: list[tuple[bool, list[DnfHelperChronicleBasicAwardInfo]]]
        ) -> list[tuple[bool, DnfHelperChronicleBasicAwardInfo]]:
            not_taken_award_list = []

            for selfGift, basicList in listOfBasicList:
                for award in basicList:
                    if award.isLock == 0 and award.isUsed == 0:
                        # 已解锁，且未领取，则加入待领取列表
                        not_taken_award_list.append((selfGift, award))

            return not_taken_award_list

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def take_all_not_taken_awards(not_taken_awards: list[tuple[bool, DnfHelperChronicleBasicAwardInfo]]):
            for selfGift, award in not_taken_awards:
                take_basic_award_op(award, selfGift)

        def take_basic_award_op(awardInfo: DnfHelperChronicleBasicAwardInfo, selfGift=True):
            if selfGift:
                mold = 1  # 自己
                side = "自己"
            else:
                mold = 2  # 队友
                side = "队友"
            res = wang_get(
                "领取基础奖励",
                "send/basic",
                isLock=awardInfo.isLock,
                amsid=awardInfo.sLbCode,
                iLbSel1=awardInfo.iLbSel1,
                num=1,
                mold=mold,
            )
            logger.info(f"领取{side}的第{awardInfo.sName}个基础奖励: {awardInfo.giftName} - {res}")
            ret_msg = res.get("msg", "")
            if ret_msg == "登录态异常":
                msg = f"账号 {self.cfg.name} 的 dnf助手鉴权信息不对，将无法领取奖励。请将配置工具中dnf助手的四个参数全部填写。或者直接月末手动去dnf助手app上把等级奖励都领一遍，一分钟搞定-。-"
                async_message_box(msg, "助手鉴权失败", show_once=True)
                raise DnfHelperChronicleTokenExpiredOrWrongException()
            elif ret_msg == "查询角色失败":
                msg = f"账号 {self.cfg.name} 的 dnf助手app 绑定的角色与 道聚城app 绑定的角色不一样，会导致无法自动领取等级奖励，请将两个调整为一样的。"
                if is_daily_first_run(f"编年史查询角色失败_{self.cfg.name}"):
                    async_message_box(msg, "助手角色不一致")
            elif ret_msg == "角色绑定的账号错误":
                msg = f"账号 {self.cfg.name} 的 dnf编年史尚未初始化，请手动去助手app到编年史页面完成初始化操作（也就是 是否绑定 QQ XXX 为本期编年史的账号），点下确认即可"
                logger.warning(msg)

        def prompt_take_awards():
            # 如果有奖励，且未配置token，则在下列情况提醒手动领取
            # 1. 满级了
            # 2. 是本月最后一天
            info = getUserActivityTopInfo()
            _, end_date = start_and_end_date_of_a_month(get_now())
            last_day = get_today(end_date)

            if info.is_full_level() or get_today() == last_day:
                msg = f"{self.cfg.name} 的编年史等级已满级，或者今天已是本月最后一天，但其仍有未领取的等级奖励，且未配置token，所以无法自动领取，请自行去道聚城app将这个账号的等级奖励都领取掉~"
                async_message_box(msg, "提醒手动领取编年史奖励")

        @try_except(show_last_process_result=False, extra_msg="大概率是token不对或者过期了，导致无法领取等级奖励")
        def exchange_awards():
            exchangeList = exchange_list()

            # 本地保存一份，方便配置工具那边查询
            db = DnfHelperChronicleExchangeListDB().load()
            if len(exchangeList.gifts) != 0:
                db.exchange_list = exchangeList
            else:
                logger.warning("本次查询兑换列表失败，将使用之前保存的版本~")
                exchangeList = db.exchange_list
            db.save()

            exchangeGiftMap = {}
            for gift in exchangeList.gifts:
                exchangeGiftMap[gift.sLbcode] = gift

            logger.info(color("bold_green") + "本期可兑换道具如下:")
            heads = ["名称", "兑换id", "所需等级", "领取次数", "消耗年史碎片"]
            colSizes = [40, 8, 8, 8, 12]
            logger.info(color("bold_green") + tableify(heads, colSizes))
            for gift in exchangeList.gifts:
                row = [gift.sName, gift.sLbcode, gift.iLevel, gift.iNum, gift.iCard]
                logger.info(tableify(row, colSizes))

            if len(self.cfg.dnf_helper_info.chronicle_exchange_items) != 0:
                all_exchanged = True
                for ei in self.cfg.dnf_helper_info.chronicle_exchange_items:
                    if ei.sLbcode not in exchangeGiftMap:
                        logger.error(
                            f"未找到兑换项{ei.sLbcode}({ei.sName})对应的配置，请参考 {db.prepare_env_and_get_db_filepath()}"
                        )
                        continue

                    gift = exchangeGiftMap[ei.sLbcode]
                    if gift.usedNum >= int(gift.iNum):
                        logger.warning(f"{gift.sName}已经达到兑换上限{gift.iNum}次, 将跳过")
                        continue

                    userInfo = getUserActivityTopInfo()
                    if userInfo.level < int(gift.iLevel):
                        all_exchanged = False
                        logger.warning(
                            f"目前等级为{userInfo.level}，不够兑换{gift.sName}所需的{gift.iLevel}级，将跳过后续优先级较低的兑换奖励"
                        )
                        break
                    if userInfo.point < int(gift.iCard):
                        all_exchanged = False
                        logger.warning(
                            f"目前年史碎片数目为{userInfo.point}，不够兑换{gift.sName}所需的{gift.iCard}个，将跳过后续优先级较低的兑换奖励"
                        )
                        break

                    exchange_count = min(ei.count, userInfo.point // int(gift.iCard))
                    for idx in range_from_one(exchange_count):
                        exchange_award_op(f"[{idx}/{exchange_count}]", gift)

                if all_exchanged:
                    logger.info(
                        color("fg_bold_yellow")
                        + "似乎配置的兑换列表已到达兑换上限，建议开启抽奖功能，避免浪费年史碎片~"
                    )
            else:
                logger.info("未配置dnf助手编年史活动的兑换列表，若需要兑换，可前往配置文件进行调整")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def exchange_award_op(ctx: str, giftInfo: DnfHelperChronicleExchangeGiftInfo):
            res = wang_get(
                "兑换奖励",
                "send/exchange",
                exNum=1,
                iCard=giftInfo.iCard,
                amsid=giftInfo.sLbcode,
                iNum=giftInfo.iNum,
                isLock=giftInfo.isLock,
            )
            logger.info(f"{ctx}兑换奖励({giftInfo.sName}): {res}")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def lottery():
            if self.cfg.dnf_helper_info.chronicle_lottery:
                userInfo = getUserActivityTopInfo()
                totalLotteryTimes = userInfo.point // 10
                logger.info(f"当前共有{userInfo.point}年史诗片，将进行{totalLotteryTimes}次抽奖")
                for idx in range_from_one(totalLotteryTimes):
                    op_lottery(idx, totalLotteryTimes)
            else:
                logger.info(
                    "当前未启用抽奖功能，若奖励兑换完毕时，建议开启抽奖功能~（ps: 年史碎片可以保留到下个月，也可以留着兑换以后的东西）"
                )

        def op_lottery(idx: int, totalLotteryTimes: int):
            ctx = f"[{idx}/{totalLotteryTimes}]"
            res = wang_get(
                f"{ctx} 抽奖",
                "send/lottery",
                amsid="lottery_0007",
                iCard=10,
            )
            gift = res.get("giftName", "出错啦: " + res.get("msg", "未知错误"))
            beforeMoney = res.get("money", 0)
            afterMoney = res.get("value", 0)
            logger.info(f"{ctx} 抽奖结果为: {gift}，年史诗片：{beforeMoney}->{afterMoney}")

        # ------ 实际逻辑 ------

        # 检查一下userid是否真实存在
        if self.cfg.dnf_helper_info.userId == "" or len(_getUserTaskList().get("data", {})) == 0:
            extra_msg = f"dnf助手的userId未配置或配置有误或者本月没有编年史活动，当前值为[{self.cfg.dnf_helper_info.userId}]，无法进行dnf助手编年史活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key=f"dnf_helper_chronicle_{get_month()}")
            return

        # 检查领奖额外需要的参数
        if self.cfg.dnf_helper_info.token == "" or self.cfg.dnf_helper_info.uniqueRoleId == "":
            extra_msg = "dnf助手的token/uniqueRoleId未配置，将无法领取 【等级奖励】和【任务经验】（其他似乎不受影响）。若想要自动执行这些操作，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key=f"dnf_helper_chronicle_{get_month()}")
            # 不通过也继续走，只是领奖会失败而已
        else:
            # 在设置了必要参数的情况下，检查是否绑定QQ
            check_bind_qq()

        # 提示做任务
        msg = "dnf助手签到任务和浏览咨询详情页请使用auto.js等自动化工具来模拟打开助手去执行对应操作，当然也可以每天手动打开助手点一点-。-"
        if is_monthly_first_run("dnf_helper_chronicle_task_tips_month_monthly"):
            async_message_box(msg, "编年史任务提示")
        else:
            logger.warning(color("bold_cyan") + msg)

        # 领取任务奖励的经验
        takeTaskAwards()
        if take_task_award_only:
            return

        if not self.cfg.dnf_helper_info.disable_fetch_access_token:
            # note: 下面的流程需要一个额外参数，在这里再进行，避免影响后续流程
            try_fetch_xinyue_openid_access_token()

            # 领取连续签到奖励
            take_continuous_signin_gifts()

            # 领取基础奖励
            take_basic_awards()

            # 根据配置兑换奖励
            exchange_awards()

            # 抽奖
            lottery()
        else:
            async_message_box(
                (
                    "2022.7开始，编年史需要两个新的参数，恰好这两个参数可以通过心悦专区登录后来获取，因此稍后会尝试登录心悦专区\n"
                    "\n"
                    "如果你这个登录一直失败，可以去配置工具打开开关【账号配置/dnf助手/不尝试获取编年史新鉴权参数】，禁用掉这个功能\n"
                    "这样的话，在填写了token等参数的情况下，将仅尝试领取任务经验。而每次签到奖励、领取等级奖励、兑换奖励等功能，则因为没有这个新的参数，将无法执行~\n"
                ),
                "借用心悦来获取编年史所需的新鉴权参数_{self.cfg.name}",
                show_once=True,
            )

        # 展示进度信息
        def show_user_info(name: str, ui: DnfHelperChronicleUserActivityTopInfo):
            logger.warning(
                color("fg_bold_yellow")
                + f"账号 {name} 当前编年史等级为LV{ui.level}({ui.levelName}) 本级经验：{ui.currentExp}/{ui.levelExp} 当前总获取经验为{ui.totalExp} 剩余年史碎片为{ui.point}"
            )

        # 自己
        userInfo = getUserActivityTopInfo()
        show_user_info(self.cfg.name, userInfo)

        # 队友
        taskInfo = getUserTaskList()
        if taskInfo.hasPartner:
            partner_name = "你的搭档"
            if dnf_helper_info.pNickName != "":
                partner_name += f"({dnf_helper_info.pNickName})"
            elif dnf_helper_info.enable_auto_match_dnf_chronicle:
                partner_name += "(自动匹配)"
            show_user_info(partner_name, self.query_dnf_helper_chronicle_info(taskInfo.pUserId))

        # 更新本月的进度信息
        # 编年史的自动组队的时候，可以根据保存的上个月的这个信息去决定是否有资格参与自动组队 @2021-11-01 10:40:51
        user_info_db = (
            DnfHelperChronicleUserActivityTopInfoDB().with_context(self.get_dnf_helper_chronicle_db_key()).load()
        )
        user_info_db.account_name = self.cfg.name
        user_info_db.year_month_to_user_info[get_month()] = userInfo
        user_info_db.save()

        # 上报下编年史等级，看看等级分布，方便日后添加自动组队的时候，确认下用30级作为门槛能符合条件的人数与比例
        increase_counter(ga_category="chronicle_level", name=userInfo.level)

    @try_except(show_exception_info=False, return_val_on_except=DnfHelperChronicleUserActivityTopInfo())
    def query_dnf_helper_chronicle_info(self, userId="") -> DnfHelperChronicleUserActivityTopInfo:
        url_mwegame = self.urls.dnf_helper_chronicle_mwegame
        dnf_helper_info = self.cfg.dnf_helper_info
        roleinfo = self.get_dnf_bind_role()
        partition = roleinfo.serviceID
        roleid = roleinfo.roleCode

        if userId == "":
            userId = dnf_helper_info.userId

        common_params = {
            "userId": userId,
            "sPartition": partition,
            "sRoleId": roleid,
            "print_res": False,
        }
        res = self.post("活动基础状态信息", url_mwegame, "", api="getUserActivityTopInfo", **common_params)
        return DnfHelperChronicleUserActivityTopInfo().auto_update_config(res.get("data", {}))

    @try_except(show_exception_info=False, return_val_on_except=DnfHelperChronicleUserTaskList())
    def query_dnf_helper_chronicle_user_task_list(self) -> DnfHelperChronicleUserTaskList:
        url_mwegame = self.urls.dnf_helper_chronicle_mwegame
        dnf_helper_info = self.cfg.dnf_helper_info
        roleinfo = self.get_dnf_bind_role()
        partition = roleinfo.serviceID
        roleid = roleinfo.roleCode

        common_params = {
            "userId": dnf_helper_info.userId,
            "sPartition": partition,
            "sRoleId": roleid,
            "print_res": False,
        }
        res = self.post("任务信息", url_mwegame, "", api="getUserTaskList", **common_params)  # type: ignore
        return DnfHelperChronicleUserTaskList().auto_update_config(res.get("data", {}))

    @try_except(return_val_on_except=False)
    def check_dnf_helper_chronicle_auto_match(self, user_buy_info: BuyInfo, print_waring=True) -> bool:
        # 在按月付费期间
        if not user_buy_info.is_active(bypass_run_from_src=False):
            if print_waring:
                logger.warning(f"{self.cfg.name} 未付费，将不会尝试自动匹配心悦队伍")
            return False

        # 开启了本开关
        if not self.cfg.dnf_helper_info.enable_auto_match_dnf_chronicle:
            if print_waring:
                logger.info(f"{self.cfg.name} 未启用自动匹配编年史开关")
            return False

        # 上个月达到30级（根据本地上个月的记录）
        user_info_db = (
            DnfHelperChronicleUserActivityTopInfoDB().with_context(self.get_dnf_helper_chronicle_db_key()).load()
        )
        last_month_info = user_info_db.get_last_month_user_info()
        if not last_month_info.is_full_level():
            if print_waring:
                logger.info(f"{self.cfg.name} 上个月编年史等级未满级，等级为 {last_month_info.level}")
            return False

        return True

    def get_dnf_helper_chronicle_db_key(self):
        return f"编年史进度-{self.qq()}"

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

    # --------------------------------------------DNF格斗大赛--------------------------------------------
    @try_except()
    def dnf_pk(self):
        show_head_line("DNF格斗大赛功能")
        self.show_amesvr_act_info(self.dnf_pk_op)

        if not self.cfg.function_switches.get_dnf_pk or self.disable_most_activities():
            logger.warning("未启用DNF格斗大赛功能，将跳过")
            return

        self.check_dnf_pk()

        def query_ticket_count():
            res = self.dnf_pk_op("查询数据", "852125", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue1)

        self.dnf_pk_op("每日在线30分钟（977156）", "852098")
        self.dnf_pk_op("每日PK（977162）", "852102")
        self.dnf_pk_op("回流（977167）", "852107")

        ticket = query_ticket_count()
        logger.info(color("bold_cyan") + f"当前剩余抽奖券数目为：{ticket}")
        for idx in range_from_one(ticket):
            self.dnf_pk_op(f"[{idx}/{ticket}]幸运夺宝", "852109")
            if idx != ticket:
                time.sleep(5)

        # self.dnf_pk_op("海选普发奖励（977173）", "852113")
        # self.dnf_pk_op("周赛晋级奖励（977176）", "852115")
        # self.dnf_pk_op("决赛普发奖励（977180）", "852123")
        # self.dnf_pk_op("决赛冠军奖励（977181）", "852124")

    def check_dnf_pk(self):
        self.check_bind_account(
            "DNF格斗大赛",
            get_act_url("DNF格斗大赛"),
            activity_op_func=self.dnf_pk_op,
            query_bind_flowid="852085",
            commit_bind_flowid="852084",
        )

    def dnf_pk_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_pk

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            "http://dnf.qq.com/cp/a20210405pk/",
            **extra_params,
        )

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

    # --------------------------------------------DNF心悦--------------------------------------------
    @try_except()
    def dnf_xinyue(self):
        show_head_line("DNF心悦")
        self.show_amesvr_act_info(self.dnf_xinyue_op)

        if not self.cfg.function_switches.get_dnf_xinyue or self.disable_most_activities():
            logger.warning("未启用领取DNF心悦活动合集功能，将跳过")
            return

        self.check_dnf_xinyue()

        def jfAction(str_info, num):
            str_arr = str_info.split("|")[1:-1]

            result_list = []

            for part in str_arr:
                result_list.append(part.strip().split(" ")[num])

            return result_list

        def query_info() -> tuple[int, int, int]:
            res = self.dnf_xinyue_op("输出数据", "952002", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            xy_type = int(raw_info.sOutValue1)

            temp_list = jfAction(raw_info.sOutValue2, 2)
            total_step = int(temp_list[0])  # 总的步数
            cj_ticket = int(temp_list[1])  # 抽奖券

            return xy_type, total_step, cj_ticket

        async_message_box(
            "请手动前往 DPL职业联赛 活动页面进行报名PVP和PVE，可领取几个一次性的蚊子腿~。如果后续实际要参与鼻塞，对应周的排行奖励请自行领取",
            "DPL职业联赛 报名",
            open_url=get_act_url("DNF心悦"),
            show_once=True,
        )
        # self.dnf_xinyue_op("报名礼包PVE", "964191")
        # self.dnf_xinyue_op("报名礼包PVP", "964209")
        self.dnf_xinyue_op("回流礼", "964201")
        self.dnf_xinyue_op("心悦专属礼", "964206")

        # self.dnf_xinyue_op("排行第1周", "964788")
        # self.dnf_xinyue_op("排行第2周", "966444")
        # self.dnf_xinyue_op("排行第3周", "966445")
        # self.dnf_xinyue_op("排行第4周", "966446")
        # self.dnf_xinyue_op("PVE排名奖励S", "966896")
        # self.dnf_xinyue_op("PVE排名奖励A", "966910")
        # self.dnf_xinyue_op("PVE排名奖励B", "966911")

        # self.dnf_xinyue_op("通关领取", "964218")
        # self.dnf_xinyue_op("全图鉴达成B级", "964219")
        # self.dnf_xinyue_op("全图鉴达成A级", "964778")
        # self.dnf_xinyue_op("全图鉴达成S级", "964780")
        # self.dnf_xinyue_op("达成10个A级图鉴", "964781")
        # self.dnf_xinyue_op("达成8个S级图鉴", "964782")

        self.dnf_xinyue_op("参与一次怪物乱斗", "964198")
        self.dnf_xinyue_op("登录心悦俱乐部App", "964202")
        self.dnf_xinyue_op("消耗30点疲劳", "964203")
        self.dnf_xinyue_op("加入游戏家俱乐部", "964204")

        max_try = 4
        for idx in range_from_one(max_try):
            res = self.dnf_xinyue_op(f"{idx}/{max_try} 抽奖", "964196")
            if res["ret"] == "700":
                break
            time.sleep(5)

    def check_dnf_xinyue(self):
        # re: 部分心悦活动，如DPL职业联赛报名后就不能修改绑定角色了，所以这里设定在已有绑定且与道聚城不一致的情况下，则不尝试修改绑定
        act_can_change_bind = False

        self.check_bind_account(
            "DNF心悦",
            get_act_url("DNF心悦"),
            activity_op_func=self.dnf_xinyue_op,
            query_bind_flowid="964189",
            commit_bind_flowid="964188",
            act_can_change_bind=act_can_change_bind,
        )

    def dnf_xinyue_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_xinyue

        return self.amesvr_request(
            ctx,
            "act.game.qq.com",
            "xinyue",
            "tgclub",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF心悦"),
            **extra_params,
        )

    # --------------------------------------------DNF心悦Dup--------------------------------------------
    @try_except()
    def dnf_xinyue_dup(self):
        show_head_line("DNF心悦Dup")
        self.show_amesvr_act_info(self.dnf_xinyue_dup_op)

        if not self.cfg.function_switches.get_dnf_xinyue or self.disable_most_activities():
            logger.warning("未启用领取DNF心悦Dup活动合集功能，将跳过")
            return

        self.check_dnf_xinyue_dup()

        def query_info() -> tuple[int, int, int, bool]:
            res = self.dnf_xinyue_dup_op("输出数据", "952766", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            lottery_ticket = int(raw_info.sOutValue3)

            has_team = int(raw_info.sOutValue4) != 0

            qdweek = raw_info.sOutValue5.split("|")
            normal_sign_days = int(qdweek[0])
            lucky_sign_days = int(qdweek[1])

            return lottery_ticket, normal_sign_days, lucky_sign_days, has_team

        _, normal_sign_days, lucky_sign_days, has_team = query_info()
        if not has_team:
            async_message_box(
                "心悦俱乐部签到活动需要组队进行，请创建队伍或加入其他人的队伍。也可以按照稍后弹出的在线文档中的指引，与其他使用小助手的朋友进行组队~",
                "23.6 心悦签到组队提醒",
                show_once=True,
                open_url="https://docs.qq.com/sheet/DYlNmcVhHQ2VXalhj?tab=BB08J2",
            )
        else:
            self.dnf_xinyue_dup_op(f"7天签到 - {normal_sign_days}", "952789", today=normal_sign_days)
            self.dnf_xinyue_dup_op(f"7天签到buff奖励 - {lucky_sign_days}", "952790", today=lucky_sign_days)

        self.dnf_xinyue_dup_op("回流礼", "952777")
        self.dnf_xinyue_dup_op("当日消耗疲劳值30", "953312")
        self.dnf_xinyue_dup_op("当日充值6元", "953326")

        self.dnf_xinyue_dup_op("登录DNF客户端", "952774")
        self.dnf_xinyue_dup_op("消耗30点疲劳", "952779")
        self.dnf_xinyue_dup_op("加入游戏家俱乐部", "952780")

        lottery_ticket, _, _, _ = query_info()
        logger.info(color("bold_cyan") + f"当前抽奖次数为 {lottery_ticket}")
        for idx in range_from_one(lottery_ticket):
            self.dnf_xinyue_dup_op(f"{idx}/{lottery_ticket} 抽奖", "952772")
            time.sleep(5)

    def check_dnf_xinyue_dup(self):
        self.check_bind_account(
            "DNF心悦Dup",
            get_act_url("DNF心悦Dup"),
            activity_op_func=self.dnf_xinyue_dup_op,
            query_bind_flowid="952765",
            commit_bind_flowid="952764",
        )

    def dnf_xinyue_dup_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_xinyue_dup

        return self.amesvr_request(
            ctx,
            "act.game.qq.com",
            "xinyue",
            "tgclub",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF心悦Dup"),
            **extra_params,
        )

    # --------------------------------------------微信签到--------------------------------------------
    def wx_checkin(self):
        # 目前通过autojs实现
        return

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

    # --------------------------------------------DNF福利中心兑换--------------------------------------------
    @try_except()
    def dnf_welfare(self):
        show_head_line("DNF福利中心兑换")
        self.show_amesvr_act_info(self.dnf_welfare_op)

        if not self.cfg.function_switches.get_dnf_welfare or self.disable_most_activities():
            logger.warning("未启用领取DNF福利中心兑换活动功能，将跳过")
            return

        self.check_dnf_welfare()

        # note: 这里面的奖励都需要先登陆过游戏才可以领取

        # note: 新版本一定要记得刷新这个版本号~（不刷似乎也行- -）
        welfare_version = "v8"
        db = WelfareDB().with_context(welfare_version).load()
        account_db = WelfareDB().with_context(f"{welfare_version}/{self.cfg.get_account_cache_key()}").load()

        def exchange_package(sContent: str):
            # 检查是否已经兑换过
            if sContent in account_db.exchanged_dict:
                logger.warning(f"已经兑换过【{sContent}】，不再尝试兑换")
                return

            reg = "^[0-9]+-[0-9A-Za-z]{18}$"
            if re.fullmatch(reg, sContent) is not None:
                siActivityId, sContent = sContent.split("-")
                res = self.dnf_welfare_op(
                    f"兑换分享口令-{siActivityId}-{sContent}",
                    "649260",
                    siActivityId=siActivityId,
                    sContent=quote_plus(quote_plus(quote_plus(sContent))),
                )
            else:
                res = self.dnf_welfare_op(
                    f"兑换口令-{sContent}", "558229", sContent=quote_plus(quote_plus(quote_plus(sContent)))
                )

            # 每次请求间隔一秒
            time.sleep(3)

            if int(res["ret"]) != 0 or int(res["modRet"]["iRet"]) != 0:
                return

            # 本地标记已经兑换过
            def callback(val: WelfareDB):
                val.exchanged_dict[sContent] = True

            account_db.update(callback)

            try:
                shareCode = res["modRet"]["jData"]["shareCode"]
                if shareCode != "":

                    def callback(val: WelfareDB):
                        if shareCode not in val.share_code_list:
                            val.share_code_list.append(shareCode)

                    db.update(callback)
            except Exception:
                pass

        @try_except(return_val_on_except="19", show_exception_info=False)
        def query_siActivityId():
            res = self.dnf_welfare_op("查询我的分享码状态", "649261", print_res=False)
            return res["modRet"]["jData"]["siActivityId"]

        # 正式逻辑
        shareCodeList = db.share_code_list

        sContents = [
            "万物有灵守护不息",
            "DNF16周年生日快乐",
            "冲云破雾一路横扫",
            "6月13日登录领好礼",
        ]
        random.shuffle(sContents)
        sContents = [*shareCodeList, *sContents]
        for sContent in sContents:
            exchange_package(sContent)

        # # 分享礼包
        # self.dnf_welfare_op("分享奖励领取", "863948", siActivityId=query_siActivityId())

        # # 登陆游戏领福利
        # self.dnf_welfare_login_gifts_op("1月20 - 22日登录礼包", "831262")
        # self.dnf_welfare_login_gifts_op("1月23 - 26日登录礼包", "831263")
        # self.dnf_welfare_login_gifts_op("1月27日 - 2月2日登录礼包", "831264")
        #
        # # 分享礼包
        # self.dnf_welfare_login_gifts_op("分享奖励领取", "831272", siActivityId=query_siActivityId())

    def check_dnf_welfare(self):
        self.check_bind_account(
            "DNF福利中心兑换",
            get_act_url("DNF福利中心兑换"),
            activity_op_func=self.dnf_welfare_op,
            query_bind_flowid="558227",
            commit_bind_flowid="558226",
        )

    def dnf_welfare_op(self, ctx, iFlowId, siActivityId="", sContent="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_welfare

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF福利中心兑换"),
            siActivityId=siActivityId,
            sContent=sContent,
            **extra_params,
        )

    def dnf_welfare_login_gifts_op(self, ctx, iFlowId, siActivityId="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_welfare_login_gifts

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
            get_act_url("DNF福利中心兑换"),
            sArea=roleinfo.serviceID,
            sPartition=roleinfo.serviceID,
            sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
            sRoleId=roleinfo.roleCode,
            sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
            md5str=checkInfo.md5str,
            ams_checkparam=checkparam,
            checkparam=checkparam,
            siActivityId=siActivityId,
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

    # --------------------------------------------DNF马杰洛的规划--------------------------------------------
    # re: 变更时需要调整这些
    # note: 查询马杰洛信息的id [查询引导石数量和资格消耗] [初始化]
    flowid_majieluo_query_info = "222972"
    # note: 马杰洛过期时间，最近的活动查询到的信息里都不会给出，需要自己填入，在 urls.py 的 not_ams_activities 中填写起止时间

    @try_except()
    def majieluo(self):
        show_head_line("DNF马杰洛的规划")
        self.show_not_ams_act_info("DNF马杰洛的规划")

        if not self.cfg.function_switches.get_majieluo or self.disable_most_activities():
            logger.warning("未启用领取DNF马杰洛的规划活动功能，将跳过")
            return

        # re: 根据本次检查绑定具体使用的活动体系决定使用哪个函数
        check_func = self.check_majieluo
        # check_func = self.check_majieluo_amesvr

        check_func()

        def query_info() -> MaJieLuoInfo:
            raw_res = self.majieluo_op("查询信息", self.flowid_majieluo_query_info, print_res=False)

            return MaJieLuoInfo().auto_update_config(raw_res["jData"])

        self.majieluo_op("领取次元见面礼", "248079")

        self.majieluo_op("领取抽奖机会礼包", "248082")
        self.majieluo_op("幸运抽奖", "248353")

        # self.majieluo_op("领取邀请好友礼包", "248359", inviteNum=1)

        for day in [1, 3, 5, 7]:
            self.majieluo_op(f"流失用户领取登录游戏礼包-{day}", "248360", loginDays=day)
            time.sleep(5)

        # request_wait_time = 3
        #
        # self.majieluo_op("次元任务-进入活动页", "222974")
        # self.majieluo_op("次元任务-游戏在线30分钟", "224200")
        # self.majieluo_op("次元任务-每日登录", "224392")
        # self.majieluo_op("次元任务-每日通关4次推荐地下城", "224415")
        #
        # self.majieluo_op("次元任务-每周通关噩梦回廊地下城一次", "224475")
        # self.majieluo_op("次元任务-每周通关次元回廊地下城一次", "224613")
        # self.majieluo_op("次元任务-每周通关巴卡尔攻坚战一次", "224645")
        #
        # info = query_info()
        #
        # if len(info.itemInfo) <= 1:
        #     async_message_box(
        #         "卡牌次元活动中部分内容需要组队进行，请创建队伍或加入其他人的队伍。(PS：与之前几次一样，几乎需要队伍成员全部满勤才能领到最高的奖励，所以自行决定是否需要折腾~)",
        #         "23.9 卡牌次元组队提醒",
        #         show_once=True,
        #     )
        #
        # self.majieluo_op("领取反击卡达标15奖励", "225050")
        # self.majieluo_op("领取反击卡达标30奖励", "225102")
        # self.majieluo_op("领取反击卡达标40奖励", "225103")
        # self.majieluo_op("领取反击卡达标50奖励", "225104")
        #
        # lottery_times = int(info.luckCard) // 3
        # logger.info(f"当前的幸运卡牌数目为 {info.luckCard}，可以抽奖 {lottery_times} 次")
        # for idx in range_from_one(lottery_times):
        #     self.majieluo_op(f"[{idx}/{lottery_times}] 抽奖", "224651")
        #     time.sleep(request_wait_time)

        # # 马杰洛的见面礼
        # def take_gift(take_lottery_count_role_info: RoleInfo) -> bool:
        #     self.majieluo_op("领取见面礼", "163667")
        #     return True
        #
        # logger.info(f"当前马杰洛尝试使用回归角色领取见面礼的开关状态为：{self.cfg.enable_majieluo_lucky}")
        # if self.cfg.enable_majieluo_lucky:
        #     self.try_do_with_lucky_role_and_normal_role("领取马杰洛见面礼", check_func, take_gift)
        # else:
        #     take_gift(self.get_dnf_bind_role_copy())
        #
        # # 马杰洛的特殊任务
        # # self.majieluo_op("选择阵营", "141618", iType=2)
        #
        # tasks = [
        #     ("每日登录礼包", "163691"),
        #     ("每日通关礼包", "163706"),
        #     ("每日在线礼包", "163713"),
        #     ("每日邀请礼包", "163717"),
        #     ("特殊任务-登录游戏15次", "163718"),
        #     ("特殊任务-史诗之路50装备", "163719"),
        #     ("特殊任务-邀请10位好友", "163728"),
        #     ("特殊任务-邀请2位幸运好友登录", "163729"),
        # ]
        # for name, flowid in tasks:
        #     self.majieluo_op(name, flowid)
        #     time.sleep(5)
        #
        # # # 抽奖
        # # info = query_info()
        # # lottery_times = int(info.iDraw)
        # # logger.info(color("bold_cyan") + f"当前抽奖次数为 {lottery_times}")
        # # for idx in range_from_one(lottery_times):
        # #     self.majieluo_op(f"{idx}/{lottery_times} 幸运抽奖", "141617")
        #
        # # 赠送礼盒
        # self.majieluo_permit_social()
        #
        # # self.majieluo_send_to_xiaohao([openid])
        #
        # # invite_uins = self.common_cfg.majieluo_invite_uin_list
        # # if len(invite_uins) != 0:
        # #     # 假设第一个填写的QQ是主QQ，尝试每个号都先领取这个，其余的则是小号，随机顺序，确保其他qq有同等机会
        # #     main_qq, others = invite_uins[0], invite_uins[1:]
        # #     random.shuffle(others)
        # #     invite_uins = [main_qq, *others]
        # #     for uin in invite_uins:
        # #         self.majieluo_open_box(uin)
        # # else:
        # #     logger.warning(f"当前未配置接收赠送礼盒的inviteUin，将不会尝试接收礼盒。如需开启，请按照配置工具中-其他-马杰洛赠送uin列表的字段说明进行配置")
        #
        # async_message_box(
        #     (
        #         "本期马杰洛的深渊礼盒不能绑定固定人，所以请自行完成赠送宝箱的流程~"
        #         # # note: 当uin是qq的时候才显示下面这个，如果是哈希值或加密后的，则放弃显示
        #         # "(可以选择配置工具中的马杰洛小助手减少操作量)"
        #         "(如果单个好友活动期间只能操作一次，那就只能找若干个人慢慢做了-。-)"
        #     ),
        #     f"马杰洛赠送提示_{get_act_url('DNF马杰洛的规划')}",
        #     show_once=True,
        # )
        # logger.info(color("bold_green") + f"当前已累计赠送{self.query_invite_count()}次")
        #
        # # self.majieluo_op("累计赠送30次礼包", "113887")
        # # self.majieluo_op("冲顶25", "138766")
        # # self.majieluo_op("冲顶40", "138767")
        # # self.majieluo_op("冲顶65", "138768")
        # # self.majieluo_op("冲顶75", "138769")
        #
        # # 提取得福利
        # stoneCount = self.query_stone_count()
        # logger.warning(color("bold_yellow") + f"当前共有{stoneCount}个引导石")
        #
        # act_info = self.majieluo_op("获取活动信息", "", get_act_info_only=True)
        # sDownDate = act_info.dev.action.sDownDate
        # if sDownDate == not_know_end_time____:
        #     sDownDate = get_not_ams_act("DNF马杰洛的规划").dtEndTime
        # endTime = get_today(parse_time(sDownDate))
        #
        # if get_today() == endTime:
        #     # # 最后一天再领取仅可领取单次的奖励
        #     # self.majieluo_op("晶体礼包", "131561")
        #
        #     act_url = get_act_url("DNF马杰洛的规划")
        #     async_message_box(
        #         "本次马杰洛奖励是兑换或者抽奖，所以本次不会自动兑换。今天已是活动最后一天，请自行到活动页面去兑换想要的奖励，或者抽奖",
        #         f"手动兑换通知-{act_url}",
        #         open_url=act_url,
        #     )
        #     # self.majieluo_op("幸运抽奖", "134228")
        #     #
        #     # self.majieluo_op("兑换纯净的增幅书1次", "138754")
        #     # self.majieluo_op("兑换黑钻1次", "138755")
        #     # self.majieluo_op("兑换一次性继承装置2次", "138756")
        #     # self.majieluo_op("兑换装备提升礼盒1次", "138757")
        #     # self.majieluo_op("兑换复活币礼盒8次", "138758")
        #     # self.majieluo_op("兑换黑钻3天3次", "138759")
        # else:
        #     logger.warning(f"当前不是活动最后一天({endTime})，将不会尝试领取 最终大奖")
        #
        # # takeStone = False
        # # takeStoneFlowId = "113898"
        # # maxStoneCount = 1500
        # # if stoneCount >= maxStoneCount:
        # #     # 达到上限
        # #     self.majieluo_op("提取时间引导石", takeStoneFlowId, giftNum=str(maxStoneCount // 100))
        # #     takeStone = True
        # # elif get_today() == endTime:
        # #     # 今天是活动最后一天
        # #     self.majieluo_op("提取时间引导石", takeStoneFlowId, giftNum=str(stoneCount // 100))
        # #     takeStone = True
        # # else:
        # #     logger.info(f"当前未到最后领取期限（活动结束时-{endTime} 23:59:59），且石头数目({stoneCount})不足{maxStoneCount}，故不尝试提取")
        #
        # # if takeStone:
        # #     self.majieluo_op("提取引导石大于1000礼包", "113902")
        # #     # self.majieluo_op("分享得好礼", "769008")

    def majieluo_permit_social(self):
        self.dnf_social_relation_permission_op(
            "更新创建用户授权信息", "108939", sAuthInfo="MJL", sActivityInfo="a20220811searching"
        )
        return

    @try_except()
    def majieluo_send_to_xiaohao(self, xiaohao_qq_list: list[str]) -> list[str]:
        p_skey = self.fetch_share_p_skey("马杰洛赠送好友")

        self.majieluo_permit_social()

        results = []
        iType = 0  # 0 赠送 1 索要
        for openid in xiaohao_qq_list:
            res = self.majieluo_op(
                f"赠送单个用户（发送好友ark消息）-{openid}", "141620", openid=openid, iType=iType, p_skey=p_skey
            )
            if int(res["iRet"]) == 0:
                results.append("赠送成功")
            else:
                results.append(res["flowRet"]["sMsg"])

        return results

    @try_except()
    def majieluo_open_box(self, scode: str) -> tuple[int, str]:
        self.majieluo_permit_social()

        raw_res = self.majieluo_op(f"接受好友赠送礼盒 - {scode}", "138734", sCode=scode)
        return raw_res["iRet"], raw_res["sMsg"]

    @try_except(return_val_on_except=0, show_exception_info=False)
    def query_invite_count(self) -> int:
        res = self.majieluo_op("查询邀请数目", self.flowid_majieluo_query_info, print_res=False)

        return len(res["jData"]["iSend"])

    @try_except(return_val_on_except=0, show_exception_info=False)
    def query_stone_count(self):
        res = self.majieluo_op("查询当前时间引导石数量", "156956", print_res=False)

        return int(res["jData"]["iExp"])

    def check_majieluo(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF马杰洛的规划",
            get_act_url("DNF马杰洛的规划"),
            activity_op_func=self.majieluo_op,
            sAuthInfo="MJL",
            sActivityInfo="MJL13",
            **extra_params,
        )

    def majieluo_op(
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
        iActivityId = self.urls.ide_iActivityId_majieluo

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF马杰洛的规划"),
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

    def check_majieluo_amesvr(self, **extra_params):
        """有时候马杰洛活动可能绑定走amesvr系统，活动内容走ide，这里做下特殊处理"""
        self.check_bind_account(
            "DNF马杰洛的规划",
            get_act_url("DNF马杰洛的规划"),
            activity_op_func=self.majieluo_amesvr_op,
            query_bind_flowid="952130",
            commit_bind_flowid="952129",
            **extra_params,
        )

    def majieluo_amesvr_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_majieluo

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF马杰洛的规划"),
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

    # --------------------------------------------新版活动统一社交权限接口--------------------------------------------

    def dnf_social_relation_permission_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_social_relation_permission

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            "",
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

    # --------------------------------------------dnf论坛签到--------------------------------------------
    # note: 相关说明
    #   可能同时存在多个版本的兑换活动，将分别在 v1/v2 中去实现，有新的活动时，用这两个中未使用的那个来实现。若同时存在三个，则添加v3即可
    #
    # re:
    #  新增流程
    #   1. 从 v1/v2/... 中找到一个未使用的（check 或者 op 函数直接返回None），去除开头的 return
    #   2. 将新活动的相关信息填入op和check函数中，再修改查询奖励和兑换奖励的部分，并调整相对顺序即可
    #   3. 修改 dnf_bbs_op 函数，将其指向最新的版本的op函数，并修改查询代币券的flowid，改为最新版本中的flowid
    #  删除流程
    #   1. 将过期活动的check和op直接返回即可
    @try_except()
    def dnf_bbs(self):
        # https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign
        show_head_line("dnf官方论坛签到")
        self.show_amesvr_act_info(self.dnf_bbs_op)

        if not self.cfg.function_switches.get_dnf_bbs_signin or self.disable_most_activities():
            logger.warning("未启用领取dnf官方论坛签到活动合集功能，将跳过")
            return

        if self.cfg.dnf_bbs_cookie == "":
            logger.warning(
                "未配置dnf官方论坛的cookie，将跳过（dnf官方论坛相关的配置会配置就配置，不会就不要配置，我不会回答关于这俩如何获取的问题）"
            )
            return

        # self.check_dnf_bbs_v1()
        #
        # self.check_dnf_bbs_v2()

        def query_formhash() -> str:
            if self.cfg.dnf_bbs_cookie == "":
                return ""

            # note: 鉴于兑换活动会存在真空期，改用解析个人中心的方式来获取论坛代币数目
            url = self.urls.dnf_bbs_home
            headers = {
                "cookie": self.cfg.dnf_bbs_cookie,
            }

            res = requests.get(url, headers=headers, timeout=10)
            html_text = res.text

            # <a class="logout" href="member.php?mod=logging&amp;action=logout&amp;formhash=02d1xxxx">退出登陆</a>
            prefix = "formhash="
            suffix = '">退出登陆</a>'
            if prefix not in html_text:
                logger.warning("未能定位到论坛formhash")
                return ""

            prefix_idx = html_text.index(prefix) + len(prefix)
            suffix_idx = html_text.index(suffix, prefix_idx)

            formhash = html_text[prefix_idx:suffix_idx]

            return formhash

        def signin():
            retryCfg = self.common_cfg.retry
            for idx in range(retryCfg.max_retry_count):
                try:
                    formhash = query_formhash()
                    logger.info(f"查询到的formhash为: {formhash}")

                    url = self.urls.dnf_bbs_signin.format(formhash=formhash)
                    headers = {
                        "cookie": self.cfg.dnf_bbs_cookie,
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                        "accept-encoding": "gzip, deflate, br",
                        "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,en-GB;q=0.6,ja;q=0.5",
                        "cache-control": "max-age=0",
                        "content-type": "application/x-www-form-urlencoded",
                        "dnt": "1",
                        "origin": "https://dnf.gamebbs.qq.com",
                        "referer": "https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign",
                        "sec-ch-ua": '"Google Chrome";v="87", " Not;A Brand";v="99", "Chromium";v="87"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-fetch-dest": "document",
                        "sec-fetch-mode": "navigate",
                        "sec-fetch-site": "same-origin",
                        "sec-fetch-user": "?1",
                        "upgrade-insecure-requests": "1",
                        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
                    }

                    res = requests.post(url, headers=headers, timeout=10)
                    html_text = res.text

                    prefixes = [
                        '<div id="messagetext" class="alert_right">\n<p>',
                        '<div id="messagetext" class="alert_info">\n<p>',
                    ]
                    suffix = "</p>"
                    for prefix in prefixes:
                        if prefix in html_text:
                            prefix_idx = html_text.index(prefix) + len(prefix)
                            suffix_idx = html_text.index(suffix, prefix_idx)
                            logger.info(f"论坛签到OK: {html_text[prefix_idx:suffix_idx]}")
                            return

                    logger.warning(
                        color("bold_yellow")
                        + "不知道为啥没有这个前缀，请去日志文件查看具体请求返回的结果是啥。将等待一会，然后重试"
                    )
                    logger.debug(f"不在预期内的签到返回内容如下：\n{html_text}")

                    async_message_box(
                        f"{self.cfg.name} 的 官方论坛cookie似乎过期了，记得更新最新的cookie~（可参照config.example.toml中这个字段的注释操作，打开后搜索 dnf_bbs_cookie）。如果不想继续签到了，可以不填论坛的cookie，就不会继续弹窗提示了",
                        "cookie似乎过期",
                    )

                    time.sleep(retryCfg.retry_wait_time)
                except Exception as e:
                    logger.exception(f"第{idx + 1}次尝试论坛签到失败了，等待一会", exc_info=e)
                    time.sleep(retryCfg.retry_wait_time)

        # 可能有多个活动并行
        # https://dnf.qq.com/act/a20210803act/index.html
        # https://dnf.qq.com/cp/a20211130act/index.html
        @try_except()
        def query_remaining_quota():
            # _query_quota_version_one(
            #     "9-12月",
            #     self.dnf_bbs_op_v2,
            #     "788271",
            #     [
            #         "一次性材质转换器",
            #         "一次性继承装置",
            #         "华丽的徽章神秘礼盒",
            #         "装备提升礼盒",
            #         "华丽的徽章自选礼盒",
            #         "抗疲劳秘药 (30点)",
            #         "Lv100传说装备自选礼盒",
            #         "异界气息净化书",
            #         "灿烂的徽章神秘礼盒",
            #         "灿烂的徽章自选礼盒",
            #     ],
            # )
            #
            # _query_quota_version_one(
            #     "12-3月",
            #     self.dnf_bbs_op_v1,
            #     "821339",
            #     [
            #         "一次性材质转换器",
            #         "一次性继承装置",
            #         "装备提升礼盒",
            #         "灵魂武器袖珍罐",
            #         "华丽的徽章神秘礼盒",
            #         "华丽的徽章自选礼盒",
            #         "Lv100传说装备自选礼盒",
            #         "纯净的增幅书",
            #         "灿烂的徽章神秘礼盒",
            #         "灿烂的徽章自选礼盒",
            #     ],
            # )

            pass

        @try_except()
        def _query_quota_version_one(ctx: str, op_func: Callable[..., dict], flow_id: str, item_name_list: list[str]):
            res = op_func("查询礼包剩余量", flow_id, print_res=False)
            if res is None:
                return

            info = parse_amesvr_common_info(res)

            # 999989,49990,49989,49981,19996,9998,9999,9999,9997,9996
            remaining_counts = info.sOutValue2.split(",")

            messages = [f"{ctx} 当前礼包全局剩余量如下"]
            for idx, item_name in enumerate(item_name_list):
                messages.append(f"\t{item_name}: {remaining_counts[idx]}")
            logger.info("\n".join(messages))

        @try_except()
        def _query_quota_version_two(
            op_func: Callable[..., dict], flow_id_part_1: str, flow_id_part_2: str, ctx: str, item_name_list: list[str]
        ):
            res = op_func("查询礼包剩余量 1-8", flow_id_part_1, print_res=False)
            if res is None:
                return
            info = parse_amesvr_common_info(res)

            res = op_func("查询礼包剩余量 9-10", flow_id_part_2, print_res=False)
            if res is None:
                return
            info_2 = parse_amesvr_common_info(res)

            # 后面通过eval使用，这里赋值来避免lint报错
            _, _ = info, info_2

            messages = [f"{ctx} 当前礼包全局剩余量如下"]
            for idx in range(8):
                count = eval(f"info.sOutValue{idx + 1}")
                messages.append(f"\t{messages[idx]}: {count}")

            for idx in range(2):
                count = eval(f"info_2.sOutValue{idx + 1}")
                messages.append(f"\t{messages[8 + idx]}: {count}")

            logger.info("\n".join(messages))

        @try_except()
        def try_exchange():
            operations: list[tuple[str, str, int, str, Callable]] = [
                # ("10", "788270", 1, "灿烂的徽章自选礼盒【50代币券】", self.dnf_bbs_op_v2),
                # ("10", "821327", 1, "灿烂的徽章自选礼盒【50代币券】", self.dnf_bbs_op_v1),
                # ("9", "788270", 1, "灿烂的徽章神秘礼盒【25代币券】", self.dnf_bbs_op_v2),
                # ("9", "821327", 1, "灿烂的徽章神秘礼盒【25代币券】", self.dnf_bbs_op_v1),
                # ("4", "788270", 5, "装备提升礼盒【2代币券】", self.dnf_bbs_op_v2),
                # ("8", "821327", 1, "纯净的增幅书【25代币券】", self.dnf_bbs_op_v1),
                # ("3", "821327", 5, "装备提升礼盒【2代币券】", self.dnf_bbs_op_v1),
                # ("1", "788270", 5, "一次性材质转换器【2代币券】", self.dnf_bbs_op_v2),
                # ("1", "821327", 5, "一次性材质转换器【2代币券】", self.dnf_bbs_op_v1),
                # ("2", "788270", 5, "一次性继承装置【2代币券】", self.dnf_bbs_op_v2),
                # ("2", "821327", 5, "一次性继承装置【2代币券】", self.dnf_bbs_op_v1),
                # ("5", "788270", 2, "华丽的徽章自选礼盒【12代币券】", self.dnf_bbs_op_v2),
                # ("6", "821327", 2, "华丽的徽章自选礼盒【12代币券】", self.dnf_bbs_op_v1),
                # ("3", "788270", 5, "华丽的徽章神秘礼盒【2代币券】", self.dnf_bbs_op_v2),
                # ("5", "821327", 2, "华丽的徽章神秘礼盒【5代币券】", self.dnf_bbs_op_v1),
                # ("7", "788270", 1, "Lv100传说装备自选礼盒【12代币券】", self.dnf_bbs_op_v2),
                # ("7", "821327", 1, "Lv100传说装备自选礼盒【12代币券】", self.dnf_bbs_op_v1),
                # ("8", "788270", 1, "异界气息净化书【25代币券】", self.dnf_bbs_op_v2),
                # ("6", "788270", 1, "抗疲劳秘药 (30点)【12代币券】", self.dnf_bbs_op_v2),
                # ("4", "821327", 1, "灵魂武器袖珍罐【12代币券】", self.dnf_bbs_op_v1),
            ]

            for index_str, flowid, count, name, op_func in operations:
                logger.debug(f"{op_func}, {name}, {flowid}, {index_str}, {count}")

                for _i in range(count):
                    res = op_func(f"{op_func.__name__}_{name}", flowid, index=index_str)
                    if res is None:
                        # 说明被标记为过期了
                        continue

                    if res["ret"] == "700":
                        msg = res["flowRet"]["sMsg"]
                        if msg in ["您的该礼包兑换次数已达上限~", "抱歉，该礼包已被领完~"]:
                            # {"ret": "700", "flowRet": {"iRet": "700", "iCondNotMetId": "1425065", "sMsg": "您的该礼包兑换次数已达上限~", "sCondNotMetTips": "您的该礼包兑换次数已达上限~"}}
                            # 已达到兑换上限，尝试下一个
                            break
                        elif msg in ["您的代币券不足~", "抱歉，您当前的代币券不足！"]:
                            # {"ret": "700", "flowRet": {"iRet": "700", "iCondNotMetId": "1423792", "sMsg": "您的代币券不足~", "sCondNotMetTips": "您的代币券不足~"}}
                            logger.warning("代币券不足，直接退出，确保优先级高的兑换后才会兑换低优先级的")
                            return

        # ================= 实际逻辑 =================
        old_dbq = self.query_dnf_bbs_dbq()

        # 签到
        signin()

        after_sign_dbq = self.query_dnf_bbs_dbq()

        # 兑换签到奖励
        query_remaining_quota()
        try_exchange()

        after_exchange_dbq = self.query_dnf_bbs_dbq()
        logger.warning(
            color("bold_yellow")
            + f"账号 {self.cfg.name} 本次论坛签到获得 {after_sign_dbq - old_dbq} 个代币券，兑换道具消耗了 {after_exchange_dbq - after_sign_dbq} 个代币券，余额：{old_dbq} => {after_exchange_dbq}"
        )

    # note: 用于查询活动信息和查询剩余代币券，方便快速切换新旧版本
    # re: 若切换版本，需要将查询代币券处的flowid切换为新的版本对应的flowid
    def dnf_bbs_op(self, ctx, iFlowId, print_res=True, **extra_params):
        latest_op = self.dnf_bbs_op_v1
        # latest_op = self.dnf_bbs_op_v2

        return latest_op(ctx, iFlowId, print_res, **extra_params)

    @try_except(show_exception_info=False, return_val_on_except=0)
    def query_dnf_bbs_dbq(self) -> int:
        if self.cfg.dnf_bbs_cookie == "":
            return 0

        # note: 鉴于兑换活动会存在真空期，改用解析个人中心的方式来获取论坛代币数目
        url = self.urls.dnf_bbs_home
        headers = {
            "cookie": self.cfg.dnf_bbs_cookie,
        }

        res = requests.get(url, headers=headers, timeout=10)
        html_text = res.text

        # <li><em> 论坛代币: </em>17 </li>
        prefix = "论坛代币: </em>"
        suffix = "</li>"
        if prefix not in html_text:
            logger.warning("未能定位到论坛代币数目")
            return 0

        prefix_idx = html_text.index(prefix) + len(prefix)
        suffix_idx = html_text.index(suffix, prefix_idx)

        coin = int(html_text[prefix_idx:suffix_idx])

        return coin

    @try_except()
    def check_dnf_bbs_v1(self):
        self.check_bind_account(
            "DNF论坛积分兑换活动",
            "https://dnf.qq.com/cp/a20211130act/index.html",
            activity_op_func=self.dnf_bbs_op_v1,
            query_bind_flowid="821323",
            commit_bind_flowid="821322",
        )

    def dnf_bbs_op_v1(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_bbs_v1

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            "https://dnf.qq.com/cp/a20211130act/",
            **extra_params,
        )

    @try_except()
    def check_dnf_bbs_v2(self):
        return
        self.check_bind_account(
            "DNF论坛积分兑换活动",
            "https://dnf.qq.com/act/a20210803act/index.html",
            activity_op_func=self.dnf_bbs_op_v2,
            query_bind_flowid="788267",
            commit_bind_flowid="788266",
        )

    def dnf_bbs_op_v2(self, ctx, iFlowId, print_res=True, **extra_params):
        return
        iActivityId = self.urls.iActivityId_dnf_bbs_v2

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            "https://dnf.qq.com/act/a20210803act/index.html",
            **extra_params,
        )

    # --------------------------------------------colg每日签到--------------------------------------------
    @try_except()
    def colg_signin(self):
        # https://bbs.colg.cn/forum-171-1.html
        show_head_line("colg每日签到")
        self.show_not_ams_act_info("colg每日签到")

        if not self.cfg.function_switches.get_colg_signin or self.disable_most_activities():
            logger.warning("未启用colg每日签到功能，将跳过")
            return

        if self.cfg.colg_cookie == "":
            logger.warning(
                "未配置colg的cookie，将跳过（colg相关的配置会配置就配置，不会就不要配置，我不会回答关于这玩意如何获取的问题）"
            )
            return

        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,en-GB;q=0.6,ja;q=0.5",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://bbs.colg.cn",
            "referer": get_act_url("colg每日签到"),
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
            "cookie": json.dumps(self.cfg.colg_cookie, ensure_ascii=True),
        }

        session = requests.session()
        session.headers = headers  # type: ignore

        def query_task_info() -> ColgBattlePassQueryInfo:
            res = session.get(self.urls.colg_task_info_url, timeout=10)
            raw_info = res.json()

            task_info = ColgBattlePassQueryInfo().auto_update_config(raw_info["data"])
            return task_info

        def query_info() -> ColgBattlePassInfo:
            res = session.get(self.urls.colg_url, timeout=10)
            html = res.text

            activity_id = extract_between(html, "var activity_id = '", "';", str)

            task_info = query_task_info()

            lv_score = int(task_info.user_credit)
            conversion = int(task_info.cm_token)
            tasks = to_raw_type(task_info.user_task_list.list)
            rewards = to_raw_type(task_info.user_reward_list)

            info = ColgBattlePassInfo().auto_update_config(
                {
                    "activity_id": activity_id,
                    "lv_score": lv_score,
                    "conversion": conversion,
                    "tasks": tasks,
                    "rewards": rewards,
                }
            )

            return info

        info = query_info()

        for task in info.tasks:
            if not task.status:
                logger.info(f"任务 {task.task_name} 暂未开始，将跳过")
                continue

            if not task.is_finish:
                if task.sub_type == "1":
                    # 如果是签到任务，额外签到
                    signin_res = session.post(self.urls.colg_sign_in_url, data=f"task_id={task.id}", timeout=10)
                    logger.info(color("bold_green") + f"colg每日签到 {signin_res.json()}")
                    task.is_finish = True
                else:
                    # 如果任务未完成，则跳过
                    logger.warning(f"任务 {task.task_name} 条件尚未完成，请自行前往colg进行完成")
                    continue

            # 如果任务已领取，则跳过
            if task.is_get:
                logger.info(f"任务 {task.task_name} 的 积分奖励({task.task_reward}) 已经领取过，将跳过")
                continue

            # 尝试领取任务奖励
            res = session.get(
                self.urls.colg_take_sign_in_credits.format(aid=info.activity_id, task_id=task.id), timeout=10
            )
            logger.info(
                color("bold_green") + f"领取 {task.task_name} 的 积分奖励({task.task_reward})， 结果={res.json()}"
            )

        info = query_info()
        untaken_awards = info.untaken_rewards()
        msg = f"账号 {self.cfg.name} Colg活跃值已经达到 【{info.lv_score}】 了咯"
        if len(untaken_awards) > 0:
            msg += f"，目前有以下奖励可以领取，记得去Colg领取哦\n{untaken_awards}"
        else:
            msg += "，目前暂无未领取的奖励"
        logger.info(color("bold_green") + msg)

        if len(untaken_awards) > 0:
            need_show_message_box = False
            title = ""

            # 如果有剩余奖励
            act_config = get_not_ams_act("colg每日签到")
            if act_config is not None and will_act_expired_in(act_config.dtEndTime, datetime.timedelta(days=5)):
                # 活动即将过期时，则每天提示一次
                need_show_message_box = is_daily_first_run(f"colg_{info.activity_id}2_领取奖励_活动即将结束时_每日提醒")
                title = f"活动快过期了，记得领取奖励（过期时间为 {act_config.dtEndTime}）"
            else:
                # 否则，每周提示一次
                need_show_message_box = is_weekly_first_run(f"colg_{info.activity_id}2_领取奖励_每周提醒")
                title = "可以领奖励啦"

            if need_show_message_box:
                async_message_box(msg, title, open_url="https://bbs.colg.cn/forum-171-1.html", print_log=False)

        async_message_box(
            (
                "除签到外的任务条件，以及各个奖励的领取，请自己前往colg进行嗷\n"
                "\n"
                "此外colg社区活跃任务右侧有个【前往商城】，请自行完成相关活动后点进去自行兑换奖品"
            ),
            f"colg社区活跃任务-{info.activity_id}-提示",
            show_once=True,
        )

        conversion_status_message = f"账号 {self.cfg.name} Colg 当前兑换币数量为 {info.conversion}"
        logger.info(conversion_status_message)

        # 当兑换币足够时，提示兑换限量兑换的奖励
        limit_award_name = "黑钻30天"
        limit_award_require_conversion = 12
        # limit_award_count = 7500
        if info.conversion >= limit_award_require_conversion:
            async_message_box(
                (
                    f"{conversion_status_message}\n"
                    f"已足够兑换 {limit_award_name}(需{limit_award_require_conversion}兑换币)\n"
                    # f"该奖励限量{limit_award_count}个，"
                    f"请及时前往兑换。如果已经没有了，可以兑换其他奖励\n"
                ),
                f"colg社区活跃任务-{info.activity_id}-兑换限量奖励提示",
                open_url="https://bbs.colg.cn/colg_cmall-colg_cmall.html",
            )

    # --------------------------------------------colg其他活动--------------------------------------------
    @try_except()
    def colg_other_act(self):
        # 年终盛典 https://bbs.colg.cn/colg_activity_new-aggregation_activity.html?aid=16
        show_head_line("colg其他活动")
        self.show_not_ams_act_info("colg其他活动")

        if not self.cfg.function_switches.get_colg_other_act or self.disable_most_activities():
            logger.warning("未启用colg其他活动功能，将跳过")
            return

        if self.cfg.colg_cookie == "":
            logger.warning(
                "未配置colg的cookie，将跳过（colg相关的配置会配置就配置，不会就不要配置，我不会回答关于这玩意如何获取的问题）"
            )
            return

        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,en-GB;q=0.6,ja;q=0.5",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://bbs.colg.cn",
            "referer": get_act_url("colg其他活动"),
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
            "cookie": json.dumps(self.cfg.colg_cookie, ensure_ascii=True),
        }

        session = requests.session()
        session.headers = headers  # type: ignore

        session.get(self.urls.colg_other_act_url, timeout=10)

        reward_list = [
            {
                "reward_bag_id": "60",
                "title": "累计签到3天",
            },
            {
                "reward_bag_id": "61",
                "title": "累计签到7天",
            },
            {
                "reward_bag_id": "62",
                "title": "累计签到10天",
            },
            {
                "reward_bag_id": "63",
                "title": "累计签到15天",
            },
            {
                "reward_bag_id": "64",
                "title": "累计签到21天",
            },
            {
                "reward_bag_id": "65",
                "title": "累计签到28天",
            },
        ]
        for reward in reward_list:
            reward_bag_id = reward["reward_bag_id"]
            title = reward["title"]

            res = session.post(
                self.urls.colg_other_act_get_reward,
                data=f"aid={self.urls.colg_other_act_id}&reward_bag_id={reward_bag_id}",
                timeout=10,
            )
            res_json = res.json()
            logger.info(color("bold_green") + f"{title}，结果={res_json}")

            # 等一会，避免请求太快
            time.sleep(1)

            if "累积签到天数不足" in res_json["msg"]:
                logger.warning("累积天数不足，跳过尝试后续")
                break

        res = session.post(
            self.urls.colg_other_act_lottery, data=f"type=2&aid={self.urls.colg_other_act_id}", timeout=10
        )
        logger.info(color("bold_green") + f"每日抽奖，结果={res.json()}")

    # --------------------------------------------小酱油周礼包和生日礼包--------------------------------------------
    @try_except()
    def xiaojiangyou(self):
        show_head_line("小酱油周礼包和生日礼包")
        self.show_not_ams_act_info("小酱油周礼包和生日礼包")

        if not self.cfg.function_switches.get_xiaojiangyou or self.disable_most_activities():
            logger.warning("未启用小酱油周礼包和生日礼包功能，将跳过")
            return

        # ------------------------- 准备各种参数 -------------------------
        self.xjy_prepare_env()

        # ------------------------- 封装的各种操作函数 -------------------------
        def _get(ctx: str, url: str, print_res=True, **params):
            return self.get(
                ctx,
                url,
                **params,
                print_res=print_res,
                extra_headers=self.xjy_headers_with_role,
                is_jsonp=True,
                is_normal_jsonp=True,
            )

        def init_page():
            raw_info = _get("初始化页面", self.urls.xiaojiangyou_init_page, print_res=False)
            return raw_info

        def _ask_question(question: str, question_id: str, robot_type: str, print_res=True) -> dict:
            question_quoted = quote(question)

            raw_info = _get(
                question,
                self.urls.xiaojiangyou_ask_question,
                question=question_quoted,
                question_id=question_id,
                robot_type=robot_type,
                certificate=self.xjy_info.certificate,
                print_res=print_res,
            )

            return raw_info

        def query_activities():
            return _ask_question("福利活动", "11104840", "2", print_res=False)

        def take_weekly_gift():
            raw_weekly_package_info = _ask_question("每周礼包", "11175574", "0", print_res=False)
            pi = XiaojiangyouPackageInfo().auto_update_config(raw_weekly_package_info["result"]["answer"][1]["content"])

            _get(
                "领取每周礼包",
                self.urls.xiaojiangyou_get_packge,
                token=pi.token,
                ams_id=pi.ams_id,
                package_group_id=pi.package_group_id,
                tool_id=pi.tool_id,
                certificate=self.xjy_info.certificate,
            )

        def take_birthday_gift():
            raw_birthday_package_info = _ask_question("生日礼包", "11090757", "0", print_res=False)
            pi = XiaojiangyouPackageInfo().auto_update_config(
                raw_birthday_package_info["result"]["answer"][0]["content"]
            )

            _get(
                "领取生日礼包",
                self.urls.xiaojiangyou_get_packge,
                token=pi.token,
                ams_id=pi.ams_id,
                package_group_id=pi.package_group_id,
                tool_id=pi.tool_id,
                certificate=self.xjy_info.certificate,
            )

            notify_birthday(raw_birthday_package_info)

        def notify_birthday(raw_birthday_package_info: dict):
            text = json.dumps(raw_birthday_package_info, ensure_ascii=False)

            reg_birthday = r"你的生日是在(\d{4})年(\d{2})月(\d{2})日"

            match = re.search(reg_birthday, text)
            if match is not None:
                year, month, day = (int(v) for v in match.groups())
                birthday = datetime.datetime(year, month, day)
                logger.info(f"{self.cfg.name} 的 DNF生日（账号创建日期） 为 {birthday}")

                now = get_now()
                max_delta = datetime.timedelta(days=30)

                # 依次判断去年、今年生日是否在今天之前30天内
                possiable_birthdays = [
                    birthday.replace(year=now.year - 1),
                    birthday.replace(year=now.year),
                ]

                for try_birth_day in possiable_birthdays:
                    if try_birth_day <= now <= try_birth_day + max_delta:
                        act_url = "https://pay.qq.com/m/active/activity_dispatcher.php?id=3099"
                        msg = (
                            f"{self.cfg.name} 的 DNF生日（账号创建日期） 为 {birthday}，最近一次生日为 {try_birth_day}，在该日期的30天内可以用手机去qq的充值中心领取一个生日礼\n"
                            f"\n"
                            f"具体链接为 {act_url}"
                        )
                        logger.info(color("bold_yellow") + msg)
                        if is_weekly_first_run(f"生日提醒_{self.cfg.name}"):
                            async_message_box(msg, "生日提醒", open_url=act_url)

        # ------------------------- 正式逻辑 -------------------------
        take_weekly_gift()
        take_birthday_gift()

    def xjy_prepare_env(self):
        logger.info("准备小酱油所需的各个参数，可能会需要几秒~")

        roleinfo = self.get_dnf_bind_role()

        uin_skey_cookie = f"uin={self.cfg.account_info.uin}; skey={self.cfg.account_info.skey}; "
        roleNameUnquote = roleinfo.roleName
        partition_id = roleinfo.serviceID

        roleName = quote(roleNameUnquote)
        self.xjy_base_headers = {
            "Referer": "https://tool.helper.qq.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.78",
            "Cookie": f"{uin_skey_cookie}",
        }

        role_id = self.xjy_get_role_id(partition_id, roleName, self.xjy_base_headers)

        xychat_lumen_role = (
            "a$10${"
            's$6$"source";s$8$"xy_games";'
            's$7$"game_id";s$1$"1";'
            f's$7$"role_id";{self.xjy_encode_str(role_id)}'
            f's$9$"role_name";{self.xjy_encode_str(roleNameUnquote)}'
            's$9$"system_id";s$1$"2";'
            's$9$"region_id";s$1$"1";'
            's$7$"area_id";s$1$"1";'
            's$7$"plat_id";s$1$"1";'
            f's$12$"partition_id";{self.xjy_encode_str(partition_id)}'
            's$7$"acctype";s$0$"";'
            "}"
        ).replace("$", ":")

        self.xjy_headers_with_role = {
            **self.xjy_base_headers,
            "Cookie": f"{uin_skey_cookie}" "xychat_login_type=qq; " f"xychat_lumen_role={quote(xychat_lumen_role)}" "",
        }

        self.xjy_info = self.xjy_query_info()

    def xjy_get_role_id(self, areaId: str, roleName: str, headers: dict) -> str:
        res = requests.get(
            self.format(self.urls.xiaojiangyou_get_role_id, areaId=areaId, roleName=roleName), headers=headers
        )
        parsed = parse.urlparse(res.url)
        role_id = parse.parse_qs(parsed.query)["role_id"][0]

        return role_id

    def xjy_query_info(self) -> XiaojiangyouInfo:
        raw_info = self.get(
            "获取小酱油信息",
            self.urls.xiaojiangyou_query_info,
            extra_headers=self.xjy_headers_with_role,
            is_jsonp=True,
            is_normal_jsonp=True,
            print_res=False,
        )
        info = XiaojiangyouInfo().auto_update_config(raw_info["result"])

        return info

    def xjy_encode_str(self, s: str) -> str:
        """
        将字符串str编码为 s${str的utf编码长度}$"{str}";
        如 test 编码为 s$4$"test";
        """
        return f's${utf8len(s)}$"{s}";'

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

    # --------------------------------------------DNF落地页活动--------------------------------------------
    @try_except()
    def dnf_luodiye(self):
        show_head_line("DNF落地页活动")
        self.show_amesvr_act_info(self.dnf_luodiye_op)

        if not self.cfg.function_switches.get_dnf_luodiye or self.disable_most_activities():
            logger.warning("未启用领取DNF落地页活动功能，将跳过")
            return

        self.check_dnf_luodiye()

        def query_scode() -> str:
            res = self.dnf_luodiye_op("初始化", "990073")
            raw_info = res["modRet"]["jData"]

            return raw_info["sCode"]

        # ------------ 实际流程 --------------
        self.dnf_luodiye_op("见面礼", "989287")

        self.dnf_luodiye_op("每日任务一", "989304")
        self.dnf_luodiye_op("每日任务二", "989305")
        self.dnf_luodiye_op("每周任务一", "989306")
        self.dnf_luodiye_op("每周任务二", "989307")

        lottery_times = 6
        for idx in range_from_one(lottery_times):
            res = self.dnf_luodiye_op(f"{idx}/{lottery_times} 抽奖", "989308")
            if res["ret"] == "700" or (res["ret"] == "0" and res["modRet"]["ret"] == 10001):
                break
            time.sleep(5)

        # # 1, 3, 4
        # self.dnf_luodiye_op("道具5选3", "978851", sNum="1|3|4")
        #
        # self.dnf_luodiye_op("通关任意难度盖加波", "978852")
        # self.dnf_luodiye_op("累计获得史诗10件", "978853")
        # self.dnf_luodiye_op("累计获得史诗20件", "978854")

        self.dnf_social_relation_permission_op(
            "更新创建用户授权信息", "108939", sAuthInfo="LDY", sActivityInfo="a20231116index"
        )

        if not self.cfg.function_switches.disable_share and is_first_run(
            f"dnf_luodiye_{get_act_url('DNF落地页活动')}_分享_{self.uin()}_v2"
        ):
            p_skey = self.fetch_share_p_skey("落地页邀请")
            my_scode = query_scode()
            self.dnf_luodiye_op("发送ark消息给自己", "989316", targetQQ=my_scode, p_skey=p_skey)

        self.dnf_luodiye_op("首次邀请领黑钻礼包", "989318")

        async_message_box(
            "落地页活动页面有个拉回归的活动，拉四个可以换一个红10增幅券，有兴趣的请自行完成~(每天只能拉一个，至少需要分四天）",
            "1117 落地页拉回归活动",
            show_once=True,
            open_url=get_act_url("DNF落地页活动"),
        )

    def check_dnf_luodiye(self):
        self.check_bind_account(
            "DNF落地页活动",
            get_act_url("DNF落地页活动"),
            activity_op_func=self.dnf_luodiye_op,
            query_bind_flowid="993001",
            commit_bind_flowid="993000",
        )

    def dnf_luodiye_op(self, ctx, iFlowId, p_skey="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_luodiye

        # roleinfo = self.get_dnf_bind_role()
        # checkInfo = self.get_dnf_roleinfo()
        #
        # checkparam = quote_plus(quote_plus(checkInfo.checkparam))

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF落地页活动"),
            # sArea=roleinfo.serviceID, sPartition=roleinfo.serviceID, sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
            # sRoleId=roleinfo.roleCode, sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
            # md5str=checkInfo.md5str, ams_checkparam=checkparam, checkparam=checkparam,
            **extra_params,
            extra_cookies=f"p_skey={p_skey}",
        )

    # --------------------------------------------DNF落地页活动_ide--------------------------------------------
    @try_except()
    def dnf_luodiye_ide(self):
        show_head_line("DNF落地页活动_ide")
        self.show_not_ams_act_info("DNF落地页活动_ide")

        if not self.cfg.function_switches.get_dnf_luodiye or self.disable_most_activities():
            logger.warning("未启用领取DNF落地页活动_ide功能，将跳过")
            return

        self.check_dnf_luodiye_ide()

        def query_info() -> tuple[int, int]:
            res = self.dnf_luodiye_ide_op("初始化", "295037", print_res=False)
            raw_info = res["jData"]

            # 抽奖次数
            iLottery = int(raw_info["iLottery"])

            # 累计登录天数
            iLoginTotal = int(raw_info["iLoginTotal"])

            return iLottery, iLoginTotal

        # ------------ 实际流程 --------------
        self.dnf_luodiye_ide_op("周年礼包", "295043")

        self.dnf_luodiye_ide_op("每日登录礼包", "295044")

        login_gifts_list = {
            (1, 3),
            (2, 5),
            (3, 7),
            (4, 10),
            (5, 14),
            (6, 21),
            (7, 28),
        }
        _, iLoginTotal = query_info()
        logger.info(f"累计登录天数为 {iLoginTotal}")
        for gift_index, require_login_days in login_gifts_list:
            if iLoginTotal >= require_login_days:
                self.dnf_luodiye_ide_op(f"[{gift_index}] 累计登录{require_login_days}天礼包", "295045", num=gift_index)
            else:
                logger.warning(f"[{gift_index}] 当前累计登录未达到{require_login_days}天，将不尝试领取该累计奖励")

        tasks = [
            ("每日任务一", "295085"),
            ("每日任务二", "295089"),
            ("每周任务一", "295113"),
            ("每周任务二", "295150"),
        ]
        for name, flowid in tasks:
            self.dnf_luodiye_ide_op(name, flowid)
            time.sleep(5)

        # iTicket, iLottery = query_info()
        # async_message_box(
        #     (
        #         f"当前好友积分为{iTicket}，请自行前往点击确认弹出的网页中进行兑换奖品\n"
        #         "其中完成任务后还有需要进行分享完成的普通积分礼包和豪华积分礼包，如有兴趣，请自行完成\n"
        #     ),
        #     f"官网新春签到活动_每周提示_{self.cfg.name}",
        #     open_url=get_act_url("DNF落地页活动_ide"),
        #     show_once_weekly=True,
        # )

        iLottery, _ = query_info()
        logger.info(f"当前抽奖次数为 {iLottery}")
        for idx in range_from_one(iLottery):
            res = self.dnf_luodiye_ide_op(f"{idx}/{iLottery} 抽奖", "295154")
            _ = res
            # if res["ret"] == 10001:
            #     break
            time.sleep(5)

        async_message_box(
            "落地页活动页面有个拉回归的活动，拉四个可以换一个红10增幅券，有兴趣的请自行完成~(每天只能拉一个，至少需要分四天）",
            "24.6 落地页拉回归活动",
            show_once=True,
            open_url=get_act_url("DNF落地页活动_ide"),
        )

    def check_dnf_luodiye_ide(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF落地页活动_ide",
            get_act_url("DNF落地页活动_ide"),
            activity_op_func=self.dnf_luodiye_ide_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_luodiye_ide_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_luodiye

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF落地页活动_ide"),
            **extra_params,
        )

    # --------------------------------------------DNF落地页活动_ide_dup--------------------------------------------
    @try_except()
    def dnf_luodiye_ide_dup(self):
        show_head_line("DNF落地页活动_ide_dup")
        self.show_not_ams_act_info("DNF落地页活动_ide_dup")

        if not self.cfg.function_switches.get_dnf_luodiye or self.disable_most_activities():
            logger.warning("未启用领取DNF落地页活动_ide_dup功能，将跳过")
            return

        self.check_dnf_luodiye_ide_dup()

        def query_info() -> int:
            res = self.dnf_luodiye_ide_dup_op("初始化", "280105", print_res=False)
            raw_info = res["jData"]

            # 抽奖次数
            iLottery = int(raw_info["iLottery"])

            return iLottery

        # ------------ 实际流程 --------------
        self.dnf_luodiye_ide_dup_op("回流礼包", "280254")
        time.sleep(5)
        self.dnf_luodiye_ide_dup_op("全民礼包", "280247")

        tasks = [
            ("每日任务一", "280256"),
            ("每日任务二", "280257"),
            ("每周任务一", "280258"),
            ("每周任务二", "280259"),
        ]
        for name, flowid in tasks:
            self.dnf_luodiye_ide_dup_op(name, flowid)
            time.sleep(5)

        # iTicket, iLottery = query_info()
        # async_message_box(
        #     (
        #         f"当前好友积分为{iTicket}，请自行前往点击确认弹出的网页中进行兑换奖品\n"
        #         "其中完成任务后还有需要进行分享完成的普通积分礼包和豪华积分礼包，如有兴趣，请自行完成\n"
        #     ),
        #     f"官网新春签到活动_每周提示_{self.cfg.name}",
        #     open_url=get_act_url("DNF落地页活动_ide_dup"),
        #     show_once_weekly=True,
        # )

        iLottery = query_info()
        logger.info(f"当前抽奖次数为 {iLottery}")
        for idx in range_from_one(iLottery):
            res = self.dnf_luodiye_ide_dup_op(f"{idx}/{iLottery} 抽奖", "280260")
            _ = res
            # if res["ret"] == 10001:
            #     break
            time.sleep(5)

        async_message_box(
            "落地页活动页面有个拉回归的活动，拉四个可以换一个红10增幅券，有兴趣的请自行完成~(每天只能拉一个，至少需要分四天）",
            "24.4 落地页拉回归活动",
            show_once=True,
            open_url=get_act_url("DNF落地页活动_ide_dup"),
        )

    def check_dnf_luodiye_ide_dup(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF落地页活动_ide_dup",
            get_act_url("DNF落地页活动_ide_dup"),
            activity_op_func=self.dnf_luodiye_ide_dup_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_luodiye_ide_dup_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_luodiye_dup

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF落地页活动_ide_dup"),
            **extra_params,
        )

    # --------------------------------------------DNF年货铺--------------------------------------------
    @try_except()
    def dnf_nianhuopu(self):
        show_head_line("DNF年货铺")
        self.show_not_ams_act_info("DNF年货铺")

        if not self.cfg.function_switches.get_dnf_nianhuopu or self.disable_most_activities():
            logger.warning("未启用领取DNF年货铺功能，将跳过")
            return

        self.check_dnf_nianhuopu()

        def query_info() -> int:
            res = self.dnf_nianhuopu_op("初始化", "260625", print_res=False)
            raw_info = res["jData"]

            # 普通积分
            ticket_num = int(raw_info["iExchange"])

            return ticket_num

        self.dnf_nianhuopu_op("每日任务一 | 通关神界任意普通地下城1次，可获得年货券x1", "261559")
        self.dnf_nianhuopu_op("每日任务二 | 累计游戏内消耗50疲劳值，可获得年货券x1", "261560")
        self.dnf_nianhuopu_op("每周任务一 | 通关深渊地下城【均衡仲裁者】2次，可获得年货券x2", "261562")
        self.dnf_nianhuopu_op("每周任务二 | 通关任意难度高级地下城*2次，可获得年货券x4", "261563")
        self.dnf_nianhuopu_op("每周任务三 | 进行装备属性成长*10次，可获得年货券x2", "261649")
        self.dnf_nianhuopu_op("每周任务四 | 进行装备属性成长*10次，可获得年货券x2", "261650")

        self.dnf_nianhuopu_op("语音电话奖励", "261711")
        self.dnf_nianhuopu_op("除夕分享奖励", "261717")
        self.dnf_nianhuopu_op("房间图片分享", "261721")

        # self.dnf_nianhuopu_op("获取灯谜", "261976")
        # self.dnf_nianhuopu_op("回答灯谜", "262012")
        #
        # self.dnf_nianhuopu_op("灯谜抽奖", "262048")

        # self.dnf_nianhuopu_op("好友列表", "261866")
        # self.dnf_nianhuopu_op("发送ark消息", "261867")
        # self.dnf_nianhuopu_op("新增好友", "261868")
        # self.dnf_nianhuopu_op("接受邀请", "261945")
        # self.dnf_nianhuopu_op("邀请好友奖励", "264630")

        ticket_num = query_info()

        tips = f"当前年货券为 {ticket_num}, 请自行前往点击确认弹出的网页中进行兑换奖品(次元穿梭光环、高级装扮、增幅书等）\n"
        title = f"年货铺兑换_每周提示_{self.cfg.name}"
        show_once_weekly = True

        act_info = get_not_ams_act("DNF年货铺")
        if act_info.is_last_day():
            tips = f"当前已是活动最后一天，年货券为 {ticket_num}, 请自行前往点击确认弹出的网页中进行兑换奖品(次元穿梭光环、高级装扮、增幅书等）\n"
            title = f"年货铺兑换_最后一天提示_{self.cfg.name}"
            show_once_weekly = False

        async_message_box(
            tips,
            title,
            open_url=get_act_url("DNF年货铺"),
            show_once_weekly=show_once_weekly,
        )
        # self.dnf_nianhuopu_op("兑换年货", "261666")

    def check_dnf_nianhuopu(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF年货铺",
            get_act_url("DNF年货铺"),
            activity_op_func=self.dnf_nianhuopu_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_nianhuopu_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_nianhuopu

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF年货铺"),
            **extra_params,
        )

    # --------------------------------------------DNF神界成长之路--------------------------------------------
    @try_except()
    def dnf_shenjie_grow_up(self):
        show_head_line("DNF神界成长之路")
        self.show_not_ams_act_info("DNF神界成长之路")

        if not self.cfg.function_switches.get_dnf_shenjie_grow_up or self.disable_most_activities():
            logger.warning("未启用领取DNF神界成长之路功能，将跳过")
            return

        # 这个活动让用户自己去选择绑定的角色，因为关系到角色绑定的奖励领取到哪个角色上
        # self.check_dnf_shenjie_grow_up()

        def query_has_bind_role() -> bool:
            bind_config = self.dnf_shenjie_grow_up_op(
                "查询活动信息 - DNF神界成长之路", "", get_act_info_only=True
            ).get_bind_config()

            query_bind_res = self.dnf_shenjie_grow_up_op("查询绑定", bind_config.query_map_id, print_res=False)

            has_bind = query_bind_res["jData"]["bindarea"] is not None

            return has_bind

        def query_info() -> ShenJieGrowUpInfo:
            res = self.dnf_shenjie_grow_up_op("初始化用户及查询", "263027", print_res=False)

            info = ShenJieGrowUpInfo()
            info.auto_update_config(res["jData"]["userData"])

            return info

        @try_except()
        def take_task_rewards(curStageData: ShenJieGrowUpCurStageData, taskData: dict[str, ShenJieGrowUpTaskData]):
            task_index_to_name = {
                "1": "通关代号：盖波加",
                "2": "通关白云溪谷或索利达里斯",
                "3": "通关任意难度机械崛起：巴卡尔攻坚战",
                "4": "通关任意难度军团地下城：幽暗岛",
                "5": "通关均衡仲裁者",
            }
            if int(curStageData.stage) >= 5:
                # 阶段 5及以后  第三个任务变更了
                task_index_to_name["3"] = "通关任意难度异面边界"

            not_finished_task_desc_list = []

            for task_index, task_info in taskData.items():
                task_name = task_index_to_name[task_index]

                if int(task_info.giftStatus) == 1:
                    logger.info(f"已领取任务 {task_name} 奖励")
                else:
                    if task_info.needNum > task_info.doneNum:
                        logger.info(f"未完成任务 {task_name}，当前进度为 {task_info.doneNum}/{task_info.needNum}")
                        not_finished_task_desc_list.append(
                            f"    {task_index} {task_name} {task_info.doneNum}/{task_info.needNum}"
                        )
                    else:
                        logger.info(f"已完成任务 {task_name}，尝试领取奖励")

                        self.dnf_shenjie_grow_up_op(
                            f"领取任务奖励 - {task_name}",
                            "263070",
                            u_stage=curStageData.stage,
                            u_task_index=task_index,
                        )

            # 提示当前未完成的任务
            # 周期的前半段，也就是正常可以完成对应任务内容的456三天不弹窗提示进度，之后几天，若仍有任务未完成，则每天尝试提示一次
            now = get_now()
            do_not_show_message_box = now.isoweekday() in [4, 5, 6] or len(not_finished_task_desc_list) == 0

            cycle_start_thursday = get_this_thursday_of_dnf()
            day_index_in_cycle = (now - cycle_start_thursday).days + 1

            role_name = double_unquote(curStageData.sRoleName)
            server_name = dnf_server_id_to_name(curStageData.iAreaId)

            total_task = len(taskData)
            done_task = total_task - len(not_finished_task_desc_list)

            tips = ""
            tips = tips + f"当前账号：{self.cfg.name} {self.qq()}\n"
            tips = tips + f"绑定角色：{server_name} {role_name}\n"

            if len(not_finished_task_desc_list) > 0:
                tips = (
                    tips
                    + f"当前为本周期第 {day_index_in_cycle} 天，神界成长之路（大百变与8周锁2）绑定的角色尚未完成以下的任务，请在下个周四零点之前完成~\n"
                )
                tips = tips + "\n"
                tips = tips + "\n".join(not_finished_task_desc_list)
            else:
                tips = tips + f"当前为本周期第 {day_index_in_cycle} 天，本周任务均已完成\n"

            title = f"{self.cfg.name} {role_name} 大百变活动进度提示 当前阶段{curStageData.stage}/8 本周期已完成任务 {done_task}/{total_task}"

            show_head_line("大百变活动进度", msg_color=color("bold_yellow"))
            async_message_box(
                tips,
                title,
                show_once_daily=True,
                do_not_show_message_box=do_not_show_message_box,
                color_name="bold_yellow",
            )

            # 自己使用时，若尚未完成，则每次运行都弹提示，更加直观
            if use_by_myself() and len(not_finished_task_desc_list) > 0:
                async_message_box(
                    tips,
                    title,
                )

        @try_except()
        def take_stage_rewards(curStageData: ShenJieGrowUpCurStageData, allStagePack: list[ShenJieGrowUpStagePack]):
            for stage_pack in allStagePack:
                if stage_pack.packStatus == 1:
                    logger.info(f"阶段{stage_pack.stage} 奖励已领取")
                else:
                    logger.info(f"阶段{stage_pack.stage} 奖励未领取, 尝试领取")
                    self.dnf_shenjie_grow_up_op(
                        f"领取 阶段{stage_pack.stage} 奖励", "263107", u_stage_index=stage_pack.stage
                    )

        has_bind_role = query_has_bind_role()
        logger.info(f"DNF神界成长之路是否已绑定角色: {has_bind_role}")

        if not has_bind_role:
            async_message_box(
                (
                    f"当前账号 {self.cfg.name} {self.qq()} 尚未在大百变活动（神界成长之路）中绑定角色\n"
                    "\n"
                    "请打开游戏，进入你想要绑定的角色，点击游戏右下角对应的按钮完成绑定流程\n"
                ),
                "大百变活动未绑定",
                show_once_weekly=True,
            )
            return

        info = query_info()
        curStageData = info.curStageData
        taskData = info.taskData
        allStagePack = info.allStagePack

        role_name = double_unquote(curStageData.sRoleName)
        server_name = dnf_server_id_to_name(curStageData.iAreaId)

        logger.info(f"角色昵称: {role_name}")
        logger.info(f"绑定大区: {server_name}")
        logger.info(f"当前任务阶段: {curStageData.stage}/8")

        self.dnf_shenjie_grow_up_op("领取大百变", "263051")

        take_task_rewards(curStageData, taskData)

        take_stage_rewards(curStageData, allStagePack)

    def check_dnf_shenjie_grow_up(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF神界成长之路",
            get_act_url("DNF神界成长之路"),
            activity_op_func=self.dnf_shenjie_grow_up_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_shenjie_grow_up_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_shenjie_grow_up

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF神界成长之路"),
            **extra_params,
        )

    # --------------------------------------------DNF神界成长之路二期--------------------------------------------
    @try_except()
    def dnf_shenjie_grow_up_v2(self):
        show_head_line("DNF神界成长之路二期")
        self.show_not_ams_act_info("DNF神界成长之路二期")

        if not self.cfg.function_switches.get_dnf_shenjie_grow_up or self.disable_most_activities():
            logger.warning("未启用领取DNF神界成长之路二期功能，将跳过")
            return

        # 这个活动让用户自己去选择绑定的角色，因为关系到角色绑定的奖励领取到哪个角色上
        # self.check_dnf_shenjie_grow_up_v2()

        def query_has_bind_role() -> bool:
            bind_config = self.dnf_shenjie_grow_up_v2_op(
                "查询活动信息 - DNF神界成长之路二期", "", get_act_info_only=True
            ).get_bind_config()

            query_bind_res = self.dnf_shenjie_grow_up_v2_op("查询绑定", bind_config.query_map_id, print_res=False)

            has_bind = query_bind_res["jData"]["bindarea"] is not None

            return has_bind

        def query_info() -> ShenJieGrowUpInfo:
            res = self.dnf_shenjie_grow_up_v2_op("初始化用户及查询", "280272", print_res=False)

            info = ShenJieGrowUpInfo()
            info.auto_update_config(res["jData"]["userData"])

            return info

        @try_except()
        def take_task_rewards(curStageData: ShenJieGrowUpCurStageData, taskData: dict[str, ShenJieGrowUpTaskData]):
            task_index_to_name = {
                "1": "通关神界任意高级地下城1次",
                "2": "通关均衡仲裁者20次",
                "3": "通关盖波加1次",
                "4": "通关异面边界1次",
            }
            if int(curStageData.stage) >= 2:
                # 阶段2以后，后面俩任务条件有所变化
                task_index_to_name["3"] = "通关异面边界1次"
                task_index_to_name["4"] = "通关幽暗岛1次"

            not_finished_task_desc_list = []

            for task_index, task_info in taskData.items():
                task_name = task_index_to_name[task_index]

                if int(task_info.giftStatus) == 1:
                    logger.info(f"已领取任务 {task_name} 奖励")
                else:
                    if task_info.needNum > task_info.doneNum:
                        logger.info(f"未完成任务 {task_name}，当前进度为 {task_info.doneNum}/{task_info.needNum}")
                        not_finished_task_desc_list.append(
                            f"    {task_index} {task_name} {task_info.doneNum}/{task_info.needNum}"
                        )
                    else:
                        logger.info(f"已完成任务 {task_name}，尝试领取奖励")

                        self.dnf_shenjie_grow_up_v2_op(
                            f"领取任务奖励 - {task_name}",
                            "280275",
                            u_stage=curStageData.stage,
                            u_task_index=task_index,
                        )

            # 提示当前未完成的任务
            # 周期的前半段，也就是正常可以完成对应任务内容的456三天不弹窗提示进度，之后几天，若仍有任务未完成，则每天尝试提示一次
            now = get_now()
            do_not_show_message_box = now.isoweekday() in [4, 5, 6] or len(not_finished_task_desc_list) == 0

            cycle_start_thursday = get_this_thursday_of_dnf()
            day_index_in_cycle = (now - cycle_start_thursday).days + 1

            role_name = double_unquote(curStageData.sRoleName)
            server_name = dnf_server_id_to_name(curStageData.iAreaId)

            total_task = len(taskData)
            done_task = total_task - len(not_finished_task_desc_list)

            tips = ""
            tips = tips + f"当前账号：{self.cfg.name} {self.qq()}\n"
            tips = tips + f"绑定角色：{server_name} {role_name}\n"

            if len(not_finished_task_desc_list) > 0:
                tips = (
                    tips
                    + f"当前为本周期第 {day_index_in_cycle} 天，神界成长之路（大百变与8周锁2）绑定的角色尚未完成以下的任务，请在下个周四零点之前完成~\n"
                )
                tips = tips + "\n"
                tips = tips + "\n".join(not_finished_task_desc_list)
            else:
                tips = tips + f"当前为本周期第 {day_index_in_cycle} 天，本周任务均已完成\n"

            title = f"{self.cfg.name} {role_name} 成长之路2 进度提示 当前阶段{curStageData.stage}/8 本周期已完成任务 {done_task}/{total_task}"

            show_head_line("大百变活动进度", msg_color=color("bold_yellow"))
            async_message_box(
                tips,
                title,
                show_once_daily=True,
                do_not_show_message_box=do_not_show_message_box,
                color_name="bold_yellow",
            )

            # 自己使用时，若尚未完成，则每次运行都弹提示，更加直观
            if use_by_myself() and len(not_finished_task_desc_list) > 0:
                async_message_box(
                    tips,
                    title,
                )

        @try_except()
        def take_stage_rewards(curStageData: ShenJieGrowUpCurStageData, allStagePack: list[ShenJieGrowUpStagePack]):
            for stage_pack in allStagePack:
                if stage_pack.packStatus == 1:
                    logger.info(f"阶段{stage_pack.stage} 奖励已领取")
                else:
                    logger.info(f"阶段{stage_pack.stage} 奖励未领取, 尝试领取")
                    self.dnf_shenjie_grow_up_v2_op(
                        f"领取 阶段{stage_pack.stage} 奖励", "280276", u_stage_index=stage_pack.stage
                    )

        has_bind_role = query_has_bind_role()
        logger.info(f"DNF神界成长之路二期是否已绑定角色: {has_bind_role}")

        if not has_bind_role:
            async_message_box(
                (
                    f"当前账号 {self.cfg.name} {self.qq()} 尚未在大百变活动（神界成长之路）中绑定角色\n"
                    "\n"
                    "请打开游戏，进入你想要绑定的角色，点击游戏右下角对应的按钮完成绑定流程\n"
                ),
                "大百变活动 第二期 未绑定",
                show_once_weekly=True,
            )
            return

        info = query_info()
        curStageData = info.curStageData
        taskData = info.taskData
        allStagePack = info.allStagePack

        role_name = double_unquote(curStageData.sRoleName)
        server_name = dnf_server_id_to_name(curStageData.iAreaId)

        logger.info(f"角色昵称: {role_name}")
        logger.info(f"绑定大区: {server_name}")
        logger.info(f"当前任务阶段: {curStageData.stage}/8")

        # self.dnf_shenjie_grow_up_v2_op("领取大百变", "263051")

        take_task_rewards(curStageData, taskData)

        take_stage_rewards(curStageData, allStagePack)

    def check_dnf_shenjie_grow_up_v2(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF神界成长之路二期",
            get_act_url("DNF神界成长之路二期"),
            activity_op_func=self.dnf_shenjie_grow_up_v2_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_shenjie_grow_up_v2_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_shenjie_grow_up_v2

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF神界成长之路二期"),
            **extra_params,
        )

    # --------------------------------------------绑定手机活动--------------------------------------------
    @try_except()
    def dnf_bind_phone(self):
        show_head_line("绑定手机活动")
        self.show_amesvr_act_info(self.dnf_bind_phone_op)

        if not self.cfg.function_switches.get_dnf_bind_phone or self.disable_most_activities():
            logger.warning("未启用领取绑定手机活动功能，将跳过")
            return

        self.check_dnf_bind_phone()

        def query_info():
            res = self.dnf_bind_phone_op("查询信息", "971619", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            isGetBindGift = int(raw_info.sOutValue1) == 1
            bindPhone = raw_info.sOutValue2
            exchangeTickets = int(raw_info.sOutValue3)
            isSettlement = int(raw_info.sOutValue4) == 1

            return isGetBindGift, bindPhone, exchangeTickets, isSettlement

        isGetBindGift, bindPhone, exchangeTickets, isSettlement = query_info()
        if bindPhone == "0":
            async_message_box(
                "当前账号尚未绑定手机，可前往活动页面绑定手机，绑定后可以领取666代币券，同时每月可以领取积分来兑换其他蚊子腿",
                f"绑定手机-{self.cfg.name}",
                open_url=get_act_url("绑定手机活动"),
                show_once_monthly=True,
            )

        if not isGetBindGift:
            self.dnf_bind_phone_op("领取豪礼（新）", "970721")

        if not isSettlement:
            self.dnf_bind_phone_op("发放兑换积分", "970838")

        if exchangeTickets > 2:
            self.dnf_bind_phone_op("兑换-增肥器-4", "970763", selectNo="4")

    def check_dnf_bind_phone(self):
        self.check_bind_account(
            "绑定手机活动",
            get_act_url("绑定手机活动"),
            activity_op_func=self.dnf_bind_phone_op,
            query_bind_flowid="970815",
            commit_bind_flowid="970814",
        )

    def dnf_bind_phone_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_bind_phone
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("绑定手机活动"),
            **extra_params,
        )

    # --------------------------------------------WeGame活动--------------------------------------------
    @try_except()
    def dnf_wegame(self):
        show_head_line("WeGame活动")
        self.show_amesvr_act_info(self.dnf_wegame_op)

        if not self.cfg.function_switches.get_dnf_wegame or self.disable_most_activities():
            logger.warning("未启用领取WeGame活动功能，将跳过")
            return

        self.check_dnf_wegame()

        # jifen_flowid = "864315"

        def query_counts() -> tuple[int, int]:
            res = self.dnf_wegame_op("查询各种数据", "916703", print_res=False)
            info = parse_amesvr_common_info(res)

            key_count, lottery_count = info.sOutValue5.split("|")
            return int(key_count), int(lottery_count)

        def query_open_box_times():
            return -1, query_counts()[0]

            # res = self.dnf_wegame_op("查询开盒子次数-jifenOutput", jifen_flowid, print_res=False)
            # return self.parse_jifenOutput(res, "469")

        def query_daily_lottery_times():
            return -1, query_counts()[1]

            # res = self.dnf_wegame_op("查询每日抽奖次数-jifenOutput", jifen_flowid, print_res=False)
            # return self.parse_jifenOutput(res, "470")

        # self.dnf_wegame_op("预约", "998406")
        self.dnf_wegame_op("预约后玩家是否点击过收取礼包按钮", "999238")

        # self.dnf_wegame_op("接受邀请（二期）", "998612")
        # self.dnf_wegame_op("我的邀请列表（二期）", "998708")
        self.dnf_wegame_op("抽奖（二期）", "998719")

        self.dnf_wegame_op("给巴卡尔造成伤害（二期）", "998712")
        self.dnf_wegame_op("巴卡尔宝藏（二期）", "998726")

        self.dnf_wegame_op("预约期礼包兑换（二期）", "998716")

    def check_dnf_wegame(self, roleinfo=None, roleinfo_source="道聚城所绑定的角色"):
        self.check_bind_account(
            "WeGame活动",
            get_act_url("WeGame活动"),
            activity_op_func=self.dnf_wegame_op,
            query_bind_flowid="998404",
            commit_bind_flowid="998403",
            roleinfo=roleinfo,
            roleinfo_source=roleinfo_source,
        )

    def dnf_wegame_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_wegame
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("WeGame活动"),
            **extra_params,
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

    # --------------------------------------------勇士的冒险补给--------------------------------------------
    # re: 搜 wpe类活动的接入办法为
    @try_except()
    def maoxian(self):
        show_head_line("勇士的冒险补给")
        self.show_not_ams_act_info("勇士的冒险补给")

        if not self.cfg.function_switches.get_maoxian or self.disable_most_activities():
            logger.warning("未启用领取勇士的冒险补给功能，将跳过")
            return

        # self.check_maoxian_dup()

        self.prepare_wpe_act_openid_accesstoken("勇士的冒险补给wpe")

        self.maoxian_wpe_op("勇士见面礼", 172287)

        # 冒险之路
        self.maoxian_wpe_op("每日消耗30点疲劳-签到", 172318)
        self.maoxian_wpe_op("选择 - 累计获得28枚冒险印记", 174484)
        self.maoxian_wpe_op("领取 - 累计获得28枚冒险印记", 174516)

        # 勇士回归礼
        self.maoxian_wpe_op("今日通关推荐地下城5次", 172278)
        self.maoxian_wpe_op("今日通关推荐地下城3次", 172291)
        self.maoxian_wpe_op("今日消耗疲劳30点", 172286)
        self.maoxian_wpe_op("今日在线30分钟", 172277)
        self.maoxian_wpe_op("今日登录游戏", 172283)

        # self.maoxian_op("幸运礼包", "942257")
        #
        # self.maoxian_op("登录礼包-1", "942259")
        # self.maoxian_op("登录礼包-2", "942260")
        # self.maoxian_op("登录礼包-3", "942261")
        # self.maoxian_op("登录礼包-4", "942262")
        #
        # self.maoxian_op("任务礼包-在线30", "942263")
        # self.maoxian_op("任务礼包-副本5", "942264")
        # self.maoxian_op("任务礼包-在线60", "942265")
        # self.maoxian_op("任务礼包-疲劳100", "942266")
        # self.maoxian_op("任务礼包-副本10", "942267")
        # self.maoxian_op("任务礼包-疲劳150", "942268")

    def check_maoxian_dup(self):
        self.check_bind_account(
            "勇士的冒险补给",
            get_act_url("勇士的冒险补给"),
            activity_op_func=self.maoxian_op,
            query_bind_flowid="942254",
            commit_bind_flowid="942253",
        )

    def maoxian_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_maoxian

        roleinfo = self.get_dnf_bind_role()
        qq = self.qq()
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(
            ctx,
            # note: 如果提示 非法请求，可以看看请求是不是 host变成另一个了
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            # "comm.ams.game.qq.com",
            # "group_k",
            # "bb",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("勇士的冒险补给"),
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

    def maoxian_wpe_op(self, ctx: str, flow_id: int, print_res=True, **extra_params):
        # 该类型每个请求之间需要间隔一定时长，否则会请求失败
        time.sleep(3)

        roleinfo = self.get_dnf_bind_role()

        act_id = 17463

        json_data = {
            "biz_id": "bb",
            "act_id": act_id,
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
            "data": json.dumps(
                {
                    "num": 1,
                    "ceiba_plat_id": "ios",
                    "user_attach": json.dumps({"nickName": quote(roleinfo.roleName)}),
                    "cExtData": {},
                }
            ),
        }

        return self.post(
            ctx,
            self.urls.maoxian_wpe_api,
            flowId=flow_id,
            actId=act_id,
            json=json_data,
            print_res=print_res,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
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

    # --------------------------------------------DNF周年庆登录活动--------------------------------------------
    @try_except()
    def dnf_anniversary(self):
        show_head_line("DNF周年庆登录活动")

        if now_in_range("2024-06-15 06:00:00", "2024-06-17 05:59:59") and is_daily_first_run(
            "2024_DNF周年庆登录活动_提示登录"
        ):
            async_message_box(
                (
                    "周年庆是否所有需要领奖励的号都已经登录了？如果没有的话，记得去一个个登录哦~\n"
                    # "\n"
                    # "此外在6.17到6.19期间，登录即可领一套透明天空<_<在游戏中的【从100开始的全新冒险】活动中点击领取\n"
                ),
                "周年庆登录",
                open_url=get_act_url("DNF周年庆登录活动"),
            )

        if not self.cfg.function_switches.get_dnf_anniversary or self.disable_most_activities():
            logger.warning("未启用领取DNF周年庆登录活动功能，将跳过")
            return

        # self.show_amesvr_act_info(self.dnf_anniversary_op)
        # self.check_dnf_anniversary()

        self.show_not_ams_act_info("DNF周年庆登录活动")
        self.check_dnf_anniversary_ide()

        self.dnf_anniversary_ide_op("【H5】更新后首次登录", "294601")
        self.dnf_anniversary_ide_op("【H5】周末登录礼包", "294618")

        gifts = [
            ("第一弹", "294661", "2024-06-20 16:00:00"),
            ("第二弹", "294662", "2024-06-21 00:00:00"),
            ("第三弹", "294663", "2024-06-22 00:00:00"),
            ("第四弹", "294664", "2024-06-23 00:00:00"),
            ("第五弹", "294665", "2024-06-24 00:00:00"),
        ]

        now = get_now()
        for name, flowid, can_take_time in gifts:
            if now >= parse_time(can_take_time):
                self.dnf_anniversary_ide_op(f"领取{name}周年庆礼包", flowid)
            else:
                logger.warning(f"当前未到{can_take_time}，无法领取{name}")

    def check_dnf_anniversary(self):
        self.check_bind_account(
            "DNF周年庆登录活动",
            get_act_url("DNF周年庆登录活动"),
            activity_op_func=self.dnf_anniversary_op,
            query_bind_flowid="861915",
            commit_bind_flowid="861914",
        )

    def dnf_anniversary_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_anniversary
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF周年庆登录活动"),
            **extra_params,
        )

    def check_dnf_anniversary_ide(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF周年庆登录活动",
            get_act_url("DNF周年庆登录活动"),
            activity_op_func=self.dnf_anniversary_ide_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_anniversary_ide_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_anniversary

        roleinfo = self.get_dnf_bind_role()

        bindData = {
            "iAreaId": roleinfo.serviceID,
            "sArea": roleinfo.serviceID,  # 大区号
            "sPartition": roleinfo.serviceID,
            "sPlatId": roleinfo.serviceID,
            "sRole": roleinfo.roleCode,  # 角色ID
            "sRoleName": quote_plus(quote_plus(roleinfo.roleName)),  # 角色名称
            "source": "pc",
        }

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF周年庆登录活动"),
            **{
                **bindData,
                **extra_params,
            },
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

    # --------------------------------------------拯救赛利亚--------------------------------------------
    @try_except()
    def dnf_save_sailiyam(self):
        show_head_line("拯救赛利亚")
        self.show_not_ams_act_info("拯救赛利亚")

        if not self.cfg.function_switches.get_dnf_save_sailiyam or self.disable_most_activities():
            logger.warning("未启用领取 拯救赛利亚 功能，将跳过")
            return

        self.check_dnf_save_sailiyam()

        self.dnf_save_sailiyam_op("勇士冒险礼", "247186")

        self.dnf_save_sailiyam_op("复活币-每日登录游戏", "247190")
        self.dnf_save_sailiyam_op("复活币-每日分享", "247194")
        # self.dnf_save_sailiyam_op("复活币-好友列表", "247588")
        # self.dnf_save_sailiyam_op("复活币-发送ark消息", "247589")
        # self.dnf_save_sailiyam_op("复活币-助力", "247619")

        @try_except()
        def game_1():
            res = self.dnf_save_sailiyam_op("游戏分支1-开始", "250322")
            iGameId = res["jData"]["iGameId"]
            self.dnf_save_sailiyam_op("刷新数据", "252655")
            time.sleep(5)

            # 1-成功 2-失败
            self.dnf_save_sailiyam_op("游戏分支1-结束", "250351", iSuccess=1, iGameId=iGameId)
            time.sleep(1)

            self.dnf_save_sailiyam_op("游戏分支1-领奖", "250368")
            self.dnf_save_sailiyam_op("刷新数据", "252655")
            time.sleep(3)

        @try_except()
        def game_2():
            res = self.dnf_save_sailiyam_op("游戏分支2-开始", "250382")
            iGameId = res["jData"]["iGameId"]
            self.dnf_save_sailiyam_op("刷新数据", "252655")
            time.sleep(5)

            self.dnf_save_sailiyam_op("游戏分支2-结束", "250383", sAnswer="0101", iSuccess=1, iGameId=iGameId)
            time.sleep(1)

            self.dnf_save_sailiyam_op("游戏分支2-领奖", "250393")
            self.dnf_save_sailiyam_op("刷新数据", "252655")
            time.sleep(3)

        game_1()
        game_2()

        # self.dnf_save_sailiyam_op("游戏分支3-开始", "250405")
        # self.dnf_save_sailiyam_op("游戏分支3-校验", "250407")
        # self.dnf_save_sailiyam_op("游戏分支3-领奖", "250428")

        async_message_box(
            "拯救赛丽亚的小游戏第三个游戏和第四个游戏比较麻烦，请自行在手机里完成-。-",
            f"拯救赛丽亚邀请好友_{self.cfg.name}",
            show_once=True,
            open_url=get_act_url("拯救赛利亚"),
        )
        # self.dnf_save_sailiyam_op("游戏分支4-好友列表", "251268")
        # self.dnf_save_sailiyam_op("游戏分支4-发送ark消息", "251298")
        # self.dnf_save_sailiyam_op("游戏分支4-接受召唤", "251361")
        # self.dnf_save_sailiyam_op("游戏分支4-召唤好友列表", "251512")
        self.dnf_save_sailiyam_op("游戏分支4-领奖", "251372")

        self.dnf_save_sailiyam_op("游戏终极大奖", "251373")

    def check_dnf_save_sailiyam(self, **extra_params):
        return self.ide_check_bind_account(
            "拯救赛利亚",
            get_act_url("拯救赛利亚"),
            activity_op_func=self.dnf_save_sailiyam_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_save_sailiyam_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_save_sailiyam

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("拯救赛利亚"),
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

    # --------------------------------------------DNFxSNK--------------------------------------------
    @try_except()
    def dnf_snk(self):
        show_head_line("DNFxSNK")
        self.show_not_ams_act_info("DNFxSNK")

        if not self.cfg.function_switches.get_dnf_snk or self.disable_most_activities():
            logger.warning("未启用领取 DNFxSNK 功能，将跳过")
            return

        self.check_dnf_snk()

        self.dnf_snk_op("每日登录", "277763")
        self.dnf_snk_op("每日分享", "277768")

        self.dnf_snk_op("见面礼", "277788")

        # self.dnf_snk_op("胜利成就奖励", "277794")
        # self.dnf_snk_op("失败成就奖励", "277802")
        # self.dnf_snk_op("兑换奖励", "277807")
        async_message_box(
            "联动snk的网页小游戏需要邀请好友一起玩才能对战，胜利或失败指定次数可以领取一些奖励，对局获得的硬币可以兑换红10券等东西，有兴趣的朋友请在点击确认打开的网页中自行玩",
            "DNFxSNK网页小游戏",
            show_once=True,
            open_url=get_act_url("DNFxSNK"),
        )

    def check_dnf_snk(self, **extra_params):
        return self.ide_check_bind_account(
            "DNFxSNK",
            get_act_url("DNFxSNK"),
            activity_op_func=self.dnf_snk_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_snk_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_snk

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNFxSNK"),
            **extra_params,
        )

    # --------------------------------------------DNF卡妮娜的心愿摇奖机--------------------------------------------
    @try_except()
    def dnf_kanina(self):
        show_head_line("DNF卡妮娜的心愿摇奖机")
        self.show_not_ams_act_info("DNF卡妮娜的心愿摇奖机")

        if not self.cfg.function_switches.get_dnf_kanina or self.disable_most_activities():
            logger.warning("未启用领取 DNF卡妮娜的心愿摇奖机 功能，将跳过")
            return

        self.check_dnf_kanina()

        self.dnf_kanina_op("见面礼(15天黑钻)", "296547")

        self.dnf_kanina_op("更新访问", "297056")
        self.dnf_kanina_op("跑马灯", "297036", print_res=False)

        # self.dnf_kanina_op("每日分享", "294436")

        # self.dnf_kanina_op("好友列表（阶段一）", "294510")
        # self.dnf_kanina_op("发送ark消息（阶段一）", "295009")
        # self.dnf_kanina_op("接受邀请（阶段一）", "295010")
        # self.dnf_kanina_op("开奖（阶段一）", "295012")

        # self.dnf_kanina_op("刷新任务", "295166")
        # self.dnf_kanina_op("完成心愿任务", "296093")
        # self.dnf_kanina_op("领取奖励", "296375")
        # self.dnf_kanina_op("好友列表（阶段二）", "296501")
        # self.dnf_kanina_op("发送ark消息（阶段二）", "296505")
        # self.dnf_kanina_op("接受邀请（阶段二）", "296507")

        # self.dnf_kanina_op("打开彩蛋", "296684")
        for take_cash_success_people_count in [5000, 10000, 30000]:
            self.dnf_kanina_op(f"全服提现达标奖励 - {take_cash_success_people_count}人", "296906", index=take_cash_success_people_count)
            time.sleep(5)
        # self.dnf_kanina_op("新职业角色任务", "296966")

        # self.dnf_kanina_op("好友获奖数据", "297048")
        # self.dnf_kanina_op("新增好友", "297141")
        # self.dnf_kanina_op("刷新轮次", "297443")
        # self.dnf_kanina_op("随机刷新S级别道具", "297969")

        async_message_box(
            (
                "卡妮娜摇奖机活动小助手仅领取见面礼（15天黑钻部分），后续部分实际上是拼多多砍一刀玩法，如有兴趣，请自行参与\n"
                "\n"
                "大致规则就是分为两阶段\n"
                "一阶段：抽取10次，确定奖池。而抽奖次数则需要每天分享（每天1次）和邀请他人来获得（每天2次，单个QQ最多帮一次）\n"
                "二阶段：变成抽任务，通过完成抽到的任务来获得进度值，从而兑换奖池里的东西。而这个抽任务似乎也需要拉人头？\n"
            ),
            "卡妮娜心愿摇奖机活动",
            show_once=True,
            open_url=get_act_url("DNF卡妮娜的心愿摇奖机"),
        )

    def check_dnf_kanina(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF卡妮娜的心愿摇奖机",
            get_act_url("DNF卡妮娜的心愿摇奖机"),
            activity_op_func=self.dnf_kanina_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_kanina_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_kanina

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF卡妮娜的心愿摇奖机"),
            **extra_params,
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

    # --------------------------------------------DNF预约--------------------------------------------
    @try_except()
    def dnf_reservation(self):
        show_head_line("DNF预约")
        self.show_amesvr_act_info(self.dnf_reservation_op)

        if not self.cfg.function_switches.get_dnf_reservation or self.disable_most_activities():
            logger.warning("未启用领取DNF预约功能，将跳过")
            return

        self.check_dnf_reservation()

        def query_info() -> tuple[int, int]:
            res = self.dnf_reservation_op("查询信息", "985029", print_res=False)
            raw_info = res["modRet"]["jData"]

            iFragments = int(raw_info["iFragments"])
            iTeamNum = int(raw_info["iTeamNum"])

            return iFragments, iTeamNum

        iFragments, iTeamNum = query_info()

        self.dnf_reservation_op("见面礼", "985043")
        for idx in range_from_one(4):
            if idx <= iFragments:
                logger.info(f"碎片-{idx} 已获取，跳过")
                continue

            self.dnf_reservation_op(f"获取碎片-{idx}", "986607", iNum=idx)
        self.dnf_reservation_op("灯塔礼包", "985293")
        self.dnf_reservation_op("组队奖励", "985108")

        if iTeamNum < 3:
            async_message_box(
                "嘉年华组成3人小队后可以在16号后领取到彩虹内裤装扮，有兴趣的小伙伴可以在稍后弹出的云表单中加入他人的队伍，若均已满，可在后面加上自己的队伍",
                "嘉年华组队",
                show_once=True,
                open_url="https://docs.qq.com/sheet/DYlJoSFFBblpWV3JI",
            )

    def check_dnf_reservation(self):
        self.check_bind_account(
            "DNF预约",
            get_act_url("DNF预约"),
            activity_op_func=self.dnf_reservation_op,
            query_bind_flowid="985027",
            commit_bind_flowid="985026",
        )

    def dnf_reservation_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_reservation
        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF预约"),
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

    # --------------------------------------------DNF娱乐赛--------------------------------------------
    @try_except()
    def dnf_game(self):
        show_head_line("DNF娱乐赛")
        self.show_not_ams_act_info("DNF娱乐赛")

        if not self.cfg.function_switches.get_dnf_game or self.disable_most_activities():
            logger.warning("未启用领取DNF娱乐赛功能，将跳过")
            return

        self.check_dnf_game_ide()

        vote_list: list[tuple[str, str, str, int, list[int] | list[str]]] = [
            ("惩罚饮料", "233409", "drinksId", 5, [1, 2, 3, 4, 5, 6, 7, 8]),
            ("游戏", "242670", "gameId", 3, [1, 2, 3, 4, 5]),
            ("比分", "233411", "score", 1, ["3:0", "2:1", "1:2", "0:3"]),
        ]

        for name, flow_id, param_key_name, vote_count, choice_id_list in vote_list:
            ctx = f"{name}{len(choice_id_list)}选{vote_count}"
            logger.info(f"开始投 {ctx}")
            chosen = random.sample(choice_id_list, vote_count)
            for choice_id in chosen:
                res = self.dnf_game_ide_op(f"{ctx} - {choice_id}", flow_id, **{param_key_name: choice_id})
                time.sleep(1)

                if res["sMsg"] in [f"您的投票次数已满{vote_count}次", "您已投票"]:
                    break

        if now_after("2023-11-20 12:00:00"):
            self.dnf_game_ide_op("猜对比分 红10增幅券", "233417")

        for idx in range_from_one(6):
            res = self.dnf_game_ide_op(f"{idx} 许愿池抽奖", "233412")
            if res["ret"] != 0:
                break
            time.sleep(5)

        self.dnf_game_ide_op("查询我的竞猜和投票", "233282")

    def check_dnf_game(self):
        self.check_bind_account(
            "DNF娱乐赛",
            get_act_url("DNF娱乐赛"),
            activity_op_func=self.dnf_game_op,
            query_bind_flowid="906057",
            commit_bind_flowid="906056",
        )

    def dnf_game_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_game
        return self.amesvr_request(
            ctx,
            "comm.ams.game.qq.com",
            "group_k",
            "bb",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF娱乐赛"),
            **extra_params,
        )

    def check_dnf_game_ide(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF娱乐赛",
            get_act_url("DNF娱乐赛"),
            activity_op_func=self.dnf_game_ide_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_game_ide_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_game

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF娱乐赛"),
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

        if now_after("2000-06-15 20:00:00"):
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

                self.dnf_card_flip_op(f"翻牌 - 第 {idx+1} 张牌", "848911", iNum=idx + 1)

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

    # --------------------------------------------DNF心悦wpe--------------------------------------------
    # re: 搜 wpe类活动的接入办法为
    @try_except()
    def dnf_xinyue_wpe(self):
        show_head_line("DNF心悦wpe")
        self.show_not_ams_act_info("DNF心悦wpe")

        if not self.cfg.function_switches.get_dnf_xinyue or self.disable_most_activities():
            logger.warning("未启用领取DNF心悦wpe功能，将跳过")
            return

        self.prepare_wpe_act_openid_accesstoken("DNF心悦wpe")

        async_message_box(
            (
                "心悦活动页面可参与拼团活动，如果准备购买年套，可以在心悦这个页面拼团充值，领取额外的一些蚊子腿。\n"
                "每累计充值200元，可以在活动页面开一次盲盒\n"
                "同时，也能参与到游戏内的累积充值活动\n"
                "\n"
                "有兴趣的朋友可以点确认后在弹出的活动页面中参与\n"
            ),
            "心悦拼团",
            open_url=get_act_url("DNF心悦wpe"),
            show_once=True,
        )

        self.dnf_xinyue_wpe_op("心悦VIP4-5礼包", 151021)
        self.dnf_xinyue_wpe_op("心悦VIP2-3礼包", 151020)
        self.dnf_xinyue_wpe_op("心悦VIP1礼包", 151009)
        self.dnf_xinyue_wpe_op("特邀会员礼包", 151007)

        self.dnf_xinyue_wpe_op("每日签到", 151024)
        self.dnf_xinyue_wpe_op("签到 3 天", 151025)
        self.dnf_xinyue_wpe_op("签到 5 天", 151026)
        self.dnf_xinyue_wpe_op("签到 6 天", 151027)
        self.dnf_xinyue_wpe_op("签到 12 天", 151028)

    def prepare_wpe_act_openid_accesstoken(self, ctx: str, replace_if_exists: bool = True, print_res=True):
        """获取心悦的相关登录态，并设置到类的实例变量中，供实际请求中使用"""
        if not replace_if_exists and hasattr(self, "dnf_xinyue_wpe_extra_headers"):
            openid = self.dnf_xinyue_wpe_extra_headers.get("t-openid", "")
            access_token = self.dnf_xinyue_wpe_extra_headers.get("t-access-token", "")

            # 仅在已设置的两个参数都不为空时，才尝试跳过
            if openid != "" and access_token != "":
                get_logger_func(print_res, logger.info)(
                    color("bold_cyan") + f"当前请求设置为不覆盖，而且已存在 {ctx} 所需的登录态，将跳过该流程"
                )
                return
            else:
                logger.debug(
                    f"尽管已设置心悦鉴权信息，但数据不全，将重新进行获取。dnf_xinyue_wpe_extra_headers={self.dnf_xinyue_wpe_extra_headers}"
                )

        lr = self.fetch_xinyue_login_info(f"获取 {ctx} 所需的access_token", print_res=print_res)
        self.dnf_xinyue_wpe_set_openid_accesstoken(lr.openid, lr.xinyue_access_token)

    def dnf_xinyue_wpe_set_openid_accesstoken(self, openid: str, access_token: str):
        """wpe类型的活动请求时需要这串额外的headers"""
        logger.debug(f"更新心悦鉴权信息 openid={openid} access_token={access_token}")
        self.dnf_xinyue_wpe_extra_headers = {
            "t-account-type": "qc",
            "t-mode": "true",
            "t-appid": "101478665",
            "t-openid": openid,
            "t-access-token": access_token,
        }

    def dnf_xinyue_wpe_op(self, ctx: str, flow_id: int, print_res=True, extra_data: dict | None = None, **extra_params):
        # 该类型每个请求之间需要间隔一定时长，否则会请求失败
        time.sleep(3)

        act_id = "16382"
        roleinfo = self.get_dnf_bind_role()

        if extra_data is None:
            extra_data = {}

        json_data = {
            "biz_id": "tgclub",
            "act_id": act_id,
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
            "data": json.dumps(
                {
                    "num": 1,
                    "ceiba_plat_id": "ios",
                    "user_attach": json.dumps({"nickName": quote(roleinfo.roleName)}),
                    "cExtData": {},
                    **extra_data,
                }
            ),
        }

        return self.post(
            ctx,
            self.urls.dnf_xinyue_wpe_api,
            json=json_data,
            print_res=print_res,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
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

    # --------------------------------------------神界预热--------------------------------------------
    @try_except()
    def dnf_shenjie_yure(self):
        show_head_line("神界预热")
        self.show_amesvr_act_info(self.dnf_shenjie_yure_op)

        if not self.cfg.function_switches.get_dnf_shenjie_yure or self.disable_most_activities():
            logger.warning("未启用领取神界预热活动合集功能，将跳过")
            return

        self.check_dnf_shenjie_yure()

        gifts = [
            ("2023-12-07 10:00:00", "2023-12-14 05:59:59", "997992", "登录游戏"),
            ("2023-12-14 06:00:00", "2023-12-21 05:59:59", "997996", "更新前 登录游戏"),
            ("2023-12-21 06:00:00", "2024-02-01 05:59:59", "997997", "更新前 登录游戏"),
        ]
        for start_time, end_time, flowid, name in gifts:
            if now_before(start_time):
                logger.info(f"当前时间 {get_now()} 未到 {name} 开始时间 {start_time}，将跳过")
                continue

            self.dnf_shenjie_yure_op(f"{start_time} ~ {end_time} {name} 礼包", flowid)

    def check_dnf_shenjie_yure(self):
        self.check_bind_account(
            "神界预热",
            get_act_url("神界预热"),
            activity_op_func=self.dnf_shenjie_yure_op,
            query_bind_flowid="997793",
            commit_bind_flowid="997792",
        )

    def dnf_shenjie_yure_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_shenjie_yure

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("神界预热"),
            **extra_params,
        )

    # --------------------------------------------9163补偿--------------------------------------------
    @try_except()
    def dnf_9163_apologize(self):
        show_head_line("9163补偿")
        self.show_amesvr_act_info(self.dnf_9163_apologize_op)

        if not self.cfg.function_switches.get_dnf_9163_apologize or self.disable_most_activities():
            logger.warning("未启用领取9163补偿活动合集功能，将跳过")
            return

        self.check_dnf_9163_apologize()

        self.dnf_9163_apologize_op("领取9163礼包(2w代币券+2星辰百变部件)", "1014635", u_confirm=1)

        async_message_box(
            "3.30策划针对9163事件进行了说明，并提供了补偿礼盒，具体内容为20000欢乐代币券礼盒与及星辰百变部件礼盒（2个），小助手已帮你领取，可在绑定账号的邮箱查看",
            "9163补偿",
            show_once=True,
            open_url="https://dnf.qq.com/webplat/info/news_version3/119/495/498/m21449/202403/950215.shtml",
        )

    def check_dnf_9163_apologize(self):
        self.check_bind_account(
            "9163补偿",
            get_act_url("9163补偿"),
            activity_op_func=self.dnf_9163_apologize_op,
            query_bind_flowid="1014634",
            commit_bind_flowid="1014633",
        )

    def dnf_9163_apologize_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_9163_apologize

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("9163补偿"),
            **extra_params,
        )

    # --------------------------------------------辅助函数--------------------------------------------
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
        return self.network.get(
            ctx,
            self.format(url, **params),
            pretty,
            print_res,
            is_jsonp,
            is_normal_jsonp,
            need_unquote,
            extra_cookies,
            check_fn,
            extra_headers,
            use_this_cookies,
            prefix_to_remove,
            suffix_to_remove,
        )

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
        return self.network.post(
            ctx,
            self.format(url, **params),
            data,
            json,
            pretty,
            print_res,
            is_jsonp,
            is_normal_jsonp,
            need_unquote,
            extra_cookies,
            check_fn,
            extra_headers,
            disable_retry,
            use_this_cookies,
            prefix_to_remove,
            suffix_to_remove,
        )

    def format(self, url, **params):
        endTime = datetime.datetime.now()
        startTime = endTime - datetime.timedelta(days=int(365 / 12 * 5))
        date = get_today()

        # 有值的默认值
        default_valued_params = {
            "appVersion": appVersion,
            "sVersionName": sVersionName,
            "p_tk": self.cfg.g_tk,
            "g_tk": self.cfg.g_tk,
            "sDeviceID": self.cfg.sDeviceID,
            "sDjcSign": self.cfg.get_sDjcSign(),
            "callback": jsonp_callback_flag,
            "month": self.get_month(),
            "starttime": self.getMoneyFlowTime(
                startTime.year, startTime.month, startTime.day, startTime.hour, startTime.minute, startTime.second
            ),
            "endtime": self.getMoneyFlowTime(
                endTime.year, endTime.month, endTime.day, endTime.hour, endTime.minute, endTime.second
            ),
            "sSDID": str(uuid.uuid4()).replace("-", ""),
            "uuid": uuid.uuid4(),
            "uuid4": uuid.uuid4(),
            "millseconds": getMillSecondsUnix(),
            "seconds": int(time.time()),
            "rand": random.random(),
            "date": date,
            "rand32": self.rand32(),
            "djcRequestId": f"{self.cfg.sDeviceID}-{getMillSecondsUnix()}-{random.randint(0, 999)}",
        }

        # 无值的默认值
        default_empty_params = {
            key: ""
            for key in [
                "package_id",
                "lqlevel",
                "teamid",
                "weekDay",
                "sArea",
                "serverId",
                "areaId",
                "nickName",
                "sRoleId",
                "sRoleName",
                "uin",
                "skey",
                "userId",
                "token",
                "iActionId",
                "iGoodsId",
                "sBizCode",
                "partition",
                "iZoneId",
                "platid",
                "sZoneDesc",
                "sGetterDream",
                "dzid",
                "page",
                "iPackageId",
                "isLock",
                "amsid",
                "iLbSel1",
                "num",
                "mold",
                "exNum",
                "iCard",
                "iNum",
                "actionId",
                "plat",
                "extraStr",
                "sContent",
                "sPartition",
                "sAreaName",
                "md5str",
                "ams_md5str",
                "ams_checkparam",
                "checkparam",
                "type",
                "moduleId",
                "giftId",
                "acceptId",
                "sendQQ",
                "cardType",
                "giftNum",
                "inviteId",
                "inviterName",
                "sendName",
                "invitee",
                "receiveUin",
                "receiver",
                "receiverName",
                "receiverUrl",
                "inviteUin",
                "user_area",
                "user_partition",
                "user_areaName",
                "user_roleId",
                "user_roleName",
                "user_roleLevel",
                "user_checkparam",
                "user_md5str",
                "user_sex",
                "user_platId",
                "cz",
                "dj",
                "siActivityId",
                "needADD",
                "dateInfo",
                "sId",
                "userNum",
                "index",
                "pageNow",
                "pageSize",
                "clickTime",
                "skin_id",
                "decoration_id",
                "adLevel",
                "adPower",
                "username",
                "petId",
                "fuin",
                "sCode",
                "sNickName",
                "iId",
                "sendPage",
                "hello_id",
                "prize",
                "qd",
                "iReceiveUin",
                "map1",
                "map2",
                "len",
                "itemIndex",
                "sRole",
                "loginNum",
                "level",
                "iGuestUin",
                "ukey",
                "iGiftID",
                "iInviter",
                "iPageNow",
                "iPageSize",
                "pUserId",
                "isBind",
                "iType",
                "iWork",
                "iPage",
                "sNick",
                "iMatchId",
                "iGameId",
                "iIPId",
                "iVoteId",
                "iResult",
                "personAct",
                "teamAct",
                "sRoleId",
                "sRoleName",
                "sArea",
                "sMd5str",
                "sCheckparam",
                "roleJob",
                "sAreaName",
                "sAuthInfo",
                "sActivityInfo",
                "openid",
                "param",
                "dhnums",
                "sUin",
                "pointID",
                "startPos",
                "workId",
                "isSort",
                "jobName",
                "title",
                "toUin",
                "actSign",
                "prefer",
                "card",
                "answer1",
                "answer2",
                "answer3",
                "countsInfo",
                "power",
                "appid",
                "appOpenid",
                "accessToken",
                "iAreaId",
                "iRoleId",
                "randomSeed",
                "taskId",
                "point",
                "cRand",
                "tghappid",
                "sig",
                "date_chronicle_sign_in",
                "crossTime",
                "getLv105",
                "use_fatigue",
                "dayNum",
                "iFarmland",
                "fieldId",
                "sRice",
                "exchangeId",
                "sChannel",
                "flow_id",
                "pass",
                "pass_date",
                "packageId",
                "targetId",
                "myId",
                "id",
                "bossId",
                "iCardId",
                "today",
                "anchor",
                "sNum",
                "week",
                "position",
                "packages",
                "selectNo",
                "targetQQ",
                "drinksId",
                "gameId",
                "score",
                "loginDays",
                "iSuccess",
                "sAnswer",
                "u_stage",
                "u_task_index",
                "u_stage_index",
                "u_confirm",
                "sPlatId",
                "source",
            ]
        }

        # 整合得到所有默认值
        default_params = {**default_valued_params, **default_empty_params}

        # 首先将默认参数添加进去，避免format时报错
        merged_params = {**default_params, **params}

        # # 需要url encode一下，否则如果用户配置的值中包含&等符号时，会影响后续实际逻辑
        # quoted_params = {k: quote_plus(str(v)) for k, v in merged_params.items()}

        # 将参数全部填充到url的参数中
        urlRendered = url.format(**merged_params)

        # 过滤掉没有实际赋值的参数
        return filter_unused_params_catch_exception(urlRendered)

    def get_month(self):
        now = datetime.datetime.now()
        return "%4d%02d" % (now.year, now.month)

    def getMoneyFlowTime(self, year, month, day, hour, minute, second):
        return f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}"

    def show_amesvr_act_info(self, activity_op_func):
        activity_op_func("查询活动信息", "", show_info_only=True)

    def show_idesvr_act_info(self, activity_op_func):
        activity_op_func("查询活动信息", "", show_info_only=True)

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
    ):
        if show_info_only:
            self.show_ams_act_info(iActivityId)
            return
        if get_act_info_only:
            return get_ams_act(iActivityId)

        eas_url = self.preprocess_eas_url(eas_url)

        data = self.format(
            self.urls.amesvr_raw_data,
            sServiceDepartment=sServiceDepartment,
            sServiceType=sServiceType,
            eas_url=quote_plus(eas_url),
            iActivityId=iActivityId,
            iFlowId=iFlowId,
            **data_extra_params,
        )

        if append_raw_data != "":
            data = f"{data}&{append_raw_data}"

        return self.post(
            ctx,
            self.urls.amesvr,
            data,
            amesvr_host=amesvr_host,
            sServiceDepartment=sServiceDepartment,
            sServiceType=sServiceType,
            iActivityId=iActivityId,
            sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
            print_res=print_res,
            extra_cookies=extra_cookies,
        )

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
        if show_info_only:
            self.show_ide_act_info(iActivityId)
            return None
        if get_act_info_only:
            return get_ide_act(iActivityId)

        # 当外部没有显式传入sIdeToken的时候，尝试通过活动id和flowid去查出该信息
        if sIdeToken == "" and iFlowId != "":
            act_info = get_ide_act(iActivityId)
            sIdeToken = act_info.flows[iFlowId].sIdeToken

        eas_url = self.preprocess_eas_url(eas_url)

        eas_refer = ""
        if eas_url != "":
            eas_refer = f"{eas_url}?reqid={uuid.uuid4()}&version=24"

        data = self.format(
            self.urls.ide_raw_data,
            iChartId=iFlowId,
            iSubChartId=iFlowId,
            sIdeToken=sIdeToken,
            eas_url=quote_plus(quote_plus(eas_url)),
            eas_refer=quote_plus(quote_plus(eas_refer)),
            **data_extra_params,
        )

        return self.post(
            ctx,
            self.urls.ide,
            data,
            ide_host=ide_host,
            print_res=print_res,
            extra_cookies=extra_cookies,
        )

    def preprocess_eas_url(self, eas_url: str) -> str:
        eas_url = remove_suffix(eas_url, "index.html")
        eas_url = remove_suffix(eas_url, "index_pc.html")
        eas_url = remove_suffix(eas_url, "index_new.html")
        eas_url = remove_suffix(eas_url, "index.htm")
        eas_url = remove_suffix(eas_url, "zzx.html")

        return eas_url

    def show_ams_act_info(self, iActivityId: str):
        logger.info(color("bold_green") + get_meaningful_call_point_for_log() + get_ams_act_desc(iActivityId))

    def show_ide_act_info(self, iActivityId: str):
        logger.info(color("bold_green") + get_meaningful_call_point_for_log() + get_ide_act_desc(iActivityId))

    def show_not_ams_act_info(self, act_name: str):
        logger.info(color("bold_green") + get_meaningful_call_point_for_log() + get_not_ams_act_desc(act_name))

    def make_s_milo_tag(self, iActivityId, iFlowId):
        return f"AMS-MILO-{iActivityId}-{iFlowId}-{self.uin()}-{getMillSecondsUnix()}-{self.rand6()}"

    def rand6(self):
        return "".join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=6))

    def rand32(self):
        return "".join(random.choices(string.digits + string.ascii_lowercase, k=32))

    def make_cookie(self, map: dict):
        return "; ".join([f"{k}={v}" for k, v in map.items()])

    def temporary_change_bind_and_do(
        self,
        ctx: str,
        change_bind_role_infos: list[TemporaryChangeBindRoleInfo],
        check_func: Callable,
        callback_func: Callable[[RoleInfo], bool],
        need_try_func: Callable[[RoleInfo], bool] | None = None,
    ):
        """
        callback_func: 传入参数为 将要领奖的角色信息，返回参数为 是否继续尝试下一个
        """
        total_index = len(change_bind_role_infos)
        for role_index, change_bind_role_info in enumerate(change_bind_role_infos):
            server_id, role_id = change_bind_role_info.serviceID, change_bind_role_info.roleCode

            role_info = self.query_dnf_role_info_by_serverid_and_roleid(server_id, role_id)
            server_name = dnf_server_id_to_name(server_id)
            area_info = dnf_server_id_to_area_info(server_id)

            # 复刻一份道聚城绑定角色信息，用于临时修改，同时确保不会影响到其他活动
            take_lottery_count_role_info = self.get_dnf_bind_role().clone()
            take_lottery_count_role_info.roleCode = role_id
            take_lottery_count_role_info.roleName = role_info.rolename
            take_lottery_count_role_info.serviceID = server_id
            take_lottery_count_role_info.serviceName = server_name
            take_lottery_count_role_info.areaID = area_info.v
            take_lottery_count_role_info.areaName = area_info.t

            logger.warning(
                get_meaningful_call_point_for_log()
                + f"[{role_index + 1}/{total_index}] 尝试临时切换为 {server_name} 的 {role_info.rolename} 来进行 {ctx}"
            )

            if need_try_func is not None and not need_try_func(take_lottery_count_role_info):
                logger.warning(
                    color("bold_cyan")
                    + f"设置了快速鉴别流程，判定不需要尝试 {role_info.rolename}，将跳过该角色，以加快处理"
                )
                continue

            try:
                check_func(roleinfo=take_lottery_count_role_info, roleinfo_source="临时切换的领取角色")

                continue_next = callback_func(take_lottery_count_role_info)
                if not continue_next:
                    logger.warning("本次回调返回False，将不再继续尝试其他角色")
                    break
            except Exception as e:
                logger.error(f"尝试 {role_info.rolename} 时出错了，报错如下", exc_info=e)
                continue

        logger.info("操作完毕，切换为原有角色")
        check_func()

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
        while True:
            res = activity_op_func(f"查询是否绑定-尝试自动({try_auto_bind})", query_bind_flowid, print_res=False)
            # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
            need_bind = False
            bind_reason = ""
            if len(res["modRet"]["jData"]) == 0:
                # 未绑定角色
                need_bind = True
                bind_reason = "未绑定角色"
            elif act_can_change_bind and self.common_cfg.force_sync_bind_with_djc:
                if roleinfo is None:
                    # 若未从外部传入roleinfo，则使用道聚城绑定的信息
                    roleinfo = self.get_dnf_bind_role()
                bindinfo = AmesvrUserBindInfo().auto_update_config(res["modRet"]["jData"]["data"])

                if roleinfo.serviceID != bindinfo.Farea or roleinfo.roleCode != bindinfo.FroleId:
                    current_account = (
                        f"{unquote_plus(bindinfo.FareaName)}-{unquote_plus(bindinfo.FroleName)}-{bindinfo.FroleId}"
                    )
                    djc_account = f"{roleinfo.serviceName}-{roleinfo.roleName}-{roleinfo.roleCode}"

                    need_bind = True
                    bind_reason = f"当前绑定账号({current_account})与{roleinfo_source}({djc_account})不一致"

            if need_bind:
                self.guide_to_bind_account(
                    activity_name,
                    activity_url,
                    activity_op_func=activity_op_func,
                    query_bind_flowid=query_bind_flowid,
                    commit_bind_flowid=commit_bind_flowid,
                    try_auto_bind=try_auto_bind,
                    bind_reason=bind_reason,
                    roleinfo=roleinfo,
                    roleinfo_source=roleinfo_source,
                )
            else:
                # 已经绑定
                break

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
        if (
            try_auto_bind
            and self.common_cfg.try_auto_bind_new_activity
            and activity_op_func is not None
            and commit_bind_flowid != ""
        ):
            if self.get_dnf_bind_role() is not None:
                # 若道聚城已绑定dnf角色，则尝试绑定这个角色
                if roleinfo is None:
                    # 若未从外部传入roleinfo，则使用道聚城绑定的信息
                    roleinfo = self.get_dnf_bind_role()
                checkInfo = self.get_dnf_roleinfo(roleinfo)

                logger.warning(
                    color("bold_yellow")
                    + f"活动【{activity_name}】{bind_reason}，当前配置为自动绑定模式，将尝试绑定为{roleinfo_source}({roleinfo.serviceName}-{roleinfo.roleName})"
                )
                activity_op_func(
                    "提交绑定大区",
                    commit_bind_flowid,
                    True,
                    user_area=roleinfo.serviceID,
                    user_partition=roleinfo.serviceID,
                    user_areaName=double_quote(roleinfo.serviceName),
                    user_roleId=roleinfo.roleCode,
                    user_roleName=double_quote(roleinfo.roleName),
                    user_roleLevel="100",
                    user_checkparam=double_quote(checkInfo.checkparam),
                    user_md5str=checkInfo.md5str,
                    user_sex="",
                    user_platId="",
                )
            else:
                logger.warning(
                    color("bold_yellow")
                    + f"活动【{activity_name}】{bind_reason}，当前配置为自动绑定模式，但道聚城未绑定角色，因此无法应用自动绑定，将使用手动绑定方案"
                )

            # 绑定完毕，再次检测，这次如果检测仍未绑定，则不再尝试自动绑定
            self.check_bind_account(
                activity_name,
                activity_url,
                activity_op_func,
                query_bind_flowid,
                commit_bind_flowid,
                try_auto_bind=False,
                roleinfo=roleinfo,
                roleinfo_source=roleinfo_source,
            )
        else:
            msg = (
                f"当前账号【{self.cfg.get_account_cache_key()}】{bind_reason}，且未开启自动绑定模式，请点击右下角的【确定】按钮后，在自动弹出的【{activity_name}】活动页面进行绑定，然后按任意键继续\n"
                "\n"
                "若默认浏览器打不开该页面，请自行在手机或其他浏览器打开下面的页面\n"
                f"{activity_url}\n"
                "\n"
                f"若无需该功能，可关闭小助手，然后在配置工具中【账号配置/活动开关】自行关闭【{activity_name}】功能\n"
                "\n"
                "如果该账号没有DNF角色，无法完成绑定，请在配置工具中勾选【账号配置/活动开关/各功能开关/禁用绝大部分活动】，避免每次都弹出需要绑定的窗口\n"
                "PS: 部分活动需单独关闭，可参考上面开关下方的文字说明~\n"
            )
            message_box(msg, "需绑定账号", open_url=activity_url)
            logger.info(color("bold_yellow") + "请在完成绑定后按任意键继续")
            pause()

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
        if sAuthInfo != "" and sActivityInfo != "":
            self.dnf_social_relation_permission_op(
                "更新创建用户授权信息", "108939", sAuthInfo=sAuthInfo, sActivityInfo=sActivityInfo, print_res=False
            )

        bind_config = activity_op_func(f"查询活动信息 - {activity_name}", "", get_act_info_only=True).get_bind_config()

        query_bind_res = activity_op_func("查询绑定", bind_config.query_map_id, print_res=False)

        need_bind = False
        bind_reason = ""

        if query_bind_res["jData"]["bindarea"] is None:
            # 未绑定角色
            need_bind = True
            bind_reason = "未绑定角色"
        elif self.common_cfg.force_sync_bind_with_djc:
            if roleinfo is None:
                # 若未从外部传入roleinfo，则使用道聚城绑定的信息
                roleinfo = self.get_dnf_bind_role()
            bindinfo = AmesvrUserBindInfo().auto_update_config(query_bind_res["jData"]["bindarea"])

            if roleinfo.serviceID != bindinfo.Farea or roleinfo.roleCode != bindinfo.FroleId:
                current_account = (
                    f"{unquote_plus(bindinfo.FareaName)}-{unquote_plus(bindinfo.FroleName)}-{bindinfo.FroleId}"
                )
                djc_account = f"{roleinfo.serviceName}-{roleinfo.roleName}-{roleinfo.roleCode}"

                need_bind = True
                bind_reason = f"当前绑定账号({current_account})与{roleinfo_source}({djc_account})不一致"

        if not need_bind:
            # 不需要绑定
            return

        if not self.common_cfg.try_auto_bind_new_activity:
            # 未开启自动绑定
            return

        if self.get_dnf_bind_role() is None:
            # 道聚城未绑定DNF角色
            return

        # 若道聚城已绑定dnf角色，则尝试绑定这个角色
        if roleinfo is None:
            # 若未从外部传入roleinfo，则使用道聚城绑定的信息
            roleinfo = self.get_dnf_bind_role()
        checkInfo = self.get_dnf_roleinfo(roleinfo)
        role_extra_info = self.query_dnf_role_info_by_serverid_and_roleid(roleinfo.serviceID, roleinfo.roleCode)

        logger.warning(
            color("bold_yellow")
            + f"活动【{activity_name}】{bind_reason}，当前配置为自动绑定模式，将尝试绑定为{roleinfo_source}({roleinfo.serviceName}-{roleinfo.roleName})"
        )

        activity_op_func(
            "提交绑定",
            bind_config.bind_map_id,
            sRoleId=roleinfo.roleCode,
            sRoleName=triple_quote(roleinfo.roleName),
            sArea=roleinfo.serviceID,
            sMd5str=checkInfo.md5str,
            sCheckparam=quote_plus(checkInfo.checkparam),
            roleJob=role_extra_info.forceid,
            sAreaName=triple_quote(roleinfo.serviceName),
        )

    def disable_most_activities(self):
        return self.cfg.function_switches.disable_most_activities_v2

    def get_dnf_roleinfo(self, roleinfo: RoleInfo | None = None):
        if roleinfo is None:
            roleinfo = self.get_dnf_bind_role()

        res = self.get(
            "查询角色信息",
            self.urls.get_game_role_list,
            game="dnf",
            area=roleinfo.serviceID,
            sAMSTargetAppId="",
            platid="",
            partition="",
            print_res=False,
            is_jsonp=True,
            need_unquote=False,
        )
        return AmesvrQueryRole().auto_update_config(res)

    def fetch_share_p_skey(self, ctx: str, cache_max_seconds: int = 600) -> str:
        if self.cfg.function_switches.disable_login_mode_normal:
            logger.warning(f"禁用了普通登录模式，将不会尝试获取分享用的p_skey: {ctx}")
            return ""

        return self.fetch_login_result(ctx, QQLogin.login_mode_normal, cache_max_seconds=cache_max_seconds).apps_p_skey

    def fetch_club_vip_p_skey(self, ctx: str, cache_max_seconds: int = 0) -> LoginResult:
        return self.fetch_login_result(ctx, QQLogin.login_mode_club_vip, cache_max_seconds=cache_max_seconds)

    def fetch_login_result(
        self,
        ctx: str,
        login_mode: str,
        cache_max_seconds: int = 0,
        cache_validate_func: Callable[[Any], bool] | None = None,
        print_warning=True,
    ) -> LoginResult:
        meaingful_caller = get_meaningful_call_point_for_log()

        get_logger_func(print_warning)(
            meaingful_caller
            + color("bold_green")
            + f"{self.cfg.name} 开启了 {ctx} 功能，因此需要登录活动页面来更新登录票据（skey或p_skey），请稍候~"
        )

        cache_category, cache_key = self.get_login_cache_category_and_key(login_mode)
        return with_cache(
            cache_category,
            cache_key,
            cache_miss_func=functools.partial(self.update_login_info, login_mode),
            cache_validate_func=cache_validate_func,
            cache_max_seconds=cache_max_seconds,
            cache_value_unmarshal_func=LoginResult().auto_update_config,
            cache_hit_func=lambda lr: get_logger_func(print_warning, logger.info)(
                meaingful_caller + f"使用缓存的登录信息: {lr}"
            ),
        )

    def get_login_cache_category_and_key(self, login_mode: str) -> tuple[str, str]:
        return (
            f"登录信息_{login_mode}",
            self.cfg.get_account_cache_key(),
        )

    def update_login_info(self, login_mode: str) -> LoginResult:
        logger.warning("登陆信息已过期，将重新获取")

        ql = QQLogin(self.common_cfg)
        if self.cfg.login_mode == "qr_login":
            # 扫码登录
            lr = ql.qr_login(login_mode, name=self.cfg.name, account=self.cfg.account_info.account)
        else:
            # 自动登录
            lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode, name=self.cfg.name)

        return lr

    def fetch_xinyue_login_info(self, ctx: str, print_res=True) -> LoginResult:
        if self.cfg.function_switches.disable_login_mode_xinyue:
            get_logger_func(print_res, logger.warning)(f"禁用了心悦登录模式，将不会尝试更新心悦登录信息: {ctx}")
            return LoginResult()

        self.check_xinyue_login_cache_not_duplicate()

        return self.fetch_login_result(
            ctx,
            QQLogin.login_mode_xinyue,
            cache_max_seconds=-1,
            cache_validate_func=self.is_xinyue_login_info_valid,
            print_warning=print_res,
        )

    @try_except()
    def check_xinyue_login_cache_not_duplicate(self):
        cache_category, cache_key = self.get_login_cache_category_and_key(QQLogin.login_mode_xinyue)

        db = CacheDB()
        db.with_context(cache_category).load()

        if cache_key not in db.cache:
            return

        cache_info = db.cache[cache_key]
        lr = LoginResult()
        lr.auto_update_config(cache_info.value)

        same_open_id_key_list: list[str] = []
        for k, v in db.cache.items():
            if k == cache_key:
                continue

            other_lr = LoginResult()
            other_lr.auto_update_config(v.value)
            if other_lr.openid == lr.openid:
                # 有另外一个号与本号的openid一样，大概率是使用了同一个QQ来扫码登录心悦页面，会导致后续都以该账号来操作心悦，遇到这种情况则移除它
                same_open_id_key_list.append(k)

        if len(same_open_id_key_list) == 0:
            return

        async_message_box(
            (
                "当前发现本地缓存的其他账号的心悦信息与当前账号一致，可能是都使用了同一个QQ来扫描。将移除当前QQ和这些QQ的缓存信息，稍后重新登录心悦\n"
                "\n"
                f"{cache_key}\n"
                f"{same_open_id_key_list}\n"
            ),
            "心悦登录信息重复检测",
        )
        db.cache.pop(cache_key)
        for k in same_open_id_key_list:
            db.cache.pop(k)

        db.save()

    def is_xinyue_login_info_valid(self, lr: LoginResult) -> bool:
        return self._is_openid_login_info_valid("101478665", lr.openid, lr.xinyue_access_token)

    def fetch_iwan_login_info(self, ctx) -> LoginResult:
        if self.cfg.function_switches.disable_login_mode_iwan:
            logger.warning(f"禁用了爱玩登录模式，将不会尝试更新爱玩 p_skey: {ctx}")
            return LoginResult()

        return self.fetch_login_result(
            ctx, QQLogin.login_mode_iwan, cache_max_seconds=-1, cache_validate_func=self.is_iwan_login_info_valid
        )

    def is_iwan_login_info_valid(self, lr: LoginResult) -> bool:
        return self._is_openid_login_info_valid("101489622", lr.iwan_openid, lr.iwan_access_token)

    def _is_openid_login_info_valid(self, qq_appid: str, openid: str, access_token: str) -> bool:
        if qq_appid == "" or openid == "" or access_token == "":
            return False

        self.dnf_xinyue_wpe_set_openid_accesstoken(openid, access_token)

        # {'data': {}, 'msg': 'login status verification failed: access token check failed', 'ret': 7001}
        res = self.dnf_xinyue_wpe_op("查询抽奖次数", 80507, print_res=False)
        return res["ret"] != 7001

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

    def fetch_djc_login_info(self, ctx, print_warning=True) -> LoginResult:
        self.djc_custom_cookies = ""

        if self.cfg.function_switches.disable_login_mode_djc:
            get_logger_func(print_warning)(f"禁用了道聚城登录模式，将不会尝试更新道聚城登陆信息: {ctx}")
            return LoginResult()

        def is_login_info_valid(lr: LoginResult) -> bool:
            self.djc_set_custom_cookies(lr.common_openid, lr.common_access_token)

            # {"ret": 0, "msg": "ok"...}}
            # {..."msg": "对不起，您的登录态无效！", "ret": "-990301"...}
            # {..."msg": "对不起，手Q互联登录态校验失败！", "ret": "-9908"...}
            # {..."msg": "积分余额查询失败", "ret": -53526...} note: 这个情况似乎是服务器在维护，偶尔会这样，不过返回这个的时候说明skey是正常的，等过了校验流程
            query_data = self.raw_query_balance(
                "判断道聚城鉴权信息是否过期",
                print_res=False,
            )
            return str(query_data["ret"]) not in ["-990301", "-9908"]

        lr = self.fetch_login_result(
            ctx,
            QQLogin.login_mode_djc,
            cache_max_seconds=-1,
            cache_validate_func=is_login_info_valid,
            print_warning=print_warning,
        )

        self.djc_set_custom_cookies(lr.common_openid, lr.common_access_token)

        return lr

    def djc_set_custom_cookies(self, openid: str, access_token: str):
        self.djc_custom_cookies = f"djc_appSource=android; djc_appVersion={appVersion}; acctype=qc; appid=1101958653; openid={openid}; access_token={access_token}"

    def parse_condOutput(self, res: dict, cond_id: str) -> int:
        """
        解析并返回对应的数目
        """
        info = parse_amesvr_common_info(res)
        # "sOutValue1": "e0c747b4b51392caf0c99162e69125d8:iRet:0|b1ecb3ecd311175835723e484f2d8d88:iRet:0",
        for cond_info in info.sOutValue1.split("|"):
            cid, name, val = cond_info.split(":")
            if cid == cond_id:
                return int(val)

        return 0

    def parse_jifenOutput(self, res: dict, count_id: str) -> tuple[int, int]:
        """
        解析并返回对应的总数和剩余值
        """
        info = parse_amesvr_common_info(res)
        # "sOutValue1": "239:16:4|240:8:1",
        for count_info in info.sOutValue1.split("|"):
            cid, total, remaining = count_info.split(":")
            if cid == count_id:
                return int(total), int(remaining)

        return 0, 0

    def uin(self) -> str:
        return self.cfg.account_info.uin

    def qq(self) -> str:
        return uin2qq(self.uin())

    def try_do_with_lucky_role_and_normal_role(
        self, ctx: str, check_role_func: Callable, action_callback: Callable[[RoleInfo], bool]
    ):
        if self.cfg.ark_lottery.lucky_dnf_role_id != "":
            # 尝试使用配置的幸运角色
            change_bind_role = TemporaryChangeBindRoleInfo()
            change_bind_role.serviceID = self.cfg.ark_lottery.lucky_dnf_server_id
            change_bind_role.roleCode = self.cfg.ark_lottery.lucky_dnf_role_id
            self.temporary_change_bind_and_do(ctx, [change_bind_role], check_role_func, action_callback)

        # 保底尝试普通角色领取
        check_role_func()
        action_callback(self.get_dnf_bind_role_copy())


def async_run_all_act(
    account_config: AccountConfig, common_config: CommonConfig, activity_funcs_to_run: list[tuple[str, Callable]]
):
    pool_size = len(activity_funcs_to_run)
    logger.warning(color("bold_yellow") + f"将使用{pool_size}个进程并行运行{len(activity_funcs_to_run)}个活动")
    act_pool = Pool(pool_size)
    act_pool.starmap(
        run_act,
        [(account_config, common_config, act_name, act_func.__name__) for act_name, act_func in activity_funcs_to_run],
    )


def run_act(
    account_config: AccountConfig,
    common_config: CommonConfig,
    user_buy_info: BuyInfo,
    act_name: str,
    act_func_name: str,
):
    login_retry_count = 0
    max_login_retry_count = 5
    while True:
        try:
            # 这里故意等待随机一段时间，避免某账号skey过期时，多个进程同时走到尝试更新处，无法区分先后
            time.sleep(random.random())

            djcHelper = DjcHelper(account_config, common_config, user_buy_info)
            djcHelper.fetch_pskey()
            djcHelper.check_skey_expired()
            djcHelper.get_bind_role_list(print_warning=False)

            getattr(djcHelper, act_func_name)()
            return
        except SameAccountTryLoginAtMultipleThreadsException:
            notify_same_account_try_login_at_multiple_threads(account_config.name)
        except AttributeError as e:
            ctx = f"[{login_retry_count}/{max_login_retry_count}] [{account_config.name}] {act_name}"
            logger.error("{ctx} 出错了", exc_info=e)

            # 一般是因为网络原因登录检查失败了，等待一会，最多重试若干次
            if login_retry_count >= max_login_retry_count:
                logger.warning(f"{ctx} 经过多次重试后均失败了，将跳过该活动")
                return

            wait_for(f"{ctx} 登录检查失败了，等待一会后重试", 5)
            login_retry_count += 1


def notify_same_account_try_login_at_multiple_threads(account_name: str):
    wait_for(
        color("bold_yellow")
        + f"[{account_name}] 似乎因为skey中途过期，而导致多个进程同时尝试重新登录当前账号，当前进程较迟尝试，因此先等待一段时间，等第一个进程登录完成后再重试。\n"
        + "\n"
        + color("bold_cyan")
        + "如果一直重复，请关闭当前窗口，然后在配置工具中点击【清除登录状态】按钮后再次运行~"
        + "\n",
        20,
    )


def is_new_version_ark_lottery() -> bool:
    return fake_djc_helper().is_new_version_ark_lottery()


def is_ark_lottery_enabled() -> bool:
    return fake_djc_helper().is_ark_lottery_enabled()


def get_prize_names() -> list[str]:
    return fake_djc_helper().dnf_ark_lottery_get_prize_names()


def fake_djc_helper() -> DjcHelper:
    cfg = config(force_reload_when_no_accounts=True, print_res=False)

    account_config: AccountConfig
    if len(cfg.account_configs) != 0:
        account_config = cfg.account_configs[0]
    else:
        account_config = AccountConfig()
        account_config.on_config_update({})

    return DjcHelper(account_config, cfg.common)


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


if __name__ == "__main__":
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    from main_def import check_proxy

    check_proxy(cfg)

    # ps: 小号一号是 4 + 1
    RunAll = False
    indexes = []
    indexes.extend([1])
    # indexes.extend([4 + 7])
    # indexes.extend([4 + idx for idx in range(2, 7 + 1)])
    if RunAll:
        indexes = [i + 1 for i in range(len(cfg.account_configs))]

    qq_to_djcHelper: dict[str, DjcHelper] = {}

    # 测试时仍然启用被标记为安全模式的账号，方便测试
    cfg.common.enable_in_safe_mode_accounts = True

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]

        show_head_line(f"预先获取第{idx}个账户[{account_config.name}]的skey", color("fg_bold_yellow"))

        if not account_config.is_enabled():
            logger.warning("账号被禁用，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()

        qq_to_djcHelper[djcHelper.qq()] = djcHelper

    from main_def import get_user_buy_info

    user_buy_info = get_user_buy_info(cfg.get_qq_accounts())

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]

        # 为了方便测试，特殊设置一些配置，确保正常执行
        account_config.disable_in_run_env_list = []
        account_config.function_switches.disable_login_mode_xinyue = False

        show_head_line(f"开始处理第{idx}个账户[{account_config.name}({account_config.qq()})]", color("fg_bold_yellow"))

        if not account_config.is_enabled():
            logger.warning("账号被禁用，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common, user_buy_info)

        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        # djcHelper.dnf_kol()
        djcHelper.dnf_kanina()

    pause()

