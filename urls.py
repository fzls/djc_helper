import json
import os
from typing import List, Optional

import requests

from const import cached_dir
from dao import ActCommonInfo, AmsActInfo, IdeActInfo
from log import color, logger
from util import (
    exists_flag_file,
    format_time,
    get_now,
    get_past_time,
    get_remaining_time,
    is_act_expired,
    make_sure_dir_exists,
    padLeftRight,
    parse_time,
    start_and_end_date_of_a_month,
    tableify,
    try_except,
    with_cache,
)

# 活动描述文件缓存时间
DESC_JS_CACHE_SECONDS = 1 * 24 * 3600


def newNotAmsActInfo(dtBeginTime: str, dtEndTime: str, sActivityName: str) -> AmsActInfo:
    info = AmsActInfo()
    info.iActivityId = "000000"
    info.sActivityName = sActivityName
    info.dtBeginTime = dtBeginTime
    info.dtEndTime = dtEndTime

    return info


not_know_start_time__ = "2000-01-01 00:00:00"
# 不知道时间的统一把时间设定为后年年初-。-
not_know_end_time____ = format_time(
    get_now().replace(year=get_now().year + 2, month=1, day=1, hour=0, second=0, microsecond=0)
)

_msd, _med = start_and_end_date_of_a_month(get_now())
month_start_day______, month_end_day________ = format_time(_msd), format_time(_med)

not_ams_activities = [
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "道聚城"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "黑钻礼包"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "腾讯游戏信用礼包"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "心悦app"),
    newNotAmsActInfo("2022-01-20 00:00:00", "2022-02-28 23:59:59", "管家蚊子腿"),
    newNotAmsActInfo("2021-10-18 00:00:00", "2021-11-18 23:59:59", "qq视频蚊子腿"),
    newNotAmsActInfo("2023-11-16 00:00:00", "2023-12-19 23:59:59", "qq视频蚊子腿-爱玩"),
    newNotAmsActInfo("2021-07-04 00:00:00", not_know_end_time____, "会员关怀"),
    newNotAmsActInfo("2024-06-13 00:00:00", "2024-07-12 23:59:59", "超级会员"),
    newNotAmsActInfo("2022-11-24 00:00:00", "2022-12-23 23:59:59", "黄钻"),
    newNotAmsActInfo("2024-06-13 00:00:00", "2024-07-12 23:59:59", "集卡"),
    newNotAmsActInfo(month_start_day______, month_end_day________, "DNF助手编年史"),
    newNotAmsActInfo("2024-06-13 00:00:00", "2024-07-31 23:59:59", "colg每日签到"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "小酱油周礼包和生日礼包"),
    newNotAmsActInfo("2021-09-19 00:00:00", "2021-10-05 23:59:59", "qq会员杯"),
    newNotAmsActInfo("2021-09-11 00:00:00", "2021-10-13 23:59:59", "虎牙"),
    newNotAmsActInfo("2021-12-13 00:00:00", "2021-12-31 23:59:59", "WeGame活动_新版"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "幸运勇士"),
    newNotAmsActInfo("2022-09-22 00:00:00", "2022-10-21 23:59:59", "我的小屋"),
    newNotAmsActInfo("2023-12-21 00:00:00", "2024-01-24 23:59:59", "DNF马杰洛的规划"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "dnf论坛签到"),
    newNotAmsActInfo("2022-09-22 00:00:00", "2022-10-21 23:59:59", "DNF集合站_ide"),
    newNotAmsActInfo("2022-09-22 00:00:00", "2022-10-19 23:59:59", "超享玩"),
    newNotAmsActInfo("2024-01-11 10:00:00", "2024-02-20 23:59:59", "DNF心悦wpe"),
    newNotAmsActInfo("2023-01-05 00:00:00", "2023-02-22 23:59:59", "巴卡尔对战地图"),
    newNotAmsActInfo("2023-01-12 00:00:00", "2023-02-10 23:59:59", "魔界人探险记"),
    newNotAmsActInfo("2023-12-05 00:00:00", "2024-02-24 23:59:59", "colg其他活动"),
    newNotAmsActInfo("2024-06-13 00:00:00", "2024-07-04 23:59:59", "DNF周年庆登录活动"),
    newNotAmsActInfo("2024-06-13 00:00:00", "2024-07-25 23:59:59", "勇士的冒险补给"),
    newNotAmsActInfo("2023-12-21 00:00:00", "2024-02-11 23:59:59", "dnf助手活动wpe"),
    newNotAmsActInfo("2023-11-16 00:00:00", "2023-11-30 23:59:59", "DNF娱乐赛"),
    newNotAmsActInfo("2024-06-13 09:55:00", "2024-07-12 23:59:59", "DNF落地页活动_ide"),
    newNotAmsActInfo("2023-12-21 00:00:00", not_know_end_time____, "DNF漫画预约活动"),
    newNotAmsActInfo("2023-12-21 00:00:00", "2024-01-25 23:59:59", "拯救赛利亚"),
    newNotAmsActInfo("2023-12-21 00:00:00", not_know_end_time____, "DNF地下城与勇士心悦特权专区"),
    newNotAmsActInfo("2024-02-01 12:00:00", "2024-02-29 23:59:59", "DNF年货铺"),
    newNotAmsActInfo("2024-02-01 12:00:00", "2024-06-30 23:59:59", "DNF神界成长之路"),
    newNotAmsActInfo("2024-04-18 00:00:00", "2024-07-31 23:59:59", "DNF神界成长之路二期"),
    newNotAmsActInfo("2024-02-05 12:00:00", "2024-03-31 23:59:59", "超核勇士wpe"),
    newNotAmsActInfo("2024-04-18 00:00:00", "2024-05-17 23:59:59", "DNFxSNK"),
    newNotAmsActInfo("2024-06-13 00:00:00", "2024-07-10 23:59:59", "DNF卡妮娜的心愿摇奖机"),
]

