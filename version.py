# 格式：大版本号.小版本号.补丁版本号
# 含义
#   大版本号：大重构、或者引入很重要的改动时
#   小版本号：新的活动周期，比如国庆节版本、春节版本
#   补丁版本号：修复bug，或者同一个活动周期内出的新活动
now_version = "22.11.1"
ver_time = "2026.1.10"
author = "风之凌殇"


# re: 可以运行这个方法来获取changelog中所需的版本信息
def print_current_version_for_changelog():
    print(f"# v{now_version} {ver_time}")


if __name__ == "__main__":
    print_current_version_for_changelog()
