from __future__ import annotations

import os
import random
from typing import Callable

import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from const import downloads_dir
from log import color, logger
from util import get_now, human_readable_size, make_sure_dir_exists, show_progress

user_agent_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
}

# 全局禁用 SSL 警告
disable_warnings(InsecureRequestWarning)

progress_callback_func_type = Callable[[str, int, int, float], None]

# 默认连接超时
DOWNLOAD_CONNECT_TIMEOUT = 8

# 测速模式开关，开启后将对比各个不同镜像的下载速度
TEST_SPEED_MODE = False
MAX_TEST_SECONDS = 10


def download_file(
    url: str,
    download_dir=downloads_dir,
    filename="",
    connect_timeout=DOWNLOAD_CONNECT_TIMEOUT,
    extra_progress_callback: progress_callback_func_type | None = None,
    extra_info="",
) -> str:
    """
    下载指定url的文件到指定目录

    :param url: 要下载的文件的url
    :param download_dir: 保存的目录
    :param filename: 保存的文件名，如果为空，则使用url的文件名
    :param connect_timeout: 连接超时时间
    :param extra_progress_callback: 每次更新进度时的额外回调，比如可在特定条件下通过抛异常来中断下载
    :return: 下载后的文件绝对路径
    """
    download_dir = os.path.realpath(download_dir)
    filename = filename or os.path.basename(url)

    start_time = get_now()

    target_file_path = os.path.join(download_dir, filename)

    logger.info(f"开始下载 {url} 到 {target_file_path}（连接超时为 {connect_timeout} 秒）")
    if extra_info != "":
        logger.info(extra_info)
    response = requests.get(url, stream=True, timeout=connect_timeout, headers=user_agent_headers, verify=False)

    if response.status_code != 200:
        raise Exception(f"下载失败，状态码 {response.status_code}")

    make_sure_dir_exists(download_dir)

    check_cloudflare_100mb_test(response)

    with open(target_file_path, "wb") as f:
        total_length_optional = response.headers.get("content-length")

        if total_length_optional is None:  # no content length header
            f.write(response.content)
        else:
            dl = 0
            total_length = int(total_length_optional)
            for data in response.iter_content(chunk_size=4096):
                # filter out keep-alive new lines
                if not data:
                    continue

                f.write(data)

                dl += len(data)
                used_seconds = (get_now() - start_time).total_seconds()
                show_progress(filename, total_length, dl, used_seconds)

                if extra_progress_callback is not None:
                    extra_progress_callback(filename, total_length, dl, used_seconds)

                if TEST_SPEED_MODE and used_seconds >= MAX_TEST_SECONDS:
                    logger.warning(f"当前为测试模式，仅最多尝试 {MAX_TEST_SECONDS} 秒，避免测试时间过久")
                    return ""

            if dl > total_length:
                # 如果实际写入文件大小比headers中写的要大，一般是因为启用了gzip，传输的内容是压缩后的，但是requests会自动解压缩，所以实际大小会更大
                # 这种情况会导致上面的进度条没有换行，这里主动换行一下
                print("")

    end_time = get_now()
    used_time = end_time - start_time

    actual_size = os.stat(target_file_path).st_size
    speed = actual_size / used_time.total_seconds()
    human_readable_speed = human_readable_size(speed)

    logger.info(color("bold_yellow") + f"下载完成，耗时 {used_time}({human_readable_speed}/s)")

    return target_file_path


def check_cloudflare_100mb_test(response: requests.Response):
    content_type = response.headers.get("content-type")
    content_length = response.headers.get("content-length")
    server = response.headers.get("server")

    if content_type == "application/x-tar" and content_length == "104857600" and server == "cloudflare":
        raise Exception("镜像返回了cf的拦截文件100mb.test，跳过当前镜像")


def extend_urls(current_urls: list[str], new_urls: list[str]):
    urls_to_add = [*new_urls]
    if not TEST_SPEED_MODE:
        random.shuffle(urls_to_add)

    current_urls.extend(urls_to_add)