act_name_to_url = {
    # 长期免费活动
    "道聚城": "https://daoju.qq.com/mall/",
    "DNF地下城与勇士心悦特权专区": "https://act.xinyue.qq.com/act/a20231103dnf/index.html",
    "心悦app": "https://xinyue.qq.com/beta/#/download",
    "dnf论坛签到": "https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign",
    "小酱油周礼包和生日礼包": "游戏内右下角点击 小酱油 图标",
    "DNF福利中心兑换": "https://dnf.qq.com/cp/a20190312welfare/index.htm",
    #
    # 短期付费活动
    #
    "DNF助手编年史": "dnf助手左侧栏",
    "绑定手机活动": "https://dnf.qq.com/cp/a20230817info/",
    "DNF漫画预约活动": "https://dnf.qq.com/cp/a20231211comic/index.html",
    "DNF神界成长之路": "https://dnf.qq.com/cp/a2024user/page1.html",
    "DNF神界成长之路二期": "https://dnf.qq.com/cp/a2024user/index.html",
    "DNF落地页活动_ide": "https://dnf.qq.com/act/a20240613index/index.html",
    "DNF周年庆登录活动": "https://dnf.qq.com/cp/a20240613celebration/",
    "超级会员": "https://act.qzone.qq.com/v2/vip/tx/p/50148_928bd0e0",
    "集卡": "https://act.qzone.qq.com/v2/vip/tx/p/50140_591877ab",
    "DNF卡妮娜的心愿摇奖机": "https://dnf.qq.com/cp/a20240613wish/indexm.html",
    "colg每日签到": "https://bbs.colg.cn/forum-171-1.html",
    "勇士的冒险补给": "https://act.xinyue.qq.com/bb/act/a4a4b8cefdc8645299a546567fc1c68ad/index.html",
    #
    # 已过期活动
    #
    "DNF落地页活动_ide_dup": "https://dnf.qq.com/act/a20240418index/index.html",
    "DNFxSNK": "https://dnf.qq.com/cp/a20240418snklink/indexm.html",
    "9163补偿": "https://dnf.qq.com/cp/a20240330apologize/index.html",
    "超核勇士wpe": "https://act.supercore.qq.com/supercore/act/a9eba0142961a4a64a52e369e002a66e8/index.html",
    "DNF年货铺": "https://dnf.qq.com/cp/a20240201newyear/",
    "DNF心悦wpe": "https://act.xinyue.qq.com/act/a20240105dnf/index.html",
    "dnf助手活动wpe": "https://mwegame.qq.com/act/dnf/a20231213zhaohui/index.html",
    "colg其他活动": "https://bbs.colg.cn/colg_activity_new-aggregation_activity.html?aid=16",
    "拯救赛利亚": "https://dnf.qq.com/cp/a20231221save/indexm.html",
    "WeGame活动": "https://dnf.qq.com/cp/SJ20231221wg/index_other.html",
    "DNF马杰洛的规划": "https://dnf.qq.com/cp/a20231221card/index.html",
    "神界预热": "https://dnf.qq.com/cp/a20231207gift/index.html",
    "qq视频蚊子腿-爱玩": "https://ovact.iwan.qq.com/magic-act/WHJL0iOwifXqDKtGNrOsd3jTDJ/index_page1.html",
    "DNF落地页活动": "https://dnf.qq.com/cp/a20231116index/index.html",
    "DNF预约": "https://dnf.qq.com/cp/a20231110invite/indexm2.html?pt=1",
    "DNF娱乐赛": "https://dnf.qq.com/act/a20231106match/index.html",
    "dnf助手活动": "https://mwegame.qq.com/helper/dnf/laoban/index.html",
    "腾讯游戏信用礼包": "https://gamecredit.qq.com/static/web/index.html#/gift-pack",
    "黑钻礼包": "https://dnf.qq.com/act/blackDiamond/gift.shtml",
    "DNF心悦": "https://act.xinyue.qq.com/act/a20230718combat/index.html",
    "DNF心悦Dup": "https://xinyue.qq.com/act/a20230606dnf/index.html",
    "dnf周年拉好友": "https://dnf.qq.com/cp/a20230615emotion/indexm.html",
    "心悦app理财礼卡": "https://xinyue.qq.com/act/app/xyjf/a20171031lclk/index1.shtml",
    "冒险的起点": "https://dnf.qq.com/lbact/a20221228lb00nmo/indexm.html",
    "DNF巴卡尔竞速": "https://xinyue.qq.com/act/a20230220dnf/index.html",
    "和谐补偿活动": "https://dnf.qq.com/cp/a20230223being/",
    "巴卡尔对战地图": "https://dnf.qq.com/cp/a20230105bakal/page1.html",
    "巴卡尔大作战": "https://dnf.qq.com/cp/a20230112herd/index.html?pt=1",
    "魔界人探险记": "https://dnf.qq.com/cp/a20230112sjpk/index.html",
    "DNF集合站": "https://dnf.qq.com/cp/xc20230112jhy/index.html",
    "dnf助手活动Dup": "https://mwegame.qq.com/act/dnf/a20221220summary/index.html",
    "心悦app周礼包": "https://xinyue.qq.com/act/a20180906gifts/index.html",
    "DNF闪光杯": "https://xinyue.qq.com/act/a20221114xyFlashAct/index.html",
    "DNF冒险家之路": "https://dnf.qq.com/cp/a20220921luck/index.html?sChannel=wegame&wg_ad_from=communitycoverNew",
    "超享玩": "https://act.supercore.qq.com/supercore/act/ac2cb66d798da4d71bd33c7a2ec1a7efb/index.html",
    "我的小屋": "https://dnf.qq.com/act/a20220910farm/index.html?pt=1",
    "DNF集合站_ide": "https://dnf.qq.com/cp/jinqiu0922jiheye/index.html",
    "幸运勇士": "https://dnf.qq.com/cp/a20191114wastage/index.html",
    "会员关怀": "https://act.qzone.qq.com/v2/vip/tx/p/42034_cffe8db4",
    "KOL": "https://dnf.qq.com/cp/a20220526kol/index.html",
    "黄钻": "https://act.qzone.qq.com/v2/vip/tx/p/41784_f68ffe5f",
    "心悦猫咪": "https://xinyue.qq.com/act/a20180912tgclubcat/index.html",  # userAgent: tgclub/5.7.11.85(Xiaomi MIX 2;android 9;Scale/440;android;865737030437124)
    "DNF互动站": "https://dnf.qq.com/cp/a20220609fete/index.html",
    "DNF格斗大赛": "https://dnf.qq.com/cp/a20220402pk/index.htm",
    "DNF共创投票": "https://dnf.qq.com/cp/a20210914design/list-end.html",
    "翻牌活动": "https://dnf.qq.com/cp/a20220420cardflip/index.html",
    "hello语音（皮皮蟹）网页礼包兑换": "https://dnf.qq.com/cp/a20210806dnf/",
    "管家蚊子腿": "https://sdi.3g.qq.com/v/2022011118372511947",
    "组队拜年": "https://dnf.qq.com/cp/a20211221BN/index.html",
    "新职业预约活动": "https://dnf.qq.com/cp/a20211130reserve/index.html",
    "WeGame活动_新版": "https://act.wegame.com.cn/wand/danji/a20211201DNFCarnival/",
    "DNF公会活动": "https://dnf.qq.com/cp/a20211028GH/index.html",
    "关怀活动": "https://dnf.qq.com/lbact/a20211118care/index.html",
    "DNF记忆": "https://dnf.qq.com/cp/a20211203dnfmem/index.html",
    "DNF名人堂": "https://dnf.qq.com/cp/hof20211123/index.html",
    "qq视频蚊子腿": "https://m.film.qq.com/magic-act/yauhs87ql00t63xttwkas8papl/index_index.html",
    "WeGameDup": "https://dnf.qq.com/lbact/a20211014wg/index.html",
    "轻松之路": "https://dnf.qq.com/cp/a20210914qszlm/index.html",
    "命运的抉择挑战赛": "https://dnf.qq.com/cp/a20210826fate/index.html",
    "虎牙": "https://www.huya.com/367967",
    "wegame国庆活动【秋风送爽关怀常伴】": "https://dnf.qq.com/lbact/a20200922wegame/index.html",
    "微信签到": "微信DNF公众号",
    "10月女法师三觉": "https://mwegame.qq.com/act/dnf/Mageawaken/index?subGameId=10014&gameId=10014&gameId=1006",
    "dnf助手排行榜": "https://mwegame.qq.com/dnf/rankv2/index.html",
    "2020DNF嘉年华页面主页面签到": "https://dnf.qq.com/cp/a20201203carnival/index.html",
    "DNF进击吧赛利亚": "https://xinyue.qq.com/act/a20201023sailiya/index.html",
    "阿拉德勇士征集令": "https://act.qzone.qq.com/vip/2020/dnf1126",
    "dnf漂流瓶": "https://dnf.qq.com/cp/a20201211driftm/index.html",
    "暖冬好礼活动": "https://dnf.qq.com/lbact/a20200911lbz3dns/index.html",
    "史诗之路来袭活动合集": "https://dnf.qq.com/lbact/a20201224aggregate/index.html",
    "新春福袋大作战": "https://dnf.qq.com/cp/a20210108luckym/index.html",
    "燃放爆竹活动": "https://dnf.qq.com/cp/a20210118rfbz/index.html",
    "DNF福签大作战": "https://dnf.qq.com/cp/a20210325sjlbv3pc/index.html",
    "DNF强者之路": "https://dnf.qq.com/cp/a20210312Strong/index.html",
    "管家蚊子腿-旧版": "https://guanjia.qq.com/act/cop/20210425dnf/pc/",
    "DNF十三周年庆活动": "https://dnf.qq.com/cp/a20210524fete/index.html",
    "qq视频-AME活动": "https://dnf.qq.com/cp/a20210816video/",
    "qq会员杯": "https://club.vip.qq.com/qqvip/acts2021/dnf",
}


