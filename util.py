import threading
import time
import traceback

import psutil
import win32con
import win32gui
import win32process

from db import *
from log import logger, color


def uin2qq(uin):
    return str(uin)[1:].lstrip('0')


def maximize_console():
    threading.Thread(target=maximize_console_sync, daemon=True).start()


def maximize_console_sync():
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
    win32gui.ShowWindow(current_hwnd, win32con.SW_MAXIMIZE)


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


def padLeftRight(msg, target_size, pad_char=" "):
    msg = str(msg)
    msg_len = printed_width(msg)
    pad_left_len, pad_right_len = 0, 0
    if msg_len < target_size:
        total = target_size - msg_len
        pad_left_len = total // 2
        pad_right_len = total - pad_left_len

    return pad_char * pad_left_len + msg + pad_char * pad_right_len


def tableify(cols, colSizes, delimiter=' '):
    return delimiter.join([padLeftRight(col, colSizes[idx]) for idx, col in enumerate(cols)])


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
    now = datetime.datetime.now()
    monday = now - datetime.timedelta(days=now.weekday())
    return monday.strftime("%Y%m%d")


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


def is_daily_first_run():
    db = load_db()

    today = get_today()
    daily_run_key = 'last_run_at'
    last_run_at = db.get(daily_run_key, "")

    db[daily_run_key] = today

    save_db(db)
    return last_run_at != today


def is_weekly_first_run():
    db = load_db()

    week = get_week()
    weekly_run_key = 'last_run_at_week'
    last_run_at_week = db.get(weekly_run_key, "")

    db[weekly_run_key] = week

    save_db(db)
    return last_run_at_week != week


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
        logger.error("过滤参数出错了，urlRendered={}".format(originalUrl), exc_info=e)
        logger.error("看到上面这个报错，请帮忙截图发反馈群里~ 调用堆栈=\n{}".format(color("bold_black") + ''.join(traceback.format_stack())))
        return originalUrl


if __name__ == '__main__':
    print(get_now_unix())