def download_latest_github_release(
    download_dir=downloads_dir,
    asset_name="djc_helper.7z",
    owner="fzls",
    repo_name="djc_helper",
    connect_timeout=DOWNLOAD_CONNECT_TIMEOUT,
    extra_progress_callback: progress_callback_func_type | None = None,
    version="",
) -> str:
    """
    从github及其镜像下载指定仓库最新的release中指定资源

    :param download_dir: 下载目录
    :param asset_name: release的资源名称
    :param owner: 仓库拥有者名称
    :param repo_name: 仓库名称
    :param connect_timeout: 连接超时时间
    :param extra_progress_callback: 每次更新进度时的额外回调，比如可在特定条件下通过抛异常来中断下载
    :param version: 指定的版本号，形如 20.1.2，若未指定则下载最新版本
    :return: 最终下载的本地文件绝对路径
    """
    if TEST_SPEED_MODE:
        logger.warning("当前为测速模式，将禁用洗牌流程，并依次尝试各个镜像，从而进行对比")

    release_file_path = f"{owner}/{repo_name}/releases/latest/download/{asset_name}"
    if version != "":
        release_file_path = f"{owner}/{repo_name}/releases/download/v{version}/{asset_name}"

    # note: 手动测试下载速度时，使用 IDM / 迅雷 等测试，不要直接用chrome测试，速度差很多

    urls: list[str] = []

    # 可用性较高的镜像
    extend_urls(
        urls,
        [
            # 887.3KiB/s
            f"https://ghfast.top/https://github.com/{release_file_path}",
            # 419.5KiB/s
            f"https://git.yylx.win/https://github.com/{release_file_path}",
            # 1.8MiB/s
            f"https://ghp.keleyaa.com/https://github.com/{release_file_path}",
            # 157.6KiB/s
            f"https://gh.xx9527.cn/https://github.com/{release_file_path}",
            # # 10054
            # f"https://cors.isteed.cc/github.com/{release_file_path}",
            # 360.4KiB/s
            f"https://github.boki.moe/https://github.com/{release_file_path}",
            # 228.2KiB/s
            f"https://gh-proxy.com/https://github.com/{release_file_path}",
            # 127.8KiB/s
            f"https://hub.gitmirror.com/https://github.com/{release_file_path}",
            # 37.2KiB/s
            f"https://kkgithub.com/{release_file_path}",
            # 559.2KiB/s
            f"https://gh.h233.eu.org/https://github.com/{release_file_path}",
        ],
    )

    # 原始地址
    extend_urls(
        urls,
        [
            # timeout
            f"https://github.com/{release_file_path}",
        ],
    )

    # 再保底放入一些可能失效的镜像
    extend_urls(
        urls,
        [
        ],
    )

    # 一些注释掉的已失效的，仅留着备忘
    # note: 每次更新的时候，若可用节点不多了的时候，临时挪到上面的不可达的组里面，看看是否有恢复的
    memo_invalid_mirror_list = [  # noqa: F841
    ]
    extend_urls(
        memo_invalid_mirror_list,
        [
            # 11001
            f"https://slink.ltd/https://github.com/{release_file_path}",
            # 403
            f"https://ghproxy.cc/https://github.com/{release_file_path}",
            # 11001
            f"https://wget.la/https://github.com/{release_file_path}",
            # 502
            f"https://github.ednovas.xyz/https://github.com/{release_file_path}",
            # handshake
            f"https://gh.api.99988866.xyz/https://github.com/{release_file_path}",
            # 无效
            f"https://gh.con.sh/https://github.com/{release_file_path}",
            # 无效
            f"https://dl.ghpig.top/https://github.com/{release_file_path}",
            # 无效
            f"https://dl-slb.ghpig.top/https://github.com/{release_file_path}",
            # 11001
            f"https://js.xxooo.ml/https://github.com/{release_file_path}",
            # 无效
            f"https://gh.gh2233.ml/https://github.com/{release_file_path}",
            # 502
            f"https://download.yzuu.cf/{release_file_path}",
            # 11001
            f"https://download.fastgit.org/{release_file_path}",
            # 429
            f"https://gh.ddlc.top/https://github.com/{release_file_path}",
            # 11001
            f"https://download.njuu.cf/{release_file_path}",
            # timeout
            f"https://download.nuaa.cf/{release_file_path}",
            # 无效
            f"https://ghps.cc/https://github.com/{release_file_path}",
            # 11001
            f"https://download.fgit.cf/{release_file_path}",
            # 502
            f"https://ghproxy.net/https://github.com/{release_file_path}",
            # timeout
            f"https://ghproxy.com/https://github.com/{release_file_path}",
            # 11001
            f"https://proxy.zyun.vip/https://github.com/{release_file_path}",
            # timeout
            f"https://kgithub.com/{release_file_path}",
            # 11001
            f"https://ghdl.feizhuqwq.cf/https://github.com/{release_file_path}",
            # 11001
            f"https://download.fastgit.ixmu.net/{release_file_path}",
            # 无效
            f"https://mirror.ghproxy.com/https://github.com/{release_file_path}",
            # timeout
            f"https://github.moeyy.xyz/https://github.com/{release_file_path}",
            # 11001
            f"https://download.ixnic.net/{release_file_path}",
            # 无效
            f"https://dgithub.xyz/{release_file_path}",
        ],
    )
    _ = memo_invalid_mirror_list

    if TEST_SPEED_MODE:
        logger.info(color("bold_cyan") + "当前全部镜像如下:\n" + "\n".join(urls) + "\n")

    # 开始依次下载，直到成功下载
    for idx, url in enumerate(urls):
        try:
            mirror = extract_mirror_site(
                url,
                release_file_path,
                "https://github.com/",
            )
            log_mirror_status(idx, len(urls), mirror)

            file_path = download_file(
                url, download_dir, connect_timeout=connect_timeout, extra_progress_callback=extra_progress_callback
            )

            if not TEST_SPEED_MODE:
                return file_path
            else:
                logger.warning("\n")
        except BaseException as e:
            logger.error(f"{idx + 1}/{len(urls)}: 下载失败，异常内容： {e}，将继续尝试下一个github镜像")
            logger.debug("详细异常信息", exc_info=e)
            continue

    raise Exception("所有镜像都下载失败")


