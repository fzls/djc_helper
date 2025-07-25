from __future__ import annotations

import json
import os

import requests

from const import cached_dir
from dao import ActCommonInfo, AmsActInfo, IdeActInfo
from log import color, logger
from util import (
    exists_flag_file,
    format_time,
    generate_raw_data_template,
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
    # 长期免费活动
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "道聚城"),
    newNotAmsActInfo("2023-12-21 00:00:00", not_know_end_time____, "DNF地下城与勇士心悦特权专区"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "心悦app"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "dnf论坛签到"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "小酱油周礼包和生日礼包"),
    #
    # 短期付费活动
    #
    newNotAmsActInfo(month_start_day______, month_end_day________, "DNF助手编年史"),
    newNotAmsActInfo("2025-05-20 00:00:00", "2025-10-31 23:59:59", "DNF福利中心兑换"),
    newNotAmsActInfo("2025-06-12 00:00:00", "2025-07-30 23:59:59", "colg每日签到"),
    newNotAmsActInfo("2025-06-07 11:00:00", "2025-07-31 23:59:59", "回流引导秘籍"),
    newNotAmsActInfo("2025-06-24 10:00:00", "2025-07-31 23:59:59", "colg其他活动"),
    newNotAmsActInfo("2025-06-20 10:10:00", "2025-07-31 23:59:59", "vp挑战赛"),
    newNotAmsActInfo("2025-06-20 00:00:00", "2025-09-28 23:59:59", "绑定手机活动"),
    newNotAmsActInfo("2025-07-24 00:00:00", "2025-08-20 23:59:59", "助手限定活动"),
    #
    # 已过期活动
    #
    newNotAmsActInfo("2025-06-26 19:10:00", "2025-07-10 23:59:59", "挑战世界记录"),
    newNotAmsActInfo("2025-06-12 10:00:00", "2025-07-16 23:59:59", "周年庆网吧集结"),
    newNotAmsActInfo("2025-06-12 00:00:00", "2025-07-11 23:59:59", "DNF心悦wpe"),
    newNotAmsActInfo("2025-06-12 00:00:00", "2025-07-11 23:59:59", "WeGame活动"),
    newNotAmsActInfo("2025-06-12 00:00:00", "2025-07-13 23:59:59", "DNF落地页活动_ide"),
    newNotAmsActInfo("2025-06-12 00:00:00", "2025-07-10 23:59:59", "DNF周年庆登录活动"),
    newNotAmsActInfo("2025-04-24 00:00:00", "2025-07-11 21:59:59", "超级会员"),
    newNotAmsActInfo("2025-05-22 00:00:00", "2025-07-09 23:59:59", "新职业预约活动"),
    newNotAmsActInfo("2025-03-03 00:00:00", "2025-07-30 23:59:59", "助手魔界人每日幸运签"),
    newNotAmsActInfo("2025-05-12 19:10:00", "2025-06-30 23:59:59", "幸运色卡"),
    newNotAmsActInfo("2025-05-23 11:30:00", "2025-07-03 21:59:59", "超核勇士wpe_dup"),
    newNotAmsActInfo("2025-04-24 15:00:00", "2025-06-09 21:59:59", "超核勇士wpe"),
    newNotAmsActInfo("2025-04-24 00:00:00", "2025-05-21 23:59:59", "共赴西装节"),
    newNotAmsActInfo("2025-02-28 00:00:00", "2025-03-26 23:59:59", "助手能量之芽"),
    newNotAmsActInfo("2024-12-19 11:00:00", "2025-03-13 23:59:59", "DNF预约"),
    newNotAmsActInfo("2023-12-21 00:00:00", "2025-02-28 23:59:59", "DNF漫画预约活动"),
    newNotAmsActInfo("2025-01-26 10:00:00", "2025-02-12 23:59:59", "新春充电计划"),
    newNotAmsActInfo("2025-01-16 00:00:00", "2025-02-14 23:59:59", "集卡"),
    newNotAmsActInfo("2024-09-12 12:00:00", "2025-01-16 23:59:59", "喂养删除补偿"),
    newNotAmsActInfo("2024-11-23 10:00:00", "2024-12-08 23:59:59", "嘉年华星与心愿"),
    newNotAmsActInfo("2024-09-12 12:00:00", "2024-10-13 23:59:59", "回流攻坚队"),
    newNotAmsActInfo("2024-02-01 12:00:00", "2024-11-29 23:59:59", "DNF神界成长之路"),
    newNotAmsActInfo("2024-04-18 00:00:00", "2024-12-31 23:59:59", "DNF神界成长之路二期"),
    newNotAmsActInfo("2024-07-18 00:00:00", "2024-12-31 23:59:59", "DNF神界成长之路三期"),
    newNotAmsActInfo("2024-09-12 12:00:00", "2024-10-09 23:59:59", "DNF卡妮娜的心愿摇奖机"),
    newNotAmsActInfo("2024-06-13 00:00:00", "2024-07-25 23:59:59", "勇士的冒险补给"),
    newNotAmsActInfo("2024-06-20 00:00:00", "2024-07-10 23:59:59", "DNF格斗大赛"),
    newNotAmsActInfo("2023-11-16 00:00:00", "2023-12-19 23:59:59", "qq视频蚊子腿-爱玩"),
    newNotAmsActInfo("2023-12-21 00:00:00", "2024-01-24 23:59:59", "DNF马杰洛的规划"),
    newNotAmsActInfo("2023-12-21 00:00:00", "2024-02-11 23:59:59", "dnf助手活动wpe"),
    newNotAmsActInfo("2023-11-16 00:00:00", "2023-11-30 23:59:59", "DNF娱乐赛"),
    newNotAmsActInfo("2023-12-21 00:00:00", "2024-01-25 23:59:59", "拯救赛利亚"),
    newNotAmsActInfo("2024-02-01 12:00:00", "2024-02-29 23:59:59", "DNF年货铺"),
    newNotAmsActInfo("2024-04-18 00:00:00", "2024-05-17 23:59:59", "DNFxSNK"),
]

