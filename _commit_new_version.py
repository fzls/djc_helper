# 构建发布压缩包
import shutil
import subprocess

from version import now_version


def commit_new_version():
    # 同步相关文件到docs目录，用于生成github pages
    shutil.copyfile("README.MD", "docs/README.md")
    shutil.copyfile("CHANGELOG.MD", "docs/CHANGELOG.md")

    # 提交版本信息和docs目录
    # ps：需要确保运行前本地git无其他待commit内容，否则会一起提交
    subprocess.call(['git', 'add', 'README.MD', 'CHANGELOG.MD', 'version.py'])
    subprocess.call(['git', 'add', '--', './docs'])
    subprocess.call(['git', 'commit', '-m', f'v{now_version} 版本说明'])


def main():
    commit_new_version()

    import os
    os.system("PAUSE")


if __name__ == '__main__':
    main()
