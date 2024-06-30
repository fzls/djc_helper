from __future__ import annotations

import json
import os.path
from datetime import timedelta

from const import downloads_dir
from data_struct import ConfigInterface, to_raw_type
from download import download_github_raw_content
from first_run import is_daily_first_run, is_first_run, is_monthly_first_run, is_weekly_first_run, reset_first_run
from log import logger
from update import version_less
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
    current_notices_file_name = "notices.txt"
    archived_notices_file_name = "notice_archived.txt"

    def __init__(self, load_from_remote=True, download_only_if_not_exists=False):
        """

        :param load_from_remote: 是否从远程加载配置文件，目前仅在本地添加公告时，该值会为False
        :param download_only_if_not_exists: 是否仅在文件不存在时下载。在本体运行时，该值为False，而通过配置工具调用时，则取True
        """
        self.notices: list[Notice] = []

        self.file_name = self.current_notices_file_name

        self.load(load_from_remote, download_only_if_not_exists)

    @property
    def cache_path(self) -> str:
        return f"{downloads_dir}/{self.file_name}"

    @property
    def save_path(self) -> str:
        return f"utils/{self.file_name}"

    @try_except()
    def load(self, from_remote=True, download_only_if_not_exists=False):
        if from_remote:
            path = self.cache_path

            need_download = True
            if download_only_if_not_exists and os.path.exists(path):
                # 设置了仅当本地文件不存在时才下载
                need_download = False

            if need_download:
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
        dirpath = os.path.dirname(self.cache_path)
        download_github_raw_content(self.save_path, dirpath)

    @try_except()
    def save(self):
        # 本地存盘
        with open(self.save_path, "w", encoding="utf-8") as save_file:
            json.dump(to_raw_type(self.notices), save_file, ensure_ascii=False, indent=2)
            logger.info("公告存盘完毕")

        logger.warning("稍后请自行提交修改后的公告到github")

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
        valid_duration: timedelta | None = None,
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
    title = "24.6 卡妮娜活动修正说明"
    message = """刚刚新版本里的卡妮娜活动的描述有问题，但也没必要发个新版本，这里重新说明下参与流程

本质确实是拉人头的拼多多活动
如果你有4个回归小号（比如那种每年领周年庆代币券的号），那么你可以按下面的流程领取到50元
0. 一阶段（拉回归号）
    1. 大号登录活动页面 https://dnf.qq.com/cp/a20240613wish/indexm.html，进来可以抽一次，同时可以获得3次抽奖励内容的机会
    2. 点击右下角的扫码助力，点复制链接，获得一阶段的链接，发给自己的小号
    3. 使用3个小号分别点进去这个链接，一直进行到完成收下那个【50元奖励】到奖励池，每次大号会获得2次添加奖池机会
    4. 前面几步凑满10次后，一直按下面的抽奖池，把奖池弄满
1. 二阶段（拉登录游戏过的回归号）
    1. 大号再次打开这个活动页面，疯狂点中间的按钮，刷新心愿名单，直到【邀请4位回归】和【邀请2位回归】都在列表里了
    点右下角的扫码助力，点复制链接，获得二阶段的链接，发给自己的小号
    2. 使用4个小号分别执行下面操作
        1. 登录游戏，选一个角色进入赛利亚房间，再随便选个其他频道跳过去，从而被认定为回流玩家
        2. 打开二阶段的链接，点击宝箱，选择【接受邀请】
    3. 执行完上述操作后，大号在页面里领取这两个心愿的奖励，得到6个进度值，然后点【50元】的那个格子，领取奖励

    PS: 不确定先把条件达成，再随机出这个任务，是否也能领取。所以最稳妥是先把这俩任务都碎出来，再操作。实在弄不出来，可以试试先弄完条件，然后一个个随出来，看看是否也可以领

 每个奖励都是达到对应列的指定进度值就可以领了，所以其他奖励如果你也想要，也可以随对应任务然后去完成
"""
    open_url = ""
    show_only_before_version = ""
    valid_duration = timedelta(days=7)

    if title != "":
        nm.add_notice(
            title,
            message,
            send_at=format_now(),
            show_type=NoticeShowType.ONCE,
            open_url=open_url,
            valid_duration=valid_duration,
            show_only_before_version=show_only_before_version,
        )

    nm.save()


def test():
    nm = NoticeManager(load_from_remote=True)

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
