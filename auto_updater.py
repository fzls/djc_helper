import platform
from distutils.errors import DistutilsFileError

from _create_patches import get_patch_7z_filename
from config import CommonConfig
from log import color, fileHandler, logger, new_file_handler
from version import now_version, ver_time

logger.name = "auto_updater"
logger.removeHandler(fileHandler)
logger.addHandler(new_file_handler())

import argparse
import os
import subprocess
from distutils import dir_util

from alist import download_from_alist, is_file_in_folder
from compress import decompress_dir_with_bandizip
from config_cloud import config_cloud
from download import download_latest_github_release
from update import get_latest_version_from_github, need_update
from upload_lanzouyun import Uploader
from usage_count import increase_counter
from util import (
    bypass_proxy,
    change_title,
    disable_quick_edit_mode,
    exists_flag_file,
    kill_process,
    pause_and_exit,
    range_from_one,
    show_unexpected_exception_message,
    start_djc_helper,
)

tmp_dir = "_update_temp_dir"

# note: 作为cwd的默认值，用于检测是否直接双击自动更新工具
invalid_cwd = "./invalid_cwd"

TEST_MODE = False


def check_keyboard_interrupt_on_download(file_name: str, total_size: int, now_size: int, used_seconds: float = 0.0):
    if platform.system() != "Windows":
        return

    import msvcrt

    if not msvcrt.kbhit():
        return

    print()
    logger.warning("检测到键盘输入，将尝试切换下一个镜像")

    # 将缓冲区的状态清空，避免影响到下一个镜像
    while msvcrt.kbhit():
        msvcrt.getch()

    raise InterruptedError()


# 自动更新的基本原型，日后想要加这个逻辑的时候再细化接入
def auto_update():
    args = parse_args()

    change_title("自动更新DLC")

    disable_quick_edit_mode()

    logger.info(color("bold_yellow") + f"更新器的进程为{os.getpid()}, 代码版本为{now_version} {ver_time}")
    logger.info(color("bold_yellow") + f"需要检查更新的小助手主进程为{args.pid}, 版本为{args.version}")

    # note: 工作目录预期为小助手的exe所在目录
    if args.cwd == invalid_cwd:
        logger.error(
            "请不要直接双击打开自动更新工具，正确的用法是放到utils目录后，照常双击【DNF蚊子腿小助手.exe】来使用，小助手会自行调用自动更新DLC的"
        )
        os.system("PAUSE")
        return

    logger.info(f"切换工作目录到{args.cwd}")
    os.chdir(args.cwd)

    if not exists_flag_file(".use_proxy"):
        bypass_proxy()
        logger.info("当前已默认无视系统代理（VPN），如果需要dlc使用代理，请在小助手目录创建 .use_proxy 目录或文件")

    uploader = Uploader()

    # 进行实际的检查是否需要更新操作
    latest_version = get_latest_version(uploader)
    logger.info(color("bold_yellow") + f"当前版本为{args.version}，网盘最新版本为{latest_version}")

    if need_update(args.version, latest_version):
        update(args, uploader, latest_version)
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


def get_latest_version(uploader: Uploader) -> str:
    """
    尝试从github获取版本信息，形如 19.1.8
    """
    cfg = CommonConfig()
    return get_latest_version_from_github(cfg)


def update(args, uploader, latest_version: str):
    logger.info("需要更新，开始更新流程")

    logger.warning(
        color("bold_cyan") + "如果卡住了，可以 按ctrl+c 或者 点击右上角的X 强制跳过自动更新，本体仍可正常运行。"
    )

    logger.warning(color("bold_yellow") + "如果下载速度慢，可以按 任意键（比如ctrl+c） 来切换到下一个镜像")

    logger.info(color("bold_yellow") + "尝试增量更新")

    config = config_cloud()
    if config.dlc_enable_incremental_update:
        try:
            # 首先尝试使用增量更新文件
            patch_7z_filename = get_patch_7z_filename(args.version, latest_version)

            can_use_patch = is_file_in_folder("/", patch_7z_filename)
            if can_use_patch:
                logger.info(color("bold_yellow") + "当前版本可使用增量补丁，尝试进行增量更新")

                update_ok = incremental_update(args, uploader, latest_version)
                if update_ok:
                    logger.info("增量更新完毕")
                    report_dlc_usage("incremental update")
                    return
                else:
                    logger.warning("增量更新失败，尝试默认的全量更新方案")
        except BaseException as e:
            logger.exception("增量更新失败，尝试默认的全量更新方案", exc_info=e)
    else:
        logger.info(color("bold_yellow") + "当前已在云端禁用增量更新功能，将跳过")

    # 保底使用全量更新
    logger.info(color("bold_yellow") + "尝试全量更新")
    max_retry = 3
    for idx in range_from_one(max_retry):
        try:
            full_update(args, uploader, latest_version)
            break
        except DistutilsFileError as e:
            if is_mirror_compressed_file_incomplete(e):
                logger.error(
                    f"[{idx}/{max_retry}] 从本次随机到的镜像下载的文件不完整，将重新尝试随机挑选一个镜像来下载"
                )
                continue

            # 其他情况则继续抛出异常
            raise

    logger.info("全量更新完毕")
    return


def is_mirror_compressed_file_incomplete(e: DistutilsFileError) -> bool:
    """是否从镜像下载的文件不完整"""
    for msg in e.args:
        if "not a directory" in msg:
            return True

    return False


