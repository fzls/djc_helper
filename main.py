import os

from ark_lottery import ArkLottery
from config import load_config, config, XinYueOperationConfig
from djc_helper import DjcHelper
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
    if has_any_account_in_normal_run(cfg):
        _show_head_line("启动时检查各账号skey和pskey是否过期")

    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.enable_and_normal_run():
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        logger.warning("------------检查第{}个账户({})------------".format(idx, account_config.name))
        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.fetch_pskey()


def show_lottery_status(cfg):
    if has_any_account_in_normal_run(cfg):
        _show_head_line("运行完毕展示各账号抽卡卡片以及各礼包剩余可领取信息")

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

    logger.info(tableify(heads, colSizes))
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

        al = ArkLottery(djcHelper, lr)
        al.fetch_lottery_data()

        card_counts = al.get_card_counts()
        prize_counts = al.get_prize_counts()

        cols = [idx, account_config.name]
        for card_index in card_indexes:
            card_count = card_counts[order_map[card_index]]
            # 特殊处理色彩
            if card_count == 0:
                if idx == 1:
                    card_count = color("fg_bold_cyan") + padLeftRight(card_count, 3) + color("INFO")
                else:
                    card_count = ""
            else:
                if idx == 1:
                    pass
                else:
                    card_count = color("bold_black") + padLeftRight(card_count, 3) + color("INFO")
            cols.append(card_count)
        cols.extend([prize_counts[order_map[prize_index]] for prize_index in prize_indexes])

        logger.info(tableify(cols, colSizes))

    logger.info("")
    logger.warning(color("fg_bold_green") + "抽卡信息如上，可参照上述信息来确定小号赠送啥卡片给大号")
    logger.info("")


def show_accounts_status(cfg, ctx):
    if has_any_account_in_normal_run(cfg):
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
    if has_any_account_in_normal_run(cfg):
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
    if has_any_account_in_normal_run(cfg):
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
    if has_any_account_in_normal_run(cfg):
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
        logger.warning("如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以打开支持一下.png，扫码打赏哦~")
        if cfg.common.show_support_pic:
            os.popen("支持一下.png")


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
    # 最大化窗口
    logger.info("尝试最大化窗口，打包exe可能会运行的比较慢")
    maximize_console()

    logger.warning("开始运行DNF蚊子腿小助手，ver={} {}，powered by {}".format(now_version, ver_time, author))
    logger.warning(color("fg_bold_green") + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开支持一下.png，扫码打赏哦~")

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        logger.error("未找到有效的账号配置，请检查是否正确配置。ps：多账号版本配置与旧版本不匹配，请重新配置")
        exit(-1)

    check_all_skey_and_pskey(cfg)

    show_accounts_status(cfg, "启动时展示账号概览")

    # 预先尝试创建和加入固定队伍，从而每周第一次操作的心悦任务也能加到队伍积分中
    try_join_xinyue_team(cfg)

    # 正式进行流程
    run(cfg)

    # 尝试领取心悦组队奖励
    try_take_xinyue_team_award(cfg)

    show_lottery_status(cfg)

    show_accounts_status(cfg, "运行完毕展示账号概览")

    # 每次正式模式运行成功时弹出打赏图片
    show_support_pic(cfg)

    # 全部账号操作完成后，检查更新
    check_update(cfg)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.exception("运行过程中出现未捕获的异常，请加群553925117反馈或自行解决", exc_info=e)
    finally:
        # 暂停一下，方便看结果
        os.system("PAUSE")
