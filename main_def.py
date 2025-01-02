from __future__ import annotations

import datetime
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import threading
import time
from multiprocessing import cpu_count, freeze_support
from typing import Callable

import requests

from alist import download_from_alist
from config import AccountConfig, CommonConfig, Config, config, load_config
from config_cloud import config_cloud, try_update_config_cloud
from const import downloads_dir
from dao import BuyInfo, BuyRecord
from db import DnfHelperChronicleUserActivityTopInfoDB, UserBuyInfoDB
from djc_helper import DjcHelper, get_prize_names, notify_same_account_try_login_at_multiple_threads, run_act
from exceptions_def import ArkLotteryTargetQQSendByRequestReachMaxCount, SameAccountTryLoginAtMultipleThreadsException
from first_run import is_daily_first_run, is_first_run, is_monthly_first_run, is_weekly_first_run
from log import asciiReset, color, logger
from notice import NoticeManager
from pool import get_pool, get_pool_size, init_pool
from qq_login import QQLogin
from server import get_pay_server_addr
from show_usage import (
    global_usage_counter_name,
    my_active_monthly_pay_usage_counter_name,
    my_auto_updater_usage_counter_name,
    my_usage_counter_name,
    this_version_global_usage_counter_name,
    this_version_my_usage_counter_name,
)
from update import check_update_on_start, get_update_info
from upload_lanzouyun import Uploader
from urls import Urls, get_not_ams_act_desc
from usage_count import get_count, increase_counter
from util import (
    MB_ICONINFORMATION,
    MiB,
    append_if_not_in,
    async_call,
    async_message_box,
    auto_updater_latest_path,
    auto_updater_path,
    bypass_proxy,
    cache_name_user_buy_info,
    change_title,
    clean_dir_to_size,
    clear_login_status,
    exists_auto_updater_dlc,
    exists_auto_updater_dlc_and_not_empty,
    exists_flag_file,
    format_now,
    format_time,
    get_act_name_and_next_expect_time_list,
    get_appdata_dir,
    get_next_regular_activity_desc,
    get_next_regular_activity_name_and_expected_datetime,
    get_now,
    get_time_since_last_update,
    is_run_in_github_action,
    is_windows,
    make_sure_dir_exists,
    md5_file,
    message_box,
    open_with_default_app,
    padLeftRight,
    parse_time,
    parse_timestamp,
    pause,
    pause_and_exit,
    printed_width,
    range_from_one,
    remove_none_from_list,
    run_from_src,
    show_act_not_enable_warning,
    show_head_line,
    show_quick_edit_mode_tip,
    sync_configs,
    tableify,
    time_less,
    try_except,
    uin2qq,
    use_by_myself,
    wait_a_while,
    with_cache,
)
from version import author, now_version, ver_time

if is_windows():
    import win32api
    import win32con


def has_any_account_in_normal_run(cfg: Config):
    for _idx, account_config in enumerate(cfg.account_configs):
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        return True
    return False


def _show_head_line(msg):
    show_head_line(msg, color("fg_bold_yellow"))


def check_djc_role_binding():
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if not has_any_account_in_normal_run(cfg):
        logger.warning("未发现任何有效的账户配置，请检查配置文件")
        pause_and_exit(-1)

    _show_head_line("启动时检查各账号是否在道聚城绑定了dnf账号和任意手游账号")

    while True:
        all_binded = True
        not_binded_accounts = []

        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            logger.warning(color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name}------------")

            # 如果配置为无法绑定道聚城，则提示将无法领取任何奖励
            if account_config.cannot_bind_dnf_v2:
                async_message_box(
                    (
                        f"账号 {account_config.name} 目前配置为 【无法在道聚城绑定dnf】，将产生下列后果：\n"
                        "1. 将跳过检查dnf角色绑定流程，在未绑定道聚城的情况下可以继续使用\n"
                        "2. 如果真的没用在道聚城中绑定dnf的角色，将导致后续流程中无法获取角色绑定信息，因此将无法完成自动绑定活动角色以及领取奖励\n"
                        "\n"
                        "这个开关主要用于小号，被风控不能注册dnf账号，但是不影响用来当抽卡等活动的工具人\n"
                        "请确定你打开这个开关的目的是这样，如果仅仅是不想领取道聚城的奖励，其他奖励想正常使用，请勿打开本开关，请单独修改【道聚城兑换】相关的配置\n"
                    ),
                    f"禁用道聚城绑定后果提示_{account_config.name}",
                    show_once=True,
                    color_name="yellow",
                )

            djcHelper = DjcHelper(account_config, cfg.common)
            if not djcHelper.check_djc_role_binding():
                all_binded = False
                not_binded_accounts.append((account_config.name, account_config.qq()))

        if all_binded:
            break
        else:
            _show_head_line("0. 以上是问题描述")

            _show_head_line("1. 解决方案")
            logger.warning(
                color("bold_cyan")
                + "请前往道聚城（未安装的话，手机上应用商城搜索 道聚城 下载安装就行）将上述提示的未绑定【dnf】或【任意手游】的账号进行绑定（就是去道聚城对应游戏页面把领奖角色给选好）"
            )

            logger.info(color("bold_cyan") + "相关账号如下:")
            heads, colSizes = zip(
                ("序号", 4),
                ("账号名", 12),
                ("QQ", 10),
            )
            logger.info(color("bold_cyan") + tableify(heads, colSizes))
            for idx, info in enumerate(not_binded_accounts):
                name, qq = info

                row = [idx + 1, name, qq]
                logger.info(color("bold_cyan") + tableify(row, colSizes))

            _show_head_line("2. 详细教程")
            logger.warning(
                color("bold_cyan")
                + (
                    "具体操作流程可以参考一下教程信息：\n"
                    "1. 使用教程/使用文档.docx 【设置领奖角色】章节和【设置道聚城手游角色】章节\n"
                    "2. 使用教程/道聚城自动化助手使用视频教程 中 DNF蚊子腿小助手4.1.1版本简要&完整视频教程 中 3:17 位置 关于绑定的介绍\n"
                )
            )

            _show_head_line("3. 跳过方式")
            logger.warning(
                color("bold_yellow")
                + (
                    "如果本账号不需要道聚城相关操作，请按下列步骤操作\n"
                    "1. 可以打开配置工具，点开对应账号的tab\n"
                    "2. 将该账号的【道聚城配置】中的【无法在道聚城绑定dnf】勾选上\n"
                    "3. 并将【完成礼包达人任务的手游名称】选择为最上方的【无】\n"
                    "4. 保存配置\n"
                    "5. 回到这个页面按任意键继续\n"
                    "\n"
                    "PS:\n"
                    "勾选【无法在道聚城绑定dnf】后将无法领取任何奖励，主要用于小号，被风控不能注册dnf账号，但是不影响用来当抽卡等活动的工具人\n"
                    "勾选【完成礼包达人任务的手游名称】后道聚城的每日手游活动将不会完成，活跃度会低于领取金宝箱所需\n"
                    "\n"
                    "由于现在道聚城没有什么可以兑换的，以前每天兑换的10个调整箱也已经挪到助手app的编年史中了，如果没有玩任何手游的话，可以放心地将手游名称设置为 无\n"
                )
            )

            _show_head_line("4. 请完成上述操作，然后按任意键再次进行检查")
            logger.warning(
                color("bold_red")
                + "如果你真的无法看懂上面到底在说什么，请加群私聊我支付宝账号进行退款，然后手动领取吧-。-"
            )
            logger.warning(
                color("bold_yellow")
                + "如果你真的无法看懂上面到底在说什么，请加群私聊我支付宝账号进行退款，然后手动领取吧-。-"
            )
            logger.warning(
                color("bold_blue")
                + "如果你真的无法看懂上面到底在说什么，请加群私聊我支付宝账号进行退款，然后手动领取吧-。-"
            )

            _show_head_line("5. 异常状态")
            logger.warning(
                color("bold_yellow")
                + "如果之前曾设置过，但最近突然开始一直弹这个，而且去道聚城app里看确实已经绑定。那么大概率是道聚城修改了接口，这种情况下，请在qq群私聊我的小号告知我，我会尽快尝试修复~"
            )
            logger.warning(
                color("bold_cyan")
                + "也可以尝试通过 配置工具/账号配置/角色绑定 来本地配置领奖角色，避免因为道聚城的改动而影响领奖"
            )
            logger.info("\n\n")
            pause()

            # 这时候重新读取一遍用户修改过后的配置文件（比如把手游设为了 无 ）
            load_config("config.toml", "config.toml.local")
            cfg = config()


def check_all_skey_and_pskey(cfg: Config, check_skey_only=False):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("启动时检查各账号skey/pskey/openid是否过期")

    QQLogin(cfg.common).check_and_download_chrome_ahead()

    if (
        cfg.common.enable_multiprocessing
        and cfg.common.enable_multiprocessing_login
        and cfg.is_all_account_auto_login()
    ):
        # 并行登陆
        logger.info(
            color("bold_yellow")
            + f"已开启多进程模式({get_pool_size()})，并检测到所有账号均使用自动登录模式，将开启并行登录模式"
        )

        get_pool().starmap(
            do_check_all_skey_and_pskey,
            [
                (_idx + 1, _idx + 1, account_config, cfg.common, check_skey_only)
                for _idx, account_config in enumerate(cfg.account_configs)
                if account_config.is_enabled()
            ],
        )

        logger.info(color("bold_green") + "并行登陆完毕，串行加载缓存的登录信息到cfg变量中")
        check_all_skey_and_pskey_silently_sync(cfg)
    else:
        # 串行登录
        qq2index: dict[str, int] = {}

        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1

            djcHelper = do_check_all_skey_and_pskey(idx, 1, account_config, cfg.common, check_skey_only)
            if djcHelper is None:
                continue

            qq = uin2qq(djcHelper.cfg.account_info.uin)
            if qq in qq2index:
                if not cfg.common.disable_clear_login_status_when_duplicate_login:
                    msg = (
                        f"第{idx}个账号的实际登录QQ {qq} 与第{qq2index[qq]}个账号的qq重复，是否重复扫描了？\n"
                        "\n"
                        "点击确认后，程序将清除本地登录记录，并退出运行。请重新运行并按顺序登录正确的账号~\n"
                        "\n"
                        "若不想启用该功能，请在 配置工具/公共配置/其他 中找到禁用重复登录时清空状态的选项，勾选上即可\n"
                    )
                    message_box(msg, "重复登录", color_name="fg_bold_red")
                    clear_login_status()
                    sys.exit(-1)
                else:
                    msg = (
                        f"第{idx}个账号的实际登录QQ {qq} 与第{qq2index[qq]}个账号的qq重复，是否重复扫描了？\n"
                        "\n"
                        "由于当前禁用了重复登录时清空状态的功能，将不会清除登录状态，仅提示告知\n"
                        "若需单独手动去清除重复登录的账号，请在.cached目录中找到重复账号对应的两个文件，形如 .saved_pskey.你的账号名字.json .saved_skey.你的账号名字.json ，将其删除后再运行即可\n"
                        "\n"
                        "若想启用该功能，请在 配置工具/公共配置/其他 中找到禁用重复登录时清空状态的选项，取消勾选即可\n"
                    )
                    async_message_box(
                        msg,
                        "账号登录串号提醒",
                    )

            qq2index[qq] = idx

    logger.info("全部账号检查完毕")


