#!/usr/bin/env python
# -------------------------------
# File      : test_util
# DateTime  : 2021/8/4 19:07
# Author    : Chen Ji
# Email     : fzls.zju@gmail.com
# -------------------------------
import datetime
import os
import random
import socket
import time
from math import pow

import pytest
import selenium.common.exceptions

from db import CacheDB
from network import set_last_response_info
from util import (
    EiB,
    GiB,
    KiB,
    MiB,
    PiB,
    TiB,
    YiB,
    ZiB,
    append_if_not_in,
    base64_decode,
    base64_encode,
    bytes_arr_to_hex_str,
    check_some_exception,
    endswith_any,
    extract_between,
    filter_unused_params,
    format_now,
    format_time,
    format_timestamp,
    generate_raw_data_template,
    get_cid,
    get_current,
    get_first_exists_dict_value,
    get_last_month,
    get_last_n_days,
    get_last_week_monday,
    get_last_week_monday_datetime,
    get_meaningful_call_point_for_log,
    get_month,
    get_now,
    get_now_unix,
    get_past_time,
    get_random_face,
    get_remaining_time,
    get_this_thursday_of_dnf,
    get_this_week_monday,
    get_this_week_monday_datetime,
    get_today,
    get_uuid,
    get_week,
    get_year,
    hex_str_to_bytes_arr,
    human_readable_size,
    is_act_expired,
    is_valid_qq,
    md5,
    now_after,
    now_before,
    now_in_range,
    padLeftRight,
    parse_scode,
    parse_time,
    parse_timestamp,
    parse_unicode_escape_string,
    parse_url_param,
    post_json_to_data,
    printed_width,
    remove_invalid_unicode_escape_string,
    remove_none_from_list,
    remove_prefix,
    remove_suffix,
    start_and_end_date_of_a_month,
    startswith_any,
    tableify,
    time_less,
    truncate,
    try_except,
    uin2qq,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
    use_by_myself,
    utf8len,
    will_act_expired_in,
    with_cache,
)

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


def test_get_this_thursday_of_dnf():
    test_week_4_5 = datetime.datetime.now().replace(2021, 11, 18, 5, 0, 0, 0)
    test_week_4_6 = datetime.datetime.now().replace(2021, 11, 18, 6, 0, 0, 0)
    test_week_4 = datetime.datetime.now().replace(2021, 11, 18, 12, 0, 0, 0)
    test_week_5 = datetime.datetime.now().replace(2021, 11, 19, 12, 0, 0, 0)

    expect_week_4 = datetime.datetime.now().replace(2021, 11, 18, 0, 0, 0, 0)

    assert get_this_thursday_of_dnf(test_week_4_5) == expect_week_4
    assert get_this_thursday_of_dnf(test_week_4_6) == expect_week_4
    assert get_this_thursday_of_dnf(test_week_4) == expect_week_4
    assert get_this_thursday_of_dnf(test_week_5) == expect_week_4

    test_week_2 = datetime.datetime.now().replace(2021, 11, 16, 12, 0, 0, 0)
    expect_last_week_4 = datetime.datetime.now().replace(2021, 11, 11, 0, 0, 0, 0)
    assert get_this_thursday_of_dnf(test_week_2) == expect_last_week_4


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
    assert get_last_n_days(3, now_for_test) == ["20210805", "20210804", "20210803"]


def test_get_week():
    assert get_week(now_for_test) == "2021-week-31"


def test_get_month():
    assert get_month(now_for_test) == "202108"


def test_get_last_month():
    assert get_last_month(now_for_test) == "202107"


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

    with pytest.raises(ValueError):
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


def test_with_cache():
    test_category = f"test_with_cache_category_{time.time()}_{random.random()}"
    cache_duration = 2

    def f() -> float:
        return get_now().timestamp()

    test_key = f"test_with_cache_key_{random.random()}"
    c1 = with_cache(test_category, test_key, f, cache_max_seconds=cache_duration)
    time.sleep(1.2 * cache_duration)
    c2 = with_cache(test_category, test_key, f, cache_max_seconds=cache_duration)
    assert c1 != c2


