import random
import subprocess
import webbrowser
from sys import exit
from typing import Dict

import win32api

from config import load_config, config, XinYueOperationConfig, Config
from dao import BuyInfo, BuyRecord
from djc_helper import DjcHelper
from qzone_activity import QzoneActivity
from setting import *
from show_usage import get_count, my_usage_counter_name
from update import check_update_on_start, get_update_info
from upload_lanzouyun import Uploader, lanzou_cookie
from util import *
from version import *


def has_any_account_in_normal_run(cfg):
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
        os.system("PAUSE")
        exit(-1)

    _show_head_line("启动时检查各账号是否在道聚城绑定了dnf账号和任意手游账号")

    while True:
        all_binded = True
        not_binded_accounts = []

        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            logger.warning(color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name})------------")
            djcHelper = DjcHelper(account_config, cfg.common)
            if not djcHelper.check_djc_role_binding():
                all_binded = False
                not_binded_accounts.append(account_config.name)

        if all_binded:
            break
        else:
            logger.warning(color("yellow") + f"请前往道聚城将上述提示的未绑定dnf或任意手游的账号【{not_binded_accounts}】进行绑定，具体操作流程可以参考使用文档或者教学视频。")
            logger.warning(color("green") + "如果本账号不需要道聚城相关操作，可以打开配置表，将该账号的cannot_bind_dnf设为true，game_name设为无，即可跳过道聚城相关操作")
            logger.warning(color("green") + "  ps: 上面这个cannot_bind_dnf之前笔误写成了cannot_band_dnf，如果之前填过，请手动把配置名称改成cannot_bind_dnf~")
            logger.warning(color("fg_bold_cyan") + "操作完成后点击任意键即可再次进行检查流程...")
            os.system("PAUSE")

            # 这时候重新读取一遍用户修改过后的配置文件（比如把手游设为了 无 ）
            load_config("config.toml", "config.toml.local")
            cfg = config()


def check_all_skey_and_pskey(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("启动时检查各账号skey/pskey/openid是否过期")

    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        logger.warning(color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name})------------")
        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list(print_warning=False)
        djcHelper.fetch_guanjia_openid(print_warning=False)


