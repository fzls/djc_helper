import os
import shutil

from log import color
from util import show_head_line


def clear_github_artifact(dir_all_release, dir_github_action_artifact):
    old_cwd = os.getcwd()

    show_head_line(f"清空旧版本github artifact目录", color("bold_yellow"))

    if not os.path.isdir(dir_all_release):
        os.mkdir(dir_all_release)

    os.chdir(dir_all_release)

    shutil.rmtree(dir_github_action_artifact, ignore_errors=True)
    os.mkdir(dir_github_action_artifact)

    os.chdir(old_cwd)


if __name__ == '__main__':
    dir_all_release = os.path.realpath(os.path.join("releases"))
    clear_github_artifact(dir_all_release, "_github_action_artifact")
