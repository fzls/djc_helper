import os.path
from datetime import timedelta
from typing import List

from first_run import *
from upload_lanzouyun import Uploader


class NoticeShowType:
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALWAYS = "always"
    DEPRECATED = "deprecated"


valid_notice_show_type = set(attr for attr in NoticeShowType.__dict__.keys() if not attr.startswith("__"))


class Notice(ConfigInterface):
    def __init__(self):
        self.sender = "风之凌殇"
        self.title = "测试消息标题"
        self.message = "测试消息内容"
        self.send_at = "2021-05-11 00:00:00"
        self.show_type = NoticeShowType.ONCE
        self.open_url = ""  # 若填入，在展示对应公告时会弹出该网页
        self.expire_at = "2121-05-11 00:00:00"

    def __lt__(self, other):
        return parse_time(self.send_at) < parse_time(other.send_at)

    def need_show(self) -> bool:
        key = f"notice_need_show_{self.title}_{self.send_at}"

        # 判断是否过期
        if get_now() > parse_time(self.expire_at):
            return False

        # 根据显示类型判断
        if self.show_type == NoticeShowType.ONCE:
            return is_first_run(key)
        elif self.show_type == NoticeShowType.DAILY:
            return is_daily_first_run(key)
        elif self.show_type == NoticeShowType.WEEKLY:
            return is_weekly_first_run(key)
        elif self.show_type == NoticeShowType.MONTHLY:
            return is_monthly_first_run(key)
        elif self.show_type == NoticeShowType.ALWAYS:
            return True
        elif self.show_type == NoticeShowType.DEPRECATED:
            return False
        else:
            return False


class NoticeManager:
    def __init__(self, load_from_remote=True):
        self.notices = []  # type: List[Notice]

        self.file_name = "notices.txt"
        self.cache_path = f".cached/{self.file_name}"
        self.save_path = f"utils/{self.file_name}"

        self.load(load_from_remote)

    @try_except()
    def load(self, from_remote=True):
        if from_remote:
            path = self.cache_path
            # 下载最新公告
            self.download_latest_notices()
        else:
            path = self.save_path

        if not os.path.isfile(path):
            return

        # 读取公告
        with open(path, 'r', encoding='utf-8') as save_file:
            for raw_notice in json.load(save_file):
                notice = Notice().auto_update_config(raw_notice)
                self.notices.append(notice)

        self.notices = sorted(self.notices)
        logger.info("公告读取完毕")

    def download_latest_notices(self):
        uploader = Uploader()

        dirpath, filename = os.path.dirname(self.cache_path), os.path.basename(self.cache_path)
        uploader.download_file_in_folder(uploader.folder_online_files, filename, dirpath, try_compressed_version_first=True)

    @try_except()
    def save(self):
        # 本地存盘
        with open(self.save_path, 'w', encoding='utf-8') as save_file:
            json.dump(to_raw_type(self.notices), save_file, ensure_ascii=False, indent=2)
            logger.info("公告存盘完毕")

        # 上传到网盘
        uploader = Uploader()
        with open("upload_cookie.json") as fp:
            cookie = json.load(fp)
        uploader.login(cookie)
        uploader.upload_to_lanzouyun(self.save_path, uploader.folder_online_files, also_upload_compressed_version=True)

    @try_except()
    def show_notices(self):
        valid_notices = list(filter(lambda notice: notice.need_show(), self.notices))

        logger.info(f"发现 {len(valid_notices)} 个新公告")
        for idx, notice in enumerate(valid_notices):
            # 展示公告
            message_box(notice.message, f"公告({idx + 1}/{len(valid_notices)}) - {notice.title}", icon=win32con.MB_ICONINFORMATION, open_url=notice.open_url)

        logger.info("所有需要展示的公告均已展示完毕")

    def add_notice(self, title, message, sender="风之凌殇", send_at=format_now(), show_type=NoticeShowType.ONCE, open_url="", valid_duration=timedelta(days=7)):
        if show_type not in valid_notice_show_type:
            logger.error(f"无效的show_type={show_type}，有效值为{valid_notice_show_type}")
            return

        for old_notice in self.notices:
            if old_notice.title == title and old_notice.message == message and old_notice.sender == sender:
                logger.error(f"发现内容完全一致的公告，请确定是否是误操作，若非误操作请去文本直接修改。\n{old_notice}")
                return

        notice = Notice()
        notice.title = title
        notice.message = message
        notice.sender = sender
        notice.send_at = send_at
        notice.show_type = show_type
        notice.open_url = open_url
        notice.expire_at = format_time(get_now() + valid_duration)

        self.notices.append(notice)
        logger.info(f"添加公告：{notice}")


def main():
    # 初始化
    nm = NoticeManager(load_from_remote=False)

    # note: 在这里添加公告
    title = "关于超快速模式的额外说明"
    message = """超快速模式下可能会经常弹窗提示，这个问题是已知的，目前不太好解决。如果无法接受这个，请关闭超快速模式~
    
原因说明如下
目前判断是否需要弹窗的数据是存到.db/db.json文件中，弹窗功能的次数和时机按预期表现依赖于这个文件是正常的。
由于目前的本地数据的读写是线程不安全的，而在超快速模式下，默认进程数是4*cpu，很容易出现同时读写导致数据文件损坏而重置的情况。
因此在这种情况下，之后再查询这个数据文件时，相关弹窗的数据都会丢失，因此会再次弹出-。-
"""
    nm.add_notice(title, message,
                  send_at=format_now(),
                  show_type=NoticeShowType.ONCE, open_url="", valid_duration=timedelta(days=7))

    nm.save()


if __name__ == '__main__':
    main()
