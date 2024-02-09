from __future__ import annotations

import json
import os
import re
from collections import namedtuple
from datetime import datetime, timedelta

from compress import compress_file_with_lzma, decompress_file_with_lzma
from const import compressed_temp_dir, downloads_dir
from lanzou.api import LanZouCloud
from lanzou.api.types import FileInFolder, FolderDetail
from log import color, get_log_func, logger
from util import (
    cache_name_download,
    human_readable_size,
    make_sure_dir_exists,
    parse_time,
    parse_timestamp,
    show_progress,
    with_cache,
)

Folder = namedtuple("Folder", ["name", "id", "url", "password"])


# 参考文档可见：https://github.com/zaxtyson/LanZouCloud-API/wiki

# 如果日后蓝奏云仍出现多次问题，可以考虑增加一个fallback选项
# 在gitee新建一个仓库，通过git add操作更新文件，通过访问raw链接来下载文件
# 如：https://gitee.com/fzls/djc_helper/raw/master/CHANGELOG.MD


class Uploader:
    default_sub_domain = "fzls"
    default_main_domain = "lanzouo"
    default_domain = f"{default_sub_domain}.{default_main_domain}.com"

    folder_dnf_calc = Folder("魔改计算器", "1810329", f"https://{default_domain}/s/dnf-calc", "")
    folder_djc_helper = Folder("蚊子腿小助手", "2290618", f"https://{default_domain}/s/djc-helper", "")
    folder_history_files = Folder("历史版本", "2303716", f"https://{default_domain}/b01bp17zg", "")
    folder_djc_helper_tools = Folder("蚊子腿小助手相关工具", "2291287", f"https://{default_domain}/s/djc-tools", "")
    folder_online_files = Folder("在线文件存储-v2", "3828082", f"https://{default_domain}/s/myfiles-v2", "3jte")
    folder_online_files_history_files = Folder(
        "历史版本-v2", "3828089", f"https://{default_domain}/myfiles-v2-history", "fwqi"
    )

    history_version_prefix = "DNF蚊子腿小助手_v"
    history_patches_prefix = "DNF蚊子腿小助手_增量更新文件_"
    history_dlc_version_prefix = "auto_updater.exe"

    regex_version = r"DNF蚊子腿小助手_v(.+)_by风之凌殇.7z"
    regex_patches = r"DNF蚊子腿小助手_增量更新文件_v(.+)_to_v(.+).7z"

    # 保存购买了自动更新工具的用户信息
    buy_auto_updater_users_filename = "buy_auto_updater_users.txt"

    # 保存用户的付费信息
    user_monthly_pay_info_filename = "user_monthly_pay_info.txt"

    # 卡密操作的付费信息
    cs_used_card_secrets = "_used_card_secrets.txt"
    cs_buy_auto_updater_users_filename = "cs_buy_auto_updater_users.txt"
    cs_user_monthly_pay_info_filename = "cs_user_monthly_pay_info.txt"

    # 直接充值的付费信息
    all_jiaoyile_orders_filename = "_all_jiaoyile_orders_filepath.txt"

    # 压缩版本的前后缀
    compressed_version_prefix = "compressed_"
    compressed_version_suffix = ".7z"

    def __init__(self):
        self.lzy = LanZouCloud()
        self.login_ok = False

        self.lzy._timeout = 5

    def login(self, cookie: dict | None = None):
        # 仅上传需要登录
        if cookie is None:
            with open("upload_cookie.json") as fp:
                cookie = json.load(fp)

        # 仅上传需要登录
        self.login_ok = self.lzy.login_by_cookie(cookie) == LanZouCloud.SUCCESS

    def upload_to_lanzouyun(
        self,
        filepath: str,
        target_folder: Folder,
        history_file_prefix="",
        delete_history_file=False,
        also_upload_compressed_version=False,
        only_upload_compressed_version=False,
    ) -> bool:
        if not self.login_ok:
            logger.info("未登录，不能上传文件")
            return False

        if history_file_prefix == "":
            # 未设置历史文件前缀，默认为当前文件名
            history_file_prefix = os.path.basename(filepath)

        if not only_upload_compressed_version:
            ok = self._upload_to_lanzouyun(filepath, target_folder, history_file_prefix, delete_history_file)
            if not ok:
                return False

        if also_upload_compressed_version:
            filename = os.path.basename(filepath)
            compressed_filepath = os.path.join(compressed_temp_dir, self.get_compressed_version_filename(filename))
            compressed_history_file_prefix = f"{self.compressed_version_prefix}{history_file_prefix}"

            logger.info(color("bold_green") + f"创建压缩版本并上传 {compressed_filepath}")
            # 创建压缩版本
            compress_file_with_lzma(filepath, compressed_filepath)
            # 上传
            return self._upload_to_lanzouyun(
                compressed_filepath, target_folder, compressed_history_file_prefix, delete_history_file
            )

        return True

    def _upload_to_lanzouyun(
        self, filepath: str, target_folder: Folder, history_file_prefix, delete_history_file=False
    ) -> bool:
        if history_file_prefix == "":
            logger.error("未设置history_file_prefix")
            return False

        filename = os.path.basename(filepath)
        logger.warning(f"开始上传 {filename} 到 {target_folder.name}")
        run_start_time = datetime.now()

        def on_uploaded(fid, is_file):
            if not is_file:
                return

            logger.info(f"上传完成，fid={fid}")

            folder_history_files = self.folder_history_files
            if target_folder.id == self.folder_online_files.id:
                folder_history_files = self.folder_online_files_history_files

            files = self.lzy.get_file_list(target_folder.id)
            for file in files:
                if file.name.startswith(history_file_prefix):
                    if not delete_history_file:
                        self.lzy.move_file(file.id, folder_history_files.id)
                        logger.info(f"将{file.name}移动到目录({folder_history_files.name})")
                    else:
                        self.lzy.delete(file.id, True)
                        logger.info(f"移除旧版本的{file.name}")

            logger.info(f"将文件移到目录({target_folder.name})中")
            self.lzy.move_file(fid, target_folder.id)

        # 上传到指定的文件夹中
        retCode = self.lzy.upload_file(filepath, -1, callback=show_progress, uploaded_handler=on_uploaded)
        if retCode != LanZouCloud.SUCCESS:
            logger.error(f"上传失败，retCode={retCode}")
            return False

        filesize = os.path.getsize(filepath)
        logger.warning(
            color("bold_yellow")
            + f"上传文件 {filename}({human_readable_size(filesize)}) 总计耗时{datetime.now() - run_start_time}"
        )

        return True

    def get_compressed_version_filename(self, filename: str) -> str:
        return f"{self.compressed_version_prefix}{filename}{self.compressed_version_suffix}"

    def latest_version(self) -> str:
        """
        返回形如"1.0.0"的最新版本信息
        """
        latest_version_file = self.find_latest_version()

        return self.parse_version_from_djc_helper_file_name(latest_version_file.name)

    def parse_version_from_djc_helper_file_name(self, filename: str) -> str:
        """
        从小助手压缩包文件名中提取版本信息
        DNF蚊子腿小助手_v4.6.6_by风之凌殇.7z => v4.6.6
        """
        match = re.search(self.regex_version, filename)
        if match is None:
            # 保底返回1.0.0
            return "1.0.0"

        return match.group(1)

    def download_latest_version(self, download_dir, show_log=True) -> str:
        """
        下载最新版本压缩包到指定目录，并返回最终压缩包的完整路径
        """
        # note: 如果哪天蓝奏云不可用了，可以尝试使用github的release，对于国内情况，使用其镜像来下载
        #   官网： https://github.com/fzls/djc_helper/releases/download/latest/djc_helper.7z
        #   镜像： https://download.fastgit.org/fzls/djc_helper/releases/download/latest/djc_helper.7z
        return self.download_file(self.find_latest_version(), download_dir, show_log=show_log)

    def find_latest_version(self) -> FileInFolder:
        """
        查找最新版本，如找到，返回lanzouyun提供的file信息，否则抛出异常
        """
        folder_info = self.get_folder_info_by_url(self.folder_djc_helper.url)
        for file in folder_info.files:
            if file.name.startswith(self.history_version_prefix):
                return file

        raise FileNotFoundError("latest version not found")

    def latest_patches_range(self):
        """
        返回形如("1.0.0", "1.1.2")的补丁范围
        """
        latest_patches_file = self.find_latest_patches()
        # DNF蚊子腿小助手_增量更新文件_v4.6.5_to_v4.6.6.7z
        match = re.search(self.regex_patches, latest_patches_file.name)
        if match is not None:
            version_left, version_right = match.group(1), match.group(2)
            return (version_left, version_right)

        # 保底返回
        return ("1.0.0", "1.0.0")

    def download_latest_patches(self, download_dir) -> str:
        """
        下载最新版本压缩包到指定目录，并返回最终压缩包的完整路径
        """
        return self.download_file(self.find_latest_patches(), download_dir)

    def find_latest_patches(self) -> FileInFolder:
        """
        查找最新版本的补丁，如找到，返回lanzouyun提供的file信息，否则抛出异常
        """
        folder_info = self.get_folder_info_by_url(self.folder_djc_helper.url)
        for file in folder_info.files:
            if file.name.startswith(self.history_patches_prefix):
                return file

        raise FileNotFoundError("latest patches not found")

    def download_latest_dlc_version(self, download_dir) -> str:
        """
        下载最新版本dlc压缩包到指定目录，并返回最终压缩包的完整路径
        """
        return self.download_file(self.find_latest_dlc_version(), download_dir)

    def find_latest_dlc_version(self) -> FileInFolder:
        """
        查找最新版本dlc，如找到，返回lanzouyun提供的file信息，否则抛出异常
        """
        folder_info = self.get_folder_info_by_url(self.folder_djc_helper.url)
        for file in folder_info.files:
            if file.name.startswith(self.history_dlc_version_prefix):
                return file

        raise FileNotFoundError("latest version not found")

    def download_file_in_folder(
        self,
        folder: Folder,
        name: str,
        download_dir: str,
        overwrite=True,
        show_log=True,
        try_compressed_version_first=False,
        cache_max_seconds=600,
        download_only_if_server_version_is_newer=True,
        return_none_on_exception=False,
    ) -> str | None:
        """
        下载网盘指定文件夹的指定文件到本地指定目录，并返回最终本地文件的完整路径
        """

        def _download(fname: str) -> str:
            return with_cache(
                cache_name_download,
                os.path.join(folder.name, fname),
                cache_max_seconds=cache_max_seconds,
                cache_miss_func=lambda: self.download_file(
                    self.find_file(folder, fname),
                    download_dir,
                    overwrite=overwrite,
                    show_log=show_log,
                    download_only_if_server_version_is_newer=download_only_if_server_version_is_newer,
                ),
                cache_validate_func=lambda target_path: os.path.isfile(target_path),
                return_none_on_exception=return_none_on_exception,
            )

        if try_compressed_version_first:
            # 先尝试获取压缩版本
            compressed_filename = self.get_compressed_version_filename(name)
            try:
                get_log_func(logger.info, show_log)(color("bold_green") + f"尝试优先下载压缩版本 {compressed_filename}")

                # 记录下载前的最近修改时间
                before_download_last_modify_time = None
                old_compressed_filepath = os.path.join(download_dir, compressed_filename)
                if os.path.isfile(old_compressed_filepath):
                    before_download_last_modify_time = parse_timestamp(os.stat(old_compressed_filepath).st_mtime)

                # 下载压缩版本
                compressed_filepath = _download(compressed_filename)

                # 记录下载完成后的最近修改时间
                after_download_last_modify_time = parse_timestamp(os.stat(compressed_filepath).st_mtime)

                # 解压缩
                dirname = os.path.dirname(compressed_filepath)
                target_path = os.path.join(dirname, name)

                need_decompress = True
                if (
                    before_download_last_modify_time is not None
                    and before_download_last_modify_time == after_download_last_modify_time
                    and os.path.exists(target_path)
                ):
                    # 如果前后修改时间没有变动，说明没有实际发生下载，比如网盘版本与当前本地版本一致，如果此时目标文件已经解压过，将不再尝试解压
                    need_decompress = False

                if need_decompress:
                    decompress_file_with_lzma(compressed_filepath, target_path)
                else:
                    get_log_func(logger.info, show_log)(
                        f"{compressed_filepath}未发生改变，且目标文件已存在，无需尝试解压缩"
                    )
                # 返回解压缩的文件路径
                return target_path
            except Exception as e:
                get_log_func(logger.error, show_log)(
                    f"下载压缩版本 {compressed_filename} 失败，将尝试普通版本~", exc_info=e
                )

        # 下载普通版本
        return _download(name)

    def find_file(self, folder, name) -> FileInFolder:
        """
        在对应目录查找指定名称的文件，如找到，返回lanzouyun提供的file信息，否则抛出异常
        """
        folder_info = self.get_folder_info_by_url(folder.url, folder.password)
        for file in folder_info.files:
            if file.name == name:
                return file

        raise FileNotFoundError(f"file={name} not found in folder={folder.name}")

    def download_file(
        self,
        fileinfo: FileInFolder,
        download_dir: str,
        overwrite=True,
        show_log=True,
        download_only_if_server_version_is_newer=True,
    ) -> str:
        """
        下载最新版本压缩包到指定目录，并返回最终压缩包的完整路径
        """
        make_sure_dir_exists(download_dir)

        download_dir = os.path.realpath(download_dir)
        target_path = StrWrapper(os.path.join(download_dir, fileinfo.name))

        if download_only_if_server_version_is_newer and os.path.isfile(target_path.value):
            # 仅在服务器版本比本地已有文件要新的时候才重新下载
            # 由于蓝奏云时间显示不精确，将其往前一分钟，避免同一文件下次检查时其蓝奏云时间显示为xx分钟前，解析后会有最多一分钟内的误差，而导致不必要的重新下载
            # 比如本次是x分y秒检查并更新，下次检查时是x+6分y+10秒，此时解析蓝奏云时间得到上传时间为x分y+10秒，就会产生额外的不必要下载
            server_version_upload_time = parse_time(fileinfo.time) - timedelta(minutes=1)
            local_version_last_modify_time = parse_timestamp(os.stat(target_path.value).st_mtime)

            get_log_func(logger.info, show_log)(
                f"{fileinfo.name} 本地修改时间为：{local_version_last_modify_time} 网盘版本上传时间为：{server_version_upload_time}"
            )

            if server_version_upload_time <= local_version_last_modify_time:
                # 暂无最新版本，无需重试
                get_log_func(logger.info, show_log)(
                    color("bold_cyan")
                    + f"当前设置了对比修改时间参数，网盘中最新版本 {fileinfo.name} 上传于{server_version_upload_time}左右，在当前版本{local_version_last_modify_time}之前，无需重新下载"
                )
                return target_path.value

        def after_downloaded(file_name):
            """下载完成后的回调函数"""
            target_path.value = file_name
            get_log_func(logger.info, show_log)(f"最终下载文件路径为 {file_name}")

        get_log_func(logger.info, show_log)(f"即将开始下载 {target_path.value}")
        callback = None
        if show_log:
            callback = show_progress
        retCode = self.down_file_by_url(
            fileinfo.url, "", download_dir, callback=callback, downloaded_handler=after_downloaded, overwrite=overwrite
        )
        if retCode != LanZouCloud.SUCCESS:
            get_log_func(logger.error, show_log)(f"下载失败，retCode={retCode}")
            if retCode == LanZouCloud.NETWORK_ERROR:
                get_log_func(logger.warning, show_log)(
                    color("bold_yellow")
                    + (
                        "蓝奏云api返回网络错误，这很可能是由于dns的问题导致的\n"
                        "分别尝试在浏览器中访问下列两个网页，是否一个打的开一个打不开？\n"
                        "https://fzls.lanzoux.com/s/djc-helper\n"
                        "https://fzls.lanzous.com/s/djc-helper\n"
                        "\n"
                        "如果是这样，请按照下面这个链接，修改本机的dns，使用阿里、腾讯、百度、谷歌dns中的任意一个应该都可以解决。\n"
                        "https://www.ypojie.com/9830.html\n"
                        "\n"
                        "如果两个都打不开，大概率是蓝奏云挂了-。-可选择忽略后面的弹框，继续运行旧版本，或者手动去QQ群或github下载最新版本"
                    )
                )
            raise Exception("下载失败")

        return target_path.value

    def get_folder_info_by_url(self, share_url, dir_pwd="", get_this_page=0) -> FolderDetail:
        for possiable_url in self.all_possiable_urls(share_url):
            try:
                folder_info = self.lzy.get_folder_info_by_url(possiable_url, dir_pwd, get_this_page=get_this_page)
            except Exception as e:
                folder_info = FolderDetail(LanZouCloud.NETWORK_ERROR)
                logger.debug(f"get_folder_info_by_url {possiable_url} 出异常了", exc_info=e)

            if folder_info.code != LanZouCloud.SUCCESS:
                logger.debug(f"请求{possiable_url}失败，将尝试下一个")
                continue

            return folder_info

        return FolderDetail(LanZouCloud.FAILED)

    def down_file_by_url(
        self, share_url, pwd="", save_path="./Download", *, callback=None, overwrite=False, downloaded_handler=None
    ) -> int:
        for possiable_url in self.all_possiable_urls(share_url):
            try:
                retCode = self.lzy.down_file_by_url(
                    possiable_url,
                    pwd,
                    save_path,
                    callback=callback,
                    overwrite=overwrite,
                    downloaded_handler=downloaded_handler,
                )
            except Exception as e:
                retCode = LanZouCloud.NETWORK_ERROR
                logger.debug(f"down_file_by_url {possiable_url} 出异常了", exc_info=e)

            if retCode != LanZouCloud.SUCCESS:
                logger.debug(f"请求{possiable_url}失败，将尝试下一个")
                continue

            return retCode

        return LanZouCloud.FAILED

    def all_possiable_urls(self, lanzouyun_url: str) -> list[str]:
        return self.lzy._all_possible_urls(lanzouyun_url)


