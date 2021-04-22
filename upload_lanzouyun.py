import json
import lzma
import os
import re
from collections import namedtuple
from datetime import datetime

from lanzou.api import LanZouCloud

from log import logger, color
from util import make_sure_dir_exists, with_cache, human_readable_size

lanzou_cookie = {
    "ylogin": "1442903",
    "phpdisk_info": "VmNRZwxqBDpSaVMzXTRWBVIzDDoIWF07ADRVNgczV21UYgU2VzYFOVVhUjdcDwdqWz9QZ108VDQHYQdvATcLO1ZhUTUMOgQ8UjZTYl1iVmpSNwxsCGZdPAAxVTwHNlcxVGAFY1c0BWpVM1I0XD8HVFs6UGVdN1QxBzwHZQE2CzpWYlFlDGs%3D",
}

Folder = namedtuple('Folder', ['name', 'id'])


# 参考文档可见：https://github.com/zaxtyson/LanZouCloud-API/wiki

class Uploader:
    folder_dnf_calc = Folder("魔改计算器", "1810329")
    folder_djc_helper = Folder("蚊子腿小助手", "2290618")
    folder_history_files = Folder("历史版本", "2303716")
    folder_online_files = Folder("在线文件存储", "2866929")
    folder_online_files_history_files = Folder("历史版本", "2867307")

    history_version_prefix = "DNF蚊子腿小助手_v"
    history_patches_prefix = "DNF蚊子腿小助手_增量更新文件_"

    regex_version = r'DNF蚊子腿小助手_v(.+)_by风之凌殇.7z'
    regex_patches = r'DNF蚊子腿小助手_增量更新文件_v(.+)_to_v(.+).7z'

    # 保存购买了自动更新工具的用户信息
    buy_auto_updater_users_filename = "buy_auto_updater_users.txt"

    # 保存用户的付费信息
    user_monthly_pay_info_filename = "user_monthly_pay_info.txt"

    # 卡密操作的付费信息
    cs_buy_auto_updater_users_filename = "cs_buy_auto_updater_users.txt"
    cs_user_monthly_pay_info_filename = "cs_user_monthly_pay_info.txt"

    # 压缩版本的前后缀
    compressed_version_prefix = "compressed_"
    compressed_version_suffix = ".7z"

    def __init__(self, cookie):
        self.lzy = LanZouCloud()
        self.login_ok = self.lzy.login_by_cookie(cookie) == LanZouCloud.SUCCESS

    def upload_to_lanzouyun(self, filepath, target_folder, history_file_prefix="", also_upload_compressed_version=False) -> bool:
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

    def _upload_to_lanzouyun(self, filepath, target_folder, history_file_prefix="") -> bool:
        filename = os.path.basename(filepath)
        logger.warning(f"开始上传 {filename} 到 {target_folder.name}")
        run_start_time = datetime.now()

        def on_uploaded(fid, is_file):
            if not is_file:
                return

            logger.info(f"上传完成，fid={fid}")

            prefix = history_file_prefix
            if prefix == "":
                prefix = self.history_version_prefix

            folder_history_files = self.folder_history_files
            if target_folder.id == self.folder_online_files.id:
                folder_history_files = self.folder_online_files_history_files

            files = self.lzy.get_file_list(target_folder.id)
            for file in files:
                if file.name.startswith(prefix):
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
        logger.warning(f"上传文件 {filename}({human_readable_size(filesize)}) 总计耗时{datetime.now() - run_start_time}")

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

    def find_latest_version(self):
        """
        查找最新版本，如找到，返回lanzouyun提供的file信息，否则抛出异常
        """
        files = self.lzy.get_file_list(self.folder_djc_helper.id)
        for file in files:
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

    def find_latest_patches(self):
        """
        查找最新版本的补丁，如找到，返回lanzouyun提供的file信息，否则抛出异常
        """
        files = self.lzy.get_file_list(self.folder_djc_helper.id)
        for file in files:
            if file.name.startswith(self.history_patches_prefix):
                return file

        raise FileNotFoundError("latest patches not found")

    def download_file_in_folder(self, folder: Folder, name, download_dir, overwrite=True, show_log=True, try_compressed_version_first=False, cache_max_seconds=600) -> str:
        """
        下载网盘指定文件夹的指定文件到本地指定目录，并返回最终本地文件的完整路径
        """

        def _download(fname: str) -> str:
            return with_cache("download_cache", os.path.join(folder.name, fname), cache_max_seconds=cache_max_seconds,
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

    def find_file(self, folder, name):
        """
        在对应目录查找指定名称的文件，如找到，返回lanzouyun提供的file信息，否则抛出异常
        """
        files = self.lzy.get_file_list(folder.id)
        for file in files:
            if file.name == name:
                return file

        raise FileNotFoundError(f"file={name} not found in folder={folder.name}")

    def download_file(self, fileinfo, download_dir, overwrite=True, show_log=True) -> str:
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
        retCode = self.lzy.down_file_by_id(fileinfo.id, download_dir, callback=callback, downloaded_handler=after_downloaded, overwrite=overwrite)
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


if __name__ == '__main__':
    with open("upload_cookie.json") as fp:
        cookie = json.load(fp)
    uploader = Uploader(cookie)
    if uploader.login_ok:
        # file = r"D:\_codes\Python\djc_helper_public\bandizip_portable\bz.exe"
        # uploader.upload_to_lanzouyun(file, uploader.folder_djc_helper)
        # uploader.upload_to_lanzouyun(file, uploader.folder_dnf_calc)
        # logger.info(f"最新版本为{uploader.latest_version()}")
        # uploader.download_latest_version("_update_temp_dir")

        logger.info(f"最新增量补丁范围为{uploader.latest_patches_range()}")
        # uploader.download_latest_patches("_update_temp_dir")
    else:
        logger.error("登录失败")
