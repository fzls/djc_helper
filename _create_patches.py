#!/usr/bin/env python
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

from compress import compress_dir_with_bandizip, decompress_dir_with_bandizip
from log import color, logger
from update import version_less
from upload_lanzouyun import FileInFolder, Uploader
from util import human_readable_size, range_from_one
from version import now_version


class HistoryVersionFileInfo:
    def __init__(self, fileinfo: FileInFolder, version: str):
        self.fileinfo = fileinfo
        self.version = version

    def __lt__(self, other):
        return version_less(self.version, other.version)

    def __eq__(self, other):
        return self.version == other.version

    def __repr__(self):
        return self.version


def create_patch(
    dir_src,
    dir_all_release,
    create_patch_for_latest_n_version,
    dir_github_action_artifact,
    get_final_patch_path_only=False,
) -> str:
    latest_version = now_version

    old_cwd = os.getcwd()
    os.chdir(dir_all_release)
    if not get_final_patch_path_only:
        logger.info(f"工作目录已调整为{os.getcwd()}，最新版本为v{latest_version}")

    uploader = Uploader()

    if not get_final_patch_path_only:
        logger.info(f"尝试从网盘查找在{latest_version}版本之前最近{create_patch_for_latest_n_version}个版本的信息")
    old_version_infos = []  # type: List[HistoryVersionFileInfo]

    # 获取当前网盘的最新版本，若比当前发布版本低，也加入
    netdisk_latest_version_fileinfo = uploader.find_latest_version()
    netdisk_latest_version = uploader.parse_version_from_djc_helper_file_name(netdisk_latest_version_fileinfo.name)
    if version_less(netdisk_latest_version, latest_version):
        old_version_infos.append(HistoryVersionFileInfo(netdisk_latest_version_fileinfo, netdisk_latest_version))

    # 从历史版本网盘中查找旧版本
    for page in range_from_one(100):
        folder_info = uploader.get_folder_info_by_url(uploader.folder_history_files.url, get_this_page=page)
        for file in folder_info.files:
            filename = file.name  # type: str

            if not filename.startswith(uploader.history_version_prefix):
                # 跳过非历史版本的文件
                continue

            file_version = uploader.parse_version_from_djc_helper_file_name(filename)
            info = HistoryVersionFileInfo(file, file_version)

            if not version_less(file_version, latest_version):
                continue

            if info in old_version_infos:
                # 已经加入过（可能重复）
                continue

            old_version_infos.append(info)

        if len(old_version_infos) >= create_patch_for_latest_n_version + 2:
            # 已经找到超过前n+2个版本，因为网盘返回的必定是按上传顺序排列的，不过为了保险起见，多考虑一些
            break

    if create_patch_for_latest_n_version > len(old_version_infos):
        create_patch_for_latest_n_version = len(old_version_infos)

    old_version_infos = sorted(old_version_infos)[-create_patch_for_latest_n_version:]

    # 确认最终文件名
    patch_oldest_version = old_version_infos[0].version
    patch_newest_version = old_version_infos[-1].version
    patches_dir = f"DNF蚊子腿小助手_增量更新文件_v{patch_oldest_version}_to_v{patch_newest_version}"
    temp_dir = "patches_temp"

    patch_7z_file = f"{patches_dir}.7z"
    if get_final_patch_path_only:
        return patch_7z_file

    logger.info(f"需要制作补丁包的版本为{old_version_infos}")

    # 确保版本都在本地
    logger.info("确保以上版本均已下载并解压到本地~")
    for info in old_version_infos:
        local_folder_path = os.path.join(dir_all_release, f"DNF蚊子腿小助手_v{info.version}_by风之凌殇")
        local_7z_path = local_folder_path + ".7z"

        if os.path.isdir(local_folder_path):
            # 本地已存在对应版本，跳过
            continue

        logger.info(f"本地发布目录不存在 {local_folder_path}")
        if not os.path.isfile(local_7z_path):
            logger.info(f"本地不存在{info.fileinfo.name}的7z文件，将从网盘下载")
            uploader.download_file(info.fileinfo, dir_all_release)

        logger.info(f"尝试解压 {info.fileinfo.name} 到 {local_folder_path}")
        decompress_dir_with_bandizip(local_7z_path, dir_src)

    # --------------------------- 实际只做补丁包 ---------------------------
    logger.info(color("bold_yellow") + f"将为【{old_version_infos}】版本制作补丁包")

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
        logger.info(
            color("bold_yellow")
            + f"[{idx + 1}/{len(old_version_infos)}] 创建从v{version}升级到v{latest_version}的补丁{patch_file}"
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

    # 移除临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)

    # 压缩打包
    compress_dir_with_bandizip(patches_dir, patch_7z_file, dir_src)

    # 额外备份一份最新的供github action 使用
    shutil.copyfile(patch_7z_file, os.path.join(dir_github_action_artifact, "djc_helper_patches.7z"))

    os.chdir(old_cwd)

    return patch_7z_file


if __name__ == "__main__":
    dir_src = os.path.realpath(".")
    dir_all_release = os.path.realpath(os.path.join("releases"))
    dir_github_action_artifact = "_github_action_artifact"
    create_patch(dir_src, dir_all_release, 3, dir_github_action_artifact)
