# 更新器不启用文件日志
from log import logger, fileHandler

logger.name = "auto_updater"
logger.removeHandler(fileHandler)

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

bandizip_executable_path = os.path.realpath("./bandizip_portable/bz.exe")


# 自动更新的基本原型，日后想要加这个逻辑的时候再细化接入
def auto_update():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", default=0, type=int)
    parser.add_argument("--version", default="1.0.0", type=str)
    parser.add_argument("--cwd", default=".", type=str)
    parser.add_argument("--exe_name", default="DNF蚊子腿小助手.exe", type=str)
    args = parser.parse_args()

    logger.info("更新器的进程为{}，主进程为{}".format(os.getpid(), args.pid))

    # note: 工作目录预期为小助手的exe所在目录
    logger.info("切换工作目录到{}".format(args.cwd))
    os.chdir(args.cwd)

    uploader = Uploader(lanzou_cookie)

    # 进行实际的检查是否需要更新操作
    latest_version = uploader.latest_version()
    logger.info("当前版本为{}，网盘最新版本为{}".format(args.version, latest_version))

    if need_update(args.version, latest_version):
        tmp_dir = "_update_temp_dir"

        logger.info("需要更新，开始下载{}版本的压缩包".format(latest_version))
        filepath = uploader.download_latest_version(tmp_dir)

        logger.info("下载完毕，开始解压缩")
        subprocess.call([bandizip_executable_path, "x", "-target:auto", filepath, tmp_dir])

        target_dir = filepath.replace('.7z', '')

        logger.info("预处理解压缩文件：移除部分文件")
        for file in ["config.toml", "utils/auto_updater.exe"]:
            file_to_remove = os.path.join(target_dir, file)
            try:
                logger.info("移除 {}".format(file_to_remove))
                os.remove(file_to_remove)
            except Exception as e:
                logger.debug("移除 {} 时出错了".format(file_to_remove), exc_info=e)

        logger.info("尝试干掉原进程={}".format(args.pid))
        os.kill(args.pid, 9)

        logger.info("进行更新操作...")
        dir_util.copy_tree(target_dir, ".")

        logger.info("更新完毕，移除临时目录")
        dir_util.remove_tree(tmp_dir)

        target_exe = os.path.join(args.cwd, args.exe_name)
        logger.info("更新完毕，重新启动程序 {}".format(target_exe))
        subprocess.call([target_exe])
    else:
        logger.info("已经是最新版本，不需要更新")


if __name__ == '__main__':
    auto_update()

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
