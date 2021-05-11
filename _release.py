import json
import os
import re
from datetime import datetime
from sys import exit

from _build import build
from _clear_github_artifact import clear_github_artifact
from _commit_new_version import commit_new_version
from _create_patches import create_patch
from _package import package
from _push_github import push_github
from log import logger
from upload_lanzouyun import Uploader
from util import maximize_console, make_sure_dir_exists
from version import now_version

# ---------------准备工作
prompt = f"如需直接使用默认版本号：{now_version} 请直接按回车\n或手动输入版本号后按回车："
version = input(prompt) or now_version

version_reg = r"\d+\.\d+\.\d+"

if re.match(version_reg, version) is None:
    logger.info(f"版本号格式有误，正确的格式类似：1.0.0 ，而不是 {version}")
    exit(-1)

# 最大化窗口
maximize_console()

version = 'v' + version

run_start_time = datetime.now()
logger.info(f"开始发布版本 {version}")

# 先声明一些需要用到的目录的地址
dir_src = os.path.realpath('.')
dir_all_release = os.path.realpath(os.path.join("releases"))
release_dir_name = f"DNF蚊子腿小助手_{version}_by风之凌殇"
release_7z_name = f'{release_dir_name}.7z'
dir_github_action_artifact = "_github_action_artifact"

# ---------------构建
# 调用构建脚本
os.chdir(dir_src)
build()

# ---------------清除一些历史数据
make_sure_dir_exists(dir_all_release)
os.chdir(dir_all_release)
clear_github_artifact(dir_all_release, dir_github_action_artifact)

# ---------------打包
os.chdir(dir_src)
package(dir_src, dir_all_release, release_dir_name, release_7z_name, dir_github_action_artifact)

# ---------------构建增量补丁
# 构建增量包
os.chdir(dir_all_release)
create_patch_for_latest_n_version = 3
logger.info(f"开始构建增量包，最多包含过去{create_patch_for_latest_n_version}个版本到最新版本的补丁")
patch_file_name = create_patch(dir_src, dir_all_release, create_patch_for_latest_n_version, dir_github_action_artifact)

# ---------------标记新版本
logger.info("提交版本和版本变更说明，并同步到docs目录，用于生成github pages")
os.chdir(dir_src)
commit_new_version()

# ---------------上传到蓝奏云
logger.info("开始上传到蓝奏云")
os.chdir(dir_src)
with open("upload_cookie.json") as fp:
    cookie = json.load(fp)
os.chdir(dir_all_release)
uploader = Uploader()
uploader.login(cookie)
if uploader.login_ok:
    logger.info("蓝奏云登录成功，开始上传压缩包")
    uploader.upload_to_lanzouyun(patch_file_name, uploader.folder_djc_helper, history_file_prefix=uploader.history_patches_prefix)
    uploader.upload_to_lanzouyun(release_7z_name, uploader.folder_djc_helper, history_file_prefix=uploader.history_version_prefix)
    uploader.upload_to_lanzouyun(release_7z_name, uploader.folder_dnf_calc, history_file_prefix=uploader.history_version_prefix)
    uploader.upload_to_lanzouyun(os.path.realpath(os.path.join(dir_src, "utils/buy_auto_updater_users.txt")), uploader.folder_online_files, also_upload_compressed_version=True)
    uploader.upload_to_lanzouyun(os.path.realpath(os.path.join(dir_src, "utils/user_monthly_pay_info.txt")), uploader.folder_online_files, also_upload_compressed_version=True)
else:
    logger.error("蓝奏云登录失败")

# ---------------推送版本到github
# 打包完成后git添加标签
os.chdir(dir_src)
logger.info("开始推送到github")
push_github(version)

# ---------------结束
logger.info('+' * 40)
logger.info(f"发布完成，共用时{datetime.now() - run_start_time}，请检查上传至蓝奏云流程是否OK")
logger.info('+' * 40)

os.system("PAUSE")