def do_check_all_skey_and_pskey(
    idx: int, window_index: int, account_config: AccountConfig, common_config: CommonConfig, check_skey_only: bool
) -> DjcHelper | None:
    while True:
        try:
            wait_a_while(idx)

            logger.warning(
                color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name})------------"
            )

            return _do_check_all_skey_and_pskey(window_index, account_config, common_config, check_skey_only)
        except SameAccountTryLoginAtMultipleThreadsException:
            notify_same_account_try_login_at_multiple_threads(account_config.name)


def check_all_skey_and_pskey_silently_sync(cfg: Config):
    for account_config in cfg.account_configs:
        _do_check_all_skey_and_pskey(1, account_config, cfg.common, False)


def _do_check_all_skey_and_pskey(
    window_index: int, account_config: AccountConfig, common_config: CommonConfig, check_skey_only: bool
) -> DjcHelper | None:
    if not account_config.is_enabled():
        # 未启用的账户的账户不走该流程
        return None

    djcHelper = DjcHelper(account_config, common_config)
    djcHelper.fetch_pskey(window_index=window_index)
    djcHelper.check_skey_expired(window_index=window_index)

    if not check_skey_only:
        djcHelper.get_bind_role_list(print_warning=False)
        # djcHelper.fetch_guanjia_openid(print_warning=False)

    return djcHelper


@try_except()
def auto_send_cards(cfg: Config):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("运行完毕自动赠送卡片")

    target_qqs = cfg.common.auto_send_card_target_qqs
    if len(target_qqs) == 0:
        logger.warning("未定义自动赠送卡片的对象QQ数组，将跳过本阶段")
        return

    # 统计各账号卡片数目
    logger.info("拉取各账号的卡片数据中，请耐心等待...")
    account_data = []
    if cfg.common.enable_multiprocessing:
        logger.info(f"已开启多进程模式({get_pool_size()})，将并行拉取数据~")
        for data in get_pool().starmap(
            query_account_ark_lottery_info,
            [
                (_idx + 1, len(cfg.account_configs), account_config, cfg.common)
                for _idx, account_config in enumerate(cfg.account_configs)
                if account_config.is_enabled()
            ],
        ):
            account_data.append(data)
    else:
        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            account_data.append(
                query_account_ark_lottery_info(idx, len(cfg.account_configs), account_config, cfg.common)
            )

    account_data = remove_none_from_list(account_data)

    qq_to_card_name_to_counts = {}
    qq_to_prize_counts = {}
    qq_to_djcHelper = {}
    for card_name_to_counts, prize_counts, djcHelper in account_data:
        qq = uin2qq(djcHelper.cfg.account_info.uin)

        qq_to_card_name_to_counts[qq] = card_name_to_counts
        qq_to_prize_counts[qq] = prize_counts
        qq_to_djcHelper[qq] = djcHelper

    # 赠送卡片
    for idx, target_qq in enumerate(target_qqs):
        if target_qq in qq_to_djcHelper:
            # 新版本里似乎没有查询接口，先随便写一个固定值
            left_times = 4 * len(cfg.account_configs)
            extra_message = "（这个数字是4*账号数，新版集卡查询不到实际数值）"

            name = qq_to_djcHelper[target_qq].cfg.name
            logger.warning(
                color("fg_bold_green")
                + f"第{idx + 1}/{len(target_qqs)}个赠送目标账号 {name}({target_qq}) 今日仍可被赠送 {left_times} 次卡片{extra_message}"
            )
            # 最多赠送目标账号今日仍可接收的卡片数
            try:
                for send_idx in range_from_one(left_times):
                    logger.info(
                        color("bold_yellow") + f"尝试第 [{send_idx}/{left_times}] 次赠送卡片给 {name}({target_qq})"
                    )
                    other_account_has_card = send_card(
                        target_qq, qq_to_card_name_to_counts, qq_to_prize_counts, qq_to_djcHelper, target_qqs
                    )
                    if not other_account_has_card:
                        logger.warning(f"第 {send_idx} 次赠送时其他账号已经没有任何卡片，跳过后续尝试")
                        break
            except ArkLotteryTargetQQSendByRequestReachMaxCount as e:
                logger.warning(
                    color("bold_yellow")
                    + f"{name}({target_qq}) 今日被赠送和通过索取来赠送均已达上限，将跳过尝试后续赠送尝试。具体结果为：{e}"
                )

            # 赠送卡片完毕后尝试领取奖励和抽奖
            djcHelper = qq_to_djcHelper[target_qq]
            lr = djcHelper.fetch_pskey()
            if lr is not None:
                logger.info("赠送完毕，尝试领取奖励和抽奖")

                # if is_new_version_ark_lottery():
                #     try_copy_cards(djcHelper)

                djcHelper.dnf_ark_lottery_take_ark_lottery_awards()
                djcHelper.dnf_ark_lottery_try_lottery_using_cards()


def try_copy_cards(djcHelper: DjcHelper):
    if not use_by_myself():
        return
    # 目前似乎可以赠送给自己，先自己测试几天
    logger.warning(color("bold_yellow") + "仅本号测试：尝试额外赠送给自己（复制卡片）")

    card_name_to_counts = djcHelper.dnf_ark_lottery_get_card_counts()
    logger.warning(color("bold_green") + f"尝试额外赠送给自己（复制卡片），最新卡片信息为：{card_name_to_counts}")

    # 尝试复制四次
    for _copy_idx in range_from_one(4):
        # 当前账号的卡牌按照卡牌数升序排列，取出其中为正数的部分来尝试进行复制卡片（赠送给自己）
        owned_card_infos = get_owned_card_infos_sort_by_count(card_name_to_counts)
        if len(owned_card_infos) == 0:
            # 没有任何卡片，不尝试复制
            break

        # 复制拥有的卡片中最少的那张
        least_card_info = owned_card_infos[0]
        card_name, card_count = least_card_info
        send_ok = djcHelper.dnf_ark_lottery_send_card(card_name, djcHelper.qq())

        name = djcHelper.cfg.name
        index = new_ark_lottery_parse_index_from_card_id(card_name)
        logger.warning(color("thin_cyan") + f"账号 {name} 尝试复制一张 {index}({card_name})，结果为 {send_ok}")

        card_name_to_counts[card_name] += 1


def get_owned_card_infos_sort_by_count(card_name_to_counts: dict[str, int]) -> list[tuple[str, int]]:
    owned_card_infos = []
    for card_name, card_count in card_name_to_counts.items():
        if card_count == 0:
            continue
        owned_card_infos.append((card_name, card_count))
    owned_card_infos.sort(key=lambda card: card[1])

    return owned_card_infos


def query_account_ark_lottery_info(
    idx: int, total_account: int, account_config: AccountConfig, common_config: CommonConfig
) -> tuple[dict[str, int], dict[str, int], DjcHelper] | None:
    djcHelper = DjcHelper(account_config, common_config)
    lr = djcHelper.fetch_pskey()
    if lr is None:
        return None

    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list(print_warning=False)

    card_name_to_counts = djcHelper.dnf_ark_lottery_get_card_counts()
    prize_counts = djcHelper.dnf_ark_lottery_get_prize_counts()

    logger.info(f"{idx:2d}/{total_account} 账号 {padLeftRight(account_config.name, 12)} 的数据拉取完毕")

    return card_name_to_counts, prize_counts, djcHelper


def send_card(
    target_qq: str,
    qq_to_card_name_to_counts: dict[str, dict[str, int]],
    qq_to_prize_counts: dict[str, dict[str, int]],
    qq_to_djcHelper: dict[str, DjcHelper],
    target_qqs: list[str],
) -> bool:
    """
    返回 是否有其他账号有可以赠送的卡片
    """

    # 检查目标账号是否有可剩余的兑换奖励次数
    has_any_left_gift = False
    for _name, count in qq_to_prize_counts[target_qq].items():
        if count > 0:
            has_any_left_gift = True
            break

    target_card_infos = []
    if has_any_left_gift:
        logger.debug("仍有可兑换奖励，将赠送目标QQ最需要的卡片")
        # 当前账号的卡牌按照卡牌数升序排列
        for card_name, card_count in qq_to_card_name_to_counts[target_qq].items():
            target_card_infos.append((card_name, card_count))
        target_card_infos.sort(key=lambda card: card[1])
    else:
        logger.debug("所有奖励都已兑换，将赠送目标QQ其他QQ最富余的卡片")
        # 统计其余账号的各卡牌总数
        merged_card_name_to_count: dict[str, int] = {}
        for _qq, card_name_to_count in qq_to_card_name_to_counts.items():
            for card_name, card_count in card_name_to_count.items():
                merged_card_name_to_count[card_name] = merged_card_name_to_count.get(card_name, 0) + card_count
        # 降序排列
        for card_name, card_count in merged_card_name_to_count.items():
            target_card_infos.append((card_name, card_count))
        target_card_infos.sort(key=lambda card: -card[1])

    # 升序遍历
    for card_name, _card_count in target_card_infos:
        # 找到任意一个拥有卡片的其他账号，让他送给目标账户。默认越靠前的号越重要，因此从后面的号开始查
        for qq, card_name_to_count in reverse_map(qq_to_card_name_to_counts):
            if qq in target_qqs:
                continue
            # 如果某账户有这个卡，则赠送该当前玩家，并结束本回合赠卡
            if card_name_to_count[card_name] > 0:
                send_ok = qq_to_djcHelper[qq].dnf_ark_lottery_send_card(
                    card_name, target_qq, target_djc_helper=qq_to_djcHelper[target_qq]
                )

                index = new_ark_lottery_parse_index_from_card_id(card_name)

                card_name_to_count[card_name] -= 1
                qq_to_card_name_to_counts[target_qq][card_name] += 1

                name = qq_to_djcHelper[qq].cfg.name
                target_name = qq_to_djcHelper[target_qq].cfg.name

                logger.warning(
                    color("fg_bold_cyan")
                    + f"账号 {name} 赠送一张 {index}({card_name}) 给 {target_name}， 结果为 {send_ok}"
                )
                return True

    return False


def new_ark_lottery_parse_index_from_card_id(card_id_str: str) -> str:
    """
    将 卡片id 转换为 坐标，如 7 -> 2-3
    """
    card_id = int(card_id_str)
    row = (card_id + 3) // 4
    col = (card_id - 1) % 4 + 1
    index = f"{row}-{col}"

    return index


def new_ark_lottery_parse_card_id_from_index(index: str) -> str:
    """
    将 坐标 转换为 卡片id，如 2-3 -> 7
    """
    row, col = index.split("-")
    return str(4 * (int(row) - 1) + int(col))


def reverse_map(map):
    kvs = list(map.items())
    kvs.reverse()
    return kvs


