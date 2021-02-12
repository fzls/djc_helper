import platform
import random
import socket
import sys
import threading
import time
import traceback
import uuid
import webbrowser

import psutil
import requests.exceptions
import selenium.common.exceptions
import urllib3.exceptions
import win32api
import win32con
import win32gui
import win32process

from db import *
from log import logger, color, asciiReset


def uin2qq(uin):
    return str(uin)[1:].lstrip('0')


def maximize_console():
    threading.Thread(target=maximize_console_sync, daemon=True).start()


def maximize_console_sync():
    if os.path.exists(".no_max_console"):
        logger.info("不启用最大化窗口")
        return

    current_pid = os.getpid()
    parents = get_parents(current_pid)

    # 找到所有窗口中在该当前进程到进程树的顶端之间路径的窗口
    candidates_index_to_hwnd = {}

    def max_current_console(hwnd, argument):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid in parents:
            # 记录下他们在进程树路径的下标
            argument[parents.index(pid)] = hwnd

    # 遍历所有窗口
    win32gui.EnumWindows(max_current_console, candidates_index_to_hwnd)

    # 排序，从而找到最接近的那个，就是我们所需的当前窗口
    indexes = sorted(list(candidates_index_to_hwnd.keys()))
    current_hwnd = candidates_index_to_hwnd[indexes[0]]
    op = win32con.SW_MAXIMIZE
    if os.path.exists(".min_console"):
        op = win32con.SW_MINIMIZE
    win32gui.ShowWindow(current_hwnd, op)


def get_parents(child):
    parents = [child]

    try:
        current = child
        while True:
            parent = psutil.Process(current).ppid()
            parents.append(parent)
            current = parent
    except psutil.NoSuchProcess:
        # 遍历到进程树最顶层仍未找到parent，说明不是父子关系
        pass

    return parents


def printed_width(msg):
    return sum([1 if ord(c) < 128 else 2 for c in msg])


def truncate(msg, expect_width) -> str:
    if printed_width(msg) <= expect_width:
        return msg

    truncated = []
    current_width = 3
    for substr in msg:
        current_width += printed_width(substr)
        if current_width > expect_width:
            truncated.append("...")
            break
        truncated.append(substr)

    return ''.join(truncated)


def padLeftRight(msg, target_size, pad_char=" ", need_truncate=False):
    msg = str(msg)
    if need_truncate:
        msg = truncate(msg, target_size)
    msg_len = printed_width(msg)
    pad_left_len, pad_right_len = 0, 0
    if msg_len < target_size:
        total = target_size - msg_len
        pad_left_len = total // 2
        pad_right_len = total - pad_left_len

    return pad_char * pad_left_len + msg + pad_char * pad_right_len


def tableify(cols, colSizes, delimiter=' ', need_truncate=False):
    return delimiter.join([padLeftRight(col, colSizes[idx], need_truncate=need_truncate) for idx, col in enumerate(cols)])


def show_head_line(msg, msg_color=None):
    char = "+"
    line_length = 80

    # 按照下列格式打印
    # +++++++++++
    # +  test   +
    # +++++++++++
    if msg_color is None:
        msg_color = color("fg_bold_green")
    logger.warning(char * line_length)
    logger.warning(char + msg_color + padLeftRight(msg, line_length - 2) + color("WARNING") + char)
    logger.warning(char * line_length)


def get_this_week_monday():
    return _get_this_week_monday().strftime("%Y%m%d")


def get_last_week_monday():
    lastWeekMonday = _get_this_week_monday() - datetime.timedelta(days=7)
    return lastWeekMonday.strftime("%Y%m%d")


def _get_this_week_monday():
    now = datetime.datetime.now()
    monday = now - datetime.timedelta(days=now.weekday())
    return monday


def get_now():
    return datetime.datetime.now()


def get_now_unix():
    return int(time.time())


def get_today():
    return get_now().strftime("%Y%m%d")


def get_last_n_days(n):
    return [(get_now() - datetime.timedelta(i)).strftime("%Y%m%d") for i in range(1, n + 1)]


def get_week():
    return get_now().strftime("%Y-week-%W")


def get_month():
    return get_now().strftime("%Y%m")


def is_daily_first_run(key=""):
    db = load_db()

    today = get_today()
    daily_run_key = f'last_run_at_{key}'
    last_run_at = db.get(daily_run_key, "")

    db[daily_run_key] = today

    save_db(db)
    return last_run_at != today


def is_weekly_first_run(key=""):
    db = load_db()

    week = get_week()
    weekly_run_key = f'last_run_at_week_{key}'
    last_run_at_week = db.get(weekly_run_key, "")

    db[weekly_run_key] = week

    save_db(db)
    return last_run_at_week != week


def is_monthly_first_run(key=""):
    db = load_db()

    month = get_month()
    monthly_run_key = f'last_run_at_month_{key}'
    last_run_at_month = db.get(monthly_run_key, "")

    db[monthly_run_key] = month

    save_db(db)
    return last_run_at_month != month


def is_first_run(key):
    db = load_db()

    cfr = 'custom_first_run'
    if cfr not in db:
        db[cfr] = {}

    hasRun = db[cfr].get(key, False)

    db[cfr][key] = True

    save_db(db)
    return not hasRun


def get_year():
    return get_now().strftime("%Y")


