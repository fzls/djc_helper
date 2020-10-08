import os

from ark_lottery import ArkLottery
from config import load_config, config, XinYueOperationConfig
from djc_helper import DjcHelper
from ga import track_event, track_page
from update import check_update_on_start
from util import *
from version import *


def has_any_account_in_normal_run(cfg):
    for _idx, account_config in enumerate(cfg.account_configs):
        if not account_config.enable_and_normal_run():
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        return True
    return False


def _show_head_line(msg):
    show_head_line(msg, color("fg_bold_yellow"))


def check_all_skey_and_pskey(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("启动时检查各账号skey/pskey/openid是否过期")

    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.enable_and_normal_run():
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        logger.warning(color("fg_bold_yellow") + "------------检查第{}个账户({})------------".format(idx, account_config.name))
        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list(print_warning=False)
        djcHelper.fetch_pskey()
        djcHelper.fetch_guanjia_openid(print_warning=False)


def auto_send_cards(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("运行完毕自动赠送卡片")

    target_qq = cfg.common.auto_send_card_target_qq
    if target_qq == "":
        logger.warning("未定义自动赠送卡片的对象，将跳过本阶段")
        return

    track_page("/misc/auto_send_cards")

    # 统计各账号卡片数目
    logger.info("拉取各账号的卡片数据中，请耐心等待...")
    qq_to_card_name_to_counts = {}
    qq_to_djcHelper = {}
    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.enable_and_normal_run():
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list(print_warning=False)

        lr = djcHelper.fetch_pskey()
        if lr is None:
            continue

        qq = uin2qq(lr.uin)
        al = ArkLottery(djcHelper, lr)

        qq_to_card_name_to_counts[qq] = al.get_card_counts()
        qq_to_djcHelper[qq] = djcHelper

        logger.info("{}/{} 账号 {:} 的数据拉取完毕".format(idx, len(cfg.account_configs), padLeftRight(account_config.name, 12)))

    # 赠送卡片
    if target_qq in qq_to_djcHelper:
        left_times = qq_to_djcHelper[target_qq].ark_lottery_query_left_times(target_qq)
        logger.warning(color("fg_bold_green") + "账号 {}({}) 今日仍可被赠送 {} 次卡片".format(qq_to_djcHelper[target_qq].cfg.name, target_qq, left_times))
        # 最多赠送目标账号今日仍可接收的卡片数
        for i in range(left_times):
            send_most_wantted_card(target_qq, qq_to_card_name_to_counts, qq_to_djcHelper)

        # 赠送卡片完毕后尝试抽奖
        djcHelper = qq_to_djcHelper[target_qq]
        lr = djcHelper.fetch_pskey()
        if lr is not None:
            al = ArkLottery(djcHelper, lr)
            al.try_lottery_using_cards(print_warning=False)


def send_most_wantted_card(target_qq, qq_to_card_name_to_counts, qq_to_djcHelper):
    card_name_to_id = {
        "多人配合新挑战": "116193", "丰富机制闯难关": "116192", "新剧情视听盛宴": "116191", "单人成团战不停": "116190",
        "回归奖励大升级": "116189", "秒升Lv96刷深渊": "116188", "灿烂自选回归领": "116187", "告别酱油变大佬": "116186",
        "单人爽刷新玩法": "116185", "独立成团打副本": "116184", "海量福利金秋享": "116183", "超强奖励等你拿": "116182",
    }
    card_name_to_index = {
        "多人配合新挑战": "1-1", "丰富机制闯难关": "1-2", "新剧情视听盛宴": "1-3", "单人成团战不停": "1-4",
        "回归奖励大升级": "2-1", "秒升Lv96刷深渊": "2-2", "灿烂自选回归领": "2-3", "告别酱油变大佬": "2-4",
        "单人爽刷新玩法": "3-1", "独立成团打副本": "3-2", "海量福利金秋享": "3-3", "超强奖励等你拿": "3-4",
    }
    # 当前卡牌的卡牌按照卡牌数升序排列
    target_card_infos = []
    for card_name, card_count in qq_to_card_name_to_counts[target_qq].items():
        target_card_infos.append((card_name, card_count))
    target_card_infos.sort(key=lambda card: card[1])

    # 升序遍历
    for card_name, card_count in target_card_infos:
        # 找到任意一个拥有卡片的其他账号，让他送给目标账户。默认越靠前的号越重要，因此从后面的号开始查
        for qq, card_name_to_count in reverse_map(qq_to_card_name_to_counts):
            if qq == target_qq:
                continue
            # 如果某账户有这个卡，则赠送该当前玩家，并结束本回合赠卡
            if card_name_to_count[card_name] > 0:
                qq_to_djcHelper[qq].send_card(card_name_to_id[card_name], target_qq)
                card_name_to_count[card_name] -= 1
                qq_to_card_name_to_counts[target_qq][card_name] += 1

                logger.warning(color("fg_bold_cyan") + "账号 {} 赠送一张 {}({}) 给 {}".format(
                    qq_to_djcHelper[qq].cfg.name,
                    card_name_to_index[card_name], card_name,
                    qq_to_djcHelper[target_qq].cfg.name
                ))
                return


def reverse_map(map):
    kvs = list(map.items())
    kvs.reverse()
    return kvs


def show_lottery_status(ctx, cfg, need_show_tips=False):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line(ctx)

    order_map = {
        "1-1": "多人配合新挑战", "1-2": "丰富机制闯难关", "1-3": "新剧情视听盛宴", "1-4": "单人成团战不停",
        "2-1": "回归奖励大升级", "2-2": "秒升Lv96刷深渊", "2-3": "灿烂自选回归领", "2-4": "告别酱油变大佬",
        "3-1": "单人爽刷新玩法", "3-2": "独立成团打副本", "3-3": "海量福利金秋享", "3-4": "超强奖励等你拿",
        "全新团本": "勇士归来礼包",
        "超低门槛": "超低门槛",
        "人人可玩": "人人可玩",
        "幸运礼包": "幸运礼包",
    }

    heads = ["序号", "账号名"]
    colSizes = [4, 12]

    card_indexes = ["1-1", "1-2", "1-3", "1-4", "2-1", "2-2", "2-3", "2-4", "3-1", "3-2", "3-3", "3-4"]
    card_width = 3
    heads.extend(card_indexes)
    colSizes.extend([card_width for i in card_indexes])

    prize_indexes = ["全新团本", "超低门槛", "人人可玩", "幸运礼包"]
    heads.extend(prize_indexes)
    colSizes.extend([printed_width(name) for name in prize_indexes])

    accounts_that_should_enable_cost_card_to_lottery = []

    logger.info(tableify(heads, colSizes))
    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.enable_and_normal_run():
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        if not account_config.ark_lottery.show_status:
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list(print_warning=False)

        lr = djcHelper.fetch_pskey()
        if lr is None:
            continue

        al = ArkLottery(djcHelper, lr)

        card_counts = al.get_card_counts()
        prize_counts = al.get_prize_counts()

        cols = [idx, account_config.name]
        has_any_card = False
        has_any_left_gift = False
        # 处理各个卡片数目
        for card_index in card_indexes:
            card_count = card_counts[order_map[card_index]]

            show_count = card_count
            # 特殊处理色彩
            if card_count == 0:
                if idx == 1:
                    # 突出显示大号没有的卡片
                    show_count = color("fg_bold_cyan") + padLeftRight(card_count, 3) + color("INFO")
                else:
                    # 小号没有的卡片直接不显示，避免信息干扰
                    show_count = ""
            else:
                if idx == 1:
                    if card_count == 1:
                        # 大号只有一张的卡片也特殊处理
                        show_count = color("fg_bold_blue") + padLeftRight(card_count, 3) + color("INFO")
                    else:
                        # 大号其余卡片亮绿色
                        show_count = color("fg_bold_green") + padLeftRight(card_count, 3) + color("INFO")
                else:
                    # 小号拥有的卡片淡化处理，方便辨识
                    show_color = account_config.ark_lottery.show_color or "fg_bold_black"
                    show_count = color(show_color) + padLeftRight(card_count, 3) + color("INFO")

            cols.append(show_count)

            if card_count > 0:
                has_any_card = True

        # 处理各个奖励剩余领取次数
        for prize_index in prize_indexes:
            prize_count = prize_counts[order_map[prize_index]]
            cols.append(prize_count)

            if prize_count > 0:
                has_any_left_gift = True

        logger.info(tableify(cols, colSizes))

        if has_any_card and not has_any_left_gift:
            accounts_that_should_enable_cost_card_to_lottery.append(account_config.name)

    if need_show_tips and len(accounts_that_should_enable_cost_card_to_lottery) > 0:
        msg = "账户({})仍有剩余卡片，但已无任何可领取礼包，建议开启消耗卡片来抽奖的功能".format(', '.join(accounts_that_should_enable_cost_card_to_lottery))
        logger.warning(color("fg_bold_yellow") + msg)


def show_accounts_status(cfg, ctx):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line(ctx)

    heads = ["序号", "账号名", "启用状态", "聚豆余额", "聚豆历史总数", "成就点", "心悦组队"]
    colSizes = [4, 12, 8, 8, 12, 6, 8]

    logger.info(tableify(heads, colSizes))
    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.enable_and_normal_run():
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()

        status = "启用" if account_config.enable else "未启用"

        djc_info = djcHelper.query_balance("查询聚豆概览", print_res=False)["data"]
        djc_allin, djc_balance = int(djc_info['allin']), int(djc_info['balance'])

        xinyue_info = djcHelper.query_xinyue_info("查询心悦成就点概览", print_res=False)
        teaminfo = djcHelper.query_xinyue_teaminfo(print_res=False)
        team_score = "无队伍"
        if teaminfo.id != "":
            team_score = "{}/20".format(teaminfo.score)

        cols = [idx, account_config.name, status, djc_balance, djc_allin, xinyue_info.score, team_score]

        logger.info(color("fg_bold_green") + tableify(cols, colSizes))


def try_join_xinyue_team(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("尝试加入心悦固定队")

    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.enable_and_normal_run():
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        logger.info("")
        logger.warning(color("fg_bold_yellow") + "------------尝试第{}个账户({})------------".format(idx, account_config.name))

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        # 尝试加入固定心悦队伍
        djcHelper.try_join_fixed_xinyue_team()

        if cfg.common._debug_run_first_only:
            logger.warning("调试开关打开，不再处理后续账户")
            break


def run(cfg):
    _show_head_line("开始核心逻辑")

    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.enable:
            logger.info("第{}个账号({})未启用，将跳过".format(idx, account_config.name))
            continue

        _show_head_line("开始处理第{}个账户({})".format(idx, account_config.name))

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.run()

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
        if not account_config.enable_and_normal_run():
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        logger.info("")
        logger.warning(color("fg_bold_green") + "------------开始尝试为第{}个账户({})领取心悦组队奖励------------".format(idx, account_config.name))

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


def show_support_pic(cfg):
    normal_run = False
    for account_config in cfg.account_configs:
        if account_config.run_mode == "normal":
            normal_run = True
            break
    if normal_run:
        logger.info("")
        logger.warning(color("fg_bold_cyan") + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以打开支持一下.png，扫码打赏哦~")
        if cfg.common.show_support_pic:
            os.popen("支持一下.png")
            track_page("show_support")


def check_update(cfg):
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


def main():
    track_event("main", "start")
    track_event("version", "ver{} {}".format(now_version, ver_time))

    # 最大化窗口
    logger.info("尝试最大化窗口，打包exe可能会运行的比较慢")
    maximize_console()

    logger.warning("开始运行DNF蚊子腿小助手，ver={} {}，powered by {}".format(now_version, ver_time, author))
    logger.warning(color("fg_bold_cyan") + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开支持一下.png，扫码打赏哦~")

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        logger.error("未找到有效的账号配置，请检查是否正确配置。ps：多账号版本配置与旧版本不匹配，请重新配置")
        exit(-1)

    track_event("account_count", str(len(cfg.account_configs)))

    check_all_skey_and_pskey(cfg)

    show_accounts_status(cfg, "启动时展示账号概览")

    # 预先尝试创建和加入固定队伍，从而每周第一次操作的心悦任务也能加到队伍积分中
    try_join_xinyue_team(cfg)

    # 正式进行流程
    run(cfg)

    # 尝试领取心悦组队奖励
    try_take_xinyue_team_award(cfg)

    show_lottery_status("运行完毕展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg, need_show_tips=True)
    auto_send_cards(cfg)
    show_lottery_status("卡片赠送完毕后展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg)

    show_accounts_status(cfg, "运行完毕展示账号概览")

    # 每次正式模式运行成功时弹出打赏图片
    show_support_pic(cfg)

    # 临时代码
    temp_code(cfg)

    track_event("main", "finish")

    # 全部账号操作完成后，检查更新
    check_update(cfg)


def temp_code(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("一些临时tips")

    # re: 闪光杯活动结束后删除
    logger.warning(color("fg_bold_yellow") + "记得每日手动登陆下心悦app，不然闪光杯抽奖会少一次。研究了下，心悦app使用jce协议并加了各种校验和加密，且客户端经过加壳，比较难搞，最终决定手动操作了<_<，有兴趣了解可以参考 https://juejin.im/post/6844903583524225031")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.exception("运行过程中出现未捕获的异常，请加群553925117反馈或自行解决", exc_info=e)
    finally:
        # 暂停一下，方便看结果
        os.system("PAUSE")
