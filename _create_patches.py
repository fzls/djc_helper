from __future__ import annotations

# !/usr/bin/env python
# -------------------------------
# File      : _create_patch.py
# DateTime  : 2020/7/15 0015 2:22
# Author    : Chen Ji
# Email     : fzls.zju@gmail.com
# -------------------------------
import multiprocessing
import os
import shutil
import subprocess
from typing import List

from compress import compress_file_with_lzma, decompress_dir_with_bandizip
from download import download_latest_github_release
from log import color, logger
from update import get_version_list_from_gitee
from util import human_readable_size
from version import now_version


def create_patch(
    dir_src,
    dir_all_release,
    create_patch_for_latest_n_version,
    dir_github_action_artifact,
    get_final_patch_path_only=False,
) -> list[str]:
    latest_version = now_version

    old_cwd = os.getcwd()
    os.chdir(dir_all_release)
    if not get_final_patch_path_only:
        logger.info(f"工作目录已调整为{os.getcwd()}，最新版本为v{latest_version}")

    if not get_final_patch_path_only:
        logger.info(f"尝试从github查找在{latest_version}版本之前最近{create_patch_for_latest_n_version}个版本的信息")

    old_version_list: List[str] = []

    version_list = get_version_list_from_gitee()
    for version in version_list:
        if version == latest_version:
            continue

        old_version_list.append(version)
        if len(old_version_list) >= create_patch_for_latest_n_version:
            break

    # 确认最终文件名
    patch_oldest_version = old_version_list[-1]
    patch_newest_version = old_version_list[0]
    patches_dir = f"DNF蚊子腿小助手_增量更新文件_v{patch_oldest_version}_to_v{patch_newest_version}"
    temp_dir = "patches_temp"

    patch_filepath_list = list([
        os.path.join(patches_dir, f"DNF蚊子腿小助手_增量更新文件_v{version}_to_v{latest_version}.patch.7z") for version in old_version_list
    ])
    if get_final_patch_path_only:
        return patch_filepath_list

    logger.info(f"需要制作补丁包的版本为{old_version_list}")

    # 确保版本都在本地
    logger.info("确保以上版本均已下载并解压到本地~")
    for version in old_version_list:
        local_folder_path = os.path.join(dir_all_release, f"DNF蚊子腿小助手_v{version}_by风之凌殇")
        local_7z_path = local_folder_path + ".7z"

        if os.path.isdir(local_folder_path):
            # 本地已存在对应版本，跳过
            continue

        logger.info(f"本地发布目录不存在 {local_folder_path}")

        if not os.path.isfile(local_7z_path):
            local_7z_path = "djc_helper.7z"
            logger.info(f"本地不存在{version}版本，将从github下载 {local_7z_path}")
            download_latest_github_release(dir_all_release, version=version)

        logger.info(f"尝试从 {local_7z_path} 解压 {version}版本 到 {local_folder_path}")
        decompress_dir_with_bandizip(local_7z_path, dir_src)

    # --------------------------- 实际制作补丁包 ---------------------------
    logger.info(color("bold_yellow") + f"将为【{old_version_list}】版本制作补丁包")

    shutil.rmtree(patches_dir, ignore_errors=True)
    os.mkdir(patches_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.mkdir(temp_dir)

    def temp_path(dir_name):
        return os.path.realpath(os.path.join(temp_dir, dir_name))

    def preprocess_before_patch(temp_version_path):
        for filename in ["config.toml", "utils/auto_updater.exe"]:
            filepath = os.path.join(temp_version_path, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)

    # 为旧版本创建patch文件
    target_version_dir = f"DNF蚊子腿小助手_v{latest_version}_by风之凌殇"
    logger.info(f"目标版本目录为{target_version_dir}")
    shutil.copytree(target_version_dir, temp_path(target_version_dir))
    preprocess_before_patch(temp_path(target_version_dir))

    for idx, version in enumerate(old_version_list):
        patch_file = f"{patches_dir}/DNF蚊子腿小助手_增量更新文件_v{version}_to_v{latest_version}.patch"

        logger.info("-" * 80)
        logger.info(
            color("bold_yellow")
            + f"[{idx + 1}/{len(old_version_list)}] 创建从v{version}升级到v{latest_version}的补丁{patch_file}"
        )

        version_dir = f"DNF蚊子腿小助手_v{version}_by风之凌殇"

        shutil.copytree(version_dir, temp_path(version_dir))
        preprocess_before_patch(temp_path(version_dir))

        subprocess.call(
            [
                os.path.realpath(os.path.join(dir_src, "utils/hdiffz.exe")),
                f"-p-{multiprocessing.cpu_count()}",  # 设置系统最大cpu数
                os.path.realpath(os.path.join(temp_dir, version_dir)),
                os.path.realpath(os.path.join(temp_dir, target_version_dir)),
                patch_file,
            ]
        )

        filesize = os.path.getsize(patch_file)
        logger.info(f"创建补丁{patch_file}结束，最终大小为{human_readable_size(filesize)}")

        compressed_patch_file = patch_file + ".7z"
        compress_file_with_lzma(patch_file, compressed_patch_file)
        logger.info(f"压缩后大小为{human_readable_size(os.path.getsize(compressed_patch_file))}")

    # 移除临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)

    os.chdir(old_cwd)

    return patch_filepath_list


if __name__ == "__main__":
    dir_src = os.path.realpath(".")
    dir_all_release = os.path.realpath(os.path.join("releases"))
    dir_github_action_artifact = "_github_action_artifact"
    create_patch(dir_src, dir_all_release, 3, dir_github_action_artifact)
