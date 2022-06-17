import json
import os.path
from datetime import timedelta
from typing import List, Optional

from const import downloads_dir
from data_struct import ConfigInterface, to_raw_type
from first_run import is_daily_first_run, is_first_run, is_monthly_first_run, is_weekly_first_run, reset_first_run
from log import logger
from update import version_less
from upload_lanzouyun import Uploader
from util import format_now, format_time, get_now, is_windows, message_box, parse_time, try_except
from version import now_version

if is_windows():
    import win32con


class NoticeShowType:
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALWAYS = "always"
    DEPRECATED = "deprecated"


valid_notice_show_type = {val for attr, val in NoticeShowType.__dict__.items() if not attr.startswith("__")}


class Notice(ConfigInterface):
    def __init__(self):
        self.sender = "风之凌殇"
        self.title = "测试消息标题"
        self.message = "测试消息内容"
        self.send_at = "2021-05-11 00:00:00"
        self.show_type = NoticeShowType.ONCE
        self.open_url = ""  # 若填入，在展示对应公告时会弹出该网页
        self.expire_at = "2121-05-11 00:00:00"
        self.show_only_before_version = now_version  # 若填入，则仅在对应版本前才会展示

    def __lt__(self, other):
        return parse_time(self.send_at) < parse_time(other.send_at)

    def need_show(self) -> bool:
        key = self.get_first_run_key()

        # 判断是否过期
        if get_now() > parse_time(self.expire_at):
            return False

        # 判断是否满足版本需求
        if self.show_only_before_version != "" and not version_less(now_version, self.show_only_before_version):
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

    def reset_first_run(self):
        reset_first_run(self.get_first_run_key())

    def get_first_run_key(self) -> str:
        return f"notice_need_show_{self.title}_{self.send_at}"


class NoticeManager:
    def __init__(self, load_from_remote=True):
        self.notices: List[Notice] = []

        self.file_name = "notices.txt"
        self.cache_path = f"{downloads_dir}/{self.file_name}"
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
        with open(path, encoding="utf-8") as save_file:
            for raw_notice in json.load(save_file):
                notice = Notice().auto_update_config(raw_notice)
                self.notices.append(notice)

        self.notices = sorted(self.notices)
        logger.info("公告读取完毕")

    def download_latest_notices(self):
        uploader = Uploader()

        dirpath, filename = os.path.dirname(self.cache_path), os.path.basename(self.cache_path)
        uploader.download_file_in_folder(
            uploader.folder_online_files, filename, dirpath, try_compressed_version_first=True
        )

    @try_except()
    def save(self):
        # 本地存盘
        with open(self.save_path, "w", encoding="utf-8") as save_file:
            json.dump(to_raw_type(self.notices), save_file, ensure_ascii=False, indent=2)
            logger.info("公告存盘完毕")

        # 上传到网盘
        uploader = Uploader()
        with open("upload_cookie.json") as fp:
            cookie = json.load(fp)
        uploader.login(cookie)
        uploader.upload_to_lanzouyun(
            self.save_path, uploader.folder_online_files, delete_history_file=True, also_upload_compressed_version=True
        )

    @try_except()
    def show_notices(self):
        valid_notices = list(filter(lambda notice: notice.need_show(), self.notices))

        logger.info(f"发现 {len(valid_notices)} 个新公告")
        for idx, notice in enumerate(valid_notices):
            # 展示公告
            message_box(
                notice.message,
                f"公告({idx + 1}/{len(valid_notices)}) - {notice.title}",
                icon=win32con.MB_ICONINFORMATION,
                open_url=notice.open_url,
                follow_flag_file=False,
            )

        logger.info("所有需要展示的公告均已展示完毕")

    def add_notice(
        self,
        title,
        message,
        sender="风之凌殇",
        send_at: str = "",
        show_type=NoticeShowType.ONCE,
        open_url="",
        valid_duration: Optional[timedelta] = None,
        show_only_before_version="",
    ):
        send_at = send_at or format_now()
        valid_duration = valid_duration or timedelta(days=7)

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
        notice.show_only_before_version = show_only_before_version

        self.notices.append(notice)
        logger.info(f"添加公告：{notice}")


def main():
    # 初始化
    nm = NoticeManager(load_from_remote=False)

    # note: 在这里添加公告
    title = "关于 无法在道聚城绑定dnf 与 禁用绝大部分活动 开关的说明"
    message = """在最近的版本中，增加了一个流程改动，如果你勾选了【无法在道聚城绑定dnf】，小助手将自动启用【禁用绝大部分活动】。
这是因为目前小助手中用于领奖的角色信息是通过道聚城绑定的dnf角色信息来确定的，如果你没有设置这个，理论上小助手无法为你领取绝大部分活动，只有集卡等不需要角色信息也能参与部分活动的除外

部分朋友可能错误理解了前者的含义，将其勾选了。但是实际上已经在道聚城app中绑定了dnf的角色信息，所以之前版本中，仍能够正常领取活动。
在新版本这个流程改动后，这种情况下，小助手会启用【禁用绝大部分活动】开关，导致活动都不能领取了。

如果你发现周年庆这两天几乎没有领到任何奖励，请检查你是否属于这种情况~ 如果你这个号是想要领取奖励的，请将这两个选项全部【取消勾选】

最后再介绍一下前面这个开关到底是干啥的，主要是用来给集卡的工具QQ用的，有些QQ可能一进DNF还没创角色就提示被封了，但是这种情况下还是可以集卡抽卡，给大号送卡的
"""
    open_url = ""
    show_only_before_version = ""

    if title != "":
        nm.add_notice(
            title,
            message,
            send_at=format_now(),
            show_type=NoticeShowType.ONCE,
            open_url=open_url,
            valid_duration=timedelta(days=7),
            show_only_before_version=show_only_before_version,
        )

    nm.save()


def test():
    nm = NoticeManager(load_from_remote=False)

    for notice in nm.notices:
        notice.reset_first_run()
        notice.show_only_before_version = ""

    logger.info("测试环境已重置完毕，所有公告都已改为未展示状态，且关闭版本限制")

    nm.show_notices()

    os.system("PAUSE")


if __name__ == "__main__":
    TEST = False
    from util import bypass_proxy

    bypass_proxy()

    if not TEST:
        main()
    else:
        test()
