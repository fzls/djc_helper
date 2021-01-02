import json
import os
import re
import shutil
from datetime import datetime
from sys import exit

from _build import build
from _commit_new_version import commit_new_version
from _create_patches import create_patch
from _package import package
from _push_github import push_github
from log import logger
from upload_lanzouyun import Uploader
from util import maximize_console
from version import now_version
from _clear_github_artifact import clear_github_artifact

# 最大化窗口
maximize_console()

# ---------------准备工作
prompt = "如需直接使用默认版本号：{} 请直接按回车\n或手动输入版本号后按回车：".format(now_version)
version = input(prompt) or now_version

version_reg = r"\d+\.\d+\.\d+"

if re.match(version_reg, version) is None:
    logger.info("版本号格式有误，正确的格式类似：1.0.0 ，而不是 {}".format(version))
    exit(-1)

version = 'v' + version

run_start_time = datetime.now()
logger.info("开始发布版本 {}".format(version))

# 先声明一些需要用到的目录的地址
dir_src = os.path.realpath('.')
dir_all_release = os.path.realpath(os.path.join("releases"))
release_dir_name = "DNF蚊子腿小助手_{version}_by风之凌殇".format(version=version)
release_7z_name = '{}.7z'.format(release_dir_name)
dir_github_action_artifact = "_github_action_artifact"

# ---------------构建
# 调用构建脚本
os.chdir(dir_src)
build()

# ---------------清除一些历史数据
os.chdir(dir_all_release)
clear_github_artifact(dir_all_release, dir_github_action_artifact)

# ---------------打包
os.chdir(dir_src)
package(dir_src, dir_all_release, release_dir_name, release_7z_name, dir_github_action_artifact)

# ---------------构建增量补丁
# 构建增量包
os.chdir(dir_all_release)
create_patch_for_latest_n_version = 3
logger.info("开始构建增量包，最多包含过去{}个版本到最新版本的补丁".format(create_patch_for_latest_n_version))
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
uploader = Uploader(cookie)
if uploader.login_ok:
    logger.info("蓝奏云登录成功，开始上传压缩包")
    uploader.upload_to_lanzouyun(patch_file_name, uploader.folder_djc_helper, history_file_prefix=uploader.history_patches_prefix)
    uploader.upload_to_lanzouyun(release_7z_name, uploader.folder_djc_helper)
    uploader.upload_to_lanzouyun(release_7z_name, uploader.folder_dnf_calc)
else:
    logger.error("蓝奏云登录失败")

# ---------------推送版本到github
# 打包完成后git添加标签
os.chdir(dir_src)
logger.info("开始推送到github")
push_github(version)

# ---------------结束
logger.info('+' * 40)
logger.info("发布完成，共用时{}，请检查上传至蓝奏云流程是否OK".format(datetime.now() - run_start_time))
logger.info('+' * 40)

os.system("PAUSE")
