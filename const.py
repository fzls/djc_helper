import os

# 一些常数
appVersion = 149
sVersionName = "v4.7.3.0"
guanjia_skey_version = 2

tmp_path = "/tmp/"


def get_final_dir_path(current_dir: str) -> str:
    if os.getenv("TENCENTCLOUD_RUNENV") is not None and not current_dir.startswith(tmp_path):
        # 腾讯云函数运行环境下仅/tmp目录可写
        return tmp_path + current_dir

    return current_dir


# 不同版本的db目录
# key_md5[0:3]/key_md5
db_top_dir_v1 = get_final_dir_path(".db")

# key_md5[0:2]/key_md5[2:4]/key_md5
db_top_dir_v2 = get_final_dir_path(".db_v2")

# 定义一些目录
db_top_dir = db_top_dir_v2
cached_dir = get_final_dir_path(".cached")

downloads_dir = f"{cached_dir}/downloads"
compressed_temp_dir = f"{cached_dir}/compressed"

# 确保上面定义的这些目录都存在
directory_list = [v for k, v in locals().items() if k.endswith("_dir")]
for directory in directory_list:
    os.makedirs(directory, exist_ok=True)

# vscode 在线版
vscode_online_url = "https://vscode.dev/"
