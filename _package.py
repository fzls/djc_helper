# 构建发布压缩包
import os
import re
import shutil
import subprocess

from log import logger


def package(dir_src, dir_all_release, release_dir_name, release_7z_name):
    # 需要复制的文件与目录
    files_to_copy = []
    reg_wantted_file = r'.*\.(toml|md|txt|png|docx|url)$'
    for file in os.listdir('.'):
        if not re.search(reg_wantted_file, file, flags=re.IGNORECASE):
            continue
        files_to_copy.append(file)
    files_to_copy.extend([
        "config.toml.example",
        "DNF蚊子腿小助手.exe",
        "DNF蚊子腿小助手配置工具.bat",
        "bandizip_portable",
        "reference_data",
        "chromedriver_85.0.4183.87.exe",
        "public_key.der",
        "使用教程",
        "npp_portable",
    ])
    files_to_copy = sorted(files_to_copy)

    # 确保发布根目录存在
    if not os.path.isdir(dir_all_release):
        os.mkdir(dir_all_release)
    # 并清空当前的发布版本目录
    dir_current_release = os.path.realpath(os.path.join(dir_all_release, release_dir_name))
    shutil.rmtree(dir_current_release, ignore_errors=True)
    os.mkdir(dir_current_release)
    # 复制文件与目录过去
    logger.info("将以下内容从{}复制到{}".format(dir_src, dir_current_release))
    for filename in files_to_copy:
        source = os.path.join(dir_src, filename)
        destination = os.path.join(dir_current_release, filename)
        if os.path.isdir(filename):
            logger.info("拷贝目录 {}".format(filename))
            shutil.copytree(source, destination)
        else:
            logger.info("拷贝文件 {}".format(filename))
            shutil.copyfile(source, destination)

    # 压缩打包
    os.chdir(dir_all_release)
    logger.info("开始压缩打包")
    path_bz = os.path.join(dir_src, "bandizip_portable", "bz.exe")
    subprocess.call([path_bz, 'c', '-y', '-r', '-aoa', '-fmt:7z', '-l:9', release_7z_name, release_dir_name])


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('dir_src', help='src path')
    parser.add_argument('dir_all_release', help='release root path')
    parser.add_argument('release_dir_name', help='release current version directory name')
    parser.add_argument('release_7z_name', help='release current version 7z name')

    args = parser.parse_args()

    package(args.dir_src, args.dir_all_release, args.release_dir_name, args.release_7z_name)


if __name__ == '__main__':
    main()