act_name_to_url = {
    # 长期免费活动
    "道聚城": "https://daoju.qq.com/mall/",
    "DNF地下城与勇士心悦特权专区": "https://act.xinyue.qq.com/act/a20231103dnf/index.html",
    "心悦app": "https://xinyue.qq.com/beta/#/download",
    "dnf论坛签到": "https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign",
    "小酱油周礼包和生日礼包": "游戏内右下角点击 小酱油 图标",
    #
    # 短期付费活动
    #
    "DNF助手编年史": "dnf助手左侧栏",
    "DNF福利中心兑换": "https://dnf.qq.com/cp/a20190312welfare/index.htm",
    "colg每日签到": "https://bbs.colg.cn/forum-171-1.html",
    "回流引导秘籍": "https://dnf.qq.com/cp/a20250612guide/",
    "colg其他活动": "https://hub.bbs.colg.cn/activity/professional_team/index.html",
    "vp挑战赛": "https://dnf.qq.com/cp/a20250530tzs/index.html",
    "绑定手机活动": "https://dnf.qq.com/cp/a20230817info/",
    "助手限定活动": "https://dzhu.qq.com/fe/dnf/summer-act/",
    #
    # 已过期活动
    #
    "挑战世界记录": "https://dnf.qq.com/cp/a20250617record/index.html",
    "start云游戏": "https://my.start.qq.com/act/my_activity/?group_id=1&act_id=158#/index",
    "周年庆网吧集结": "https://dnf.qq.com/cp/a20250525netbar/",
    "DNF心悦wpe": "https://act.xinyue.qq.com/act/a20250606dnfyear/index.html",
    "WeGame活动": "https://dnf.qq.com/cp/a20250612wegame/index.html",
    "DNF落地页活动_ide": "https://dnf.qq.com/cp/a20250612index/",
    "DNF周年庆登录活动": "https://dnf.qq.com/cp/a20250612gift/",
    "超级会员": "https://act.qzone.qq.com/v2/vip/tx/p/53130_a5314717",
    "新职业预约活动": "https://dnf.qq.com/cp/a20250517brand/index.html",
    "助手魔界人每日幸运签": "https://dzhu.qq.com/fe/dnf/lucky_lottery/?share=1&gameId=10014&activityId=1001",
    "幸运色卡": "https://dnf.qq.com/cp/a20250611dnf/",
    "超核勇士wpe_dup": "https://act.supercore.qq.com/supercore/act/affea2f1e0525457aae20043f8eafd4ee/index.html?actVersion=364206",
    "超核勇士wpe": "https://act.supercore.qq.com/supercore/act/a311c68ee22864aebac61a94f2612ac54/index.html?actVersion=353918",
    "共赴西装节": "https://dnf.qq.com/cp/a20250424welcome/index.html?pt=1",
    "助手能量之芽": "https://dzhu.qq.com/fe/dnf/energy_tree/?share=1&gameId=10014&activityId=1",
    "DNF预约": "https://dnf.qq.com/cp/a20241219prepare/index.html",
    "DNF漫画预约活动": "https://dnf.qq.com/cp/a20231211comic/index.html",
    "新春充电计划": "https://dnf.qq.com/cp/a20250126battery/",
    "集卡": "https://act.qzone.qq.com/v2/vip/tx/p/50965_510d3610",
    "喂养删除补偿": "https://dnf.qq.com/cp/a20240912being/",
    "嘉年华星与心愿": "https://dnf.qq.com/cp/a20241030wish/index.html",
    "回流攻坚队": "https://dnf.qq.com/cp/a2024socialize/index_g.html",
    "DNF神界成长之路": "https://dnf.qq.com/cp/a2024user/page1.html",
    "DNF神界成长之路二期": "https://dnf.qq.com/cp/a2024user/page2.html",
    "DNF神界成长之路三期": "https://dnf.qq.com/cp/a2024user/index.html",
    "DNF卡妮娜的心愿摇奖机": "https://dnf.qq.com/cp/a20240912wish/indexm.html?pt=1",
    "勇士的冒险补给": "https://act.xinyue.qq.com/bb/act/a4a4b8cefdc8645299a546567fc1c68ad/index.html",
    "DNF格斗大赛": "https://act.xinyue.qq.com/act/a20240613dnfcombat/index.html",
    "DNF落地页活动_ide_dup": "https://dnf.qq.com/act/a20240418index/index.html",
    "DNFxSNK": "https://dnf.qq.com/cp/a20240418snklink/indexm.html",
    "DNF年货铺": "https://dnf.qq.com/cp/a20240201newyear/",
    "dnf助手活动wpe": "https://mwegame.qq.com/act/dnf/a20231213zhaohui/index.html",
    "拯救赛利亚": "https://dnf.qq.com/cp/a20231221save/indexm.html",
    "DNF马杰洛的规划": "https://dnf.qq.com/cp/a20231221card/index.html",
    "神界预热": "https://dnf.qq.com/cp/a20231207gift/index.html",
    "qq视频蚊子腿-爱玩": "https://ovact.iwan.qq.com/magic-act/WHJL0iOwifXqDKtGNrOsd3jTDJ/index_page1.html",
    "DNF落地页活动": "https://dnf.qq.com/cp/a20231116index/index.html",
    "DNF娱乐赛": "https://dnf.qq.com/act/a20231106match/index.html",
    "dnf助手活动": "https://mwegame.qq.com/helper/dnf/laoban/index.html",
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
        self.get_game_role_list = "https://comm.aci.game.qq.com/main?game={game}&sCloudApiName=ams.gameattr.role&tempArea={tempArea}&tempAreaname={tempAreaname}&area={area}&sAreaName={sAreaName}&callback={millseconds}&_={millseconds}"
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

        # fmt: off

        # 一些参数列表
        # 默认填充的空参数
        # ame的参数列表
        self.amesvr_default_params_list = [
            "iActivityId", "g_tk", "iFlowId", "package_id", "lqlevel", "teamid", "weekDay", "eas_url", "sServiceDepartment", "sServiceType", "sArea", "sRoleId", "uin", "userId", "token", "sRoleName",
            "serverId", "areaId", "skey", "nickName", "date", "dzid", "page", "iPackageId", "plat", "extraStr", "sContent", "sPartition", "sAreaName", "md5str", "ams_md5str", "ams_checkparam",
            "checkparam", "type", "moduleId", "giftId", "acceptId", "invitee", "giftNum", "sendQQ", "receiver", "receiverName", "inviterName", "user_area", "user_partition", "user_areaName",
            "user_roleId", "user_roleName", "user_roleLevel", "user_checkparam", "user_md5str", "user_sex", "user_platId", "cz", "dj", "siActivityId", "needADD", "dateInfo", "sId", "userNum",
            "cardType", "inviteId", "sendName", "receiveUin", "receiverUrl", "index", "pageNow", "pageSize", "clickTime", "username", "petId", "skin_id", "decoration_id", "fuin", "sCode", "sNickName",
            "iId", "sendPage", "hello_id", "prize", "qd", "iReceiveUin", "map1", "map2", "len", "itemIndex", "sRole", "loginNum", "level", "inviteUin", "iGuestUin", "ukey", "iGiftID", "iInviter",
            "iPageNow", "iPageSize", "iType", "iWork", "iPage", "sNick", "iMatchId", "iGameId", "iIPId", "iVoteId", "iResult", "personAct", "teamAct", "param", "dhnums", "sUin", "pointID", "workId",
            "isSort", "jobName", "title", "actSign", "iNum", "prefer", "card", "answer1", "answer2", "answer3", "countsInfo", "power", "crossTime", "getLv105", "use_fatigue", "exchangeId", "sChannel",
            "pass", "pass_date", "bossId", "today", "anchor", "sNum", "week", "position", "packages", "selectNo", "targetQQ", "u_confirm",
        ]
        # ide的参数列表
        self.ide_default_params_list = [
            "iChartId", "iSubChartId", "sIdeToken", "sRoleId", "sRoleName", "sArea", "sMd5str", "sCheckparam", "roleJob", "sAreaName", "sAuthInfo", "sActivityInfo", "openid", "sCode", "startPos",
            "eas_url", "eas_refer", "iType", "iPage", "type", "sUin", "dayNum", "iFarmland", "fieldId", "sRice", "packageId", "targetId", "myId", "id", "iCardId", "iAreaId", "sRole", "drinksId",
            "gameId", "score", "loginDays", "iSuccess", "iGameId", "sAnswer", "index", "u_stage", "u_task_index", "u_stage_index", "num", "sPartition", "sPlatId", "source", "iIndex", "giftId", "iCode",
            "sDay", "iNum", "hour", "week", "points", "taskId",
        ]
        # 其他默认填充的空参数
        self.other_default_empty_params_list = [
            "iActionId", "iGoodsId", "sBizCode", "partition", "iZoneId", "platid", "sZoneDesc", "sGetterDream", "isLock", "amsid", "iLbSel1", "mold", "exNum", "iCard", "actionId",
            "adLevel", "adPower", "pUserId", "isBind", "toUin", "appid", "appOpenid", "accessToken", "iRoleId", "randomSeed", "taskId", "point", "cRand", "tghappid", "sig",
            "date_chronicle_sign_in", "flow_id", "tempArea", "tempAreaname",
        ]
        # 基于上面三个，生成一个format url时使用的这些参数的空值列表
        self.default_empty_params = {
            key: ""
            for key in [
                *self.amesvr_default_params_list,
                *self.ide_default_params_list,
                *self.other_default_empty_params_list,
            ]
        }

        # fmt: on

        # amesvr通用活动
        # 其对应活动描述文件一般可通过下列链接获取，其中{actId}替换为活动ID，{last_three}替换为活动ID最后三位
        # https://dnf.qq.com/comm-htdocs/js/ams/actDesc/{last_three}/{actId}/act.desc.js
        # https://apps.game.qq.com/comm-htdocs/js/ams/v0.2R02/act/{actId}/act.desc.js
        self.iActivityId_djc_operations = "11117"  # 道聚城
        self.iActivityId_xinyue_battle_ground = "366480"  # DNF地下城与勇士心悦特权专区
        self.iActivityId_dnf_welfare = "215651"  # DNF福利中心兑换
        self.iActivityId_dnf_welfare_login_gifts = "441426"  # DNF福利中心-登陆游戏领福利
        self.iActivityId_dnf_helper = "581863"  # DNF助手活动
        self.iActivityId_dnf_bbs_v1 = "431448"  # DNF论坛积分兑换活动
        self.iActivityId_dnf_bbs_v2 = "397645"  # DNF论坛积分兑换活动
        self.iActivityId_dnf_luodiye = "593802"  # DNF落地页活动需求
        self.iActivityId_dnf_wegame = "603490"  # WeGame活动
        self.iActivityId_dnf_pk = "463319"  # DNF格斗大赛
        self.iActivityId_dnf_comic = "386057"  # DNF&腾讯动漫周年庆合作活动
        self.iActivityId_dnf_anniversary = "474801"  # DNF周年庆登录活动
        self.iActivityId_maoxian = "548876"  # 勇士的冒险补给
        self.iActivityId_dnf_reservation = "590510"  # DNF预约
        self.iActivityId_dnf_bind_phone = "420695"  # 绑定手机活动
        self.iActivityId_dnf_shenjie_yure = "602887"  # 神界预热
        self.iActivityId_dnf_cloud_game = "735481"  # start云游戏

        # fmt: off
        # amesvr活动
        self.amesvr = "https://{amesvr_host}/ams/ame/amesvr?ameVersion=0.3&sSDID={sSDID}&sMiloTag={sMiloTag}&sServiceType={sServiceType}&iActivityId={iActivityId}&sServiceDepartment={sServiceDepartment}&isXhrPost=true"
        self.amesvr_raw_data = "xhrPostKey=xhr_{millseconds}&eas_refer=http%3A%2F%2Fnoreferrer%2F%3Freqid%3D{uuid}%26version%3D23&e_code=0&g_code=0&xhr=1" + "&" + generate_raw_data_template(self.amesvr_default_params_list)
        # fmt: on

        # ide通用活动
        # 其对应活动描述文件一般可通过下列链接获取，其中{actId}替换为活动ID
        #   https://comm.ams.game.qq.com/ide/page/{actId}
        #
        # note: 在活动页面 网络请求 过滤 ide/page/ 即可定位到活动id
        self.ide_iActivityId_dnf_social_relation_permission = "14_uK7KKe"  # DNF关系链接-用户授权接口
        self.ide_iActivityId_dnf_anniversary = "86_e5rV7O"  # DNF周年庆登录活动
        self.ide_iActivityId_dnf_game = "64_Yetu1m"  # dnf娱乐赛
        self.ide_iActivityId_dnf_luodiye = "97_3PFh1o"  # DNF落地页
        self.ide_iActivityId_dnf_luodiye_dup = "16_FDvprx"  # DNF落地页dup
        self.ide_iActivityId_dnf_comic = "64_p5cLkZ"  # DNF漫画预约活动
        self.ide_iActivityId_dnf_save_sailiyam = "35_w7UB7L"  # 拯救赛利亚
        self.ide_iActivityId_dnf_nianhuopu = "47_aiKrck"  # DNF年货铺
        self.ide_iActivityId_dnf_shenjie_grow_up = "34_DA6bLu"  # DNF神界成长之路
        self.ide_iActivityId_dnf_shenjie_grow_up_v2 = "22_ylD5VE"  # DNF神界成长之路二期
        self.ide_iActivityId_dnf_shenjie_grow_up_v3 = "97_JFFynS"  # DNF神界成长之路三期
        self.ide_iActivityId_dnf_snk = "43_L5dwVl"  # DNFxSNK
        self.ide_iActivityId_dnf_kanina = "89_On7Z0H"  # DNF卡妮娜的心愿摇奖机
        self.ide_iActivityId_dnf_wegame = "5_BkxPRF"  # WeGame活动
        self.ide_iActivityId_weiyang_compensate = "4_ttG6gw"  # 喂养删除补偿
        self.ide_iActivityId_dnf_socialize = "25_KHIbP0"  # 回流攻坚队
        self.ide_iActivityId_dnf_star_and_wish = "71_ptNFnW"  # 嘉年华星与心愿
        self.ide_iActivityId_dnf_reservation = "45_eTCfMl"  # DNF预约
        self.ide_iActivityId_dnf_recall_guide = "26_iNpZy8"  # 回流引导秘籍
        self.ide_iActivityId_new_year_signin = "12_BfzMwV"  # 新春充电计划
        self.ide_iActivityId_dnf_suit = "14_UrsfVG"  # 共赴西装节
        self.ide_iActivityId_dnf_reserve = "76_rZP67G"  # 新职业预约活动
        self.ide_iActivityId_dnf_welfare = "99_fdC9AL"  # DNF福利中心兑换
        self.ide_iActivityId_dnf_netbar = "11_RWbofn"  # 周年庆网吧集结
        self.ide_iActivityId_dnf_color = "16_kfJ3xD"  # 幸运色卡
        self.ide_iActivityId_dnf_challenge_world_record = "70_gzIaCC"  # 挑战世界记录
        self.ide_iActivityId_vp_challenge = "65_6beKBQ"  # vp挑战赛
        self.ide_iActivityId_dnf_bind_phone = "3_Rsi2sk"  # 绑定手机活动

        # re: 部分情况下，可能会同时关联ame和ide活动，这里放到一起管理
        self.iActivityId_majieluo = "603648"  # DNF马杰洛的规划
        self.ide_iActivityId_majieluo = "16_S86Tjb"  # DNF马杰洛的规划

        # ide活动
        self.ide = "https://{ide_host}/ide/"
        self.ide_raw_data = "e_code=0&g_code=0" + "&" + generate_raw_data_template(self.ide_default_params_list)

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
        self.pesudo_ark_lottery_act_id = 10018

        # qq视频 - 爱玩
        self.qq_video_iwan = "https://act.iwan.qq.com/trpc.iwan.mission_system_server.MissionSystemSvr/dealSimpleMission?platformId=10&platformid=10&guid=&device=&acctype=qq&missionId={missionId}&gameId=48&sPlat=&sArea=&serverId={serverId}&sRoleId={sRoleId}"

        # dnf助手编年史活动
        # mwegame peak 相关接口，额外参数：api: 具体api名称，userId（助手userId），sPartition/sRoleId, isLock->isLock, amsid->sLbCode, iLbSel1->iLbSel1, 区分自己还是队友的基础奖励, num: 1, mold: 1-自己，2-队友,  exNum->1, iCard->iCard, iNum->iNum
        self.dnf_helper_chronicle_wang_xinyue = (
            "https://dzhu.qq.com/peak/{api}?userId={userId}&gameId=1006&sPartition={sPartition}&sRoleId={sRoleId}&game_code=dnf&token={token}&uin={uin}&toUin={toUin}&uniqueRoleId={uniqueRoleId}&openid="
            "&isLock={isLock}&amsid={amsid}&iLbSel1={iLbSel1}&num={num}&mold={mold}&exNum={exNum}&iCard={iCard}&iNum={iNum}&appidTask=1000042&&date={date_chronicle_sign_in}&accessToken={accessToken}&appOpenid={appOpenid}&appid={appid}"
            "&cRand={cRand}&tghappid={tghappid}&sig={sig}"
        )
        # mwegame ajax 相关接口，额外参数：api: 具体api名称，userId（助手userId），sPartition/sRoleId, actionId: 自己的任务为任务信息中的各个任务的mActionId，队友的任务对应的是各个任务的pActionId
        self.dnf_helper_chronicle_mwegame = (
            "https://dzhu.qq.com/act/GradeExp/ajax/{api}?userId={userId}&gameId=1006&sPartition={sPartition}&sRoleId={sRoleId}&game_code=dnf&actionId={actionId}&pUserId={pUserId}&isBind={isBind}"
            "&cRand={cRand}&tghappid={tghappid}&sig={sig}"
        )

        # 编年史新版接口
        self.dnf_helper_chronicle_yoyo = "https://dzhu.qq.com/yoyo/dnf/{api}"

        # 助手活动相关接口
        self.dnf_helper = "https://mwegame.qq.com/act/dnf/destiny/{api}?gameId=10014&roleSwitch=1&toOpenid=&roleId={roleId}&uniqueRoleId={uniqueRoleId}&openid=&serverName={serverName}&toUin={toUin}&cGameId=1006&userId={userId}&serverId={serverId}&token={token}&isMainRole=0&subGameId=10014&areaId={areaId}&gameName=DNF&areaName={areaName}&roleJob={roleJob}&nickname={nickname}&roleName={roleName}&uin={uin}&roleLevel={roleLevel}&"

        # hello语音（皮皮蟹），额外参数：api，hello_id，type，packid
        self.hello_voice = "https://ulink.game.qq.com/app/1164/c7028bb806cd2d6c/index.php?route=Raward/{api}&iActId=1192&ulenv=&game=dnf&hello_id={hello_id}&type={type}&packid={packid}"

        # dnf论坛签到，额外参数：formhash: 论坛formhash
        self.dnf_bbs_signin = (
            "https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign&operation=qiandao&formhash={formhash}&format=empty"
        )
        self.dnf_bbs_home = "https://dnf.gamebbs.qq.com/home.php?mod=spacecp&ac=credit"

        # colg-战令
        self.colg_url = "https://bbs.colg.cn/forum-171-1.html"
        self.colg_task_info_url = "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=getTask&fid=171"
        self.colg_sign_in_url = "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=passUserSign"
        self.colg_take_sign_in_credits = (
            "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=getUserCredit&aid={aid}&task_id={task_id}"
        )
        self.colg_take_sign_in_get_reward = "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=getReward&reward_id={reward_id}&aid={aid}&from_id=1"
        self.colg_mall_product_list_url = "https://bbs.colg.cn/colg_cmall-colg_cmall.html/getCMallProductList"
        self.colg_mall_get_reward_url = "https://bbs.colg.cn/colg_cmall-colg_cmall.html/getCMallRewardV1"
        # ------- colg其他活动 --------
        self.colg_other_act_type = 2
        self.colg_other_act_id = 28
        # 活动页面
        self.colg_other_act_url = "https://hub.bbs.colg.cn/activity/professional_team/index.html"
        # api链接
        self.colg_other_act_api = "https://bbs.colg.cn/colg_activity_new-career_village.html/{api}?aid=28"
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

        self.dnf_xinyue_wpe_api = "https://agw.xinyue.qq.com/amp2.WPESrv/WPEIndex?flowId={flowId}&actId={actId}"
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

        # 助手能量之芽
        self.dnf_helper_energy_tree_api = "https://dzhu.qq.com/zangyi/activity/activity"
        # 助手魔界人每日幸运签
        self.dnf_helper_lucky_lottery_api = "https://dzhu.qq.com/zangyi/activity/act"
        # 助手限定活动
        self.dnf_helper_limit_act_api = "https://dzhu.qq.com/zangyi/activity/act"

    def show_current_valid_act_infos(self):
        acts: list[ActCommonInfo] = []

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

        heads, colSizes = zip(
            ("序号", 4),
            ("活动名称", 44),
            ("活动ID", 10),
            ("开始时间", 20),
            ("结束时间", 20),
            ("剩余时间", 14),
        )

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
def search_act(actId) -> AmsActInfo | None:
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
def search_ide_act(actId: str) -> IdeActInfo | None:
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


def get_ams_act(actId: str) -> AmsActInfo | None:
    act = search_act(actId)
    return act


def get_ide_act_desc(actId: str) -> str:
    act = get_ide_act(actId)
    if act is None:
        return ""

    action = act.dev.action
    return format_act(actId, action.sName, action.sUpDate, action.sDownDate)


def get_ide_act(actId: str) -> IdeActInfo | None:
    act = search_ide_act(actId)
    return act


def get_not_ams_act_desc(act_name: str) -> str:
    act = get_not_ams_act(act_name)
    if act is None:
        return f"未找到活动 {act_name} 的相关信息"

    return format_act(act.iActivityId, act.sActivityName, act.dtBeginTime, act.dtEndTime)


def get_not_ams_act(act_name: str) -> AmsActInfo | None:
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
