# 编译脚本
import argparse
import os
import shutil
import subprocess

from log import logger


def build(disable_douban=False):
    venv_path = ".venv"
    src_name = "main.py"
    exe_name = 'DNF蚊子腿小助手.exe'
    icon = 'DNF蚊子腿小助手.ico'
    updater_src_name = "auto_updater.py"
    updater_exe_name = "auto_updater.exe"
    util_dir = "utils"
    updater_target_path = os.path.join(util_dir, updater_exe_name)

    if not os.path.isdir(util_dir):
        os.mkdir(util_dir)

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

    logger.info("开始编译 {}".format(exe_name))

    cmd_build = [
        pyinstaller_path,
        '--icon', icon,
        '--name', exe_name,
        '-F',
        src_name,
    ]

    subprocess.call(cmd_build)

    logger.info("开始编译 {}".format(updater_exe_name))

    cmd_build = [
        pyinstaller_path,
        '--name', updater_exe_name,
        '-F',
        updater_src_name,
    ]

    subprocess.call(cmd_build)

    logger.info("编译结束，进行善后操作")
    # 复制二进制
    shutil.copyfile(os.path.join("dist", exe_name), exe_name)
    shutil.copyfile(os.path.join("dist", updater_exe_name), updater_target_path)
    # 删除临时文件
    for directory in ["build", "dist", "__pycache__"]:
        shutil.rmtree(directory, ignore_errors=True)
    for file in ["{}.spec".format(name) for name in [exe_name, updater_exe_name]]:
        os.remove(file)

    logger.info("done")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disable_douban", action='store_true')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = parse_args()
    build(args.disable_douban)