@try_except()
def show_lottery_status(ctx, cfg: Config, need_show_tips=False):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line(ctx)

    logger.info(get_not_ams_act_desc("集卡"))

    order_map, prizeDisplayTitles = make_ark_lottery_card_and_award_info()

    # 定义表格标题栏
    heads = []
    colSizes = []

    baseHeads = ["序号", "账号名"]
    baseColSizes = [4, 12]
    heads.extend(baseHeads)
    colSizes.extend(baseColSizes)

    card_indexes = ["1-1", "1-2", "1-3", "1-4", "2-1", "2-2", "2-3", "2-4", "3-1", "3-2", "3-3", "3-4"]
    card_width = 3
    heads.extend(card_indexes)
    colSizes.extend([card_width for i in card_indexes])

    prize_indexes = [*prizeDisplayTitles]
    heads.extend(prize_indexes)
    colSizes.extend([printed_width(name) for name in prize_indexes])

    # 获取数据
    logger.warning("开始获取数据，请耐心等待~")
    rows = []
    if cfg.common.enable_multiprocessing:
        logger.info(f"已开启多进程模式({get_pool_size()})，将并行拉取数据~")
        for row in get_pool().starmap(
            query_lottery_status,
            [
                (_idx + 1, account_config, cfg.common, card_indexes, prize_indexes, order_map)
                for _idx, account_config in enumerate(cfg.account_configs)
                if account_config.is_enabled()
            ],
        ):
            rows.append(row)
    else:
        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            rows.append(query_lottery_status(idx, account_config, cfg.common, card_indexes, prize_indexes, order_map))

    rows = remove_none_from_list(rows)

    # 计算概览
    summaryCols = [
        1,
        "总计",
        *[0 for card in card_indexes],
        *[count_with_color(0, "bold_green", show_width=printed_width(prize_index)) for prize_index in prize_indexes],
    ]
    for row in rows:
        summaryCols[0] += 1
        for i in range(2, 2 + 12):
            summaryCols[i] += row[i]

    for cardIdx in range(len(card_indexes)):
        idx = len(baseHeads) + cardIdx
        summaryCols[idx] = colored_count(
            len(cfg.account_configs), summaryCols[idx], cfg.common.ark_lottery_summary_show_color or "fg_thin_cyan"
        )

    # 计算可以开启抽奖卡片的账号
    accounts_that_should_enable_cost_card_to_lottery = []
    for row in rows:
        has_any_card = False
        has_any_left_gift = False
        for i in range(2, 2 + 12):
            if row[i] > 0:
                has_any_card = True
        for i in range(14, 14 + 4):
            if row[i] > 0:
                has_any_left_gift = True
        if has_any_card and not has_any_left_gift:
            accounts_that_should_enable_cost_card_to_lottery.append(row[1])

    # 给每一行上色
    for row in rows:
        idx = row[0]
        name = row[1]

        for i in range(2, 2 + 12):
            row[i] = colored_count(idx, row[i], cfg.get_account_config_by_name(name).ark_lottery.show_color)
        for i in range(14, 14 + 4):
            row[i] = count_with_color(row[i], "bold_green", show_width=printed_width(prize_indexes[i - 14]))

    # 打印卡片情况
    logger.info(tableify(heads, colSizes))
    for row in rows:
        logger.info(tableify(row, colSizes))
    logger.info(tableify(summaryCols, colSizes))

    logger.info("")
    logger.info("新版集卡不再可以查询剩余领奖次数，上面右侧四个值没有实际含义，望周知")

    # 打印提示
    if need_show_tips and len(accounts_that_should_enable_cost_card_to_lottery) > 0:
        accounts = ", ".join(accounts_that_should_enable_cost_card_to_lottery)
        msg = f"账户({accounts})仍有剩余卡片，但已无任何可领取礼包，建议开启消耗卡片来抽奖的功能"
        logger.warning(color("fg_bold_yellow") + msg)


def make_ark_lottery_card_and_award_info():
    # 构建各个卡片和奖励名称的映射关系
    # card index => name(旧版), id(新版)
    order_map = {}
    # 奖励名称列表
    prizeDisplayTitles = []

    for row in range_from_one(3):
        for col in range_from_one(4):
            index = f"{row}-{col}"
            card_id = str(4 * (row - 1) + col)

            order_map[index] = card_id

    for title in get_prize_names():
        order_map[title] = title
        prizeDisplayTitles.append(title)

    return order_map, prizeDisplayTitles


def query_lottery_status(
    idx: int,
    account_config: AccountConfig,
    common_config: CommonConfig,
    card_indexes: list[str],
    prize_indexes: list[str],
    order_map: dict[str, str],
) -> list | None:
    if not account_config.ark_lottery.show_status:
        return None

    djcHelper = DjcHelper(account_config, common_config)
    lr = djcHelper.fetch_pskey()
    if lr is None:
        return None
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list(print_warning=False)

    # 获取卡片和奖励数目，其中新版本卡片为 id=>count ，旧版本卡片为 name=>count
    card_counts = djcHelper.dnf_ark_lottery_get_card_counts()
    prize_counts = djcHelper.dnf_ark_lottery_get_prize_counts()

    # 构建本行数据
    cols = [idx, account_config.name]

    # 处理各个卡片数目
    for _card_position, card_index in enumerate(card_indexes):
        card_count = card_counts[order_map[card_index]]

        cols.append(card_count)

    # 处理各个奖励剩余领取次数
    for prize_index in prize_indexes:
        prize_count = prize_counts[order_map[prize_index]]
        cols.append(prize_count)

    return cols


def colored_count(accountIdx, card_count, show_color=""):
    # 特殊处理色彩
    if card_count == 0:
        if accountIdx == 1:
            # 突出显示大号没有的卡片
            show_count = count_with_color(card_count, "fg_bold_cyan")
        else:
            # 小号没有的卡片直接不显示，避免信息干扰
            show_count = ""
    else:
        if accountIdx == 1:
            if card_count == 1:
                # 大号只有一张的卡片也特殊处理
                show_count = count_with_color(card_count, "fg_bold_blue")
            else:
                # 大号其余卡片亮绿色
                show_count = count_with_color(card_count, "fg_bold_green")
        else:
            # 小号拥有的卡片淡化处理，方便辨识
            show_color = show_color or "fg_bold_black"
            show_count = count_with_color(card_count, show_color)

    return show_count


def count_with_color(card_count, show_color, show_width=3):
    return color(show_color) + padLeftRight(card_count, show_width) + asciiReset + color("INFO")


@try_except()
def show_extra_infos(cfg: Config):
    show_activity_info(cfg)

    show_following_regular_activity_expected_info()

    show_tips(cfg)


@try_except()
def show_pay_info(cfg):
    logger.info("")
    _show_head_line("付费相关信息")
    user_buy_info = get_user_buy_info(cfg.get_qq_accounts())
    show_buy_info(user_buy_info, cfg)


@try_except()
def show_activity_info(cfg: Config):
    logger.info("")
    _show_head_line("部分活动信息")
    logger.warning("如果一直卡在这一步，请在小助手目录下创建一个空文件：不查询活动.txt")
    Urls().show_current_valid_act_infos()

    user_buy_info = get_user_buy_info(cfg.get_qq_accounts(), show_dlc_info=False)
    show_activities_summary(cfg, user_buy_info)


def show_following_regular_activity_expected_info():
    logger.info("")
    _show_head_line("未来一年常规活动周期的预估信息")

    lines = []

    heads, colSizes = zip(
        ("序号", 4),
        ("常规活动周期", 12),
        ("预估开始时间", 12),
        ("距今天数", 12),
    )
    lines.append(color("bold_green") + tableify(heads, colSizes))

    now = get_now()

    next_year_act_list = get_act_name_and_next_expect_time_list()
    for idx, name_and_time in enumerate(next_year_act_list):
        act_name, act_time = name_and_time

        act_time_str = format_time(act_time, "%Y-%m-%d")

        expected_days = (act_time - now).days
        f"{expected_days}天后"

        lines.append(
            color("bold_yellow")
            + tableify(
                [idx + 1, act_name, act_time_str, expected_days],
                colSizes,
                need_truncate=False,
            )
        )

    logger.info("\n" + "\n".join(lines))

    if is_first_run("常规活动周期预估信息"):
        async_message_box(
            "在运行结束的活动链接与小提示中间新增了一个常规活动周期预估信息，可以查看未来一年内的一些常规活动周期的预估时间点，方便大家知晓大概什么时候会有新活动",
            "常规活动周期预估",
        )


@try_except()
# show_accounts_status 展示个人概览
def sas(cfg: Config, ctx: str, user_buy_info: BuyInfo):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line(ctx)

    # 获取数据
    rows = []
    if cfg.common.enable_multiprocessing:
        logger.warning(f"已开启多进程模式({get_pool_size()})，将开始并行拉取数据，请稍后")
        for row in get_pool().starmap(
            get_account_status,
            [
                (_idx + 1, account_config, cfg.common, user_buy_info)
                for _idx, account_config in enumerate(cfg.account_configs)
                if account_config.is_enabled()
            ],
        ):
            rows.append(row)
    else:
        logger.warning("拉取数据中，请稍候")
        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            rows.append(get_account_status(idx, account_config, cfg.common, user_buy_info))

    # 打印结果
    heads, colSizes = zip(
        ("序号", 4),
        ("账号名", 12),
        ("聚豆余额", 8),
        ("心悦类型", 10),
        ("成就点", 6),
        ("勇士币", 6),
        ("心悦组队", 16),
        ("前两周心悦", 10),
        ("自动组队", 8),
        ("编年史", 14),
        ("年史碎片", 8),
        ("搭档", 20),
        ("上月", 4),
        ("自动匹配", 8),
        ("论坛代币券", 10),
        ("漫画星星", 8),
    )

    logger.info(tableify(heads, colSizes))
    for row in rows:
        logger.info(color("fg_bold_green") + tableify(row, colSizes, need_truncate=True))

    # # 展示本周闪光杯爆装
    # DjcHelper(cfg.account_configs[0], cfg.common).dnf_shanguang_show_equipments()


def get_account_status(idx: int, account_config: AccountConfig, common_config: CommonConfig, user_buy_info: BuyInfo):
    djcHelper = DjcHelper(account_config, common_config)
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list(print_warning=False)

    _, djc_balance = djcHelper.query_balance("查询聚豆概览", print_res=False)

    xinyue_info = djcHelper.query_xinyue_info("查询心悦成就点概览", print_res=False)
    teaminfo = djcHelper.query_xinyue_teaminfo()
    team_award_summary = "无队伍"
    if teaminfo.is_team_full():
        team_award_summary = djcHelper.query_xinyue_team_this_week_award_summary()

    last_two_week_xinyue_take_award_count = djcHelper.query_last_two_week_xinyue_team_take_award_count()
    can_auto_match_xinyue_team = ""
    if djcHelper.can_auto_match_xinyue_team(user_buy_info, print_waring=False):
        if teaminfo.is_team_full():
            can_auto_match_xinyue_team = "匹配成功"
        else:
            can_auto_match_xinyue_team = "等待匹配"
    elif xinyue_info.is_xinyue_or_special_member() and not account_config.enable_auto_match_xinyue_team:
        can_auto_match_xinyue_team = "未开启"

    levelInfo, chronicle_points = djcHelper.query_dnf_helper_chronicle_info().get_level_info_and_points_to_show()

    partner_Info = ""
    user_task_info = djcHelper.query_dnf_helper_chronicle_user_task_list()
    if user_task_info.hasPartner:
        partner_Info = user_task_info.get_partner_info(account_config.dnf_helper_info)

    user_info_db = (
        DnfHelperChronicleUserActivityTopInfoDB().with_context(djcHelper.get_dnf_helper_chronicle_db_key()).load()
    )
    last_month_user_task_info = user_info_db.get_last_month_user_info()
    last_month_level = last_month_user_task_info.level

    can_auto_match_dnf_helper_chronicle = ""
    if djcHelper.check_dnf_helper_chronicle_auto_match(user_buy_info, print_waring=False):
        if user_task_info.hasPartner:
            can_auto_match_dnf_helper_chronicle = "匹配成功"
        else:
            can_auto_match_dnf_helper_chronicle = "等待匹配"
    elif not account_config.dnf_helper_info.enable_auto_match_dnf_chronicle:
        can_auto_match_dnf_helper_chronicle = "未开启"

    # majieluo_stone = djcHelper.query_stone_count()
    # time.sleep(1)  # 避免查询下面的次数时提示 速度过快
    # majieluo_invite_count = f"{djcHelper.query_invite_count()}/30"

    dbq = djcHelper.query_dnf_bbs_dbq()

    comic_start_count = djcHelper.query_dnf_comic_star_count()

    return [
        idx,
        account_config.name,
        djc_balance,
        xinyue_info.xytype_str,
        xinyue_info.score,
        xinyue_info.ysb,
        team_award_summary,
        last_two_week_xinyue_take_award_count,
        can_auto_match_xinyue_team,
        levelInfo,
        chronicle_points,
        partner_Info,
        last_month_level,
        can_auto_match_dnf_helper_chronicle,
        # majieluo_stone, majieluo_invite_count,
        dbq,
        comic_start_count,
    ]


