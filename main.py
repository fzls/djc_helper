import os

import util
from config import load_config, config
from djc_helper import DjcHelper
from log import logger
from update import check_update_on_start
from version import *


def show_accounts_status(cfg):
    logger.info("将操作下列账号")
    logger.info("序号\t账号名\t\t启用状态")
    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        status = "启用" if account_config.enable else "未启用"
        logger.info("{}\t{}\t{}".format(idx, account_config.name, status))
    logger.info("")


def try_join_xinyue_team(cfg):
    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.enable or account_config.run_mode == "pre_run":
            # 未启用的账户或者预运行阶段的账户不走该流程
            continue

        logger.info("")
        logger.info("------------尝试为第{}个账户({})加入心悦固定队------------\n".format(idx, account_config.name))

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        # 尝试加入固定心悦队伍
        djcHelper.try_join_fixed_xinyue_team()

        if cfg.common._debug_run_first_only:
            logger.warning("调试开关打开，不再处理后续账户")
            break


def run(cfg):
    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        if not account_config.enable:
            logger.info("第{}个账号({})未启用，将跳过".format(idx, account_config.name))
            continue

        logger.info("")
        logger.info("------------开始处理第{}个账户({})------------\n".format(idx, account_config.name))

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.run()

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
    util.maximize_console()

    logger.warning("开始运行DNF蚊子腿小助手，ver={} {}，powered by {}".format(now_version, ver_time, author))
    logger.warning("如果觉得我的小工具对你有所帮助，想要支持一下我的话，可以帮忙宣传一下或打开支持一下.png，扫码打赏哦~")

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        logger.error("未找到有效的账号配置，请检查是否正确配置。ps：多账号版本配置与旧版本不匹配，请重新配置")
        exit(-1)

    # 展示状态状况
    show_accounts_status(cfg)

    # 预先尝试创建和加入固定队伍，从而每周第一次操作的心悦任务也能加到队伍积分中
    try_join_xinyue_team(cfg)

    # 正式进行流程
    run(cfg)

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
