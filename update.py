from __future__ import annotations

import platform
import random
import re
import webbrowser
from datetime import datetime

import requests

from config import CommonConfig
from dao import UpdateInfo
from download import download_github_raw_content
from first_run import is_weekly_first_run
from log import color, logger
from upload_lanzouyun import Uploader
from util import (
    async_message_box,
    bypass_proxy,
    get_next_regular_activity_desc,
    get_time_since_last_update,
    is_run_in_github_action,
    is_windows,
    try_except,
    use_by_myself,
    use_proxy,
)
from version import now_version, ver_time

if is_windows():
    import win32api
    import win32con


def get_update_desc(config: CommonConfig):
    try:
        uploader = Uploader()
        latest_version = uploader.latest_version()

        if not need_update(now_version, latest_version):
            return ""

        return f"最新版本为v{latest_version}，请及时更新~"
    except Exception as e:
        logger.debug("get_update_desc error", exc_info=e)
        return ""


# 启动时检查是否有更新
def check_update_on_start(config: CommonConfig):
    if config.bypass_proxy:
        logger.info("检查更新前临时启用代理")
        use_proxy()

    check_update = config.check_update_on_start or config.check_update_on_end
    try:
        if is_run_in_github_action():
            logger.info("当前在github action环境下运行，无需检查更新")
            return

        if not check_update:
            logger.warning("启动时检查更新被禁用，若需启用请在config.toml中设置")
            return

        ui = get_update_info(config)

        if check_update:
            try_manaual_update(ui)
    except Exception as e:
        logger.debug(f"更新失败 {e}")
        if check_update:
            update_fallback(config)
    finally:
        if config.bypass_proxy:
            logger.info("检查完毕，继续无视代理")
            bypass_proxy()


def try_manaual_update(ui: UpdateInfo) -> bool:
    if not is_windows():
        logger.info("当前不是在windows下运行，不尝试检查更新")
        return False

    if need_update(now_version, ui.latest_version):
        logger.info(f"当前版本为{now_version}，已有最新版本{ui.latest_version}，更新内容为{ui.update_message}")

        ask_update = True
        if platform.system() == "Windows":
            message = (
                f"当前版本为{now_version}，已有最新版本{ui.latest_version}. 你需要更新吗?\n" f"{ui.update_message}"
            )
            res = win32api.MessageBox(0, message, "更新", win32con.MB_OKCANCEL)
            if res == win32con.IDOK:
                ask_update = True
            else:
                ask_update = False
        else:
            # 非windows系统默认更新
            ask_update = True

        if ask_update:
            if not is_shared_content_blocked(ui.netdisk_link):
                webbrowser.open(ui.netdisk_link)
                win32api.MessageBox(
                    0, f"蓝奏云网盘提取码为： {ui.netdisk_passcode}", "蓝奏云网盘提取码", win32con.MB_ICONINFORMATION
                )
            else:
                # 如果分享的网盘链接被系统屏蔽了，写日志并弹窗提示
                logger.warning(f"网盘链接={ui.netdisk_link}又被系统干掉了=-=")
                webbrowser.open("https://github.com/fzls/djc_helper/releases")
                message = (
                    "分享的网盘地址好像又被系统给抽掉了呢=。=先暂时使用github的release页面下载吧0-0\n"
                    "请稍作等待~ 风之凌殇看到这个报错后会尽快更新网盘链接的呢\n"
                    "届时再启动程序将自动获取到最新的网盘地址呢~"
                )
                win32api.MessageBox(0, message, "不好啦", win32con.MB_ICONERROR)
        else:
            message = "如果想停留在当前版本，不想每次启动都弹出前面这个提醒更新的框框，可以打开配置工具，在【公共配置】/【更新】中取消检查更新即可。"
            win32api.MessageBox(0, message, "取消启动时自动检查更新方法", win32con.MB_ICONINFORMATION)
    else:
        logger.info(f"当前版本{now_version}已是最新版本，无需更新")

    has_new_version = need_update(now_version, ui.latest_version)
    return has_new_version


