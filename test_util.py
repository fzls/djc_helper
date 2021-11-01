#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------
# File      : test_util
# DateTime  : 2021/8/4 19:07
# Author    : Chen Ji
# Email     : fzls.zju@gmail.com
# -------------------------------
from math import pow

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


def test_get_last_week_monday_datetime():
    last_monday = datetime.datetime.now().replace(2021, 7, 26, 0, 0, 0, 0)
    assert get_last_week_monday_datetime(now_for_test) == last_monday


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
    t1 = get_current()
    time.sleep(1)
    t2 = get_current()
    assert t1 != t2


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
    assert filter_unused_params("a=1=2=3&b=1") == "a=1=2=3&b=1"

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
    assert is_act_expired("2021-08-05 12:00:00", now=now_for_test) is True
    assert is_act_expired("2021-08-06 12:00:00", now=now_for_test) is False
    assert is_act_expired("2021-08-06 12:00:01", now=now_for_test) is False


def test_will_act_expired_in():
    assert will_act_expired_in("2021-08-16 00:00:00", datetime.timedelta(days=10), now=now_for_test) is True
    assert will_act_expired_in("2021-08-17 00:00:00", datetime.timedelta(days=10), now=now_for_test) is False


def test_get_remaining_time():
    assert get_remaining_time("2021-08-17 00:00:00", now=now_for_test) == datetime.timedelta(days=10, hours=12)


def test_get_past_time():
    assert get_past_time("2021-08-05 00:00:00", now=now_for_test) == datetime.timedelta(days=1, hours=12)


def test_time_less():
    assert time_less("2021-08-16 00:00:00", "2021-08-16 00:00:00") is False
    assert time_less("2021-08-16 00:00:00", "2021-08-06 00:00:00") is False
    assert time_less("2021-08-06 00:00:00", "2021-08-16 00:00:00") is True


def test_parse_time():
    assert parse_time("2021-08-06 12:00:00") == now_for_test


def test_parse_timestamp():
    assert parse_timestamp(1628222400.0) == now_for_test


def test_format_time():
    assert format_time(now_for_test) == "2021-08-06 12:00:00"


def test_format_now():
    assert format_now(now=now_for_test) == "2021-08-06 12:00:00"

    nt = format_now()
    time.sleep(1.1)
    nt2 = format_now()
    assert nt != nt2


def test_format_timestamp():
    assert format_timestamp(1628222400.0) == "2021-08-06 12:00:00"


def test_bytes_size():
    assert KiB == int(pow(1024, 1))
    assert MiB == int(pow(1024, 2))
    assert GiB == int(pow(1024, 3))
    assert TiB == int(pow(1024, 4))
    assert PiB == int(pow(1024, 5))
    assert EiB == int(pow(1024, 6))
    assert ZiB == int(pow(1024, 7))
    assert YiB == int(pow(1024, 8))


def test_human_readable_size():
    assert human_readable_size(512) == "512.0B"
    assert human_readable_size(512 * KiB) == "512.0KiB"
    assert human_readable_size(512 * MiB) == "512.0MiB"
    assert human_readable_size(512 * GiB) == "512.0GiB"
    assert human_readable_size(512 * TiB) == "512.0TiB"
    assert human_readable_size(512 * PiB) == "512.0PiB"
    assert human_readable_size(512 * EiB) == "512.0EiB"
    assert human_readable_size(512 * ZiB) == "512.0ZiB"
    assert human_readable_size(512 * YiB) == "512.0YiB"
    assert human_readable_size(51200 * YiB) == "51200.0YiB"


def test_get_random_face():
    assert get_random_face() != ""


def test_remove_invalid_unicode_escape_string():
    escaped = "\\user\\u5982\\u679c\\u8981\\u53cd\\u9988\\uff0c\\u8bf7\\u628a\\u6574\\u4e2a\\u7a97\\u53e3\\u90fd\\u622a\\u56fe\\u4e0b\\u6765- -\\u4e0d\\u8981\\u53ea\\u622a\\u4e00\\u90e8\\u5206"
    unescaped = " user如果要反馈，请把整个窗口都截图下来- -不要只截一部分"
    assert remove_invalid_unicode_escape_string(escaped) == unescaped


def test_parse_unicode_escape_string():
    with pytest.raises(UnicodeDecodeError):
        parse_unicode_escape_string("\\user\\u5982\\u679c")

    assert parse_unicode_escape_string("\\u5982\\u679c") == "如果"


def test_remove_none_from_list():
    assert remove_none_from_list([]) == []
    assert remove_none_from_list([None]) == []
    assert remove_none_from_list([1, None, 2]) == [1, 2]


def test_append_if_not_in():
    assert append_if_not_in([], 1) == [1]
    assert append_if_not_in([1], 1) == [1]
    assert append_if_not_in([0], 1) == [0, 1]


def test_md5():
    assert md5("test") == "098f6bcd4621d373cade4e832627b4f6"
    assert md5("") == "d41d8cd98f00b204e9800998ecf8427e"


def test_get_meaningful_call_point_for_log():
    caller_list = [""]

    def expect_caller():
        check_fake()

    def check_fake():
        fake_op()

    def fake_op():
        process_result()

    def process_result():
        caller_list[0] = get_meaningful_call_point_for_log()

    expect_caller()
    assert caller_list[0].startswith(expect_caller.__name__)


def test_startswith_any():
    assert startswith_any("test", ["123", "te"]) is True
    assert startswith_any("test", ["123", "tttt"]) is False


def test_endswith_any():
    assert endswith_any("test", ["123", "st"]) is True
    assert endswith_any("test", ["123", "tttt"]) is False


def test_extract_between():
    text = """
    var activity_id = '1';
    var lvScore = 66;
    """

    activity_id = extract_between(text, "var activity_id = '", "';", str)
    lv_score = extract_between(text, "var lvScore = ", ";", int)

    assert activity_id == "1"
    assert lv_score == 66


def test_start_and_end_date_of_a_month():
    start_date, end_date = start_and_end_date_of_a_month(now_for_test)
    assert start_date == datetime.datetime(now_for_test.year, now_for_test.month, 1, 0, 0, 0)
    assert end_date == datetime.datetime(now_for_test.year, now_for_test.month, 31, 23, 59, 59)


def test_remove_suffix():
    assert remove_suffix("test_suffix", "_suffix") == "test"
    assert remove_suffix("test_suffix", "not_exist_suffix") == "test_suffix"


def test_get_cid():
    assert get_cid() == get_cid()


def test_parse_scode():
    assert parse_scode("MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=") == "MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0="
    assert parse_scode("https://dnf.qq.com/cp/a20210730care/index.html?sCode=MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=") == "MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0="
    assert parse_scode("https://dnf.qq.com/cp/a20210911care/index.html?sCode=MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=") == "MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0="


def test_bytes_arr_to_hex_str():
    assert bytes_arr_to_hex_str([0x58, 0x59, 0x01, 0x00, 0x00]) == "0x58, 0x59, 0x01, 0x00, 0x00"


def test_hex_str_to_bytes_arr():
    assert hex_str_to_bytes_arr("0x58, 0x59, 0x01, 0x00, 0x00") == [0x58, 0x59, 0x01, 0x00, 0x00]


def test_utf8len():
    assert utf8len("test") == 4
    assert utf8len("测试") == 6
    assert utf8len("test测试") == 10


def test_base64_str():
    assert base64_str("test") == "dGVzdA=="
    assert base64_str("测试") == "5rWL6K+V"
    assert base64_str("&&&=12kjsabdsa") == "JiYmPTEya2pzYWJkc2E="
