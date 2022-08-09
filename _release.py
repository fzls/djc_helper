import os
import re
import webbrowser
from datetime import datetime

from _commit_new_version import commit_new_version
from _push_github import push_github
from log import color, logger
from util import change_console_window_mode_async, pause_and_exit, show_head_line
from version import now_version


def release():
    # ---------------准备工作
    prompt = f"如需直接使用默认版本号：{now_version} 请直接按回车\n或手动输入版本号后按回车："
    version = input(prompt) or now_version

    version_reg = r"\d+\.\d+\.\d+"

    if re.match(version_reg, version) is None:
        logger.info(f"版本号格式有误，正确的格式类似：1.0.0 ，而不是 {version}")
        pause_and_exit(-1)

    # 最大化窗口
    change_console_window_mode_async(disable_min_console=True)

    version = "v" + version

    run_start_time = datetime.now()
    show_head_line(f"开始发布版本 {version}", color("bold_yellow"))

    set_title_cmd = f"title 发布 {version}"
    os.system(set_title_cmd)

    # 先声明一些需要用到的目录的地址
    dir_src = os.path.realpath(".")
    # dir_all_release = os.path.realpath(os.path.join("releases"))
    # release_dir_name = f"DNF蚊子腿小助手_{version}_by风之凌殇"
    # release_7z_name = f"{release_dir_name}.7z"
    # dir_github_action_artifact = "_github_action_artifact"

    show_head_line("实际构建打包流程将在github action中自动执行，本地仅在git打tag", color("bold_yellow"))

    # ---------------标记新版本
    show_head_line("提交版本和版本变更说明，并同步到docs目录，用于生成github pages", color("bold_yellow"))
    os.chdir(dir_src)
    commit_new_version()

    show_head_line("软件分发改用github release，不再尝试上传蓝奏云", color("bold_yellow"))

    # ---------------推送版本到github
    # 打包完成后git添加标签
    os.chdir(dir_src)
    show_head_line("开始推送到github", color("bold_yellow"))
    push_github(version)

    # ---------------查看github action
    show_head_line("请在稍后打开的github action中查看打包结果", color("bold_yellow"))
    webbrowser.open("https://github.com/fzls/djc_helper/actions/workflows/package.yml")

    # ---------------结束
    logger.info("+" * 40)
    logger.info(color("bold_yellow") + f"{version} 发布完成，共用时{datetime.now() - run_start_time}，请等待github action的构建打包流程完成")
    logger.info("+" * 40)

    os.system("PAUSE")


if __name__ == "__main__":
    release()