def test_with_cache_v2():
    test_category = f"test_with_cache_category_{time.time()}_{random.random()}"
    cache_duration = 2

    def f() -> float:
        time.sleep(0.05)
        return get_now().timestamp()

    test_key = f"test_with_cache_key_{random.random()}"

    # 先触发一次cache miss
    c1 = with_cache(test_category, test_key, f, cache_max_seconds=cache_duration)

    # 移除_update字段，模拟上个版本的存盘记录
    db = CacheDB().with_context(test_category).load()
    db_info = db.cache[test_key]
    db_info.update_at = db_info._update_at
    delattr(db_info, "_update_at")
    db.save()

    # 再次调用，此时应当重新触发cache miss
    c2 = with_cache(test_category, test_key, f, cache_max_seconds=cache_duration)

    assert c1 != c2


def test_with_cache_continued():
    test_category = f"test_with_cache_category_{time.time()}_{random.random()}"
    cache_duration = 2

    def f() -> float:
        return get_now().timestamp()

    test_key = f"test_with_cache_key_{random.random()}"
    c1 = with_cache(test_category, test_key, f, cache_max_seconds=cache_duration)
    time.sleep(0.6 * cache_duration)
    c2 = with_cache(test_category, test_key, f, cache_max_seconds=cache_duration)
    time.sleep(0.6 * cache_duration)
    c3 = with_cache(test_category, test_key, f, cache_max_seconds=cache_duration)
    assert c1 == c2
    assert c1 != c3


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


def test_remove_prefix():
    assert remove_prefix("prefix_test", "prefix_") == "test"
    assert remove_prefix("prefix_test", "not_exist_prefix") == "prefix_test"


def test_remove_suffix():
    assert remove_suffix("test_suffix", "_suffix") == "test"
    assert remove_suffix("test_suffix", "not_exist_suffix") == "test_suffix"


def test_get_cid():
    assert get_cid() == get_cid()


def test_parse_scode():
    assert (
        parse_scode("MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=")
        == "MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0="
    )
    assert (
        parse_scode(
            "https://dnf.qq.com/cp/a20210730care/index.html?sCode=MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0="
        )
        == "MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0="
    )
    assert (
        parse_scode(
            "https://dnf.qq.com/cp/a20210911care/index.html?sCode=MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0="
        )
        == "MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0="
    )


def test_bytes_arr_to_hex_str():
    assert bytes_arr_to_hex_str([0x58, 0x59, 0x01, 0x00, 0x00]) == "0x58, 0x59, 0x01, 0x00, 0x00"


def test_hex_str_to_bytes_arr():
    assert hex_str_to_bytes_arr("0x58, 0x59, 0x01, 0x00, 0x00") == [0x58, 0x59, 0x01, 0x00, 0x00]


def test_utf8len():
    assert utf8len("test") == 4
    assert utf8len("测试") == 6
    assert utf8len("test测试") == 10


def test_base64_encode():
    assert base64_encode("test") == "dGVzdA=="
    assert base64_encode("测试") == "5rWL6K+V"
    assert base64_encode("&&&=12kjsabdsa") == "JiYmPTEya2pzYWJkc2E="
    assert base64_encode("广西一区") == "5bm/6KW/5LiA5Yy6"
    assert base64_encode("游戏领域大神") == "5ri45oiP6aKG5Z+f5aSn56We"


def test_base64_decode():
    assert base64_decode("dGVzdA==") == "test"
    assert base64_decode("5rWL6K+V") == "测试"
    assert base64_decode("JiYmPTEya2pzYWJkc2E=") == "&&&=12kjsabdsa"
    assert base64_decode("5bm/6KW/5LiA5Yy6") == "广西一区"
    assert base64_decode("5ri45oiP6aKG5Z+f5aSn56We") == "游戏领域大神"