def update_fallback(config: CommonConfig):
    if not is_windows():
        return

    try:
        # 到这里一般是无法访问github，这时候试试gitee的方案
        latest_version = get_version_from_gitee()
        ui = UpdateInfo()
        ui.latest_version = latest_version
        ui.netdisk_link = config.netdisk_link
        ui.netdisk_passcode = "fzls"
        ui.update_message = "当前无法访问github，暂时无法获取更新内容，若欲知更新内容，请浏览gitee主页进行查看哦~\n\nhttps://gitee.com/fzls/djc_helper/blob/master/CHANGELOG.MD"

        try_manaual_update(ui)
    except Exception as err:
        logger.error(
            f"手动检查版本更新失败（这个跟自动更新没有任何关系）,大概率是访问不了github和gitee导致的，可自行前往网盘查看是否有更新, 错误为{err}"
            + color("bold_green")
            + "\n（无法理解上面这段话的话，就当没看见这段话，对正常功能没有任何影响）"
        )


def get_latest_version_from_github(common_config: CommonConfig) -> str:
    try:
        logger.debug("尝试使用github 页面获取版本号")
        ui = get_update_info(common_config)
        return ui.latest_version
    except Exception:
        logger.debug("尝试使用gitee api获取版本号")
        return get_version_from_gitee()


@try_except()
def notify_manual_check_update_on_release_too_long(config: CommonConfig):
    time_since_last_update = get_time_since_last_update()
    max_update_duration_days = 45
    if time_since_last_update.days >= max_update_duration_days:
        msg = (
            f"当前版本更新于{ver_time}，距今已有{time_since_last_update}。\n"
            "可能原因如下:\n"
            f"    没有新活动：可能最近没有新活动，根据以往经验，下次常规的活动可能是 {get_next_regular_activity_desc()}\n"
            f"    购买了DLC：可能是dlc出了bug，后续版本可能已经修复\n"
            f"    未购买DLC：可能是因网络问题而未能检查更新\n"
            "\n"
            f"【很可能】已经有新的版本，建议在小助手的群公告的置顶公告中找到最新的下载地址，在浏览器中打开看看是否有新版本\n"
            "\n"
            "(若未加群，可打开配置工具，点击上方的【加群反馈问题/交流】按钮即可)\n"
            "\n"
            "如果在网盘没有发现更新的版本，说明自这次版本发布至今，没有任何新活动需要添加，也没有bug需要修复，无视本提示即可。\n"
            "本提示是用于在无法检查更新，且当前版本已经发布很久的情况下，每周保底提醒一次更新可能存在的新版本，避免一直使用好几个月以前的版本而无法领到新活动的奖励\n"
            "\n"
            "关于活动的发布周期，可以参考我之前统计的一个帖子，里面有过去几年各个月份蚊子腿活动发布的时间点：\n"
            "https://docs.qq.com/sheet/DYkNUemlxT2pibHNs\n"
        )
        logger.warning(color("bold_yellow") + msg)
        if is_weekly_first_run(f"notify_manual_update_if_can_not_connect_github_v{now_version}"):
            async_message_box(
                msg, "当前版本似乎太老了，请按提示确认是否存在更新的版本", open_url=config.netdisk_link, print_log=False
            )


# 获取最新版本号与下载网盘地址
def get_update_info(config: CommonConfig) -> UpdateInfo:
    # 尝试通过raw文件来解析更新信息
    try:
        return get_update_info_by_download_raw_file()
    except Exception as e:
        logger.warning("尝试下载raw文件来解析更新信息失败")
        logger.debug("具体信息", exc_info=e)

    # 尝试从github页面来解析更新信息
    changelog_page = "https://github.com/fzls/djc_helper/blob/master/CHANGELOG.MD"
    readme_page = "https://github.com/fzls/djc_helper/blob/master/README.MD"
    try:
        return _get_update_info(changelog_page, readme_page)
    except Exception as e:
        # 尝试使用镜像来访问
        logger.warning(f"使用 {changelog_page} 获取更新信息失败 错误={e}")
        logger.debug("具体信息", exc_info=e)

    raise Exception("无法获取更新信息")