def auto_send_cards(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("运行完毕自动赠送卡片")

    target_qqs = cfg.common.auto_send_card_target_qqs
    if len(target_qqs) == 0:
        logger.warning("未定义自动赠送卡片的对象QQ数组，将跳过本阶段")
        return

    # 统计各账号卡片数目
    logger.info("拉取各账号的卡片数据中，请耐心等待...")
    qq_to_card_name_to_counts = {}
    qq_to_prize_counts = {}
    qq_to_djcHelper = {}
    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        lr = djcHelper.fetch_pskey()
        if lr is None:
            continue
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list(print_warning=False)

        qq = uin2qq(lr.uin)
        qa = QzoneActivity(djcHelper, lr)

        qq_to_card_name_to_counts[qq] = qa.get_card_counts()
        qq_to_prize_counts[qq] = qa.get_prize_counts()
        qq_to_djcHelper[qq] = djcHelper

        logger.info(f"{idx:2d}/{len(cfg.account_configs)} 账号 {padLeftRight(account_config.name, 12)} 的数据拉取完毕")

    # 赠送卡片
    for idx, target_qq in enumerate(target_qqs):
        if target_qq in qq_to_djcHelper:
            left_times = qq_to_djcHelper[target_qq].ark_lottery_query_left_times(target_qq)
            name = qq_to_djcHelper[target_qq].cfg.name
            logger.warning(color("fg_bold_green") + f"第{idx + 1}/{len(target_qqs)}个赠送目标账号 {name}({target_qq}) 今日仍可被赠送 {left_times} 次卡片")
            # 最多赠送目标账号今日仍可接收的卡片数
            for i in range(left_times):
                send_card(target_qq, qq_to_card_name_to_counts, qq_to_prize_counts, qq_to_djcHelper, target_qqs)

            # 赠送卡片完毕后尝试领取奖励和抽奖
            djcHelper = qq_to_djcHelper[target_qq]
            lr = djcHelper.fetch_pskey()
            if lr is not None:
                logger.info("赠送完毕，尝试领取奖励和抽奖")
                qa = QzoneActivity(djcHelper, lr)
                qa.take_ark_lottery_awards(print_warning=False)
                qa.try_lottery_using_cards(print_warning=False)


def send_card(target_qq, qq_to_card_name_to_counts, qq_to_prize_counts, qq_to_djcHelper, target_qqs):
    card_info_map = parse_card_group_info_map(qq_to_djcHelper[target_qq].zzconfig)
    # 检查目标账号是否有可剩余的兑换奖励次数
    has_any_left_gift = False
    for name, count in qq_to_prize_counts[target_qq].items():
        if count > 0:
            has_any_left_gift = True

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
        merged_card_name_to_count = {}
        for qq, card_name_to_count in qq_to_card_name_to_counts.items():
            for card_name, card_count in card_name_to_count.items():
                merged_card_name_to_count[card_name] = merged_card_name_to_count.get(card_name, 0) + card_count
        # 降序排列
        for card_name, card_count in merged_card_name_to_count.items():
            target_card_infos.append((card_name, card_count))
        target_card_infos.sort(key=lambda card: -card[1])

    # 升序遍历
    for card_name, card_count in target_card_infos:
        # 找到任意一个拥有卡片的其他账号，让他送给目标账户。默认越靠前的号越重要，因此从后面的号开始查
        for qq, card_name_to_count in reverse_map(qq_to_card_name_to_counts):
            if qq in target_qqs:
                continue
            # 如果某账户有这个卡，则赠送该当前玩家，并结束本回合赠卡
            if card_name_to_count[card_name] > 0:
                qq_to_djcHelper[qq].send_card(card_name, card_info_map[card_name].id, target_qq)
                card_name_to_count[card_name] -= 1
                qq_to_card_name_to_counts[target_qq][card_name] += 1

                name = qq_to_djcHelper[qq].cfg.name
                index = card_info_map[card_name].index
                target_name = qq_to_djcHelper[target_qq].cfg.name

                logger.warning(color("fg_bold_cyan") + f"账号 {name} 赠送一张 {index}({card_name}) 给 {target_name}")
                return


def reverse_map(map):
    kvs = list(map.items())
    kvs.reverse()
    return kvs


def show_lottery_status(ctx, cfg, need_show_tips=False):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line(ctx)

    show_end_time("2021-02-28 23:59:59")

    lottery_zzconfig = zzconfig()
    card_info_map = parse_card_group_info_map(lottery_zzconfig)
    order_map = {}
    # 卡片编码 => 名称
    for name, card_info in card_info_map.items():
        order_map[card_info.index] = name

    # 奖励展示名称 => 实际名称
    groups = [
        lottery_zzconfig.prizeGroups.group1,
        lottery_zzconfig.prizeGroups.group2,
        lottery_zzconfig.prizeGroups.group3,
        lottery_zzconfig.prizeGroups.group4,
    ]
    prizeDisplayTitles = []
    for group in groups:
        displayTitle = group.title
        if len(displayTitle) > 4 and "礼包" in displayTitle:
            # 将 全民竞速礼包 这种名称替换为 全民竞速
            displayTitle = displayTitle.replace("礼包", "")

        order_map[displayTitle] = group.title
        prizeDisplayTitles.append(displayTitle)

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

    accounts_that_should_enable_cost_card_to_lottery = []

    logger.info(tableify(heads, colSizes))
    summaryCols = [1, "总计", *[0 for card in card_indexes], *[count_with_color(0, "bold_green", show_width=printed_width(prize_index)) for prize_index in prize_indexes]]
    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        if not account_config.ark_lottery.show_status:
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        lr = djcHelper.fetch_pskey()
        if lr is None:
            continue
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list(print_warning=False)

        qa = QzoneActivity(djcHelper, lr)

        card_counts = qa.get_card_counts()
        prize_counts = qa.get_prize_counts()

        summaryCols[0] += 1

        cols = [idx, account_config.name]
        has_any_card = False
        has_any_left_gift = False
        # 处理各个卡片数目
        for card_position, card_index in enumerate(card_indexes):
            card_count = card_counts[order_map[card_index]]

            cols.append(colored_count(idx, card_count, account_config.ark_lottery.show_color))

            # 更新统计信息
            summaryCols[len(baseHeads) + card_position] += card_count

            if card_count > 0:
                has_any_card = True

        # 处理各个奖励剩余领取次数
        for prize_index in prize_indexes:
            prize_count = prize_counts[order_map[prize_index]]
            cols.append(count_with_color(prize_count, "bold_green", show_width=printed_width(prize_index)))

            if prize_count > 0:
                has_any_left_gift = True

        logger.info(tableify(cols, colSizes))

        if has_any_card and not has_any_left_gift:
            accounts_that_should_enable_cost_card_to_lottery.append(account_config.name)

    for cardIdx in range(len(card_indexes)):
        idx = len(baseHeads) + cardIdx
        summaryCols[idx] = colored_count(len(cfg.account_configs), summaryCols[idx], cfg.common.ark_lottery_summary_show_color or "fg_thin_cyan")

    logger.info(tableify(summaryCols, colSizes))

    if need_show_tips and len(accounts_that_should_enable_cost_card_to_lottery) > 0:
        accounts = ', '.join(accounts_that_should_enable_cost_card_to_lottery)
        msg = f"账户({accounts})仍有剩余卡片，但已无任何可领取礼包，建议开启消耗卡片来抽奖的功能"
        logger.warning(color("fg_bold_yellow") + msg)

    if not os.path.exists("DNF蚊子腿小助手_集卡特别版.exe"):
        logger.warning(color("bold_cyan") + (
            "以下为广告时间0-0\n"
            "如果只需要集卡功能，可以联系我购买集卡特别版哦，特别版仅包含集卡相关功能（集卡、送卡、展示卡片信息、兑换卡片奖励、使用卡片抽奖），供某些只需要集卡的朋友使用\n"
            "演示地址：https://www.bilibili.com/video/BV1zA411H7mP\n"
            "价格：6.66元\n"
            "购买方式：加小助手群后QQ私聊我付款截图，我确认无误后会将DLC以及用法发给你，并拉到一个无法主动加入的专用群，通过群文件分发该DLC的后续更新版本~\n"
            "PS：这个DLC相当于是小助手的子集，用于仅处理集卡相关内容，之前听到有的朋友有这样的需求，所以特地制作的，是否购买自行考量哈。\n"
            "如果购买的话能鼓励我花更多时间来维护小助手，支持新的蚊子腿以及优化使用体验(oﾟ▽ﾟ)o  \n"
            "\n"
            "2021.2.2 update: 本轮集卡我又换完啦，有需要买卡的朋友可以加群私聊我购买哦~依旧是一元一张任意卡。先问下有没有卡，得到确定回复后直接发付款截图和要收卡片的QQ号码即可（不需要加好友）"
        ))


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


def show_accounts_status(cfg, ctx):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line(ctx)

    heads = ["序号", "账号名", "启用状态", "聚豆余额", "聚豆历史总数", "成就点", "心悦组队", "闪光杯出货数", "赛丽亚卡片", "爆竹积分"]
    colSizes = [4, 12, 8, 8, 12, 6, 8, 12, 14, 8]

    logger.info(tableify(heads, colSizes))
    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()

        status = "启用" if account_config.is_enabled() else "未启用"

        djc_info = djcHelper.query_balance("查询聚豆概览", print_res=False)["data"]
        djc_allin, djc_balance = int(djc_info['allin']), int(djc_info['balance'])

        xinyue_info = djcHelper.query_xinyue_info("查询心悦成就点概览", print_res=False)
        teaminfo = djcHelper.query_xinyue_teaminfo(print_res=False)
        team_score = "无队伍"
        if teaminfo.id != "":
            team_score = f"{teaminfo.score}/20"
            fixed_team = djcHelper.get_fixed_team()
            if fixed_team is not None:
                team_score = f"[{fixed_team.id}]{team_score}"

        shanguang_equip_count = djcHelper.query_dnf_shanguang_equip_count(print_warning=False)

        sailiya_cards = djcHelper.query_majieluo_card_info()

        firecrackers_points = djcHelper.query_firecrackers_points()

        cols = [idx, account_config.name, status, djc_balance, djc_allin, xinyue_info.score, team_score, shanguang_equip_count, sailiya_cards, firecrackers_points]
        logger.info(color("fg_bold_green") + tableify(cols, colSizes, need_truncate=True))

    logger.info("")
    _show_head_line("付费相关信息")
    user_buy_info = get_user_buy_info(cfg)
    show_buy_info(user_buy_info)


def try_join_xinyue_team(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("尝试加入心悦固定队")

    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        logger.info("")
        logger.warning(color("fg_bold_yellow") + f"------------尝试第{idx}个账户({account_config.name})------------")

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        # 尝试加入固定心悦队伍
        djcHelper.try_join_fixed_xinyue_team()

        if cfg.common._debug_run_first_only:
            logger.warning("调试开关打开，不再处理后续账户")
            break


def run(cfg):
    _show_head_line("开始核心逻辑")

    user_buy_info = get_user_buy_info(cfg)
    show_buy_info(user_buy_info)

    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.is_enabled():
            logger.info(f"第{idx}个账号({account_config.name})未启用，将跳过")
            continue

        _show_head_line(f"开始处理第{idx}个账户({account_config.name})")

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.run(user_buy_info)

        if cfg.common._debug_run_first_only:
            logger.warning("调试开关打开，不再处理后续账户")
            break


def try_take_xinyue_team_award(cfg):
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
        logger.warning(color("fg_bold_green") + f"------------开始尝试为第{idx}个账户({account_config.name})领取心悦组队奖励------------")

        if len(account_config.xinyue_operations) == 0:
            logger.warning("未设置心悦相关操作信息，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        xinyue_info = djcHelper.query_xinyue_info("获取心悦信息", print_res=False)

        op_cfgs = [("513818", "查询小队信息"), ("514385", "领取组队奖励")]

        xinyue_operations = []
        for opcfg in op_cfgs:
            op = XinYueOperationConfig()
            op.iFlowId, op.sFlowName = opcfg
            op.count = 1
            xinyue_operations.append(op)

        for op in xinyue_operations:
            djcHelper.do_xinyue_op(xinyue_info.xytype, op)

        if cfg.common._debug_run_first_only:
            logger.warning("调试开关打开，不再处理后续账户")
            break


def try_xinyue_sailiyam_start_work(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("尝试派赛利亚出去打工")

    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.is_enabled():
            # 未启用的账户的账户不走该流程
            continue

        logger.info("")
        logger.warning(color("fg_bold_green") + f"------------开始处理第{idx}个账户({account_config.name})的赛利亚的打工和领工资~------------")

        djcHelper = DjcHelper(account_config, cfg.common)
        if account_config.function_switches.get_xinyue_sailiyam or account_config.function_switches.disable_most_activities:
            # 先尝试领工资
            djcHelper.show_xinyue_sailiyam_work_log()
            djcHelper.xinyue_sailiyam_op("领取工资", "714229", iPackageId=djcHelper.get_xinyue_sailiyam_package_id())
            djcHelper.xinyue_sailiyam_op("全勤奖", "715724")

            # 然后派出去打工
            djcHelper.xinyue_sailiyam_op("出去打工", "714255")

            logger.info("等待一会，避免请求过快")
            time.sleep(3)

        logger.info(color("fg_bold_cyan") + djcHelper.get_xinyue_sailiyam_workinfo())
        logger.info(color("fg_bold_cyan") + djcHelper.get_xinyue_sailiyam_status())


def show_buy_info(user_buy_info: BuyInfo):
    msg = f"{user_buy_info.qq} 付费内容过期时间为{user_buy_info.expire_at}，累计购买{user_buy_info.total_buy_month}个月。"
    if len(user_buy_info.buy_records) != 0:
        msg += "购买详情如下：\n" + '\n'.join('\t' + f'{record.buy_at} {record.reason} {record.buy_month} 月' for record in user_buy_info.buy_records)
    logger.info(color("bold_cyan") + msg)

    if not user_buy_info.is_active() and is_weekly_first_run("show_buy_info"):
        threading.Thread(target=show_buy_info_sync, args=(user_buy_info,), daemon=True).start()
        wait_seconds = 15
        logger.info(color("bold_green") + f"等待{wait_seconds}秒，确保看完这段话~")
        time.sleep(wait_seconds)


def show_buy_info_sync(msg):
    usedDays = get_count(my_usage_counter_name, "all")
    message = (
        f"Hello~ 你已经累积使用小助手{usedDays}天，希望小助手为你节省了些许时间和精力(●—●)\n"
        "\n"
        "2.2号添加了一个付费弹窗，但是截至2.6晚上六点，仅有不到百分之一的使用者进行了付费。\n"
        "考虑到近日来花在维护小助手上的时间比较久，因此本人决定，自2021-02-06 00:00:00之后添加的所有短期活动都将只能在付费生效期间使用，此前已有的功能（如道聚城、心悦）或之后出的长期功能都将继续免费使用。\n"
        "毕竟用爱发电不能持久，人毕竟是要恰饭的ლ(╹◡╹ლ)\n"
        "你的付费能让我更乐意使用本来用于玩DNF的闲暇时间来及时更新小助手，适配各种新出的蚊子腿活动，添加更多自动功能。( • ̀ω•́ )✧\n"
        "\n"
        "使用源码运行将不受该限制，但是使用我的打包二进制时，只有付费生效期间才能运行上述日期后的短期新活动，各位可自行决定通过付费激活还是自己研究如何使用源码去运行~\n"
        "\n"
        "目前定价为5元每月（31天）\n"
        "支付方式：\n"
        "    1. 扫描稍后弹出的付款码（左侧微信，右侧支付宝）\n"
        "    2. 加群后QQ私聊我的小号（1470237902，群昵称为 付费相关私聊我~（我是小号））以下内容：\n"
        "        2.1 付款截图\n"
        "        2.2 要使用该服务的游戏QQ号\n"
        "        2.3 ps: 私聊小号是因为大号接受太多私聊会被系统冻结- -有点危险\n"
        "（若未购买，则这个消息每周会弹出一次ヾ(=･ω･=)o）\n"
    )
    logger.warning(color("fg_bold_cyan") + message)
    if not use_by_myself():
        win32api.MessageBox(0, message, f"付费提示(〃'▽'〃)", win32con.MB_OK)
    os.popen("支持一下.png")


def check_update(cfg):
    auto_updater_path = os.path.realpath("utils/auto_updater.exe")
    if not os.path.exists(auto_updater_path):
        logger.warning(color("bold_cyan") + (
            "未发现自动更新DLC，因此自动更新功能没有激活，需要根据检查更新结果手动进行更新操作~\n"
            "-----------------\n"
            "以下为广告时间0-0\n"
            "花了两天多时间，给小助手加入了目前唯一一个付费DLC功能：自动更新（支持增量更新和全量更新）\n"
            "当没有该DLC时，所有功能将正常运行，只是需要跟以往一样，检测到更新时需要自己去手动更新\n"
            "当添加该DLC后，将额外增加自动更新功能，启动时将会判断是否需要更新，若需要则直接干掉小助手，然后更新到最新版后自动启动新版本\n"
            "演示视频: https://www.bilibili.com/video/BV1FA411W7Nq\n"
            "由于这个功能并不影响实际领蚊子腿的功能，且花费了我不少时间来倒腾这东西，所以目前决定该功能需要付费获取，暂定价为10.24元。\n"
            "想要摆脱每次有新蚊子腿更新或bugfix时，都要手动下载并转移配置文件这种无聊操作的小伙伴如果觉得这个价格值的话，可以按下面的方式购买0-0\n"
            "价格：10.24元\n"
            "购买方式：加小助手群后QQ私聊我付款截图（扫小助手目录中的[支持一下.png]付款），我确认无误后会将DLC以及用法发给你，并拉到一个无法主动加入的专用群，通过群文件分发自动更新DLC的后续更新版本~\n"
            "PS：不购买这个DLC也能正常使用蚊子腿小助手哒（跟之前版本体验一致）~只是购买后可以免去手动升级的烦恼哈哈，顺带能鼓励我花更多时间来维护小助手，支持新的蚊子腿以及优化使用体验(oﾟ▽ﾟ)o  \n"
        ))

    logger.info((
        "\n"
        "++++++++++++++++++++++++++++++++++++++++\n"
        "全部账号操作已经成功完成\n"
        "现在准备访问github仓库相关页面来检查是否有新版本\n"
        "由于国内网络问题，访问可能会比较慢，请不要立即关闭，可以选择最小化或切换到其他窗口0-0\n"
        "若有新版本会自动弹窗提示~\n"
        "++++++++++++++++++++++++++++++++++++++++\n"
    ))
    check_update_on_start(cfg.common)


def print_update_message_on_first_run_new_version():
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if is_first_run(f"print_update_message_v{now_version}"):
        try:
            ui = get_update_info(cfg.common)
            message = (
                f"新版本v{ui.latest_version}已更新完毕，具体更新内容展示如下，以供参考：\n"
                f"{ui.update_message}"
                "\n"
                "若未购买自动更新dlc，可无视下一句\n"
                "PS：自动更新会更新示例配置config.toml.example，但不会更新config.toml。不过由于基本所有活动的默认配置都是开启的，所以除非你想要关闭特定活动，或者调整活动配置，其实没必要修改config.toml\n"
            )
            logger.warning(color("bold_yellow") + message)
        except Exception as e:
            logger.warning("新版本首次运行获取更新内容失败，请自行查看CHANGELOG.MD", exc_info=e)


def show_ask_message_box_only_once():
    threading.Thread(target=show_ask_message_box_only_once_sync, daemon=True).start()


def show_ask_message_box_only_once_sync():
    return
    # 临时加一个请求帮忙弄下白嫖活动的逻辑
    if is_first_run("赛利亚卡牌"):
        message = (
            "马杰洛活动中的赛利亚卡牌，有小伙伴有多余的Q版赛利亚卡牌吗（第5个）？\n"
            "如果有多的话，可以不可以送我一张哇0-0\n"
            "\n"
            "点 确定 打开赠送页面进行赠送，点 取消 拒绝-。-\n"
        )
        res = win32api.MessageBox(0, message, "求送卡", win32con.MB_OKCANCEL)
        if res == win32con.IDOK:
            webbrowser.open("https://dnf.qq.com/cp/a20210121welfare/index.html?askforId=11820&askforUin=1054073896")
            win32api.MessageBox(0, "打开网页后登陆后点击[确认]按钮赠送就好啦~多谢啦，嘿嘿嘿0-0", "致谢", win32con.MB_ICONINFORMATION)
        else:
            win32api.MessageBox(0, "嘤嘤嘤", "TAT", win32con.MB_ICONINFORMATION)


def temp_code(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("一些小提示")

    tips = [
        (
            "【预购新春礼包送好礼】活动目前已在auto.js脚本中支持，可参考https://github.com/fzls/autojs/blob/main/qq.js使用~"
        ),
        (
            "万物皆新意 牛转阿拉德 活动只需要抽签三次，不再加入，请自行参与。链接为：https://dnf.qq.com/cp/a20210121index/"
        ),
        (
            "QQ黄钻和超级会员惠的白嫖活动只能领取一次性的幸运礼包、登录礼包、分享礼包，不再加入，请自行参与。链接分别为：\n"
            "https://act.qzone.qq.com/vip/meteor/blockly/p/6700xbe127",
            "https://act.qzone.qq.com/vip/meteor/blockly/p/6702x585e9",
        ),
    ]

    for idx, tip in enumerate(tips):
        logger.warning(color("fg_bold_yellow") + f"{idx + 1}. {tip}\n ")


def try_auto_update(cfg):
    try:
        if not cfg.common.auto_update_on_start:
            return

        pid = os.getpid()
        exe_path = sys.argv[0]
        dirpath, filename = os.path.dirname(exe_path), os.path.basename(exe_path)

        if run_from_src():
            logger.info("当前为源码模式运行，自动更新功能将不启用~请自行定期git pull更新代码")
            return

        if not exists_auto_updater_dlc():
            logger.warning(color("bold_cyan") + "未发现自动更新DLC，将跳过自动更新流程~")
            return

        if not has_buy_auto_updater_dlc(cfg):
            msg = (
                "经对比，本地所有账户均未购买DLC，似乎是从其他人手中获取的？\n"
                "小助手本体已经免费提供了，自动更新功能只是锦上添花而已。如果觉得价格不合适，可以选择手动更新，请不要在未购买的情况下使用自动更新DLC。\n"
                "目前只会跳过自动更新流程，日后若发现这类行为很多，可能会考虑将这样做的人加入本工具的黑名单，后续版本将不再允许其使用。\n"
                "目前名单是基于DLC付费群的群成员整合出来的，若之前是通过其他朋友获取到的这个DLC，并通过他来转账给我（是有这么几个，但是我记不清是谁了）。请加群私聊我当时的付款截图，我会将你加到购买名单中~\n"
                "\n"
                "（重点看下面这句话，大部分时候都属于这个情况）\n"
                "如果游戏账号和加群的QQ不一样，请把实际使用的QQ号私聊发我，我看到后会加入名单~\n"
                "\n"
                "如果没有购买，也没有向别人索取，可以直接将utils目录下的auto_updater.exe删除即可\n"
            )
            logger.warning(color("bold_yellow") + msg)
            win32api.MessageBox(0, msg, "未购买自动更新DLC", win32con.MB_ICONWARNING)
            return

        logger.info("开始尝试调用自动更新工具进行自动更新~ 当前处于测试模式，很有可能有很多意料之外的情况，如果真的出现很多问题，可以自行关闭该功能的配置")

        logger.info(f"当前进程pid={pid}, 版本={now_version}, 工作目录={dirpath}，exe名称={filename}")

        logger.info(color("bold_yellow") + "尝试启动更新器，等待其执行完毕。若版本有更新，则会干掉这个进程并下载更新文件，之后重新启动进程...(请稍作等待）")
        p = subprocess.Popen([
            auto_updater_path(),
            "--pid", str(pid),
            "--version", str(now_version),
            "--cwd", dirpath,
            "--exe_name", filename,
        ], cwd="utils", shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        logger.info(color("bold_yellow") + "当前版本为最新版本，不需要更新~")
    except Exception as e:
        logger.error("自动更新出错了，报错信息如下", exc_info=e)


def has_buy_auto_updater_dlc(cfg: Config):
    retrtCfg = cfg.common.retry
    for idx in range(retrtCfg.max_retry_count):
        try:
            uploader = Uploader(lanzou_cookie)
            user_list_filepath = uploader.download_file_in_folder(uploader.folder_online_files, uploader.buy_auto_updater_users_filename, ".cached", show_log=False)
            buy_users = []
            with open(user_list_filepath, 'r', encoding='utf-8') as data_file:
                buy_users = json.load(data_file)

            if len(buy_users) == 0:
                # note: 如果读取失败或云盘该文件列表为空，则默认所有人都放行
                return True

            for account_cfg in cfg.account_configs:
                qq = uin2qq(account_cfg.account_info.uin)
                if qq in buy_users:
                    return True

            return False
        except Exception as e:
            logFunc = logger.debug
            if use_by_myself():
                logFunc = logger.error
            logFunc(f"第{idx + 1}次检查是否购买DLC时出错了，稍后重试", exc_info=e)
            time.sleep(retrtCfg.retry_wait_time)

    return True


def get_user_buy_info(cfg: Config):
    user_buy_info = _get_user_buy_info(cfg)
    # 购买过dlc的用户可以获得两个月免费使用付费功能的时长
    if has_buy_auto_updater_dlc(cfg):
        max_present_times = datetime.timedelta(days=2 * 31)

        free_start_time = parse_time("2021-02-08 00:00:00")
        if user_buy_info.total_buy_month == 0:
            # 如果从未购买过，过期时间改为免费开始时间点
            user_buy_info.expire_at = format_time(free_start_time)

        now = datetime.datetime.now()
        since_start_time = now - free_start_time
        not_paied_time = max(since_start_time - datetime.timedelta(days=user_buy_info.total_buy_month * 31), datetime.timedelta())

        present_times = datetime.timedelta()
        if not_paied_time < max_present_times:
            # 如果当前到2.7号的未付费时长少于两个月，则补齐差值到过期时间
            present_times = max_present_times - not_paied_time

        user_buy_info.expire_at = format_time(parse_time(user_buy_info.expire_at) + present_times)
        user_buy_info.buy_records.insert(0, BuyRecord().auto_update_config({
            "buy_month": 2,
            "buy_at": free_start_time,
            "reason": "自动更新DLC赠送"
        }))
        logger.info(color("bold_green") + f"当前运行的qq中已有某个qq购买过自动更新dlc，自{free_start_time}开始将累积可免费使用付费功能两个月，目前累积未付费时长为{not_paied_time}，故而补偿{present_times}")

    return user_buy_info


def _get_user_buy_info(cfg: Config):
    retrtCfg = cfg.common.retry
    default_user_buy_info = BuyInfo()
    for idx in range(retrtCfg.max_retry_count):
        try:
            # 默认设置首个qq为购买信息
            default_user_buy_info.qq = uin2qq(cfg.account_configs[0].account_info.uin)

            uploader = Uploader(lanzou_cookie)
            buy_info_filepath = uploader.download_file_in_folder(uploader.folder_online_files, uploader.user_monthly_pay_info_filename, ".cached", show_log=False)
            buy_users = {}  # type: Dict[str, BuyInfo]
            with open(buy_info_filepath, 'r', encoding='utf-8') as data_file:
                raw_infos = json.load(data_file)
                for qq, raw_info in raw_infos.items():
                    info = BuyInfo().auto_update_config(raw_info)
                    buy_users[qq] = info
                    for game_qq in info.game_qqs:
                        buy_users[game_qq] = info

            if len(buy_users) == 0:
                # note: 如果读取失败或云盘该文件列表为空，则默认所有人都放行
                default_user_buy_info.expire_at = "2120-01-01 00:00:00"
                return default_user_buy_info

            user_buy_info = default_user_buy_info
            for account_cfg in cfg.account_configs:
                qq = uin2qq(account_cfg.account_info.uin)
                if qq in buy_users:
                    if time_less(user_buy_info.expire_at, buy_users[qq].expire_at):
                        # 若当前配置的账号中有多个账号都付费了，选择其中付费结束时间最晚的那个
                        user_buy_info = buy_users[qq]

            return user_buy_info
        except Exception as e:
            logFunc = logger.debug
            if use_by_myself():
                logFunc = logger.error
            logFunc(f"第{idx + 1}次检查是否付费时出错了，稍后重试", exc_info=e)
            time.sleep(retrtCfg.retry_wait_time)

    return default_user_buy_info


def change_title(dlcInfo=""):
    if dlcInfo == "" and exists_auto_updater_dlc():
        dlcInfo = " 自动更新豪华升级版"

    face = random.choice([
        'ヾ(◍°∇°◍)ﾉﾞ', 'ヾ(✿ﾟ▽ﾟ)ノ', 'ヾ(๑╹◡╹)ﾉ"', '٩(๑❛ᴗ❛๑)۶', '٩(๑-◡-๑)۶ ',
        'ヾ(●´∀｀●) ', '(｡◕ˇ∀ˇ◕)', '(◕ᴗ◕✿)', '✺◟(∗❛ัᴗ❛ั∗)◞✺', '(づ｡◕ᴗᴗ◕｡)づ',
        '(≧∀≦)♪', '♪（＾∀＾●）ﾉ', '(●´∀｀●)ﾉ', "(〃'▽'〃)", '(｀・ω・´)',
        'ヾ(=･ω･=)o', '(◍´꒳`◍)', '(づ●─●)づ', '｡◕ᴗ◕｡', '●﹏●',
    ])

    os.system(f"title DNF蚊子腿小助手 {dlcInfo} v{now_version} by风之凌殇 {face}")


def exists_auto_updater_dlc():
    return os.path.exists(auto_updater_path())


def auto_updater_path():
    return os.path.realpath("utils/auto_updater.exe")


def _test_main():
    need_check_bind_and_skey = True
    # need_check_bind_and_skey = False

    # # 最大化窗口
    # logger.info("尝试最大化窗口，打包exe可能会运行的比较慢")
    # maximize_console()

    logger.warning(f"开始运行DNF蚊子腿小助手，ver={now_version} {ver_time}，powered by {author}")
    logger.warning(color("fg_bold_cyan") + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开支持一下.png，扫码打赏哦~")

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        logger.error("未找到有效的账号配置，请检查是否正确配置。ps：多账号版本配置与旧版本不匹配，请重新配置")
        exit(-1)

    if need_check_bind_and_skey:
        check_all_skey_and_pskey(cfg)
        check_djc_role_binding()

    # note: 用于本地测试main的相关逻辑
    # show_accounts_status(cfg, "启动时展示账号概览")
    # try_join_xinyue_team(cfg)
    # run(cfg)
    # try_take_xinyue_team_award(cfg)
    # try_xinyue_sailiyam_start_work(cfg)
    show_lottery_status("运行完毕展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg, need_show_tips=True)
    # auto_send_cards(cfg)
    # show_lottery_status("卡片赠送完毕后展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg)
    # show_accounts_status(cfg, "运行完毕展示账号概览")
    # show_support_pic_monthly(cfg)
    # temp_code(cfg)
    # if cfg.common._show_usage:
    #     show_usage()
    # check_update(cfg)


if __name__ == '__main__':
    _test_main()
