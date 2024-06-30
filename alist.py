from __future__ import annotations

import functools
import os
from datetime import timedelta
from urllib.parse import quote

import requests

from const import downloads_dir
from dao import ConfigInterface, to_raw_type
from download import DOWNLOAD_CONNECT_TIMEOUT, download_file, progress_callback_func_type
from log import color, logger
from server import get_alist_server_addr
from util import KiB, get_now, human_readable_size, reset_cache, with_cache

fn_SERVER_ADDR = get_alist_server_addr


def _make_api(api_name="/") -> str:
    return f"{fn_SERVER_ADDR()}{api_name}"


def fn_API_LOGIN():
    return _make_api("/api/auth/login")


def fn_API_UPLOAD():
    return _make_api("/api/fs/put")


def fn_API_DOWNLOAD():
    return _make_api("/api/fs/get")


def fn_API_LIST():
    return _make_api("/api/fs/list")


def fn_API_REMOVE():
    return _make_api("/api/fs/remove")


NORMAL_TIMEOUT = 8
UPLOAD_TIMEOUT = 60 * 5

alist_session = requests.session()
alist_session.request = functools.partial(alist_session.request, timeout=NORMAL_TIMEOUT)  # type: ignore


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
        self.password = ""
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


class DownloadRequest(ConfigInterface):
    def __init__(self):
        self.path = ""
        self.password = ""


class DownloadResponse(ConfigInterface):
    def __init__(self):
        self.name = "DNF蚊子腿小助手_v20.0.1_by风之凌殇.7z"
        self.size = 51111681
        self.is_dir = False
        self.modified = "2022-10-28T10:38:13+08:00"
        self.sign = "h9zSwqaagxTsodawAGF53ICbv19t0_y9FJP2qj2gjhA=:0"
        self.thumb = ""
        self.type = 0
        self.raw_url = ""
        self.readme = ""
        self.provider = "Aliyundrive"
        self.related = None

        # 用于构建下载链接的参数，使用时设置
        self.remote_file_path = ""

    def get_url(self) -> str:
        if self.sign != "" and self.remote_file_path != "":
            # 尽量使用alist的下载接口做中转，这样服务器日志方便查看下载情况
            return f"{fn_SERVER_ADDR()}/d{self.remote_file_path}?sign={self.sign}"

        return self.raw_url


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

    raw_res = alist_session.post(fn_API_LOGIN(), json=to_raw_type(req))

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

    start_time = get_now()

    with open(local_file_path, "rb") as file_to_upload:
        raw_res = alist_session.put(
            fn_API_UPLOAD(),
            data=file_to_upload,
            headers={
                "File-Path": quote(remote_file_path),
                "As-Task": "false",
                "Authorization": login_using_env(),
            },
            timeout=UPLOAD_TIMEOUT,
        )

        res = CommonResponse().auto_update_config(raw_res.json())
        if res.code != 200:
            raise generate_exception(res, "upload")

    end_time = get_now()
    used_time = end_time - start_time

    speed = actual_size / used_time.total_seconds()
    human_readable_speed = human_readable_size(speed)

    logger.info(color("bold_yellow") + f"上传完成，耗时 {used_time}({human_readable_speed}/s)")

    remote_dir = os.path.dirname(remote_file_path)
    remote_filename = os.path.basename(remote_file_path)
    if old_version_name_prefix != "":
        remove_file_startswith_prefix(remote_dir, old_version_name_prefix, [remote_filename])

        logger.info("旧版本处理完毕，将开始实际上传流程")

    logger.info("上传完毕后强制刷新该目录，确保后续访问可以看到新文件")
    get_file_list(remote_dir, refresh=True)


def remove_file_startswith_prefix(remote_dir: str, name_prefix: str, except_filename_list: list[str] | None = None):
    logger.info(f"将移除网盘目录 {remote_dir} 中 前缀为 {name_prefix} 的文件")
    dir_file_list_info = get_file_list(remote_dir, refresh=True)
    for file_info in dir_file_list_info.content:
        if file_info.is_dir:
            continue

        if not file_info.name.startswith(name_prefix):
            continue

        if except_filename_list is not None and file_info.name in except_filename_list:
            # 不包括最新上传的文件，因为alist会自动覆盖相同名字的文件
            continue

        remove(os.path.join(remote_dir, file_info.name))


