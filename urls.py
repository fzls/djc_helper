import json
import os
from typing import Optional

import requests

from const import cached_dir
from dao import AmsActInfo
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


def newAmsActInfo(sActivityName, dtBeginTime, dtEndTime):
    info = AmsActInfo()
    info.iActivityId = "000000"
    info.sActivityName = sActivityName
    info.dtBeginTime = dtBeginTime
    info.dtEndTime = dtEndTime

    return info


not_know_start_time = "2000-01-01 00:00:00"
# 不知道时间的统一把时间设定为后年年初-。-
not_know_end_time = format_time(
    get_now().replace(year=get_now().year + 2, month=1, day=1, hour=0, second=0, microsecond=0)
)

month_start_day, month_end_day = start_and_end_date_of_a_month(get_now())

not_ams_activities = [
    newAmsActInfo("道聚城", not_know_start_time, not_know_end_time),
    newAmsActInfo("黑钻礼包", not_know_start_time, not_know_end_time),
    newAmsActInfo("腾讯游戏信用礼包", not_know_start_time, not_know_end_time),
    newAmsActInfo("心悦app", not_know_start_time, not_know_end_time),
    newAmsActInfo("管家蚊子腿", "2021-12-16 00:00:00", "2022-01-16 23:59:59"),
    newAmsActInfo("qq视频蚊子腿", "2021-10-18 00:00:00", "2021-11-18 23:59:59"),
    newAmsActInfo("qq视频蚊子腿-爱玩", "2021-11-26 00:00:00", "2021-12-17 23:59:59"),
    newAmsActInfo("会员关怀", "2021-03-31 00:00:00", not_know_end_time),
    newAmsActInfo("超级会员", "2021-12-16 00:00:00", "2022-01-16 23:59:59"),
    newAmsActInfo("黄钻", "2021-12-16 00:00:00", "2022-01-16 23:59:59"),
    newAmsActInfo("集卡", "2021-12-16 00:00:00", "2022-01-18 23:59:59"),
    newAmsActInfo("DNF助手编年史", format_time(month_start_day), format_time(month_end_day)),
    newAmsActInfo("colg每日签到", "2021-09-17 00:00:00", "2021-10-19 23:59:59"),
    newAmsActInfo("小酱油周礼包和生日礼包", not_know_start_time, not_know_end_time),
    newAmsActInfo("qq会员杯", "2021-09-19 00:00:00", "2021-10-5 23:59:59"),
    newAmsActInfo("虎牙", "2021-09-11 00:00:00", "2021-10-13 23:59:59"),
    newAmsActInfo("WeGame活动_新版", "2021-12-13 00:00:00", "2021-12-31 23:59:59"),
]

