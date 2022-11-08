from __future__ import annotations

import os
from urllib.parse import quote

import requests

from dao import ConfigInterface, to_raw_type
from log import color, logger
from util import get_now, human_readable_size, with_cache

SERVER_ADDR = "http://114.132.252.185:5244"

API_LOGIN = f"{SERVER_ADDR}/api/auth/login"
API_UPLOAD = f"{SERVER_ADDR}/api/fs/put"
API_LIST = f"{SERVER_ADDR}/api/fs/list"
API_REMOVE = f"{SERVER_ADDR}/api/fs/remove"


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


class ListRequest(ConfigInterface):
    def __init__(self):
        self.path = ""
        self.passwrod = ""
        self.refresh = False
        self.page = 1
        self.per_page = 0


class ListResponse(ConfigInterface):
    def __init__(self):
        self.provider = "189Cloud"
        self.readme = ""
        self.write = True
        self.total = 3
        self.content: list[Content] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("content", Content),
        ]


class Content(ConfigInterface):
    def __init__(self):
        self.name = "自制小工具"
        self.size = 0
        self.is_dir = True
        self.modified = "2022-10-28T10:38:13+08:00"
        self.sign = ""
        self.thumb = ""
        self.type = 1


class RemoveRequest(ConfigInterface):
    def __init__(self):
        self.dir = "/"
        self.names: list[str] = []


def login(username: str, password: str, otp_code: str = "") -> str:
    """
    登录alist，获取上传所需token
    """
    return with_cache(
        "alist", "login", cache_max_seconds=24 * 60 * 60, cache_miss_func=lambda: _login(username, password, otp_code)
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


def format_remote_file_path(remote_file_path: str) -> str:
    """
    确保远程路径以 / 开头
    """
    if not remote_file_path.startswith("/"):
        remote_file_path = "/" + remote_file_path

    return remote_file_path


def upload(local_file_path: str, remote_file_path: str = "", old_version_name_prefix: str = ""):
    if remote_file_path == "":
        remote_file_path = os.path.basename(local_file_path)

    remote_file_path = format_remote_file_path(remote_file_path)

    actual_size = os.stat(local_file_path).st_size
    file_size = human_readable_size(actual_size)

    logger.info(f"开始上传 {local_file_path} ({file_size}) 到网盘，远程路径为 {remote_file_path}")

    remote_dir = os.path.dirname(remote_file_path)
    if old_version_name_prefix != "":
        logger.info(f"将移除网盘目录 {remote_dir} 中 前缀为 {old_version_name_prefix} 的文件")
        dir_file_list_info = get_file_list(remote_dir, refresh=True)
        for file_info in dir_file_list_info.content:
            if file_info.is_dir:
                continue

            if not file_info.name.startswith(old_version_name_prefix):
                continue

            remove(os.path.join(remote_dir, file_info.name))

        logger.info("旧版本处理完毕，将开始实际上传流程")

    start_time = get_now()

    with open(local_file_path, "rb") as file_to_upload:
        raw_res = requests.put(
            API_UPLOAD,
            data=file_to_upload,
            headers={
                "File-Path": quote(remote_file_path),
                "As-Task": "false",
                "Authorization": login_using_env(),
            },
        )

        res = CommonResponse().auto_update_config(raw_res.json())
        if res.code != 200:
            raise generate_exception(res, "upload")

    end_time = get_now()
    used_time = end_time - start_time

    speed = actual_size / used_time.total_seconds()
    human_readable_speed = human_readable_size(speed)

    logger.info(color("bold_yellow") + f"上传完成，耗时 {used_time}({human_readable_speed}/s)")

    logger.info("上传完毕后强制刷新该目录，确保后续访问可以看到新文件")
    get_file_list(remote_dir, refresh=True)


def get_download_url(remote_file_path: str):
    remote_file_path = format_remote_file_path(remote_file_path)

    return f"{SERVER_ADDR}/d{remote_file_path}"


def get_file_list(
    remote_dir_path: str, password: str = "", page: int = 1, per_page: int = 0, refresh=False
) -> ListResponse:
    req = ListRequest()
    req.path = remote_dir_path
    req.passwrod = password
    req.page = page
    req.per_page = per_page
    req.refresh = refresh

    headers = {}
    if refresh:
        # 刷新需要token
        headers = {
            "Authorization": login_using_env(),
        }

    raw_res = requests.post(API_LIST, json=to_raw_type(req), headers=headers)

    res = CommonResponse().auto_update_config(raw_res.json())
    if res.code != 200:
        raise generate_exception(res, "list")

    data = ListResponse().auto_update_config(res.data)

    return data


def remove(remote_file_path: str):
    remote_file_path = format_remote_file_path(remote_file_path)

    dir = os.path.dirname(remote_file_path)
    file_name = os.path.basename(remote_file_path)

    logger.info(f"开始删除网盘文件 {remote_file_path}")

    req = RemoveRequest()
    req.path = dir
    req.names = [
        file_name,
    ]

    raw_res = requests.post(
        API_REMOVE,
        json=to_raw_type(req),
        headers={
            "Authorization": login_using_env(),
        },
    )

    res = CommonResponse().auto_update_config(raw_res.json())
    if res.code != 200:
        raise generate_exception(res, "remove")

    logger.info(color("bold_yellow") + "删除完成")


def login_using_env() -> str:
    username = str(os.getenv("ALIST_USERNAME"))
    password = str(os.getenv("ALIST_PASSWORD"))

    return login(username, password)


def demo_login():
    username = os.getenv("ALIST_USERNAME")
    password = os.getenv("ALIST_PASSWORD")

    cached_token = login(username, password)
    logger.info(f"cached_token   = {cached_token}")

    uncached_token = _login(username, password)
    logger.info(f"uncached_token = {uncached_token}")


def demo_upload():
    upload(
        "C:/Users/fzls/Downloads/chromedriver_102.exe",
        "/文本编辑器、chrome浏览器、autojs、HttpCanary等小工具/chromedriver_102.exe",
    )


def demo_download():
    url = get_download_url("/文本编辑器、chrome浏览器、autojs、HttpCanary等小工具/chromedriver_102.exe")

    from download import download_file

    download_file(url)


def demo_list():
    res = get_file_list("/", refresh=True)
    logger.info(res)


def demove_remove():
    remove("/文本编辑器、chrome浏览器、autojs、HttpCanary等小工具/chromedriver_102.exe")


if __name__ == "__main__":
    # demo_login()
    # demo_upload()
    # demo_download()
    demo_list()
    # demove_remove()
