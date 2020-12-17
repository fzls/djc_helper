# 编译脚本
import os
import shutil
import subprocess

from log import logger


def build():
    venv_path = ".venv"
    src_name = "main.py"
    exe_name = 'DNF蚊子腿小助手.exe'
    icon = 'DNF蚊子腿小助手.ico'

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
    subprocess.call([
        py_path,
        "-m",
        "pip",
        "install",
        "-i",
        "https://pypi.doubanio.com/simple",
        "--upgrade",
        "pip",
        "setuptools",
        "wheel",
    ])

    logger.info("尝试安装依赖库和pyinstaller")
    subprocess.call([
        pip_path,
        "install",
        "-i",
        "https://pypi.doubanio.com/simple",
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

    logger.info("编译结束，进行善后操作")
    # 复制二进制
    shutil.copyfile(os.path.join("dist", exe_name), exe_name)
    # 删除临时文件
    for directory in ["build", "dist", "__pycache__"]:
        shutil.rmtree(directory, ignore_errors=True)
    for file in ["{}.spec".format(exe_name)]:
        os.remove(file)

    logger.info("done")


if __name__ == '__main__':
    build()
