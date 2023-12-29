# 格式：大版本号.小版本号.补丁版本号
# 含义
#   大版本号：大重构、或者引入很重要的改动时
#   小版本号：新的活动周期，比如国庆节版本、春节版本
#   补丁版本号：修复bug，或者同一个活动周期内出的新活动
now_version = "21.1.6"
ver_time = "2023.12.29"
author = "风之凌殇"


# re: 可以运行这个方法来获取changelog中所需的版本信息
def print_current_version_for_changelog():
    print(f"# v{now_version} {ver_time}")


# UNDONE: 可以使用 changelog_number.py 脚本来自动格式化更新日志中的序号

if __name__ == "__main__":
    print_current_version_for_changelog()