@try_except()
def try_join_xinyue_team(cfg: Config, user_buy_info: BuyInfo):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("尝试加入心悦固定队或在线匹配")

    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        logger.info("")
        logger.warning(color("fg_bold_yellow") + f"------------尝试第{idx}个账户({account_config.name})------------")

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()
        # 尝试加入心悦队伍
        djcHelper.try_join_xinyue_team(user_buy_info)


def run(cfg: Config, user_buy_info: BuyInfo):
    _show_head_line("开始核心逻辑")

    # 上报付费使用情况
    try_report_pay_info(cfg, user_buy_info)

    # 展示活动概览
    show_activities_summary(cfg, user_buy_info)

    start_time = datetime.datetime.now()

    if cfg.common.enable_multiprocessing:
        _show_head_line(f"已开启多进程模式({get_pool_size()})，将并行运行~")

        if is_monthly_first_run("每月提醒：多进程模式可能漏奖励"):
            async_message_box(
                """
经反馈发现，超快速模式下单次运行时可能会漏奖励。大概率是因为部分活动会共享请求CD，而超快速模式下，所有活动会并行执行，导致可能部分请求因超出频率而失败。

可采取下列方式：
1. 每天多运行几次，
这样基本都能领全，而且每次运行时间比较快

2. 调小默认并发进程数
默认设置的并发数可能比较大，调小一点可能能缓解这个，代价是运行会慢一些

3. 关闭超快速模式，仅保留多进程模式
速度会比超快速模式慢不少，但是因为请求过快而单次领不全的概率会大幅下降

4. 关闭超快速模式和多进程模式
速度会显著变慢，但是基本不会出现请求过快而领不全奖励的问题了

PS0:1/3/4方案的大致速度对比如下，可自行按需选择
1: 一般在2-4分钟，基本等于 登录单个账号 + 运行单个活动 + 查询单个账号概览 的时间
3: 一般在十分钟上下，基本等于 登录单个账号 + 运行单个账号所有活动 + 查询单个账号概览 的时间
4: 一般在 账号数目*3分钟 上下， 基本等于 账号数目 * （登录单个账号 + 运行所有活动 + 查询单个账号概览） 的世界

PS1：相关配置位置：配置工具/公共配置/多进程

PS2：在开启多进程模式的情况下，这个弹窗每月会弹出一次，用来提示这种副作用的存在~
""".strip(),
                "超快速模式副作用",
            )

        if not cfg.common.enable_super_fast_mode:
            logger.info("当前未开启超快速模式~将并行运行各个账号")
            get_pool().starmap(
                do_run,
                [
                    (_idx + 1, account_config, cfg.common, user_buy_info)
                    for _idx, account_config in enumerate(cfg.account_configs)
                    if account_config.is_enabled()
                ],
            )
        else:
            logger.info(
                color("bold_cyan")
                + f"已启用超快速模式，将使用{get_pool_size()}个进程并发运行各个账号的各个活动，日志将完全不可阅读~"
            )
            activity_funcs_to_run = get_activity_funcs_to_run(cfg, user_buy_info)
            get_pool().starmap(
                run_act,
                [
                    (account_config, cfg.common, user_buy_info, act_name, act_func.__name__)
                    for account_config in cfg.account_configs
                    if account_config.is_enabled()
                    for act_name, act_func in activity_funcs_to_run
                ],
            )
    else:
        for idx, account_config in enumerate(cfg.account_configs):
            idx += 1
            if not account_config.is_enabled():
                logger.info(f"第{idx}个账号({account_config.name})未启用，将跳过")
                continue

            do_run(idx, account_config, cfg.common, user_buy_info)

    used_time = datetime.datetime.now() - start_time
    _show_head_line(f"处理总计{len(cfg.account_configs)}个账户 共耗时 {used_time}")


@try_except(show_exception_info=False)
def try_report_usage_info(cfg: Config):
    # 方便ga4统计新用户数目
    increase_counter(ga_category="first_visit", name="first_visit")
    increase_counter(ga_category="first_open", name="first_open")

    # 整体使用次数
    increase_counter(this_version_global_usage_counter_name)
    increase_counter(global_usage_counter_name)

    # 当前用户使用次数
    increase_counter(this_version_my_usage_counter_name)
    increase_counter(my_usage_counter_name, report_to_lean_cloud=True)

    # 是否启用了自动备份功能
    increase_counter(ga_category="enable_auto_sync_config", name=not os.path.exists(disable_flag_file))

    # 是否使用源码运行
    increase_counter(ga_category="run_from_src", name=run_from_src())

    # 运行的系统(windows/linux)
    increase_counter(ga_category="run_system", name=platform.system())

    # 上报账号相关的一些信息（如账号数、使用的登录模式，不包含任何敏感信息）
    increase_counter(ga_category="account_count", name=len(cfg.account_configs))
    for account_config in cfg.account_configs:
        if not account_config.is_enabled():
            # 不启用的账户不统计
            continue

        increase_counter(ga_category="login_mode", name=account_config.login_mode)

        increase_counter(ga_category="enable_xinyue_team_auto_match", name=account_config.enable_auto_match_xinyue_team)
        increase_counter(
            ga_category="enable_auto_match_dnf_chronicle",
            name=account_config.dnf_helper_info.enable_auto_match_dnf_chronicle,
        )
        increase_counter(
            ga_category="enable_fixed_dnf_chronicle_partner", name=account_config.dnf_helper_info.pUserId != ""
        )

    # 上报网盘地址，用于区分分发渠道
    if not run_from_src():
        increase_counter(ga_category="netdisk_link", name=cfg.common.netdisk_link_for_report)


@try_except(show_exception_info=False)
def try_report_pay_info(cfg: Config, user_buy_info: BuyInfo):
    if not run_from_src():
        # 仅打包版本尝试上报付费信息
        if has_buy_auto_updater_dlc(cfg.get_qq_accounts()):
            increase_counter(my_auto_updater_usage_counter_name)

        increase_counter(ga_category="pay_or_not", name=user_buy_info.is_active())
        if user_buy_info.is_active():
            increase_counter(my_active_monthly_pay_usage_counter_name, report_to_lean_cloud=True)
            increase_counter(ga_category="buy_times", name=len(user_buy_info.buy_records))
            increase_counter(ga_category="buy_month", name=user_buy_info.total_buy_month)
            increase_counter(ga_category="game_qq_count", name=len(user_buy_info.game_qqs))


def get_activity_funcs_to_run(cfg: Config, user_buy_info: BuyInfo) -> list[tuple[str, Callable]]:
    return DjcHelper(cfg.account_configs[0], cfg.common).get_activity_funcs_to_run(user_buy_info)


def show_activities_summary(cfg: Config, user_buy_info: BuyInfo):
    djcHelper = DjcHelper(cfg.get_any_enabled_account(), cfg.common)
    djcHelper.fetch_pskey()
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list()

    djcHelper.show_activities_summary(user_buy_info)


def do_run(idx: int, account_config: AccountConfig, common_config: CommonConfig, user_buy_info: BuyInfo):
    wait_a_while(idx)

    _show_head_line(f"开始处理第{idx}个账户({account_config.name})")

    start_time = datetime.datetime.now()

    djcHelper = DjcHelper(account_config, common_config, user_buy_info)
    djcHelper.run(user_buy_info)

    used_time = datetime.datetime.now() - start_time
    _show_head_line(f"处理第{idx}个账户({account_config.name}) 共耗时 {used_time}")


@try_except()
def try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once(cfg: Config, user_buy_info: BuyInfo):
    if not cfg.common.try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once:
        return

    if not has_any_account_in_normal_run(cfg):
        return
    if not user_buy_info.is_active():
        return

    _show_head_line(
        "尝试在全部账号运行完毕后再次领取编年史任务奖励，从而当本地两个号设置为搭档时可以领取到对方的经验，而不需要再运行一次"
    )

    # 所有账号运行完毕后，尝试领取一次心悦组队奖励，避免出现前面角色还没完成，后面的完成了，前面的却没领奖励
    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        logger.info("")
        logger.warning(
            color("fg_bold_green")
            + f"------------开始尝试为第{idx}个账户({account_config.name})再次领取编年史任务奖励------------"
        )

        if not account_config.function_switches.get_dnf_helper_chronicle:
            show_act_not_enable_warning("编年史")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        djcHelper.dnf_helper_chronicle(take_task_award_only=True)


@try_except()
def try_take_xinyue_team_award(cfg: Config, user_buy_info: BuyInfo):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("尝试领取心悦组队奖励")

    # 所有账号运行完毕后，尝试领取一次心悦组队奖励，避免出现前面角色还没完成，后面的完成了，前面的却没领奖励
    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        logger.info("")
        logger.warning(
            color("fg_bold_green")
            + f"------------开始尝试为第{idx}个账户({account_config.name})领取心悦组队奖励------------"
        )

        if not account_config.function_switches.get_xinyue:
            show_act_not_enable_warning("心悦特权专区")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        # 如果使用了云端自动组队功能，且仍未组到队，则暂时先不尝试领取奖励
        group_info = djcHelper.get_xinyue_team_group_info(user_buy_info)
        teaminfo = djcHelper.query_xinyue_teaminfo()
        if not group_info.is_local and not teaminfo.is_team_full():
            logger.warning(
                color("fg_yellow")
                + "当前启用了云端自动组队功能，但仍未组到队。因为组队前获取的奖励不会计入默契福利，暂时不尝试领取心悦奖励"
            )
            continue

        djcHelper.xinyue_battle_ground_wpe_op("领取队伍3次运镖幸运加成", 131432)


