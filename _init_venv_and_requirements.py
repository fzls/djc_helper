# 初始化依赖脚本
import argparse
import os
import shutil
import subprocess

from log import color, logger
from util import bypass_proxy, show_head_line


def init_venv_and_requirements(
    venv_path=".venv", requirements_path="requirements.txt", disable_douban=False, enable_proxy=False, reset_venv=False
):
    if not enable_proxy:
        logger.info("当前已无视系统代理")
        bypass_proxy()

    # 初始化相关路径变量
    pyscript_path = os.path.join(venv_path, "Scripts")
    py_path = os.path.join(pyscript_path, "python")
    pip_path = os.path.join(pyscript_path, "pip")

    if reset_venv:
        show_head_line("先清空原来的环境，确保每次从头开始准备环境，避免莫名其妙的问题", color("bold_yellow"))
        shutil.rmtree(venv_path, ignore_errors=True)

    show_head_line("尝试初始化venv环境", color("bold_yellow"))

    subprocess.call(
        [
            "python",
            "-m",
            "venv",
            venv_path,
        ]
    )

    logger.info("尝试更新pip setuptools wheel")
    douban_op = ["-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
    if disable_douban:
        douban_op = []
    subprocess.call(
        [
            py_path,
            "-m",
            "pip",
            "install",
            *douban_op,
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ]
    )

    logger.info("尝试安装依赖库和pyinstaller")
    subprocess.call(
        [
            pip_path,
            "install",
            *douban_op,
            "-r",
            requirements_path,
            "--upgrade",
            "wheel",
            "pyinstaller",
        ]
    )

    logger.info("安装pywin32_postinstall")
    subprocess.call(
        [
            py_path,
            os.path.join(pyscript_path, "pywin32_postinstall.py"),
            "-install",
        ]
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disable_douban", action="store_true")
    parser.add_argument("--enable_proxy", action="store_true")
    parser.add_argument("--venv_path", default=".venv")
    parser.add_argument("--requirements_path", default="requirements.txt")
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--reset_venv", action="store_true")
    args = parser.parse_args()

    if args.dev:
        args.venv_path = ".venv_dev"
        args.requirements_path = "requirements_dev.txt"

    return args


if __name__ == "__main__":
    args = parse_args()
    init_venv_and_requirements(
        args.venv_path, args.requirements_path, args.disable_douban, args.enable_proxy, args.reset_venv
    )