def filter_unused_params(urlRendered):
    originalUrl = urlRendered
    try:
        path = ""
        if urlRendered.startswith("http"):
            if '?' not in urlRendered:
                return urlRendered

            idx = urlRendered.index('?')
            path, urlRendered = urlRendered[:idx], urlRendered[idx + 1:]

        parts = urlRendered.split('&')

        validParts = []
        for part in parts:
            if part == "":
                continue
            k, v = part.split('=')
            if v != "":
                validParts.append(part)

        newUrl = '&'.join(validParts)
        if path != "":
            newUrl = path + "?" + newUrl

        return newUrl
    except Exception as e:
        logger.error(f"过滤参数出错了，urlRendered={originalUrl}", exc_info=e)
        stack_info = color("bold_black") + ''.join(traceback.format_stack())
        logger.error(f"看到上面这个报错，请帮忙截图发反馈群里~ 调用堆栈=\n{stack_info}")
        return originalUrl


def run_from_src():
    exe_path = sys.argv[0]
    dirpath, filename = os.path.dirname(exe_path), os.path.basename(exe_path)

    return filename.endswith(".py")


def get_uuid():
    return f"{platform.node()}-{uuid.getnode()}"


def use_by_myself():
    return os.path.exists(".use_by_myself")


def try_except(fun):
    def decorator(*args, **kwargs):
        try:
            fun(*args, **kwargs)
        except Exception as e:
            logger.error(f"执行{fun.__name__}出错了" + check_some_exception(e), exc_info=e)

    return decorator


def check_some_exception(e) -> str:
    msg = ""

    def format_msg(msg):
        return "\n" + color("bold_yellow") + msg + asciiReset

    # 特判一些错误
    if type(e) is KeyError and e.args[0] == 'modRet':
        msg += format_msg("大概率是这个活动过期了，或者放鸽子到点了还没开放，若影响正常运行流程，可先自行关闭这个活动开关(若config.toml中没有，请去config.toml.example找到对应开关名称)，或等待新版本（日常加班，有时候可能会很久才发布新版本）")
    elif type(e) in [socket.timeout,
                     urllib3.exceptions.ConnectTimeoutError, urllib3.exceptions.MaxRetryError, urllib3.exceptions.ReadTimeoutError,
                     requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, ]:
        msg += format_msg("网络超时了，一般情况下是因为网络问题，也有可能是因为对应网页的服务器不太行，多试几次就好了<_<")
    elif type(e) in [selenium.common.exceptions.TimeoutException, ]:
        msg += format_msg("浏览器等待对应元素超时了，很常见的。如果一直超时导致无法正常运行，可去config.toml.example将登录超时相关配置加到config.toml中，并调大超时时间")

    return msg


def show_end_time(end_time):
    # end_time = "2021-02-23 00:00:00"
    remaining_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S") - datetime.datetime.now()
    logger.info(color("bold_black") + f"活动的结束时间为{end_time}，剩余时间为{remaining_time}")


def time_less(left_time_str, right_time_str, time_fmt="%Y-%m-%d %H:%M:%S"):
    left_time = datetime.datetime.strptime(left_time_str, time_fmt)
    right_time = datetime.datetime.strptime(right_time_str, time_fmt)

    return left_time < right_time


def parse_time(time_str, time_fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(time_str, time_fmt)


def format_time(dt, time_fmt="%Y-%m-%d %H:%M:%S"):
    return dt.strftime(time_fmt)


def format_now(time_fmt="%Y-%m-%d %H:%M:%S"):
    return format_time(datetime.datetime.now(), time_fmt=time_fmt)


def async_call(cb, *args, **params):
    threading.Thread(target=cb, args=args, kwargs=params, daemon=True).start()


def async_message_box(msg, title, print_log=True, icon=win32con.MB_ICONWARNING, open_url=""):
    def cb():
        if print_log:
            logger.warning(color("bold_cyan") + msg)

        win32api.MessageBox(0, msg, title, icon)

        if open_url != "":
            webbrowser.open(open_url)

    async_call(cb)


def human_readable_size(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def get_random_face():
    return random.choice([
        'ヾ(◍°∇°◍)ﾉﾞ', 'ヾ(✿ﾟ▽ﾟ)ノ', 'ヾ(๑╹◡╹)ﾉ"', '٩(๑❛ᴗ❛๑)۶', '٩(๑-◡-๑)۶ ',
        'ヾ(●´∀｀●) ', '(｡◕ˇ∀ˇ◕)', '(◕ᴗ◕✿)', '✺◟(∗❛ัᴗ❛ั∗)◞✺', '(づ｡◕ᴗᴗ◕｡)づ',
        '(≧∀≦)♪', '♪（＾∀＾●）ﾉ', '(●´∀｀●)ﾉ', "(〃'▽'〃)", '(｀・ω・´)',
        'ヾ(=･ω･=)o', '(◍´꒳`◍)', '(づ●─●)づ', '｡◕ᴗ◕｡', '●﹏●',
    ])


if __name__ == '__main__':
    print(get_now_unix())
    print(get_this_week_monday())
    print(get_last_week_monday())
    print(get_uuid())
    print(run_from_src())
    print(use_by_myself())
    print(show_end_time("2021-02-23 00:00:00"))
    print(truncate("风之凌殇风之凌殇", 12))