def show_buy_info(user_buy_info: BuyInfo, cfg: Config, need_show_message_box=True):
    logger.info(color("bold_cyan") + user_buy_info.description())

    monthly_pay_info = "按月付费未激活"
    if user_buy_info.total_buy_month != 0:
        if user_buy_info.is_active():
            rt = user_buy_info.remaining_time()
            monthly_pay_info = f"按月付费剩余时长为 {rt.days}天{rt.seconds // 3600}小时"
        else:
            monthly_pay_info = "按月付费已过期"
    change_title(
        monthly_pay_info=monthly_pay_info,
        multiprocessing_pool_size=get_pool_size(),
        enable_super_fast_mode=cfg.common.enable_super_fast_mode,
        may_have_buy_dlc=user_buy_info.infer_has_buy_dlc(),
        show_next_regular_activity_info=True,
    )

    if need_show_message_box:
        # 仅在运行结束时的那次展示付费信息的时候尝试进行下列弹窗~
        expired = not user_buy_info.is_active()
        will_expired_soon = user_buy_info.will_expire_in_days(cfg.common.notify_pay_expired_in_days)
        if (expired and is_weekly_first_run("show_buy_info_expired")) or (
            will_expired_soon and is_daily_first_run("show_buy_info_will_expired_soon")
        ):
            ctx = ""
            if expired:
                ctx = monthly_pay_info
            elif will_expired_soon:
                ctx = f"按月付费即将在{user_buy_info.remaining_time().days}天后过期({user_buy_info.expire_at})"
            threading.Thread(target=show_buy_info_sync, args=(ctx, cfg), daemon=True).start()
            wait_seconds = 15
            logger.info(color("bold_green") + f"等待{wait_seconds}秒，确保看完这段话~")
            time.sleep(wait_seconds)

        has_use_card_secret = False
        for record in user_buy_info.buy_records:
            if record.reason in ["卡密自助购买", "直接自助购买"]:
                has_use_card_secret = True
                break

        if (
            not use_by_myself()
            and user_buy_info.total_buy_month > 0
            and not has_use_card_secret
            and is_weekly_first_run("每周提示一次已付费用户续费可使用卡密或直接付费来自助操作")
        ):
            msg = "现已添加新的的付费方案，可在一分钟内自助完成付费和激活对应功能（自动更新或按月付费）。\n如果想要付费或者续费可以选择这个方案~ 详情请看 【付费指引/付费指引.url】"
            title = "新增付费方案"
            async_message_box(msg, title, icon=MB_ICONINFORMATION, follow_flag_file=False)


def show_buy_info_sync(ctx: str, cfg: Config, force_message_box=False):
    usedDays = get_count(my_usage_counter_name, "all")
    message = (
        f"{ctx}\n"
        "\n"
        f"Hello~ 你已经累积使用小助手{usedDays}天，希望小助手为你节省了些许时间和精力(●—●)\n"
        "\n"
        f"目前已登录的账号列表为：{cfg.get_qq_accounts()}，这些QQ当前 【均无按月付费】 或者 【已过期】 或者 【即将过期】\n"
        "\n"
        "2.2号添加了一个付费弹窗，但是截至2.6晚上六点，仅有不到百分之一的使用者进行了付费。\n"
        "考虑到近日来花在维护小助手上的时间比较久，因此本人决定，自2021-02-06 00:00:00之后添加的所有短期活动都将只能在付费生效期间使用，此前已有的功能（如道聚城、心悦）或之后出的长期功能都将继续免费使用。\n"
        "毕竟用爱发电不能持久，人毕竟是要恰饭的ლ(╹◡╹ლ)\n"
        "你的付费能让我更乐意使用本来用于玩DNF的闲暇时间来及时更新小助手，适配各种新出的蚊子腿活动，添加更多自动功能。( • ̀ω•́ )✧\n"
        "\n"
        "使用源码运行将不受该限制，但是使用我的打包二进制时，只有付费生效期间才能运行上述日期后的短期新活动，各位可自行决定通过付费激活还是自己研究如何使用源码去运行~\n"
        "使用源码运行将不受该限制，但是使用我的打包二进制时，只有付费生效期间才能运行上述日期后的短期新活动，各位可自行决定通过付费激活还是自己研究如何使用源码去运行~\n"
        "使用源码运行将不受该限制，但是使用我的打包二进制时，只有付费生效期间才能运行上述日期后的短期新活动，各位可自行决定通过付费激活还是自己研究如何使用源码去运行~\n"
        "(重要的话说三遍)\n"
        "\n"
        "目前定价为5元每月（31天）\n"
        "购买方式可查看目录中的【付费指引/付费指引.docx】\n"
        "（若未购买，则这个消息每周会弹出一次）\n"
        "（若当前剩余付费时长在配置的提前提醒天数内，则这个消息每天会弹出一次）\n"
        "（ヾ(=･ω･=)o）\n"
    )
    logger.warning(color("fg_bold_cyan") + message)
    if is_windows():
        if not use_by_myself() or force_message_box:
            win32api.MessageBox(0, message, "付费提示(〃'▽'〃)", win32con.MB_OK)
        # os.popen("付费指引/支持一下.png")
        open_with_default_app("付费指引/付费指引.url")


def show_recommend_reward_tips(user_buy_info: BuyInfo):
    if user_buy_info.total_buy_month == 0:
        # 未付费过的用户不提示该信息
        return

    remote_config = config_cloud()
    if not remote_config.enable_recommend_reward:
        # 未启用推荐功能的情况下，不展示该提示
        return

    async_message_box(
        (
            "Hello~ 你已经累积使用小助手一段时间啦，希望小助手为你节省了些时间和精力(●—●)\n"
            "\n"
            "如果你觉得小助手好用的话，可以推荐给你的小伙伴们\n"
            "你的小伙伴在首次购买按月付费时，可在推荐人处填写你的主QQ\n"
            "当他完成购买时，你将获得一个月的小助手使用时长作为奖励0-0\n"
        ),
        "推荐奖励",
        show_once=True,
        color_name="bold_green",
    )


def check_update(cfg):
    if is_run_in_github_action():
        logger.info("当前在github action环境下运行，无需检查更新")
        return

    if exists_auto_updater_dlc():
        # 如果存在自动更新DLC，则走自动更新的流程，不再手动检查是否有更新内容
        return

    logger.warning(
        color("bold_cyan")
        + (
            "未发现自动更新DLC（预期应放在utils/auto_updater.exe路径，但是木有发现嗷），因此自动更新功能没有激活，需要根据检查更新结果手动进行更新操作~\n"
            "如果已经购买过DLC，请先打开目录中的[付费指引/付费指引.docx]，找到自动更新DLC的使用说明，按照教程操作一番即可\n"
            "-----------------\n"
            "以下为广告时间0-0\n"
            "花了两天多时间，给小助手加入了目前(指2021.1.6)唯一一个付费DLC功能：自动更新（支持增量更新和全量更新）\n"
            "当没有该DLC时，所有功能将正常运行，只是需要跟以往一样，检测到更新时需要自己去手动更新\n"
            "当添加该DLC后，将额外增加自动更新功能，启动时将会判断是否需要更新，若需要则直接干掉小助手，然后更新到最新版后自动启动新版本\n"
            "演示视频: https://www.bilibili.com/video/BV1FA411W7Nq\n"
            "由于这个功能并不影响实际领蚊子腿的功能，且花费了我不少时间来倒腾这东西，所以目前决定该功能需要付费获取，暂定价为10.24元。\n"
            "想要摆脱每次有新蚊子腿更新或bugfix时，都要手动下载并转移配置文件这种无聊操作的小伙伴如果觉得这个价格值的话，可以按下面的方式购买0-0\n"
            "价格：10.24元\n"
            "购买方式和使用方式可查看目录中的【付费指引/付费指引.docx】\n"
            "PS：不购买这个DLC也能正常使用蚊子腿小助手哒（跟之前版本体验一致）~只是购买后可以免去手动升级的烦恼哈哈，顺带能鼓励我花更多时间来维护小助手，支持新的蚊子腿以及优化使用体验(oﾟ▽ﾟ)o  \n"
        )
    )

    logger.info(
        "\n"
        "++++++++++++++++++++++++++++++++++++++++\n"
        "现在准备访问github仓库相关页面来检查是否有新版本\n"
        "由于国内网络问题，访问可能会比较慢，请不要立即关闭，可以选择最小化或切换到其他窗口0-0\n"
        "若有新版本会自动弹窗提示~\n"
        "++++++++++++++++++++++++++++++++++++++++\n"
    )
    check_update_on_start(cfg.common)


def print_update_message_on_first_run_new_version():
    if is_run_in_github_action():
        logger.info("github action环境下无需打印新版本更新内容")
        return

    load_config("config.toml", "config.toml.local")
    cfg = config()

    if is_first_run(f"print_update_message_v{now_version}"):
        try:
            ui = get_update_info(cfg.common)
            message = f"新版本v{ui.latest_version}已更新完毕，具体更新内容展示如下，以供参考：\n" f"{ui.update_message}"

            async_message_box(message, "新版本更新内容")
        except Exception as e:
            logger.warning("新版本首次运行获取更新内容失败，请自行查看CHANGELOG.MD", exc_info=e)


def show_ask_message_box(cfg: Config):
    threading.Thread(target=show_ask_message_box_sync, args=(cfg,), daemon=True).start()


def show_ask_message_box_sync(cfg: Config):
    if not is_windows():
        return

    if exists_flag_file(".never_show_ask_message_box"):
        return

    if (
        cfg.common.enable_alipay_redpacket_v3
        and config_cloud().enable_alipay_redpacket
        and is_weekly_first_run("支付宝红包活动")
        and not use_by_myself()
    ):
        title = "支付宝红包活动（v3）"
        message = (
            "现在支付宝有个红包活动，扫弹出来的这个二维码就可以领取一个红包，在便利店等实体店扫码就可以使用，购买小助手的时候似乎也可以使用。\n"
            "你使用后我会同时领到一个小红包，大家一起白嫖-。-\n"
            "\n"
            "\n"
            "如果不想看到该弹窗，可以前往配置工具，取消勾选 公共配置/其他/是否弹出支付宝红包活动图片 即可，否则将每周第一次运行时弹出一次0-0"
            "\n"
            "支付宝这个红包活动延期了-。-所以我把开关调整了下，之前关闭过的，如果真的不想看到，可以再去点一点<_<\n"
        )
        image_path = random.choice(["付费指引/支付宝红包活动.jpg", "付费指引/支付宝红包活动_实体版.jpg"])
        message_box(message, title, open_image=image_path)


@try_except()
def show_tips(cfg: Config):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("一些小提示")

    tips = {
        "工具下载": (
            "如需下载chrome、autojs、HttpCanary、vscode、bandizip等小工具，可前往网盘自助下载：\n"
            "http://101.43.54.94:5244/%E6%96%87%E6%9C%AC%E7%BC%96%E8%BE%91%E5%99%A8%E3%80%81chrome%E6%B5%8F%E8%A7%88%E5%99%A8%E3%80%81autojs%E3%80%81HttpCanary%E7%AD%89%E5%B0%8F%E5%B7%A5%E5%85%B7\n"
        ),
        "查看历史公告": (
            "目前部分信息会通过小助手的公告机制来告知大家，比如最近升级win11后可能会桌面卡住的解决方案\n"
            "但是之前一直只能显示一次，部分朋友可能看到时还没遇到公告中所提到的问题，等后面遇到时又发现忘记了之前公告里是咋说的了\n"
            "为此，花了点功夫，在配置工具中最上方第三排新增了一个【查看公告】的按钮，点击即可查看过去发的所有公告\n"
            "在后续遇到公告中提及的问题时，可以在这里快速找到对应公告\n"
        ),
        "视频教程": (
            "部分活动的配置可能比较麻烦，因此新录制了几个视频教程，有兴趣的朋友可以自行观看：\n"
            "https://www.bilibili.com/video/BV1LQ4y1y7QJ?p=1\n"
        ),
        "助手编年史": (
            "dnf助手签到任务和浏览咨询详情页请使用auto.js等自动化工具来模拟打开助手去执行对应操作，当然也可以每天手动打开助手点一点-。-\n"
            "也就是说，小助手不会帮你*完成*上述任务的条件，只会在你完成条件的前提下，替你去领取任务奖励\n"
            "此外，如果想要自动领取等级奖励，请把配置工具中助手相关的所有配置项都填上\n"
        ),
        "24.1 漫画兑换": (
            "小助手现已支持漫画活动的兑换功能，各位可打开配置工具【账号配置/漫画】，配置需要兑换的道具（如黑钻）\n"
        ),
        "24.11 嘉年华": (
            "嘉年华的预约活动需要分享给好友才能领取奖励，有兴趣的朋友请自行在页面上分享后领取\n"
            "https://dnf.qq.com/cp/a20241122live/\n"
        ),
        "24.11 加官方Q群活动": (
            "加入官方QQ群，可以领取一个蚊子腿，有兴趣的可以查看下方的网页\n"
            "https://dnf.qq.com/cp/a20241015dnf_114152/\n"
        ),
    }

    logger.info(
        color("bold_green")
        + "如果看上去卡在这了，请看看任务是否有弹窗的图标，把他们一个个按掉就能继续了（活动此时已经运行完毕）"
    )

    for title, tip in tips.items():
        # 为保证格式一致，移除末尾的\n
        tip = str(tip)
        if tip.endswith("\n"):
            tip = tip[:-1]

        msg = tip.replace("\n", "\n\n") + "\n"
        message_box(msg, f"一些小提示_{title}", show_once=True, follow_flag_file=False, use_qt_messagebox=True)

    if cfg.common.disable_cmd_quick_edit:
        show_quick_edit_mode_tip()


