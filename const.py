import os

# 一些常数
appVersion = 106
guanjia_skey_version = 2

# 特殊处理腾讯云函数
base_dir_prefix = ""
if os.getenv("TENCENTCLOUD_RUNENV") is not None:
    base_dir_prefix = "/tmp/"

# 定义一些目录
db_top_dir = base_dir_prefix + ".db"
cached_dir = base_dir_prefix + ".cached"

downloads_dir = f"{cached_dir}/downloads"
compressed_temp_dir = f"{cached_dir}/compressed"

# 确保上面定义的这些目录都存在
directory_list = [v for k, v in locals().items() if k.endswith("_dir")]
for directory in directory_list:
    os.makedirs(directory, exist_ok=True)
