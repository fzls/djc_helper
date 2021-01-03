# 更新器不启用文件日志
from log import logger, fileHandler, new_file_handler, color
from version import now_version

logger.name = "auto_updater"
logger.removeHandler(fileHandler)
logger.addHandler(new_file_handler())

import time
import argparse
import os
import subprocess
from distutils import dir_util
from upload_lanzouyun import Uploader
from update import need_update

lanzou_cookie = {
    "ylogin": "1442903",
    "phpdisk_info": "VmNRZwxqBDpSaVMzXTRWBVIzDDoIWF07ADRVNgczV21UYgU2VzYFOVVhUjdcDwdqWz9QZ108VDQHYQdvATcLO1ZhUTUMOgQ8UjZTYl1iVmpSNwxsCGZdPAAxVTwHNlcxVGAFY1c0BWpVM1I0XD8HVFs6UGVdN1QxBzwHZQE2CzpWYlFlDGs%3D",
}

bandizip_executable_path = "./bandizip_portable/bz.exe"


# 自动更新的基本原型，日后想要加这个逻辑的时候再细化接入
def auto_update():
    args = parse_args()

    logger.info("更新器的进程为{}，主进程为{}".format(os.getpid(), args.pid))

    # note: 工作目录预期为小助手的exe所在目录
    logger.info("切换工作目录到{}".format(args.cwd))
    os.chdir(args.cwd)

    uploader = Uploader(lanzou_cookie)

    # 进行实际的检查是否需要更新操作
    latest_version = uploader.latest_version()
    logger.info("当前版本为{}，网盘最新版本为{}".format(args.version, latest_version))

    if need_update(args.version, latest_version):
        update(args, uploader)
        start_new_version(args)
    else:
        logger.info("已经是最新版本，不需要更新")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", default=0, type=int)
    parser.add_argument("--version", default="1.0.0", type=str)
    parser.add_argument("--cwd", default=".", type=str)
    parser.add_argument("--exe_name", default="DNF蚊子腿小助手.exe", type=str)
    args = parser.parse_args()

    return args


def update(args, uploader):
    logger.info("需要更新，开始更新流程")

    try:
        # 首先尝试使用增量更新文件
        patches_range = uploader.latest_patches_range()
        logger.info("当前可以应用增量补丁更新的版本范围为{}".format(patches_range))

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
    tmp_dir = "_update_temp_dir"

    logger.info("更新前，先移除临时目录，避免更新失败时这个目录会越来越大")
    dir_util.remove_tree(tmp_dir)

    logger.info("开始下载最新版本的压缩包")
    filepath = uploader.download_latest_version(tmp_dir)

    logger.info("下载完毕，开始解压缩")
    decompress(filepath, tmp_dir)

    target_dir = filepath.replace('.7z', '')
    logger.info("预处理解压缩文件：移除部分文件")
    for file in ["config.toml", "utils/auto_updater.exe"]:
        file_to_remove = os.path.realpath(os.path.join(target_dir, file))
        try:
            logger.info("移除 {}".format(file_to_remove))
            os.remove(file_to_remove)
        except Exception as e:
            logger.debug("移除 {} 时出错了".format(file_to_remove), exc_info=e)

    kill_original_process(args.pid)

    logger.info("进行更新操作...")
    dir_util.copy_tree(target_dir, ".")

    logger.info("更新完毕，移除临时目录")
    dir_util.remove_tree(tmp_dir)

    return True


def incremental_update(args, uploader):
    tmp_dir = "_update_temp_dir"

    logger.info("更新前，先移除临时目录，避免更新失败时这个目录会越来越大")
    dir_util.remove_tree(tmp_dir)

    logger.info("开始下载增量更新包")
    filepath = uploader.download_latest_patches(tmp_dir)

    logger.info("下载完毕，开始解压缩")
    decompress(filepath, tmp_dir)

    kill_original_process(args.pid)

    target_dir = filepath.replace('.7z', '')
    target_patch = os.path.join(target_dir, "{}.patch".format(args.version))
    logger.info("开始应用补丁 {}".format(target_patch))
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
        logger.error("增量更新失败，错误码为{}，具体报错请看上面日志".format(ret_code))
        return False

    logger.info("更新完毕，移除临时目录")
    dir_util.remove_tree(tmp_dir)

    return True


def decompress(filepath, target_dir):
    subprocess.call([os.path.realpath(bandizip_executable_path), "x", "-target:auto", filepath, target_dir])


def kill_original_process(pid):
    logger.info("尝试干掉原进程={}".format(pid))
    try:
        os.kill(pid, 9)
    except OSError:
        logger.warning("未找到该pid，也许是早已经杀掉了")

    logger.info("等待五秒，确保原进程已经被干掉")
    time.sleep(5)


def start_new_version(args):
    target_exe = os.path.join(args.cwd, args.exe_name)
    logger.info("更新完毕，重新启动程序 {}".format(target_exe))
    subprocess.call([target_exe])


if __name__ == '__main__':
    try:
        os.system("title 自动更新工具")
        auto_update()
    except Exception as e:
        msg = (
            "更新器 ver {} 运行过程中出现未捕获的异常。\n"
            "目前更新器处于测试模式，可能会有一些未考虑到的点，请加群553925117反馈"
        ).format(now_version)
        logger.exception(color("fg_bold_red") + msg, exc_info=e)

        logger.info("完整截图反馈后点击任意键继续流程，谢谢合作~")
        os.system("PAUSE")

# 示例用法
# import subprocess
# import os
# import argparse
# import sys
#
# version = "1.0.0"
#
# print("这是更新前的主进程，version={}".format(version))
#
# print("主进程pid={}".format(os.getpid()))
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
