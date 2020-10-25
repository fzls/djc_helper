from usage_count import *
from util import *
from version import *

global_usage_counter_name = "global_count"
this_version_global_usage_counter_name = "version/ver{} {}".format(now_version, ver_time)
user_usage_counter_name_prefix = "user_count"
my_usage_counter_name = "{}/{}".format(user_usage_counter_name_prefix, get_uuid())
this_version_user_usage_prefix = "version_user_usage/{}".format(now_version)
this_version_my_usage_counter_name = "{}/{}".format(this_version_user_usage_prefix, get_uuid())


def show_usage():
    show_head_line("从2020-10-26至今小助手使用情况概览", color("fg_bold_yellow"))

    user_all_usage, user_today_usage = get_count(my_usage_counter_name, 'all'), get_count(my_usage_counter_name, get_today())
    global_all_usage, global_today_usage = get_count(global_usage_counter_name, 'all'), get_count(global_usage_counter_name, get_today())
    all_user, today_user = get_record_count_name_start_with(user_usage_counter_name_prefix, 'all'), get_record_count_name_start_with(user_usage_counter_name_prefix, get_today())

    heads = ["计数对象", "累积", "今日", "本周", "本月", "本年"]
    periods = ['all', util.get_today(), util.get_week(), util.get_month(), util.get_year()]
    colSizes = [20, 8, 8, 8, 8, 8]
    rows = [
        ["本机使用次数", *[get_count(my_usage_counter_name, period) for period in periods]],
        ["当前版本使用次数", *[get_count(this_version_global_usage_counter_name, period) for period in periods]],
        ["所有用户使用次数", *[get_count(global_usage_counter_name, period) for period in periods]],
        ["当前版本活跃用户数", *[get_record_count_name_start_with(this_version_user_usage_prefix, period) for period in periods]],
        ["所有版本活跃用户数", *[get_record_count_name_start_with(user_usage_counter_name_prefix, period) for period in periods]],
    ]

    logger.info(tableify(heads, colSizes))
    for row in rows:
        logger.info(color("fg_bold_cyan") + tableify(row, colSizes))


if __name__ == '__main__':
    show_usage()

    maximize_console()
    os.system("PAUSE")
