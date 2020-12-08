# 构建发布压缩包
import shutil
import subprocess


def update_docs():
    shutil.copyfile("README.MD", "docs/README.md")
    shutil.copyfile("CHANGELOG.MD", "docs/CHANGELOG.md")
    subprocess.call(['git', 'add', '--', './docs'])
    subprocess.call(['git', 'commit', '-m', '"update github pages"', '--', './docs'])


def main():
    update_docs()

    import os
    os.system("PAUSE")


if __name__ == '__main__':
    main()
