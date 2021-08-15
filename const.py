import os

# 一些常数
appVersion = 106
guanjia_skey_version = 2

# 定义一些目录
cached_dir = ".cached"
os.makedirs(cached_dir, exist_ok=True)

db_top_dir = ".db"
os.makedirs(db_top_dir, exist_ok=True)

downloads_dir = f"{cached_dir}/downloads"
os.makedirs(downloads_dir, exist_ok=True)

compressed_temp_dir = f"{cached_dir}/compressed"
os.makedirs(compressed_temp_dir, exist_ok=True)
