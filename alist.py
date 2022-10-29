import os

import requests

from dao import ConfigInterface, to_raw_type
from util import with_cache

SERVER_ADDR = "http://114.132.252.185:5244"

API_LOGIN = f"{SERVER_ADDR}/api/auth/login"


class LoginRequest(ConfigInterface):
    def __init__(self):
        self.username = ""
        self.password = ""
        self.otp_code = ""


class LoginResponse(ConfigInterface):
    def __init__(self):
        self.code = 200
        self.message = "success"
        self.data = LoginResponseData()


class LoginResponseData(ConfigInterface):
    def __init__(self):
        self.token = ""


def login(username: str, password: str, otp_code: str = "") -> str:
    """
    登录alist，获取上传所需token
    """
    return with_cache(
        "alist",
        "login",
        cache_max_seconds=24 * 60 * 60,
        cache_miss_func=lambda: _login(username, password, otp_code)
    )


def _login(username: str, password: str, otp_code: str = "") -> str:
    req = LoginRequest()
    req.username = username
    req.password = password
    req.otp_code = otp_code

    raw_res = requests.post(API_LOGIN, json=to_raw_type(req))

    res = LoginResponse().auto_update_config(raw_res.json())

    if res.code != 200:
        raise Exception(f"alist login failed, code={res.code}, message={res.message}")

    return res.data.token


def demo_login():
    username = os.getenv("ALIST_USERNAME")
    password = os.getenv("ALIST_PASSWORD")

    cached_token = login(username, password)
    print(f"cached_token   = {cached_token}")

    uncached_token = _login(username, password)
    print(f"uncached_token = {uncached_token}")


if __name__ == '__main__':
    demo_login()
