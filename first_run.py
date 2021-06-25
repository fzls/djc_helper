from db_def import FirstRunData
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


@try_except(return_val_on_except=True)
def _is_first_run(first_run_type: str, key="") -> bool:
    def cb(first_run_data: FirstRunData) -> bool:
        # 检查是否是首次运行
        first_run = True

        if first_run_data.file_created:
            # 仅当文件已经存在时，才有可能不是首次运行
            if first_run_type == FirstRunType.ONCE:
                first_run = False
            else:
                duration_func = duration_func_map[first_run_type]
                first_run = duration_func() != duration_func(first_run_data.get_update_at())

        # 如果是，则更新缓存文件
        if first_run:
            first_run_data.update_at = format_now()
            first_run_data.key = key

        logger.debug(f"{first_run_type:7s} {first_run_data.get_db_filename()} first_run={first_run} first_run_data={first_run_data}")
        logger.warning(f"{first_run_type:7s} {first_run_data.get_db_filename()} first_run={first_run} first_run_data={first_run_data}")

        return first_run

    return FirstRunData().with_context(key).update_db(cb)


if __name__ == '__main__':
    print(is_first_run("first_run"))
    print(is_daily_first_run("first_run_daily"))
    print(is_weekly_first_run("first_run_weekly"))
    print(is_monthly_first_run("first_run_monthly"))
    print(is_yearly_first_run("first_run_yearly"))
