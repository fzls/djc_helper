import json
from multiprocessing import cpu_count, freeze_support
from sys import exit

from config import AccountConfig, CommonConfig, Config, config, load_config
from const import downloads_dir
from dao import BuyInfo, BuyRecord
from djc_helper import DjcHelper, run_act
from first_run import *
from notice import NoticeManager
from pool import get_pool, init_pool
from qq_login import QQLogin
from qzone_activity import QzoneActivity
from setting import *
from show_usage import *
from update import check_update_on_start, get_update_info
from upload_lanzouyun import Uploader
from urls import Urls, get_not_ams_act_desc
from usage_count import *
from version import author


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
        pause()
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

            logger.warning(color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name}------------")
            djcHelper = DjcHelper(account_config, cfg.common)
            if not djcHelper.check_djc_role_binding():
                all_binded = False
                not_binded_accounts.append((account_config.name, account_config.qq()))

        if all_binded:
            break
        else:
            logger.warning(color("yellow") + f"请前往道聚城（未安装的话，手机上应用商城搜索 道聚城 下载安装就行）将上述提示的未绑定dnf或任意手游的账号【{not_binded_accounts}】进行绑定（就是去道聚城对应游戏页面把领奖角色给选好）")
            logger.warning(color("yellow") + (
                f"具体操作流程可以参考一下教程信息：\n"
                "1. 使用教程/使用文档.docx 【设置领奖角色】章节和【设置道聚城手游角色】章节\n"
                "2. 使用教程/道聚城自动化助手使用视频教程 中 DNF蚊子腿小助手4.1.1版本简要&完整视频教程 中 3:17 位置 关于绑定的介绍"
            ))
            logger.warning(color("green") + "如果本账号不需要道聚城相关操作，可以打开配置表，将该账号的cannot_bind_dnf设为true，game_name设为无，即可跳过道聚城相关操作")
            logger.warning(color("fg_bold_cyan") + "操作完成后点击任意键即可再次进行检查流程...")
            pause()

            # 这时候重新读取一遍用户修改过后的配置文件（比如把手游设为了 无 ）
            load_config("config.toml", "config.toml.local")
            cfg = config()


def check_all_skey_and_pskey(cfg: Config, check_skey_only=False):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("启动时检查各账号skey/pskey/openid是否过期")

    QQLogin(cfg.common).check_and_download_chrome_ahead()

    if cfg.common.enable_multiprocessing and cfg.is_all_account_auto_login():
        # 并行登陆
        logger.info(color("bold_yellow") + f"已开启多进程模式({cfg.get_pool_size()})，并检测到所有账号均使用自动登录模式，将开启并行登录模式")

        get_pool().starmap(do_check_all_skey_and_pskey, [(_idx + 1, _idx + 1, account_config, cfg.common, check_skey_only)
                                                         for _idx, account_config in enumerate(cfg.account_configs) if account_config.is_enabled()])

        logger.info("并行登陆完毕，串行加载缓存的登录信息到cfg变量中")
        check_all_skey_and_pskey_silently_sync(cfg)
    else:
        # 串行登录
        qq2index = {}

        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1

            djcHelper = do_check_all_skey_and_pskey(idx, 1, account_config, cfg.common, check_skey_only)
            if djcHelper is None:
                continue

            qq = uin2qq(djcHelper.cfg.account_info.uin)
            if qq in qq2index:
                msg = f"第{idx}个账号的实际登录QQ {qq} 与第{qq2index[qq]}个账号的qq重复，是否重复扫描了？\n\n点击确认后，程序将清除本地登录记录，并退出运行。请重新运行并按顺序登录正确的账号~"
                message_box(msg, "重复登录", color_name="fg_bold_red")
                clear_login_status()
                sys.exit(-1)

            qq2index[qq] = idx

    logger.info("全部账号检查完毕")


def do_check_all_skey_and_pskey(idx: int, window_index: int, account_config: AccountConfig, common_config: CommonConfig, check_skey_only: bool) -> Optional[DjcHelper]:
    wait_a_while(idx)

    logger.warning(color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name})------------")

    return _do_check_all_skey_and_pskey(window_index, account_config, common_config, check_skey_only)


def check_all_skey_and_pskey_silently_sync(cfg: Config):
    for account_config in cfg.account_configs:
        _do_check_all_skey_and_pskey(1, account_config, cfg.common, False)


