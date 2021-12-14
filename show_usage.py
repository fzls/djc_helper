from log import color, logger
from usage_count import get_count, get_record_count_name_start_with, time_periods, time_periods_desc
from util import get_last_n_days, get_uuid, show_head_line, tableify
from version import now_version, ver_time

user_usage_counter_name_prefix = "user_count"
auto_updater_usage_counter_name_prefix = "auto_updater"
active_monthly_pay_user_usage_counter_name_prefix = "active_monthly_pay"

global_usage_counter_name = "global_count"
my_usage_counter_name = f"{user_usage_counter_name_prefix}/{get_uuid()}"
my_auto_updater_usage_counter_name = f"{auto_updater_usage_counter_name_prefix}/{get_uuid()}"
my_active_monthly_pay_usage_counter_name = f"{active_monthly_pay_user_usage_counter_name_prefix}/{get_uuid()}"

this_version_global_usage_counter_name = f"version/ver{now_version} {ver_time}"
this_version_user_usage_prefix = f"version_user_usage/{now_version}"
this_version_my_usage_counter_name = f"{this_version_user_usage_prefix}/{get_uuid()}"


def show_usage():
    show_head_line("从2020-10-26至今小助手使用情况概览", color("fg_bold_yellow"))

    last_n_days = get_last_n_days(14)
    extra_time_periods = [*time_periods, *last_n_days]
    extra_time_periods_desc = [*time_periods_desc, *last_n_days]

    heads = ["计数对象", *extra_time_periods_desc]
    colSizes = [20, *[8 for _ in extra_time_periods_desc]]
    rows = [
        ["本机使用次数", *[get_count(my_usage_counter_name, period) for period in extra_time_periods]],
        # ["当前版本总计使用数", *[get_count(this_version_global_usage_counter_name, period) for period in extra_time_periods]],
        # ["所有版本总计使用数", *[get_count(global_usage_counter_name, period) for period in extra_time_periods]],
        # ["当前版本活跃用户数", *[get_record_count_name_start_with(this_version_user_usage_prefix, period) for period in extra_time_periods]],
        [
            "活跃用户数",
            *[
                get_record_count_name_start_with(user_usage_counter_name_prefix, period)
                for period in extra_time_periods
            ],
        ],
        # ["DLC用户数", *[get_record_count_name_start_with(auto_updater_usage_counter_name_prefix, period) for period in extra_time_periods]],
        [
            "按月付费用户数",
            *[
                get_record_count_name_start_with(active_monthly_pay_user_usage_counter_name_prefix, period)
                for period in extra_time_periods
            ],
        ],
    ]

    logger.info(tableify(heads, colSizes))
    for row in rows:
        logger.info(color("fg_bold_cyan") + tableify(row, colSizes))


if __name__ == "__main__":
    import os

    from util import change_console_window_mode_async

    change_console_window_mode_async()
    show_usage()
    os.system("PAUSE")
