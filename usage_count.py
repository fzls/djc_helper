# 使用次数统计脚本

import threading

import leancloud
import leancloud.object_

import util
from log import logger
from ga import track_event

LEAN_CLOUD_SERVER_ADDR = "https://d02na0oe.lc-cn-n1-shared.com"
LEAN_CLOUD_APP_ID = "D02NA0OEBGXu0YqwpVQYUNl3-gzGzoHsz"
LEAN_CLOUD_APP_KEY = "LAs9VtM5UtGHLksPzoLwuCvx"

leancloud.init(LEAN_CLOUD_APP_ID, LEAN_CLOUD_APP_KEY)


def increase_counter(name):
    threading.Thread(target=increase_counter_sync, args=(name,), daemon=True).start()


def increase_counter_sync(name):
    increase_counter_sync_lean_cloud(name)
    increase_counter_sync_google_analytics(name)
    # UNDONE: 增加自建的计数器上报


def increase_counter_sync_lean_cloud(name):
    try:
        logger.debug(f"update counter {name}")
        for counter in get_counters(name):
            counter.increment('count')
            counter.save()
    except Exception as exc:
        logger.debug(f"increase_counter {name} failed", exc_info=exc)


def increase_counter_sync_google_analytics(name):
    try:
        logger.debug(f"ga hit {name}")
        track_event("counter", name)
    except Exception as exc:
        logger.debug(f"ga hit {name} failed", exc_info=exc)


time_periods = ["all", util.get_today()]
time_periods_desc = ["累积", "今日"]


def get_counters(name):
    """
    获取此计数器的若干个实例，如总计数，本日计数，本月计数，本年计数
    """
    res = [get_counter(name, time_period) for time_period in time_periods]
    return res


def get_count(name, time_period):
    try:
        return get_counter(name, time_period).get('count', 0)
    except Exception as e:
        logger.debug(f"get_count failed name={name}, time_period={time_period} e={e}")
        return 0


def get_record_count_name_start_with(name_start_with, time_period):
    try:
        CounterClass = leancloud.Object.extend("CounterClass")
        query = CounterClass.query
        query.startswith('name', name_start_with)
        query.equal_to('time_period', time_period)
        return query.count()
    except Exception as e:
        logger.debug(f"get_record_count_name_start_with failed name_start_with={name_start_with}, time_period={time_period} e={e}")
        return 0


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
    increase_counter_sync("测试上报")

if __name__ == '__main__':
    test()