def _do_check_all_skey_and_pskey(window_index: int, account_config: AccountConfig, common_config: CommonConfig, check_skey_only: bool) -> Optional[DjcHelper]:
    if not account_config.is_enabled():
        # 未启用的账户的账户不走该流程
        return None

    djcHelper = DjcHelper(account_config, common_config)
    djcHelper.fetch_pskey(window_index=window_index)
    djcHelper.check_skey_expired(window_index=window_index)

    if not check_skey_only:
        djcHelper.get_bind_role_list(print_warning=False)
        djcHelper.fetch_guanjia_openid(print_warning=False)

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
        logger.info(f"已开启多进程模式({cfg.get_pool_size()})，将并行拉取数据~")
        for data in get_pool().starmap(query_account_ark_lottery_info, [(_idx + 1, len(cfg.account_configs), account_config, cfg.common)
                                                                        for _idx, account_config in enumerate(cfg.account_configs) if account_config.is_enabled()]):
            account_data.append(data)
    else:
        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            account_data.append(query_account_ark_lottery_info(idx, len(cfg.account_configs), account_config, cfg.common))

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


def query_account_ark_lottery_info(idx: int, total_account: int, account_config: AccountConfig, common_config: CommonConfig) -> Tuple[Dict[str, int], Dict[str, int], DjcHelper]:
    djcHelper = DjcHelper(account_config, common_config)
    lr = djcHelper.fetch_pskey()
    if lr is None:
        return
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list(print_warning=False)

    qa = QzoneActivity(djcHelper, lr)

    card_name_to_counts = qa.get_card_counts()
    prize_counts = qa.get_prize_counts()

    logger.info(f"{idx:2d}/{total_account} 账号 {padLeftRight(account_config.name, 12)} 的数据拉取完毕")

    return card_name_to_counts, prize_counts, djcHelper


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


@try_except()
def show_lottery_status(ctx, cfg: Config, need_show_tips=False):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line(ctx)

    logger.info(get_not_ams_act_desc("集卡"))

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

    # 获取数据
    logger.warning("开始获取数据，请耐心等待~")
    rows = []
    if cfg.common.enable_multiprocessing:
        logger.info(f"已开启多进程模式({cfg.get_pool_size()})，将并行拉取数据~")
        for row in get_pool().starmap(query_lottery_status, [(_idx + 1, account_config, cfg.common, card_indexes, prize_indexes, order_map)
                                                             for _idx, account_config in enumerate(cfg.account_configs) if account_config.is_enabled()]):
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
    summaryCols = [1, "总计", *[0 for card in card_indexes], *[count_with_color(0, "bold_green", show_width=printed_width(prize_index)) for prize_index in prize_indexes]]
    for row in rows:
        summaryCols[0] += 1
        for i in range(2, 2 + 12):
            summaryCols[i] += row[i]

    for cardIdx in range(len(card_indexes)):
        idx = len(baseHeads) + cardIdx
        summaryCols[idx] = colored_count(len(cfg.account_configs), summaryCols[idx], cfg.common.ark_lottery_summary_show_color or "fg_thin_cyan")

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

    # 打印提示
    if need_show_tips and len(accounts_that_should_enable_cost_card_to_lottery) > 0:
        accounts = ', '.join(accounts_that_should_enable_cost_card_to_lottery)
        msg = f"账户({accounts})仍有剩余卡片，但已无任何可领取礼包，建议开启消耗卡片来抽奖的功能"
        logger.warning(color("fg_bold_yellow") + msg)


def query_lottery_status(idx: int, account_config: AccountConfig, common_config: CommonConfig, card_indexes: List[str], prize_indexes: List[str], order_map: Dict[str, str]) -> Optional[List]:
    if not account_config.ark_lottery.show_status:
        return

    djcHelper = DjcHelper(account_config, common_config)
    lr = djcHelper.fetch_pskey()
    if lr is None:
        return
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list(print_warning=False)

    qa = QzoneActivity(djcHelper, lr)

    card_counts = qa.get_card_counts()
    prize_counts = qa.get_prize_counts()

    cols = [idx, account_config.name]
    # 处理各个卡片数目
    for card_position, card_index in enumerate(card_indexes):
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


@try_except()
def show_accounts_status(cfg, ctx):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line(ctx)

    # 获取数据
    rows = []
    if cfg.common.enable_multiprocessing:
        logger.warning(f"已开启多进程模式({cfg.get_pool_size()})，将开始并行拉取数据，请稍后")
        for row in get_pool().starmap(get_account_status, [(_idx + 1, account_config, cfg.common) for _idx, account_config in enumerate(cfg.account_configs)
                                                           if account_config.is_enabled()]):
            rows.append(row)
    else:
        logger.warning("拉取数据中，请稍候")
        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            rows.append(get_account_status(idx, account_config, cfg.common))

    # 打印结果
    heads = ["序号", "账号名", "启用状态", "聚豆余额", "聚豆历史总数", "心悦类型", "成就点", "勇士币", "心悦组队", "赛利亚", "心悦G分", "编年史", "年史碎片", "引导石", "赠送礼盒"]
    colSizes = [4, 12, 8, 8, 12, 10, 6, 6, 16, 12, 8, 14, 8, 6, 8]

    logger.info(tableify(heads, colSizes))
    for row in rows:
        logger.info(color("fg_bold_green") + tableify(row, colSizes, need_truncate=True))


