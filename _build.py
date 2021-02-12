# 编译脚本
import argparse
import os
import shutil
import subprocess

from log import logger
from util import human_readable_size


def build(disable_douban=False):
    venv_path = ".venv"

    # 初始化相关路径变量
    pyscript_path = os.path.join(venv_path, "Scripts")
    py_path = os.path.join(pyscript_path, "python")
    pip_path = os.path.join(pyscript_path, "pip")
    pyinstaller_path = os.path.join(pyscript_path, "pyinstaller")

    logger.info("尝试初始化venv环境")
    subprocess.call([
        "python",
        "-m",
        "venv",
        venv_path,
    ])

    logger.info("将使用.venv环境进行编译")

    logger.info("尝试更新pip setuptools wheel")
    douban_op = ["-i", "https://pypi.doubanio.com/simple"]
    if disable_douban:
        douban_op = []
    subprocess.call([
        py_path,
        "-m",
        "pip",
        "install",
        *douban_op,
        "--upgrade",
        "pip",
        "setuptools",
        "wheel",
    ])

    logger.info("尝试安装依赖库和pyinstaller")
    subprocess.call([
        pip_path,
        "install",
        *douban_op,
        "-r",
        "requirements.txt",
        "wheel",
        "pyinstaller",
    ])

    logger.info("安装pywin32_postinstall")
    subprocess.call([
        py_path,
        os.path.join(pyscript_path, "pywin32_postinstall.py"),
        "-install",
    ])

    build_configs = [
        ("main.py", "DNF蚊子腿小助手.exe", "icons/DNF蚊子腿小助手.ico", ".", ["PyQt5"], []),
        ("auto_updater.py", "auto_updater.exe", "", "utils", ["PyQt5"], []),
        ("ark_lottery_special_version.py", "DNF蚊子腿小助手_集卡特别版.exe", "icons/ark_lottery_special_version.ico", ".", ["PyQt5"], []),
        ("config_ui.py", "DNF蚊子腿小助手配置工具.exe", "icons/config_ui.ico", ".", [], ["--noconsole"]),
    ]

    for idx, config in enumerate(build_configs):
        prefix = f"{idx + 1}/{len(build_configs)}"

        src_path, exe_name, icon_path, target_dir, exclude_modules, extra_args = config
        logger.info(f"{prefix} 开始编译 {exe_name}")

        cmd_build = [
            pyinstaller_path,
            '--name', exe_name,
            '-F',
            src_path,
        ]
        if icon_path != "":
            cmd_build.extend(['--icon', icon_path])
        for module in exclude_modules:
            cmd_build.extend(['--exclude-module', module])
        cmd_build.extend(extra_args)

        subprocess.call(cmd_build)

        logger.info(f"编译结束，进行善后操作")

        # 复制二进制
        logger.info(f"复制{exe_name}到目标目录{target_dir}")
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)
        target_path = os.path.join(target_dir, exe_name)
        shutil.copyfile(os.path.join("dist", exe_name), target_path)

        # 删除临时文件
        logger.info("删除临时文件")
        for directory in ["build", "dist", "__pycache__"]:
            shutil.rmtree(directory, ignore_errors=True)
        os.remove(f"{exe_name}.spec")

        filesize = os.path.getsize(target_path)
        logger.info(f"{prefix} 编译{exe_name}结束，最终大小为{human_readable_size(filesize)}")

    logger.info("done")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disable_douban", action='store_true')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = parse_args()
    build(args.disable_douban)
