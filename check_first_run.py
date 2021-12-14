import platform
import threading

from config import Config
from first_run import is_first_run
from log import logger
from util import is_run_in_github_action, message_box


def check_first_run_async(cfg: Config):
    threading.Thread(target=check_first_run, args=(cfg,), daemon=True).start()


def check_first_run(cfg: Config):
    show_tip_on_first_run_config_ui()
    show_tip_on_first_run_promot()
    show_tip_on_first_run_any()
    show_tip_on_first_run_document()
    show_tip_on_first_run_use_old_config()

    if cfg.has_any_account_auto_login():
        show_tip_on_first_run_auto_login_mode()


def show_tip_on_first_run_config_ui():
    title = "配置工具"
    tips = """
    现已添加简易版配置工具，大家可以双击【DNF蚊子腿小助手配置工具.exe】进行体验~
            """
    loginfo = "首次运行弹出配置工具提示"

    show_tip_on_first_run("config_ui", title, tips, loginfo)


def show_tip_on_first_run_promot():
    title = "宣传"
    tips = """
    如果觉得好用的话，可否帮忙宣传一下哈(*^▽^*)
    或者扫描二维码打赏一下也是极好的φ(>ω<*)
    """
    loginfo = "首次运行弹出宣传弹窗"

    show_tip_on_first_run("promot", title, tips, loginfo)


def show_tip_on_first_run_any():
    title = "使用须知"
    tips = """# 『重要』与个人隐私有关的skey相关说明
    1. skey是腾讯系应用的通用鉴权票据，个中风险，请Google搜索《腾讯skey》后自行评估
    2. skey有过期时间，目前根据测试来看应该是一天。目前已实现手动登录、扫码登录（默认）、自动登录。手动登录需要自行在网页中登录并获取skey填写到配置表。扫码登录则会在每次过期时打开网页让你签到，无需手动填写。自动登录则设置过一次账号密码后续无需再操作。
    3. 本脚本仅使用skey进行必要操作，用以实现自动化查询、签到、领奖和兑换等逻辑，不会上传到与此无关的网站，请自行阅读源码进行审阅
    4. 如果感觉有风险，请及时停止使用本软件，避免后续问题
            """
    loginfo = "首次运行，弹出使用须知"

    show_tip_on_first_run("init", title, tips, loginfo)


def show_tip_on_first_run_document():
    title = "引导查看相关教程"
    tips = """
    如果使用过程中有任何疑惑，或者相关功能想要调整，都请先好好看看以下现有资源后再来提问~（如不想完整查看对应文档，请善用搜索功能，查找可能的关键词）
        1. 使用教程/使用文档.docx
        2. 使用教程/道聚城自动化助手使用视频教程.url
        3. config.toml以及config.example.toml中各个配置项说明
        4. DNF蚊子腿小助手配置工具.exe
            """
    loginfo = "首次运行弹出提示查看教程"

    show_tip_on_first_run("document", title, tips, loginfo, show_count=3)


def show_tip_on_first_run_use_old_config():
    title = "继承配置"
    tips = """
    如果是从旧版本升级过来的，则不需要再完整走一遍配置流程，直接将旧版本目录中的config.toml文件复制过来，替换新版本的这个文件就行。
    新版本可能新增一些配置，可查看更新日志或者自行对比新旧版本配置文件。如果未配置，则会使用设定的默认配置。
    更多信息可查看使用教程/使用文档.docx中背景知识章节中关于继承存档的描述
            """
    loginfo = "首次运行弹出提示继承以前配置"

    show_tip_on_first_run("use_old_config", title, tips, loginfo)


def show_tip_on_first_run_auto_login_mode():
    title = "自动登录须知"
    tips = """自动登录需要在本地配置文件明文保存账号和密码，利弊如下，请仔细权衡后再决定是否适用
    弊：
        1. 需要填写账号和密码，有潜在泄漏风险
        2. 需要明文保存到本地，可能被他人窥伺
        3. 涉及账号密码，总之很危险<_<
    利：
        1. 无需手动操作，一劳永逸

    若觉得有任何不妥，强烈建议改回其他需要手动操作的登录模式
            """
    loginfo = "首次运行自动登录模式，弹出利弊分析"

    show_tip_on_first_run("auto_login_mode", title, tips, loginfo, show_count=3)


def show_tip_on_first_run(first_run_tip_name, title, tips, loginfo, show_count=1):
    if not is_first_run(f"show_tip_{first_run_tip_name}"):
        logger.debug(f"{first_run_tip_name} 已经提示过，不再展示")
        return

    # 仅在window系统下检查
    if platform.system() != "Windows":
        return

    # 如果在github action环境下，则不弹窗
    if is_run_in_github_action():
        return

    # 若是首次运行，提示相关信息
    logger.info(loginfo)

    for i in range(show_count):
        _title = title
        if show_count != 1:
            _title = f"第{i + 1}/{show_count}次提示 {title}"
        message_box(tips, _title)


if __name__ == "__main__":
    from config import config

    check_first_run_async(config())
    input("按enter结束测试")
