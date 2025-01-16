from __future__ import annotations

import datetime
import functools
import json
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
from const import appVersion, cached_dir, sVersionName, vscode_online_url
from dao import (
    XIN_YUE_MIN_LEVEL,
    AmesvrQueryRole,
    AmesvrUserBindInfo,
    AmsActInfo,
    BuyInfo,
    ColgBattlePassInfo,
    ColgBattlePassQueryInfo,
    ComicDataList,
    DnfChronicleMatchServerAddUserRequest,
    DnfChronicleMatchServerCommonResponse,
    DnfChronicleMatchServerRequestUserRequest,
    DnfChronicleMatchServerRequestUserResponse,
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
    IdeActInfo,
    MaJieLuoInfo,
    MobileGameGiftInfo,
    NewArkLotteryAgreeRequestCardResult,
    NewArkLotteryCardCountInfo,
    NewArkLotteryLotteryCountInfo,
    NewArkLotteryRequestCardResult,
    NewArkLotterySendCardResult,
    RoleInfo,
    ShenJieGrowUpCurStageData,
    ShenJieGrowUpInfo,
    ShenJieGrowUpStagePack,
    ShenJieGrowUpTaskData,
    SoulStoneInfo,
    SoulStoneResponse,
    TemporaryChangeBindRoleInfo,
    XiaojiangyouInfo,
    XiaojiangyouPackageInfo,
    XinYueBattleGroundWpeBindRole,
    XinYueBattleGroundWpeGetBindRoleResult,
    XinYueBgwUserInfo,
    XinYueInfo,
    XinYueMatchServerAddTeamRequest,
    XinYueMatchServerCommonResponse,
    XinYueMatchServerRequestTeamRequest,
    XinYueMatchServerRequestTeamResponse,
    XinYueMyTeamInfo,
    XinYueSummaryTeamInfo,
    XinYueTeamAwardInfo,
    XinYueTeamGroupInfo,
    parse_amesvr_common_info,
)
from data_struct import to_raw_type
from db import CacheDB, CacheInfo, DnfHelperChronicleExchangeListDB, DnfHelperChronicleUserActivityTopInfoDB, WelfareDB
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
from network import Network, check_tencent_game_common_status_code, jsonp_callback_flag
from qq_login import LoginResult, QQLogin
from server import get_match_server_api
from setting import dnf_server_id_to_area_info, dnf_server_id_to_name
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
)
from usage_count import increase_counter
from util import (
    async_message_box,
    base64_decode,
    base64_encode,
    double_quote,
    double_unquote,
    extract_between,
    filter_unused_params_catch_exception,
    format_now,
    format_time,
    get_first_exists_dict_value,
    get_logger_func,
    get_meaningful_call_point_for_log,
    get_month,
    get_now,
    get_this_thursday_of_dnf,
    get_this_week_monday_datetime,
    get_today,
    get_week,
    is_act_expired,
    json_compact,
    message_box,
    now_after,
    now_before,
    now_in_range,
    padLeftRight,
    parse_time,
    pause,
    pause_and_exit,
    post_json_to_data,
    range_from_one,
    remove_suffix,
    show_act_not_enable_warning,
    show_head_line,
    show_quick_edit_mode_tip,
    start_and_end_date_of_a_month,
    tableify,
    triple_quote,
    try_except,
    uin2qq,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
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

    local_saved_teamid_file = os.path.join(cached_dir, ".teamid_v2.{}.json")

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

                heads, colSizes = zip(
                    ("序号", 4),
                    ("活动名称", 24),
                    ("结束于", 12),
                    ("剩余天数", 8),
                    ("活动链接为", 50),
                )

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
        ]

    def payed_activities(self) -> list[tuple[str, Callable]]:
        # re: 更新新的活动时记得更新urls.py的 not_ams_activities
        # ? NOTE: 同时顺带更新 配置工具功能开关列表 act_category_to_act_desc_switch_list
        # undone: 常用过滤词 -aegis -beacon -log?sCloudApiName -.png -.jpg -.gif -.js -.css  -.ico -data:image -.mp4 -pingfore.qq.com -.mp3 -.wav -logs.game.qq.com -fx_fe_report -trace.qq.com -.woff2 -.TTF -.otf -snowflake.qq.com -vd6.l.qq.com -doGPMReport -wuji/object -thumbplayer -get_video_mark_all
        return [
            ("DNF助手编年史", self.dnf_helper_chronicle),
            ("绑定手机活动", self.dnf_bind_phone),
            ("DNF漫画预约活动", self.dnf_comic),
            ("colg其他活动", self.colg_other_act),
            ("DNF预约", self.dnf_reservation),
            ("DNF福利中心兑换", self.dnf_welfare),
            ("灵魂石的洗礼", self.soul_stone),
            ("colg每日签到", self.colg_signin),
        ]

    def expired_activities(self) -> list[tuple[str, Callable]]:
        # re: 记得过期活动全部添加完后，一个个确认下确实过期了
        # hack: 已经过期非常久且很久未再出的的活动相关信息已挪到 djc_helper_tomb.py ，需要时可前往查看
        # undone: 当这个列表下方过期很久的活动变得很多的时候，就再将部分挪到上面这个墓地中
        return [
            ("喂养删除补偿", self.weiyang_compensate),
            ("嘉年华星与心愿", self.dnf_star_and_wish),
            ("集卡", self.dnf_ark_lottery),
            ("超级会员", self.dnf_super_vip),
            ("DNF落地页活动_ide", self.dnf_luodiye_ide),
            ("回流攻坚队", self.dnf_socialize),
            ("DNF神界成长之路", self.dnf_shenjie_grow_up),
            ("DNF神界成长之路二期", self.dnf_shenjie_grow_up_v2),
            ("DNF神界成长之路三期", self.dnf_shenjie_grow_up_v3),
            ("DNF卡妮娜的心愿摇奖机", self.dnf_kanina),
            ("DNF心悦wpe", self.dnf_xinyue_wpe),
            ("WeGame活动", self.dnf_wegame),
            ("勇士的冒险补给", self.maoxian),
            ("DNF格斗大赛", self.dnf_pk),
            ("DNF周年庆登录活动", self.dnf_anniversary),
            ("DNF落地页活动_ide_dup", self.dnf_luodiye_ide_dup),
            ("DNFxSNK", self.dnf_snk),
            ("超核勇士wpe", self.dnf_chaohe_wpe),
            ("DNF年货铺", self.dnf_nianhuopu),
            ("dnf助手活动wpe", self.dnf_helper_wpe),
            ("拯救赛利亚", self.dnf_save_sailiyam),
            ("DNF马杰洛的规划", self.majieluo),
            ("神界预热", self.dnf_shenjie_yure),
            ("qq视频蚊子腿-爱玩", self.qq_video_iwan),
            ("DNF落地页活动", self.dnf_luodiye),
            ("DNF娱乐赛", self.dnf_game),
            ("dnf助手活动", self.dnf_helper),
        ]

    # --------------------------------------------道聚城--------------------------------------------
    @try_except()
    def djc_operations(self):
        show_head_line("开始道聚城相关操作")
        self.show_not_ams_act_info("道聚城")

        if not self.cfg.function_switches.get_djc:
            show_act_not_enable_warning("道聚城")
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
            show_act_not_enable_warning("心悦特权专区")
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

        # 前两周心悦战场荣耀镖局完成运镖任务并领取奖励 6 次
        take_award_count = self.query_last_two_week_xinyue_team_take_award_count()
        if take_award_count < 6:
            if print_waring:
                async_message_box(
                    (
                        f"{self.cfg.name} 前两周心悦战场荣耀镖局完成运镖任务并领取奖励次数为 {take_award_count}，少于需求的 6 次，将不会尝试自动匹配心悦队伍\n"
                        "\n"
                        "本周请自行前往心悦特权专区加入队伍并完成三次任务的条件（当日完成条件后小助手会自动帮你领取），直至连续两周满勤，之后的一周即可重新自动匹配\n"
                        "\n"
                        "PS: 这样主要是为了确保进入匹配队伍的朋友们都是长期全勤的，匹配到一起后基本都能领到每周的组队奖励\n"
                        "\n"
                        "若无需心悦自动匹配功能，可前往当前账号的配置tab，取消勾选 心悦组队/自动匹配 即可\n"
                    ),
                    "心悦战场前两周未完成 6 次任务（每周弹一次）",
                    show_once_weekly=True,
                    open_url=get_act_url("DNF地下城与勇士心悦特权专区"),
                )
            return False

        return True

    def query_last_two_week_xinyue_team_take_award_count(self) -> int:
        last_two_week_awards = self.query_last_two_week_xinyue_team_awards()

        take_count = 0
        for award in last_two_week_awards:
            # 判断是否是运镖令奖励
            # 初级运镖令奖励   4748214
            # 中级运镖令奖励   4748279
            # 高级运镖令奖励   4748280
            if award.gift_id in ["4748214", "4748279", "4748280"] or "运镖令" in award.gift_name:
                take_count += 1

        return take_count

    def query_last_two_week_xinyue_team_awards(self) -> list[XinYueTeamAwardInfo]:
        # 检查过去两周的记录
        check_weeks = 2

        # 假设过去每周每天兑换40个道具（比如装备提升礼盒），每页为10个
        page_size = 10
        # 这里最多考虑比所需周数多一周的情况下的最大页数
        max_page = 40 * 7 * (check_weeks + 1) // page_size

        # 检查的最晚时间
        time_end = get_this_week_monday_datetime()
        # 检查的最早时间
        time_start = time_end - datetime.timedelta(days=7 * check_weeks)

        check_weeks_awards = []
        for page in range_from_one(max_page):
            awards = self.query_xinyue_team_awards(page, page_size)
            if len(awards) == 0:
                break

            for award in awards:
                take_at = parse_time(award.gift_time)
                if take_at >= time_end:
                    # 跳过本周的
                    continue
                elif take_at >= time_start:
                    # 在指定周数范围内的奖励
                    check_weeks_awards.append(award)
                else:
                    # 从这开始是指定周数之前的，不必再额外处理，可以直接返回了
                    return check_weeks_awards

        return check_weeks_awards

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

    def check_xinyue_battle_ground_wpe(self) -> XinYueBattleGroundWpeBindRole | None:
        """检查心悦战场的绑定信息，并返回绑定信息"""
        # 运行期间仅尝试获取一次
        if not hasattr(self, "dnf_xinyue_wpe_bind_role"):
            # 查询心悦的绑定信息
            xy_bind_role = self.xinyue_battle_ground_wpe_query_bind_role()

            need_bind = False
            bind_reason = ""
            if xy_bind_role is None:
                # 若未绑定，则尝试使用道聚城的绑定角色进行绑定
                need_bind = True
                bind_reason = "未绑定角色"
            elif self.common_cfg.force_sync_bind_with_djc:
                # 若设定了强制同步绑定信息，则尝试同步为道聚城的角色进行绑定
                djc_roleinfo = self.get_dnf_bind_role()

                if (
                    int(djc_roleinfo.serviceID) != xy_bind_role.partition_id
                    or djc_roleinfo.roleCode != xy_bind_role.role_id
                ):
                    need_bind = True
                    bind_reason = f"绑定角色({urlsafe_base64_decode(xy_bind_role.role_name)}-{base64_decode(xy_bind_role.partition_name)}) 与 道聚城绑定角色({djc_roleinfo.roleName}-{djc_roleinfo.serviceName}) 不同，且开启了强制同步绑定角色功能"

            if need_bind:
                ok = self.xinyue_battle_ground_wpe_bind_role()
                logger.info(f"心悦战场 {bind_reason}，将使用道聚城的绑定角色，绑定角色结果={ok}")

                # 绑定完后再次尝试查询
                xy_bind_role = self.xinyue_battle_ground_wpe_query_bind_role()

            # 将查询结果保存到内存中，方便后续使用
            self.dnf_xinyue_wpe_bind_role = xy_bind_role

        return self.dnf_xinyue_wpe_bind_role

    def xinyue_battle_ground_wpe_query_bind_role(self) -> XinYueBattleGroundWpeBindRole | None:
        """查询心悦战场的绑定信息"""
        json_data = {"game_code": "dnf", "device": "pc", "scene": "tgclub_act_15488"}

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
                "partition_name": base64_encode(roleinfo.serviceName),
                "role_id": roleinfo.roleCode,
                # 网页上这里的角色名特殊处理了下，会将 + 和 / 替换成 - 和 _ ，确保用在url中也能安全，跟其保持一致
                "role_name": urlsafe_base64_encode(roleinfo.roleName),
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
            flowId=flow_id,
            actId=act_id,
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
            show_act_not_enable_warning("心悦app")
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

        # old_gpoints = self.query_gpoints()
        old_gpoints = -1

        for op in self.cfg.xinyue_app_operations:
            res = requests.post(url, bytes(op.encrypted_raw_http_body), headers=headers, timeout=10)  # type: ignore
            logger.info(f"心悦app操作：{op.name} 返回码={res.status_code}, 请求结果={res.content!r}")

        # new_gpoints = self.query_gpoints()
        new_gpoints = -1

        logger.info(
            color("bold_yellow")
            + f"兑换前G分为{old_gpoints}， 兑换后G分为{new_gpoints}，差值为{old_gpoints - new_gpoints}，请自行前往心悦app确认是否兑换成功"
        )

    # --------------------------------------------pskey相关操作--------------------------------------------

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

        # def check_by_ark_lottery() -> bool:
        #     al = QzoneActivity(self, lr)
        #     res = al.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日登陆页面", 25970, print_res=False)
        #     return res["code"] == -3000 and res["subcode"] == -4001

        # def check_by_warriors_call() -> bool:
        #     qa = QzoneActivity(self, lr)
        #     qa.fetch_dnf_warriors_call_data()
        #     res = qa.do_dnf_warriors_call(
        #         "fcg_receive_reward",
        #         "测试pskey是否过期",
        #         qa.zz().actbossRule.buyVipPrize,
        #         gameid=qa.zz().gameid,
        #         print_res=False,
        #     )
        #     return res["code"] == -3000 and res["subcode"] == -4001

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
            # check_by_warriors_call,
            # check_by_ark_lottery,
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

    # --------------------------------------------QQ空间超级会员--------------------------------------------
    # note: 适配流程如下
    #   0. 电脑chrome中设置Network conditions中的User agent为手机QQ的： Mozilla/5.0 (Linux; U; Android 5.0.2; zh-cn; X900 Build/CBXCNOP5500912251S) AppleWebKit/533.1 (KHTML, like Gecko)Version/4.0 MQQBrowser/5.4 TBS/025489 Mobile Safari/533.1 V1_AND_SQ_6.0.0_300_YYB_D QQ/6.0.0.2605 NetType/WIFI WebP/0.3.0 Pixel/1440
    #   1. 获取子活动id   chrome设置为手机qq UA后，登录活动页面 get_act_url("超级会员") ，然后在幸运勇士、勇士见面礼等按钮上右键Inspect，然后在Sources中搜索其vt-itemid(如xcubeItem_4)，
    #       在结果中双击main.bundle.js结果，点击格式化后搜索【下面这行的关键词】(其他按钮的替换为对应值），其下方的subActId的值替换到下方代码处即可
    #           default.methods.xcubeItem_4=
    #   2. 填写新链接和活动时间   在 urls.py 中，替换get_act_url("超级会员")的值为新的网页链接，并把活动时间改为最新
    #   3. 重新启用代码 将调用处从 expired_activities 移到 payed_activities
    @try_except()
    def dnf_super_vip(self):
        get_act_url("超级会员")
        show_head_line("QQ空间超级会员")
        self.show_not_ams_act_info("超级会员")

        if not self.cfg.function_switches.get_dnf_super_vip or self.disable_most_activities():
            show_act_not_enable_warning("QQ空间超级会员")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        self.fetch_pskey()
        if self.lr is None:
            return

        lucky_act_id = "120044_146f606d"
        self.qzone_act_op("幸运勇士礼包 - 当前角色", lucky_act_id)
        self.qzone_act_op(
            "幸运勇士礼包 - 集卡幸运角色",
            lucky_act_id,
            act_req_data=self.try_make_lucky_user_req_data(
                "集卡", self.cfg.ark_lottery.lucky_dnf_server_id, self.cfg.ark_lottery.lucky_dnf_role_id
            ),
        )

        self.qzone_act_op("勇士见面礼", "120045_365ef5b0")

        # self.qzone_act_op("签到", "116134_6d26254f")
        # self.qzone_act_op("累计签到1天", "116130_5fa5d050")
        # self.qzone_act_op("累计签到3天", "116131_ed9042f4")
        # self.qzone_act_op("累计签到7天", "116132_ec305918")
        # self.qzone_act_op("累计签到14天", "116133_5ffc64db")

        # https://act.qzone.qq.com/v2/vip/tx/p/51488_4bb4f04b?traceTint=tianxuan_copy
        lucky_act_id = "119256_e72df5a1"
        self.qzone_act_op("QQ会员 幸运勇士 - 当前角色", lucky_act_id)
        self.qzone_act_op(
            "QQ会员 幸运勇士 - 集卡幸运角色",
            lucky_act_id,
            act_req_data=self.try_make_lucky_user_req_data(
                "集卡", self.cfg.ark_lottery.lucky_dnf_server_id, self.cfg.ark_lottery.lucky_dnf_role_id
            ),
        )

        if not self.cfg.function_switches.disable_share and is_first_run(
            f"dnf_super_vip_{get_act_url('超级会员')}_分享_{self.uin()}"
        ):
            self.qzone_act_op(
                "分享给自己",
                "119257_dd20e826",
                act_req_data={
                    "receivers": [
                        self.qq(),
                    ]
                },
            )

        self.qzone_act_op("专属红包礼", "119258_dbd6d1c0")
        self.qzone_act_op("分享领取礼包", "119306_94a1c801")

    # --------------------------------------------QQ空间 新版 集卡--------------------------------------------

    def is_ark_lottery_enabled(self) -> bool:
        """当前生效的付费活动中是否包含集卡活动，用于判断主流程中是否需要进行自动赠送卡片以及展示集卡信息等流程"""
        enabled_payed_act_funcs = [func for name, func in self.payed_activities()]
        return self.dnf_ark_lottery in enabled_payed_act_funcs

    # note: 需要先在 https://act.qzone.qq.com/ 中选一个活动登陆后，再用浏览器抓包

    # note: 以下几个页面右键点击对应按钮即可，与上方 超级会员 【 def dnf_super_vip 】 完全一致，参照其流程即可
    ark_lottery_sub_act_id_login = "119472_fe8f704b"  # 增加抽卡次数-每日登陆游戏
    ark_lottery_sub_act_id_share = "119466_3b0a470c"  # 增加抽卡次数-每日活动分享
    ark_lottery_sub_act_id_lucky = "119467_d5d8827f"  # 增加抽卡次数-幸运勇士
    ark_lottery_sub_act_id_draw_card = "119468_9278a5d8"  # 抽卡
    ark_lottery_sub_act_id_award_1 = "120441_ec0cdd7b"  # 领取奖励-第一排
    ark_lottery_sub_act_id_award_2 = "119470_18cebaea"  # 领取奖励-第二排
    ark_lottery_sub_act_id_award_3 = "119471_a344e20e"  # 领取奖励-第三排
    ark_lottery_sub_act_id_award_all = "119474_cd12dd72"  # 领取奖励-十二张
    ark_lottery_sub_act_id_lottery = "119473_5bddcab6"  # 消耗卡片来抽奖

    # note: 清空抓包数据，按f5刷新后，搜索  QueryItems  (hack: 其实就是活动链接的 最后一部分)
    ark_lottery_packet_id_card = "51530_64c7a990"  # 查询当前卡片数目

    # note: xxx. 修改 urls.py 中的 pesudo_ark_lottery_act_id ，将其加一即可

    # note: 启用和废弃抽卡活动的流程如下
    #   1.1 在 djc_helper.py 中将 ark_lottery 的调用处从 expired_activities 移到 payed_activities
    #   1.2 在 config.toml 和 config.example.toml 中 act_id_to_cost_all_cards_and_do_lottery 中增加新集卡活动的默认开关
    #   1.3 更新 urls.py 中 not_ams_activities 中集卡活动的时间
    #
    # hack:
    #   2. 废弃
    #   2.1 在 djc_helper.py 中将 ark_lottery 的调用处从 normal_run 移到 expired_activities

    @try_except()
    def dnf_ark_lottery(self):
        get_act_url("集卡")
        show_head_line("QQ空间集卡")
        self.show_not_ams_act_info("集卡")

        if not self.cfg.function_switches.get_ark_lottery:
            show_act_not_enable_warning("QQ空间集卡")
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
        if self.common_cfg.cost_all_cards_and_do_lottery_on_last_day and self.dnf_ark_lottery_is_last_day():
            logger.info("已是最后一天，且配置在最后一天将全部卡片抽掉，故而将开始消耗卡片抽奖~")
            return True

        return self.cfg.ark_lottery.act_id_to_cost_all_cards_and_do_lottery.get(
            self.urls.pesudo_ark_lottery_act_id, False
        )

    def dnf_ark_lottery_is_last_day(self) -> bool:
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
        """赠送指定数目的某个卡片给指定QQ"""
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
        """获取卡片数目"""
        url = self.urls.qzone_activity_new_query_card.format(
            packetID=self.ark_lottery_packet_id_card,
            g_tk=getACSRFTokenForAMS(self.lr.p_skey),
        )

        res = self._qzone_act_get_op("查询卡片", url, print_res=False)

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
        """新版本集卡无法查询奖励剩余兑换次数，因此直接写死，从而可以兼容旧版本代码"""
        return {
            "第一排": 1,
            "第二排": 1,
            "第三排": 1,
            "十二张": 10,
        }

    def dnf_ark_lottery_get_prize_names(self) -> list[str]:
        return list(self.dnf_ark_lottery_get_prize_counts().keys())

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

    # --------------------------------------------DNF漫画预约活动--------------------------------------------
    @try_except()
    def dnf_comic(self):
        show_head_line("DNF漫画预约活动")
        self.show_not_ams_act_info("DNF漫画预约活动")

        if not self.cfg.function_switches.get_dnf_comic or self.disable_most_activities():
            show_act_not_enable_warning("DNF漫画预约活动")
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
            "DNF漫画预约活动",
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
            show_act_not_enable_warning("qq视频蚊子腿-爱玩")
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

    # --------------------------------------------dnf助手活动相关信息的操作--------------------------------------------
    def show_dnf_helper_info_guide(self, extra_msg="", show_message_box_once_key="", always_show_message_box=False):
        if extra_msg != "":
            logger.warning(color("fg_bold_green") + extra_msg)

        tips = "\n".join(
            [
                extra_msg,
                "",
                f"账号 {self.cfg.name} 助手token已过期或者未填写，请查看点击确认后自动弹出的在线文档，获取具体设置流程",
            ]
        )

        logger.warning("\n" + color("fg_bold_yellow") + tips)
        # 首次在对应场景时弹窗
        if always_show_message_box or (
            show_message_box_once_key != ""
            and is_first_run(self.get_show_dnf_helper_info_guide_key(show_message_box_once_key))
        ):
            async_message_box(
                tips, "助手信息获取指引", print_log=False, open_url="https://docs.qq.com/doc/DYmN0UldUbmxITkFj"
            )

    def reset_show_dnf_helper_info_guide_key(self, show_message_box_once_key: str):
        reset_first_run(self.get_show_dnf_helper_info_guide_key(show_message_box_once_key))

    def get_show_dnf_helper_info_guide_key(self, show_message_box_once_key: str) -> str:
        return f"show_dnf_helper_info_guide_{self.cfg.get_account_cache_key()}_{show_message_box_once_key}"

    # --------------------------------------------dnf助手活动(后续活动都在这个基础上改)--------------------------------------------
    # note: 接入流程说明
    #   1. 助手app分享活动页面到qq，发送到电脑
    #   2. 电脑在chrome打开链接，并将 useragent 调整为 Mozilla/5.0 (Linux; Android 9; MIX 2 Build/PKQ1.190118.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045714 Mobile Safari/537.36 GameHelper_1006/2103060508
    #   3. 过滤栏输入 -webvitals -.png -speed? -.js -.jpg -data: -analysis -eas.php -pingd? -log? -pv? -favicon.ico -performance? -whitelist? -asynccookie
    #   4. 在页面上按正常流程点击，然后通过右键/copy/copy as cURL(bash)来保存对应请求的信息
    #   5. 实现自定义的部分流程（非ams的部分）
    #
    # re: 如果同一时期有多个活动，可以去 djc_helper_tomb.py 把 dnf_helper_dup 搬回来
    @try_except()
    def dnf_helper(self):
        show_head_line("dnf助手")

        if not self.cfg.function_switches.get_dnf_helper or self.disable_most_activities():
            show_act_not_enable_warning("dnf助手活动")
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

    # --------------------------------------------dnf助手活动wpe--------------------------------------------
    # re: 搜 wpe类活动的接入办法为
    @try_except()
    def dnf_helper_wpe(self):
        show_head_line("dnf助手活动wpe")
        self.show_not_ams_act_info("dnf助手活动wpe")

        if not self.cfg.function_switches.get_dnf_helper_wpe or self.disable_most_activities():
            show_act_not_enable_warning("dnf助手活动wpe")
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
                "partition_name": base64_encode(roleinfo.serviceName),
                "role_id": roleinfo.roleCode,
                "role_name": base64_encode(roleinfo.roleName),
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
            show_act_not_enable_warning("超核勇士wpe")
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
                "partition_name": base64_encode(roleinfo.serviceName),
                "role_id": roleinfo.roleCode,
                "role_name": base64_encode(roleinfo.roleName),
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
            show_act_not_enable_warning("dnf助手编年史活动")
            return

        # 检查是否已在道聚城绑定
        if self.get_dnf_bind_role() is None:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # 为了不与其他函数名称冲突，且让函数名称短一些，将专用的流程函数写到函数内部，一些底层的挪到外面，方便其他地方查询，比如概览处
        dnf_helper_info = self.cfg.dnf_helper_info

        common_params = self.get_common_params()

        # ------ 封装通用接口 ------

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

        def dzhu_get(ctx: str, api: str, print_res=False, **extra_params) -> dict:
            return self.dzhu_get(ctx, api, common_params, print_res, **extra_params)

        def dzhu_post(ctx: str, api: str, print_res=False, **extra_params) -> dict:
            return self.dzhu_post(ctx, api, common_params, print_res, **extra_params)

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
            res = dzhu_post(
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
            raw_res = dzhu_post(
                "查询助手与QQ绑定信息",
                "getcheatguardbinding",
            )

            return DnfHelperChronicleBindInfo().auto_update_config(raw_res.get("data", {}))

        @try_except(return_val_on_except=False)
        def bind_qq() -> bool:
            current_qq = self.qq()
            raw_res = dzhu_post(
                f"{self.cfg.name} 将编年史与当前QQ({current_qq})绑定",
                "bindcheatguard",
                bindUin=current_qq,
            )

            # {"result":0,"returnCode":0,"returnMsg":""}
            return raw_res.get("returnCode", -1) == 0

        # ------ 查询各种信息 ------
        def exchange_list() -> DnfHelperChronicleExchangeList:
            res = dzhu_get("可兑换道具列表", "list/exchange")
            return DnfHelperChronicleExchangeList().auto_update_config(res)

        def basic_award_list() -> DnfHelperChronicleBasicAwardList:
            res = dzhu_get("基础奖励与搭档奖励", "list/basic")
            return DnfHelperChronicleBasicAwardList().auto_update_config(res)

        def lottery_list() -> DnfHelperChronicleLotteryList:
            res = dzhu_get("碎片抽奖奖励", "lottery/receive")
            return DnfHelperChronicleLotteryList().auto_update_config(res)

        def getUserActivityTopInfo() -> DnfHelperChronicleUserActivityTopInfo:
            res = dzhu_post("活动基础状态信息", "getUserActivityTopInfo")
            return DnfHelperChronicleUserActivityTopInfo().auto_update_config(res.get("data", {}))

        def _getUserTaskList() -> dict:
            result = dzhu_post("任务信息", "getUserTaskList")
            return result

        def getUserTaskList() -> DnfHelperChronicleUserTaskList:
            res = _getUserTaskList()
            return DnfHelperChronicleUserTaskList().auto_update_config(res.get("data", {}))

        def sign_gifts_list() -> DnfHelperChronicleSignList:
            res = dzhu_get("连续签到奖励列表", "list/sign")
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
            res = dzhu_post("领取任务经验", "doactionincrexp", actionId=actionId)

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
            res = dzhu_get(
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
            listOfBasicList: list[tuple[bool, list[DnfHelperChronicleBasicAwardInfo]]],
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
            res = dzhu_get(
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
            heads, colSizes = zip(
                ("名称", 40),
                ("兑换id", 8),
                ("所需等级", 8),
                ("领取次数", 8),
                ("消耗年史碎片", 12),
            )
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
            res = dzhu_get(
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
            res = dzhu_get(
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
            partner_name = taskInfo.get_partner_info(dnf_helper_info)

            logger.warning(
                color("fg_bold_cyan") + f"你的搭档是 {partner_name}，因接口调整，暂时无法查询到对方的等级信息~"
            )

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

    def get_millsecond_timestamps(self) -> int:
        return int(datetime.datetime.now().timestamp() * 1000)

    def append_signature_to_data(
        self,
        data: dict[str, Any],
        http_method: str,
        api_path: str,
    ):
        # 补充参数
        data["tghappid"] = "1000045"
        data["cRand"] = self.get_millsecond_timestamps()

        # 构建用于签名的请求字符串
        post_data = make_dnf_helper_signature_data(data)

        # 计算签名
        hmac_sha1_secret = "nKJH89hh@8yoHJ98y&IOhIUt9hbOh98ht"
        signature = make_dnf_helper_signature(http_method, api_path, post_data, hmac_sha1_secret)

        # 添加签名
        data["sig"] = signature
        return

    def get_api_path(self, url_template: str, **params) -> str:
        full_url = self.format(url_template, **params)
        api_path = urlparse(full_url).path

        return api_path

    def get_url_query_data(self, url_template: str, **params) -> dict[str, str]:
        full_url = self.format(url_template, **params)
        query_string = urlparse(full_url).query

        query_data = dict(parse_qsl(query_string, keep_blank_values=True))

        return query_data

    def get_common_params(self) -> dict:
        dnf_helper_info = self.cfg.dnf_helper_info
        roleinfo = self.get_dnf_bind_role()
        partition = roleinfo.serviceID
        roleid = roleinfo.roleCode

        common_params = {
            "userId": dnf_helper_info.userId,
            "sPartition": partition,
            "sRoleId": roleid,
            "uin": self.qq(),
            "toUin": self.qq(),
            "token": dnf_helper_info.token,
            "uniqueRoleId": dnf_helper_info.uniqueRoleId,
            "gameId": 1006,
            "game_code": "dnf",
            "cGameId": 1006,
        }

        return common_params

    def dzhu_get(self, ctx: str, api: str, common_params: dict, print_res=False, **extra_params) -> dict:
        data = {
            **common_params,
            **extra_params,
        }
        api_path = self.get_api_path(self.urls.dnf_helper_chronicle_wang_xinyue, api=api, **data)
        actual_query_data = self.get_url_query_data(self.urls.dnf_helper_chronicle_wang_xinyue, api=api, **data)

        self.append_signature_to_data(actual_query_data, "GET", api_path)

        res = self.get(
            ctx,
            self.urls.dnf_helper_chronicle_wang_xinyue,
            api=api,
            **{
                **data,
                **actual_query_data,
            },
            print_res=print_res,
        )
        return res

    def dzhu_post(self, ctx: str, api: str, common_params: dict, print_res=False, **extra_params) -> dict:
        data = {
            **common_params,
            **extra_params,
        }
        api_path = self.get_api_path(self.urls.dnf_helper_chronicle_yoyo, api=api)
        self.append_signature_to_data(data, "POST", api_path)

        res = self.post(
            ctx,
            self.urls.dnf_helper_chronicle_yoyo,
            api=api,
            data=post_json_to_data(data),
            print_res=print_res,
        )
        return res

    @try_except(show_exception_info=False, return_val_on_except=DnfHelperChronicleUserActivityTopInfo())
    def query_dnf_helper_chronicle_info(self) -> DnfHelperChronicleUserActivityTopInfo:
        res = self.dzhu_post("活动基础状态信息", "getUserActivityTopInfo", self.get_common_params())
        return DnfHelperChronicleUserActivityTopInfo().auto_update_config(res.get("data", {}))

    @try_except(show_exception_info=False, return_val_on_except=DnfHelperChronicleUserTaskList())
    def query_dnf_helper_chronicle_user_task_list(self) -> DnfHelperChronicleUserTaskList:
        res = self.dzhu_post("任务信息", "getUserTaskList", self.get_common_params())
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

    # --------------------------------------------DNF格斗大赛--------------------------------------------
    # re: 搜 wpe类活动的接入办法为
    @try_except()
    def dnf_pk(self):
        show_head_line("DNF格斗大赛")
        self.show_not_ams_act_info("DNF格斗大赛")

        if not self.cfg.function_switches.get_dnf_pk or self.disable_most_activities():
            show_act_not_enable_warning("DNF格斗大赛")
            return

        # self.check_dnf_pk()

        self.prepare_wpe_act_openid_accesstoken("DNF格斗大赛")

        def query_ticket_count() -> int:
            res = self.dnf_pk_wpe_op("查询抽奖次数", 196037, print_res=False)
            raw_info = json.loads(res["data"])

            # "{\"ret\":0,\"limit\":0}"
            return raw_info["limit"]

        self.dnf_pk_wpe_op("见面礼", 195914)
        self.dnf_pk_wpe_op("幸运勇士礼包", 195916)
        self.dnf_pk_wpe_op("总决赛预约礼", 195917)

        signin_flowid_list = [
            195923,
            195926,
            195928,
            195930,
            195932,
            195934,
            195936,
        ]
        for idx, flowid in enumerate(signin_flowid_list):
            res = self.dnf_pk_wpe_op(f"签到第 {idx+1} 天", flowid)
            if "今日已签到" in res["msg"]:
                logger.info(color("bold_yellow") + "今日已签到，将跳过尝试后续天数签到")
                break

            time.sleep(3)

        async_message_box(
            (
                "格斗大赛的部分奖励需要报名后才能领取，请有兴趣的朋友打开点确认后弹出的页面，在最上方登录后报名即可\n"
                "\n"
                "包括报名礼、雾隐之地通关奖励（每周一次）、雾隐之地困难模式单次奖励（按概率从三档中抽取奖励，最高是格斗大赛装扮和转职光环）"
            ),
            f"格斗大赛报名 - {self.cfg.name}",
            show_once=True,
            open_url=get_act_url("DNF格斗大赛"),
        )

        # PVE
        self.dnf_pk_wpe_op("PVE 报名礼", 195918)
        self.dnf_pk_wpe_op("雾隐之地通关", 196041)
        self.dnf_pk_wpe_op("雾隐之地困难模式通关", 196042)

        # PVP
        self.dnf_pk_wpe_op("PVP 报名礼", 195919)

        # 抽奖
        self.dnf_pk_wpe_op("每日登录游戏", 195950)
        self.dnf_pk_wpe_op("每日消耗50疲劳值", 196035)
        self.dnf_pk_wpe_op("每日在线30分钟", 196036)

        ticket = query_ticket_count()
        logger.info(color("bold_cyan") + f"当前剩余抽奖券数目为：{ticket}")
        for idx in range_from_one(ticket):
            # 搜：callJsToStart 或者点一下试试
            self.dnf_pk_wpe_op(f"[{idx}/{ticket}] 幸运夺宝", 195949)
            if idx != ticket:
                time.sleep(5)

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

    def dnf_pk_wpe_op(self, ctx: str, flow_id: int, print_res=True, **extra_params):
        # 该类型每个请求之间需要间隔一定时长，否则会请求失败
        time.sleep(3)

        roleinfo = self.get_dnf_bind_role()

        act_id = "18386"

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
                "partition_name": base64_encode(roleinfo.serviceName),
                "role_id": roleinfo.roleCode,
                "role_name": base64_encode(roleinfo.roleName),
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
            self.urls.dnf_xinyue_wpe_api,
            flowId=flow_id,
            actId=act_id,
            json=json_data,
            print_res=print_res,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
        )

    # --------------------------------------------DNF福利中心兑换--------------------------------------------
    @try_except()
    def dnf_welfare(self):
        show_head_line("DNF福利中心兑换")
        self.show_amesvr_act_info(self.dnf_welfare_op)

        if not self.cfg.function_switches.get_dnf_welfare or self.disable_most_activities():
            show_act_not_enable_warning("DNF福利中心兑换活动")
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
            "上wegame畅玩dnf享好礼",
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
            show_act_not_enable_warning("DNF马杰洛的规划活动")
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
            show_act_not_enable_warning("dnf官方论坛签到")
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
            show_act_not_enable_warning("colg每日签到")
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
        # 首页右上角 签到福利 https://bbs.colg.cn/forum-171-1.html
        show_head_line("colg其他活动")
        self.show_not_ams_act_info("colg其他活动")

        if not self.cfg.function_switches.get_colg_other_act or self.disable_most_activities():
            show_act_not_enable_warning("colg其他活动")
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

        # session.get(self.urls.colg_other_act_url, timeout=10)
        #
        # reward_list = [
        #     {
        #         "reward_bag_id": "60",
        #         "title": "累计签到3天",
        #     },
        #     {
        #         "reward_bag_id": "61",
        #         "title": "累计签到7天",
        #     },
        #     {
        #         "reward_bag_id": "62",
        #         "title": "累计签到10天",
        #     },
        #     {
        #         "reward_bag_id": "63",
        #         "title": "累计签到15天",
        #     },
        #     {
        #         "reward_bag_id": "64",
        #         "title": "累计签到21天",
        #     },
        #     {
        #         "reward_bag_id": "65",
        #         "title": "累计签到28天",
        #     },
        # ]
        # for reward in reward_list:
        #     reward_bag_id = reward["reward_bag_id"]
        #     title = reward["title"]
        #
        #     res = session.post(
        #         self.urls.colg_other_act_get_reward,
        #         data=f"aid={self.urls.colg_other_act_id}&reward_bag_id={reward_bag_id}",
        #         timeout=10,
        #     )
        #     res_json = res.json()
        #     logger.info(color("bold_green") + f"{title}，结果={res_json}")
        #
        #     # 等一会，避免请求太快
        #     time.sleep(1)
        #
        #     if "累积签到天数不足" in res_json["msg"]:
        #         logger.warning("累积天数不足，跳过尝试后续")
        #         break

        res = session.post(self.urls.colg_other_act_url, data=f"aid={self.urls.colg_other_act_id}", timeout=10)
        logger.info(color("bold_green") + f"福利签到，结果={res.json()}")

        # 5、本期限时抽奖开放时间为2024.6.13-7.31
        if now_in_range("2024-06-13 00:00:00", "2024-07-31 23:59:59"):
            res = session.post(
                self.urls.colg_other_act_lottery,
                data=f"type={self.urls.colg_other_act_type}&aid={self.urls.colg_other_act_id}",
                timeout=10,
            )
            logger.info(color("bold_green") + f"每日盲盒，结果={res.json()}")
        else:
            pass

    # --------------------------------------------小酱油周礼包和生日礼包--------------------------------------------
    @try_except()
    def xiaojiangyou(self):
        show_head_line("小酱油周礼包和生日礼包")
        self.show_not_ams_act_info("小酱油周礼包和生日礼包")

        if not self.cfg.function_switches.get_xiaojiangyou or self.disable_most_activities():
            show_act_not_enable_warning("小酱油周礼包和生日礼包")
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

    # --------------------------------------------DNF落地页活动--------------------------------------------
    @try_except()
    def dnf_luodiye(self):
        show_head_line("DNF落地页活动")
        self.show_amesvr_act_info(self.dnf_luodiye_op)

        if not self.cfg.function_switches.get_dnf_luodiye or self.disable_most_activities():
            show_act_not_enable_warning("DNF落地页活动")
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

        return self.amesvr_request(
            ctx,
            "x6m5.ams.game.qq.com",
            "group_3",
            "dnf",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF落地页活动"),
            **extra_params,
            extra_cookies=f"p_skey={p_skey}",
        )

    # --------------------------------------------DNF落地页活动_ide--------------------------------------------
    @try_except()
    def dnf_luodiye_ide(self):
        show_head_line("DNF落地页活动_ide")
        self.show_not_ams_act_info("DNF落地页活动_ide")

        if not self.cfg.function_switches.get_dnf_luodiye or self.disable_most_activities():
            show_act_not_enable_warning("DNF落地页活动_ide")
            return

        self.check_dnf_luodiye_ide()

        def query_info() -> tuple[int, int]:
            res = self.dnf_luodiye_ide_op("初始化", "343548", print_res=False)
            raw_info = res["jData"]

            # 抽奖次数
            iLottery = int(raw_info["iLottery"])

            # 累计登录天数
            iLoginTotal = int(raw_info["iLoginTotal"])

            return iLottery, iLoginTotal

        # ------------ 实际流程 --------------
        self.dnf_luodiye_ide_op("周年礼包", "343643")

        self.dnf_luodiye_ide_op("每日登录礼包", "343648")

        login_gifts_list = [
            (1, 3),
            (2, 5),
            (3, 7),
            (4, 10),
            (5, 14),
            (6, 21),
            (7, 28),
        ]
        _, iLoginTotal = query_info()
        logger.info(f"累计登录天数为 {iLoginTotal}")
        for gift_index, require_login_days in login_gifts_list:
            if iLoginTotal >= require_login_days:
                self.dnf_luodiye_ide_op(
                    f"[{gift_index}] 累计登录礼包 {require_login_days}天", "343652", iIndex=gift_index
                )
            else:
                logger.warning(f"[{gift_index}] 当前累计登录未达到{require_login_days}天，将不尝试领取该累计奖励")

        tasks = [
            ("每日任务一", "343653"),
            ("每日任务二", "343654"),
            ("每周任务一", "343655"),
            ("每周任务二", "343656"),
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
            res = self.dnf_luodiye_ide_op(f"{idx}/{iLottery} 任务抽奖礼包", "343662")
            _ = res
            # if res["ret"] == 10001:
            #     break
            time.sleep(5)

        async_message_box(
            "落地页活动页面有个拉回归的活动，拉四个可以换一个红10增幅券，有兴趣的请自行完成~(每天只能拉一个，至少需要分四天）",
            "24.11 落地页拉回归活动",
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
            show_act_not_enable_warning("DNF落地页活动_ide_dup")
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
            show_act_not_enable_warning("DNF年货铺")
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
            show_act_not_enable_warning("DNF神界成长之路")
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
            show_act_not_enable_warning("DNF神界成长之路二期")
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

    # --------------------------------------------DNF神界成长之路三期--------------------------------------------
    @try_except()
    def dnf_shenjie_grow_up_v3(self):
        show_head_line("DNF神界成长之路三期")
        self.show_not_ams_act_info("DNF神界成长之路三期")

        if not self.cfg.function_switches.get_dnf_shenjie_grow_up or self.disable_most_activities():
            show_act_not_enable_warning("DNF神界成长之路三期")
            return

        # 这个活动让用户自己去选择绑定的角色，因为关系到角色绑定的奖励领取到哪个角色上
        # self.check_dnf_shenjie_grow_up_v3()

        def query_has_bind_role() -> bool:
            bind_config = self.dnf_shenjie_grow_up_v3_op(
                "查询活动信息 - DNF神界成长之路三期", "", get_act_info_only=True
            ).get_bind_config()

            query_bind_res = self.dnf_shenjie_grow_up_v3_op("查询绑定", bind_config.query_map_id, print_res=False)

            has_bind = query_bind_res["jData"]["bindarea"] is not None

            return has_bind

        def query_info() -> ShenJieGrowUpInfo:
            res = self.dnf_shenjie_grow_up_v3_op("初始化用户及查询", "310772", print_res=False)

            info = ShenJieGrowUpInfo()
            info.auto_update_config(res["jData"]["userData"])

            return info

        @try_except()
        def take_task_rewards(curStageData: ShenJieGrowUpCurStageData, taskData: dict[str, ShenJieGrowUpTaskData]):
            task_index_to_name = {
                "1": "通关神界高级地下城1次 (不限种类)",
                "2": "通关推荐地下城20次",
                "3": "装备属性成长达成大成功",
                "4": "每周在线4小时",
            }
            # if int(curStageData.stage) >= 2:
            #     # 阶段2以后，后面俩任务条件有所变化
            #     task_index_to_name["3"] = "通关异面边界1次"
            #     task_index_to_name["4"] = "通关幽暗岛1次"

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

                        self.dnf_shenjie_grow_up_v3_op(
                            f"领取任务奖励 - {task_name}",
                            "310812",
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
                    + f"当前为本周期第 {day_index_in_cycle} 天，神界成长之路（巅峰史诗成长路线）绑定的角色尚未完成以下的任务，请在下个周四零点之前完成~\n"
                )
                tips = tips + "\n"
                tips = tips + "\n".join(not_finished_task_desc_list)
            else:
                tips = tips + f"当前为本周期第 {day_index_in_cycle} 天，本周任务均已完成\n"

            title = f"{self.cfg.name} {role_name} 成长之路 3 进度提示 当前阶段{curStageData.stage}/8 本周期已完成任务 {done_task}/{total_task}"

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
                    self.dnf_shenjie_grow_up_v3_op(
                        f"领取 阶段{stage_pack.stage} 奖励", "310779", u_stage_index=stage_pack.stage
                    )

        has_bind_role = query_has_bind_role()
        logger.info(f"DNF神界成长之路三期是否已绑定角色: {has_bind_role}")

        if not has_bind_role:
            async_message_box(
                (
                    f"当前账号 {self.cfg.name} {self.qq()} 尚未在大百变活动（巅峰史诗成长路线）中绑定角色\n"
                    "\n"
                    "请打开游戏，进入你想要绑定的角色，点击游戏右下角对应的按钮完成绑定流程\n"
                ),
                "大百变活动 第三期 未绑定",
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

        # self.dnf_shenjie_grow_up_v3_op("领取大百变", "263051")

        take_task_rewards(curStageData, taskData)

        take_stage_rewards(curStageData, allStagePack)

    def check_dnf_shenjie_grow_up_v3(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF神界成长之路三期",
            get_act_url("DNF神界成长之路三期"),
            activity_op_func=self.dnf_shenjie_grow_up_v3_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_shenjie_grow_up_v3_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_shenjie_grow_up_v3

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF神界成长之路三期"),
            **extra_params,
        )

    # --------------------------------------------绑定手机活动--------------------------------------------
    @try_except()
    def dnf_bind_phone(self):
        show_head_line("绑定手机活动")
        self.show_amesvr_act_info(self.dnf_bind_phone_op)

        if not self.cfg.function_switches.get_dnf_bind_phone or self.disable_most_activities():
            show_act_not_enable_warning("绑定手机活动")
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
            show_act_not_enable_warning("WeGame活动")
            return

        self.check_dnf_wegame_ide()

        self.dnf_wegame_ide_op("启动礼包", "302359")
        self.dnf_wegame_ide_op("幸运礼包", "302363")

        # self.dnf_wegame_ide_op("好友列表", "302415")
        # self.dnf_wegame_ide_op("发送ark消息", "302616")
        # self.dnf_wegame_ide_op("接受邀请", "302631")
        # self.dnf_wegame_ide_op("分享礼包", "303772")
        # self.dnf_wegame_ide_op("抽奖", "302670")

        self.dnf_wegame_ide_op("普通攻击", "302849")
        self.dnf_wegame_ide_op("暴击", "302998")
        self.dnf_wegame_ide_op("觉醒攻击", "303027")

        self.dnf_wegame_ide_op("每日攻击礼包", "302996")

        for progress in [10, 30, 50, 70, 100]:
            self.dnf_wegame_ide_op(f"进度 {progress}% 奖励", "303047", index=progress)

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

    def check_dnf_wegame_ide(self, **extra_params):
        return self.ide_check_bind_account(
            "WeGame活动",
            get_act_url("WeGame活动"),
            activity_op_func=self.dnf_wegame_ide_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_wegame_ide_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_wegame

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("WeGame活动"),
            **extra_params,
        )

    # --------------------------------------------勇士的冒险补给--------------------------------------------
    # re: 先抓包获取链接，然后搜 wpe类活动的接入办法为
    @try_except()
    def maoxian(self):
        show_head_line("勇士的冒险补给")
        self.show_not_ams_act_info("勇士的冒险补给")

        if not self.cfg.function_switches.get_maoxian or self.disable_most_activities():
            show_act_not_enable_warning("勇士的冒险补给")
            return

        # self.check_maoxian_dup()

        self.prepare_wpe_act_openid_accesstoken("勇士的冒险补给wpe")

        self.maoxian_wpe_op("勇士见面礼", 190505)

        # # 冒险之路
        # self.maoxian_wpe_op("每日消耗30点疲劳-签到", 172318)
        # self.maoxian_wpe_op("选择 - 累计获得28枚冒险印记", 174484)
        # self.maoxian_wpe_op("领取 - 累计获得28枚冒险印记", 174516)

        # 勇士回归礼
        self.maoxian_wpe_op("今日登录游戏", 190501)
        self.maoxian_wpe_op("今日在线30分钟", 190495)
        self.maoxian_wpe_op("今日消耗疲劳30点", 190504)
        self.maoxian_wpe_op("今日通关推荐地下城3次", 190509)
        self.maoxian_wpe_op("今日通关推荐地下城5次", 190496)

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

        act_id = 18213

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
                "partition_name": base64_encode(roleinfo.serviceName),
                "role_id": roleinfo.roleCode,
                "role_name": base64_encode(roleinfo.roleName),
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
            show_act_not_enable_warning("DNF周年庆登录活动")
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
            ("终极大礼", "294665", "2024-06-23 00:00:00"),
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

    # --------------------------------------------拯救赛利亚--------------------------------------------
    @try_except()
    def dnf_save_sailiyam(self):
        show_head_line("拯救赛利亚")
        self.show_not_ams_act_info("拯救赛利亚")

        if not self.cfg.function_switches.get_dnf_save_sailiyam or self.disable_most_activities():
            show_act_not_enable_warning("拯救赛利亚")
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

    # --------------------------------------------DNFxSNK--------------------------------------------
    @try_except()
    def dnf_snk(self):
        show_head_line("DNFxSNK")
        self.show_not_ams_act_info("DNFxSNK")

        if not self.cfg.function_switches.get_dnf_snk or self.disable_most_activities():
            show_act_not_enable_warning("DNFxSNK")
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
            show_act_not_enable_warning("DNF卡妮娜的心愿摇奖机")
            return

        self.check_dnf_kanina()

        self.dnf_kanina_op("见面礼(15天黑钻)", "322887")

        self.dnf_kanina_op("更新访问", "324614")
        self.dnf_kanina_op("跑马灯", "324613", print_res=False)

        # self.dnf_kanina_op("每日分享", "324267")
        #
        # self.dnf_kanina_op("好友列表（阶段一）", "324271")
        # self.dnf_kanina_op("发送ark（阶段一）", "324282")
        # self.dnf_kanina_op("接受邀请（阶段一）", "324285")
        # self.dnf_kanina_op("开出奖励", "324296")
        #
        # self.dnf_kanina_op("任务列表", "324327")
        # self.dnf_kanina_op("完成任务", "324335")
        # self.dnf_kanina_op("好友列表（阶段二）", "324486")
        # self.dnf_kanina_op("发送ark（阶段二）", "324492")
        # self.dnf_kanina_op("接受邀请（阶段二）", "324506")
        # self.dnf_kanina_op("领取奖励", "324528")

        # self.dnf_kanina_op("打开彩蛋", "324549")
        for idx in [0, 1, 2]:
            self.dnf_kanina_op(f"全服提现达标奖励 - {idx}", "324545", index=idx)
            time.sleep(5)

        # self.dnf_kanina_op("好友获奖记录", "324550")
        # self.dnf_kanina_op("刷新S级道具", "324559")
        # self.dnf_kanina_op("刷新轮次", "324608")
        # self.dnf_kanina_op("新增好友", "324612")
        # self.dnf_kanina_op("题目列表", "325275")
        # self.dnf_kanina_op("回答题目", "325311")

        async_message_box(
            (
                f"""
卡妮娜摇奖机活动小助手仅领取见面礼（15天黑钻部分），后续部分实际上是拼多多砍一刀玩法，如有兴趣，请按下面说明自行参与

如果你有4个回归小号（比如那种每年领周年庆代币券的号），那么你可以按下面的流程领取到50元或66QB
0. 一阶段（拉回归号）
    1. 大号登录活动页面 {get_act_url("DNF卡妮娜的心愿摇奖机")}，进来可以抽一次，同时可以获得3次抽奖励内容的机会
    2. 左下角答题可以获得两次，分享可以获得3次，剩下4次需要通过小号完成
    2. 点击右下角的扫码助力，点复制链接，获得一阶段的链接，发给自己的小号
    3. 使用4个小号分别点进去这个链接，一直进行到摇一次奖励的步骤，每次大号会获得1次添加奖池机会
    4. 前面几步凑满10次后，一直按下面的抽奖池，把奖池弄满
1. 二阶段（拉登录游戏过的回归号）
    1. 大号再次打开这个活动页面，疯狂点中间的按钮，刷新心愿名单，直到【邀请4位回归】和【邀请2位回归】都在列表里了
    点右下角的扫码助力，点复制链接，获得二阶段的链接，发给自己的小号
    2. 使用4个小号分别执行下面操作
        1. 登录游戏，选一个角色进入赛利亚房间，再随便选个其他频道跳过去，从而被认定为回流玩家
        2. 打开二阶段的链接，点击宝箱，选择【接受邀请】
    3. 执行完上述操作后，大号在页面里领取这两个心愿的奖励，得到6个进度值，然后点【50元或66QB】的那个格子，领取奖励

    PS: 不确定先把条件达成，再随机出这个任务，是否也能领取。所以最稳妥是先把这俩任务都碎出来，再操作。实在弄不出来，可以试试先弄完条件，然后一个个随出来，看看是否也可以领

 每个奖励都是达到对应列的指定进度值就可以领了，所以其他奖励如果你也想要，也可以随对应任务然后去完成


"""
            ),
            "24.9 卡妮娜心愿摇奖机活动",
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

    # --------------------------------------------DNF预约--------------------------------------------
    @try_except()
    def dnf_reservation(self):
        show_head_line("DNF预约")
        self.show_not_ams_act_info("DNF预约")

        if not self.cfg.function_switches.get_dnf_reservation or self.disable_most_activities():
            show_act_not_enable_warning("DNF预约")
            return

        self.check_dnf_reservation_ide()

        if now_in_range("2024-12-19 11:00:00", "2025-01-15 23:59:59"):
            async_message_box(
                (
                    "2024.12.19 - 2025.1.15 期间可在点确认后打开的活动页面进行预约，在1.16之后就可以领取二次觉醒装扮套装等奖励。这个预约需要自己在活动页面验证手机来完成，请自己在网页中操作下~\n"
                    "\n"
                    "为了避免有人忘记预约，本提示每周会弹一次，如已预约，可直接无视"
                ),
                "重力之泉版本预约活动 - 预约阶段",
                open_url=get_act_url("DNF预约"),
                show_once_weekly=True,
            )

        if now_in_range("2025-01-16 10:00:00", "2025-03-13 23:59:59"):
            self.dnf_reservation_ide_op("领取奖励", "355314")

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

    def check_dnf_reservation_ide(self, **extra_params):
        return self.ide_check_bind_account(
            "DNF预约",
            get_act_url("DNF预约"),
            activity_op_func=self.dnf_reservation_ide_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_reservation_ide_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_reservation

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("DNF预约"),
            **extra_params,
        )

    # --------------------------------------------DNF娱乐赛--------------------------------------------
    @try_except()
    def dnf_game(self):
        show_head_line("DNF娱乐赛")
        self.show_not_ams_act_info("DNF娱乐赛")

        if not self.cfg.function_switches.get_dnf_game or self.disable_most_activities():
            show_act_not_enable_warning("DNF娱乐赛")
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

    # --------------------------------------------DNF心悦wpe--------------------------------------------
    # re: 搜 wpe类活动的接入办法为
    @try_except()
    def dnf_xinyue_wpe(self):
        show_head_line("DNF心悦wpe")
        self.show_not_ams_act_info("DNF心悦wpe")

        if not self.cfg.function_switches.get_dnf_xinyue or self.disable_most_activities():
            show_act_not_enable_warning("DNF心悦wpe")
            return

        self.prepare_wpe_act_openid_accesstoken("DNF心悦wpe")

        def query_lottery_ticket() -> int:
            res = self.dnf_xinyue_wpe_op("查询抽奖券", 226531)
            data = json.loads(res["data"])

            remain = data["totalLeft"]

            return remain

        # 组队
        async_message_box(
            (
                "心悦活动页面可组队完成积分任务，领取抽奖券。\n"
                "\n"
                "有兴趣的朋友可以点确认后在弹出的活动页面中【金秋组队有礼】部分中与他人进行组队\n"
            ),
            "24.9 心悦组队",
            open_url=get_act_url("DNF心悦wpe"),
            show_once=True,
        )

        self.dnf_xinyue_wpe_op("任务1 每日登录DNF", 223010)
        # self.dnf_xinyue_wpe_op("任务2 每日分享活动", XXXXXX)
        self.dnf_xinyue_wpe_op("任务3 每日消耗疲劳100点", 223045)

        self.dnf_xinyue_wpe_op("积分6", 223046)
        self.dnf_xinyue_wpe_op("积分25", 223047)
        self.dnf_xinyue_wpe_op("积分55", 223048)
        self.dnf_xinyue_wpe_op("积分100", 223049)

        lottery_count = query_lottery_ticket()
        logger.info(f"当前剩余抽奖券数量为 {lottery_count}")
        for idx in range_from_one(lottery_count):
            self.dnf_xinyue_wpe_op(f"{idx}/{lottery_count} 抽奖", 223050, extra_data={"pNum": 1})

        # 每日任务
        self.dnf_xinyue_wpe_op("当日充值DNF点券达到10元", 223219)
        self.dnf_xinyue_wpe_op("通关缥缈殿书库2次", 223218)
        self.dnf_xinyue_wpe_op("在线时长>=30分钟", 223214)

        # 签到
        self.dnf_xinyue_wpe_op("每日签到（祈愿）", 223227)

        self.dnf_xinyue_wpe_op("累计签到1天", 223267)
        self.dnf_xinyue_wpe_op("累积签到3天", 223324)
        self.dnf_xinyue_wpe_op("点击激活阶段一", 223328)
        self.dnf_xinyue_wpe_op("累积签到5天", 224479)
        self.dnf_xinyue_wpe_op("累积签到7天", 223325)
        self.dnf_xinyue_wpe_op("点击激活阶段二", 223331)
        self.dnf_xinyue_wpe_op("通关觉醒之森", 223326)
        self.dnf_xinyue_wpe_op("点击激活阶段三", 223332)

        self.dnf_xinyue_wpe_op("阶段一奖励", 223340)
        self.dnf_xinyue_wpe_op("阶段二奖励", 223341)
        self.dnf_xinyue_wpe_op("阶段三奖励", 223342)

        # 等级礼
        self.dnf_xinyue_wpe_op("心悦VIP4-5礼包", 223346)
        self.dnf_xinyue_wpe_op("心悦VIP2-3礼包", 223345)
        self.dnf_xinyue_wpe_op("心悦VIP1礼包", 223344)
        self.dnf_xinyue_wpe_op("特邀会员礼包", 223343)

        # -------------- 水晶之路 幸运勇士
        # https://act.xinyue.qq.com/act/a20240903dnfCrystal/index.html
        def craystal_op(ctx: str, flow_id: int):
            return self.dnf_xinyue_wpe_op(f"水晶之路 - {ctx}", flow_id, replace_act_id="19474")

        # 水晶探索
        craystal_op("每日在线30分钟", 222946)
        craystal_op("每日消耗50疲劳", 223001)
        craystal_op("每周通关苏醒之森1次", 223002)
        craystal_op("每周通关缥缈殿书库", 223003)

        # 水晶进阶
        craystal_op("通关雾神团本", 223051)
        craystal_op("通关苏醒之森", 223087)
        craystal_op("累积签到7天", 223091)

        # 水晶奖池
        craystal_op("高级装扮兑换券", 223526)
        craystal_op("灿烂的徽章神秘礼盒", 223529)
        craystal_op("纯净的增幅书", 223231)

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

    def dnf_xinyue_wpe_op(
        self,
        ctx: str,
        flow_id: int,
        print_res=True,
        extra_data: dict | None = None,
        replace_act_id: str | None = None,
        **extra_params,
    ):
        # 该类型每个请求之间需要间隔一定时长，否则会请求失败
        time.sleep(3)

        act_id = "19479"
        if replace_act_id is not None:
            act_id = replace_act_id

        roleinfo = self.get_dnf_bind_role()

        if extra_data is None:
            extra_data = {}

        json_data = {
            "biz_id": "commercial",
            "act_id": act_id,
            "flow_id": flow_id,
            "role": {
                "game_open_id": self.qq(),
                "game_app_id": "",
                "area_id": int(roleinfo.serviceID),
                "plat_id": 2,
                "partition_id": int(roleinfo.serviceID),
                "partition_name": base64_encode(roleinfo.serviceName),
                "role_id": roleinfo.roleCode,
                "role_name": base64_encode(roleinfo.roleName),
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
            flowId=flow_id,
            actId=act_id,
            json=json_data,
            print_res=print_res,
            extra_headers=self.dnf_xinyue_wpe_extra_headers,
        )

    # --------------------------------------------神界预热--------------------------------------------
    @try_except()
    def dnf_shenjie_yure(self):
        show_head_line("神界预热")
        self.show_amesvr_act_info(self.dnf_shenjie_yure_op)

        if not self.cfg.function_switches.get_dnf_shenjie_yure or self.disable_most_activities():
            show_act_not_enable_warning("神界预热")
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

    # --------------------------------------------嘉年华星与心愿--------------------------------------------
    @try_except()
    def dnf_star_and_wish(self):
        show_head_line("嘉年华星与心愿")
        self.show_not_ams_act_info("嘉年华星与心愿")

        if not self.cfg.function_switches.get_dnf_star_and_wish or self.disable_most_activities():
            show_act_not_enable_warning("嘉年华星与心愿")
            return

        self.check_dnf_star_and_wish()

        self.dnf_star_and_wish_op("见面礼", "340356")
        self.dnf_star_and_wish_op("幸运勇士礼包", "340360")

        self.dnf_star_and_wish_op("许愿道具", "340366", iIndex=0)

        self.dnf_star_and_wish_op("登录游戏奖励", "340569")
        self.dnf_star_and_wish_op("副本通关奖励", "340571")
        # self.dnf_star_and_wish_op("助力好友", "340596")

        async_message_box(
            "复原星图部分需要自己在网页上玩小游戏，跟DNF里那个基本差不多，有兴趣的可以自己完成",
            "星与心愿 复原星团",
            open_url=get_act_url("嘉年华星与心愿"),
            show_once=True,
        )

    def check_dnf_star_and_wish(self):
        return self.ide_check_bind_account(
            "嘉年华星与心愿",
            get_act_url("嘉年华星与心愿"),
            activity_op_func=self.dnf_star_and_wish_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_star_and_wish_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.ide_iActivityId_dnf_star_and_wish

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("嘉年华星与心愿"),
            **extra_params,
        )

    # --------------------------------------------喂养删除补偿--------------------------------------------
    @try_except()
    def weiyang_compensate(self):
        show_head_line("喂养删除补偿")
        self.show_not_ams_act_info("喂养删除补偿")

        if not self.cfg.function_switches.get_weiyang_compensate or self.disable_most_activities():
            show_act_not_enable_warning("喂养删除补偿")
            return

        self.check_weiyang_compensate()

        self.weiyang_compensate_op("领取补偿", "323733")

    def check_weiyang_compensate(self, **extra_params):
        return self.ide_check_bind_account(
            "喂养删除补偿",
            get_act_url("喂养删除补偿"),
            activity_op_func=self.weiyang_compensate_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def weiyang_compensate_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_weiyang_compensate

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("喂养删除补偿"),
            **extra_params,
        )

    # --------------------------------------------回流攻坚队--------------------------------------------
    @try_except()
    def dnf_socialize(self):
        show_head_line("回流攻坚队")
        self.show_not_ams_act_info("回流攻坚队")

        if not self.cfg.function_switches.get_dnf_socialize or self.disable_most_activities():
            show_act_not_enable_warning("回流攻坚队")
            return

        self.check_dnf_socialize()

        def query_sInviteCode() -> str:
            res = self.dnf_socialize_op("初始化", "323905")
            return res["jData"]["sInviteCode"]

        sInviteCode = query_sInviteCode()
        async_message_box(
            (
                "回流攻坚队活动加入攻坚队后可以更快积攒进队，可以加入他人队伍，或者邀请他人加入你的队伍\n"
                f"你的队列邀请链接为：https://dnf.qq.com/cp/a2024socialize/indexm.html?pt=1&sCode={sInviteCode}&sName=\n"
                "(点击确认后将打开该页面)"
            ),
            "24.9 回流攻坚队__",
            open_url=f"https://dnf.qq.com/cp/a2024socialize/indexm.html?pt=1&sCode={sInviteCode}&sName=",
            show_once=True,
        )

        self.dnf_socialize_op("任务-每日登录游戏", "324911")
        self.dnf_socialize_op("任务-每日在线30分钟", "324912")
        self.dnf_socialize_op("任务-每日疲劳消耗50点", "324914")
        self.dnf_socialize_op("任务-每日通关缥缈殿书库", "324915")

        stage_gift_list = [
            (1, "100攻坚值"),
            (2, "300攻坚值"),
            (3, "500攻坚值"),
            (4, "800攻坚值"),
            (5, "1000攻坚值"),
        ]
        for giftId, stage_name in stage_gift_list:
            self.dnf_socialize_op(f"攻坚值累计奖励领取 - {stage_name}", "325419", giftId=giftId)

        exchange_gift_list = [
            # (1, 5, "扭曲的次元晶体"),
            (2, 10, "梦境原石"),
            (3, 30, "灿烂的徽章神秘礼盒"),
            (4, 50, "纯净增幅书"),
            (5, 100, "星之残像礼盒"),
        ]
        for giftId, require_points, gift_name in exchange_gift_list:
            self.dnf_socialize_op(f"个人积分兑换奖励领取 - {gift_name} - {require_points}积分", "325420", giftId=giftId)

    def check_dnf_socialize(self, **extra_params):
        return self.ide_check_bind_account(
            "回流攻坚队",
            get_act_url("回流攻坚队"),
            activity_op_func=self.dnf_socialize_op,
            sAuthInfo="",
            sActivityInfo="",
        )

    def dnf_socialize_op(
        self,
        ctx: str,
        iFlowId: str,
        print_res=True,
        **extra_params,
    ):
        iActivityId = self.urls.ide_iActivityId_dnf_socialize

        return self.ide_request(
            ctx,
            "comm.ams.game.qq.com",
            iActivityId,
            iFlowId,
            print_res,
            get_act_url("回流攻坚队"),
            **extra_params,
        )

    # --------------------------------------------灵魂石的洗礼--------------------------------------------
    @try_except()
    def soul_stone(self):
        show_head_line("灵魂石的洗礼")
        self.show_not_ams_act_info("灵魂石的洗礼")

        if not self.cfg.function_switches.get_soul_stone or self.disable_most_activities():
            show_act_not_enable_warning("灵魂石的洗礼")
            return

        if self.cfg.dnf_helper_info.token == "":
            extra_msg = "未配置dnf助手相关信息，无法进行 灵魂石的洗礼，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(
                extra_msg, show_message_box_once_key=f"dnf_helper_{get_act_url('灵魂石的洗礼')}"
            )
            return

        def query_info() -> SoulStoneInfo:
            raw_res = self.soul_stone_op(
                "获取当前状态",
                "init",
                print_res=False,
                route="activity",
                nickname=quote_plus(self.cfg.name),
                avatar=quote_plus(f"https://q.qlogo.cn/g?b=qq&nk={self.qq()}&s=100"),
            )
            res = SoulStoneResponse().auto_update_config(raw_res)

            return res.data

        info = query_info()

        # 完成任务并领取增幅次数
        for task_id, task_info in info.taskConfig.items():
            # 完成任务
            self.soul_stone_op(f"完成任务-{task_info.title}", "doTask", taskId=task_id)

            # 领取奖励
            self.soul_stone_op(
                f"领取任务奖励-{task_info.title}-{task_info.upgradeTimes}次增幅次数", "pickupTaskAward", taskId=task_id
            )

        info = query_info()
        logger.info(f"当前剩余增幅次数为 {info.remainUpgradeCount}")
        for idx in range_from_one(info.remainUpgradeCount):
            # 增幅
            self.soul_stone_op(f"第{idx}/{info.remainUpgradeCount}次增幅", "upgrade")

        info = query_info()

        # 领取增幅等级奖励
        logger.info(f"当前灵魂石增幅等级为{info.currLevel}级({info.emulatorPropTitle})")
        for idx, award in enumerate(info.upgradePropAwardConfig, start=1):
            if info.currLevel < award.level:
                logger.warning(f"等级不够，跳过领取增幅+{award.level} {award.propName}")
                continue

            if idx in info.upgradeLevelPickupStatus:
                logger.warning(f"已领取，跳过领取增幅+{award.level} {award.propName}")
                continue

            self.soul_stone_op(f"领取增幅+{award.level} {award.propName}", "pickupGift", type="1", propId=award.propId)

        # 领取增幅次数奖励
        logger.info(f"当前灵魂石增幅次数为{info.upgradedCount}")

        for idx, award in enumerate(info.upgradeCountAwardConfig, start=1):
            if info.upgradedCount < award.count:
                logger.warning(f"次数不够，跳过领取增幅 {award.count}次 {award.propName}")
                continue

            if idx in info.upgradeCountPickupStatus:
                logger.warning(f"已领取，跳过领取增幅 {award.count}次 {award.propName}")
                continue

            self.soul_stone_op(
                f"领取增幅 {award.count}次 {award.propName}", "pickupGift", type="2", propId=award.propId
            )

        if now_after("2025-01-16 00:00:00"):
            if info.rankingPickupStatus == 0:
                self.soul_stone_op("尝试领取排名奖励", "pickupGift", type="3")
            else:
                logger.warning("排名奖励已领取，跳过")

    def soul_stone_op(self, ctx: str, action: str, print_res=True, **extra_params):
        if action != "init":
            # 该类型每个请求之间间隔一定时长
            time.sleep(1)

        roleinfo = self.get_dnf_bind_role()
        dnf_helper_info = self.cfg.dnf_helper_info

        # fmt: off
        data = {
            "action": action,

            **extra_params,

            "roleId": roleinfo.roleCode,
            "userId": dnf_helper_info.userId,
            "token": dnf_helper_info.token,
            "cGameId": "1006",
        }
        # fmt: on

        res = self.post(
            ctx,
            self.urls.soul_stone_api,
            data=post_json_to_data(data),
            print_res=print_res,
        )

        if dnf_helper_info.token != "":
            # {'result': -30003, 'returnCode': -30003, 'returnMsg': 'auth verification failed'}
            show_message_box_once_key = "灵魂石的洗礼_token过期2_" + get_week()
            if res.get("returnCode", 0) == -30003:
                extra_msg = (
                    "dnf助手的登录态已过期，导致 灵魂石的洗礼 相关操作无法执行，目前需要手动更新，具体操作流程如下"
                )
                self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key=show_message_box_once_key)
                raise Exception("token过期，跳过后续尝试")
            else:
                self.reset_show_dnf_helper_info_guide_key(show_message_box_once_key)

        return res

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

        # fmt: off

        # 无值的默认值
        # ps: 这个列表改为挪到 urls.py 中进行维护，跳转过去可以查看详情
        default_empty_params = self.urls.default_empty_params

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
            "starttime": self.getMoneyFlowTime(startTime.year, startTime.month, startTime.day, startTime.hour, startTime.minute, startTime.second),
            "endtime": self.getMoneyFlowTime(endTime.year, endTime.month, endTime.day, endTime.hour, endTime.minute, endTime.second),
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
        # fmt: on

        # 参数优先级： 无值默认值 < 有值默认值 < 外部调用时传入的值
        # 整合得到所有默认值
        default_params = {**default_empty_params, **default_valued_params}

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
    ) -> dict | AmsActInfo | None:
        if show_info_only:
            self.show_ams_act_info(iActivityId)
            return None
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
        djcHelper.dnf_reservation()

    pause()