def download_github_raw_content(
    filepath_in_repo: str,
    download_dir=downloads_dir,
    owner="fzls",
    repo_name="djc_helper",
    branch_name="master",
    connect_timeout=DOWNLOAD_CONNECT_TIMEOUT,
) -> str:
    """
    从github及其镜像下载指定仓库的指定分支的指定文件到本地指定目录

    :param filepath_in_repo: 要下载的文件在仓库中的路径，如 docs/README.md
    :param download_dir: 本地保存的目录
    :param owner: 仓库拥有者名称
    :param repo_name: 仓库名称
    :param branch_name: 分支名称
    :param connect_timeout: 连接超时
    :return: 最终下载的本地文件绝对路径
    """
    if TEST_SPEED_MODE:
        logger.warning("当前为测速模式，将禁用洗牌流程，并依次尝试各个镜像，从而进行对比")

    urls: list[str] = []

    # 可用性较高的几个镜像
    extend_urls(
        urls,
        [
            # 281.9KiB/s
            f"https://hk.gh-proxy.com/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 159.7KiB/s
            f"https://ghproxy.net/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 150.2KiB/s
            f"https://g.blfrp.cn/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 131.0KiB/s
            f"https://hub.gitmirror.com/https://raw.githubusercontent.com/{owner}/{repo_name}/refs/heads/{branch_name}/{filepath_in_repo}",
            # 139.3KiB/s
            # 最新地址可见：https://ghproxy.link/
            f"https://ghfast.top/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 74.6KiB/s
            f"https://fastly.jsdelivr.net/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
            # 67.4KiB/s
            f"https://gh.catmak.name/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 378.4KiB/s
            f"https://raw.kkgithub.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 148.6KiB/s
            f"https://gh-proxy.com/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 50.7KiB/s
            f"https://cdn.jsdelivr.net/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
            # ok
            f"https://jsdelivr.b-cdn.net/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
            # 235.9KiB/s
            f"https://gcore.jsdelivr.net/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
            # 470.8KiB/s
            f"https://cdn.jsdmirror.com/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
        ],
    )

    # 原始地址
    extend_urls(
        urls,
        [
            # 70.6KiB/s
            f"https://github.com/{owner}/{repo_name}/raw/{branch_name}/{filepath_in_repo}",
        ],
    )
    # 一些不可达的
    extend_urls(
        urls,
        [
        ],
    )

    # 有可能缓存过时内容的镜像，作为最后备选
    extend_urls(
        urls,
        [
        ],
    )

    # 一些注释掉的已失效的，仅留着备忘
    # note: 每次更新的时候，若可用节点不多了的时候，临时挪到上面的不可达的组里面，看看是否有恢复的
    memo_invalid_mirror_list = [  # noqa: F841
    ]
    extend_urls(
        memo_invalid_mirror_list,
        [
            # timeout
            f"https://github.moeyy.xyz/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 11001
            f"https://wget.la/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # timeout
            f"https://github.3x25.com/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 11001
            f"https://gitdl.cn/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 11001
            f"https://raw.ixnic.net/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # timeout
            f"https://ghgo.xyz/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 11002
            f"https://jsd.proxy.aks.moe/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
            # ConnectTimeoutError
            f"https://mirror.ghproxy.com/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 11001
            f"https://raw.fastgit.org/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 11001
            f"https://raw.fgit.cf/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 10054
            f"https://ghproxy.com/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # timeout
            f"https://raw.iqiq.io/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # 11001
            f"https://raw.fastgit.ixmu.net/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # timeout
            f"https://raw.kgithub.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
        ],
    )
    _ = memo_invalid_mirror_list

    if TEST_SPEED_MODE:
        logger.info(color("bold_cyan") + "当前全部镜像如下:\n" + "\n".join(urls) + "\n")

    # 开始依次下载，直到成功下载
    for idx, url in enumerate(urls):
        try:
            mirror = extract_mirror_site(
                url,
                "/" + owner,
                "/" + repo_name,
                "/" + branch_name,
                "@" + branch_name,
                "/" + filepath_in_repo,
                "https://github.com/",
                "https://raw.githubusercontent.com/",
            )
            log_mirror_status(idx, len(urls), mirror)

            file_path = download_file(url, download_dir, connect_timeout=connect_timeout)

            if not TEST_SPEED_MODE:
                return file_path
            else:
                logger.warning("\n")
        except BaseException as e:
            logger.error(f"{idx + 1}/{len(urls)}: 下载失败，异常内容： {e}，将继续尝试下一个github镜像")
            logger.debug("详细异常信息", exc_info=e)
            continue

    raise Exception("所有镜像都下载失败")


def log_mirror_status(current_index: int, total_count: int, mirror: str):
    if TEST_SPEED_MODE:
        logger.info("\n")
    logger.info(
        f"{current_index + 1}/{total_count}: 尝试镜像： {mirror}"
        + color("bold_yellow")
        + "（如果速度较慢，请按 ctrl + c 强制切换下一个镜像）"
    )


def extract_mirror_site(mirror_download_url: str, *words_to_remove: str) -> str:
    mirror_site = mirror_download_url
    for word in words_to_remove:
        mirror_site = mirror_site.replace(word, "")

    return mirror_site


if __name__ == "__main__":
    from config import CommonConfig
    from update import get_latest_version_from_github

    def get_latest_version() -> str:
        # 尝试从github获取版本信息
        cfg = CommonConfig()
        return get_latest_version_from_github(cfg)

    latest_version = get_latest_version()

    # re: 要测试的话，把这个开关设为 True
    TEST_SPEED_MODE = False

    # download_latest_github_release(version=latest_version)
    download_github_raw_content("CHANGELOG.MD")
