from __future__ import annotations

from urls import newNotAmsActInfo

# 将几乎可以确定不再会重新上线的活动代码挪到这里，从而减少 urls.py 的行数


not_ams_activities_tomb = [
    newNotAmsActInfo("2021-09-19 00:00:00", "2021-10-05 23:59:59", "qq会员杯"),
]


act_name_to_url_bomb = {
    "qq会员杯": "https://club.vip.qq.com/qqvip/acts2021/dnf",
}

class UrlsTomb:
    def __init__(self):
        # amesvr通用活动
        self.iActivityId_qq_video_amesvr = "398546"  # qq视频-AME活动