act_name_to_url = {
    # 长期免费活动
    "道聚城": "https://daoju.qq.com/mall/ 下载app",
    "DNF地下城与勇士心悦特权专区": "https://xinyue.qq.com/act/a20210317dnf/index_pc.html",
    "心悦app": "https://xinyue.qq.com/beta/#/download",
    "黑钻礼包": "https://dnf.qq.com/act/blackDiamond/gift.shtml",
    "腾讯游戏信用礼包": "https://gamecredit.qq.com/static/web/index.html#/gift-pack",
    "心悦app理财礼卡": "https://xinyue.qq.com/act/app/xyjf/a20171031lclk/index1.shtml",
    "心悦猫咪": "https://xinyue.qq.com/act/a20180912tgclubcat/index.html",  # userAgent: tgclub/5.7.11.85(Xiaomi MIX 2;android 9;Scale/440;android;865737030437124)
    "心悦app周礼包": "https://xinyue.qq.com/act/a20180906gifts/index.html",
    "dnf论坛签到": "https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign",
    "小酱油周礼包和生日礼包": "游戏内右下角点击 小酱油 图标",
    #
    # 短期付费活动
    #
    "DNF助手编年史": "dnf助手左侧栏",
    "DNF漫画预约活动": "https://dnf.qq.com/lbact/a20210617comic/",
    "DNF福利中心兑换": "https://dnf.qq.com/cp/a20190312welfare/index.htm",
    "会员关怀": "https://act.qzone.qq.com/v2/vip/tx/p/1648_4615e306",
    "hello语音网页礼包兑换": "https://dnf.qq.com/cp/a20210806dnf/",
    "DNF闪光杯": "https://xinyue.qq.com/act/a20211022sgb/pc/index.html",
    "DNF集合站_史诗之路": "https://dnf.qq.com/lbact/a20211028jhye/index.html",
    "DNF心悦": "https://xinyue.qq.com/act/a20211108zsdc/index_pc.html",
    "WeGame活动": "https://dnf.qq.com/lbact/a20211118wegame/index.html",
    "DNF落地页活动": "https://dnf.qq.com/cp/a20211118index/",
    "DNF公会活动": "https://dnf.qq.com/cp/a20211028GH/index.html",
    "DNF马杰洛的规划": "https://dnf.qq.com/cp/a20211122care/index.html",
    "qq视频蚊子腿-爱玩": "https://magic.iwan.qq.com/magic-act/w5jli4iijddi98d7i8jr00hpu9/index_page1.html",
    "DNF名人堂": "https://dnf.qq.com/cp/hof20211123/index.html",
    "DNF预约": "https://dnf.qq.com/cp/a20211115dnf/",
    "DNF记忆": "https://dnf.qq.com/cp/a20211203dnfmem/index.html",
    "关怀活动": "https://dnf.qq.com/lbact/a20211118care/index.html",
    "DNF娱乐赛": "https://dnf.qq.com/cp/a20211219dnfyulesai/index.html",
    "dnf助手活动": "https://mwegame.qq.com/act/dnf/MatchGuess2021/index1",
    "WeGame活动_新版": "https://act.wegame.com.cn/wand/danji/a20211201DNFCarnival/",
    "黄钻": "https://act.qzone.qq.com//v2/vip/tx/p/20171_a565fd57",
    "超级会员": "https://act.qzone.qq.com//v2/vip/tx/p/7531_349e4f73",
    "管家蚊子腿": "https://sdi.3g.qq.com/v/2021121414444511605",
    "集卡": "https://act.qzone.qq.com//v2/vip/tx/p/7533_13e52f70",
    #
    # 已过期活动
    #
    "DNF共创投票": "http://dnf.qq.com/cp/a20210922create/page.html",
    "DNF集合站": "https://dnf.qq.com/lbact/a20210914jhye/index.html",
    "qq视频蚊子腿": "https://m.film.qq.com/magic-act/yauhs87ql00t63xttwkas8papl/index_index.html",
    "KOL": "https://dnf.qq.com/lbact/a20211014kol2/index.html",
    "WeGameDup": "https://dnf.qq.com/lbact/a20211014wg/index.html",
    "勇士的冒险补给": "https://dnf.qq.com/lbact/a20210622lb0wcuh/index.html",
    "轻松之路": "https://dnf.qq.com/cp/a20210914qszlm/index.html",
    "colg每日签到": "https://bbs.colg.cn/forum-171-1.html",
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
    "DNF周年庆登录活动": "https://dnf.qq.com/cp/a20210618anniversary/index.html",
    "刃影预约活动": "https://dnf.qq.com/cp/a20210618reserve/index.html",
    "DNF格斗大赛": "https://dnf.qq.com/cp/a20210405pk/",
    "DNF奥兹玛竞速": "https://xinyue.qq.com/act/a20210526znqhd/index.html",
    "我的dnf13周年活动": "https://dnf.qq.com/cp/a20210604history/index.html",
    "qq视频-AME活动": "https://dnf.qq.com/cp/a20210816video/",
    "qq会员杯": "https://club.vip.qq.com/qqvip/acts2021/dnf",
}


def get_act_url(act_name: str) -> str:
    return act_name_to_url.get(act_name, "未找到活动链接，请自行百度")


