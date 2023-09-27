# 编译脚本
import argparse
import os
import shutil
import subprocess

from _init_venv_and_requirements import init_venv_and_requirements
from log import color, logger
from util import (
    async_message_box,
    clear_file,
    human_readable_size,
    make_sure_dir_exists,
    remove_file_or_directory,
    show_head_line,
)


def build(disable_douban=False, enable_proxy=False, use_upx=True):
    # 初始化相关路径变量
    venv_path = ".venv"
    pyinstaller_path = os.path.join(venv_path, "Scripts", "pyinstaller")

    # 确保test.py内容为空，避免出现异常状况
    if os.path.isfile("test.py") and os.stat("test.py").st_size != 0:
        with open("test.py", encoding="utf-8") as f:
            async_message_box(f"test.py内容不为空，未避免构建过程中执行产生副作用，将清空其内容，其内容如下:\n\n{f.read()}", "警告：test.py的测试代码未移除")

        clear_file("test.py")

    # 初始化venv和依赖
    init_venv_and_requirements(".venv", "requirements.txt", disable_douban, enable_proxy, True)

    show_head_line("将使用.venv环境进行编译", color("bold_yellow"))

    temp_remove_file_dir = os.path.join(".cached", "build_temp_remove_files")
    site_packages_path = os.path.join(venv_path, "Lib", "site-packages")
    dep_files_to_remove_during_build = {
        "PyQt5/Qt5": [
            "Translations",
        ],
        "PyQt5/Qt5/bin": [
            "opengl32sw.dll",
            "libEGL.dll",
            "libGLESV2.dll",
            "Qt5Svg.dll",
            "Qt5Network.dll",
            "Qt5Qml.dll",
            "Qt5QmlModels.dll",
            "Qt5Quick.dll",
            "Qt5WebSockets.dll",
            "d3dcompiler_47.dll",
        ],
        "PyQt5/Qt5/plugins": [
            "iconengines/qsvgicon.dll",
            "imageformats/qsvg.dll",
            "imageformats/qwebp.dll",
            "platforms/qwebgl.dll",
        ],
    }
    logger.info(color("bold_green") + f"开始编译前先尝试移动这些确定用不到的库文件到临时目录 {temp_remove_file_dir}，从而尽可能减少最终编译的大小")
    for parent_directory, file_or_directory_name_list in dep_files_to_remove_during_build.items():
        for file_or_directory_name in file_or_directory_name_list:
            path = os.path.join(site_packages_path, parent_directory, file_or_directory_name)
            backup_path = os.path.join(temp_remove_file_dir, parent_directory, file_or_directory_name)

            if not os.path.exists(path):
                logger.warning(f"\t{path} 不存在，将跳过")
                continue
            if os.path.exists(backup_path):
                remove_file_or_directory(backup_path)

            # 将文件移动到备份目录
            logger.info(f"\t开始移动 {path}")
            make_sure_dir_exists(os.path.dirname(backup_path))
            shutil.move(path, backup_path)

    # 实际编译流程
    build_configs: list[tuple[str, str, str, str, list[str], list[str]]] = [
        ("main.py", "DNF蚊子腿小助手.exe", "utils/icons/DNF蚊子腿小助手.ico", ".", [], []),
        ("config_ui.py", "DNF蚊子腿小助手配置工具.exe", "utils/icons/config_ui.ico", ".", [], ["--noconsole"]),
        ("auto_updater.py", "auto_updater.exe", "", "utils", ["PyQt5"], []),
        # ("my_home_special_version.py", "DNF蚊子腿小助手_我的小屋特别版.exe", "utils/icons/my_home.ico", ".", ["PyQt5"], []),
    ]

    # ark_icon = "utils/icons/ark_lottery_special_version.ico"
    # build_configs.append(
    #     ("ark_lottery_special_version.py", "DNF蚊子腿小助手_集卡特别版.exe", ark_icon, ".", ["PyQt5"], []),
    # )

    for idx, config in enumerate(build_configs):
        prefix = f"{idx + 1}/{len(build_configs)}"

        src_path, exe_name, icon_path, target_dir, exclude_modules, extra_args = config
        logger.info(color("bold_yellow") + f"{prefix} 开始编译 {exe_name}")

        cmd_build = [
            pyinstaller_path,
            "--name",
            exe_name,
            "-F",
            src_path,
        ]
        if icon_path != "":
            cmd_build.extend(["--icon", icon_path])
        for module in exclude_modules:
            cmd_build.extend(["--exclude-module", module])
        if use_upx:
            cmd_build.extend(["--upx-dir", "utils"])
        cmd_build.extend(extra_args)

        logger.info(f"{prefix} 开始编译 {exe_name}，命令为：{' '.join(cmd_build)}")
        subprocess.call(cmd_build)

        logger.info("编译结束，进行善后操作")

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
        logger.info(color("bold_green") + f"{prefix} 编译{exe_name}结束，最终大小为{human_readable_size(filesize)}")

    logger.info(color("bold_green") + f"编译完毕将库文件移动回来 - {site_packages_path}")
    for parent_directory, file_or_directory_name_list in dep_files_to_remove_during_build.items():
        for file_or_directory_name in file_or_directory_name_list:
            path = os.path.join(site_packages_path, parent_directory, file_or_directory_name)
            backup_path = os.path.join(temp_remove_file_dir, parent_directory, file_or_directory_name)

            if not os.path.exists(backup_path):
                logger.warning(f"\t备份文件 {backup_path} 不存在，将跳过")
                continue

            # 将文件移动到备份目录
            logger.info(f"开始还原备份文件/目录 {backup_path}")
            make_sure_dir_exists(os.path.dirname(path))
            shutil.move(backup_path, path)

    logger.info("done")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disable_douban", action="store_true")
    parser.add_argument("--enable_proxy", action="store_true")
    parser.add_argument("--disable_upx", action="store_true")
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_args()
    build(args.disable_douban, args.enable_proxy, not args.disable_upx)
