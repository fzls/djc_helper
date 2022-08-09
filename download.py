import os
import random

import requests

from const import downloads_dir
from log import color, logger
from util import get_now, human_readable_size, make_sure_dir_exists, show_progress

user_agent_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
}


def download_file(url: str, download_dir=downloads_dir, filename="", connect_timeout=10) -> str:
    """
    下载指定url的文件到指定目录

    :param url: 要下载的文件的url
    :param download_dir: 保存的目录
    :param filename: 保存的文件名，如果为空，则使用url的文件名
    :param connect_timeout: 连接超时时间
    :return: 下载后的文件绝对路径
    """
    download_dir = os.path.realpath(download_dir)
    filename = filename or os.path.basename(url)

    start_time = get_now()

    target_file_path = os.path.join(download_dir, filename)

    logger.info(f"开始下载 {url} 到 {target_file_path}")
    response = requests.get(url, stream=True, timeout=connect_timeout, headers=user_agent_headers)

    if response.status_code != 200:
        raise Exception(f"下载失败，状态码 {response.status_code}")

    make_sure_dir_exists(download_dir)

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


def download_latest_github_release(
    download_dir=downloads_dir, asset_name="djc_helper.7z", owner="fzls", repo_name="djc_helper", connect_timeout=10
) -> str:
    """
    从github及其镜像下载指定仓库最新的release中指定资源

    :param download_dir: 下载目录
    :param asset_name: release的资源名称
    :param owner: 仓库拥有者名称
    :param repo_name: 仓库名称
    :param connect_timeout: 连接超时时间
    :return: 最终下载的本地文件绝对路径
    """
    release_file_path = f"{owner}/{repo_name}/releases/latest/download/{asset_name}"

    # note: 手动测试下载速度时，使用 IDM / 迅雷 等测试，不要直接用chrome测试，速度差很多

    # 先加入比较快的几个镜像
    urls = [
        f"https://gh.gh2233.ml/https://github.com/{release_file_path}",
        f"https://download.fastgit.org/{release_file_path}",
        f"https://ghproxy.com/https://github.com/{release_file_path}",
        f"https://gh.ddlc.top/https://github.com/{release_file_path}",
        f"https://kgithub.com/{release_file_path}",
        f"https://github.91chi.fun/https://github.com/{release_file_path}",
        f"https://gh2.yanqishui.work/https://github.com/{release_file_path}",
    ]

    # 随机乱序，确保均匀分布请求
    random.shuffle(urls)

    # 最后加入几个慢的镜像和源站
    urls.extend(
        [
            f"https://gh-proxy-misakano7545.koyeb.app/https://github.com/{release_file_path}",
            f"https://gh.api.99988866.xyz/https://github.com/{release_file_path}",
            f"https://github.com/{release_file_path}",
        ]
    )

    # 开始依次下载，直到成功下载
    for idx, url in enumerate(urls):
        try:
            mirror = extract_mirror_site(url,
                                         release_file_path,
                                         "https://github.com/",
                                         )
            logger.info(f"{idx + 1}/{len(urls)}: 尝试镜像： {mirror}")

            return download_file(url, download_dir, connect_timeout=connect_timeout)
        except Exception as e:
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
    connect_timeout=10,
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
    # 先加入比较快的几个镜像
    urls = [
        # 下面这个似乎会缓存很久，不会及时更新，先注释掉
        # f"https://github.do/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
        # f"https://hk1.monika.love/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
        f"https://raw.iqiq.io/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
        f"https://raw.連接.台灣/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
        f"https://raw-gh.gcdn.mirr.one/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
    ]

    # 随机乱序，确保均匀分布请求
    random.shuffle(urls)

    # 然后加入几个慢的镜像和源站
    urls.extend(
        [
            f"https://cdn.staticaly.com/gh/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            # f"https://cdn.jsdelivr.net/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
            f"https://gcore.jsdelivr.net/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
            f"https://fastly.jsdelivr.net/gh/{owner}/{repo_name}@{branch_name}/{filepath_in_repo}",
            f"https://raw.fastgit.org/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            f"https://ghproxy.com/https://raw.githubusercontent.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            f"https://ghproxy.futils.com/https://github.com/{owner}/{repo_name}/blob/{branch_name}/{filepath_in_repo}",
        ]
    )

    # 最后加入原始地址和一些不可达的
    urls.extend(
        [
            f"https://raw.githubusercontents.com/{owner}/{repo_name}/{branch_name}/{filepath_in_repo}",
            f"https://github.com/{owner}/{repo_name}/raw/{branch_name}/{filepath_in_repo}",
        ]
    )

    # 开始依次下载，直到成功下载
    for idx, url in enumerate(urls):
        try:
            mirror = extract_mirror_site(url,
                                         "/" + owner,
                                         "/" + repo_name,
                                         "/" + branch_name,
                                         "@" + branch_name,
                                         "/" + filepath_in_repo,
                                         "https://github.com/",
                                         "https://raw.githubusercontent.com/",
                                         )
            logger.info(f"{idx + 1}/{len(urls)}: 尝试镜像： {mirror}")

            return download_file(url, download_dir, connect_timeout=connect_timeout)
        except Exception as e:
            logger.error(f"{idx + 1}/{len(urls)}: 下载失败，异常内容： {e}，将继续尝试下一个github镜像")
            logger.debug("详细异常信息", exc_info=e)
            continue

    raise Exception("所有镜像都下载失败")


def extract_mirror_site(mirror_download_url: str, *words_to_remove: str) -> str:
    mirror_site = mirror_download_url
    for word in words_to_remove:
        mirror_site = mirror_site.replace(word, "")

    return mirror_site


if __name__ == "__main__":
    # download_latest_github_release()
    download_github_raw_content("utils/notices.txt")
