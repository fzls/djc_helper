import datetime
from multiprocessing import freeze_support

from config import AccountConfig, CommonConfig, config, load_config
from djc_helper import DjcHelper
from log import color, logger
from main_def import _show_head_line, check_proxy, has_any_account_in_normal_run, show_multiprocessing_info
from pool import close_pool, get_pool, get_pool_size, init_pool
from qq_login import QQLogin
from util import change_console_window_mode_async, change_title, pause, show_unexpected_exception_message
from version import author, now_version, ver_time


def check_all_skey_and_pskey(cfg):
    if not has_any_account_in_normal_run(cfg):
        return
    _show_head_line("启动时检查各账号skey/pskey/openid是否过期")

    QQLogin(cfg.common).check_and_download_chrome_ahead()

    if cfg.common.enable_multiprocessing and cfg.is_all_account_auto_login():
        logger.info(
            color("bold_yellow")
            + f"已开启多进程模式({get_pool_size()})，并检测到所有账号均使用自动登录模式，将开启并行登录模式"
        )

        get_pool().starmap(
            do_check_all_skey_and_pskey,
            [
                (_idx + 1, account_config, cfg.common)
                for _idx, account_config in enumerate(cfg.account_configs)
                if account_config.is_enabled()
            ],
        )
        logger.info("全部账号检查完毕")
    else:
        for _idx, account_config in enumerate(cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            do_check_all_skey_and_pskey(idx, account_config, cfg.common)


def do_check_all_skey_and_pskey(idx: int, account_config: AccountConfig, common_config: CommonConfig):
    if not account_config.is_enabled():
        # 未启用的账户的账户不走该流程
        return None

    logger.warning(color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name})------------")
    djcHelper = DjcHelper(account_config, common_config)
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list(print_warning=False)


def run(cfg):
    _show_head_line("开始核心逻辑")

    start_time = datetime.datetime.now()

    if cfg.common.enable_multiprocessing:
        logger.info(f"已开启多进程模式({get_pool_size()})，将并行运行~")
        get_pool().starmap(
            do_run,
            [
                (_idx + 1, account_config, cfg.common)
                for _idx, account_config in enumerate(cfg.account_configs)
                if account_config.is_enabled()
            ],
        )
    else:
        for idx, account_config in enumerate(cfg.account_configs):
            idx += 1
            if not account_config.is_enabled():
                logger.info(f"第{idx}个账号({account_config.name})未启用，将跳过")
                continue

            do_run(idx, account_config, cfg.common)

    used_time = datetime.datetime.now() - start_time
    _show_head_line(f"处理总计{len(cfg.account_configs)}个账户 共耗时 {used_time}")


def do_run(idx: int, account_config: AccountConfig, common_config: CommonConfig):
    _show_head_line(f"开始处理第{idx}个账户({account_config.name})")

    start_time = datetime.datetime.now()

    djcHelper = DjcHelper(account_config, common_config)
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list()

    djcHelper.dnf_my_home(run_notify_only=True)

    used_time = datetime.datetime.now() - start_time
    _show_head_line(f"处理第{idx}个账户({account_config.name}) 共耗时 {used_time}")


def main():
    special_version_name = "我的小屋特别版"

    change_title(special_version_name)

    # 最大化窗口
    logger.info("尝试调整窗口显示模式，打包exe可能会运行的比较慢")
    change_console_window_mode_async()

    logger.warning(f"开始运行DNF蚊子腿小助手 {special_version_name}，ver={now_version} {ver_time}，powered by {author}")
    logger.warning(
        color("fg_bold_cyan")
        + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开付费指引/支持一下.png，扫码打赏哦~"
    )

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        raise Exception("未找到有效的账号配置，请检查是否正确配置。")

    check_proxy(cfg)

    pool_size = cfg.get_enabled_account_count() if cfg.common.enable_multiprocessing else 0
    init_pool(pool_size)

    change_title(special_version_name, multiprocessing_pool_size=pool_size)

    show_multiprocessing_info(cfg)

    check_all_skey_and_pskey(cfg)

    # 正式进行流程
    run(cfg)

    # 运行结束展示下多进程信息
    show_multiprocessing_info(cfg)


if __name__ == "__main__":
    freeze_support()
    try:
        run_start_time = datetime.datetime.now()
        main()
        logger.warning(color("fg_bold_yellow") + f"运行完成，共用时{datetime.datetime.now() - run_start_time}")
    except Exception as e:
        show_unexpected_exception_message(e)
    finally:
        # 暂停一下，方便看结果
        pause()
        close_pool()