def get_act_url(act_name: str) -> str:
    return act_name_to_url.get(act_name, "未找到活动链接，请自行百度")


class Urls:
    def __init__(self):
        # 余额
        self.balance = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.bean.balance&appVersion={appVersion}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&iAppId=1001&_app_id=1001&method=balance&page=0&w_ver=23&w_id=45&djcRequestId={djcRequestId}&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"
        self.money_flow = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.bean.water&appVersion={appVersion}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&page=1&starttime={starttime}&endtime={endtime}&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"

        # 每日登录事件：app登录
        self.user_login_event = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.login.user.first&appVersion={appVersion}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"

        # 每日签到的奖励规则
        self.sign_reward_rule = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.reward.sign.rule&appVersion={appVersion}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&output_format=json&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"

        # 签到相关接口的入口
        self.sign = "https://comm.ams.game.qq.com/ams/ame/amesvr?ameVersion=0.3&appVersion={appVersion}&&sDeviceID={sDeviceID}&sServiceType=dj&iActivityId=11117&sServiceDepartment=djc&set_info=newterminals&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&&appSource=android&ch=10000&osVersion=Android-28&sVersionName={sVersionName}"
        # post数据，需要手动额外传入参数：iFlowId
        self.sign_raw_data = "appVersion={appVersion}&g_tk={g_tk}&iFlowId={iFlowId}&month={month}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&sign_version=1.0&ch=10000&iActivityId=11117&osVersion=Android-28&sVersionName={sVersionName}&sServiceDepartment=djc&sServiceType=dj&appSource=android"

        # 任务列表
        self.usertask = "https://djcapp.game.qq.com/daoju/v3/api/we/usertaskv2/Usertask.php?iAppId=1001&appVersion={appVersion}&&sDeviceID={sDeviceID}&_app_id=1001&output_format=json&_output_fmt=json&appid=1001&optype=get_usertask_list&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"
        # 领取任务奖励，需要手动额外传入参数：iruleId
        self.take_task_reward = "https://djcapp.game.qq.com/daoju/v3/api/we/usertaskv2/Usertask.php?iAppId=1001&appVersion={appVersion}&iruleId={iruleId}&&sDeviceID={sDeviceID}&_app_id=1001&output_format=json&_output_fmt=json&appid=1001&optype=receive_usertask&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"
        # 上报任务完成，需要手动额外传入参数：task_type
        self.task_report = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.task.report&appVersion={appVersion}&task_type={task_type}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"

        # 许愿道具列表，额外参数：plat, biz
        self.query_wish_goods_list = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.goods.list&appVersion={appVersion}&&plat={plat}&biz={biz}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&output_format=json&&weexVersion=0.9.4&deviceModel=MIX%202&&wishing=1&view=biz_portal&page=1&ordertype=desc&orderby=dtModifyTime&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"
        # 查询许愿列表，额外参数：appUid
        self.query_wish = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.demand.user.demand&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&_app_id=1001&_biz_code=&pn=1&ps=5&appUid={appUid}&sDeviceID={sDeviceID}&appVersion={appVersion}&&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android&sDjcSign={sDjcSign}"
        # 删除许愿，额外参数：sKeyId
        self.delete_wish = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.demand.delete&output_format=jsonp&iAppId=1001&_app_id=1001&sKeyId={sKeyId}&w_ver=2&w_id=89&sDeviceID={sDeviceID}&djcRequestId={djcRequestId}&appVersion={appVersion}&p_tk={p_tk}&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android&sDjcSign={sDjcSign}"
        # 许愿 ，需要手动额外传入参数：iActionId, iGoodsId, sBizCode, partition, iZoneId, platid, sZoneDesc, sRoleId, sRoleName, sGetterDream
        self.make_wish = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.demand.create&&iActionId={iActionId}&iGoodsId={iGoodsId}&sBizCode={sBizCode}&partition={partition}&iZoneId={iZoneId}&platid={platid}&sZoneDesc={sZoneDesc}&sRoleId={sRoleId}&sRoleName={sRoleName}&sGetterDream={sGetterDream}&sDeviceID={sDeviceID}&appVersion={appVersion}&&sDjcSign={sDjcSign}&iAppId=1001&_app_id=1001&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"

        # 查询道聚城绑定的各游戏角色列表，dnf的角色信息和选定手游的角色信息将从这里获取
        self.query_bind_role_list = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.role.bind_list&appVersion={appVersion}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&type=1&output_format=json&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"

        # 绑定道聚城游戏（仅用作偶尔不能通过app绑定的时候根据这个来绑定）
        self.bind_role = "https://djcapp.game.qq.com/daoju/djcapp/v5/rolebind/BindRole.php?type=2&biz=dnf&output_format=jsonp&_={millseconds}&role_info={role_info}"

        # 查询服务器列表，需要手动额外传入参数：bizcode。具体游戏参数可查阅djc_biz_list.json
        self.query_game_server_list = (
            "https://gameact.qq.com/comm-htdocs/js/game_area/utf8verson/{bizcode}_server_select_utf8.js"
        )
        self.query_game_server_list_for_web = (
            "https://gameact.qq.com/comm-htdocs/js/game_area/{bizcode}_server_select.js"
        )

        # 查询手游礼包礼包，需要手动额外传入参数：bizcode
        self.query_game_gift_bags = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.package.list&bizcode={bizcode}&appVersion={appVersion}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&showType=qq&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"
        # 查询手游角色列表，需要手动额外传入参数：game(game_info.gameCode)、sAMSTargetAppId(game_info.wxAppid)、area(roleinfo.channelID)、platid(roleinfo.systemID)、partition(areaID)
        self.get_game_role_list = "https://comm.aci.game.qq.com/main?sCloudApiName=ams.gameattr.role&game={game}&sAMSTargetAppId={sAMSTargetAppId}&appVersion={appVersion}&area={area}&platid={platid}&partition={partition}&callback={callback}&&sDeviceID={sDeviceID}&&sAMSAcctype=pt&&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"
        # 一键领取手游礼包，需要手动额外传入参数：bizcode、iruleId、systemID、sPartition(areaID)、channelID、channelKey、roleCode、sRoleName
        self.receive_game_gift = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.package.receive&bizcode={bizcode}&appVersion={appVersion}&iruleId={iruleId}&sPartition={sPartition}&roleCode={roleCode}&sRoleName={sRoleName}&channelID={channelID}&channelKey={channelKey}&systemID={systemID}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&appid=1001&output_format=json&optype=receive_usertask_game&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"

        # 兑换道具，需要手动额外传入参数：iGoodsSeqId、rolename、lRoleId、iZone(roleinfo.serviceID)
        self.exchangeItems = "https://apps.game.qq.com/cgi-bin/daoju/v3/hs/i_buy.cgi?&weexVersion=0.9.4&appVersion={appVersion}&iGoodsSeqId={iGoodsSeqId}&iZone={iZone}&lRoleId={lRoleId}&rolename={rolename}&&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&platform=android&deviceModel=MIX%202&&&_output_fmt=1&_plug_id=9800&_from=app&iActionId=2594&iActionType=26&_biz_code=dnf&biz=dnf&appid=1003&_app_id=1003&_cs=2&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"
        # 新的兑换道具接口，新接入的游戏都用这个（其实dnf也可以用这个，不过得先在app里兑换一次，使绑定角色信息刷新为新的格式），需要手动额外传入参数：iGoodsSeqId、iActionId、iActionType、bizcode、platid、iZone、partition、lRoleId、rolename
        self.new_exchangeItems = (
            "https://djcapp.game.qq.com/daoju/igw/main/?_service=buy.plug.swoole.judou&iAppId=1001&_app_id=1003&_output_fmt=1&_plug_id=9800&_from=app&iGoodsSeqId={iGoodsSeqId}&iActionId={iActionId}&iActionType={iActionType}"
            "&_biz_code={bizcode}&biz={bizcode}&platid={platid}&iZone={iZone}&partition={partition}&lRoleId={lRoleId}&rolename={rolename}&p_tk={p_tk}&_cs=2&w_ver=156&w_id=4&sDeviceID={sDeviceID}&djcRequestId={djcRequestId}"
            "&appVersion={appVersion}&p_tk={p_tk}&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android&sDjcSign={sDjcSign}"
        )
        # 获取所有可兑换的道具的列表
        self.show_exchange_item_list = "https://app.daoju.qq.com/jd/js/{bizcode}_index_list_dj_info_json.js?&weexVersion=0.9.4&appVersion={appVersion}&&sDeviceID={sDeviceID}&platform=android&deviceModel=MIX%202&&osVersion=Android-28&ch=10000&sVersionName={sVersionName}&appSource=android"

        # amesvr通用活动
        # 其对应活动描述文件一般可通过下列链接获取，其中{actId}替换为活动ID，{last_three}替换为活动ID最后三位
        # https://dnf.qq.com/comm-htdocs/js/ams/actDesc/{last_three}/{actId}/act.desc.js
        # https://apps.game.qq.com/comm-htdocs/js/ams/v0.2R02/act/{actId}/act.desc.js
        self.iActivityId_djc_operations = "11117"  # 道聚城
        self.iActivityId_xinyue_battle_ground = "366480"  # DNF地下城与勇士心悦特权专区
        self.iActivityId_xinyue_sailiyam = "339263"  # DNF进击吧赛利亚
        self.iActivityId_wegame_guoqing = "331515"  # wegame国庆活动【秋风送爽关怀常伴】
        self.iActivityId_dnf_1224 = "353266"  # DNF-1224渠道活动合集
        self.iActivityId_dnf_shanguang = "494507"  # DNF闪光杯
        self.iActivityId_dnf_female_mage_awaken = "336524"  # 10月女法师三觉活动
        self.iActivityId_dnf_rank = "347456"  # DNF-2020年KOL榜单建设送黑钻
        self.iActivityId_dnf_carnival = "346329"  # DNF嘉年华页面主页面签到-pc
        self.iActivityId_dnf_carnival_live = "346830"  # DNF嘉年华直播页面-PC
        self.iActivityId_dnf_dianzan = "472877"  # DNF2020共创投票领礼包需求
        self.iActivityId_dnf_welfare = "215651"  # DNF福利中心兑换
        self.iActivityId_dnf_welfare_login_gifts = "441426"  # DNF福利中心-登陆游戏领福利
        self.iActivityId_xinyue_financing = "126962"  # 心悦app理财礼卡
        self.iActivityId_xinyue_cat = "141920"  # 心悦猫咪
        self.iActivityId_xinyue_weekly_gift = "155525"  # 心悦app周礼包
        self.iActivityId_dnf_drift = "348890"  # dnf漂流瓶
        self.iActivityId_dnf_helper = "581863"  # DNF助手活动
        self.iActivityId_dnf_helper_dup = "526183"  # dnf助手活动Dup
        self.iActivityId_warm_winter = "347445"  # 暖冬有礼
        self.iActivityId_qq_video_amesvr = "398546"  # qq视频-AME活动
        self.iActivityId_dnf_bbs_v1 = "431448"  # DNF论坛积分兑换活动
        self.iActivityId_dnf_bbs_v2 = "397645"  # DNF论坛积分兑换活动
        self.iActivityId_dnf_luodiye = "593802"  # DNF落地页活动需求
        self.iActivityId_dnf_wegame = "603490"  # WeGame活动
        self.iActivityId_dnf_wegame_dup = "415808"  # WeGame活动
        self.iActivityId_spring_fudai = "354771"  # 新春福袋大作战
        self.iActivityId_dnf_fuqian = "362403"  # DNF福签大作战
        self.iActivityId_dnf_collection = "522722"  # DNF集合站
        self.iActivityId_dnf_collection_dup = "423011"  # DNF集合站
        self.iActivityId_firecrackers = "355187"  # 燃放爆竹活动
        self.iActivityId_dnf_bakaer = "535429"  # DNF巴卡尔竞速
        self.iActivityId_hello_voice = "438826"  # hello语音（皮皮蟹）奖励兑换
        self.iActivityId_dnf_pk = "463319"  # DNF格斗大赛
        self.iActivityId_dnf_xinyue = "569923"  # DNF心悦
        self.iActivityId_dnf_xinyue_dup = "560401"  # DNF心悦Dup
        self.iActivityId_dnf_strong = "366330"  # DNF强者之路
        self.iActivityId_dnf_comic = "386057"  # DNF&腾讯动漫周年庆合作活动
        self.iActivityId_dnf_13 = "381033"  # DNF十三周年庆双端站点
        self.iActivityId_dnf_anniversary_friend = "558623"  # dnf周年拉好友
        self.iActivityId_dnf_reserve = "430779"  # 新职业预约活动
        self.iActivityId_dnf_anniversary = "474801"  # DNF周年庆登录活动
        self.iActivityId_dnf_kol = "472448"  # DNF KOL
        self.iActivityId_maoxian_start = "525776"  # 冒险的起点
        self.iActivityId_maoxian = "548876"  # 勇士的冒险补给
        self.iActivityId_dnf_gonghui = "421277"  # DNF公会活动
        self.iActivityId_dnf_mingyun_jueze = "405654"  # 命运的抉择挑战赛
        self.iActivityId_dnf_guanhuai = "421327"  # 关怀活动
        self.iActivityId_dnf_relax_road = "407354"  # 轻松之路
        self.iActivityId_dnf_vote = "428587"  # DNF名人堂
        self.iActivityId_dnf_reservation = "590510"  # DNF预约
        self.iActivityId_dnf_memory = "431712"  # DNF记忆
        self.iActivityId_dnf_game = "514615"  # DNF娱乐赛
        self.iActivityId_team_happy_new_year = "438251"  # 组队拜年
        self.iActivityId_dnf_card_flip = "458381"  # 翻牌活动
        self.iActivityId_dnf_interactive = "469840"  # DNF互动站
        self.iActivityId_dnf_maoxian_road = "500495"  # DNF冒险家之路
        self.iActivityId_dnf_bakaer_fight = "523361"  # 巴卡尔大作战
        self.iActivityId_dnf_compensate = "535922"  # DNF游戏调整补偿
        self.iActivityId_dnf_bind_phone = "420695"  # 绑定手机活动
        self.iActivityId_dnf_shenjie_yure = "602887"  # 神界预热
        self.iActivityId_dnf_9163_apologize = "619079"  # 9163补偿

        # amesvr通用活动系统配置
        # 需要手动额外传入参数：sMiloTag, sServiceDepartment, sServiceType
        self.amesvr = "https://{amesvr_host}/ams/ame/amesvr?ameVersion=0.3&sSDID={sSDID}&sMiloTag={sMiloTag}&sServiceType={sServiceType}&iActivityId={iActivityId}&sServiceDepartment={sServiceDepartment}&isXhrPost=true"
        # &sArea={sArea}&sRoleId={sRoleId}&uin={uin}&userId={userId}&token={token}&sRoleName={sRoleName}&serverId={serverId}&skey={skey}&nickName={nickName}
        # 需要手动额外传入参数：iFlowId/package_id/lqlevel/teamid, sServiceDepartment/sServiceType, sArea/serverId/nickName/sRoleId/sRoleName/uin/skey/userId/token, date
        self.amesvr_raw_data = (
            "iActivityId={iActivityId}&g_tk={g_tk}&iFlowId={iFlowId}&package_id={package_id}&xhrPostKey=xhr_{millseconds}&eas_refer=http%3A%2F%2Fnoreferrer%2F%3Freqid%3D{uuid}%26version%3D23&lqlevel={lqlevel}"
            "&teamid={teamid}&weekDay={weekDay}&e_code=0&g_code=0&eas_url={eas_url}&xhr=1&sServiceDepartment={sServiceDepartment}&sServiceType={sServiceType}&sArea={sArea}&sRoleId={sRoleId}&uin={uin}"
            "&userId={userId}&token={token}&sRoleName={sRoleName}&serverId={serverId}&areaId={areaId}&skey={skey}&nickName={nickName}&date={date}&dzid={dzid}&page={page}&iPackageId={iPackageId}&plat={plat}"
            "&extraStr={extraStr}&sContent={sContent}&sPartition={sPartition}&sAreaName={sAreaName}&md5str={md5str}&ams_md5str={ams_md5str}&ams_checkparam={ams_checkparam}&checkparam={checkparam}&type={type}&moduleId={moduleId}"
            "&giftId={giftId}&acceptId={acceptId}&invitee={invitee}&giftNum={giftNum}&sendQQ={sendQQ}&receiver={receiver}&receiverName={receiverName}&inviterName={inviterName}&user_area={user_area}"
            "&user_partition={user_partition}&user_areaName={user_areaName}&user_roleId={user_roleId}&user_roleName={user_roleName}&user_roleLevel={user_roleLevel}&user_checkparam={user_checkparam}"
            "&user_md5str={user_md5str}&user_sex={user_sex}&user_platId={user_platId}&cz={cz}&dj={dj}&siActivityId={siActivityId}&needADD={needADD}&dateInfo={dateInfo}&sId={sId}&userNum={userNum}"
            "&cardType={cardType}&inviteId={inviteId}&sendName={sendName}&receiveUin={receiveUin}&receiverUrl={receiverUrl}&index={index}&pageNow={pageNow}&pageSize={pageSize}&clickTime={clickTime}"
            "&username={username}&petId={petId}&skin_id={skin_id}&decoration_id={decoration_id}&fuin={fuin}&sCode={sCode}&sNickName={sNickName}&iId={iId}&sendPage={sendPage}&hello_id={hello_id}"
            "&prize={prize}&qd={qd}&iReceiveUin={iReceiveUin}&map1={map1}&map2={map2}&len={len}&itemIndex={itemIndex}&sRole={sRole}&loginNum={loginNum}&level={level}&inviteUin={inviteUin}"
            "&iGuestUin={iGuestUin}&ukey={ukey}&iGiftID={iGiftID}&iInviter={iInviter}&iPageNow={iPageNow}&iPageSize={iPageSize}&iType={iType}&iWork={iWork}&iPage={iPage}&sNick={sNick}"
            "&iMatchId={iMatchId}&iGameId={iGameId}&iIPId={iIPId}&iVoteId={iVoteId}&iResult={iResult}&personAct={personAct}&teamAct={teamAct}&param={param}&dhnums={dhnums}&sUin={sUin}&pointID={pointID}"
            "&workId={workId}&isSort={isSort}&jobName={jobName}&title={title}&actSign={actSign}&iNum={iNum}&prefer={prefer}&card={card}&answer1={answer1}&answer2={answer2}&answer3={answer3}"
            "&countsInfo={countsInfo}&power={power}&crossTime={crossTime}&getLv105={getLv105}&use_fatigue={use_fatigue}&exchangeId={exchangeId}&sChannel={sChannel}&pass={pass}&pass_date={pass_date}"
            "&bossId={bossId}&today={today}&anchor={anchor}&sNum={sNum}&week={week}&position={position}&packages={packages}&selectNo={selectNo}&targetQQ={targetQQ}&u_confirm={u_confirm}"
        )

        # ide通用活动
        # 其对应活动描述文件一般可通过下列链接获取，其中{actId}替换为活动ID
        #   https://comm.ams.game.qq.com/ide/page/{actId}
        #
        # note: 在活动页面 网络请求 过滤 ide/page/ 即可定位到活动id
        self.ide_iActivityId_dnf_social_relation_permission = "14_uK7KKe"  # DNF关系链接-用户授权接口
        self.ide_iActivityId_dnf_my_home = "83_WFf5TE"  # 我的小屋
        self.ide_iActivityId_collection = "57_vA2NDv"  # 集合站
        self.ide_iActivityId_dnf_bakaer_map = "38_hhO2FX"  # 巴卡尔对战地图
        self.ide_iActivityId_dnf_anniversary = "15_s0hJrQ"  # DNF周年庆登录活动
        self.ide_iActivityId_dnf_game = "64_Yetu1m"  # dnf娱乐赛
        self.ide_iActivityId_dnf_luodiye = "61_TpRquT"  # DNF落地页
        self.ide_iActivityId_dnf_luodiye_dup = "16_FDvprx"  # DNF落地页dup
        self.ide_iActivityId_dnf_comic = "64_p5cLkZ"  # DNF漫画预约活动
        self.ide_iActivityId_dnf_save_sailiyam = "35_w7UB7L"  # 拯救赛利亚
        self.ide_iActivityId_dnf_nianhuopu = "47_aiKrck"  # DNF年货铺
        self.ide_iActivityId_dnf_shenjie_grow_up = "34_DA6bLu"  # DNF神界成长之路
        self.ide_iActivityId_dnf_shenjie_grow_up_v2 = "22_ylD5VE"  # DNF神界成长之路二期
        self.ide_iActivityId_dnf_snk = "43_L5dwVl"  # DNFxSNK
        self.ide_iActivityId_dnf_kanina = "0_zsJIaU"  # DNF卡妮娜的心愿摇奖机

        # re: 部分情况下，可能会同时关联ame和ide活动，这里放到一起管理
        self.iActivityId_majieluo = "603648"  # DNF马杰洛的规划
        self.ide_iActivityId_majieluo = "16_S86Tjb"  # DNF马杰洛的规划

        self.iActivityId_mojieren = "523217"  # 魔界人探险记
        self.ide_iActivityId_mojieren = "69_vGQxc7"  # 魔界人探险记

        self.ide = "https://{ide_host}/ide/"
        self.ide_raw_data = (
            "iChartId={iChartId}&iSubChartId={iSubChartId}&sIdeToken={sIdeToken}"
            "&sRoleId={sRoleId}&sRoleName={sRoleName}&sArea={sArea}&sMd5str={sMd5str}&sCheckparam={sCheckparam}&roleJob={roleJob}&sAreaName={sAreaName}"
            "&sAuthInfo={sAuthInfo}&sActivityInfo={sActivityInfo}&openid={openid}&sCode={sCode}&startPos={startPos}"
            "&e_code=0&g_code=0&eas_url={eas_url}&eas_refer={eas_refer}&iType={iType}&iPage={iPage}&type={type}&sUin={sUin}&dayNum={dayNum}"
            "&iFarmland={iFarmland}&fieldId={fieldId}&sRice={sRice}&packageId={packageId}&targetId={targetId}&myId={myId}&id={id}"
            "&iCardId={iCardId}&iAreaId={iAreaId}&sRole={sRole}&drinksId={drinksId}&gameId={gameId}&score={score}&loginDays={loginDays}"
            "&iSuccess={iSuccess}&iGameId={iGameId}&sAnswer={sAnswer}&index={index}&u_stage={u_stage}&u_task_index={u_task_index}&u_stage_index={u_stage_index}&num={num}"
            "&sPartition={sPartition}&sPlatId={sPlatId}&source={source}"
        )

        # DNF共创投票
        # 查询作品列表，额外参数：iCategory1、iCategory2、page、pagesize
        self.query_dianzan_contents = "https://apps.game.qq.com/cms/index.php?r={rand}&callback=jQuery191015906433451135138_{millseconds}&serviceType=dnf&sAction=showList&sModel=Ugc&actId=2&iCategory1={iCategory1}&iCategory2={iCategory2}&order=0&page={page}&pagesize={pagesize}&_=1608559950347"
        # 点赞，额外参数：iContentId
        self.dianzan = "https://apps.game.qq.com/cms/index.php?r={rand}&callback=jQuery19105114998760002998_{millseconds}&serviceType=dnf&actId=2&sModel=Zan&sAction=zanContent&iContentId={iContentId}&_={millseconds}"

        # 每月黑钻等级礼包
        self.heizuan_gift = (
            "https://dnf.game.qq.com/mtask/lottery/?r={rand}&serviceType=dnf&channelId=1&actIdList=44c24e"
        )

        # 信用星级礼包
        self.credit_gift = (
            "https://dnf.game.qq.com/mtask/lottery/?r={rand}&serviceType=dnf&channelId=1&actIdList=13c48b"
        )

        # 腾讯游戏信用，需要手动额外传入参数：gift_group
        self.credit_xinyue_gift = "https://gamecredit.qq.com/api/qq/proxy/credit_xinyue_gift?gift_group={gift_group}"

        # --QQ空间相关活动--
        self.qzone_activity = "https://activity.qzone.qq.com/fcg-bin/{api}?g_tk={g_tk}&r={rand}"
        self.qzone_activity_raw_data = "gameid={gameid}&actid={actid}&ruleid={ruleid}&area={area}&partition={partition}&roleid={roleid}&platform=pc&query={query}&act_name={act_name}&format=json&uin={uin}&countid={countid}"

        # 新的qq空间接口
        self.qzone_activity_new = "https://act.qzone.qq.com/v2/vip/tx/trpc/subact/ExecAct?g_tk={g_tk}"
        self.qzone_activity_new_query = (
            "https://act.qzone.qq.com/v2/vip/tx/proxy/domain/trpc.qzone.qq.com/trpc/subact/QueryAct?g_tk={g_tk}"
        )
        self.qzone_activity_new_send_card = "https://act.qzone.qq.com/v2/vip/tx/trpc/xcard/GiftItems?g_tk={g_tk}"
        self.qzone_activity_new_query_card = (
            "https://act.qzone.qq.com/v2/vip/tx/trpc/xcard/QueryItems?g_tk={g_tk}&packetID={packetID}"
        )
        self.qzone_activity_new_request_card = "https://act.qzone.qq.com/v2/vip/tx/trpc/xcard/RequestItems?g_tk={g_tk}"
        self.qzone_activity_new_agree_request_card = (
            "https://club.vip.qq.com/qqvip/api/trpc/xcard/RequestItems?token={token}&t={rand}&g_tk={g_tk}"
        )
        # 本地假设的集卡活动id，每次新版的集卡更新时，就增加一下这个（如果继续出旧版的那种集卡活动，则不需要修改这个）
        self.pesudo_ark_lottery_act_id = 10015

        self.qzone_activity_club_vip = (
            "https://club.vip.qq.com/qqvip/api/tianxuan/access/execAct?g_tk={g_tk}&isomorphism-args={isomorphism_args}"
        )

        # 抽卡相关
        self.ark_lottery_page = get_act_url("集卡")
        # 查询次数信息：参数：to_qq, actName
        self.ark_lottery_query_left_times = 'https://proxy.vac.qq.com/cgi-bin/srfentry.fcgi?data={{"13320":{{"uin":{to_qq},"actName":"{actName}"}}}}&t={rand}&g_tk={g_tk}'
        # 赠送卡片：参数：cardId，from_qq，to_qq, actName
        self.ark_lottery_send_card = 'https://proxy.vac.qq.com/cgi-bin/srfentry.fcgi?data={{"13333":{{"cardId":{cardId},"fromUin":{from_qq},"toUin":{to_qq},"actName":"{actName}"}}}}&t={rand}&g_tk={g_tk}'

        # 阿拉德勇士征集令
        self.dnf_warriors_call_page = "https://act.qzone.qq.com/vip/2020/dnf1126"

        # qq视频活动
        self.qq_video = "https://activity.video.qq.com/fcgi-bin/asyn_activity?act_id={act_id}&module_id={module_id}&type={type}&option={option}&ptag=dnf&otype=xjson&_ts={millseconds}&task={task}&is_prepublish={is_prepublish}"

        # qq视频 - 爱玩
        self.qq_video_iwan = "https://act.iwan.qq.com/trpc.iwan.mission_system_server.MissionSystemSvr/dealSimpleMission?platformId=10&platformid=10&guid=&device=&acctype=qq&missionId={missionId}&gameId=48&sPlat=&sArea=&serverId={serverId}&sRoleId={sRoleId}"

        # 电脑管家，额外参数：api/giftId/area_id/charac_no/charac_name
        self.guanjia = "https://act.guanjia.qq.com/bin/act/{api}.php?giftId={giftId}&area_id={area_id}&charac_no={charac_no}&charac_name={charac_name}&callback=jQueryCallback&isopenid=1&_={millseconds}"
        self.guanjia_new = "https://{domain_name}/{api}"

        # 助手排行榜活动
        # 查询，额外参数：uin(qq)、userId/token
        self.rank_user_info = "https://mwegame.qq.com/dnf/kolTopV2/ajax/getUserInfo?uin={uin}&userId={userId}&token={token}&serverId=0&gameId=10014"
        # 打榜，额外参数：uin(qq)、userId/token、id/score
        self.rank_send_score = "https://mwegame.qq.com/dnf/kolTopV2/ajax/sendScore?uin={uin}&userId={userId}&token={token}&serverId=0&gameId=10014&id={id}&type=single1&score={score}"
        # 领取黑钻，额外参数：uin(qq)、userId/token，gift_id[7020, 7021, 7022]
        self.rank_receive_diamond = "https://mwegame.qq.com/ams/send/handle?uin={uin}&userId={userId}&token={token}&serverId=0&gameId=10014&gift_id={gift_id}"

        # dnf助手编年史活动
        # mwegame peak 相关接口，额外参数：api: 具体api名称，userId（助手userId），sPartition/sRoleId, isLock->isLock, amsid->sLbCode, iLbSel1->iLbSel1, 区分自己还是队友的基础奖励, num: 1, mold: 1-自己，2-队友,  exNum->1, iCard->iCard, iNum->iNum
        self.dnf_helper_chronicle_wang_xinyue = (
            "https://mwegame.qq.com/peak/{api}?userId={userId}&gameId=1006&sPartition={sPartition}&sRoleId={sRoleId}&game_code=dnf&token={token}&uin={uin}&toUin={toUin}&uniqueRoleId={uniqueRoleId}&openid="
            "&isLock={isLock}&amsid={amsid}&iLbSel1={iLbSel1}&num={num}&mold={mold}&exNum={exNum}&iCard={iCard}&iNum={iNum}&appidTask=1000042&&date={date_chronicle_sign_in}&accessToken={accessToken}&appOpenid={appOpenid}&appid={appid}"
            "&cRand={cRand}&tghappid={tghappid}&sig={sig}"
        )
        # mwegame ajax 相关接口，额外参数：api: 具体api名称，userId（助手userId），sPartition/sRoleId, actionId: 自己的任务为任务信息中的各个任务的mActionId，队友的任务对应的是各个任务的pActionId
        self.dnf_helper_chronicle_mwegame = (
            "https://mwegame.qq.com/act/GradeExp/ajax/{api}?userId={userId}&gameId=1006&sPartition={sPartition}&sRoleId={sRoleId}&game_code=dnf&actionId={actionId}&pUserId={pUserId}&isBind={isBind}"
            "&cRand={cRand}&tghappid={tghappid}&sig={sig}"
        )

        # 编年史新版接口
        self.dnf_helper_chronicle_yoyo = "https://mwegame.qq.com/yoyo/dnf/{api}"

        # 助手活动相关接口
        self.dnf_helper = "https://mwegame.qq.com/act/dnf/destiny/{api}?gameId=10014&roleSwitch=1&toOpenid=&roleId={roleId}&uniqueRoleId={uniqueRoleId}&openid=&serverName={serverName}&toUin={toUin}&cGameId=1006&userId={userId}&serverId={serverId}&token={token}&isMainRole=0&subGameId=10014&areaId={areaId}&gameName=DNF&areaName={areaName}&roleJob={roleJob}&nickname={nickname}&roleName={roleName}&uin={uin}&roleLevel={roleLevel}&"

        # hello语音（皮皮蟹），额外参数：api，hello_id，type，packid
        self.hello_voice = "https://ulink.game.qq.com/app/1164/c7028bb806cd2d6c/index.php?route=Raward/{api}&iActId=1192&ulenv=&game=dnf&hello_id={hello_id}&type={type}&packid={packid}"

        # dnf论坛签到，额外参数：formhash: 论坛formhash
        self.dnf_bbs_signin = (
            "https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign&operation=qiandao&formhash={formhash}&format=empty"
        )
        self.dnf_bbs_home = "https://dnf.gamebbs.qq.com/home.php?mod=spacecp&ac=credit"

        # 心悦app
        # 心悦猫咪api
        self.xinyue_cat_api = "https://apps.xinyue.qq.com/maomi/pet_api_info/{api}?skin_id={skin_id}&decoration_id={decoration_id}&uin={uin}&adLevel={adLevel}&adPower={adPower}"

        # colg-战令
        self.colg_url = "https://bbs.colg.cn/forum-171-1.html"
        self.colg_task_info_url = "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=getTask&fid=171"
        self.colg_sign_in_url = "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=passUserSign"
        self.colg_take_sign_in_credits = (
            "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=getUserCredit&aid={aid}&task_id={task_id}"
        )
        # ------- colg其他活动 --------
        self.colg_other_act_id = 16
        # 活动页面
        self.colg_other_act_url = (
            f"https://bbs.colg.cn/colg_activity_new-aggregation_activity.html?aid={self.colg_other_act_id}"
        )
        # 累计登录领奖
        self.colg_other_act_get_reward = "https://bbs.colg.cn/colg_activity_new-colg_activity_new.html/getReward"
        # 每日抽奖
        self.colg_other_act_lottery = "https://bbs.colg.cn/colg_activity_new-colg_activity_new.html/lottery"

        # 小酱油
        self.xiaojiangyou_get_role_id = (
            "https://user.game.qq.com/php/helper/xychat/open/redirect/1/2?areaId={areaId}&roleName={roleName}"
        )
        self.xiaojiangyou_query_info = "https://xyapi.game.qq.com/xiaoyue/service/async?_={millseconds}&callback=jQuery171004811813596127945_{millseconds}"
        self.xiaojiangyou_init_page = "https://xyapi.game.qq.com/xiaoyue/service/init?_={millseconds}&callback=jQuery171004811813596127945_{millseconds}&_={millseconds}"
        self.xiaojiangyou_ask_question = "https://xyapi.game.qq.com/xiaoyue/service/ask?_={millseconds}&question={question}&question_id={question_id}&robot_type={robot_type}&option_type=0&filter={question}&rec_more=&certificate={certificate}&callback=jQuery171004811813596127945_{millseconds}&_={millseconds}"
        self.xiaojiangyou_get_packge = "https://xyapi.game.qq.com/xiaoyue/helper/package/get?_={millseconds}&token={token}&ams_id={ams_id}&package_group_id={package_group_id}&tool_id={tool_id}&certificate={certificate}&callback=jQuery171039455388263754454_{millseconds}&_={millseconds}"

        # WeGame新版活动，需要填写 flow_id
        # md5签名内容
        #   /service/flow/v1/parse/Wand-20211206100115-Fde55ab61e52f?u=7636ee76-dc95-42e2-ac8c-af7f07982dfd&a=10004&ts=1639583575&appkey=wegame!#act$2020
        # 计算md5签名之后
        #   /service/flow/v1/parse/Wand-20211206100115-Fde55ab61e52f?u=7636ee76-dc95-42e2-ac8c-af7f07982dfd&a=10004&ts=1639583575&s=7f2eeec828830f249a7694d09833c50d
        self.wegame_new_host = "https://act.wegame.com.cn"
        self.wegame_new_api = "/service/flow/v1/parse/{flow_id}?u={uuid4}&a=10004&ts={seconds}"

        # 幸运勇士
        self.lucky_user = (
            "https://nloss.native.qq.com/{api}?iAreaId={iAreaId}&iRoleId={iRoleId}"
            "&taskId={taskId}&point={point}"
            "&randomSeed={randomSeed}"
        )

        # re: wpe类活动的接入办法为：
        #   1. 随便选一个按钮，右键查看该元素，复制其上层div对应的id的值
        #   2. 在Search标签中搜索该值，会找到一行json定义，复制出来，并格式化
        #   3. 后续在想要查看的按钮右键 Inspect，复制其上层div对应的id的值，然后在json中搜索，上面configurationData的flowID即为我们要找的值
        #
        # note: PS：获得该json后，将最上方的 activity_id 的值替换到对应 op函数 的 act_id中
        #
        # undone: 或者尝试搜索下列关键词也能定位到该json
        #   configurationData
        #   flowID
        #
        #
        # note: 如果手机抓包没法获取到活动链接，但是可以抓包的情况下，可以完成抓包设置后，依次点击对应按钮，然后在抓包结果中搜索 actid ，最下面的请求的参数中的 flowid 就是我们需要的参数

        # 超享玩
        self.super_core_api = "https://agw.xinyue.qq.com/amp2.WPESrv/WPEIndex?flowId={flowId}"

        self.dnf_xinyue_wpe_api = "https://agw.xinyue.qq.com/amp2.WPESrv/WPEIndex"
        self.dnf_xinyue_wpe_get_bind_role_api = "https://agw.xinyue.qq.com/amp2.RoleSrv/GetBindRole"
        self.dnf_xinyue_wpe_bind_role_api = "https://agw.xinyue.qq.com/amp2.RoleSrv/BindRole"

        self.maoxian_wpe_api = "https://agw.xinyue.qq.com/amp2.WPESrv/WPEIndex?flowId={flowId}&actId={actId}"
        self.dnf_helper_wpe_api = "https://agw.xinyue.qq.com/amp2.WPESrv/WPEIndex?flowId={flowId}&actId={actId}"
        self.dnf_chaohe_wpe_api = "https://agw.xinyue.qq.com/amp2.WPESrv/WPEIndex?flowId={flowId}&actId={actId}"

        # 查询心悦用户信息，目前用于获取头像信息
        self.dnf_xinyue_bgw_user_info_api = "https://bgw.xinyue.qq.com/website/website/user/info"
        # 查询心悦战场领奖信息
        self.dnf_xinyue_query_gift_record_api = "https://agw.xinyue.qq.com/amp2.MrmsSrv/GetGiftRecord"

        # 漫画更新数据
        self.dnf_comic_update_api = "https://game.gtimg.cn/images/amside/ide_timer/249678_comicDetail.js"

    def show_current_valid_act_infos(self):
        acts: List[ActCommonInfo] = []

        # others
        for not_ams_act in not_ams_activities:
            if is_act_expired(not_ams_act.dtEndTime):
                continue

            acts.append(not_ams_act.get_common_info())

        # ams
        for attr_name, act_id in self.__dict__.items():
            if not attr_name.startswith("iActivityId_"):
                continue

            # 部分电脑上可能会在这一步卡住，因此加一个标志项，允许不启用活动
            if exists_flag_file("不查询活动.txt"):
                continue

            act = search_act(act_id)
            if act is None:
                continue

            if is_act_expired(act.dtEndTime):
                continue

            acts.append(act.get_common_info())

        # ide
        for attr_name, act_id in self.__dict__.items():
            if not attr_name.startswith("ide_iActivityId_"):
                continue

            # 部分电脑上可能会在这一步卡住，因此加一个标志项，允许不启用活动
            if exists_flag_file("不查询活动.txt"):
                continue

            act = search_ide_act(act_id)
            if act is None:
                continue

            if is_act_expired(act.get_endtime()):
                continue

            acts.append(act.get_common_info(act_id))

        acts.sort(key=lambda act: act.dtEndTime)

        heads = ["序号", "活动名称", "活动ID", "开始时间", "结束时间", "剩余时间"]
        colSizes = [4, 44, 10, 20, 20, 14]

        table = ""
        table += "\n" + tableify(heads, colSizes)
        for idx, act in enumerate(acts):
            line_color = "bold_green"
            if is_act_expired(act.dtEndTime):
                line_color = "bold_black"

            print_act_name = padLeftRight(act.sActivityName, colSizes[1], mode="left", need_truncate=True)
            remaining_times = parse_time(act.dtEndTime) - get_now()
            remaining_times = f"{remaining_times.days:3d} 天 {remaining_times.seconds // 3600} 小时"

            table += (
                "\n"
                + color(line_color)
                + tableify(
                    [idx + 1, print_act_name, act.iActivityId, act.dtBeginTime, act.dtEndTime, remaining_times],
                    colSizes,
                    need_truncate=False,
                )
            )

        logger.info(table)


