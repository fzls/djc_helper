import json
import lzma
import os
import re
from collections import namedtuple
from datetime import datetime
from typing import List

from lanzou.api import LanZouCloud
from lanzou.api.types import FileInFolder, FolderDetail

from log import logger, color
from util import make_sure_dir_exists, with_cache, human_readable_size, cache_name_download

Folder = namedtuple('Folder', ['name', 'id', 'url', 'password'])


# 参考文档可见：https://github.com/zaxtyson/LanZouCloud-API/wiki

class Uploader:
    folder_dnf_calc = Folder("魔改计算器", "1810329", "https://fzls.lanzous.com/s/dnf-calc", "")
    folder_djc_helper = Folder("蚊子腿小助手", "2290618", "https://fzls.lanzous.com/s/djc-helper", "")
    folder_history_files = Folder("历史版本", "2303716", "https://fzls.lanzous.com/b01bp17zg", "")
    folder_online_files = Folder("在线文件存储", "2866929", "https://fzls.lanzous.com/s/myfiles", "6tnk")
    folder_online_files_history_files = Folder("历史版本", "2867307", "https://fzls.lanzous.com/b01c143ah", "5r75")

    history_version_prefix = "DNF蚊子腿小助手_v"
    history_patches_prefix = "DNF蚊子腿小助手_增量更新文件_"

    regex_version = r'DNF蚊子腿小助手_v(.+)_by风之凌殇.7z'
    regex_patches = r'DNF蚊子腿小助手_增量更新文件_v(.+)_to_v(.+).7z'

    # 保存购买了自动更新工具的用户信息
    buy_auto_updater_users_filename = "buy_auto_updater_users.txt"

    # 保存用户的付费信息
    user_monthly_pay_info_filename = "user_monthly_pay_info.txt"

    # 卡密操作的付费信息
    cs_used_card_secrets = "_used_card_secrets.txt"
    cs_buy_auto_updater_users_filename = "cs_buy_auto_updater_users.txt"
    cs_user_monthly_pay_info_filename = "cs_user_monthly_pay_info.txt"

    # 压缩版本的前后缀
    compressed_version_prefix = "compressed_"
    compressed_version_suffix = ".7z"

    def __init__(self):
        self.lzy = LanZouCloud()
        self.login_ok = False

    def login(self, cookie):
        # 仅上传需要登录
        self.login_ok = self.lzy.login_by_cookie(cookie) == LanZouCloud.SUCCESS

    def upload_to_lanzouyun(self, filepath: str, target_folder: Folder, history_file_prefix="", also_upload_compressed_version=False, only_upload_compressed_version=False) -> bool:
        if not self.login_ok:
            logger.info("未登录，不能上传文件")
            return False

        if history_file_prefix == "":
            # 未设置历史文件前缀，默认为当前文件名
            history_file_prefix = os.path.basename(filepath)

        if not only_upload_compressed_version:
            ok = self._upload_to_lanzouyun(filepath, target_folder, history_file_prefix)
            if not ok:
                return False

        if also_upload_compressed_version:
            make_sure_dir_exists('.cached')
            filename = os.path.basename(filepath)
            compressed_filepath = os.path.join('.cached', self.get_compressed_version_filename(filename))
            compressed_history_file_prefix = f"{self.compressed_version_prefix}{history_file_prefix}"

            logger.info(color("bold_green") + f"创建压缩版本并上传 {compressed_filepath}")
            # 创建压缩版本
            with open(f"{filepath}", "rb") as file_in:
                with lzma.open(f"{compressed_filepath}", "wb") as file_out:
                    file_out.writelines(file_in)
            # 上传
            return self._upload_to_lanzouyun(compressed_filepath, target_folder, compressed_history_file_prefix)

        return True

    def _upload_to_lanzouyun(self, filepath: str, target_folder: Folder, history_file_prefix) -> bool:
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
                    self.lzy.move_file(file.id, folder_history_files.id)
                    logger.info(f"将{file.name}移动到目录({folder_history_files.name})")

            logger.info(f"将文件移到目录({target_folder.name})中")
            self.lzy.move_file(fid, target_folder.id)

        # 上传到指定的文件夹中
        retCode = self.lzy.upload_file(filepath, -1, callback=self.show_progress, uploaded_handler=on_uploaded)
        if retCode != LanZouCloud.SUCCESS:
            logger.error(f"上传失败，retCode={retCode}")
            return False

        filesize = os.path.getsize(filepath)
        logger.warning(color("bold_yellow") + f"上传文件 {filename}({human_readable_size(filesize)}) 总计耗时{datetime.now() - run_start_time}")

        return True

    def get_compressed_version_filename(self, filename: str) -> str:
        return f"{self.compressed_version_prefix}{filename}{self.compressed_version_suffix}"

    def latest_version(self) -> str:
        """
        返回形如"1.0.0"的最新版本信息
        """
        latest_version_file = self.find_latest_version()
        # DNF蚊子腿小助手_v4.6.6_by风之凌殇.7z
        match = re.search(self.regex_version, latest_version_file.name)
        if match is not None:
            latest_version = match.group(1)
            return latest_version

        # 保底返回1.0.0
        return "1.0.0"

    def download_latest_version(self, download_dir) -> str:
        """
        下载最新版本压缩包到指定目录，并返回最终压缩包的完整路径
        """
        return self.download_file(self.find_latest_version(), download_dir)

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

    def download_file_in_folder(self, folder: Folder, name: str, download_dir: str, overwrite=True, show_log=True, try_compressed_version_first=False, cache_max_seconds=600) -> str:
        """
        下载网盘指定文件夹的指定文件到本地指定目录，并返回最终本地文件的完整路径
        """

        def _download(fname: str) -> str:
            return with_cache(cache_name_download, os.path.join(folder.name, fname), cache_max_seconds=cache_max_seconds,
                              cache_miss_func=lambda: self.download_file(self.find_file(folder, fname), download_dir, overwrite=overwrite, show_log=show_log),
                              cache_validate_func=lambda target_path: os.path.isfile(target_path),
                              )

        if try_compressed_version_first:
            # 先尝试获取压缩版本
            compressed_filename = self.get_compressed_version_filename(name)
            try:
                if show_log: logger.info(color("bold_green") + f"尝试优先下载压缩版本 {compressed_filename}")
                # 下载压缩版本
                compressed_filepath = _download(compressed_filename)

                # 解压缩
                dirname = os.path.dirname(compressed_filepath)
                target_path = os.path.join(dirname, name)
                with lzma.open(f"{compressed_filepath}", "rb") as file_in:
                    with open(f"{target_path}", "wb") as file_out:
                        file_out.writelines(file_in)
                # 返回解压缩的文件路径
                return target_path
            except Exception as e:
                if show_log: logger.error(f"下载压缩版本 {compressed_filename} 失败，将尝试普通版本~", exc_info=e)

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

    def download_file(self, fileinfo: FileInFolder, download_dir: str, overwrite=True, show_log=True) -> str:
        """
        下载最新版本压缩包到指定目录，并返回最终压缩包的完整路径
        """
        if not os.path.isdir(download_dir):
            os.mkdir(download_dir)

        download_dir = os.path.realpath(download_dir)
        target_path = os.path.join(download_dir, fileinfo.name)

        def after_downloaded(file_name):
            """下载完成后的回调函数"""
            target_path = file_name
            if show_log: logger.info(f"最终下载文件路径为 {file_name}")

        if show_log: logger.info(f"即将开始下载 {target_path}")
        callback = None
        if show_log: callback = self.show_progress
        retCode = self.down_file_by_url(fileinfo.url, "", download_dir, callback=callback, downloaded_handler=after_downloaded, overwrite=overwrite)
        if retCode != LanZouCloud.SUCCESS:
            if show_log: logger.error(f"下载失败，retCode={retCode}")
            if retCode == LanZouCloud.NETWORK_ERROR:
                if show_log: logger.warning(color("bold_yellow") + (
                    "蓝奏云api返回网络错误，这很可能是由于dns的问题导致的\n"
                    "分别尝试在浏览器中访问下列两个网页，是否一个打的开一个打不开？\n"
                    "https://fzls.lanzoux.com/s/djc-helper\n"
                    "https://fzls.lanzous.com/s/djc-helper\n"
                    "\n"
                    "如果是这样，请按照下面这个链接，修改本机的dns，使用阿里、腾讯、百度、谷歌dns中的任意一个应该都可以解决。\n"
                    "https://www.ypojie.com/9830.html\n"
                    "\n"
                    "如果两个都打不开，大概率是蓝奏云挂了-。-可选择忽略后面的弹框，继续运行旧版本，或者手动去QQ群或github下载最新版本"
                ))
            raise Exception("下载失败")

        return target_path

    def show_progress(self, file_name, total_size, now_size):
        """显示进度的回调函数"""
        percent = now_size / total_size
        bar_len = 40  # 进度条长总度
        bar_str = '>' * round(bar_len * percent) + '=' * round(bar_len * (1 - percent))
        show_percent = percent * 100
        now_mb = now_size / 1048576
        total_mb = total_size / 1048576
        print(f'\r{show_percent:.2f}%\t[{bar_str}] {now_mb:.2f}/{total_mb:.2f}MB | {file_name} ', end='')
        if total_size == now_size:
            print('')  # 下载完成换行

    def get_folder_info_by_url(self, share_url, dir_pwd='') -> FolderDetail:
        for possiable_url in self.all_possiable_urls(share_url):
            folder_info = self.lzy.get_folder_info_by_url(possiable_url, dir_pwd)
            if folder_info.code != LanZouCloud.SUCCESS:
                logger.debug(f"请求{possiable_url}失败，将尝试下一个")
                continue

            return folder_info

        return FolderDetail(LanZouCloud.FAILED)

    def down_file_by_url(self, share_url, pwd='', save_path='./Download', *, callback=None, overwrite=False,
                         downloaded_handler=None) -> int:
        for possiable_url in self.all_possiable_urls(share_url):
            retCode = self.lzy.down_file_by_url(possiable_url, pwd, save_path, callback=callback, overwrite=overwrite, downloaded_handler=downloaded_handler)
            if retCode != LanZouCloud.SUCCESS:
                logger.debug(f"请求{possiable_url}失败，将尝试下一个")
                continue

            return retCode

        return LanZouCloud.FAILED

    def all_possiable_urls(self, lanzouyun_url: str) -> List[str]:
        old_domain = 'fzls.lanzous'
        return [
            # 首先尝试传入的url
            lanzouyun_url,

            # 目前网盘默认分享链接是这个，后面可以根据经验，哪个最靠谱，调整先后顺序
            lanzouyun_url.replace(old_domain, 'wwx.lanzoui'),

            # 本地测试当前可用的域名，后续可以调整
            lanzouyun_url.replace(old_domain, 'pan.lanzoui'),
            lanzouyun_url.replace(old_domain, 'up.lanzoui'),
            lanzouyun_url.replace(old_domain, 'wws.lanzoui'),
            lanzouyun_url.replace(old_domain, 'www.lanzoui'),

            lanzouyun_url.replace(old_domain, 'pan.lanzoux'),
            lanzouyun_url.replace(old_domain, 'up.lanzoux'),
            lanzouyun_url.replace(old_domain, 'wws.lanzoux'),
            lanzouyun_url.replace(old_domain, 'www.lanzoux'),
            lanzouyun_url.replace(old_domain, 'wwx.lanzoux'),

            lanzouyun_url.replace(old_domain, 'wwx.lanzous'),

            # 其余备用的域名，测试时暂时不可用
            lanzouyun_url.replace(old_domain, 'pan.lanzous'),
            lanzouyun_url.replace(old_domain, 'up.lanzous'),
            lanzouyun_url.replace(old_domain, 'wws.lanzous'),
            lanzouyun_url.replace(old_domain, 'www.lanzous'),
        ]


if __name__ == '__main__':
    uploader = Uploader()

    # 不需要登录的接口
    logger.info(f"最新版本为{uploader.latest_version()}")
    # uploader.download_latest_version(".cached")

    logger.info(f"最新增量补丁范围为{uploader.latest_patches_range()}")
    logger.info(f"最新增量补丁为{uploader.find_latest_patches()}")
    uploader.download_latest_patches(".cached")

    uploader.download_file_in_folder(uploader.folder_online_files, uploader.cs_user_monthly_pay_info_filename, ".cached", try_compressed_version_first=True)

    # 需要登录才能使用的接口
    test_login_functions = False
    if test_login_functions:
        with open("upload_cookie.json") as fp:
            cookie = json.load(fp)
        uploader.login(cookie)
        if uploader.login_ok:
            # file = r"D:\_codes\Python\djc_helper_public\bandizip_portable\bz.exe"
            # uploader.upload_to_lanzouyun(file, uploader.folder_djc_helper)
            # uploader.upload_to_lanzouyun(file, uploader.folder_dnf_calc)
            pass
        else:
            logger.error("登录失败")