def full_update(args, uploader, latest_version: str) -> bool:
    remove_temp_dir("更新前，先移除临时目录，避免更新失败时这个目录会越来越大")

    def download_by_alist() -> str:
        logger.warning("尝试通过alist下载")
        filepath = download_from_alist(
            f"/DNF蚊子腿小助手_v{latest_version}_by风之凌殇.7z",
            tmp_dir,
            connect_timeout=5,
            extra_progress_callback=check_keyboard_interrupt_on_download,
        )
        report_dlc_usage("full_update_from_alist")

        return filepath

    def download_by_github() -> str:
        logger.warning("尝试通过github下载")
        filepath = download_latest_github_release(
            tmp_dir, connect_timeout=5, extra_progress_callback=check_keyboard_interrupt_on_download
        )
        report_dlc_usage("full_update_from_github")

        return filepath

    config = config_cloud()

    logger.info("开始下载最新版本的压缩包")
    logger.info(
        color("bold_cyan")
        + "如果一直在这不动，应该是在慢慢下载，就是速度比较慢而已。如果急着用，可以去群文件或群公告里的网盘自行下载最新版本"
    )
    filepath = ""
    download_functions = []
    if config.dlc_prefer_alist:
        logger.info("当前配置为优先alist")
        download_functions = [
            download_by_alist,
            download_by_github,
        ]
    else:
        logger.info("当前配置为优先github")
        download_functions = [
            download_by_github,
            download_by_alist,
        ]

    for download_function in download_functions:
        try:
            filepath = download_function()
            break
        except Exception:
            logger.info("下载失败了，尝试下一个下载方式")

    if filepath == "":
        raise Exception("所有下载方式都失败了")

    logger.info("下载完毕，开始解压缩")
    decompress(filepath, tmp_dir)

    # 计算解压后的目录的路径
    target_dir = extract_decompressed_directory_name(filepath)

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
    if not TEST_MODE:
        dir_util.copy_tree(target_dir, ".")
    else:
        logger.warning(f"当前为测试模式，将不会实际覆盖 {target_dir} 到当前目录")

    remove_temp_dir("更新完毕，移除临时目录")

    return True


def extract_decompressed_directory_name(filepath: str) -> str:
    # 手动打包的压缩包，去除.7z后缀后，就是对应的目录名称
    target_dir = filepath.replace(".7z", "")

    if not os.path.isdir(target_dir):
        # 兼容下从github下载的压缩包，压缩包名称固定为 xxx.7z，自动解压后 其名称为 实际的名称
        # 这里假设该目录中仅有这两个文件和目录，在更新器目前的设定下是符合的
        root_dir = os.path.dirname(filepath)
        for entry in os.listdir(root_dir):
            entry_full_path = os.path.join(root_dir, entry)

            if os.path.isdir(entry_full_path):
                target_dir = entry_full_path
                break

    return target_dir


def incremental_update(args, uploader, latest_version: str):
    remove_temp_dir("更新前，先移除临时目录，避免更新失败时这个目录会越来越大")

    logger.info("开始下载增量更新包")
    patch_7z_filename = get_patch_7z_filename(args.version, latest_version)
    filepath = download_from_alist(patch_7z_filename, tmp_dir)

    logger.info("下载完毕，开始解压缩")
    decompress(filepath, tmp_dir)

    kill_original_process(args.pid)

    target_patch = filepath.replace(".7z", "")
    logger.info(f"开始应用补丁 {target_patch}")
    if not TEST_MODE:
        # hpatchz.exe -C-diff -f . "%target_patch_file%" .
        ret_code = subprocess.call(
            [
                os.path.realpath("utils/hpatchz.exe"),
                "-C-diff",
                "-f",
                os.path.realpath("."),
                os.path.realpath(target_patch),
                os.path.realpath("."),
            ]
        )

        if ret_code != 0:
            logger.error(f"增量更新失败，错误码为{ret_code}，具体报错请看上面日志")
            return False
    else:
        logger.warning(f"当前为测试模式，将不会实际应用补丁 {target_patch}")

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
    report_dlc_usage("end_by_start_new_version")
    kill_process(os.getpid())


def main():
    try:
        report_dlc_usage("start")

        os.system("title 自动更新工具")
        auto_update()

        report_dlc_usage("end_without_update")
    except Exception as e:
        report_dlc_usage("exception")
        show_unexpected_exception_message(e)

        logger.info("完整截图反馈后点击任意键继续流程，谢谢合作~（当前版本的本体可以照常使用）")
        pause_and_exit(1)


def report_dlc_usage(ctx: str):
    increase_counter(ga_category="use_auto_updater", name=ctx)


def test():
    global TEST_MODE
    TEST_MODE = True

    logger.info(color("bold_yellow") + "开始测试更新器功能（不会实际覆盖文件）")

    args = parse_args()
    uploader = Uploader()

    args.version = "18.1.11"

    # 进行实际的检查是否需要更新操作
    latest_version = get_latest_version(uploader)
    logger.info(f"当前版本为{args.version}，网盘最新版本为{latest_version}")

    if need_update(args.version, latest_version):
        update(args, uploader, latest_version)
        start_new_version(args)
    else:
        logger.info("已经是最新版本，不需要更新")


if __name__ == "__main__":
    TEST = False

    if not TEST:
        main()
    else:
        test()

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
