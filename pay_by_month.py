import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

from dao import BuyInfo, BuyRecord, OrderInfo
from data_struct import to_json
from db import load_db, save_db
from log import logger, color
from upload_lanzouyun import Uploader
from util import format_time, parse_time

local_save_path = "utils/user_monthly_pay_info.txt"

# 一个月的天数以31计算
month_inc = timedelta(days=31)


def update_buy_user_local(order_infos: List[OrderInfo]):
    buy_users = {}  # type: Dict[str, BuyInfo]
    if os.path.exists(local_save_path):
        with open(local_save_path, 'r', encoding='utf-8') as data_file:
            raw_infos = json.load(data_file)
            for qq, raw_info in raw_infos.items():
                info = BuyInfo().auto_update_config(raw_info)
                buy_users[qq] = info

    datetime_fmt = "%Y-%m-%d %H:%M:%S"
    now = datetime.now()
    now_str = now.strftime(datetime_fmt)

    for order_info in order_infos:
        if has_buy_in_an_hour(order_info.qq):
            logger.error(f"{order_info.qq}在一小时内已经处理过，是否是重复运行了?")
            continue

        if order_info.qq in buy_users:
            user_info = buy_users[order_info.qq]
        else:
            user_info = BuyInfo()
            user_info.qq = order_info.qq
            buy_users[order_info.qq] = user_info

        # 更新时长
        expired_at = datetime.strptime(user_info.expire_at, datetime_fmt)
        if now > expired_at:
            # 已过期，从当前时间开始重新计算
            start_time = now
        else:
            # 续期，从之前结束时间叠加
            start_time = expired_at
        updated_expired_at = start_time + order_info.buy_month * month_inc
        user_info.expire_at = updated_expired_at.strftime(datetime_fmt)

        user_info.total_buy_month += order_info.buy_month
        user_info.buy_records.append(BuyRecord().auto_update_config({
            "buy_month": order_info.buy_month,
            "buy_at": now_str,
            "reason": "购买",
        }))

        # 更新游戏QQ
        for game_qq in order_info.game_qqs:
            if game_qq not in user_info.game_qqs:
                user_info.game_qqs.append(game_qq)

        msg = f"{user_info.qq} 购买 {order_info.buy_month} 个月成功，过期时间为{user_info.expire_at}，购买前过期时间为{expired_at}。累计购买{user_info.total_buy_month}个月。"
        msg += "购买详情如下：\n" + '\n'.join('\t' + f'{record.buy_at} {record.reason} {record.buy_month} 月' for record in user_info.buy_records)
        logger.info(msg)

        save_buy_timestamp(order_info.qq)

    with open(local_save_path, 'w', encoding='utf-8') as save_file:
        json.dump(to_json(buy_users), save_file, indent=2)

    total_month = 0
    for qq, user_info in buy_users.items():
        if qq == "1054073896":
            # 跳过自己<_<，不然数据被污染了
            continue
        total_month += user_info.total_buy_month
    total_money = 5 * total_month
    logger.info(color("bold_green") + f"目前总购买人数为{len(buy_users)}，累计购买月数为{total_month}，累积金额约为{total_money}")


key_buy_time = "pay_by_month_last_buy_time"


def has_buy_in_an_hour(qq):
    db = load_db()

    if key_buy_time not in db:
        return False

    buy_time = db[key_buy_time].get(str(qq), "2021-01-01 00:00:00")

    return parse_time(buy_time) >= datetime.now() - timedelta(hours=1)


def save_buy_timestamp(qq):
    db = load_db()

    if key_buy_time not in db:
        db[key_buy_time] = {}

    db[key_buy_time][str(qq)] = format_time(datetime.now())

    save_db(db)


def upload():
    logger.info("开始上传到蓝奏云")
    with open("upload_cookie.json") as fp:
        cookie = json.load(fp)
    uploader = Uploader(cookie)
    if uploader.login_ok:
        logger.info("蓝奏云登录成功，开始更新付费名单")
        uploader.upload_to_lanzouyun(os.path.realpath(local_save_path), uploader.folder_online_files, uploader.user_monthly_pay_info_filename)
    else:
        logger.error("蓝奏云登录失败")


def process_orders(order_infos: List[OrderInfo]):
    update_buy_user_local(order_infos)
    upload()


if __name__ == '__main__':
    raw_order_infos = [
        # QQ号   游戏QQ列表  购买月数
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
    ]

    order_infos = []
    for qq, game_qqs, buy_month in raw_order_infos:
        order_info = OrderInfo()
        order_info.qq = qq
        order_info.game_qqs = game_qqs
        order_info.buy_month = buy_month
        order_infos.append(order_info)

    process_orders(order_infos)
