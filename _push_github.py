# 构建发布压缩包
import subprocess

from version import now_version


def push_github(version):
    # note: 当手动触发了github action的时候，会创建一个很奇怪的tag，记得去删掉他refs/heads/master
    # 先尝试移除该tag，并同步到github，避免后面加标签失败
    subprocess.call(["git", "tag", "-d", version])
    subprocess.call(["git", "push", "origin", "master", f":refs/tags/{version}"])
    # 然后添加新tab，并同步到github
    subprocess.call(["git", "tag", "-a", version, "-m", f"release {version}"])
    subprocess.call(["git", "push", "origin", "master", "--tags"])


def main():
    version = "v" + now_version
    push_github(version)

    import os

    os.system("PAUSE")


if __name__ == "__main__":
    main()
