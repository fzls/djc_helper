from __future__ import annotations

import os.path
import pathlib
import re
import shutil
import subprocess

import requests
from bs4 import BeautifulSoup

from alist import upload
from compress import compress_dir_with_bandizip, decompress_dir_with_bandizip
from download import download_file
from log import color, logger
from update import version_to_version_int_list
from util import (
    change_console_window_mode_async,
    download_chrome_driver,
    make_sure_dir_exists,
    parse_major_version,
    pause,
    remove_directory,
    remove_file,
    show_head_line,
    try_except,
)

TEMP_DIR = "utils/chrome_temporary_dir"
SRC_DIR = os.path.realpath(".")


def download_latest_chrome_driver():
    latest_version = get_latest_chrome_driver_version()

    download_chrome_driver(latest_version, ".", SRC_DIR)


def get_latest_chrome_driver_version() -> str:
    res = requests.get("https://chromedriver.storage.googleapis.com/LATEST_RELEASE")

    return res.text


def get_latest_major_version() -> int:
    return parse_major_version(get_latest_chrome_driver_version())


def create_portable_chrome():
    latest_dir = get_latest_installed_chrome_version_directory()
    major_version = parse_major_version(os.path.basename(latest_dir))

    latest_installer = os.path.join(latest_dir, "Installer", "chrome.7z")

    logger.info(f"复制 {latest_installer} 到 当前目录中 {os.getcwd()}")
    shutil.copy2(latest_installer, ".")

    logger.info("解压缩后重新压缩，减小大小")
    temp_zip = os.path.basename(latest_installer)
    decompress_dir_with_bandizip(temp_zip, dir_src_path=SRC_DIR)

    decompressed_dir = "Chrome-bin"
    new_zip_name = f"chrome_portable_{major_version}.7z"
    logger.info(color("bold_yellow") + f"开始重新压缩打包为 {new_zip_name}，大概需要一到两分钟，请耐心等候~ ")
    compress_dir_with_bandizip(decompressed_dir, new_zip_name, dir_src_path=SRC_DIR, extra_options=["-storeroot:no"])

    logger.info("移除中间文件")
    remove_file(temp_zip)
    remove_directory(decompressed_dir)

    logger.info(color("bold_yellow") + f"便携版已制作完毕: {new_zip_name}")


def get_latest_installed_chrome_version_directory() -> str:
    chrome_dir = os.path.expandvars("%PROGRAMFILES%/Google/Chrome/Application")

    version_and_path_list: list[tuple[str, str]] = []

    for entry in pathlib.Path(chrome_dir).glob("*"):
        if not entry.is_dir():
            continue

        if re.match(r"\d+\.\d+\.\d+\.\d+", entry.name):
            version_and_path_list.append((entry.name, str(entry)))

    if len(version_and_path_list) == 0:
        raise FileNotFoundError("未找到最新安装的chrome目录")

    version_and_path_list.sort(key=lambda vp: version_to_version_int_list(vp[0]), reverse=True)
    return version_and_path_list[0][1]


def download_chrome_installer():
    download_page = requests.get(
        "https://www.ghxi.com/pcchrome.html",
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        },
    ).text

    soup = BeautifulSoup(download_page, "html.parser")

    latest_version_soup = soup.find("h1", class_="entry-title")

    # 'Google Chrome v110.0.5481.78 正式版 离线安装包'
    reg_version = r"Google Chrome v([0-9.]+) 正式版 离线安装包"
    match = re.match(reg_version, latest_version_soup.text)
    latest_version = match.group(1)

    download_url = "http://redirector.gvt1.com/edgedl/chrome/install/GoogleChromeStandaloneEnterprise64.msi"

    logger.info(f"最新版本的下载链接为: {download_url}")
    download_file(download_url, ".", f"Chrome_{latest_version}_普通安装包_非便携版.exe")