class StrWrapper:
    def __init__(self, value: str):
        self.value = value


def demo():
    uploader = Uploader()

    # 不需要登录的接口
    logger.info(f"最新版本为{uploader.latest_version()}")
    # uploader.download_latest_version(downloads_dir)

    logger.info(f"最新增量补丁范围为{uploader.latest_patches_range()}")
    logger.info(f"最新增量补丁为{uploader.find_latest_patches()}")
    uploader.download_latest_patches(downloads_dir)

    uploader.download_file_in_folder(
        uploader.folder_online_files,
        uploader.cs_user_monthly_pay_info_filename,
        downloads_dir,
        try_compressed_version_first=True,
    )
    uploader.download_file_in_folder(
        uploader.folder_online_files,
        uploader.cs_buy_auto_updater_users_filename,
        downloads_dir,
        try_compressed_version_first=True,
        download_only_if_server_version_is_newer=False,
        cache_max_seconds=0,
    )
    uploader.download_file_in_folder(
        uploader.folder_online_files,
        uploader.cs_used_card_secrets,
        downloads_dir,
        try_compressed_version_first=True,
        download_only_if_server_version_is_newer=True,
        cache_max_seconds=0,
    )

    # 需要登录才能使用的接口
    test_login_functions = False
    if test_login_functions:
        with open("upload_cookie.json") as fp:
            cookie = json.load(fp)
        uploader.login(cookie)
        if uploader.login_ok:
            # file = r"D:\_codes\Python\djc_helper_public\utils\bandizip_portable\bz.exe"
            # uploader.upload_to_lanzouyun(file, uploader.folder_djc_helper)
            # uploader.upload_to_lanzouyun(file, uploader.folder_dnf_calc)
            pass
        else:
            logger.error("登录失败")


def demo_downloads():
    uploader = Uploader()
    uploader.download_file_in_folder(
        uploader.folder_online_files,
        uploader.all_jiaoyile_orders_filename,
        downloads_dir,
        try_compressed_version_first=True,
        cache_max_seconds=0,
    )
    uploader.download_file_in_folder(
        uploader.folder_online_files,
        uploader.cs_used_card_secrets,
        downloads_dir,
        try_compressed_version_first=True,
        cache_max_seconds=0,
    )
    uploader.download_file_in_folder(
        uploader.folder_online_files,
        uploader.cs_user_monthly_pay_info_filename,
        downloads_dir,
        try_compressed_version_first=True,
        cache_max_seconds=0,
    )
    uploader.download_file_in_folder(
        uploader.folder_online_files,
        uploader.cs_buy_auto_updater_users_filename,
        downloads_dir,
        try_compressed_version_first=True,
        cache_max_seconds=0,
    )


if __name__ == "__main__":
    # demo()
    demo_downloads()
