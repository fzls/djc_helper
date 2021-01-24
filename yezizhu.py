import multiprocessing
import time
from datetime import datetime, timedelta
from multiprocessing.dummy import Pool
from urllib.parse import quote_plus

import requests

from log import logger, color
from util import tableify

mobile = 17328213065
prize_name = quote_plus("春节套*1")

processor_count = 2 * multiprocessing.cpu_count()
pool = Pool(processor_count)


def try_exchange():
    logger.info("开始运行兑换叶子猪春节套脚本")
    while True:
        now = datetime.now()
        startTime = now.replace(hour=11, minute=59, second=58, microsecond=500000)
        endTime = startTime + timedelta(seconds=3)

        # 如果今天的尝试时间已经过了，则切换为下一轮时间
        if now > endTime:
            startTime = startTime + timedelta(days=1)
            endTime = endTime + timedelta(days=1)

        query_info()
        exchange(startTime, endTime)


def query_info():
    url = "http://dnf.api.yzz.cn/activity/getExchangeList"
    res = requests.get(url).json()

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
    show_progress_delta = 0.1

    logger.info(color("bold_yellow") + f"本轮开始时间为{startTime}，结束时间为{endTime}，请求等待间隔为{waitTime}s，预计将尝试{(endTime - startTime).seconds // waitTime}次")
    progress = 0
    while datetime.now() < startTime:
        progress += waitTime
        if progress >= show_progress_delta:
            print(f"\r当前时间为{datetime.now()}...，还需要等待{startTime - datetime.now()}才会开始尝试", end='')
            progress -= show_progress_delta
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
    headers = {
        "Proxy-Connection": "keep-alive",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "DNT": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "http://dnf.yzz.cn",
        "Referer": "http://dnf.yzz.cn/",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,en-GB;q=0.6,ja;q=0.5",
    }

    res = requests.post(url, data=f"mobile={mobile}&prize_name={prize_name}", headers=headers)
    logger.info(f"请求序号{index:5d}: {res.json()}")
    return res.json()


if __name__ == '__main__':
    try_exchange()
