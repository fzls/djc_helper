import os

appVersion = 106

cached_dir = ".cached"
if not os.path.isdir(cached_dir):
    os.mkdir(cached_dir)

db_top_dir = ".db"
if not os.path.isdir(db_top_dir):
    os.mkdir(db_top_dir)

downloads_dir = f"{cached_dir}/downloads"
if not os.path.isdir(downloads_dir):
    os.mkdir(downloads_dir)

compressed_temp_dir = f"{cached_dir}/compressed"
if not os.path.isdir(compressed_temp_dir):
    os.mkdir(compressed_temp_dir)

guanjia_skey_version = 2
