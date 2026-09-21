import os

# 一些常数
appVersion = 149
sVersionName = "v4.7.3.0"
guanjia_skey_version = 2

# dnf助手app的客户端标识。带上这两个参数, 编年史接口会切到"app视图", 与不带时的"H5视图"相比:
#   1. getUserTaskList 返回的周任务不同(app视图是【周】查看地区排行榜, H5视图是【周】浏览话题详细页)
#   2. 两个视图的 doactionincrexp 互不认对方的 actionId, 跨视图领取会返回 -70007 非法任务
# 这俩周任务各自独立给经验, 所以两个视图都要跑一遍才能全拿到。
# ps: getNavUaStr 的值里含一个空格, 签名必须用 encode_uri_component(%20) 而非 quote_plus(+), 否则 -90002
dnf_helper_app_view_params = {
    "cClientVersionCode": "2104130006",
    "getNavUaStr": "t GameHelper_1006/4.13.0.6.2104130006",
}

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
