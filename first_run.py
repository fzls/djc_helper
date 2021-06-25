from const import first_run_dir
from data_struct import ConfigInterface
from util import *


class FirstRunType:
    # 单次运行
    ONCE = "once"
    # 每日首次运行
    DAILY = "daily"
    # 每周首次运行
    WEEKLY = "weekly"
    # 每月首次运行
    MONTHLY = "monthly"
    # 每年首次运行
    YEARLY = "yearly"


duration_func_map = {
    FirstRunType.DAILY: get_today,
    FirstRunType.WEEKLY: get_week,
    FirstRunType.MONTHLY: get_month,
    FirstRunType.YEARLY: get_year,
}


class FirstRunData(ConfigInterface):
    def __init__(self):
        self.key = "first_run_key"
        self.update_at = "2021-06-25 11:11:54"

    def get_update_at(self):
        return parse_time(self.update_at)


def is_first_run(key):
    return _is_first_run(FirstRunType.ONCE, key)


def is_daily_first_run(key=""):
    return _is_first_run(FirstRunType.DAILY, key)


def is_weekly_first_run(key=""):
    return _is_first_run(FirstRunType.WEEKLY, key)


def is_monthly_first_run(key=""):
    return _is_first_run(FirstRunType.MONTHLY, key)


def is_yearly_first_run(key=""):
    return _is_first_run(FirstRunType.YEARLY, key)


def _is_first_run(first_run_type: str, key="") -> bool:
    """
    逻辑说明
    假设key的md5为md5
    本地缓存文件路径为.first_run/md5{0:2}/md5{2:4}/md5.json
    文件内容为FirstRunData的json序列化结果
    :return: 是否是首次运行
    """
    key_md5 = md5(key)

    cache_dir = os.path.join(first_run_dir, key_md5[0:2], key_md5[2:4])
    cache_file = os.path.join(cache_dir, key_md5)

    make_sure_dir_exists(cache_dir)

    first_run_data = FirstRunData()

    # 检查是否是首次运行
    first_run = True
    if os.path.isfile(cache_file):
        if first_run_type == FirstRunType.ONCE:
            first_run = False
        else:
            try:
                first_run_data.load_from_json_file(cache_file)

                duration_func = duration_func_map[first_run_type]
                first_run = duration_func() != duration_func(first_run_data.get_update_at())
            except Exception as e:
                logger.error(f"检查首次运行出错了 type={first_run_type} key={key}", exc_info=e)
                first_run = True

    # 如果是，则更新缓存文件
    if first_run:
        first_run_data.update_at = format_now()
        first_run_data.key = key

        first_run_data.save_to_json_file(cache_file)

    logger.debug(f"{first_run_type:7s} {key_md5} first_run={first_run} first_run_data={first_run_data}")

    return first_run


if __name__ == '__main__':
    print(is_first_run("first_run"))
    print(is_daily_first_run("first_run_daily"))
    print(is_weekly_first_run("first_run_weekly"))
    print(is_monthly_first_run("first_run_monthly"))
    print(is_yearly_first_run("first_run_yearly"))
