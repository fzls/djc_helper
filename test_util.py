#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------
# File      : test_util
# DateTime  : 2021/8/4 19:07
# Author    : Chen Ji
# Email     : fzls.zju@gmail.com
# -------------------------------
from util import *


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


