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


def test_extract_between():
    text = """
    var activity_id = '1';
    var lvScore = 66;
    """

    activity_id = extract_between(text, "var activity_id = '", "';", str)
    lv_score = extract_between(text, "var lvScore = ", ";", int)

    assert activity_id == "1"
    assert lv_score == 66
