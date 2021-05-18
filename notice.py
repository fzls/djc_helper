import json
import os.path
from typing import List

import win32con

from data_struct import ConfigInterface, to_raw_type
from log import logger
from upload_lanzouyun import Uploader
from util import format_now, parse_time, try_except, is_first_run, is_daily_first_run, is_weekly_first_run, is_monthly_first_run, message_box

NOTICE_SHOW_TYPE_ONCE = "once"
NOTICE_SHOW_TYPE_DAILY = "daily"
NOTICE_SHOW_TYPE_WEEKLY = "weekly"
NOTICE_SHOW_TYPE_MONTHLY = "monthly"
NOTICE_SHOW_TYPE_ALWAYS = "always"
NOTICE_SHOW_TYPE_DEPRECATED = "deprecated"

valid_notice_show_type = set(v for k, v in locals().items() if k.startswith("NOTICE_SHOW_TYPE_"))


class Notice(ConfigInterface):
    def __init__(self):
        self.sender = "风之凌殇"
        self.title = "测试消息标题"
        self.message = "测试消息内容"
        self.send_at = "2021-05-11 00:00:00"
        self.show_type = NOTICE_SHOW_TYPE_ONCE
        self.open_url = ""  # 若填入，在展示对应公告时会弹出该网页

    def __lt__(self, other):
        return parse_time(self.send_at) < parse_time(other.send_at)

    def need_show(self) -> bool:
        key = f"notice_need_show_{self.title}_{self.send_at}"

        if self.show_type == NOTICE_SHOW_TYPE_ONCE:
            return is_first_run(key)
        elif self.show_type == NOTICE_SHOW_TYPE_DAILY:
            return is_daily_first_run(key)
        elif self.show_type == NOTICE_SHOW_TYPE_WEEKLY:
            return is_weekly_first_run(key)
        elif self.show_type == NOTICE_SHOW_TYPE_MONTHLY:
            return is_monthly_first_run(key)
        elif self.show_type == NOTICE_SHOW_TYPE_ALWAYS:
            return True
        elif self.show_type == NOTICE_SHOW_TYPE_DEPRECATED:
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
        for notice in self.notices:
            if not notice.need_show():
                continue

            # 展示公告
            message_box(notice.message, f"公告-{notice.title}", icon=win32con.MB_ICONINFORMATION, open_url=notice.open_url)

        logger.info("所有需要展示的公告均已展示完毕")

    def add_notice(self, title, message, sender="风之凌殇", send_at=format_now(), show_type=NOTICE_SHOW_TYPE_ONCE, open_url=""):
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

        self.notices.append(notice)
        logger.info(f"添加公告：{notice}")


def main():
    # 初始化
    nm = NoticeManager(load_from_remote=False)

    # note: 在这里添加公告
    title = "手机间接运行小助手方案"
    message = """目前可以通过以下方案来实现手机上间接运行小助手
1. 远程连接家里的电脑
    通过windows自带的远程桌面或者下载向日葵、teamviewer等远程控制软件，实现在手机上连接家里电脑，然后点击运行
    这种方案优点是省事安全且不花钱，缺点是需要家里的电脑也有对应远程控制软件，并保持联网和开机

2. 使用云电脑
    使用各种云电脑来下载安装小助手进行使用，这样电脑不在身边的时候也能使用小助手。
    这种方案优点是方便，可以随时随地去用，缺点是可能需要根据使用时间来付费，此外如果使用的平台不靠谱的话，可能账号会有危险。
    
    可以先在家里电脑下载安装并配置好小助手后，打一个压缩包，上传到仅自己可以看到的网盘，比如QQ自带的网盘。然后在云电脑上下载下来，解压缩后就可以直接用了。
    
    下面以网易云电脑为例说明下使用流程：
    打开https://cg.163.com/#/pc，使用手机扫码下载app，安装并登陆后点击PC游戏tab下的云电脑，在里面下载小助手去运行就好了。
    如果使用浏览器下载提示有病毒而不让下载的话，可以先下个迅雷，然后把下载地址复制到迅雷里来下载，实现曲线救国。
    
    目前每天签到送15分钟，足够拿来运行小助手了。
    如果免费时长不够，目前的收费好像是180云币/小时（相当于1.8元），按分钟使用，用完就退出的话，这样单个号每次假设运行3分钟，那么1.8元可以运行20次=、=
    
    如果没注册过网易云游戏的话，可以用下面这个邀请链接，注册后会送我一点时长，虽然我也暂时用不到<_<
    https://cloudgame.webapp.163.com/newer.html?invite_code=L2Q5VN
"""
    nm.add_notice(title, message,
                  send_at=format_now(),
                  show_type=NOTICE_SHOW_TYPE_ONCE, open_url="")

    nm.save()


if __name__ == '__main__':
    main()