def is_file_in_folder(remote_dir: str, filename: str) -> bool:
    remote_filepath = os.path.join(remote_dir, filename)

    try:
        get_download_info(remote_filepath)
        return True
    except Exception:
        return False


def get_download_info(remote_file_path: str) -> DownloadResponse:
    remote_file_path = format_remote_file_path(remote_file_path)

    req = DownloadRequest()
    req.path = remote_file_path
    req.password = ""

    raw_res = alist_session.post(fn_API_DOWNLOAD(), json=to_raw_type(req))

    res = CommonResponse().auto_update_config(raw_res.json())
    if res.code != 200:
        raise generate_exception(res, "download")

    data = DownloadResponse().auto_update_config(res.data)

    data.remote_file_path = remote_file_path

    return data


def download_from_alist(
    remote_file_path: str,
    download_dir=downloads_dir,
    filename="",
    connect_timeout=DOWNLOAD_CONNECT_TIMEOUT,
    extra_progress_callback: progress_callback_func_type | None = None,
) -> str:
    download_info = get_download_info(remote_file_path)

    if filename == "":
        filename = download_info.name

    guess_speed = 300 * KiB
    guess_time = timedelta(seconds=download_info.size / guess_speed)

    extra_info = f"文件大小为 {human_readable_size(download_info.size)}（进度条可能不会显示，请耐心等待。若下载速度为 {human_readable_size(guess_speed)}/s 预计耗时 {guess_time}）"
    return download_file(download_info.get_url(), download_dir, filename, extra_info=extra_info)


def get_file_list(
    remote_dir_path: str, password: str = "", page: int = 1, per_page: int = 0, refresh=False
) -> ListResponse:
    req = ListRequest()
    req.path = remote_dir_path
    req.password = password
    req.page = page
    req.per_page = per_page
    req.refresh = refresh

    headers = {}
    if refresh:
        # 刷新需要token
        headers = {
            "Authorization": login_using_env(),
        }

    raw_res = alist_session.post(fn_API_LIST(), json=to_raw_type(req), headers=headers)

    res = CommonResponse().auto_update_config(raw_res.json())
    if res.code != 200:
        if res.code == 401 and "expired" in res.message:
            reset_cache("alist")

        raise generate_exception(res, "list")

    data = ListResponse().auto_update_config(res.data)

    return data


def remove(remote_file_path: str):
    remote_file_path = format_remote_file_path(remote_file_path)

    dir = os.path.dirname(remote_file_path)
    file_name = os.path.basename(remote_file_path)

    logger.info(f"开始删除网盘文件 {remote_file_path}")

    req = RemoveRequest()
    req.dir = dir
    req.names = [
        file_name,
    ]

    raw_res = alist_session.post(
        fn_API_REMOVE(),
        json=to_raw_type(req),
        headers={
            "Authorization": login_using_env(),
        },
    )

    res = CommonResponse().auto_update_config(raw_res.json())
    if res.code != 200:
        raise generate_exception(res, "remove")

    logger.info(color("bold_yellow") + "删除完成")


def get_username_password_from_env() -> tuple[str, str]:
    username = str(os.getenv("ALIST_USERNAME", ""))
    password = str(os.getenv("ALIST_PASSWORD", ""))

    if username == "" or password == "":
        raise Exception("请在环境变量中设置 ALIST_USERNAME 和 ALIST_PASSWORD，否则将无法登录alist")

    return username, password


def login_using_env() -> str:
    username, password = get_username_password_from_env()

    return login(username, password)


def demo_login():
    username, password = get_username_password_from_env()

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
    filepath = download_from_alist("/文本编辑器、chrome浏览器、autojs、HttpCanary等小工具/chromedriver_102.exe")
    logger.info(f"最终下载路径为 {filepath}")


def demo_list():
    res = get_file_list("/", refresh=True)
    logger.info(res)


def demove_remove():
    remove("/文本编辑器、chrome浏览器、autojs、HttpCanary等小工具/chromedriver_102.exe")


if __name__ == "__main__":
    # demo_login()
    # demo_upload()
    demo_download()
    # demo_list()
    # demove_remove()
