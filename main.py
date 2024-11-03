import os
import sys

# 修改工作目录为程序所在目录，这样通过注册表实现开机自动启动时也能获取到正确的工作目录
# PS: 放到这个地方，是确保在所有其他初始化代码之前先修改掉工作目录
dirpath = os.path.dirname(os.path.realpath(sys.argv[0]))
old_path = os.getcwd()
os.chdir(dirpath)

import argparse
import datetime
import time
from multiprocessing import freeze_support

import psutil

import ga
from check_first_run import check_first_run_async
from config import config, load_config
from db_def import try_migrate_db
from djc_helper import is_ark_lottery_enabled
from first_run import is_weekly_first_run
from log import color, log_directory, logger
from main_def import (
    auto_send_cards,
    check_all_skey_and_pskey,
    check_djc_role_binding,
    check_proxy,
    check_update,
    get_user_buy_info,
    print_update_message_on_first_run_new_version,
    run,
    sas,
    show_ask_message_box,
    show_buy_info,
    show_extra_infos,
    show_lottery_status,
    show_multiprocessing_info,
    show_notices,
    show_pay_info,
    show_recommend_reward_tips,
    try_auto_update,
    try_auto_update_ignore_permission_on_special_case,
    try_join_xinyue_team,
    try_load_old_version_configs_from_user_data_dir,
    try_report_usage_info,
    try_save_configs_to_user_data_dir,
    try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once,
    try_take_xinyue_team_award,
)
from pool import close_pool, init_pool
from qq_login import QQLogin
from show_usage import show_usage
from update import notify_manual_check_update_on_release_too_long
from usage_count import increase_counter
from util import (
    MiB,
    async_call,
    async_message_box,
    change_console_window_mode_async,
    change_title,
    clean_dir_to_size,
    disable_pause_after_run,
    disable_quick_edit_mode,
    is_run_in_github_action,
    kill_other_instance_on_start,
    pause,
    remove_old_version_portable_chrome_files,
    show_head_line,
    show_unexpected_exception_message,
)
from version import author, now_version, ver_time


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no_max_console", default=False, action="store_true", help="是否不将窗口调整为最大化")
    parser.add_argument(
        "--wait_for_pid_exit",
        default=0,
        type=int,
        help="启动后是否等待对应pid的进程结束后再启动，主要用于使用配置工具启动小助手的情况，只有配置工具退出运行，自动更新才能正常进行",
    )
    parser.add_argument("--max_wait_time", default=5, type=int, help="最大等待时间")
    args = parser.parse_args()

    return args


def prepare_env():
    args = parse_args()

    # 最大化窗口
    if not args.no_max_console:
        logger.info("尝试调整窗口显示模式，打包exe可能会运行的比较慢")
        change_console_window_mode_async()

    if args.wait_for_pid_exit != 0:
        # 通过配置工具打开
        increase_counter(ga_category="open_by", name="config_tool", ga_misc_params={"dr": "config_tool"})
        logger.info(
            f"等待pid为{args.wait_for_pid_exit}的配置工具退出运行，从而确保可能有的自动更新能够正常进行，最大将等待{args.max_wait_time}秒"
        )

        wait_time = 0.0
        retry_time = 0.1
        while wait_time <= args.max_wait_time:
            if not psutil.pid_exists(args.wait_for_pid_exit):
                logger.info("配置工具已成功退出，将开始运行小助手~")
                break

            time.sleep(retry_time)
            wait_time += retry_time
    else:
        # 直接打开
        increase_counter(ga_category="open_by", name="directly", ga_misc_params={"dr": "directly"})


