import multiprocessing
import time
from datetime import datetime, timedelta
from multiprocessing.dummy import Pool
from urllib.parse import quote_plus

import requests

from log import logger, color
from util import tableify, maximize_console_sync

mobile = 17328213065
prize_name = quote_plus("春节套*1")

processor_count = multiprocessing.cpu_count()
pool = Pool(processor_count)

headers = {
    "Proxy-Connection": "keep-alive",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "DNT": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
    "Origin": "http://dnf.yzz.cn",
    "Referer": "http://dnf.yzz.cn/",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,en-GB;q=0.6,ja;q=0.5",
}

post_headers = {
    **headers,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}


def try_exchange():
    logger.info("开始运行兑换叶子猪春节套脚本")
    while True:
        now = datetime.now()
        startTime = now.replace(hour=11, minute=59, second=59, microsecond=0)
        endTime = startTime + timedelta(seconds=2)

        # 如果今天的尝试时间已经过了，则切换为下一轮时间
        if now > endTime:
            startTime = startTime + timedelta(days=1)
            endTime = endTime + timedelta(days=1)

        query_info()
        exchange(startTime, endTime)


def query_user_info():
    url = f"http://dnf.api.yzz.cn/activity/userInfo?mobile={mobile}"
    res = requests.get(url, headers=headers).json()

    return "账号({mobile}) 当前积分为{point_amount}，已使用{point_used}，已领取的奖励为：{prize_jfcj} {prize_jfdh}(查询于{ts})。".format(**res["data"], ts=datetime.now())


def query_info():
    url = "http://dnf.api.yzz.cn/activity/getExchangeList"
    res = requests.get(url, headers=headers).json()

    heads = ["id", "名称", "积分", "启用", "库存", "已发放", "总计"]
    colSizes = [3, 25, 6, 6, 6, 6, 6]

    import datetime
    logger.info(color("bold_yellow") + str(datetime.datetime.now()))
    logger.info(tableify(heads, colSizes))
    for item in res["data"]:
        cols = [item["id"], item["prize_name"], item["point"], item["enable"], item["stock"], item["sent_num"], item["stock"] + item["sent_num"]]
        logger.info(color("bold_green") + tableify(cols, colSizes))


def exchange(startTime, endTime):
    waitTime = 0.001
    show_progress_start_time = time.time()
    show_progress_delta = 0.1
    update_user_info_start_time = time.time()
    update_user_info_delta = 30 * 60

    latest_user_info = query_user_info()

    logger.info(color("bold_yellow") + f"本轮开始时间为{startTime}，结束时间为{endTime}，请求等待间隔为{waitTime}s，预计将尝试{(endTime - startTime).seconds // waitTime}次")
    while datetime.now() < startTime:
        now_time = time.time()
        if now_time - show_progress_start_time >= show_progress_delta:
            end = ''
            if now_time - update_user_info_start_time >= update_user_info_delta:
                latest_user_info = query_user_info()
                update_user_info_start_time = now_time
                end = '\n'

            print("\r" +
                  color("bold_cyan") + latest_user_info +
                  color("bold_green") + f"当前时间为{datetime.now()}...，还需要等待{startTime - datetime.now()}才会开始尝试。",
                  end=end)
            show_progress_start_time = now_time

        time.sleep(waitTime)
    print("\r", end='')

    futures = []

    logger.info(f"开始准备发请求，现在时间为{datetime.now()}，将以{waitTime}s的尝试间隔，一直尝试到{endTime}或成功抢到")
    index = 0
    while datetime.now() < endTime:
        _work_start_time = time.time()

        index += 1
        futures.append(pool.apply_async(do_exchange, [index]))

        _work_used = time.time() - _work_start_time
        if _work_used < waitTime:
            time.sleep(waitTime - _work_used)

    for future in futures:
        res = future.get()
        if res['success']:
            logger.info(color("bold_yellow") + "抢到啦~")

    logger.info(color("bold_cyan") + f"本轮尝试已完成，总计进行{index}次请求\n")


def do_exchange(index=0):
    url = "http://dnf.api.yzz.cn/activity/exchange"

    res = requests.post(url, data=f"mobile={mobile}&prize_name={prize_name}", headers=post_headers)
    logger.info(f"请求序号{index:5d}: {res.json()}")
    return res.json()


if __name__ == '__main__':
    maximize_console_sync()
    try_exchange()
