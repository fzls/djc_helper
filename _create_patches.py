#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------
# File      : _create_patch.py
# DateTime  : 2020/7/15 0015 2:22
# Author    : Chen Ji
# Email     : fzls.zju@gmail.com
# -------------------------------
import multiprocessing
import os
import re
import shutil
import subprocess
from typing import List

from log import logger
from update import need_update
from util import human_readable_size
from version import now_version


class VersionInfo:
    def __init__(self, version: str, dirpath: str):
        self.version = version
        self.dirpath = dirpath

    def __lt__(self, other):
        return need_update(self.version, other.version)

    def __repr__(self):
        return str(self.__dict__)


def create_patch(dir_src, dir_all_release, create_patch_for_latest_n_version, dir_github_action_artifact, get_final_patch_path_only=False) -> str:
    latest_version = now_version

    old_cwd = os.getcwd()
    os.chdir(dir_all_release)
    if not get_final_patch_path_only: logger.info(f"工作目录已调整为{os.getcwd()}，最新版本为v{latest_version}")

    version_dir_regex = r"DNF蚊子腿小助手_v(.*)_by风之凌殇"

    # 获取最新的几个版本的信息
    old_version_infos = []  # type: List[VersionInfo]
    for dirpath in os.listdir("."):
        if not os.path.isdir(dirpath):
            continue

        # DNF蚊子腿小助手_v4.6.6_by风之凌殇.7z
        match = re.search(version_dir_regex, dirpath)
        if match is None:
            continue

        version = match.group(1)

        if not need_update(version, latest_version):
            continue

        old_version_infos.append(VersionInfo(version, dirpath))

    if create_patch_for_latest_n_version > len(old_version_infos):
        create_patch_for_latest_n_version = len(old_version_infos)

    old_version_infos = sorted(old_version_infos)[-create_patch_for_latest_n_version:]

    # 创建patch目录
    patch_oldest_version = old_version_infos[0].version
    patch_newest_version = old_version_infos[-1].version
    patches_dir = f"DNF蚊子腿小助手_增量更新文件_v{patch_oldest_version}_to_v{patch_newest_version}"
    temp_dir = "patches_temp"

    patch_7z_file = f"{patches_dir}.7z"
    if get_final_patch_path_only:
        return patch_7z_file

    # --------------------------- 实际只做补丁包 ---------------------------
    logger.info(f"将为【{old_version_infos}】版本制作补丁包")

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

    for idx, version_info in enumerate(old_version_infos):
        version = version_info.version
        patch_file = f"{patches_dir}/{version}.patch"

        logger.info("-" * 80)
        logger.info(f"[{idx + 1}/{len(old_version_infos)}] 创建从v{version}升级到v{latest_version}的补丁{patch_file}")

        version_dir = f"DNF蚊子腿小助手_v{version}_by风之凌殇"

        shutil.copytree(version_dir, temp_path(version_dir))
        preprocess_before_patch(temp_path(version_dir))

        subprocess.call([
            os.path.realpath(os.path.join(dir_src, "utils/hdiffz.exe")),
            f"-p-{multiprocessing.cpu_count()}",  # 设置系统最大cpu数
            os.path.realpath(os.path.join(temp_dir, version_dir)),
            os.path.realpath(os.path.join(temp_dir, target_version_dir)),
            patch_file,
        ])

        filesize = os.path.getsize(patch_file)
        logger.info(f"创建补丁{patch_file}结束，最终大小为{human_readable_size(filesize)}")

    # 移除临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)

    # 压缩打包
    path_bz = os.path.join(dir_src, "bandizip_portable", "bz.exe")
    subprocess.call([path_bz, 'c', '-y', '-r', '-aoa', '-fmt:7z', '-l:9', patch_7z_file, patches_dir])

    # 额外备份一份最新的供github action 使用
    shutil.copyfile(patch_7z_file, os.path.join(dir_github_action_artifact, 'djc_helper_patches.7z'))

    os.chdir(old_cwd)

    return patch_7z_file


if __name__ == '__main__':
    dir_src = os.path.realpath('.')
    dir_all_release = os.path.realpath(os.path.join("releases"))
    dir_github_action_artifact = "_github_action_artifact"
    create_patch(dir_src, dir_all_release, 3, dir_github_action_artifact)