@try_except()
def search_act(actId) -> Optional[AmsActInfo]:
    actId = str(actId)
    act_desc_js = get_act_desc_js(actId)
    if act_desc_js == "":
        return None

    v = act_desc_js.strip().replace("\r", "\n").split("\n")

    for line in v:
        if not line.startswith("var ams_actdesc="):
            continue
        act_json = line.replace("var ams_actdesc=", "")
        act_desc = json.loads(act_json)

        info = AmsActInfo().auto_update_config(act_desc)

        return info

    return None


def get_act_desc_js(actId):
    actId = str(actId)

    act_cache_file = with_cache(
        "act_desc",
        actId,
        cache_max_seconds=DESC_JS_CACHE_SECONDS,
        cache_miss_func=lambda: download_act_desc_js(actId),
        cache_validate_func=lambda filepath: os.path.isfile(filepath),
    )

    if not os.path.exists(act_cache_file):
        return ""

    with open(act_cache_file, encoding="utf-8") as f:
        return f.read()


def download_act_desc_js(actId: str) -> str:
    last_three = str(actId[-3:])
    act_cache_dir = f"{cached_dir}/actDesc/{last_three}/{actId}"
    act_cache_file = f"{act_cache_dir}/act.desc.js"

    # 然后从服务器获取活动信息
    actUrls = [
        f"https://dnf.qq.com/comm-htdocs/js/ams/actDesc/{last_three}/{actId}/act.desc.js",
        f"https://apps.game.qq.com/comm-htdocs/js/ams/actDesc/{last_three}/{actId}/act.desc.js",
        f"https://apps.game.qq.com/comm-htdocs/js/ams/v0.2R02/act/{actId}/act.desc.js",
    ]
    for url in actUrls:
        res = requests.get(url, timeout=1)
        if res.status_code != 200:
            continue

        make_sure_dir_exists(act_cache_dir)
        with open(act_cache_file, "w", encoding="utf-8") as f:
            f.write(res.text)

        return act_cache_file

    return ""


