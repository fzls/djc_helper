import argparse

from log import log_directory
from main_def import *
from show_usage import *
from usage_count import *


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no_max_console", default=False, action="store_true", help="是否不将窗口调整为最大化")
    args = parser.parse_args()

    return args


def main():
    args = parse_args()

    change_title()
    show_ask_message_box_only_once()

    print_update_message_on_first_run_new_version()

    if is_daily_first_run():
        logger.info("今日首次运行，尝试上报使用统计~")
        # 在每日首次使用的时候，上报一下（因为api限额只有3w次，尽可能减少调用）
        # 整体使用次数
        # increase_counter(this_version_global_usage_counter_name)
        # increase_counter(global_usage_counter_name)

        # 当前用户使用次数
        # increase_counter(this_version_my_usage_counter_name)
        increase_counter(my_usage_counter_name)
    else:
        logger.info("今日已运行过，不再尝试上报使用统计")

    # 最大化窗口
    logger.info("尝试最大化窗口，打包exe可能会运行的比较慢")

    if not args.no_max_console:
        maximize_console()

    logger.warning(f"开始运行DNF蚊子腿小助手，ver={now_version} {ver_time}，powered by {author}")
    logger.warning(color("fg_bold_cyan") + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开支持一下.png，扫码打赏哦~")

    change_title()

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        logger.error("未找到有效的账号配置，请检查是否正确配置。ps：多账号版本配置与旧版本不匹配，请重新配置")
        exit(-1)

    clean_dir_to_size(log_directory, cfg.common.max_logs_size * MiB, cfg.common.keep_logs_size * MiB)
    clean_dir_to_size(f"utils/{log_directory}", cfg.common.max_logs_size * MiB, cfg.common.keep_logs_size * MiB)

    check_all_skey_and_pskey(cfg)

    check_djc_role_binding()

    # 挪到所有账号都登陆后再尝试自动更新，从而能够判定是否已购买DLC
    try_auto_update(cfg)

    show_accounts_status(cfg, "启动时展示账号概览")

    # 预先尝试创建和加入固定队伍，从而每周第一次操作的心悦任务也能加到队伍积分中
    try_join_xinyue_team(cfg)

    # 正式进行流程
    run(cfg)

    # 尝试领取心悦组队奖励
    try_take_xinyue_team_award(cfg)

    # # 尝试派赛利亚出去打工
    # try_xinyue_sailiyam_start_work(cfg)

    auto_send_cards(cfg)
    show_lottery_status("卡片赠送完毕后展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg, need_show_tips=True)

    show_accounts_status(cfg, "运行完毕展示账号概览")

    # 临时代码
    temp_code(cfg)

    # 显示小助手的使用概览
    if cfg.common._show_usage:
        show_usage()

    # 全部账号操作完成后，检查更新
    check_update(cfg)


if __name__ == '__main__':
    try:
        run_start_time = datetime.datetime.now()
        main()
        logger.warning(color("fg_bold_yellow") + f"运行完成，共用时{datetime.datetime.now() - run_start_time}")
    except Exception as e:
        msg = f"ver {now_version} 运行过程中出现未捕获的异常，请加群966403777反馈或自行解决。" + check_some_exception(e)
        logger.exception(color("fg_bold_red") + msg, exc_info=e)
        logger.warning(color("fg_bold_cyan") + "如果稳定报错，不妨打开网盘，看看是否有新版本修复了这个问题~")
        logger.warning(color("fg_bold_cyan") + "链接：https://fzls.lanzous.com/s/djc-helper")
    finally:
        # 暂停一下，方便看结果
        os.system("PAUSE")