def get_account_status(idx: int, account_config: AccountConfig, common_config: CommonConfig):
    djcHelper = DjcHelper(account_config, common_config)
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list(print_warning=False)

    status = "启用" if account_config.is_enabled() else "未启用"

    djc_info = djcHelper.query_balance("查询聚豆概览", print_res=False)["data"]
    djc_allin, djc_balance = int(djc_info['allin']), int(djc_info['balance'])

    xinyue_info = djcHelper.query_xinyue_info("查询心悦成就点概览", print_res=False)
    teaminfo = djcHelper.query_xinyue_teaminfo()
    team_award_summary = "无队伍"
    if teaminfo.id != "":
        team_award_summary = teaminfo.award_summary
        fixed_team = djcHelper.get_fixed_team()
        if fixed_team is not None:
            team_award_summary = f"[{fixed_team.id}]{team_award_summary}"

    gpoints = djcHelper.query_gpoints()

    ui = djcHelper.query_dnf_helper_chronicle_info()
    levelInfo = f"LV{ui.level}({ui.currentExp}/{ui.levelExp})"
    chronicle_points = ui.point
    if ui.totalExp == 0:
        levelInfo = ""
        chronicle_points = ""

    majieluo_stone = djcHelper.query_stone_count()
    majieluo_invite_count = djcHelper.query_invite_count()

    return [
        idx, account_config.name, status,
        djc_balance, djc_allin,
        xinyue_info.xytype_str, xinyue_info.score, xinyue_info.ysb, team_award_summary, xinyue_info.work_info(),
        gpoints,
        levelInfo, chronicle_points,
        majieluo_stone, f"{majieluo_invite_count}/30",
    ]


@try_except()
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
        djcHelper.get_bind_role_list()
        # 尝试加入固定心悦队伍
        djcHelper.try_join_fixed_xinyue_team()


def run(cfg: Config):
    _show_head_line("开始核心逻辑")

    _show_head_line("查询付费信息")
    logger.warning("开始查询付费信息，请稍候~")
    user_buy_info = get_user_buy_info(cfg.get_qq_accounts())
    show_buy_info(user_buy_info, cfg, need_show_message_box=False)

    # 上报付费使用情况
    try_report_pay_info(cfg, user_buy_info)

    # 展示活动概览
    show_activities_summary(cfg, user_buy_info)

    start_time = datetime.datetime.now()

    if cfg.common.enable_multiprocessing:
        _show_head_line(f"已开启多进程模式({cfg.get_pool_size()})，将并行运行~")

        if not cfg.common.enable_super_fast_mode:
            logger.info("当前未开启超快速模式~将并行运行各个账号")
            get_pool().starmap(do_run, [(_idx + 1, account_config, cfg.common, user_buy_info)
                                        for _idx, account_config in enumerate(cfg.account_configs) if account_config.is_enabled()])
        else:
            logger.info(color("bold_cyan") + f"已启用超快速模式，将使用{cfg.get_pool_size()}个进程并发运行各个账号的各个活动，日志将完全不可阅读~")
            activity_funcs_to_run = get_activity_funcs_to_run(cfg, user_buy_info)
            get_pool().starmap(run_act, [(account_config, cfg.common, act_name, act_func.__name__)
                                         for account_config in cfg.account_configs if account_config.is_enabled()
                                         for act_name, act_func in activity_funcs_to_run
                                         ])
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

    # 上报网盘地址，用于区分分发渠道
    if not run_from_src():
        increase_counter(ga_category="netdisk_link", name=cfg.common.netdisk_link)


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


def get_activity_funcs_to_run(cfg: Config, user_buy_info: BuyInfo) -> List[Tuple[str, Callable]]:
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

    djcHelper = DjcHelper(account_config, common_config)
    djcHelper.run(user_buy_info)

    used_time = datetime.datetime.now() - start_time
    _show_head_line(f"处理第{idx}个账户({account_config.name}) 共耗时 {used_time}")


