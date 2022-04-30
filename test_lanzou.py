from lanzou.api import LanZouCloud
from lanzou.api.utils import is_file_url, is_folder_url, time_format
from util import parse_time


def test_is_file_url():
    # 确保每个备案的域名都能正确判定
    for domain in LanZouCloud().available_domains:
        assert is_file_url(f"https://pan.{domain}/i1234abcd")


def test_is_folder_url():
    # 确保每个备案的域名都能正确判定
    for domain in LanZouCloud().available_domains:
        assert is_folder_url(f"https://pan.{domain}/b1234abcd")


def test_time_format():
    # fix: 原先这里会直接返回 2022-03-25 ，与预期不符
    time_str = time_format("2022-03-25")
    parse_time(time_str, "%Y-%m-%d %H:%M:%S")
