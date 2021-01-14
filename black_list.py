from sys import exit

import win32api
import win32con

from log import logger, color
from util import uin2qq


class BlackListInfo:
    def __init__(self, ban_at, qq, nickname, reason):
        self.ban_at = ban_at
        self.qq = qq
        self.nickname = nickname
        self.reason = reason

    def __str__(self):
        return f"{self.qq}({self.nickname})在{self.ban_at}因[{self.reason}]被本工具拉入黑名单"


black_list = {
    "823985815": BlackListInfo("2021-01-05", "823985815", "章鱼宝宝。", "伸手党，不看提示直接开问"),
}


def check_in_black_list(uin):
    qq = uin2qq(uin)
    if qq in black_list:
        message = (
            "发现你的QQ在本工具的黑名单里，本工具禁止你使用，将在本窗口消失后退出运行。\n"
            "黑名单相关信息如下：\n"
            f"{black_list[qq]}"
        )
        logger.warning(color("fg_bold_cyan") + message)
        win32api.MessageBox(0, message, "禁止使用", win32con.MB_OK)
        exit(0)


if __name__ == '__main__':
    check_in_black_list("o823985815")