def _get_update_info(changelog_page: str, readme_page: str) -> UpdateInfo:
    logger.info(f"尝试使用 {changelog_page} 来查询更新信息")

    update_info = UpdateInfo()

    # 获取github本项目的readme页面内容和changelog页面内容
    timeout = 3  # 由于国内网络不太好，加个超时
    changelog_html_text = requests.get(changelog_page, timeout=timeout).text
    readme_html_text = requests.get(readme_page, timeout=timeout).text

    # 从更新日志中提取所有版本信息
    versions = re.findall(r"(?<=[vV])[0-9.]+(?=\s+\d+\.\d+\.\d+)", changelog_html_text)
    # 找出其中最新的那个版本号
    update_info.latest_version = version_int_list_to_version(max(version_to_version_int_list(ver) for ver in versions))

    # 从readme中提取最新网盘信息
    netdisk_address_matches = re.findall(
        r'链接: <a[\s\S]+?rel="nofollow">(?P<link>.+?)<\/a> 提取码: (?P<passcode>[a-zA-Z0-9]+)',
        readme_html_text,
        re.MULTILINE,
    )
    # 先选取首个网盘链接作为默认值
    update_info.netdisk_link = netdisk_address_matches[0][0]
    update_info.netdisk_passcode = netdisk_address_matches[0][1]
    # 然后随机从仍有效的网盘链接中随机一个作为最终结果
    random.seed(datetime.now())
    random.shuffle(netdisk_address_matches)
    for match in netdisk_address_matches:
        if not is_shared_content_blocked(match[0]):
            update_info.netdisk_link = match[0]
            update_info.netdisk_passcode = match[1]
            break

    # 尝试提取更新信息
    update_message_list_match_groupdict_matches = re.search(
        r"(?<=更新公告</h1>)(\s|\S)+?<ol.+?>(?P<update_message_list>(\s|\S)+?)</ol>", changelog_html_text, re.MULTILINE
    )
    if update_message_list_match_groupdict_matches is not None:
        update_message_list_match_groupdict = update_message_list_match_groupdict_matches.groupdict()
        if "update_message_list" in update_message_list_match_groupdict:
            update_message_list_str = update_message_list_match_groupdict["update_message_list"]
            update_messages = re.findall("<li>(?P<update_message>.+?)</li>", update_message_list_str, re.MULTILINE)
            update_info.update_message = "\n".join(
                f"{idx + 1}. {message}" for idx, message in enumerate(update_messages)
            )
    else:
        update_info.update_message = (
            "更新内容解析失败，不影响正常使用。如有兴趣，可查看最新版本 相关信息/CHANGELOG.MD 中最上面的内容"
        )
        if use_by_myself():
            async_message_box(
                ("走到这里说明提取更新信息的正则表达式不符合最新的网页了，去瞅瞅看是否需要调整正则表达式\n"),
                f"(仅自己可见)提取更新内容出错了 {now_version} {ver_time}",
                show_once_daily=True,
            )

    logger.info(
        f"netdisk_address_matches={netdisk_address_matches}, selected=({update_info.netdisk_link}, {update_info.netdisk_passcode})"
    )

    return update_info


