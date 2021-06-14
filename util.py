import ctypes
import pathlib
import platform
import random
import shutil
import signal
import socket
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from typing import Callable, Any, Optional
from functools import wraps

import psutil
import requests.exceptions
import selenium.common.exceptions
import urllib3.exceptions
import win32api
import win32con
import win32gui
import win32process

from const import cached_dir
from data_struct import to_raw_type
from db import *
from log import logger, color, asciiReset
from version import now_version, ver_time


def uin2qq(uin):
    return str(uin)[1:].lstrip('0')


def is_valid_qq(qq: str) -> bool:
    return qq.isnumeric()


def maximize_console():
    threading.Thread(target=maximize_console_sync, daemon=True).start()


def maximize_console_sync():
    logger.info(color("bold_cyan") + "准备最大化运行窗口，请稍候。若不想最大化，可在小助手目录创建 .no_max_console 文件。若想最小化，则可创建 .min_console 文件。")

    if os.path.exists(".no_max_console"):
        logger.info("不启用最大化窗口")
        return

    if is_run_in_pycharm():
        logger.info("当前运行在pycharm中，不尝试最大化窗口~")
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
        logger.info("已启用最小化模式")
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


def padLeftRight(msg, target_size, pad_char=" ", mode="middle", need_truncate=False):
    msg = str(msg)
    if need_truncate:
        msg = truncate(msg, target_size)
    msg_len = printed_width(msg)
    pad_left_len, pad_right_len = 0, 0
    if msg_len < target_size:
        total = target_size - msg_len
        pad_left_len = total // 2
        pad_right_len = total - pad_left_len

    if mode == "middle":
        return pad_char * pad_left_len + msg + pad_char * pad_right_len
    elif mode == "left":
        return msg + pad_char * (pad_left_len + pad_right_len)
    else:
        return pad_char * (pad_left_len + pad_right_len) + msg


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


def get_current():
    return get_now().strftime("%Y%m%d%H%M%S")


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


def try_except(show_exception_info=True, show_last_process_result=True, extra_msg="", return_val_on_except=None):
    def decorator(fun):
        @wraps(fun)
        def wrapper(*args, **kwargs):
            try:
                return fun(*args, **kwargs)
            except Exception as e:
                msg = f"执行{fun.__name__}({args}, {kwargs})出错了"
                if extra_msg != "":
                    msg += ", " + extra_msg
                msg += check_some_exception(e, show_last_process_result)

                logFunc = logger.error
                if not show_exception_info:
                    logFunc = logger.debug
                logFunc(msg, exc_info=e)

                return return_val_on_except

        return wrapper

    return decorator


def check_some_exception(e, show_last_process_result=True) -> str:
    msg = ""

    def format_msg(msg, _color="bold_yellow"):
        return "\n" + color(_color) + msg + asciiReset

    # 特判一些错误
    if type(e) is KeyError and e.args[0] == 'modRet':
        msg += format_msg("大概率是这个活动过期了，或者放鸽子到点了还没开放，若影响正常运行流程，可先自行关闭这个活动开关(若config.toml中没有，请去config.toml.example找到对应开关名称)，或等待新版本（日常加班，有时候可能会很久才发布新版本）")
    elif type(e) in [socket.timeout,
                     urllib3.exceptions.ConnectTimeoutError, urllib3.exceptions.MaxRetryError, urllib3.exceptions.ReadTimeoutError,
                     requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, ]:
        msg += format_msg("网络超时了，一般情况下是因为网络问题，也有可能是因为对应网页的服务器不太行，多试几次就好了<_<")
    elif type(e) in [selenium.common.exceptions.TimeoutException, ]:
        msg += format_msg("浏览器等待对应元素超时了，很常见的。如果一直超时导致无法正常运行，可去config.toml.example将登录超时相关配置加到config.toml中，并调大超时时间")
    elif type(e) in [PermissionError, ]:
        msg += format_msg((
            "权限错误一般是以下原因造成的\n"
            "1. 该文件被占用，比如打开了多个小助手实例或者其他应用占用了这些文件，可以尝试重启电脑后再运行\n"
            "2. 开启了VPN，请尝试关闭VPN后再运行（看上去毫不相关，但确实会这样- -）"
        ))

    if show_last_process_result:
        from network import last_process_result, last_receive_response
        if last_process_result is not None:
            msg += format_msg(f"最近一次处理成功的请求结果为：{last_process_result}", "bold_green")
        if last_receive_response is not None:
            msg += format_msg(f"最近一次收到的请求结果为：{last_receive_response}", "bold_cyan")

    return msg