@try_except()
def search_ide_act(actId: str) -> Optional[IdeActInfo]:
    actId = str(actId)
    act_desc_json = get_ide_act_desc_json(actId)
    if act_desc_json == "":
        return None

    raw_act_info = json.loads(act_desc_json)
    info = IdeActInfo().auto_update_config(raw_act_info)

    return info


def get_ide_act_desc_json(actId) -> str:
    actId = str(actId)

    act_cache_file = with_cache(
        "ide_act_desc",
        actId,
        cache_max_seconds=DESC_JS_CACHE_SECONDS,
        cache_miss_func=lambda: download_ide_act_desc_json(actId),
        cache_validate_func=lambda filepath: os.path.isfile(filepath),
    )

    if not os.path.exists(act_cache_file):
        return ""

    with open(act_cache_file, encoding="utf-8") as f:
        return f.read()


def download_ide_act_desc_json(actId: str) -> str:
    first_two = str(actId[:2])
    act_cache_dir = f"{cached_dir}/ideActDesc/{first_two}"
    act_cache_file = f"{act_cache_dir}/{actId}.json"

    # 然后从服务器获取活动信息
    url = f"https://comm.ams.game.qq.com/ide/page/{actId}"

    res = requests.get(url, timeout=1)
    if res.status_code != 200:
        return ""

    make_sure_dir_exists(act_cache_dir)
    with open(act_cache_file, "w", encoding="utf-8") as f:
        f.write(res.text)

    return act_cache_file


