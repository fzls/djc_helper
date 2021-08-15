import os

# 一些常数
appVersion = 106
guanjia_skey_version = 2

# 定义一些目录
db_top_dir = ".db"
cached_dir = ".cached"
downloads_dir = f"{cached_dir}/downloads"
compressed_temp_dir = f"{cached_dir}/compressed"

# 确保上面定义的这些目录都存在
directory_list = [v for k, v in locals().items() if k.endswith("_dir")]
for directory in directory_list:
    os.makedirs(directory, exist_ok=True)