def test_urlsafe_base64_encode():
    assert urlsafe_base64_encode("test") == "dGVzdA=="
    assert urlsafe_base64_encode("测试") == "5rWL6K-V"
    assert urlsafe_base64_encode("&&&=12kjsabdsa") == "JiYmPTEya2pzYWJkc2E="
    assert urlsafe_base64_encode("广西一区") == "5bm_6KW_5LiA5Yy6"
    assert urlsafe_base64_encode("游戏领域大神") == "5ri45oiP6aKG5Z-f5aSn56We"


def test_urlsafe_base64_decode():
    assert urlsafe_base64_decode("dGVzdA==") == "test"
    assert urlsafe_base64_decode("5rWL6K+V") == "测试"
    assert urlsafe_base64_decode("JiYmPTEya2pzYWJkc2E=") == "&&&=12kjsabdsa"
    assert urlsafe_base64_decode("5bm_6KW_5LiA5Yy6") == "广西一区"
    assert urlsafe_base64_decode("5ri45oiP6aKG5Z-f5aSn56We") == "游戏领域大神"


def test_post_json_to_data():
    assert post_json_to_data({}) == ""
    assert post_json_to_data({"k": "v"}) == "k=v"
    assert post_json_to_data({"k1": "v1", "k2": "v2"}) == "k1=v1&k2=v2"


