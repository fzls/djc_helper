from sys import exit

from config_cloud import config_cloud
from util import message_box, uin2qq


class BlackListInfo:
    def __init__(self, ban_at, qq, nickname, reason):
        self.ban_at = ban_at
        self.qq = qq
        self.nickname = nickname
        self.reason = reason

    def __str__(self):
        return f"{self.qq}({self.nickname})在{self.ban_at}因[{self.reason}]被本工具拉入黑名单"


# fmt: off
black_list = {
    "823985815": BlackListInfo("2021-01-05", "823985815", "章鱼宝宝。", "伸手党，不看提示直接开问"),
    "1531659746": BlackListInfo("2021-01-20", "1531659746", "北望", "别人图氛围说继续发红包时，骂别人网络乞丐，然后被踢后，加我说我是傻逼罢了"),
    "262163207": BlackListInfo("2021-01-31", "262163207", "孤独患者", "说了不要问我疲劳药怎么设置，也看到注释的内容了，还要问，还说我优越感很强。既然合不来，就再见吧。"),
    "69512151": BlackListInfo("2021-02-22", "69512151", "不知道是谁", "做坏事，永久拉黑"),
    "642364310": BlackListInfo("2021-02-22", "642364310", "不知道是谁", "做坏事，永久拉黑"),
    "39752616": BlackListInfo("2021-02-22", "39752616", "不知道是谁", "做坏事，永久拉黑"),
    "4838116": BlackListInfo("2021-04-03", "4838116", "玉簪子", "不可理喻"),
    "1832447846": BlackListInfo("2021-04-17", "1832447846", "欧皇", "在半夜修完bug通知群友修好了的时候，跑出来一句：大晚上的@nm的全体啊"),
    "410639497": BlackListInfo("2021-06-11", "410639497", "一人一世界", "看不懂中文，提示写的明明白白了，让他绑定道聚城，还要问个不停"),
    "931394485": BlackListInfo("2021-08-02", "931394485", "将夜", "说卡丢了，回复应该没有这种问题，如果真怀疑是小助手的问题，可以退款停止使用，最后骂我是 麻痹脑残"),
    "79608835": BlackListInfo("2021-12-11", "79608835", "                      . ", "私聊问问题，问完来一句：那你没用了。没有一点点基本的礼貌"),
    "741038971": BlackListInfo("2021-12-31", "741038971", "㞢卄", "进群里发【我咋能明白的/集卡链接/去你妈的一群Sb】，然后自己退群，莫名其妙"),
}
# fmt: on


def try_update_black_list():
    remote_config = config_cloud()
    for info in remote_config.black_list:
        if info.qq in black_list:
            continue

        black_list[info.qq] = BlackListInfo(info.ban_at, info.qq, info.nickname, info.reason)


def check_in_black_list(uin):
    try_update_black_list()

    qq = uin2qq(uin)
    if qq in black_list:
        message = (
            "发现你的QQ在本工具的黑名单里，本工具禁止你使用，将在本窗口消失后退出运行。\n"
            "黑名单相关信息如下：\n"
            f"{black_list[qq]}\n"
            "\n"
            "如果有未使用完的付费时长，请私聊支付宝账号，按实际剩余时长退款。"
        )
        message_box(message, "禁止使用")
        exit(0)


if __name__ == "__main__":
    check_in_black_list("o823985815")