class Urls:
    def __init__(self):
        # 余额
        self.balance = "https://djcapp.game.qq.com/cgi-bin/daoju/djcapp/v5/solo/jfcloud_flow.cgi?&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&&method=balance&page=0&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        self.money_flow = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.bean.water&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&page=1&starttime={starttime}&endtime={endtime}&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 每日登录事件：imsdk登录
        self.imsdk_login = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.message.imsdk.login&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 每日登录事件：app登录
        self.user_login_event = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.login.user.first&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 每日签到的奖励规则
        self.sign_reward_rule = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.reward.sign.rule&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&output_format=json&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 签到相关接口的入口
        self.sign = "https://comm.ams.game.qq.com/ams/ame/amesvr?ameVersion=0.3&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sServiceType=dj&iActivityId=11117&sServiceDepartment=djc&set_info=newterminals&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&&appSource=android&ch=10003&osVersion=Android-28&sVersionName=v4.1.6.0"
        # post数据，需要手动额外传入参数：iFlowId
        self.sign_raw_data = "appVersion={appVersion}&g_tk={g_tk}&iFlowId={iFlowId}&month={month}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&sign_version=1.0&ch=10003&iActivityId=11117&osVersion=Android-28&sVersionName=v4.1.6.0&sServiceDepartment=djc&sServiceType=dj&appSource=android"

        # 任务列表
        self.usertask = "https://djcapp.game.qq.com/daoju/v3/api/we/usertaskv2/Usertask.php?iAppId=1001&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&_app_id=1001&output_format=json&_output_fmt=json&appid=1001&optype=get_usertask_list&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 领取任务奖励，需要手动额外传入参数：iruleId
        self.take_task_reward = "https://djcapp.game.qq.com/daoju/v3/api/we/usertaskv2/Usertask.php?iAppId=1001&appVersion={appVersion}&iruleId={iruleId}&p_tk={p_tk}&sDeviceID={sDeviceID}&_app_id=1001&output_format=json&_output_fmt=json&appid=1001&optype=receive_usertask&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 上报任务完成，需要手动额外传入参数：task_type
        self.task_report = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.task.report&appVersion={appVersion}&task_type={task_type}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 许愿道具列表，额外参数：plat, biz
        self.query_wish_goods_list = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.goods.list&appVersion={appVersion}&p_tk={p_tk}&plat={plat}&biz={biz}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&output_format=json&&weexVersion=0.9.4&deviceModel=MIX%202&&wishing=1&view=biz_portal&page=1&ordertype=desc&orderby=dtModifyTime&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 查询许愿列表，额外参数：appUid
        self.query_wish = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.demand.user.demand&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&_app_id=1001&_biz_code=&pn=1&ps=5&appUid={appUid}&sDeviceID={sDeviceID}&appVersion={appVersion}&p_tk={p_tk}&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android&sDjcSign={sDjcSign}"
        # 删除许愿，额外参数：sKeyId
        self.delete_wish = "https://apps.game.qq.com/daoju/djcapp/v5/demand/DemandDelete.php?output_format=jsonp&iAppId=1001&_app_id=1001&p_tk={p_tk}&output_format=json&_output_fmt=json&sKeyId={sKeyId}&sDeviceID={sDeviceID}&appVersion={appVersion}&p_tk={p_tk}&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 许愿 ，需要手动额外传入参数：iActionId, iGoodsId, sBizCode, partition, iZoneId, platid, sZoneDesc, sRoleId, sRoleName, sGetterDream
        self.make_wish = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.demand.create&p_tk={p_tk}&iActionId={iActionId}&iGoodsId={iGoodsId}&sBizCode={sBizCode}&partition={partition}&iZoneId={iZoneId}&platid={platid}&sZoneDesc={sZoneDesc}&sRoleId={sRoleId}&sRoleName={sRoleName}&sGetterDream={sGetterDream}&sDeviceID={sDeviceID}&appVersion={appVersion}&p_tk={p_tk}&sDjcSign={sDjcSign}&iAppId=1001&_app_id=1001&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 查询道聚城绑定的各游戏角色列表，dnf的角色信息和选定手游的角色信息将从这里获取
        self.query_bind_role_list = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.role.bind_list&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&type=1&output_format=json&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 绑定道聚城游戏（仅用作偶尔不能通过app绑定的时候根据这个来绑定）
        self.bind_role = "https://djcapp.game.qq.com/daoju/djcapp/v5/rolebind/BindRole.php?p_tk={p_tk}&type=2&biz=dnf&output_format=jsonp&_={millseconds}&role_info={role_info}"

        # 查询服务器列表，需要手动额外传入参数：bizcode。具体游戏参数可查阅djc_biz_list.json
        self.query_game_server_list = (
            "https://gameact.qq.com/comm-htdocs/js/game_area/utf8verson/{bizcode}_server_select_utf8.js"
        )
        self.query_game_server_list_for_web = (
            "https://gameact.qq.com/comm-htdocs/js/game_area/{bizcode}_server_select.js"
        )

        # 查询手游礼包礼包，需要手动额外传入参数：bizcode
        self.query_game_gift_bags = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.package.list&bizcode={bizcode}&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&output_format=json&optype=get_user_package_list&appid=1001&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&showType=qq&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 查询手游角色列表，需要手动额外传入参数：game(game_info.gameCode)、sAMSTargetAppId(game_info.wxAppid)、area(roleinfo.channelID)、platid(roleinfo.systemID)、partition(areaID)
        self.get_game_role_list = "https://comm.aci.game.qq.com/main?sCloudApiName=ams.gameattr.role&game={game}&sAMSTargetAppId={sAMSTargetAppId}&appVersion={appVersion}&area={area}&platid={platid}&partition={partition}&callback={callback}&p_tk={p_tk}&sDeviceID={sDeviceID}&&sAMSAcctype=pt&&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 一键领取手游礼包，需要手动额外传入参数：bizcode、iruleId、systemID、sPartition(areaID)、channelID、channelKey、roleCode、sRoleName
        self.receive_game_gift = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.package.receive&bizcode={bizcode}&appVersion={appVersion}&iruleId={iruleId}&sPartition={sPartition}&roleCode={roleCode}&sRoleName={sRoleName}&channelID={channelID}&channelKey={channelKey}&systemID={systemID}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&appid=1001&output_format=json&optype=receive_usertask_game&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 兑换道具，需要手动额外传入参数：iGoodsSeqId、rolename、lRoleId、iZone(roleinfo.serviceID)
        self.exchangeItems = "https://apps.game.qq.com/cgi-bin/daoju/v3/hs/i_buy.cgi?&weexVersion=0.9.4&appVersion={appVersion}&iGoodsSeqId={iGoodsSeqId}&iZone={iZone}&lRoleId={lRoleId}&rolename={rolename}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&platform=android&deviceModel=MIX%202&&&_output_fmt=1&_plug_id=9800&_from=app&iActionId=2594&iActionType=26&_biz_code=dnf&biz=dnf&appid=1003&_app_id=1003&_cs=2&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 获取所有可兑换的道具的列表
        self.show_exchange_item_list = "https://app.daoju.qq.com/jd/js/dnf_index_list_dj_info_json.js?&weexVersion=0.9.4&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&platform=android&deviceModel=MIX%202&&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # amesvr通用活动
        # 其对应活动描述文件一般可通过下列链接获取，其中{actId}替换为活动ID，{last_three}替换为活动ID最后三位
        # https://dnf.qq.com/comm-htdocs/js/ams/actDesc/{last_three}/{actId}/act.desc.js
        # https://apps.game.qq.com/comm-htdocs/js/ams/v0.2R02/act/{actId}/act.desc.js
        self.iActivityId_xinyue_battle_ground = "366480"  # DNF地下城与勇士心悦特权专区
        self.iActivityId_xinyue_sailiyam = "339263"  # DNF进击吧赛利亚
        self.iActivityId_wegame_guoqing = "331515"  # wegame国庆活动【秋风送爽关怀常伴】
        self.iActivityId_dnf_1224 = "353266"  # DNF-1224渠道活动合集
        self.iActivityId_dnf_shanguang = "419708"  # DNF闪光杯
        self.iActivityId_dnf_female_mage_awaken = "336524"  # 10月女法师三觉活动
        self.iActivityId_dnf_rank = "347456"  # DNF-2020年KOL榜单建设送黑钻
        self.iActivityId_dnf_carnival = "346329"  # DNF嘉年华页面主页面签到-pc
        self.iActivityId_dnf_carnival_live = "346830"  # DNF嘉年华直播页面-PC
        self.iActivityId_dnf_dianzan = "419223"  # DNF2020共创投票领礼包需求
        self.iActivityId_dnf_welfare = "215651"  # DNF福利中心兑换
        self.iActivityId_dnf_welfare_login_gifts = "407607"  # DNF福利中心-登陆游戏领福利
        self.iActivityId_xinyue_financing = "126962"  # 心悦app理财礼卡
        self.iActivityId_xinyue_cat = "141920"  # 心悦猫咪
        self.iActivityId_xinyue_weekly_gift = "155525"  # 心悦app周礼包
        self.iActivityId_dnf_drift = "348890"  # dnf漂流瓶
        self.iActivityId_majieluo = "425557"  # DNF马杰洛的规划
        self.iActivityId_dnf_helper = "429675"  # DNF助手活动
        self.iActivityId_warm_winter = "347445"  # 暖冬有礼
        self.iActivityId_qq_video_amesvr = "398546"  # qq视频-AME活动
        self.iActivityId_dnf_bbs = "397645"  # DNF论坛积分兑换活动
        self.iActivityId_dnf_bbs_dup = "384854"  # DNF论坛积分兑换活动
        self.iActivityId_dnf_luodiye = "419868"  # DNF落地页活动需求
        self.iActivityId_dnf_wegame = "425699"  # WeGame活动
        self.iActivityId_dnf_wegame_dup = "415808"  # WeGame活动
        self.iActivityId_spring_fudai = "354771"  # 新春福袋大作战
        self.iActivityId_dnf_fuqian = "362403"  # DNF福签大作战
        self.iActivityId_dnf_collection = "408935"  # DNF集合站
        self.iActivityId_dnf_collection_dup = "423011"  # DNF集合站
        self.iActivityId_firecrackers = "355187"  # 燃放爆竹活动
        self.iActivityId_dnf_ozma = "382419"  # DNF奥兹玛竞速
        self.iActivityId_hello_voice = "396564"  # hello语音奖励兑换
        self.iActivityId_dnf_pk = "370758"  # DNF格斗大赛
        self.iActivityId_dnf_xinyue = "422200"  # DNF心悦
        self.iActivityId_dnf_strong = "366330"  # DNF强者之路
        self.iActivityId_dnf_comic = "386057"  # DNF&腾讯动漫周年庆合作活动
        self.iActivityId_dnf_13 = "381033"  # DNF十三周年庆双端站点
        self.iActivityId_dnf_my_story = "382161"  # 我的dnf13周年活动
        self.iActivityId_dnf_reserve = "384604"  # 刃影预约活动
        self.iActivityId_dnf_anniversary = "382072"  # DNF周年庆登录活动
        self.iActivityId_dnf_kol = "416057"  # DNF KOL
        self.iActivityId_maoxian = "407067"  # 勇士的冒险补给
        self.iActivityId_maoxian_dup = "405979"  # 勇士的冒险补给-回归玩家
        self.iActivityId_dnf_gonghui = "421277"  # DNF公会活动
        self.iActivityId_dnf_mingyun_jueze = "405654"  # 命运的抉择挑战赛
        self.iActivityId_dnf_guanhuai = "421327"  # 关怀活动
        self.iActivityId_dnf_relax_road = "407354"  # 轻松之路
        self.iActivityId_dnf_vote = "428587"  # DNF名人堂
        self.iActivityId_dnf_reservation = "425797"  # DNF预约
        self.iActivityId_dnf_memory = "431712"  # DNF记忆
        self.iActivityId_dnf_game = "427765"  # DNF娱乐赛

        # amesvr通用活动系统配置
        # 需要手动额外传入参数：sMiloTag, sServiceDepartment, sServiceType
        self.amesvr = "https://{amesvr_host}/ams/ame/amesvr?ameVersion=0.3&sSDID={sSDID}&sMiloTag={sMiloTag}&sServiceType={sServiceType}&iActivityId={iActivityId}&sServiceDepartment={sServiceDepartment}&isXhrPost=true"
        # &sArea={sArea}&sRoleId={sRoleId}&uin={uin}&userId={userId}&token={token}&sRoleName={sRoleName}&serverId={serverId}&skey={skey}&nickName={nickName}
        # 需要手动额外传入参数：iFlowId/package_id/lqlevel/teamid, sServiceDepartment/sServiceType, sArea/serverId/nickName/sRoleId/sRoleName/uin/skey/userId/token, date
        self.amesvr_raw_data = (
            "iActivityId={iActivityId}&g_tk={g_tk}&iFlowId={iFlowId}&package_id={package_id}&xhrPostKey=xhr_{millseconds}&eas_refer=http%3A%2F%2Fnoreferrer%2F%3Freqid%3D{uuid}%26version%3D23&lqlevel={lqlevel}"
            "&teamid={teamid}&weekDay={weekDay}&e_code=0&g_code=0&eas_url={eas_url}&xhr=1&sServiceDepartment={sServiceDepartment}&sServiceType={sServiceType}&sArea={sArea}&sRoleId={sRoleId}&uin={uin}"
            "&userId={userId}&token={token}&sRoleName={sRoleName}&serverId={serverId}&areaId={areaId}&skey={skey}&nickName={nickName}&date={date}&dzid={dzid}&page={page}&iPackageId={iPackageId}&plat={plat}"
            "&extraStr={extraStr}&sContent={sContent}&sPartition={sPartition}&sAreaName={sAreaName}&md5str={md5str}&ams_checkparam={ams_checkparam}&checkparam={checkparam}&type={type}&moduleId={moduleId}"
            "&giftId={giftId}&acceptId={acceptId}&invitee={invitee}&giftNum={giftNum}&sendQQ={sendQQ}&receiver={receiver}&receiverName={receiverName}&inviterName={inviterName}&user_area={user_area}"
            "&user_partition={user_partition}&user_areaName={user_areaName}&user_roleId={user_roleId}&user_roleName={user_roleName}&user_roleLevel={user_roleLevel}&user_checkparam={user_checkparam}"
            "&user_md5str={user_md5str}&user_sex={user_sex}&user_platId={user_platId}&cz={cz}&dj={dj}&siActivityId={siActivityId}&needADD={needADD}&dateInfo={dateInfo}&sId={sId}&userNum={userNum}"
            "&cardType={cardType}&inviteId={inviteId}&sendName={sendName}&receiveUin={receiveUin}&receiverUrl={receiverUrl}&index={index}&pageNow={pageNow}&pageSize={pageSize}&clickTime={clickTime}"
            "&username={username}&petId={petId}&skin_id={skin_id}&decoration_id={decoration_id}&fuin={fuin}&sCode={sCode}&sNickName={sNickName}&iId={iId}&sendPage={sendPage}&hello_id={hello_id}"
            "&prize={prize}&qd={qd}&iReceiveUin={iReceiveUin}&map1={map1}&map2={map2}&len={len}&itemIndex={itemIndex}&sRole={sRole}&loginNum={loginNum}&level={level}&inviteUin={inviteUin}"
            "&iGuestUin={iGuestUin}&ukey={ukey}&iGiftID={iGiftID}&iInviter={iInviter}&iPageNow={iPageNow}&iPageSize={iPageSize}&iType={iType}&iWork={iWork}&iPage={iPage}&sNick={sNick}"
            "&iMatchId={iMatchId}&iGameId={iGameId}&iIPId={iIPId}&iVoteId={iVoteId}&iResult={iResult}&personAct={personAct}&teamAct={teamAct}"
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
        self.qzone_activity_new = "https://act.qzone.qq.com/v2/vip/tx/trpc/subact/ExecAct"
        self.qzone_activity_new_query = (
            "https://act.qzone.qq.com/v2/vip/tx/proxy/domain/trpc.qzone.qq.com/trpc/subact/QueryAct"
        )
        self.qzone_activity_new_send_card = "https://act.qzone.qq.com/v2/vip/tx/trpc/xcard/GiftItems?g_tk={g_tk}"
        self.qzone_activity_new_query_card = (
            "https://act.qzone.qq.com/v2/vip/tx/trpc/xcard/QueryItems?g_tk={g_tk}&packetID={packetID}"
        )
        # 本地假设的集卡活动id，每次新版的集卡更新时，就增加一下这个（如果继续出旧版的那种集卡活动，则不需要修改这个）
        self.pesudo_ark_lottery_act_id = 10003

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
        # wang.xinyue相关接口，额外参数：api: 具体api名称，userId（助手userId），sPartition/sRoleId, isLock->isLock, amsid->sLbCode, iLbSel1->iLbSel1, 区分自己还是队友的基础奖励, num: 1, mold: 1-自己，2-队友,  exNum->1, iCard->iCard, iNum->iNum
        self.dnf_helper_chronicle_wang_xinyue = "https://wang.xinyue.qq.com/peak/{api}?userId={userId}&gameId=1006&sPartition={sPartition}&sRoleId={sRoleId}&game_code=dnf&token={token}&uin={uin}&uniqueRoleId={uniqueRoleId}&isLock={isLock}&amsid={amsid}&iLbSel1={iLbSel1}&num={num}&mold={mold}&exNum={exNum}&iCard={iCard}&iNum={iNum}&appidTask=1000042"
        # mwegame相关接口，额外参数：api: 具体api名称，userId（助手userId），sPartition/sRoleId, actionId: 自己的任务为任务信息中的各个任务的mActionId，队友的任务对应的是各个任务的pActionId
        self.dnf_helper_chronicle_mwegame = "https://mwegame.qq.com/act/GradeExp/ajax/{api}?userId={userId}&gameId=1006&sPartition={sPartition}&sRoleId={sRoleId}&game_code=dnf&actionId={actionId}&pUserId={pUserId}&isBind={isBind}"

        # 助手活动相关接口
        self.dnf_helper = "https://mwegame.qq.com/act/dnf/destiny/{api}?gameId=10014&roleSwitch=1&toOpenid=&roleId={roleId}&uniqueRoleId={uniqueRoleId}&openid=&serverName={serverName}&toUin={toUin}&cGameId=1006&userId={userId}&serverId={serverId}&token={token}&isMainRole=0&subGameId=10014&areaId={areaId}&gameName=DNF&areaName={areaName}&roleJob={roleJob}&nickname={nickname}&roleName={roleName}&uin={uin}&roleLevel={roleLevel}&"

        # hello语音，额外参数：api，hello_id，type，packid
        self.hello_voice = "https://ulink.game.qq.com/app/1164/c7028bb806cd2d6c/index.php?route=Raward/{api}&iActId=1192&ulenv=&game=dnf&hello_id={hello_id}&type={type}&packid={packid}"

        # dnf论坛签到，额外参数：formhash: 论坛formhash
        self.dnf_bbs_signin = (
            "https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign&operation=qiandao&formhash={formhash}&format=empty"
        )

        # 心悦app
        # 心悦猫咪api
        self.xinyue_cat_api = "https://apps.xinyue.qq.com/maomi/pet_api_info/{api}?skin_id={skin_id}&decoration_id={decoration_id}&uin={uin}&adLevel={adLevel}&adPower={adPower}"

        # colg
        self.colg_url = "https://bbs.colg.cn/forum-171-1.html"
        self.colg_sign_in_url = "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=passUserSign"
        self.colg_take_sign_in_credits = (
            "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=getUserCredit&aid={aid}&task_id={task_id}"
        )

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
        self.wegame_new_appkey = "wegame!#act$2020"

    def show_current_valid_act_infos(self):
        acts = []

        for not_ams_act in not_ams_activities:
            if is_act_expired(not_ams_act.dtEndTime):
                continue

            acts.append(not_ams_act)

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

            acts.append(act)

        acts.sort(key=lambda act: act.dtEndTime)

        heads = ["序号", "活动名称", "活动ID", "开始时间", "结束时间", "剩余时间"]
        colSizes = [4, 44, 8, 20, 20, 14]

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
def search_act(actId):
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

    a_week_seconds = 7 * 24 * 3600

    act_cache_file = with_cache(
        "act_desc",
        actId,
        cache_max_seconds=a_week_seconds,
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


def get_ams_act_desc(actId: str) -> str:
    act = get_ams_act(actId)
    if act is None:
        return ""

    return format_act(act)


def get_ams_act(actId: str) -> Optional[AmsActInfo]:
    act = search_act(actId)
    return act


def get_not_ams_act_desc(act_name: str) -> str:
    act = get_not_ams_act(act_name)
    if act is None:
        return f"未找到活动 {act_name} 的相关信息"

    return format_act(act)


def get_not_ams_act(act_name: str) -> Optional[AmsActInfo]:
    for act in not_ams_activities:
        if act.sActivityName == act_name:
            return act

    return None


def format_act(act: AmsActInfo, needPadding=False):
    act_name = act.sActivityName
    if needPadding:
        act_name = padLeftRight(act.sActivityName, 44, mode="left")

    msg = f"活动 {act_name}({act.iActivityId})"

    if act.dtEndTime != "":
        msg += f" 开始时间为 {act.dtBeginTime}，结束时间为 {act.dtEndTime}，"
        if not is_act_expired(act.dtEndTime):
            msg += f"距离结束还有 {get_remaining_time(act.dtEndTime)}"
        else:
            msg += f"已经结束了 {get_past_time(act.dtEndTime)}"
    else:
        msg += " 尚无已知的开始和结束时间"

    return msg


if __name__ == "__main__":
    urls = Urls()
    urls.show_current_valid_act_infos()
    # print(get_not_ams_act_desc("集卡"))