def get_ams_act_desc(actId: str) -> str:
    act = get_ams_act(actId)
    if act is None:
        return ""

    return format_act(act.iActivityId, act.sActivityName, act.dtBeginTime, act.dtEndTime)


def get_ams_act(actId: str) -> Optional[AmsActInfo]:
    act = search_act(actId)
    return act


def get_ide_act_desc(actId: str) -> str:
    act = get_ide_act(actId)
    if act is None:
        return ""

    action = act.dev.action
    return format_act(actId, action.sName, action.sUpDate, action.sDownDate)


def get_ide_act(actId: str) -> Optional[IdeActInfo]:
    act = search_ide_act(actId)
    return act


def get_not_ams_act_desc(act_name: str) -> str:
    act = get_not_ams_act(act_name)
    if act is None:
        return f"未找到活动 {act_name} 的相关信息"

    return format_act(act.iActivityId, act.sActivityName, act.dtBeginTime, act.dtEndTime)


def get_not_ams_act(act_name: str) -> Optional[AmsActInfo]:
    for act in not_ams_activities:
        if act.sActivityName == act_name:
            return act

    return None


def format_act(act_id: str, act_name: str, begin_time: str, end_time: str, needPadding=False):
    if needPadding:
        act_name = padLeftRight(act_name, 44, mode="left")

    msg = f"活动 {act_name}({act_id})"

    if end_time != "":
        msg += f" 开始时间为 {begin_time}，结束时间为 {end_time}，"
        if not is_act_expired(end_time):
            msg += f"距离结束还有 {get_remaining_time(end_time)}"
        else:
            msg += f"已经结束了 {get_past_time(end_time)}"
    else:
        msg += " 尚无已知的开始和结束时间"

    return msg


if __name__ == "__main__":
    urls = Urls()
    urls.show_current_valid_act_infos()
    # print(get_not_ams_act_desc("集卡"))
    # print(search_ide_act("44_dOsCdP"))