def is_act_expired(end_time, time_fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(end_time, time_fmt) < datetime.datetime.now()


def get_remaining_time(end_time, time_fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(end_time, time_fmt) - datetime.datetime.now()


def get_past_time(t, time_fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now() - datetime.datetime.strptime(t, time_fmt)


def show_end_time(end_time, time_fmt="%Y-%m-%d %H:%M:%S"):
    # end_time = "2021-02-23 00:00:00"
    remaining_time = get_remaining_time(end_time, time_fmt)
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
    async_call(message_box, msg, title, print_log, icon, open_url)


def message_box(msg, title, print_log=True, icon=win32con.MB_ICONWARNING, open_url=""):
    if print_log:
        logger.warning(color("bold_cyan") + msg)

    if is_run_in_github_action():
        return

    win32api.MessageBox(0, msg, title, icon)

    if open_url != "":
        webbrowser.open(open_url)


def human_readable_size(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


KiB = 1024
MiB = 1024 * KiB
GiB = 1024 * MiB
TiB = 1024 * GiB


@try_except()
def clean_dir_to_size(dir_name: str, max_logs_size: int = 1024 * MiB, keep_logs_size: int = 512 * MiB):
    # 检查一下是否存在目录
    if not os.path.isdir(dir_name):
        return

    hrs = human_readable_size

    logger.info(color("bold_green") + f"尝试清理日志目录({dir_name})，避免日志目录越来越大~")

    logs_size = get_directory_size(dir_name)
    if logs_size <= max_logs_size:
        logger.info(f"当前日志目录大小为{hrs(logs_size)}，未超出设定最大值为{hrs(max_logs_size)}，无需清理")
        return

    logger.info(f"当前日志目录大小为{hrs(logs_size)}，超出设定最大值为{hrs(max_logs_size)}，将按照时间顺序移除部分日志，直至不高于设定清理后剩余大小{hrs(keep_logs_size)}")

    # 获取全部日志文件，并按照时间升序排列
    logs = list(pathlib.Path(dir_name).glob('**/*'))

    def sort_key(f: pathlib.Path):
        return f.stat().st_mtime

    logs.sort(key=sort_key)

    # 清除日志，直至剩余日志大小低于设定值
    remaining_logs_size = logs_size
    remove_log_count = 0
    remove_log_size = 0
    for log_file in logs:
        stat = log_file.stat()
        remaining_logs_size -= stat.st_size
        remove_log_count += 1
        remove_log_size += stat.st_size

        os.remove(f"{log_file}")
        logger.info(f"移除第{remove_log_count}个日志:{log_file.name} 大小：{hrs(stat.st_size)}，剩余日志大小为{hrs(remaining_logs_size)}")

        if remaining_logs_size <= keep_logs_size:
            logger.info(color("bold_green") + f"当前剩余日志大小为{hrs(remaining_logs_size)}，将停止日志清理流程~ 本次累计清理{remove_log_count}个日志文件，总大小为{hrs(remove_log_size)}")
            break


def get_directory_size(dir_name: str) -> int:
    root_directory = pathlib.Path(dir_name)
    return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())


def get_random_face():
    return random.choice([
        'ヾ(◍°∇°◍)ﾉﾞ', 'ヾ(✿ﾟ▽ﾟ)ノ', 'ヾ(๑╹◡╹)ﾉ"', '٩(๑❛ᴗ❛๑)۶', '٩(๑-◡-๑)۶ ',
        'ヾ(●´∀｀●) ', '(｡◕ˇ∀ˇ◕)', '(◕ᴗ◕✿)', '✺◟(∗❛ัᴗ❛ั∗)◞✺', '(づ｡◕ᴗᴗ◕｡)づ',
        '(≧∀≦)♪', '♪（＾∀＾●）ﾉ', '(●´∀｀●)ﾉ', "(〃'▽'〃)", '(｀・ω・´)',
        'ヾ(=･ω･=)o', '(◍´꒳`◍)', '(づ●─●)づ', '｡◕ᴗ◕｡', '●﹏●',
    ])


def clear_login_status():
    shutil.rmtree(cached_dir, ignore_errors=True)
    os.mkdir(cached_dir)


def get_screen_size():
    width, height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
    return width, height


def make_sure_dir_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def is_run_in_github_action():
    return get_config_from_env() != ""


def get_config_from_env():
    return os.environ.get("DJC_HELPER_CONFIG_TOML", "")


def disable_pause_after_run() -> bool:
    return os.path.exists(".disable_pause_after_run")


# 解析文件中的unicode编码字符串，形如\u5df2，将其转化为可以直观展示的【已】，目前用于查看github action的日志
def parse_unicode_escape_string(filename: str):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.read()

        invalid_chars = []
        for code in range(ord('g'), ord('z') + 1):
            invalid_chars.append(chr(code))
        for code in range(ord('G'), ord('Z') + 1):
            invalid_chars.append(chr(code))
        print(invalid_chars)
        for char in invalid_chars:
            lines = lines.replace(f"u{char}", f"_u{char}")

        print(lines.encode().decode("unicode-escape"))


def remove_none_from_list(l: list) -> list:
    return list(filter(lambda x: x is not None, l))


_root_caches_key = "caches"
cache_name_download = "download_cache"


def with_cache(cache_category: str, cache_key: str, cache_miss_func: Callable[[], Any], cache_validate_func: Optional[Callable[[Any], bool]] = None, cache_max_seconds=600):
    """

    :param cache_category: 缓存类别，不同类别的key不冲突
    :param cache_key: 缓存key，单个类别内唯一
    :param cache_miss_func: 缓存未命中时获取最新值的回调，返回值必须要是python原生类型，以便进行json的序列化和反序列化
    :param cache_validate_func: func(cached_value)->bool, 用于检查缓存值是否仍有效，比如如果缓存的是文件路径，则判断路径是否存在
    :param cache_max_seconds: 缓存时限（秒），默认600s
    :return: 缓存中获取的数据（若未过期），或最新获取的数据
    """
    db = load_db()

    if _root_caches_key not in db:
        db[_root_caches_key] = {}
    cache = db[_root_caches_key]

    # 尝试使用缓存内容
    if cache_category in cache and cache_key in cache[cache_category]:
        cache_info = cache[cache_category][cache_key]
        if parse_time(cache_info["last_update_at"]) + datetime.timedelta(seconds=cache_max_seconds) >= get_now():
            cached_value = cache_info["value"]
            if cache_validate_func is None or cache_validate_func(cached_value):
                logger.debug(f"{cache_category} {cache_key} 本地缓存尚未过期，且检验有效，将使用缓存内容。缓存信息为 {cache_info}")
                return cached_value

    # 调用回调获取最新结果，并保存
    latest_value = cache_miss_func()

    if cache_category not in cache:
        cache[cache_category] = {}
    cache[cache_category][cache_key] = {
        "last_update_at": format_now(),
        "value": latest_value,
    }

    save_db(db)

    return latest_value


def reset_cache(cache_category: str):
    db = load_db()

    if _root_caches_key not in db:
        db[_root_caches_key] = {}
    cache = db[_root_caches_key]

    # 清空cache
    cache[cache_category] = {}

    save_db(db)

    logger.debug(f"清空cache={cache_category}")

    return


def count_down(ctx: str, seconds: int, update_interval=0.1):
    if is_run_in_github_action():
        # 在github action环境下直接sleep
        logger.info(f"{ctx} wait for {seconds}seconds")
        time.sleep(seconds)
        return

    now_time = get_now()
    end_time = now_time + datetime.timedelta(seconds=seconds)

    while now_time < end_time:
        remaining_duration = end_time - now_time
        print("\r" + f"{ctx} 剩余等待时间: {remaining_duration}", end='')
        time.sleep(update_interval)
        now_time = get_now()
    print("\r" + " " * 80)


def range_from_one(stop: int):
    return range(1, stop + 1)


def get_retry_data(retry_key: str, max_retry_count: int, max_retry_wait_time: int):
    from dao import RetryData

    # 结合历史数据和配置，计算各轮重试等待的时间
    db = load_db()
    raw_login_retry_data = db.get(retry_key, {})
    login_retry_data = RetryData().auto_update_config(raw_login_retry_data)

    retry_timeouts = []
    if max_retry_count == 1:
        retry_timeouts = [max_retry_wait_time]
    elif max_retry_count > 1:
        # 默认重试时间为按时长等分递增
        retry_timeouts = list([idx / max_retry_count * max_retry_wait_time for idx in range_from_one(max_retry_count)])
        if login_retry_data.recommended_first_retry_timeout != 0:
            # 如果有历史成功数据，则以推荐首次重试时间为第一次重试的时间，后续重试次数则等分递增
            retry_timeouts = [login_retry_data.recommended_first_retry_timeout]
            remaining_retry_count = max_retry_count - 1
            retry_timeouts.extend(list([idx / remaining_retry_count * max_retry_wait_time for idx in range_from_one(remaining_retry_count)]))

    return login_retry_data, retry_timeouts


def update_retry_data(retry_key: str, success_timeout: int, recommended_retry_wait_time_change_rate=0.125, debug_ctx=""):
    from dao import RetryData

    # 重新读取数据，避免其他进程已经更新过数据
    db = load_db()
    raw_login_retry_data = db.get(retry_key, {})
    login_retry_data = RetryData().auto_update_config(raw_login_retry_data)

    # 第idx-1次的重试成功了，尝试更新历史数据
    cr = recommended_retry_wait_time_change_rate
    login_retry_data.recommended_first_retry_timeout = (1 - cr) * login_retry_data.recommended_first_retry_timeout + cr * success_timeout
    login_retry_data.history_success_timeouts.append(success_timeout)

    db[retry_key] = to_raw_type(login_retry_data)
    save_db(db)

    if use_by_myself():
        logger.info(color("bold_cyan") + f"(仅我可见){debug_ctx} 本次重试等待时间为{success_timeout}，当前历史重试数据为{login_retry_data}")


def kill_process(pid: int, wait_time=5):
    logger.info(f"尝试干掉原进程={pid}")
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        logger.warning("未找到该pid，也许是早已经杀掉了")

    logger.info(f"等待{wait_time}秒，确保原进程已经被干掉")
    time.sleep(wait_time)


def kill_other_instance_on_start():
    pids_dir = os.path.join(cached_dir, 'pids')
    make_sure_dir_exists(pids_dir)

    old_pids = os.listdir(pids_dir)
    if len(old_pids) != 0:
        logger.info(f"尝试干掉之前的实例: {old_pids}")
        for old_instance_pid in old_pids:
            kill_process(int(old_instance_pid), 1)
            os.remove(os.path.join(pids_dir, old_instance_pid))

    current_pid = os.getpid()
    pid_filename = os.path.join(pids_dir, str(current_pid))
    open(pid_filename, 'w').close()
    logger.info(f"当前pid为{current_pid}")


def append_if_not_in(l: list, v: Any):
    if v not in l:
        l.append(v)


def wait_for(msg: str, seconds):
    logger.info(msg + f", 等待{seconds}秒")
    time.sleep(seconds)


def show_unexpected_exception_message(e: Exception):
    from config import config

    time_since_release = get_now() - parse_time(ver_time, "%Y.%m.%d")
    msg = f"ver {now_version} (发布于{ver_time}，距今已有{time_since_release.days}天啦) 运行过程中出现未捕获的异常，请加群{config().common.qq_group}反馈或自行解决。" + check_some_exception(e)
    logger.exception(color("fg_bold_yellow") + msg, exc_info=e)
    logger.warning(color("fg_bold_cyan") + "如果稳定报错，不妨打开网盘，看看是否有新版本修复了这个问题~")
    logger.warning(color("fg_bold_cyan") + "如果稳定报错，不妨打开网盘，看看是否有新版本修复了这个问题~")
    logger.warning(color("fg_bold_cyan") + "如果稳定报错，不妨打开网盘，看看是否有新版本修复了这个问题~")
    logger.warning(color("fg_bold_yellow") + "不要自动无视上面这三句话哦，写出来是让你看的呀<_<不知道出啥问题的时候就按提示去看看是否有新版本哇，而不是不管三七二十一就来群里问嗷")
    logger.warning(color("fg_bold_cyan") + f"链接：{config().common.netdisk_link}")


def get_pay_server_addr() -> str:
    return "http://139.198.179.81:8438"


def disable_quick_edit_mode():
    # https://docs.microsoft.com/en-us/windows/console/setconsolemode
    def _cb():
        ENABLE_EXTENDED_FLAGS = 0x0080

        logger.info(color("bold_green") + "将禁用命令行的快速编辑模式，避免鼠标误触时程序暂停，若需启用，请去配置文件取消禁用快速编辑模式~")
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(win32api.STD_INPUT_HANDLE), ENABLE_EXTENDED_FLAGS)

    async_call(_cb)


def is_run_in_pycharm() -> bool:
    return os.getenv('PYCHARM_HOSTED') == '1'


def remove_file(file_path):
    if not os.path.isfile(file_path):
        logger.warning(f"文件 {file_path} 不存在")
        return

    try:
        os.remove(file_path)
    except Exception as e:
        logger.error(f"删除文件 {file_path} 失败", exc_info=e)


def remove_directory(directory_path):
    if not os.path.isdir(directory_path):
        logger.warning(f"目录 {directory_path} 不存在")
        return

    try:
        shutil.rmtree(directory_path)
    except Exception as e:
        logger.error(f"删除目录 {directory_path} 失败", exc_info=e)


if __name__ == '__main__':
    print(get_now_unix())
    print(get_this_week_monday())
    print(get_last_week_monday())
    print(get_uuid())
    print(run_from_src())
    print(use_by_myself())
    print(show_end_time("2021-02-23 00:00:00"))
    print(truncate("风之凌殇风之凌殇", 12))
    print(parse_time("2021-02-10 18:55:35") + datetime.timedelta(days=10 * 31))
    print(remove_none_from_list([None, 1, 2, 3, None]))
    print(get_screen_size())
    kill_other_instance_on_start()
