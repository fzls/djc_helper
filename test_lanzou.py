from lanzou.api import LanZouCloud
from lanzou.api.utils import is_file_url, is_folder_url


def test_is_file_url():
    # 确保每个备案的域名都能正确判定
    for domain in LanZouCloud().available_domains:
        assert is_file_url(f"https://pan.{domain}/i1234abcd")


def test_is_folder_url():
    # 确保每个备案的域名都能正确判定
    for domain in LanZouCloud().available_domains:
        assert is_folder_url(f"https://pan.{domain}/b1234abcd")