def show_tips_for_myself():
    if not use_by_myself():
        return

    _show_head_line("仅自己可见的一些小提示")

    # if is_weekly_first_run("微信支付维护提示"):
    #     show_tip_for_myself("看看微信支付的渠道维护结束了没。如果结束了，就把配置工具中微信支付按钮的点击特殊处理干掉", "支付维护")

    # if is_weekly_first_run("交易乐维护提示"):
    #     show_tip_for_myself("看看交易乐是否已经修复，如果已经正常运行，则将配置工具中默认启用卡密的处理移除（搜：默认启用卡密）", "交易乐维护提示")

    # 若当前版本发布已经超过14天，且距离下次常规活动的预估时间低于7天，则每天尝试提示一下，看看是否已经出了这个活动，准备接入
    time_since_last_update = get_time_since_last_update()
    if time_since_last_update.days >= 14:
        now = get_now()

        _, next_act_datetime = get_next_regular_activity_name_and_expected_datetime()

        if (next_act_datetime - now).days <= 7 and is_daily_first_run("常规活动接入"):
            show_tip_for_myself(
                f"看看常规活动周期 {get_next_regular_activity_desc()} 是否出了，是否可以开始接入了", "常规活动接入"
            )


def show_tip_for_myself(msg: str, title: str):
    message_box(msg, f"给自己看的提示 - {title}")


def try_auto_update_ignore_permission_on_special_case(cfg: Config):
    # 尝试触发下更新云配置，方便尽快生效
    # hack: 这里不使用之前的 async_update=False 来同步触发，是为了避免某些情况下，下载接口有问题而导致主流程卡住的情况。缺点是，在上次更新后的缓存时间内，可能不会获取到最新的配置
    try_update_config_cloud()

    remote_config = config_cloud()
    if not remote_config.try_auto_update_ignore_permission.can_ignore(now_version, get_now()):
        return

    # 发生了某种特殊情况，将无视权限进行自动更新
    try_auto_update(cfg, ignore_permission=True)


