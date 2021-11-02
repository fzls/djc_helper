# 更新器不启用文件日志
from log import color, fileHandler, logger, new_file_handler
from version import now_version

logger.name = "auto_updater"
logger.removeHandler(fileHandler)
logger.addHandler(new_file_handler())

import argparse
import os
import subprocess
from distutils import dir_util

from compress import decompress_dir_with_bandizip
from update import need_update
from upload_lanzouyun import Uploader
from util import (bypass_proxy, change_title, exists_flag_file, kill_process,
                  pause_and_exit, show_unexpected_exception_message,
                  start_djc_helper)

bandizip_executable_path = "./utils/bandizip_portable/bz.exe"
tmp_dir = "_update_temp_dir"

# note: 作为cwd的默认值，用于检测是否直接双击自动更新工具
invalid_cwd = "./invalid_cwd"


# 自动更新的基本原型，日后想要加这个逻辑的时候再细化接入
def auto_update():
    args = parse_args()

    change_title("自动更新DLC")

    logger.info(color("bold_yellow") + f"更新器的进程为{os.getpid()}, 代码版本为{now_version}")
    logger.info(color("bold_yellow") + f"需要检查更新的小助手主进程为{args.pid}, 版本为{args.version}")

    # note: 工作目录预期为小助手的exe所在目录
    if args.cwd == invalid_cwd:
        logger.error("请不要直接双击打开自动更新工具，正确的用法是放到utils目录后，照常双击【DNF蚊子腿小助手.exe】来使用，小助手会自行调用自动更新DLC的")
        os.system("PAUSE")
        return

    logger.info(f"切换工作目录到{args.cwd}")
    os.chdir(args.cwd)

    if not exists_flag_file(".use_proxy"):
        bypass_proxy()
        logger.info(f"当前已默认无视系统代理（VPN），如果需要dlc使用代理，请在小助手目录创建 .use_proxy 目录或文件")

    uploader = Uploader()

    # 进行实际的检查是否需要更新操作
    latest_version = uploader.latest_version()
    logger.info(f"当前版本为{args.version}，网盘最新版本为{latest_version}")

    if need_update(args.version, latest_version):
        update(args, uploader)
        start_new_version(args)
    else:
        logger.info("已经是最新版本，不需要更新")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", default=0, type=int)
    parser.add_argument("--version", default="1.0.0", type=str)
    parser.add_argument("--cwd", default=invalid_cwd, type=str)
    parser.add_argument("--exe_name", default="DNF蚊子腿小助手.exe", type=str)
    args = parser.parse_args()

    return args


def update(args, uploader):
    logger.info("需要更新，开始更新流程")

    try:
        # 首先尝试使用增量更新文件
        patches_range = uploader.latest_patches_range()
        logger.info(f"当前可以应用增量补丁更新的版本范围为{patches_range}")

        can_use_patch = not need_update(args.version, patches_range[0]) and not need_update(patches_range[1], args.version)
        if can_use_patch:
            logger.info(color("bold_yellow") + "当前版本可使用增量补丁，尝试进行增量更新")

            update_ok = incremental_update(args, uploader)
            if update_ok:
                logger.info("增量更新完毕")
                return
            else:
                logger.warning("增量更新失败，尝试默认的全量更新方案")
    except Exception as e:
        logger.exception("增量更新失败，尝试默认的全量更新方案", exc_info=e)

    # 保底使用全量更新
    logger.info(color("bold_yellow") + "尝试全量更新")
    full_update(args, uploader)
    logger.info("全量更新完毕")
    return


def full_update(args, uploader):
    remove_temp_dir("更新前，先移除临时目录，避免更新失败时这个目录会越来越大")

    logger.info("开始下载最新版本的压缩包")
    filepath = uploader.download_latest_version(tmp_dir)

    logger.info("下载完毕，开始解压缩")
    decompress(filepath, tmp_dir)

    target_dir = filepath.replace('.7z', '')
    logger.info("预处理解压缩文件：移除部分文件")
    for file in ["config.toml", "utils/auto_updater.exe"]:
        file_to_remove = os.path.realpath(os.path.join(target_dir, file))
        try:
            logger.info(f"移除 {file_to_remove}")
            os.remove(file_to_remove)
        except Exception as e:
            logger.debug(f"移除 {file_to_remove} 时出错了", exc_info=e)

    kill_original_process(args.pid)

    logger.info("进行更新操作...")
    dir_util.copy_tree(target_dir, ".")

    remove_temp_dir("更新完毕，移除临时目录")

    return True


def incremental_update(args, uploader):
    remove_temp_dir("更新前，先移除临时目录，避免更新失败时这个目录会越来越大")

    logger.info("开始下载增量更新包")
    filepath = uploader.download_latest_patches(tmp_dir)

    logger.info("下载完毕，开始解压缩")
    decompress(filepath, tmp_dir)

    kill_original_process(args.pid)

    target_dir = filepath.replace('.7z', '')
    target_patch = os.path.join(target_dir, f"{args.version}.patch")
    logger.info(f"开始应用补丁 {target_patch}")
    # hpatchz.exe -C-diff -f . "%target_patch_file%" .
    ret_code = subprocess.call([
        os.path.realpath("utils/hpatchz.exe"),
        "-C-diff",
        "-f",
        os.path.realpath("."),
        os.path.realpath(target_patch),
        os.path.realpath("."),
    ])

    if ret_code != 0:
        logger.error(f"增量更新失败，错误码为{ret_code}，具体报错请看上面日志")
        return False

    remove_temp_dir("更新完毕，移除临时目录")

    return True


def remove_temp_dir(msg):
    logger.info(msg)
    if os.path.isdir(tmp_dir):
        dir_util.remove_tree(tmp_dir)


def decompress(filepath, target_dir):
    decompress_dir_with_bandizip(filepath, ".", target_dir)


def kill_original_process(pid):
    return kill_process(pid)


def start_new_version(args):
    target_exe = os.path.join(args.cwd, args.exe_name)
    logger.info(f"更新完毕，重新启动程序 {target_exe}，并退出自动更新工具")

    start_djc_helper(target_exe)

    logger.info("退出配置工具")
    kill_process(os.getpid())


if __name__ == '__main__':
    try:
        os.system("title 自动更新工具")
        auto_update()
    except Exception as e:
        show_unexpected_exception_message(e)

        logger.info("完整截图反馈后点击任意键继续流程，谢谢合作~")
        pause_and_exit(1)

# 示例用法
# import subprocess
# import os
# import argparse
# import sys
#
# version = "1.0.0"
#
# print(f"这是更新前的主进程，version={version}")
#
# print(f"主进程pid={os.getpid()}")
#
# exe_path = sys.argv[0]
# dirpath, filename = os.path.dirname(exe_path), os.path.basename(exe_path)
#
# print("尝试启动更新器，并传入当前进程pid和版本号，等待其执行完毕。若版本有更新，则会干掉这个进程并下载更新文件，之后重新启动进程")
# p = subprocess.Popen([
#     "utils/auto_updater.exe",
#     "--pid", str(os.getpid()),
#     "--version", str(version),
#     "--cwd", dirpath,
#     "--exe_name", filename,
# ], shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, )
# p.wait()
#
# print("实际进行相关逻辑")
#
# print("主进程退出")
