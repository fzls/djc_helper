import json
from collections import namedtuple

from lanzou.api import LanZouCloud

from log import logger

Folder = namedtuple('Folder', ['name', 'id'])


class Uploader:
    folder_dnf_calc = Folder("魔改计算器", "1810329")
    folder_djc_helper = Folder("蚊子腿小助手", "2290618")
    folder_history_files = Folder("历史版本", "2303716")

    history_version_prefix = "DNF蚊子腿小助手_v"

    def __init__(self, cookie):
        self.lzy = LanZouCloud()
        self.login_ok = self.lzy.login_by_cookie(cookie) == LanZouCloud.SUCCESS

    def upload_to_lanzouyun(self, filepath, target_folder):
        def on_uploaded(fid, is_file):
            if not is_file:
                return

            logger.info("下载完成，fid={}".format(fid))

            files = self.lzy.get_file_list(target_folder.id)
            for file in files:
                if file.name.startswith(self.history_version_prefix):
                    self.lzy.move_file(file.id, self.folder_history_files.id)
                    logger.info("将{}移动到目录({})".format(file.name, self.folder_history_files.name))

            logger.info("将文件移到目录({})中".format(target_folder.name))
            self.lzy.move_file(fid, target_folder.id)

        # 上传到指定的文件夹中
        retCode = self.lzy.upload_file(filepath, -1, callback=self.show_progress, uploaded_handler=on_uploaded)
        if retCode != LanZouCloud.SUCCESS:
            logger.error("上传失败，retCode={}".format(retCode))
            return False

        return True

    def show_progress(self, file_name, total_size, now_size):
        """显示进度的回调函数"""
        percent = now_size / total_size
        bar_len = 40  # 进度条长总度
        bar_str = '>' * round(bar_len * percent) + '=' * round(bar_len * (1 - percent))
        print('\r{:.2f}%\t[{}] {:.1f}/{:.1f}MB | {} '.format(
            percent * 100, bar_str, now_size / 1048576, total_size / 1048576, file_name), end='')
        if total_size == now_size:
            print('')  # 下载完成换行


if __name__ == '__main__':
    with open("upload_cookie.json") as fp:
        cookie = json.load(fp)
    uploader = Uploader(cookie)
    if uploader.login_ok:
        file = r"D:\_codes\Python\djc_helper_public\bandizip_portable\bz.exe"
        uploader.upload_to_lanzouyun(file, uploader.folder_djc_helper)
        uploader.upload_to_lanzouyun(file, uploader.folder_dnf_calc)
    else:
        logger.error("登录失败")
