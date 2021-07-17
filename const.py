import os

appVersion = 106

cached_dir = ".cached"
if not os.path.isdir(cached_dir):
    os.mkdir(cached_dir)

db_top_dir = ".db"
if not os.path.isdir(db_top_dir):
    os.mkdir(db_top_dir)

guanjia_skey_version = 2