def get_update_info_by_download_raw_file() -> UpdateInfo:
    logger.info("尝试从github下载源文件来解析更新信息")
    readme_filepath = download_github_raw_content("README.MD")
    changelog_filepath = download_github_raw_content("CHANGELOG.MD")

    readme_txt = open(readme_filepath, encoding="utf-8").read()
    changelog_txt = open(changelog_filepath, encoding="utf-8").read()

    logger.info(f"尝试从 {changelog_filepath} 中解析更新信息")

    update_info = UpdateInfo()

    # 从更新日志中提取所有版本信息
    versions = re.findall(r"(?<=[vV])[0-9.]+(?=\s+\d+\.\d+\.\d+)", changelog_txt)
    # 找出其中最新的那个版本号
    update_info.latest_version = version_int_list_to_version(max(version_to_version_int_list(ver) for ver in versions))

    # 从readme中提取最新网盘信息
    netdisk_address_matches = re.findall(
        r"链接: (?P<link>.+?) 提取码: (?P<passcode>[a-zA-Z0-9]+)",
        readme_txt,
        re.MULTILINE,
    )
    # 先选取首个网盘链接作为默认值
    update_info.netdisk_link = netdisk_address_matches[0][0]
    update_info.netdisk_passcode = netdisk_address_matches[0][1]
    # 然后随机从仍有效的网盘链接中随机一个作为最终结果
    random.seed(datetime.now())
    random.shuffle(netdisk_address_matches)
    for match in netdisk_address_matches:
        if not is_shared_content_blocked(match[0]):
            update_info.netdisk_link = match[0]
            update_info.netdisk_passcode = match[1]
            break

    # 尝试提取更新信息
    update_message_matches = re.search(
        r"(?<=更新公告)\s*(?P<update_message>(\s|\S)+?)\n\n", changelog_txt, re.MULTILINE
    )
    if update_message_matches is not None:
        update_info.update_message = update_message_matches.groupdict()["update_message"]
    else:
        update_info.update_message = (
            "更新内容解析失败，不影响正常使用。如有兴趣，可查看最新版本 相关信息/CHANGELOG.MD 中最上面的内容"
        )
        if use_by_myself():
            async_message_box(
                ("走到这里说明从raw文件解析更新信息的正则表达式不符合最新的网页了，去瞅瞅看是否需要调整正则表达式\n"),
                f"(仅自己可见)提取更新内容出错了 {now_version} {ver_time}",
                show_once_daily=True,
            )

    logger.info(
        f"netdisk_address_matches={netdisk_address_matches}, selected=({update_info.netdisk_link}, {update_info.netdisk_passcode})"
    )

    return update_info


# 是否需要更新
def need_update(current_version, latest_version) -> bool:
    return version_less(current_version, latest_version)


def version_less(current_version="1.0.0", latest_version="1.0.1") -> bool:
    return version_to_version_int_list(current_version) < version_to_version_int_list(latest_version)


# [3, 2, 2] => 3.2.2
def version_int_list_to_version(version_int_list):
    return ".".join([str(subv) for subv in version_int_list])


# 3.2.2 => [3, 2, 2]
def version_to_version_int_list(version):
    return [int(subv) for subv in version.split(".")]


# 访问网盘地址，确认分享是否被系统干掉了- -
def is_shared_content_blocked(share_netdisk_addr: str) -> bool:
    # 切换蓝奏云，暂时应该不会被屏蔽了- -
    return False


def get_netdisk_addr(config: CommonConfig):
    try:
        ui = get_update_info(config)
        return ui.netdisk_link
    except Exception:
        return config.netdisk_link


# 备选方案：从gitee获取最新版本号（但不解析具体版本内容，作为github的fallback）
@try_except(return_val_on_except="1.0.0")
def get_version_from_gitee() -> str:
    logger.info("尝试从gitee获取更新信息")

    version_list = get_version_list_from_gitee()
    return version_list[0]


def get_version_list_from_gitee() -> list[str]:
    api = "https://gitee.com/api/v5/repos/fzls/djc_helper/tags"
    res = requests.get(api, timeout=10).json()

    reg_version = r"v\d+(\.\d+)*"
    res = filter(lambda tag_info: re.match(reg_version, tag_info["name"]) is not None, res)

    version_list = list([tag_info["name"][1:] for tag_info in res])
    version_list.sort(key=version_to_version_int_list, reverse=True)

    return version_list


if __name__ == "__main__":
    from config import config, load_config

    load_config()
    cfg = config()
    cfg.common.check_update_on_start = True

    notify_manual_check_update_on_release_too_long(cfg.common)
    check_update_on_start(cfg.common)

    ver = get_version_from_gitee()
    print(f"最新版本是：{ver}")

    info = get_update_info_by_download_raw_file()
    print(info)