def try_auto_update(cfg: Config, ignore_permission=False):
    try:
        if not cfg.common.auto_update_on_start and not ignore_permission:
            show_head_line(
                "当前已配置已关闭自动更新功能，将跳过。可在【配置工具/公共配置/更新】进行调整", color("bold_cyan")
            )
            return

        pid = os.getpid()
        exe_path = sys.argv[0]
        dirpath, filename = os.path.dirname(exe_path), os.path.basename(exe_path)

        if run_from_src():
            logger.info("当前为源码模式运行，自动更新功能将不启用~请自行定期git pull更新代码")
            return

        if not is_windows():
            logger.info("当前在非windows系统运行，自动更新功能将不启用~请自行定期自行更新")
            return

        query_ok = True
        if not ignore_permission:
            # 需要检查是否购买dlc的使用权限
            has_buy_dlc, query_ok = has_buy_auto_updater_dlc_and_query_ok(cfg.get_qq_accounts())
            if not has_buy_dlc:
                if exists_auto_updater_dlc():
                    logger.warning(color("bold_cyan") + "当前未购买自动更新DLC，将跳过自动更新流程~")
                return

        # 可使用dlc的流程
        if os.path.isfile(auto_updater_latest_path()):
            # 如果存在auto_updater_latest.exe，且与auto_updater.exe不同，则覆盖更新
            need_copy = False
            reason = ""
            if not exists_auto_updater_dlc_and_not_empty():
                # 不存在dlc，或dlc为空文件，直接复制
                need_copy = True
                reason = "当前不存在dlc，或dlc为空文件，但存在最新版dlc，将复制使用该dlc"
            else:
                # 存在dlc，判断版本是否不同
                latest_md5 = md5_file(auto_updater_latest_path())
                latest_mtime = parse_timestamp(os.stat(auto_updater_latest_path()).st_mtime)

                current_md5 = md5_file(auto_updater_path())
                current_mtime = parse_timestamp(os.stat(auto_updater_path()).st_mtime)

                logger.debug(f"latest_md5={latest_md5}, latest_mtime={latest_mtime}")
                logger.debug(f"current_md5={current_md5}, current_mtime={current_mtime}")

                need_copy = latest_md5 != current_md5 and latest_mtime > current_mtime
                reason = f"当前存在dlc({current_mtime})，但存在更新版本的最新版dlc({latest_mtime})，将覆盖替换"

            if need_copy:
                logger.info(
                    color("bold_green") + f"{reason}，将复制{auto_updater_latest_path()}到{auto_updater_path()}"
                )
                shutil.copy2(auto_updater_latest_path(), auto_updater_path())
        else:
            if not exists_auto_updater_dlc_and_not_empty():
                if not query_ok and not ignore_permission:
                    logger.debug(
                        "当前应该是查询dlc失败后全部放行的情况，这种情况下若本地没有dlc，则不尝试自动下载，避免后续查询功能恢复正常后提示没有权限，需要手动删除"
                    )
                    return

                # 未发现dlc和最新版dlc，尝试从网盘下载
                logger.info(color("bold_yellow") + f"未发现自动更新DLC({auto_updater_path()})，将尝试从网盘下载")

                download_from_alist(os.path.basename(auto_updater_path()), os.path.dirname(auto_updater_path()))

        # 保底，如果前面的流程都失败了，提示用户自行下载
        if not exists_auto_updater_dlc_and_not_empty():
            logger.warning(
                color("bold_cyan")
                + "未发现自动更新DLC，或DLC为空文件（预期应放在utils/auto_updater.exe路径，但是木有发现嗷），将跳过自动更新流程~"
            )
            logger.warning(
                color("bold_green")
                + "如果已经购买过DLC，请先打开目录中的[付费指引/付费指引.docx]，找到自动更新DLC的使用说明，按照教程操作一番即可"
            )
            return

        logger.info(
            "开始尝试调用自动更新工具进行自动更新~ 当前处于测试模式，很有可能有很多意料之外的情况，如果真的出现很多问题，可以自行关闭该功能的配置"
        )

        logger.info(f"当前进程pid={pid}, 版本={now_version}, 工作目录={dirpath}，exe名称={filename}")

        logger.info(
            color("bold_yellow")
            + "尝试启动更新器，等待其执行完毕。若版本有更新，则会干掉这个进程并下载更新文件，之后重新启动进程...(请稍作等待）"
        )
        for idx in range_from_one(3):
            dlc_path = auto_updater_path()
            cmd_args = [
                dlc_path,
                "--pid",
                str(pid),
                "--version",
                str(now_version),
                "--cwd",
                dirpath,
                "--exe_name",
                filename,
            ]
            logger.debug("dlc指令为" + " ".join(cmd_args))
            p = subprocess.Popen(
                cmd_args,
                cwd="utils",
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            p.wait()

            if p.returncode == 0:
                # dlc正常退出，无需额外处理和重试
                break

            # 异常退出时，看看网盘是否有更新的版本
            last_modify_time = parse_timestamp(os.stat(dlc_path).st_mtime)
            logger.error(
                color("bold_yellow")
                + f"第{idx}次尝试DLC出错了，错误码为{p.returncode}，DLC最后一次修改时间为{last_modify_time}"
            )

            # 更新新版本，然后重试
            logger.info(color("bold_green") + "网盘中最新版本有可能已经修复dlc的该问题，将尝试更新dlc为最新版本")
            download_from_alist(os.path.basename(auto_updater_path()), os.path.dirname(auto_updater_path()))

        logger.info(color("bold_yellow") + "当前版本为最新版本，不需要更新~")
    except Exception as e:
        logger.error("自动更新出错了，报错信息如下", exc_info=e)


def has_buy_auto_updater_dlc(qq_accounts: list[str], max_retry_count=3, retry_wait_time=5, show_log=False) -> bool:
    has_buy, _ = has_buy_auto_updater_dlc_and_query_ok(qq_accounts, max_retry_count, retry_wait_time, show_log)
    return has_buy


def has_buy_auto_updater_dlc_and_query_ok(
    qq_accounts: list[str], max_retry_count=3, retry_wait_time=5, show_log=False
) -> tuple[bool, bool]:
    """
    查询是否购买过dlc，返回 [是否有资格，查询是否成功]
    """
    logger.debug("尝试由服务器代理查询购买DLC信息，请稍候片刻~")
    user_buy_info, query_ok = get_user_buy_info_from_server(qq_accounts)
    if query_ok:
        return user_buy_info.infer_has_buy_dlc(), True

    logger.debug("服务器查询DLC信息失败，尝试直接从网盘查询~")
    for idx in range(max_retry_count):
        try:
            uploader = Uploader()
            has_no_users = True
            for remote_filename in [
                uploader.buy_auto_updater_users_filename,
                uploader.cs_buy_auto_updater_users_filename,
            ]:
                try:
                    user_list_filepath = uploader.download_file_in_folder(
                        uploader.folder_online_files,
                        remote_filename,
                        downloads_dir,
                        show_log=show_log,
                        try_compressed_version_first=True,
                    )
                except FileNotFoundError:
                    # 如果网盘没有这个文件，就跳过
                    continue

                buy_users = []
                with open(str(user_list_filepath), encoding="utf-8") as data_file:
                    buy_users = json.load(data_file)

                if len(buy_users) != 0:
                    has_no_users = False

                for qq in qq_accounts:
                    if qq in buy_users:
                        return True, True

                logger.debug(
                    "DLC购买调试日志：\n"
                    f"remote_filename={remote_filename}\n"
                    f"账号列表={qq_accounts}\n"
                    f"用户列表={buy_users}\n"
                )

            if has_no_users:
                # note: 如果读取失败或云盘该文件列表为空，则默认所有人都放行
                return True, True

            return False, True
        except Exception as e:
            logFunc = logger.debug
            if use_by_myself():
                logFunc = logger.error
            logFunc(f"第{idx + 1}次检查是否购买DLC时出错了，稍后重试", exc_info=e)
            time.sleep(retry_wait_time)

    return True, True


def get_user_buy_info(
    qq_accounts: list[str], max_retry_count=3, retry_wait_time=5, show_log=False, show_dlc_info=True
) -> BuyInfo:
    logger.info(
        f"如果卡在这里不能动，请先看看网盘里是否有新版本~ 如果新版本仍无法解决，可加群反馈~ 链接：{config().common.netdisk_link}"
    )

    if len(qq_accounts) == 0:
        # 没有传入QQ号的话，直接返回默认值
        return BuyInfo()

    logger.debug("尝试由服务器代理查询付费信息，请稍候片刻~")
    user_buy_info, query_ok = get_user_buy_info_from_server(qq_accounts)

    if not query_ok:
        logger.debug("服务器查询失败，尝试直接从网盘查询~")
        user_buy_info, _ = get_user_buy_info_from_netdisk(qq_accounts, max_retry_count, retry_wait_time, show_log)
        has_buy_dlc = has_buy_auto_updater_dlc(qq_accounts, max_retry_count, retry_wait_time, show_log)

        try_add_extra_times(user_buy_info, has_buy_dlc, show_dlc_info)

    try_notify_new_pay_info(qq_accounts, user_buy_info)

    return user_buy_info


def get_user_buy_info_from_server(qq_accounts: list[str]) -> tuple[BuyInfo, bool]:
    buyInfo = BuyInfo()
    ok = False

    try:
        if len(qq_accounts) != 0:

            def fetch_query_info_from_server() -> str:
                server_addr = get_pay_server_addr()
                raw_res = requests.post(f"{server_addr}/query_buy_info", json=qq_accounts, timeout=20)

                if raw_res.status_code == 200:
                    return raw_res.text
                else:
                    return ""

            raw_res_text = with_cache(
                cache_name_user_buy_info,
                json.dumps(qq_accounts),
                cache_max_seconds=600,
                cache_miss_func=fetch_query_info_from_server,
                cache_validate_func=None,
            )
            if raw_res_text != "":
                ok = True
                buyInfo.auto_update_config(json.loads(raw_res_text))

    except Exception as e:
        logger.debug("出错了", f"请求出现异常，报错如下:\n{e}")

    return buyInfo, ok


def get_user_buy_info_from_netdisk(
    qq_accounts: list[str], max_retry_count=3, retry_wait_time=5, show_log=False
) -> tuple[BuyInfo, bool]:
    default_user_buy_info = BuyInfo()
    for try_idx in range(max_retry_count):
        try:
            # 默认设置首个qq为购买信息
            default_user_buy_info.qq = qq_accounts[0]

            uploader = Uploader()
            has_no_users = True

            remote_filenames = [uploader.user_monthly_pay_info_filename, uploader.cs_user_monthly_pay_info_filename]
            import copy

            # 单种渠道内选择付费结束时间最晚的，手动和卡密间则叠加
            user_buy_info_list = [copy.deepcopy(default_user_buy_info) for v in remote_filenames]
            for idx, remote_filename in enumerate(remote_filenames):
                user_buy_info = user_buy_info_list[idx]

                try:
                    buy_info_filepath = uploader.download_file_in_folder(
                        uploader.folder_online_files,
                        remote_filename,
                        downloads_dir,
                        show_log=show_log,
                        try_compressed_version_first=True,
                    )
                except FileNotFoundError:
                    # 如果网盘没有这个文件，就跳过
                    continue

                buy_users: dict[str, BuyInfo] = {}

                def update_if_longer(qq: str, info: BuyInfo, buy_users: dict[str, BuyInfo]):
                    if qq not in buy_users:
                        buy_users[qq] = info
                    else:
                        # 如果已经在其他地方已经出现过这个QQ，则仅当新的付费信息过期时间较晚时才覆盖
                        old_info = buy_users[qq]
                        if time_less(old_info.expire_at, info.expire_at):
                            buy_users[qq] = info

                with open(str(buy_info_filepath), encoding="utf-8") as data_file:
                    raw_infos = json.load(data_file)
                    for qq, raw_info in raw_infos.items():
                        info = BuyInfo().auto_update_config(raw_info)
                        update_if_longer(qq, info, buy_users)
                        for game_qq in info.game_qqs:
                            update_if_longer(game_qq, info, buy_users)

                if len(buy_users) != 0:
                    has_no_users = False

                qqs_to_check = list(qq for qq in qq_accounts)
                for i in range(idx):
                    other_way_user_buy_info = user_buy_info_list[i]
                    append_if_not_in(qqs_to_check, other_way_user_buy_info.qq)
                    for qq in other_way_user_buy_info.game_qqs:
                        append_if_not_in(qqs_to_check, qq)

                for qq in qqs_to_check:
                    if qq in buy_users:
                        if time_less(user_buy_info.expire_at, buy_users[qq].expire_at):
                            # 若当前配置的账号中有多个账号都付费了，选择其中付费结束时间最晚的那个
                            user_buy_info = buy_users[qq]

                user_buy_info_list[idx] = user_buy_info

            if has_no_users:
                # note: 如果读取失败或云盘该文件列表为空，则默认所有人都放行
                default_user_buy_info.expire_at = "2120-01-01 00:00:00"
                return default_user_buy_info, True

            merged_user_buy_info = copy.deepcopy(default_user_buy_info)
            for user_buy_info in user_buy_info_list:
                if len(user_buy_info.buy_records) == 0:
                    continue

                if len(merged_user_buy_info.buy_records) == 0:
                    merged_user_buy_info = copy.deepcopy(user_buy_info)
                else:
                    merged_user_buy_info.merge(user_buy_info)

            return merged_user_buy_info, True
        except Exception as e:
            logFunc = logger.debug
            if use_by_myself():
                logFunc = logger.error
            logFunc(f"第{try_idx + 1}次检查是否付费时出错了，稍后重试", exc_info=e)
            time.sleep(retry_wait_time)

    return default_user_buy_info, False


def try_add_extra_times(user_buy_info: BuyInfo, has_buy_dlc: bool, show_dlc_info: bool):
    if has_buy_dlc:
        # hack: 这里不特别去除2021.4.11之前未购买按月付费的情况，是为了与服务器保持一致。目前从服务器解析回来时，判定是否购买dlc，是通过dlc的那个额外条目来判定的，移除后将无法判定。当然也可以选择添加新字段，但这里为了省事和兼容之前版本，就不修改了
        add_extra_times_for_dlc(user_buy_info, show_dlc_info)

    # 根据需要可以在这里添加额外的赠送时长逻辑
    # ...


def add_extra_times_for_dlc(user_buy_info: BuyInfo, show_dlc_info: bool):
    # 购买过dlc的用户可以获得两个月免费使用付费功能的时长
    max_present_times = datetime.timedelta(days=2 * 31)

    free_start_time = parse_time("2021-02-08 00:00:00")
    free_end_time = free_start_time + max_present_times

    not_paied_times = datetime.timedelta()
    fixup_times = max_present_times

    if user_buy_info.total_buy_month == 0:
        # 如果从未购买过，过期时间改为DLC免费赠送结束时间
        expire_at_time = free_end_time
    else:
        # 计算与免费时长重叠的时长，补偿这段时间
        user_buy_info.buy_records = sorted(user_buy_info.buy_records, key=lambda record: parse_time(record.buy_at))
        last_end = min(free_start_time, parse_time(user_buy_info.buy_records[0].buy_at))
        for record in user_buy_info.buy_records:
            buy_at = parse_time(record.buy_at)

            if buy_at > last_end:
                # 累加未付费区间
                not_paied_times += buy_at - last_end

                # 从新的位置开始计算结束时间
                last_end = buy_at + datetime.timedelta(days=record.buy_month * 31)
            else:
                # 从当前结束时间叠加时长（未产生未付费区间）
                last_end = last_end + datetime.timedelta(days=record.buy_month * 31)

        fixup_times = max(max_present_times - not_paied_times, datetime.timedelta())

        expire_at_time = parse_time(user_buy_info.expire_at) + fixup_times

    old_expire_at = user_buy_info.expire_at
    user_buy_info.expire_at = format_time(expire_at_time)
    user_buy_info.buy_records.insert(
        0,
        BuyRecord().auto_update_config(
            {
                "buy_month": 2,
                "buy_at": format_time(free_start_time),
                "reason": "自动更新DLC赠送(自2.8至今最多累积未付费时长两个月***注意不是从购买日开始计算***)",
            }
        ),
    )

    if show_dlc_info:
        logger.info(
            color("bold_yellow") + "注意：自动更新和按月付费是两个完全不同的东西，具体区别请看 付费指引/付费指引.docx"
        )
        logger.info(
            color("bold_cyan")
            + "当前运行的qq中已有某个qq购买过自动更新dlc\n"
            + color("bold_green")
            + f"\t自{free_start_time}开始将累积可免费使用付费功能两个月，累计未付费时长为{not_paied_times}，将补偿{fixup_times}\n"
            + f"\t实际过期时间为{user_buy_info.expire_at}(原结束时间为{old_expire_at})"
        )
        logger.info(
            color("bold_black") + "若对自动更新送的两月有疑义，请看付费指引的常见问题章节\n"
            "\t请注意这里的两月是指从2.8开始累积未付费时长最多允许为两个月，是给2.8以前购买DLC的朋友的小福利\n"
            "\t如果4.11以后才购买就享受不到这个的，因为购买时自2.8开始的累积未付费时长已经超过两个月"
        )


def try_notify_new_pay_info(
    qq_accounts: list[str], latest_user_buy_info: BuyInfo, show_message_box=True
) -> tuple[bool, bool, list[BuyRecord]]:
    new_buy_dlc = False
    new_buy_monthly_pay = False
    new_buy_monthly_pay_records: list[BuyRecord] = []

    # 获取上次保存的付费信息，对比是否产生了新的付费
    # note: 这里的key改成最新查询到的购买记录的主QQ
    #   这样即使因为新的购买，导致这次购买所属的主QQ与上次不一样时，也不会因实际对比对象完全不同，而导致展示的结果很奇怪
    db = UserBuyInfoDB().with_context(latest_user_buy_info.qq).load()

    # ps: 1999是服务器查询失败时填充的默认值，用于确保服务器异常时不影响正常使用，应排除这种情况
    fake_month = 1999

    # 在有上次保存信息的时候才尝试对比
    if db.file_created:
        # 检查dlc
        if not db.buy_info.infer_has_buy_dlc() and latest_user_buy_info.infer_has_buy_dlc():
            new_buy_dlc = True
            if show_message_box:
                async_message_box("新购买的自动更新dlc已到账，请按 付费指引 中的使用说明进行使用~", "到账提醒")

        # 检查是否有新的按月付费
        # 判定条件
        # 1. 比上次保存的月数多
        # 2. 上次保存的不是服务器异常时的保底数据
        if (
            latest_user_buy_info.total_buy_month > db.buy_info.total_buy_month
            and latest_user_buy_info.total_buy_month != fake_month
        ):
            # 计算新增的按月付费。
            # 基础假设：新增的付费时间靠后，因此只需要计算出比之前计算的按月付费条数多出来的即可。
            old_buy_records = db.buy_info.get_normal_buy_records()
            latest_buy_records = latest_user_buy_info.get_normal_buy_records()

            new_months = latest_user_buy_info.total_buy_month - db.buy_info.total_buy_month

            new_buy_monthly_pay = True
            new_buy_monthly_pay_records = latest_buy_records[len(old_buy_records) :]

            msg = f"新购买的 {new_months} 月 按月付费已到账，详情如下"
            msg += "\n购买详情如下：\n" + "\n".join(
                "\t" + f"{record.buy_at} {record.reason} {record.buy_month} 月"
                for record in new_buy_monthly_pay_records
            )

            if show_message_box:
                async_message_box(msg, "到账提醒")

    # 保存新的付费信息
    # 以下情况需要保存数据
    # 1. 新购买了dlc
    # 2. 有新购买按月付费
    # 3. 第一次保存
    # 4. 之前保存了服务器异常时的保底数据
    if new_buy_dlc or new_buy_monthly_pay or not db.file_created or db.buy_info.total_buy_month == fake_month:
        logger.info("有新的付费记录，更新本地付费记录，用于下次运行时进行对比")
        db.buy_info = latest_user_buy_info
        db.save()

    return new_buy_dlc, new_buy_monthly_pay, new_buy_monthly_pay_records


def show_multiprocessing_info(cfg: Config):
    msg = ""
    if cfg.common.enable_multiprocessing:
        msg += f"当前已开启多进程模式，进程池大小为 {get_pool_size()}"
        if cfg.common.enable_super_fast_mode:
            msg += "\n\n超快速模式已开启，将并行运行各个账号的各个活动~"
        else:
            msg += "\n\n超快速模式未开启，将并行运行各个账号。如需同时运行各个活动，可开启该模式~"

        msg += "\n\n如果每次运行时出现以下情况，请在【配置工具/公共配置/多进程】中调整进程池大小，或者关闭多进程相关模式（仅影响运行速度，不影响运行结果）"
        msg += "\n1. 启动时明显卡顿"
        msg += "\n2. 电脑死机"
        msg += "\n3. wegame双开功能失效"
    else:
        msg += "未开启多进程模式，如需开启，可前往配置工具开启"

    async_message_box(msg, "多进程配置提示", show_once=True, color_name="bold_yellow")

    # 上报多进程相关功能的使用情况
    increase_counter(ga_category="enable_multiprocessing", name=cfg.common.enable_multiprocessing)
    increase_counter(ga_category="enable_super_fast_mode", name=cfg.common.enable_super_fast_mode)
    if cfg.common.enable_multiprocessing:
        increase_counter(ga_category="cpu_count", name=cpu_count())
        increase_counter(ga_category="raw_pool_size", name=cfg.common.multiprocessing_pool_size)
        increase_counter(ga_category="final_pool_size", name=get_pool_size())


def show_notices():
    def _cb():
        # 初始化
        nm = NoticeManager()
        # 展示公告
        nm.show_notices()

    async_call(_cb)


disable_flag_file = ".no_sync_configs"
sync_configs_done_flag_file = ".sync_configs_done"


@try_except()
def try_save_configs_to_user_data_dir():
    """
    运行完毕，尝试从当前目录同步配置到%APPDATA%/djc_helper
    """
    if os.path.exists(disable_flag_file):
        logger.info(f"当前目录存在 {disable_flag_file}，故而不尝试同步配置")
        return

    cwd = os.getcwd()
    appdata_dir = get_appdata_save_dir()

    logger.info(f"运行完毕，将尝试同步当前目录的配置文件到 {appdata_dir}")
    sync_configs(cwd, appdata_dir)

    # 为了方便排查问题，在备份目录写入备份信息
    make_sure_dir_exists(appdata_dir)
    with open(os.path.join(appdata_dir, "__backup_info.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "app_version": now_version,
                "app_time": ver_time,
                "backup_time": format_now(),
            },
            f,
            indent=4,
            ensure_ascii=False,
        )

    # 顺带同时保存多个版本的配置文件，方便找回
    save_multiple_version_config()


def save_multiple_version_config():
    cwd = os.getcwd()

    config_backup_dir = get_config_backup_dir()
    current_backup_dir = os.path.join(config_backup_dir, format_now("%Y-%m-%d %H_%M_%S"))

    config_file = "config.toml"
    if os.path.isfile("config.toml.local"):
        config_file = "config.toml.local"

    source = os.path.join(cwd, config_file)
    destination = os.path.join(current_backup_dir, config_file)

    logger.info(
        color("bold_yellow")
        + f"单独保存多个版本的 {config_file} 到 {config_backup_dir}，可在该目录中找到之前版本的配置文件，方便在意外修改配置且已经同步到备份目录时仍能找回配置"
    )
    make_sure_dir_exists(current_backup_dir)

    # 备份配置文件
    shutil.copy2(source, destination)

    # 为避免备份数据过大，超过一定大小时进行删除
    clean_dir_to_size(config_backup_dir, max_logs_size=20 * MiB)


@try_except()
def try_load_old_version_configs_from_user_data_dir():
    """
    若是首次运行，尝试从%APPDATA%/djc_helper同步配置到当前目录
    """
    cwd = os.getcwd()
    appdata_dir = get_appdata_save_dir()

    logger.info(
        color("bold_green") + f"已开启首次运行时自动同步配置本机配置功能，将尝试从 {appdata_dir} 同步配置到 {cwd}"
    )
    logger.info(color("bold_yellow") + f"如果不需要同步配置，可在当前目录创建 {disable_flag_file} 文件")

    if os.path.exists(disable_flag_file):
        logger.info(f"当前目录存在 {disable_flag_file}，故而不尝试同步配置")
        return

    if run_from_src():
        logger.info("当前使用源码运行，无需同步配置")
        return

    if not os.path.isdir(appdata_dir):
        logger.info("当前没有备份的旧版本配置，无需同步配置")
        return

    if not is_first_run("sync_config"):
        logger.info("当前不是首次运行，无需同步配置")
        return

    # 上面的判定是否是首次运行的功能，偶尔会因为windows下创建目录失败而无法正常判定，增加个基于标记文件的保底措施
    if exists_flag_file(sync_configs_done_flag_file):
        logger.info(f"当前目录存在 {sync_configs_done_flag_file}，说明已经完成过同步流程，将不再尝试")
        return
    # 标记为已同步
    open(sync_configs_done_flag_file, "a").close()

    logger.info("符合同步条件，将开始同步流程~")
    sync_configs(appdata_dir, cwd)


def get_appdata_save_dir() -> str:
    return os.path.join(get_appdata_dir(), "djc_helper")


def get_config_backup_dir() -> str:
    return os.path.join(get_appdata_save_dir(), "..backups")


def check_proxy(cfg: Config):
    if cfg.common.bypass_proxy:
        logger.info("当前配置为无视系统代理，将直接访问网络。")
        bypass_proxy()
    else:
        logger.info(
            "当前未开启无视系统代理配置，如果使用了vpn，将优先通过vpn进行访问。如果在国内，并且经常用到vpn，建议打开该配置"
        )


def demo_show_notices():
    show_notices()
    input("等待公告下载完毕，测试完毕点击任何键即可退出....\n")


def demo_try_report_pay_info():
    # 读取配置信息
    load_config("config.toml")
    cfg = config()

    cfg.account_configs[0].account_info.uin = "o" + "1054073896"

    # cfg.common.log_level = "debug"
    # from config import to_raw_type
    # cfg.common.on_config_update(to_raw_type(cfg.common))

    logger.info("尝试获取按月付费信息")
    user_buy_info = get_user_buy_info(cfg.get_qq_accounts())

    try_report_pay_info(cfg, user_buy_info)
    input("等待几秒，确保上传完毕后再点击enter键")


def demo_main():
    need_check_bind_and_skey = True
    # need_check_bind_and_skey = False

    enable_multiprocessing = True
    # enable_multiprocessing = False

    # # 最大化窗口
    # logger.info("尝试最大化窗口，打包exe可能会运行的比较慢")
    # maximize_console()

    logger.warning(f"开始运行DNF蚊子腿小助手，ver={now_version} {ver_time}，powered by {author}")
    logger.warning(
        color("fg_bold_cyan")
        + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，请帮忙在你的小团体群或公会群宣传一下，谢谢~"
    )

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        raise Exception("未找到有效的账号配置，请检查是否正确配置。ps：多账号版本配置与旧版本不匹配，请重新配置")

    if enable_multiprocessing:
        init_pool(cfg.get_pool_size())
    else:
        init_pool(0)
        cfg.common.enable_multiprocessing = False
        cfg.common.enable_super_fast_mode = False

    if need_check_bind_and_skey:
        check_all_skey_and_pskey(cfg)
        check_djc_role_binding()

    # note: 用于本地测试main的相关逻辑
    # 查询付费信息供后面使用
    user_buy_info = BuyInfo()
    if need_check_bind_and_skey:
        show_head_line("查询付费信息")
        logger.warning("开始查询付费信息，请稍候~")
        user_buy_info = get_user_buy_info(cfg.get_qq_accounts())
        show_buy_info(user_buy_info, cfg, need_show_message_box=False)
    else:
        user_buy_info.expire_at = "2120-01-01 00:00:00"

    sas(cfg, "启动时展示账号概览", user_buy_info)
    # try_join_xinyue_team(cfg)
    # run(cfg)
    # try_take_xinyue_team_award(cfg)
    # try_xinyue_sailiyam_start_work(cfg)
    # show_lottery_status("运行完毕展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg, need_show_tips=True)
    # auto_send_cards(cfg)
    # show_extra_infos(cfg)
    # show_lottery_status("卡片赠送完毕后展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg)
    # show_accounts_status(cfg, "运行完毕展示账号概览")
    # show_support_pic_monthly(cfg)
    # show_tips(cfg)
    # if cfg.common._show_usage:
    #     show_usage()
    # check_update(cfg)


def demo_show_buy_info():
    user_buy_info = BuyInfo()
    user_buy_info.total_buy_month = 1
    user_buy_info.expire_at = "2021-07-01 00:00:00"
    show_buy_info(user_buy_info, config())
    os.system("PAUSE")


def demo_show_activities_summary():
    # 读取配置信息
    load_config("config.toml")
    cfg = config()

    user_buy_info = BuyInfo()
    user_buy_info.expire_at = "2120-01-01 00:00:00"
    show_activities_summary(cfg, user_buy_info)


def demo_pay_info():
    # 读取配置信息
    load_config("config.toml")
    cfg = config()

    cfg.account_configs[0].account_info.uin = "o" + "1054073896"

    # cfg.common.log_level = "debug"
    # from config import to_raw_type
    # cfg.common.on_config_update(to_raw_type(cfg.common))

    # from util import reset_cache
    # reset_cache(cache_name_user_buy_info)

    logger.info("尝试获取DLC信息")
    has_buy_auto_update_dlc = has_buy_auto_updater_dlc(cfg.get_qq_accounts())
    logger.info("尝试获取按月付费信息")
    user_buy_info = get_user_buy_info(cfg.get_qq_accounts())

    if has_buy_auto_update_dlc:
        dlc_info = "当前某一个账号已购买自动更新DLC(若对自动更新送的两月有疑义，请看付费指引的常见问题章节)"
    else:
        dlc_info = "当前所有账号均未购买自动更新DLC"
    monthly_pay_info = user_buy_info.description()

    logger.info(dlc_info)
    logger.info(color("bold_cyan") + monthly_pay_info)


def demo_show_tips():
    # 读取配置信息
    load_config("config.toml")
    cfg = config()

    show_tips(cfg)
    pause()


def demo_try_auto_update_ignore_permission_on_special_case():
    remote_config = config_cloud()

    now_version = "20.4.0"

    can_ignore = remote_config.try_auto_update_ignore_permission.can_ignore(now_version, get_now())

    logger.info(f"当前版本为 {now_version}，是否可以忽略权限检查：{can_ignore}")
    pause()


def demo_is_ark_lottery_enabled():
    from djc_helper import is_ark_lottery_enabled

    enabled = is_ark_lottery_enabled()
    logger.info(f"is_ark_lottery_enabled={enabled}")


if __name__ == "__main__":
    freeze_support()

    # demo_show_notices()
    # demo_show_activities_summary()

    # demo_show_tips()
    # demo_try_auto_update_ignore_permission_on_special_case()
    # show_following_regular_activity_expected_info()

    # demo_main()
    demo_pay_info()
