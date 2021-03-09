from main_def import *
from main_def import _show_head_line
from show_usage import *
from usage_count import *


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


def run(cfg):
    _show_head_line("开始核心逻辑")

    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.is_enabled():
            logger.info(f"第{idx}个账号({account_config.name})未启用，将跳过")
            continue

        _show_head_line(f"开始处理第{idx}个账户({account_config.name})")

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()
        djcHelper.ark_lottery()


def main():
    change_title("集卡特别版", need_append_new_version_info=False)

    # 最大化窗口
    logger.info("尝试最大化窗口，打包exe可能会运行的比较慢")
    maximize_console()

    logger.warning(f"开始运行DNF蚊子腿小助手 集卡特别版，ver={now_version} {ver_time}，powered by {author}")
    logger.warning(color("fg_bold_cyan") + "如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开支持一下.png，扫码打赏哦~")

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        logger.error("未找到有效的账号配置，请检查是否正确配置。")
        exit(-1)

    # 特别版强制启用每一个账号
    for account_config in cfg.account_configs:
        account_config.enable = True

    check_all_skey_and_pskey(cfg)

    # 正式进行流程
    run(cfg)

    auto_send_cards(cfg)
    show_lottery_status("卡片赠送完毕后展示各账号抽卡卡片以及各礼包剩余可领取信息", cfg, need_show_tips=True)


if __name__ == '__main__':
    try:
        run_start_time = datetime.datetime.now()
        main()
        logger.warning(color("fg_bold_yellow") + f"运行完成，共用时{datetime.datetime.now() - run_start_time}")
    except Exception as e:
        msg = f"ver {now_version} 运行过程中出现未捕获的异常，请加群1041823293反馈或自行解决。" + check_some_exception(e)
        logger.exception(color("fg_bold_red") + msg, exc_info=e)
        logger.warning(color("fg_bold_cyan") + "如果稳定报错，不妨打开网盘，看看是否有新版本修复了这个问题~")
        logger.warning(color("fg_bold_cyan") + "链接：https://fzls.lanzous.com/s/djc-helper")
    finally:
        # 暂停一下，方便看结果
        os.system("PAUSE")