@try_except()
def try_take_xinyue_team_award(cfg: Config):
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

        if not account_config.function_switches.get_xinyue:
            logger.warning("未启用领取心悦特权专区功能，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()
        djcHelper.xinyue_battle_ground_op("领取默契奖励点", "749229")


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
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()
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


def show_buy_info(user_buy_info: BuyInfo, cfg: Config, need_show_message_box=True):
    logger.info(color("bold_cyan") + user_buy_info.description())

    monthly_pay_info = "按月付费未激活"
    if user_buy_info.total_buy_month != 0:
        if user_buy_info.is_active():
            rt = user_buy_info.remaining_time()
            monthly_pay_info = f"按月付费剩余时长为 {rt.days}天{rt.seconds // 3600}小时"
        else:
            monthly_pay_info = "按月付费已过期"
    change_title(monthly_pay_info=monthly_pay_info, multiprocessing_pool_size=cfg.get_pool_size(), enable_super_fast_mode=cfg.common.enable_super_fast_mode)

    if need_show_message_box:
        # 仅在运行结束时的那次展示付费信息的时候尝试进行下列弹窗~
        expired = not user_buy_info.is_active()
        will_expired_soon = user_buy_info.will_expire_in_days(cfg.common.notify_pay_expired_in_days)
        if (expired and is_weekly_first_run("show_buy_info_expired")) or (will_expired_soon and is_daily_first_run("show_buy_info_will_expired_soon")):
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
            if "卡密" in record.reason:
                has_use_card_secret = True
                break

        if is_first_run("卡密付费方案提示v2") or (not use_by_myself() and user_buy_info.total_buy_month > 0 and not has_use_card_secret and is_weekly_first_run("每周提示一次已付费用户续费可使用卡密自助操作")):
            msg = "现已添加基于卡密的付费方案，可在一分钟内自助完成付费和激活对应功能（自动更新或按月付费）。\n如果想要付费或者续费可以选择这个方案~ 详情请看 【付费指引/付费指引.docx】"
            title = "新增卡密付费"
            async_message_box(msg, title, icon=MB_ICONINFORMATION, follow_flag_file=False)


def show_buy_info_sync(ctx: str, cfg: Config, force_message_box=False):
    usedDays = get_count(my_usage_counter_name, "all")
    message = (
        f"{ctx}\n"
        "\n"
        f"Hello~ 你已经累积使用小助手{usedDays}天，希望小助手为你节省了些许时间和精力(●—●)\n"
        "\n"
        f"目前已登录的账号列表为：{cfg.get_qq_accounts()}，这些QQ当前均无按月付费或已过期或者即将过期\n"
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
            win32api.MessageBox(0, message, f"付费提示(〃'▽'〃)", win32con.MB_OK)
        # os.popen("付费指引/支持一下.png")
        os.popen("付费指引/付费指引.docx")


def check_update(cfg):
    if is_run_in_github_action():
        logger.info("当前在github action环境下运行，无需检查更新")
        return

    auto_updater_path = os.path.realpath("utils/auto_updater.exe")
    if os.path.exists(auto_updater_path):
        # 如果存在自动更新DLC，则走自动更新的流程，不再手动检查是否有更新内容
        return

    logger.warning(color("bold_cyan") + (
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
    ))

    logger.info((
        "\n"
        "++++++++++++++++++++++++++++++++++++++++\n"
        "现在准备访问github仓库相关页面来检查是否有新版本\n"
        "由于国内网络问题，访问可能会比较慢，请不要立即关闭，可以选择最小化或切换到其他窗口0-0\n"
        "若有新版本会自动弹窗提示~\n"
        "++++++++++++++++++++++++++++++++++++++++\n"
    ))
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
            message = (
                f"新版本v{ui.latest_version}已更新完毕，具体更新内容展示如下，以供参考：\n"
                f"{ui.update_message}"
                "\n"
                "若未购买自动更新dlc，可无视下一句\n"
                "PS：自动更新会更新示例配置config.example.toml，但不会更新config.toml。不过由于基本所有活动的默认配置都是开启的，所以除非你想要关闭特定活动，或者调整活动配置，其实没必要修改config.toml\n"
            )
            logger.warning(color("bold_yellow") + message)
        except Exception as e:
            logger.warning("新版本首次运行获取更新内容失败，请自行查看CHANGELOG.MD", exc_info=e)


def show_ask_message_box_only_once():
    threading.Thread(target=show_ask_message_box_only_once_sync, daemon=True).start()


def show_ask_message_box_only_once_sync():
    if not is_windows():
        return

    return
    # 临时加一个请求帮忙弄下白嫖活动的逻辑
    if is_first_run("守护者卡牌"):
        message = (
            "马杰洛活动中的守护者卡牌，有小伙伴有多余的守护者卡牌吗（第5个）？\n"
            "如果有多的话，可以不可以送我一张哇0-0\n"
            "\n"
            "点 确定 打开赠送页面进行赠送，点 取消 拒绝-。-\n"
        )
        res = win32api.MessageBox(0, message, "求送卡", win32con.MB_OKCANCEL)
        if res == win32con.IDOK:
            webbrowser.open("https://dnf.qq.com/cp/a20210311welfare/index.html?askforId=11820&askforUin=1054073896")
            win32api.MessageBox(0, "打开网页后登陆后点击[确认]按钮赠送就好啦~多谢啦，嘿嘿嘿0-0", "致谢", win32con.MB_ICONINFORMATION)
        else:
            win32api.MessageBox(0, "嘤嘤嘤", "TAT", win32con.MB_ICONINFORMATION)


@try_except()
def show_tips(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("一些小提示")

    tips = {
        "工具下载": (
            "如需下载chrome、autojs、HttpCanary、notepad++、vscode、bandizip等小工具，可前往网盘自助下载：https://fzls.lanzoui.com/s/djc-tools"
        ),
        "配置工具": (
            "现已添加简易版配置工具，大家可以双击【DNF蚊子腿小助手配置工具.exe】进行体验~"
        ),
        "心悦app": (
            "现已添加心悦app的G分相关活动，获取的G分可用于每日兑换复活币*5、雷米*10、霸王契约*3天。"
            "现已添加兑换支持，只是配置流程比较晦涩，有兴趣者可打开config.toml.examle搜索 xinyue_app_operations 了解具体配置流程进行体验"
        ),
        "助手编年史": (
            "dnf助手签到任务和浏览咨询详情页请使用auto.js等自动化工具来模拟打开助手去执行对应操作，当然也可以每天手动打开助手点一点-。-\n"
            "也就是说，小助手不会帮你*完成*上述任务的条件，只会在你完成条件的前提下，替你去领取任务奖励\n"
            "此外，如果想要自动领取等级奖励，请把配置工具中助手相关的所有配置项都填上\n"
        ),
    }

    logger.info(color("bold_green") + "如果看上去卡在这了，请看看任务是否有弹窗的图标，把他们一个个按掉就能继续了（活动此时已经运行完毕）")

    for title, tip in tips.items():
        msg = f"{title}: {tip}\n "
        async_message_box(msg, f"一些小提示_{title}", show_once=True, follow_flag_file=False)


def try_auto_update(cfg):
    try:
        if not cfg.common.auto_update_on_start:
            logger.info(color("bold_cyan") + "已关闭自动更新功能，将跳过。可在配置工具的公共配置区域进行配置")
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

        has_buy_dlc, query_ok = has_buy_auto_updater_dlc_and_query_ok(cfg.get_qq_accounts())

        if not has_buy_dlc:
            if exists_auto_updater_dlc():
                msg = (
                    "经对比，本地所有账户均未购买DLC，似乎是从其他人手中获取的，或者是没有购买直接从网盘和群文件下载了=、=\n"
                    "\n"
                    f"目前已登录的账号列表为：{cfg.get_qq_accounts()}，这些QQ均没有DLC权限\n"
                    "\n"
                    "小助手本体已经免费提供了，自动更新功能只是锦上添花而已。如果觉得价格不合适，可以选择手动更新，请不要在未购买的情况下使用自动更新DLC。\n"
                    "目前只会跳过自动更新流程，日后若发现这类行为很多，可能会考虑将这样做的人加入本工具的黑名单，后续版本将不再允许其使用。\n"
                    "\n"
                    "请对照下列列表，确认是否属于以下情况\n"
                    "1. 未购买，也没有从别人那边拿过来，可能是之前查询失败时默认有权限自动下载到本地的。对策：直接将utils目录下的auto_updater.exe删除即可\n"
                    "2. 其他QQ购买了DLC，这个QQ没买。对策：请点击配置工具左上角的【添加账号】，把有权限的QQ也添加上，一起运行即可\n"
                    "3. 已购买，以前也能正常运行，但突然不行了。对策：很可能是网盘出问题了，过段时间再试试？\n"
                    "4. 已购买按月付费。对策：自动更新dlc与按月付费不是同一个东西，具体区别请阅读[付费指引/付费指引.docx]进行了解。如果无需该功能，直接将utils目录下的auto_updater.exe删除即可\n"
                )
                message_box(msg, "未购买自动更新DLC", color_name="bold_yellow")
            else:
                logger.warning(color("bold_cyan") + "当前未购买自动更新DLC，将跳过自动更新流程~")

            return

        # 已购买dlc的流程

        if os.path.isfile(auto_updater_latest_path()):
            # 如果存在auto_updater_latest.exe，且与auto_updater.exe不同，则覆盖更新
            need_copy = False
            reason = ""
            if not exists_auto_updater_dlc():
                # 不存在dlc，直接复制
                need_copy = True
                reason = "当前不存在dlc，但存在最新版dlc，将复制使用该dlc"
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
                logger.info(color("bold_green") + f"{reason}，将复制{auto_updater_latest_path()}到{auto_updater_path()}")
                shutil.copy2(auto_updater_latest_path(), auto_updater_path())
        else:
            if not exists_auto_updater_dlc():
                if not query_ok:
                    logger.debug(f"当前应该是查询dlc失败后全部放行的情况，这种情况下若本地没有dlc，则不尝试自动下载，避免后续查询功能恢复正常后提示没有权限，需要手动删除")
                    return

                # 未发现dlc和最新版dlc，尝试从网盘下载
                logger.info(color("bold_yellow") + f"未发现自动更新DLC({auto_updater_path()})，将尝试从网盘下载")
                uploader = Uploader()
                uploader.download_file_in_folder(uploader.folder_djc_helper, os.path.basename(auto_updater_path()), os.path.dirname(auto_updater_path()))

        # 保底，如果前面的流程都失败了，提示用户自行下载
        if not exists_auto_updater_dlc():
            logger.warning(color("bold_cyan") + "未发现自动更新DLC（预期应放在utils/auto_updater.exe路径，但是木有发现嗷），将跳过自动更新流程~")
            logger.warning(color("bold_green") + "如果已经购买过DLC，请先打开目录中的[付费指引/付费指引.docx]，找到自动更新DLC的使用说明，按照教程操作一番即可")
            return

        logger.info("开始尝试调用自动更新工具进行自动更新~ 当前处于测试模式，很有可能有很多意料之外的情况，如果真的出现很多问题，可以自行关闭该功能的配置")

        logger.info(f"当前进程pid={pid}, 版本={now_version}, 工作目录={dirpath}，exe名称={filename}")

        logger.info(color("bold_yellow") + "尝试启动更新器，等待其执行完毕。若版本有更新，则会干掉这个进程并下载更新文件，之后重新启动进程...(请稍作等待）")
        for idx in range_from_one(3):
            dlc_path = auto_updater_path()
            p = subprocess.Popen([
                dlc_path,
                "--pid", str(pid),
                "--version", str(now_version),
                "--cwd", dirpath,
                "--exe_name", filename,
            ], cwd="utils", shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.wait()

            if p.returncode == 0:
                # dlc正常退出，无需额外处理和重试
                break

            # 异常退出时，看看网盘是否有更新的版本
            last_modify_time = parse_timestamp(os.stat(dlc_path).st_mtime)
            logger.error(color("bold_yellow") + f"第{idx}次尝试DLC出错了，错误码为{p.returncode}，DLC最后一次修改时间为{last_modify_time}")

            uploader = Uploader()
            netdisk_latest_dlc_info = uploader.find_latest_dlc_version()
            latest_version_time = parse_time(netdisk_latest_dlc_info.time)

            if latest_version_time <= last_modify_time:
                # 暂无最新版本，无需重试
                logger.warning(f"网盘中最新版本dlc上传于{latest_version_time}左右，在当前版本之前，请耐心等待修复该问题的新版本发布~")
                break

            # 更新新版本，然后重试
            logger.info(color("bold_green") + f"网盘中最新版本dlc上传于{latest_version_time}左右，在当前版本之后，有可能已经修复dlc的该问题，将尝试更新dlc为最新版本")
            uploader.download_file(netdisk_latest_dlc_info, os.path.dirname(dlc_path))

        logger.info(color("bold_yellow") + "当前版本为最新版本，不需要更新~")
    except Exception as e:
        logger.error("自动更新出错了，报错信息如下", exc_info=e)


def has_buy_auto_updater_dlc(qq_accounts: List[str], max_retry_count=3, retry_wait_time=5, show_log=False) -> bool:
    has_buy, _ = has_buy_auto_updater_dlc_and_query_ok(qq_accounts, max_retry_count, retry_wait_time, show_log)
    return has_buy


def has_buy_auto_updater_dlc_and_query_ok(qq_accounts: List[str], max_retry_count=3, retry_wait_time=5, show_log=False) -> Tuple[bool, bool]:
    """
    查询是否购买过dlc，返回 [是否有资格，查询是否成功]
    """
    logger.debug("尝试由服务器代理查询购买DLC信息，请稍候片刻~")
    user_buy_info, query_ok = get_user_buy_info_from_server(qq_accounts)
    if query_ok:
        return infer_has_buy_auto_updater_dlc_from_server_buy_info(user_buy_info), True

    logger.debug("服务器查询DLC信息失败，尝试直接从网盘查询~")
    for idx in range(max_retry_count):
        try:
            uploader = Uploader()
            has_no_users = True
            for remote_filename in [uploader.buy_auto_updater_users_filename, uploader.cs_buy_auto_updater_users_filename]:
                try:
                    user_list_filepath = uploader.download_file_in_folder(uploader.folder_online_files, remote_filename, downloads_dir, show_log=show_log, try_compressed_version_first=True)
                except FileNotFoundError:
                    # 如果网盘没有这个文件，就跳过
                    continue

                buy_users = []
                with open(user_list_filepath, 'r', encoding='utf-8') as data_file:
                    buy_users = json.load(data_file)

                if len(buy_users) != 0:
                    has_no_users = False

                for qq in qq_accounts:
                    if qq in buy_users:
                        return True, True

                logger.debug((
                    "DLC购买调试日志：\n"
                    f"remote_filename={remote_filename}\n"
                    f"账号列表={qq_accounts}\n"
                    f"用户列表={buy_users}\n"
                ))

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


def infer_has_buy_auto_updater_dlc_from_server_buy_info(user_buy_info: BuyInfo) -> bool:
    if len(user_buy_info.buy_records) == 0:
        return False

    return user_buy_info.buy_records[0].reason.startswith("自动更新DLC赠送")


def get_user_buy_info(qq_accounts: List[str], max_retry_count=3, retry_wait_time=5, show_log=False, show_dlc_info=True) -> BuyInfo:
    logger.info(f"如果卡在这里不能动，请先看看网盘里是否有新版本~ 如果新版本仍无法解决，可加群反馈~ 链接：{config().common.netdisk_link}")

    logger.debug("尝试由服务器代理查询付费信息，请稍候片刻~")
    user_buy_info, query_ok = get_user_buy_info_from_server(qq_accounts)
    if query_ok:
        return user_buy_info

    logger.debug("服务器查询失败，尝试直接从网盘查询~")
    user_buy_info, _ = get_user_buy_info_from_netdisk(qq_accounts, max_retry_count, retry_wait_time, show_log)
    # 购买过dlc的用户可以获得两个月免费使用付费功能的时长
    if has_buy_auto_updater_dlc(qq_accounts, max_retry_count, retry_wait_time, show_log):
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
        user_buy_info.buy_records.insert(0, BuyRecord().auto_update_config({
            "buy_month": 2,
            "buy_at": format_time(free_start_time),
            "reason": "自动更新DLC赠送(自2.8至今最多累积未付费时长两个月***注意不是从购买日开始计算***)"
        }))

        if show_dlc_info:
            logger.info(color("bold_yellow") + "注意：自动更新和按月付费是两个完全不同的东西，具体区别请看 付费指引/付费指引.docx")
            logger.info(color("bold_cyan") + f"当前运行的qq中已有某个qq购买过自动更新dlc\n" +
                        color("bold_green") + f"\t自{free_start_time}开始将累积可免费使用付费功能两个月，累计未付费时长为{not_paied_times}，将补偿{fixup_times}\n"
                                              f"\t实际过期时间为{user_buy_info.expire_at}(原结束时间为{old_expire_at})")
            logger.info(color("bold_black") + "若对自动更新送的两月有疑义，请看付费指引的常见问题章节\n"
                                              "\t请注意这里的两月是指从2.8开始累积未付费时长最多允许为两个月，是给2.8以前购买DLC的朋友的小福利\n"
                                              "\t如果4.11以后才购买就享受不到这个的，因为购买时自2.8开始的累积未付费时长已经超过两个月")

    return user_buy_info


def get_user_buy_info_from_netdisk(qq_accounts: List[str], max_retry_count=3, retry_wait_time=5, show_log=False) -> Tuple[BuyInfo, bool]:
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
                    buy_info_filepath = uploader.download_file_in_folder(uploader.folder_online_files, remote_filename, downloads_dir, show_log=show_log, try_compressed_version_first=True)
                except FileNotFoundError:
                    # 如果网盘没有这个文件，就跳过
                    continue

                buy_users = {}  # type: Dict[str, BuyInfo]

                def update_if_longer(qq: str, info: BuyInfo):
                    if qq not in buy_users:
                        buy_users[qq] = info
                    else:
                        # 如果已经在其他地方已经出现过这个QQ，则仅当新的付费信息过期时间较晚时才覆盖
                        old_info = buy_users[qq]
                        if time_less(old_info.expire_at, info.expire_at):
                            buy_users[qq] = info

                with open(buy_info_filepath, 'r', encoding='utf-8') as data_file:
                    raw_infos = json.load(data_file)
                    for qq, raw_info in raw_infos.items():
                        info = BuyInfo().auto_update_config(raw_info)
                        update_if_longer(qq, info)
                        for game_qq in info.game_qqs:
                            update_if_longer(game_qq, info)

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


def get_user_buy_info_from_server(qq_accounts: List[str]) -> Tuple[BuyInfo, bool]:
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

            raw_res_text = with_cache(cache_name_user_buy_info, json.dumps(qq_accounts), cache_max_seconds=600, cache_miss_func=fetch_query_info_from_server,
                                      cache_validate_func=None)
            if raw_res_text != "":
                ok = True
                buyInfo.auto_update_config(json.loads(raw_res_text))

    except Exception as e:
        logger.debug("出错了", f"请求出现异常，报错如下:\n{e}")

    return buyInfo, ok


def show_multiprocessing_info(cfg: Config):
    msg = ""
    if cfg.common.enable_multiprocessing:
        msg += f"当前已开启多进程模式，进程池大小为 {cfg.get_pool_size()}"
        if cfg.common.enable_super_fast_mode:
            msg += ", 超快速模式已开启，将并行运行各个账号的各个活动~"
        else:
            msg += ", 超快速模式未开启，将并行运行各个账号。如需同时运行各个活动，可开启该模式~"
    else:
        msg += f"未开启多进程模式，如需开启，可前往配置工具开启"

    logger.info(color("bold_yellow") + msg)

    # 上报多进程相关功能的使用情况
    increase_counter(ga_category="enable_multiprocessing", name=cfg.common.enable_multiprocessing)
    increase_counter(ga_category="enable_super_fast_mode", name=cfg.common.enable_super_fast_mode)
    if cfg.common.enable_multiprocessing:
        increase_counter(ga_category="cpu_count", name=cpu_count())
        increase_counter(ga_category="raw_pool_size", name=cfg.common.multiprocessing_pool_size)
        increase_counter(ga_category="final_pool_size", name=cfg.get_pool_size())


def show_notices():
    def _cb():
        # 初始化
        nm = NoticeManager()
        # 展示公告
        nm.show_notices()

    async_call(_cb)


disable_flag_file = ".no_sync_configs"


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
    with open(os.path.join(appdata_dir, '__backup_info.json'), 'w', encoding='utf-8') as f:
        json.dump({
            "app_version": now_version,
            "app_time": ver_time,
            "backup_time": format_now(),
        }, f, indent=4, ensure_ascii=False)


@try_except()
def try_load_old_version_configs_from_user_data_dir():
    """
    若是首次运行，尝试从%APPDATA%/djc_helper同步配置到当前目录
    """
    cwd = os.getcwd()
    appdata_dir = get_appdata_save_dir()

    logger.info(color("bold_green") + f"已开启首次运行时自动同步配置本机配置功能，将尝试从 {appdata_dir} 同步配置到 {cwd}")
    logger.info(color("bold_yellow") + f"如果不需要同步配置，可在当前目录创建 {disable_flag_file} 文件")

    if os.path.exists(disable_flag_file):
        logger.info(f"当前目录存在 {disable_flag_file}，故而不尝试同步配置")
        return

    if run_from_src():
        logger.info(f"当前使用源码运行，无需同步配置")
        return

    if not is_first_run("sync_config"):
        logger.info(f"当前不是首次运行，无需同步配置")
        return

    if not os.path.isdir(appdata_dir):
        logger.info(f"当前没有备份的旧版本配置，无需同步配置")
        return

    logger.info("符合同步条件，将开始同步流程~")
    sync_configs(appdata_dir, cwd)


def get_appdata_save_dir() -> str:
    return os.path.join(get_appdata_dir(), 'djc_helper')


def check_proxy(cfg: Config):
    if cfg.common.bypass_proxy:
        logger.info(f"当前配置为无视系统代理，将直接访问网络。")
        bypass_proxy()
    else:
        logger.info(f"当前未开启无视系统代理配置，如果使用了vpn，将优先通过vpn进行访问。如果在国内，并且经常用到vpn，建议打开该配置")


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
    logger.warning(color("fg_bold_cyan") + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开付费指引/支持一下.png，扫码打赏哦~")

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


if __name__ == '__main__':
    freeze_support()

    # demo_main()
    demo_pay_info()

    # demo_show_notices()

    # demo_show_activities_summary()