def main():
    try_migrate_db()

    increase_counter(name="run/begin", ga_type=ga.GA_REPORT_TYPE_PAGE_VIEW)

    prepare_env()

    # 启动时检查是否需要同步本机数据目录备份的旧版本配置
    try_load_old_version_configs_from_user_data_dir()

    change_title(show_next_regular_activity_info=True)

    print_update_message_on_first_run_new_version()

    logger.warning(f"开始运行DNF蚊子腿小助手，ver={now_version} {ver_time}，powered by {author}")
    logger.warning(
        color("fg_bold_cyan")
        + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开付费指引/支持一下.png，扫码打赏哦~"
    )

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        raise Exception("未找到有效的账号配置，请检查是否正确配置。ps：多账号版本配置与旧版本不匹配，请重新配置")

    try_auto_update_ignore_permission_on_special_case(cfg)

    notify_manual_check_update_on_release_too_long(cfg.common)

    check_proxy(cfg)

    try_report_usage_info(cfg)

    if cfg.common.disable_cmd_quick_edit:
        disable_quick_edit_mode()

    show_notices()

    if cfg.common.allow_only_one_instance:
        logger.info("当前仅允许单个实例运行，将尝试干掉其他实例~")
        async_call(kill_other_instance_on_start)
    else:
        logger.info("当前允许多个实例同时运行~")

    pool_size = cfg.get_pool_size()
    init_pool(pool_size)

    change_title(multiprocessing_pool_size=pool_size, enable_super_fast_mode=cfg.common.enable_super_fast_mode, show_next_regular_activity_info=True)

    show_multiprocessing_info(cfg)

    account_names = []
    for account_cfg in cfg.account_configs:
        account_names.append(account_cfg.name)

    logger.info(f"当前共配置{len(account_names)}个账号，具体如下：{account_names}")

    clean_dir_to_size(log_directory, cfg.common.max_logs_size * MiB, cfg.common.keep_logs_size * MiB)
    clean_dir_to_size(f"utils/{log_directory}", cfg.common.max_logs_size * MiB, cfg.common.keep_logs_size * MiB)

    current_chrome_version = QQLogin(cfg.common).get_chrome_major_version()
    remove_old_version_portable_chrome_files(current_chrome_version)

    show_ask_message_box(cfg)

    # 检查是否有更新，用于提示未购买自动更新的朋友去手动更新~
    if cfg.common.check_update_on_start:
        check_update(cfg)

    check_all_skey_and_pskey(cfg)

    check_djc_role_binding()

    # 确保道聚城绑定OK后在活动运行同时进行异步的弹窗提示
    check_first_run_async(cfg)

    # 挪到所有账号都登陆后再尝试自动更新，从而能够判定是否已购买DLC
    try_auto_update(cfg)

    # 查询付费信息供后面使用
    show_head_line("查询付费信息")
    logger.warning("开始查询付费信息，请稍候~")
    user_buy_info = get_user_buy_info(cfg.get_qq_accounts())
    show_buy_info(user_buy_info, cfg, need_show_message_box=False)

    sas(cfg, "启动时展示账号概览", user_buy_info)

    # 预先尝试创建和加入固定队伍，从而每周第一次操作的心悦任务也能加到队伍积分中
    try_join_xinyue_team(cfg, user_buy_info)

    # 正式进行流程
    run(cfg, user_buy_info)

    try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once(cfg, user_buy_info)

    # 尝试领取心悦组队奖励
    try_take_xinyue_team_award(cfg, user_buy_info)

    enable_card_lottery = is_ark_lottery_enabled()

    if enable_card_lottery:
        auto_send_cards(cfg)

    show_extra_infos(cfg)
    sas(cfg, "运行完毕展示账号概览", user_buy_info)

    if enable_card_lottery:
        show_lottery_status("卡片赠送完毕后展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg, need_show_tips=True)

    show_pay_info(cfg)

    show_recommend_reward_tips(user_buy_info)

    # 显示小助手的使用概览
    if cfg.common._show_usage:
        show_usage()

    # 运行结束展示下多进程信息
    show_multiprocessing_info(cfg)

    # 检查是否有更新，用于提示未购买自动更新的朋友去手动更新~
    if cfg.common.check_update_on_end:
        check_update(cfg)

    # 运行完毕备份配置到本机数据目录
    try_save_configs_to_user_data_dir()

    increase_counter(name="run/end", ga_type=ga.GA_REPORT_TYPE_PAGE_VIEW)

    show_head_line("运行完毕")


def main_wrapper():
    freeze_support()

    logger.info(color("bold_green") + f"已将工作目录设置为小助手所在目录：{dirpath}，之前为：{old_path}")

    try:
        run_start_time = datetime.datetime.now()
        main()
        total_used_time = datetime.datetime.now() - run_start_time
        logger.warning(color("fg_bold_yellow") + f"运行完成，共用时{total_used_time}")

        # 如果总用时太高的情况时，尝试提示开启多进程和超快速模式
        cfg = config()
        if total_used_time > datetime.timedelta(minutes=10) and (
            not cfg.common.enable_multiprocessing or not cfg.common.enable_super_fast_mode
        ):
            msg = (
                f"当前累计用时似乎很久({total_used_time})，是否要尝试多进程和超快速模式？\n"
                "多进程模式下，将开启多个进程并行运行不同账号的领取流程\n"
                "额外开启超快速模式，会进一步将不同账号的不同活动都异步领取，进一步加快领取速度\n"
                "\n"
                "如果需要开启，请打开配置工具，在【公共配置】tab中勾选【是否启用多进程功能】和【是否启用超快速模式（并行活动）】"
            )
            logger.warning(color("bold_cyan") + msg)
            if is_weekly_first_run("用时过久提示"):
                async_message_box(msg, "用时过久", print_log=False)

        # 按照分钟级别来统计使用时长
        total_minutes = int(total_used_time.total_seconds()) // 60
        increase_counter(ga_category="run_used_time_minutes", name=total_minutes)
    except Exception as e:
        show_unexpected_exception_message(e)
        # 如果在github action，则继续抛出异常
        if is_run_in_github_action():
            raise e
    finally:
        # 暂停一下，方便看结果
        if not disable_pause_after_run() and not is_run_in_github_action():
            async_call_close_pool_after_some_time()
            pause()
        close_pool()


def async_call_close_pool_after_some_time():
    def _close():
        wait_time = 10 * 60
        logger.info(f"{wait_time} 秒后将自动关闭进程池，方便有足够时间查看进程池中触发的弹窗信息")
        time.sleep(wait_time)
        close_pool()

    async_call(_close)


if __name__ == "__main__":
    main_wrapper()
