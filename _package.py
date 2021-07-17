# 构建发布压缩包
import os
import re
import shutil

from compress import compress_dir_with_bandizip
from log import logger, color
from qq_login import QQLogin
from util import show_head_line
from version import now_version


def package(dir_src, dir_all_release, release_dir_name, release_7z_name, dir_github_action_artifact):
    old_cwd = os.getcwd()

    show_head_line(f"开始打包 {release_dir_name} 所需内容", color("bold_yellow"))

    # 确保发布根目录存在
    if not os.path.isdir(dir_all_release):
        os.mkdir(dir_all_release)
    # 并清空当前的发布版本目录
    dir_current_release = os.path.realpath(os.path.join(dir_all_release, release_dir_name))
    shutil.rmtree(dir_current_release, ignore_errors=True)
    os.mkdir(dir_current_release)

    logger.info(color("bold_yellow") + f"将部分内容从 {dir_src} 复制到 {dir_current_release} ")
    # 需要复制的文件与目录
    files_to_copy = []
    # 基于正则确定初始复制范围
    reg_wantted_file = r'.*\.(toml|md|txt|png|jpg|docx|url)$'
    for file in os.listdir('.'):
        if not re.search(reg_wantted_file, file, flags=re.IGNORECASE):
            continue
        files_to_copy.append(file)
    # 额外补充一些文件和目录
    files_to_copy.extend([
        "config.example.toml",
        "DNF蚊子腿小助手.exe",
        "DNF蚊子腿小助手配置工具.exe",
        "DNF蚊子腿小助手配置文件.bat",

        "使用教程",
        "付费指引",
        "相关信息",
        "utils",
    ])
    # 按顺序复制
    files_to_copy = sorted(files_to_copy)
    # 复制文件与目录过去
    for filename in files_to_copy:
        source = os.path.join(dir_src, filename)
        destination = os.path.join(dir_current_release, filename)
        if os.path.isdir(filename):
            logger.info(f"拷贝目录 {filename}")
            shutil.copytree(source, destination)
        else:
            logger.info(f"拷贝文件 {filename}")
            shutil.copyfile(source, destination)

    logger.info(color("bold_yellow") + "移动部分文件的位置和名称")
    files_to_move = [
        ("utils/auto_updater.exe", "utils/auto_updater_latest.exe"),
        ("CHANGELOG.MD", "相关信息/CHANGELOG.MD"),
        ("README.MD", "相关信息/README.MD"),
    ]
    for src_file, dst_file in files_to_move:
        src_file = os.path.join(dir_current_release, src_file)
        dst_file = os.path.join(dir_current_release, dst_file)

        logger.info(f"移动{src_file}到{dst_file}")
        shutil.move(src_file, dst_file)

    logger.info(color("bold_yellow") + "清除一些无需发布的内容")
    dir_to_filenames_need_remove = {
        ".": [
            "requirements.txt",
        ],
        "utils": [
            "logs", ".db", ".cached", ".first_run", ".log.filename",
            "buy_auto_updater_users.txt", "user_monthly_pay_info.txt", "notices.txt",
            f"chrome_portable_{QQLogin.chrome_major_version}.7z",
            f"chrome_portable_{QQLogin.chrome_major_version}",
        ],
    }
    for dir_path, filenames in dir_to_filenames_need_remove.items():
        for filename in filenames:
            filepath = os.path.join(dir_current_release, f"{dir_path}/{filename}")
            if not os.path.exists(filepath):
                continue

            if os.path.isdir(filepath):
                logger.info(f"移除目录 {filepath}")
                shutil.rmtree(filepath, ignore_errors=True)
            else:
                logger.info(f"移除文件 {filepath}")
                os.remove(filepath)

    # 压缩打包
    os.chdir(dir_all_release)
    logger.info(color("bold_yellow") + "开始压缩打包")
    compress_dir_with_bandizip(release_dir_name, release_7z_name, dir_src)

    # 额外备份一份最新的供github action 使用
    shutil.copyfile(release_7z_name, os.path.join(dir_github_action_artifact, 'djc_helper.7z'))

    os.chdir(old_cwd)


def main():
    dir_src = os.path.realpath('.')
    dir_all_release = os.path.realpath(os.path.join("releases"))
    release_dir_name = f"DNF蚊子腿小助手_v{now_version}_by风之凌殇"
    release_7z_name = f'{release_dir_name}.7z'
    dir_github_action_artifact = "_github_action_artifact"

    package(dir_src, dir_all_release, release_dir_name, release_7z_name, dir_github_action_artifact)


if __name__ == '__main__':
    main()
