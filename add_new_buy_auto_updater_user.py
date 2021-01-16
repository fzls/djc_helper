import json
import os

from log import logger
from upload_lanzouyun import Uploader

local_save_path = "utils/buy_auto_updater_users.txt"


def update_buy_user_local(new_buy_users) -> []:
    buy_users = []
    if os.path.exists(local_save_path):
        with open(local_save_path, 'r', encoding='utf-8') as data_file:
            buy_users = json.load(data_file)

    new_add = []
    for user in new_buy_users:
        if user in buy_users:
            logger.error(f"user={user}已经添加过了，将跳过")
            continue

        logger.info(f"user={user}为新用户，将加入名单")
        buy_users.append(user)
        new_add.append(user)

    with open(local_save_path, 'w', encoding='utf-8') as save_file:
        json.dump(buy_users, save_file, indent=2)

    return new_add


def upload():
    logger.info("购买用户有变动，开始上传到蓝奏云")
    with open("upload_cookie.json") as fp:
        cookie = json.load(fp)
    uploader = Uploader(cookie)
    if uploader.login_ok:
        logger.info("蓝奏云登录成功，开始更新购买名单")
        uploader.upload_to_lanzouyun(os.path.realpath(local_save_path), uploader.folder_online_files, uploader.buy_auto_updater_users_filename)
    else:
        logger.error("蓝奏云登录失败")


def add_user(new_buy_users):
    new_add = update_buy_user_local(new_buy_users)
    if len(new_add) != 0:
        upload()


if __name__ == '__main__':
    new_buy_users = [
        "1054073896",
    ]

    add_user(new_buy_users)

    AlwaysUpload = False
    if AlwaysUpload:
        upload()
