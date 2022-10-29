import os
from urllib.parse import quote

import requests

from dao import ConfigInterface, to_raw_type
from util import with_cache

SERVER_ADDR = "http://114.132.252.185:5244"

API_LOGIN = f"{SERVER_ADDR}/api/auth/login"
API_UPLOAD = f"{SERVER_ADDR}/api/fs/put"


class CommonResponse(ConfigInterface):
    def __init__(self):
        self.code = 200
        self.message = "success"
        self.data = {}


def generate_exception(res: CommonResponse, ctx: str) -> Exception:
    return Exception(f"alist {ctx} failed, code={res.code}, message={res.message}")


class LoginRequest(ConfigInterface):
    def __init__(self):
        self.username = ""
        self.password = ""
        self.otp_code = ""


class LoginResponse(ConfigInterface):
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

    res = CommonResponse().auto_update_config(raw_res.json())
    if res.code != 200:
        raise generate_exception(res, "login")

    data = LoginResponse().auto_update_config(res.data)

    return data.token


def upload(local_file_path: str, remote_file_path: str):
    username = os.getenv("ALIST_USERNAME")
    password = os.getenv("ALIST_PASSWORD")

    if not remote_file_path.startswith("/"):
        remote_file_path = "/" + remote_file_path

    with open(local_file_path, "rb") as file_to_upload:
        raw_res = requests.put(API_UPLOAD, data=file_to_upload, headers={
            "File-Path": quote(remote_file_path),
            "As-Task": "false",
            "Authorization": login(username, password),
        })

        res = CommonResponse().auto_update_config(raw_res.json())
        if res.code != 200:
            raise generate_exception(res, "upload")

        print(raw_res.status_code)
        print(raw_res.text)


def demo_login():
    username = os.getenv("ALIST_USERNAME")
    password = os.getenv("ALIST_PASSWORD")

    cached_token = login(username, password)
    print(f"cached_token   = {cached_token}")

    uncached_token = _login(username, password)
    print(f"uncached_token = {uncached_token}")


def demo_upload():
    upload(
        "C:/Users/fzls/Downloads/Everything-1.4.1.1022.x64-Setup.exe",
        "/Everything-1.4.1.1022.x64-Setup.exe",
    )


if __name__ == '__main__':
    # demo_login()
    demo_upload()