def test_generate_raw_data_template():
    assert generate_raw_data_template([]) == ""
    assert generate_raw_data_template(["a"]) == "a={a}"
    assert generate_raw_data_template(["a", "b", "c"]) == "a={a}&b={b}&c={c}"

    # fmt: off

    # 以下为改造为新的写法时，新版与旧版的数据
    # 新写法
    amesvr_default_params_list = [
        "iActivityId", "g_tk", "iFlowId", "package_id", "lqlevel", "teamid", "weekDay", "eas_url", "sServiceDepartment", "sServiceType", "sArea", "sRoleId", "uin", "userId", "token", "sRoleName",
        "serverId", "areaId", "skey", "nickName", "date", "dzid", "page", "iPackageId", "plat", "extraStr", "sContent", "sPartition", "sAreaName", "md5str", "ams_md5str", "ams_checkparam",
        "checkparam", "type", "moduleId", "giftId", "acceptId", "invitee", "giftNum", "sendQQ", "receiver", "receiverName", "inviterName", "user_area", "user_partition", "user_areaName",
        "user_roleId", "user_roleName", "user_roleLevel", "user_checkparam", "user_md5str", "user_sex", "user_platId", "cz", "dj", "siActivityId", "needADD", "dateInfo", "sId", "userNum",
        "cardType", "inviteId", "sendName", "receiveUin", "receiverUrl", "index", "pageNow", "pageSize", "clickTime", "username", "petId", "skin_id", "decoration_id", "fuin", "sCode", "sNickName",
        "iId", "sendPage", "hello_id", "prize", "qd", "iReceiveUin", "map1", "map2", "len", "itemIndex", "sRole", "loginNum", "level", "inviteUin", "iGuestUin", "ukey", "iGiftID", "iInviter",
        "iPageNow", "iPageSize", "iType", "iWork", "iPage", "sNick", "iMatchId", "iGameId", "iIPId", "iVoteId", "iResult", "personAct", "teamAct", "param", "dhnums", "sUin", "pointID", "workId",
        "isSort", "jobName", "title", "actSign", "iNum", "prefer", "card", "answer1", "answer2", "answer3", "countsInfo", "power", "crossTime", "getLv105", "use_fatigue", "exchangeId", "sChannel",
        "pass", "pass_date", "bossId", "today", "anchor", "sNum", "week", "position", "packages", "selectNo", "targetQQ", "u_confirm",
    ]
    amesvr_raw_data = "xhrPostKey=xhr_{millseconds}&eas_refer=http%3A%2F%2Fnoreferrer%2F%3Freqid%3D{uuid}%26version%3D23&e_code=0&g_code=0&xhr=1" + "&" + generate_raw_data_template(amesvr_default_params_list)
    # 旧写法
    amesvr_raw_data_old_version = (
        "iActivityId={iActivityId}&g_tk={g_tk}&iFlowId={iFlowId}&package_id={package_id}&xhrPostKey=xhr_{millseconds}&eas_refer=http%3A%2F%2Fnoreferrer%2F%3Freqid%3D{uuid}%26version%3D23&lqlevel={lqlevel}"
        "&teamid={teamid}&weekDay={weekDay}&e_code=0&g_code=0&eas_url={eas_url}&xhr=1&sServiceDepartment={sServiceDepartment}&sServiceType={sServiceType}&sArea={sArea}&sRoleId={sRoleId}&uin={uin}"
        "&userId={userId}&token={token}&sRoleName={sRoleName}&serverId={serverId}&areaId={areaId}&skey={skey}&nickName={nickName}&date={date}&dzid={dzid}&page={page}&iPackageId={iPackageId}&plat={plat}"
        "&extraStr={extraStr}&sContent={sContent}&sPartition={sPartition}&sAreaName={sAreaName}&md5str={md5str}&ams_md5str={ams_md5str}&ams_checkparam={ams_checkparam}&checkparam={checkparam}&type={type}&moduleId={moduleId}"
        "&giftId={giftId}&acceptId={acceptId}&invitee={invitee}&giftNum={giftNum}&sendQQ={sendQQ}&receiver={receiver}&receiverName={receiverName}&inviterName={inviterName}&user_area={user_area}"
        "&user_partition={user_partition}&user_areaName={user_areaName}&user_roleId={user_roleId}&user_roleName={user_roleName}&user_roleLevel={user_roleLevel}&user_checkparam={user_checkparam}"
        "&user_md5str={user_md5str}&user_sex={user_sex}&user_platId={user_platId}&cz={cz}&dj={dj}&siActivityId={siActivityId}&needADD={needADD}&dateInfo={dateInfo}&sId={sId}&userNum={userNum}"
        "&cardType={cardType}&inviteId={inviteId}&sendName={sendName}&receiveUin={receiveUin}&receiverUrl={receiverUrl}&index={index}&pageNow={pageNow}&pageSize={pageSize}&clickTime={clickTime}"
        "&username={username}&petId={petId}&skin_id={skin_id}&decoration_id={decoration_id}&fuin={fuin}&sCode={sCode}&sNickName={sNickName}&iId={iId}&sendPage={sendPage}&hello_id={hello_id}"
        "&prize={prize}&qd={qd}&iReceiveUin={iReceiveUin}&map1={map1}&map2={map2}&len={len}&itemIndex={itemIndex}&sRole={sRole}&loginNum={loginNum}&level={level}&inviteUin={inviteUin}"
        "&iGuestUin={iGuestUin}&ukey={ukey}&iGiftID={iGiftID}&iInviter={iInviter}&iPageNow={iPageNow}&iPageSize={iPageSize}&iType={iType}&iWork={iWork}&iPage={iPage}&sNick={sNick}"
        "&iMatchId={iMatchId}&iGameId={iGameId}&iIPId={iIPId}&iVoteId={iVoteId}&iResult={iResult}&personAct={personAct}&teamAct={teamAct}&param={param}&dhnums={dhnums}&sUin={sUin}&pointID={pointID}"
        "&workId={workId}&isSort={isSort}&jobName={jobName}&title={title}&actSign={actSign}&iNum={iNum}&prefer={prefer}&card={card}&answer1={answer1}&answer2={answer2}&answer3={answer3}"
        "&countsInfo={countsInfo}&power={power}&crossTime={crossTime}&getLv105={getLv105}&use_fatigue={use_fatigue}&exchangeId={exchangeId}&sChannel={sChannel}&pass={pass}&pass_date={pass_date}"
        "&bossId={bossId}&today={today}&anchor={anchor}&sNum={sNum}&week={week}&position={position}&packages={packages}&selectNo={selectNo}&targetQQ={targetQQ}&u_confirm={u_confirm}"
    )
    # 需要确保此时使用该函数生成的结果与原来是等价的（也就是基于 & 分割后的列表经过排序后完全一致）
    assert sorted(amesvr_raw_data.split("&")) == sorted(amesvr_raw_data_old_version.split("&"))

    # 同样的，下面是ide活动参数改造时的测试数据
    ide_default_params_list = [
        "iChartId", "iSubChartId", "sIdeToken", "sRoleId", "sRoleName", "sArea", "sMd5str", "sCheckparam", "roleJob", "sAreaName", "sAuthInfo", "sActivityInfo", "openid", "sCode", "startPos",
        "eas_url", "eas_refer", "iType", "iPage", "type", "sUin", "dayNum", "iFarmland", "fieldId", "sRice", "packageId", "targetId", "myId", "id", "iCardId", "iAreaId", "sRole", "drinksId",
        "gameId", "score", "loginDays", "iSuccess", "iGameId", "sAnswer", "index", "u_stage", "u_task_index", "u_stage_index", "num", "sPartition", "sPlatId", "source",
    ]
    ide_raw_data = "e_code=0&g_code=0" + "&" + generate_raw_data_template(ide_default_params_list)
    ide_raw_data_old_version = (
        "iChartId={iChartId}&iSubChartId={iSubChartId}&sIdeToken={sIdeToken}"
        "&sRoleId={sRoleId}&sRoleName={sRoleName}&sArea={sArea}&sMd5str={sMd5str}&sCheckparam={sCheckparam}&roleJob={roleJob}&sAreaName={sAreaName}"
        "&sAuthInfo={sAuthInfo}&sActivityInfo={sActivityInfo}&openid={openid}&sCode={sCode}&startPos={startPos}"
        "&e_code=0&g_code=0&eas_url={eas_url}&eas_refer={eas_refer}&iType={iType}&iPage={iPage}&type={type}&sUin={sUin}&dayNum={dayNum}"
        "&iFarmland={iFarmland}&fieldId={fieldId}&sRice={sRice}&packageId={packageId}&targetId={targetId}&myId={myId}&id={id}"
        "&iCardId={iCardId}&iAreaId={iAreaId}&sRole={sRole}&drinksId={drinksId}&gameId={gameId}&score={score}&loginDays={loginDays}"
        "&iSuccess={iSuccess}&iGameId={iGameId}&sAnswer={sAnswer}&index={index}&u_stage={u_stage}&u_task_index={u_task_index}&u_stage_index={u_stage_index}&num={num}"
        "&sPartition={sPartition}&sPlatId={sPlatId}&source={source}"
    )
    assert sorted(ide_raw_data.split("&")) == sorted(ide_raw_data_old_version.split("&"))

    # 将原来的空值默认中中包含在上面两个列表中的移除，得到剩余部分。确保这个与ame和ide的合集中，包含原来默认空值的全部值（允许超出，因为ame和ide中部分值是在调用时传入，或者是有值的默认值）
    other_default_params_list = [
        "iActionId", "iGoodsId", "sBizCode", "partition", "iZoneId", "platid", "sZoneDesc", "sGetterDream", "isLock", "amsid", "iLbSel1", "mold", "exNum", "iCard", "actionId",
        "adLevel", "adPower", "pUserId", "isBind", "toUin", "appid", "appOpenid", "accessToken", "iRoleId", "randomSeed", "taskId", "point", "cRand", "tghappid", "sig",
        "date_chronicle_sign_in", "flow_id",
    ]
    default_params_list_old_version = [
        "package_id", "lqlevel", "teamid", "weekDay", "sArea", "serverId", "areaId", "nickName", "sRoleId", "sRoleName", "uin", "skey", "userId", "token", "iActionId", "iGoodsId", "sBizCode",
        "partition", "iZoneId", "platid", "sZoneDesc", "sGetterDream", "dzid", "page", "iPackageId", "isLock", "amsid", "iLbSel1", "num", "mold", "exNum", "iCard", "iNum", "actionId", "plat",
        "extraStr", "sContent", "sPartition", "sAreaName", "md5str", "ams_md5str", "ams_checkparam", "checkparam", "type", "moduleId", "giftId", "acceptId", "sendQQ", "cardType", "giftNum",
        "inviteId", "inviterName", "sendName", "invitee", "receiveUin", "receiver", "receiverName", "receiverUrl", "inviteUin", "user_area", "user_partition", "user_areaName", "user_roleId",
        "user_roleName", "user_roleLevel", "user_checkparam", "user_md5str", "user_sex", "user_platId", "cz", "dj", "siActivityId", "needADD", "dateInfo", "sId", "userNum", "index", "pageNow",
        "pageSize", "clickTime", "skin_id", "decoration_id", "adLevel", "adPower", "username", "petId", "fuin", "sCode", "sNickName", "iId", "sendPage", "hello_id", "prize", "qd", "iReceiveUin",
        "map1", "map2", "len", "itemIndex", "sRole", "loginNum", "level", "iGuestUin", "ukey", "iGiftID", "iInviter", "iPageNow", "iPageSize", "pUserId", "isBind", "iType", "iWork", "iPage",
        "sNick", "iMatchId", "iGameId", "iIPId", "iVoteId", "iResult", "personAct", "teamAct", "sRoleId", "sRoleName", "sArea", "sMd5str", "sCheckparam", "roleJob", "sAreaName", "sAuthInfo",
        "sActivityInfo", "openid", "param", "dhnums", "sUin", "pointID", "startPos", "workId", "isSort", "jobName", "title", "toUin", "actSign", "prefer", "card", "answer1", "answer2", "answer3",
        "countsInfo", "power", "appid", "appOpenid", "accessToken", "iAreaId", "iRoleId", "randomSeed", "taskId", "point", "cRand", "tghappid", "sig", "date_chronicle_sign_in", "crossTime",
        "getLv105", "use_fatigue", "dayNum", "iFarmland", "fieldId", "sRice", "exchangeId", "sChannel", "flow_id", "pass", "pass_date", "packageId", "targetId", "myId", "id", "bossId", "iCardId",
        "today", "anchor", "sNum", "week", "position", "packages", "selectNo", "targetQQ", "drinksId", "gameId", "score", "loginDays", "iSuccess", "sAnswer", "u_stage", "u_task_index",
        "u_stage_index", "u_confirm", "sPlatId", "source",
    ]

    new_union = set().union(set(other_default_params_list), set(amesvr_default_params_list), set(ide_default_params_list))
    old_default_set = set(default_params_list_old_version)
    # 确保旧的默认值集合是新合集的子集
    assert new_union.intersection(old_default_set) == old_default_set

    # fmt: on


def test_parse_url_param():
    a = "1"
    b = "test"
    c = "~~~"
    url = f"https://example.com?a={a}&b={b}&c={c}"

    assert parse_url_param(url, "a") == a
    assert parse_url_param(url, "b") == b
    assert parse_url_param(url, "c") == c


def test_get_first_exists_dict_value():
    old_k = "k1"
    new_k = "K1"
    kv = {
        old_k: old_k,
    }

    assert get_first_exists_dict_value(kv, old_k) == old_k
    assert get_first_exists_dict_value(kv, new_k) is None

    del kv[old_k]
    kv[new_k] = old_k
    assert get_first_exists_dict_value(kv, old_k) is None
    assert get_first_exists_dict_value(kv, new_k) == old_k


def test_define_table_using_zip():
    heads = ["head1", "head2", "head3"]
    colSizes = [1, 2, 3]

    heads_new, colSizes_new = zip(
        ("head1", 1),
        ("head2", 2),
        ("head3", 3),
    )

    assert heads == list(heads_new)
    assert colSizes == list(colSizes_new)
