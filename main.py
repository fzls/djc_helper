import os

from config import load_config, config
from djc_helper import DjcHelper
from log import logger
from update import check_update_on_start
from version import *

if __name__ == '__main__':
    logger.info("开始运行道聚城自动化操作小助手，ver={} {}，powered by {}".format(now_version, ver_time, author))

    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    if len(cfg.account_configs) == 0:
        logger.error("未找到有效的账号配置，请检查是否正确配置。ps：多账号版本配置与旧版本不匹配，请重新配置")
        exit(-1)

    logger.info("将操作下列账号")
    logger.info("序号\t账号名\t\t启用状态")
    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        status = "启用" if account_config.enable else "未启用"
        logger.info("{}\t{}\t{}".format(idx, account_config.name, status))
    logger.info("")

    for _idx, account_config in enumerate(cfg.account_configs):
        idx = _idx + 1
        if not account_config.enable:
            logger.info("第{}个账号({})未启用，将跳过".format(idx, account_config.name))
            continue

        logger.info("------------开始处理第{}个账户({})------------\n".format(idx, account_config.name))

        djcHelper = DjcHelper(account_config)
        djcHelper.run()

        if account_config._debug_stop_after_this:
            logger.warn("调试开关打开，不再处理后续账户")
            break

    # 检查是否需要更新，放到末尾，避免在启动时因网络不能访问github而卡住-。-这个时机就算卡住也没啥大问题了
    logger.info((
        "\n"
        "++++++++++++++++++++++++++++++++++++++++\n"
        "全部账号操作已经成功完成\n"
        "现在准备访问github仓库相关页面来检查是否有新版本\n"
        "由于国内网络问题，访问可能会比较慢，请不要立即关闭，可以选择最小化或切换到其他窗口0-0\n"
        "若有新版本会自动弹窗提示~\n"
        "++++++++++++++++++++++++++++++++++++++++\n"
    ))

    # 全部账号操作完成后，检查更新
    check_update_on_start(cfg.account_configs[0])

    # 暂停一下，方便看结果
    os.system("PAUSE")
