import datetime
from multiprocessing import freeze_support

from config import AccountConfig, CommonConfig, Config
from djc_helper import DjcHelper
from log import color, logger
from main_def import _show_head_line, check_proxy
from qq_login import QQLogin
from util import change_console_window_mode_async, change_title, pause, show_unexpected_exception_message
from version import author, now_version, ver_time


def check_all_skey_and_pskey(cfg):
    _show_head_line("启动时检查各账号skey/pskey/openid是否过期")

    QQLogin(cfg.common).check_and_download_chrome_ahead()

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
    djcHelper.fetch_pskey()
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list(print_warning=False)


def run(cfg):
    _show_head_line("开始核心逻辑")

    start_time = datetime.datetime.now()

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
    change_title("我的小屋特别版")

    # 最大化窗口
    logger.info("尝试调整窗口显示模式，打包exe可能会运行的比较慢")
    change_console_window_mode_async()

    logger.warning(f"开始运行DNF蚊子腿小助手 我的小屋特别版，ver={now_version} {ver_time}，powered by {author}")

    # 读取配置信息
    cfg = Config()

    account_config = AccountConfig()
    account_config.on_config_update({})
    cfg.account_configs.append(account_config)

    if len(cfg.account_configs) == 0:
        raise Exception("未找到有效的账号配置，请检查是否正确配置。")

    check_proxy(cfg)

    change_title("我的小屋特别版")

    check_all_skey_and_pskey(cfg)

    # 正式进行流程
    run(cfg)


if __name__ == "__main__":
    freeze_support()
    try:
        run_start_time = datetime.datetime.now()
        main()
        logger.warning(color("fg_bold_yellow") + f"运行完成，共用时{datetime.datetime.now() - run_start_time}")
    except Exception as e:
        show_unexpected_exception_message(e)
    finally:
        pause()
