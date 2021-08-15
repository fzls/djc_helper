#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------
# File      : test_util
# DateTime  : 2021/8/4 19:07
# Author    : Chen Ji
# Email     : fzls.zju@gmail.com
# -------------------------------
import pytest

from network import set_last_response_info
from util import *

now_for_test = datetime.datetime.now().replace(2021, 8, 6, 12, 0, 0, 0)


def test_uin2qq():
    assert uin2qq("o1234567890") == "1234567890"
    assert uin2qq("o0123456789") == "123456789"


def test_is_valid_qq():
    assert is_valid_qq("123456789")
    assert not is_valid_qq("a123456789")
    assert not is_valid_qq("")


def test_printed_width():
    assert printed_width("test") == 4
    assert printed_width("测试内容") == 8
    assert printed_width("123") == 3
    assert printed_width("测试内容123test") == 15


def test_truncate():
    assert truncate("测试内容123test", 20) == "测试内容123test"
    assert truncate("测试内容123test", 11) == "测试内容..."
    assert truncate("测试内容123test", 8) == "测试..."
    assert truncate("测试内容123test", 4) == "..."


def test_pad_left_right():
    assert padLeftRight("test", 4) == "test"
    assert padLeftRight("test", 8) == "  test  "
    assert padLeftRight("test", 8, pad_char="-") == "--test--"
    assert padLeftRight("test", 8, mode="left") == "test    "
    assert padLeftRight("test", 8, mode="right") == "    test"
    assert padLeftRight("tests", 4, need_truncate=True) == "t..."


def test_tableify():
    assert tableify(["test", "测试内容"], [8, 6], need_truncate=True) == "  test   测... "


def test_get_this_week_monday():
    assert get_this_week_monday(now_for_test) == "20210802"


def test_get_last_week_monday():
    assert get_last_week_monday(now_for_test) == "20210726"


def test_get_this_week_monday_datetime():
    monday = datetime.datetime.now().replace(2021, 8, 2, 0, 0, 0, 0)
    assert get_this_week_monday_datetime(now_for_test) == monday


def test_get_now():
    assert type(get_now()) is datetime.datetime


def test_now_before():
    assert now_before("9999-01-01 00:00:00")


def test_now_after():
    assert now_after("2000-01-01 00:00:00")


def test_now_in_range():
    assert now_in_range("2000-01-01 00:00:00", "9999-01-01 00:00:00")


def test_get_now_unix():
    assert get_now_unix(now_for_test) == 1628222400


def test_get_current():
    assert get_current(now_for_test) == "20210806120000"


def test_get_today():
    assert get_today(now_for_test) == "20210806"


def test_get_last_n_days():
    assert get_last_n_days(3, now_for_test) == ['20210805', '20210804', '20210803']


def test_get_week():
    assert get_week(now_for_test) == "2021-week-31"


def test_get_month():
    assert get_month(now_for_test) == "202108"


def test_get_year():
    assert get_year(now_for_test) == "2021"


def test_filter_unused_params():
    assert filter_unused_params("https://www.example.com/index") == "https://www.example.com/index"
    assert filter_unused_params("https://www.example.com/index?a=1&b=2") == "https://www.example.com/index?a=1&b=2"
    assert filter_unused_params("www.example.com/index?a=1&b=2") == "www.example.com/index?a=1&b=2"
    assert filter_unused_params("index?a=1&b=2") == "index?a=1&b=2"
    assert filter_unused_params("index?a=1&b=&c=3") == "index?a=1&c=3"
    assert filter_unused_params("index?a=&b=&c=") == "index"
    assert filter_unused_params("index?") == "index"
    assert filter_unused_params("a=1&b=2&c=3") == "a=1&b=2&c=3"
    assert filter_unused_params("a=&b=&c=") == ""

    with pytest.raises(Exception):
        filter_unused_params("a&b&c")


def test_get_uuid():
    first_call_result = get_uuid()
    second_call_result = get_uuid()
    assert first_call_result == second_call_result


def test_use_by_myself():
    assert use_by_myself() == os.path.exists(".use_by_myself")


def test_try_except():
    return_on_ok = 1
    return_on_fail = -1

    @try_except(show_exception_info=False, return_val_on_except=return_on_fail)
    def raise_exception(need_raise=True) -> int:
        if need_raise:
            raise Exception()

        return return_on_ok

    assert raise_exception(True) == return_on_fail
    assert raise_exception(False) == return_on_ok


def test_check_some_exception():
    assert check_some_exception(Exception()) == ""
    assert check_some_exception(KeyError("modRet")) != ""
    assert check_some_exception(socket.timeout()) != ""
    assert check_some_exception(selenium.common.exceptions.TimeoutException()) != ""
    assert check_some_exception(PermissionError()) != ""

    set_last_response_info(200, "test", "测试内容")
    assert check_some_exception(Exception(), show_last_process_result=True) != ""


def test_is_act_expired():
    assert is_act_expired("2000-02-23 23:59:59", "%Y-%m-%d %H:%M:%S") is True
    assert is_act_expired("9021-02-23 23:59:59", "%Y-%m-%d %H:%M:%S") is False
