# 使用次数统计脚本
import os

import leancloud
import leancloud.object_

from first_run import is_daily_first_run
from ga import *
from log import logger
from util import get_today, try_except, async_call

LEAN_CLOUD_SERVER_ADDR = "https://d02na0oe.lc-cn-n1-shared.com"
LEAN_CLOUD_APP_ID = "D02NA0OEBGXu0YqwpVQYUNl3-gzGzoHsz"
LEAN_CLOUD_APP_KEY = "LAs9VtM5UtGHLksPzoLwuCvx"

leancloud.init(LEAN_CLOUD_APP_ID, LEAN_CLOUD_APP_KEY)


def increase_counter(name: str, report_to_lean_cloud=False, report_to_google_analytics=True, ga_type=GA_REPORT_TYPE_EVENT, ga_category=""):
    def _cb():
        if report_to_lean_cloud and is_daily_first_run(name):
            # lean_cloud的计数器每日最多上报一次
            increase_counter_sync_lean_cloud(name)

        if report_to_google_analytics:
            increase_counter_sync_google_analytics(name, ga_type, ga_category)

        # UNDONE: 增加自建的计数器上报

    async_call(_cb)


@try_except(show_exception_info=False)
def increase_counter_sync_lean_cloud(name: str):
    logger.debug(f"report to lean cloud, name = {name}")
    for counter in get_counters(name):
        counter.increment('count')
        counter.save()


@try_except(show_exception_info=False)
def increase_counter_sync_google_analytics(name: str, ga_type: str, ga_category: str):
    logger.debug(f"report to google analytics, name = {name}")
    if ga_type == GA_REPORT_TYPE_EVENT:
        track_event(ga_category, name)
    elif ga_type == GA_REPORT_TYPE_PAGE_VIEW:
        track_page(name)
    else:
        logger.error(f"unknow ga_type={ga_type}")


time_periods = ["all", get_today()]
time_periods_desc = ["累积", "今日"]


def get_counters(name):
    """
    获取此计数器的若干个实例，如总计数，本日计数，本月计数，本年计数
    """
    res = [get_counter(name, time_period) for time_period in time_periods]
    return res


@try_except(show_exception_info=False, return_val_on_except=0)
def get_count(name, time_period):
    return get_counter(name, time_period).get('count', 0)


@try_except(show_exception_info=False, return_val_on_except=0)
def get_record_count_name_start_with(name_start_with, time_period):
    CounterClass = leancloud.Object.extend("CounterClass")
    query = CounterClass.query
    query.startswith('name', name_start_with)
    query.equal_to('time_period', time_period)
    return query.count()


def get_counter(name, time_period):
    """
    获取指定计数器在指定时间段的计数实例
    """
    CounterClass = leancloud.Object.extend("CounterClass")
    query = CounterClass.query
    query.equal_to('name', name)
    query.equal_to('time_period', time_period)
    counters = query.find()
    if len(counters) != 0:
        # 若已存在，则返回现有实例
        return counters[0]

    # 否则需要创建这个counter
    counter = CounterClass()  # type: leancloud.Object
    counter.set('name', name)
    counter.set('time_period', time_period)
    counter.set('count', 0)
    counter.save()
    return counter


def leancloud_api(api):
    return f"{LEAN_CLOUD_SERVER_ADDR}/1.1/{api}"


def test():
    increase_counter("test_event", False, True, GA_REPORT_TYPE_EVENT)
    increase_counter("test_page_view", False, True, GA_REPORT_TYPE_PAGE_VIEW)

    os.system("PAUSE")


if __name__ == '__main__':
    test()
