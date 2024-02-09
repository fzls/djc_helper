import os
import subprocess

from log import color
from upload_lanzouyun import Uploader
from util import logger, parse_time, parse_timestamp
from version import now_version


def demo():
    logger.info(
        color("bold_yellow")
        + "尝试启动更新器，等待其执行完毕。若版本有更新，则会干掉这个进程并下载更新文件，之后重新启动进程...(请稍作等待）"
    )

    dlc_path = os.path.realpath("auto_updater.py")
    p = subprocess.Popen(
        [
            dlc_path,
            "--pid",
            str(os.getpid()),
            "--version",
            str(now_version),
            "--cwd",
            os.getcwd(),
            "--exe_name",
            os.path.realpath("DNF蚊子腿小助手.exe"),
        ],
        cwd="utils",
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    p.wait()

    if p.returncode != 0:
        last_modify_time = parse_timestamp(os.stat(dlc_path).st_mtime)
        logger.error(f"DLC出错了，错误码为{p.returncode}，DLC最后一次修改时间为{last_modify_time}")

        uploader = Uploader()
        netdisk_latest_dlc_info = uploader.find_latest_dlc_version()
        latest_version_time = parse_time(netdisk_latest_dlc_info.time)

        if latest_version_time > last_modify_time:
            logger.info(
                f"网盘中最新版本dlc上传于{latest_version_time}左右，在当前版本最后修改时间{last_modify_time}之后，有可能已经修复dlc的该问题，将尝试更新dlc为最新版本"
            )
            uploader.download_file(netdisk_latest_dlc_info, "utils")
        else:
            logger.warning(
                f"网盘中最新版本dlc上传于{latest_version_time}左右，在当前版本最后修改时间{last_modify_time}之前，请耐心等待修复该问题的新版本发布~"
            )


if __name__ == "__main__":
    demo()
