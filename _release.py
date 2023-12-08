import os
import re
import shutil
import time
import webbrowser
from datetime import datetime

from _build import build
from _clear_github_artifact import clear_github_artifact
from _commit_new_version import commit_new_version
from _create_patches import create_patch
from _package import package
from _push_github import push_github
from alist import remove_file_startswith_prefix, upload
from log import color, logger
from util import (
    change_console_window_mode_async,
    count_down,
    make_sure_dir_exists,
    pause_and_exit,
    range_from_one,
    show_head_line,
)
from version import now_version


def release():
    # ---------------准备工作
    prompt = f"如需直接使用默认版本号：{now_version} 请直接按回车\n或手动输入版本号后按回车："
    version = input(prompt) or now_version

    version_reg = r"\d+\.\d+\.\d+"

    if re.match(version_reg, version) is None:
        logger.info(f"版本号格式有误，正确的格式类似：1.0.0 ，而不是 {version}")
        pause_and_exit(-1)

    # 最大化窗口
    change_console_window_mode_async(disable_min_console=True)

    version = "v" + version

    run_start_time = datetime.now()
    show_head_line(f"开始发布版本 {version}", color("bold_yellow"))

    set_title_cmd = f"title 发布 {version}"
    os.system(set_title_cmd)

    # 先声明一些需要用到的目录的地址
    dir_src = os.path.realpath(".")
    dir_all_release = os.path.realpath(os.path.join("releases"))
    release_dir_name = f"DNF蚊子腿小助手_{version}_by风之凌殇"
    release_7z_name = f"{release_dir_name}.7z"
    dir_github_action_artifact = "_github_action_artifact"
    dir_upload_files = "_upload_files"

    # ---------------构建
    # 调用构建脚本
    os.chdir(dir_src)
    build()

    # ---------------清除一些历史数据
    make_sure_dir_exists(dir_all_release)
    os.chdir(dir_all_release)
    clear_github_artifact(dir_all_release, dir_github_action_artifact)

    # ---------------打包
    os.chdir(dir_src)
    package(dir_src, dir_all_release, release_dir_name, release_7z_name, dir_github_action_artifact)

    # ---------------构建增量补丁
    create_patch_for_latest_n_version = 3

    # ---------------构建增量包
    os.chdir(dir_all_release)
    show_head_line(f"开始构建增量包，最多包含过去{create_patch_for_latest_n_version}个版本到最新版本的补丁", color("bold_yellow"))
    create_patch(dir_src, dir_all_release, create_patch_for_latest_n_version, dir_github_action_artifact)

    # ---------------获取补丁地址（分开方便调试）
    os.chdir(dir_all_release)
    patch_file_name_list = create_patch(
        dir_src,
        dir_all_release,
        create_patch_for_latest_n_version,
        dir_github_action_artifact,
        get_final_patch_path_only=True,
    )

    # ---------------标记新版本
    show_head_line("提交版本和版本变更说明，并同步到docs目录，用于生成github pages", color("bold_yellow"))
    os.chdir(dir_src)
    commit_new_version()

    # ---------------上传到网盘
    show_head_line("开始上传到alist", color("bold_yellow"))
    os.chdir(dir_all_release)

    def path_in_src(filepath_relative_to_src: str) -> str:
        return os.path.realpath(os.path.join(dir_src, filepath_relative_to_src))

    realpath = os.path.realpath

    # 先清理掉旧版本的增量更新文件
    remove_file_startswith_prefix("/", "DNF蚊子腿小助手_增量更新文件_")

    shutil.rmtree(dir_upload_files, ignore_errors=True)
    os.mkdir(dir_upload_files)

    upload_list = [
        (realpath(release_7z_name), "DNF蚊子腿小助手_v"),
        (path_in_src("utils/auto_updater.exe"), ""),
        (path_in_src("使用教程/使用文档.docx"), ""),
        (path_in_src("使用教程/视频教程.txt"), ""),
        (path_in_src("付费指引/付费指引.docx"), ""),
        *[(realpath(patch_file_name), "") for patch_file_name in patch_file_name_list],
    ]

    logger.info(color("bold_green") + "具体上传列表如下：")
    for local_filepath, _history_file_prefix in upload_list:
        logger.info(f"\t\t{local_filepath}")

    # 逆序遍历，确保同一个网盘目录中，列在前面的最后才上传，从而在网盘显示时显示在最前方
    for local_filepath, history_file_prefix in reversed(upload_list):
        # 先复制一份要上传的文件到本地临时目录，方便出错时可以手动上传
        backup_filepath = os.path.join(dir_upload_files, os.path.basename(local_filepath))
        shutil.copy2(local_filepath, backup_filepath)
        logger.warning(f"复制到{backup_filepath}，方便出错时手动上传")

        total_try_count = 1
        for try_index in range_from_one(total_try_count):
            try:
                # 然后再实际上传
                upload(local_filepath, old_version_name_prefix=history_file_prefix)
            except Exception as e:
                local_filename = os.path.basename(local_filepath)
                logger.warning(
                    color("bold_yellow") + f"第{try_index}/{total_try_count}次尝试上传 {local_filename} 失败，等待一会后重试",
                    exc_info=e,
                )
                if try_index < total_try_count:
                    count_down("上传到网盘", 5 * try_index)
                    continue

            break

    # ---------------推送版本到github
    # 打包完成后git添加标签
    os.chdir(dir_src)
    show_head_line("开始推送到github", color("bold_yellow"))
    push_github(version)

    # ---------------查看github action
    show_head_line("为了保底，在github action同时打包发布一份，请在稍后打开的github action中查看打包结果", color("bold_yellow"))
    logger.info("等待两秒，确保action已开始处理，不必再手动刷新页面")
    time.sleep(2)
    webbrowser.open("https://github.com/fzls/djc_helper/actions/workflows/package.yml")

    # ---------------查看本地上传目录
    show_head_line("打开本地的上传目录，方便手动上传新版本到QQ群文件", color("bold_yellow"))
    webbrowser.open(os.path.join(dir_all_release, dir_upload_files))

    # ---------------结束
    logger.info("+" * 40)
    logger.info(color("bold_yellow") + f"{version} 发布完成，共用时{datetime.now() - run_start_time}，请等待github action的构建打包流程完成")
    logger.info("+" * 40)

    os.system("PAUSE")


if __name__ == "__main__":
    release()