def update_qq_login_version():
    major_version = get_latest_major_version()
    latest_chrome_driver_version = get_latest_chrome_driver_version()

    qq_login_file = os.path.join(SRC_DIR, "qq_login.py")

    replace_text_in_file(qq_login_file, r"chrome_major_version = (\d+)", f"chrome_major_version = {major_version}")
    replace_text_in_file(
        qq_login_file, r'chrome_driver_version = "[0-9.]+"', f'chrome_driver_version = "{latest_chrome_driver_version}"'
    )
    logger.info(
        f"已将 {qq_login_file} 中的 chrome_major_version 修改为 {major_version}, chrome_driver_version 修改为 {latest_chrome_driver_version}"
    )


def replace_text_in_file(filepath: str, pattern: str, repl: str):
    original_contents = open(filepath, encoding="utf-8").read()
    updated_contents = re.sub(pattern, repl, original_contents)

    open(filepath, "w", encoding="utf-8").write(updated_contents)


def update_linux_version():
    latest_version = get_latest_chrome_driver_version()

    ubuntu_file = os.path.join(SRC_DIR, "_ubuntu_download_chrome_and_driver.sh")
    centos_file = os.path.join(SRC_DIR, "_centos_download_and_install_chrome_and_driver.sh")

    # 100.0.4896.75
    re_version = r"(\d+)\.(\d+)\.(\d+)\.(\d+)"

    replace_text_in_file(ubuntu_file, re_version, str(latest_version))
    replace_text_in_file(centos_file, re_version, str(latest_version))
    logger.info(f"已将linux更新脚本中的版本替换为 {latest_version}")


def upload_all_to_netdisk():
    wanted_file_regex_list = [
        r"chromedriver_(\d+).exe",
        r"chrome_portable_(\d+).7z",
        r"Chrome_(\d+)\.(\d+)\.(\d+)\.(\d+)_普通安装包_非便携版.exe",
    ]

    files = list(pathlib.Path(".").glob("*"))
    for wanted_file_regex in wanted_file_regex_list:
        for file in files:
            if not re.match(wanted_file_regex, file.name):
                continue

            logger.info(f"开始上传 {file.name}")
            upload(os.path.realpath(str(file)), f"/文本编辑器、chrome浏览器、autojs、HttpCanary等小工具/{file.name}")


@try_except()
def update_latest_chrome():
    # 最大化窗口
    change_console_window_mode_async(disable_min_console=True)

    # 重置临时目录
    remove_directory(TEMP_DIR)
    make_sure_dir_exists(TEMP_DIR)

    logger.info(f"临时切换到 {TEMP_DIR}，方便后续操作")
    os.chdir(TEMP_DIR)

    show_head_line("从官方网站下载最新版chrome driver")
    download_latest_chrome_driver()

    show_head_line("开始利用本机chrome下载的更新包制作便携版")
    create_portable_chrome()

    show_head_line("从 果核剥壳网 下载最新离线安装包")
    download_chrome_installer()

    show_head_line("修改 qq_login.py 中的版本号为新的主版本号")
    update_qq_login_version()

    show_head_line("更新linux版的路径")
    update_linux_version()

    show_head_line("提示确认代码修改是否无误")
    logger.info(
        color("bold_green")
        + "请检查一遍代码，然后执行一遍 qq_login.py，以确认新的chrome制作无误，然后点击任意键提交git即可完成流程"
    )
    pause()

    show_head_line("上传到网盘")
    upload_all_to_netdisk()

    show_head_line("git commit 相关代码")
    os.chdir(SRC_DIR)
    latest_version = get_latest_chrome_driver_version()
    subprocess.call(
        [
            "git",
            "add",
            "qq_login.py",
            "_centos_download_and_install_chrome_and_driver.sh",
            "_ubuntu_download_chrome_and_driver.sh",
        ]
    )
    subprocess.call(["git", "commit", "-m", f"feat: 升级chrome版本到{latest_version}"])

    logger.info(f"更新完毕，清理临时目录 {TEMP_DIR}")
    remove_directory(TEMP_DIR)

    show_head_line("最后暂停下，方便确认结果")
    pause()


if __name__ == "__main__":
    update_latest_chrome()
