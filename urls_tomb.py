from __future__ import annotations

from urls import get_act_url, newNotAmsActInfo, not_know_end_time____

# 将几乎可以确定不再会重新上线的活动代码挪到这里，从而减少 urls.py 的行数


not_ams_activities_tomb = [
    newNotAmsActInfo("2021-09-19 00:00:00", "2021-10-05 23:59:59", "qq会员杯"),
    newNotAmsActInfo("2022-01-20 00:00:00", "2022-02-28 23:59:59", "管家蚊子腿"),
    newNotAmsActInfo("2021-07-04 00:00:00", not_know_end_time____, "会员关怀"),
]

act_name_to_url_bomb = {
    "qq会员杯": "https://club.vip.qq.com/qqvip/acts2021/dnf",
    "qq视频-AME活动": "https://dnf.qq.com/cp/a20210816video/",
    "DNF十三周年庆活动": "https://dnf.qq.com/cp/a20210524fete/index.html",
    "管家蚊子腿": "https://sdi.3g.qq.com/v/2022011118372511947",
    "管家蚊子腿-旧版": "https://guanjia.qq.com/act/cop/20210425dnf/pc/",
    "DNF强者之路": "https://dnf.qq.com/cp/a20210312Strong/index.html",
    "会员关怀": "https://act.qzone.qq.com/v2/vip/tx/p/42034_cffe8db4",
    "DNF福签大作战": "https://dnf.qq.com/cp/a20210325sjlbv3pc/index.html",
    "燃放爆竹活动": "https://dnf.qq.com/cp/a20210118rfbz/index.html",
    "新春福袋大作战": "https://dnf.qq.com/cp/a20210108luckym/index.html",
    "史诗之路来袭活动合集": "https://dnf.qq.com/lbact/a20201224aggregate/index.html",
}


class UrlsTomb:
    def __init__(self):
        # amesvr通用活动
        self.iActivityId_qq_video_amesvr = "398546"  # qq视频-AME活动
        self.iActivityId_dnf_13 = "381033"  # DNF十三周年庆双端站点
        self.iActivityId_dnf_strong = "366330"  # DNF强者之路
        self.iActivityId_dnf_fuqian = "362403"  # DNF福签大作战
        self.iActivityId_firecrackers = "355187"  # 燃放爆竹活动
        self.iActivityId_spring_fudai = "354771"  # 新春福袋大作战
        self.iActivityId_dnf_1224 = "353266"  # DNF-1224渠道活动合集

        self.qzone_activity_club_vip = (
            "https://club.vip.qq.com/qqvip/api/tianxuan/access/execAct?g_tk={g_tk}&isomorphism-args={isomorphism_args}"
        )

        # 抽卡相关
        self.ark_lottery_page = get_act_url("集卡")
        # 查询次数信息：参数：to_qq, actName
        self.ark_lottery_query_left_times = 'https://proxy.vac.qq.com/cgi-bin/srfentry.fcgi?data={{"13320":{{"uin":{to_qq},"actName":"{actName}"}}}}&t={rand}&g_tk={g_tk}'
        # 赠送卡片：参数：cardId，from_qq，to_qq, actName
        self.ark_lottery_send_card = 'https://proxy.vac.qq.com/cgi-bin/srfentry.fcgi?data={{"13333":{{"cardId":{cardId},"fromUin":{from_qq},"toUin":{to_qq},"actName":"{actName}"}}}}&t={rand}&g_tk={g_tk}'

        # 电脑管家，额外参数：api/giftId/area_id/charac_no/charac_name
        self.guanjia = "https://act.guanjia.qq.com/bin/act/{api}.php?giftId={giftId}&area_id={area_id}&charac_no={charac_no}&charac_name={charac_name}&callback=jQueryCallback&isopenid=1&_={millseconds}"
        self.guanjia_new = "https://{domain_name}/{api}"
