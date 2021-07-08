import json

import requests

from dao import AmsActInfo
from util import *


def newAmsActInfo(sActivityName, dtBeginTime, dtEndTime):
    info = AmsActInfo()
    info.iActivityId = "000000"
    info.sActivityName = sActivityName
    info.dtBeginTime = dtBeginTime
    info.dtEndTime = dtEndTime

    return info


not_know_start_time = "2000-01-01 00:00:00"
not_know_end_time = "2099-01-01 00:00:00"

month_start_day, month_end_day = start_and_end_date_of_a_month(get_now())

not_ams_activities = [
    newAmsActInfo("道聚城", not_know_start_time, not_know_end_time),
    newAmsActInfo("黑钻礼包", not_know_start_time, not_know_end_time),
    newAmsActInfo("腾讯游戏信用礼包", not_know_start_time, not_know_end_time),
    newAmsActInfo("心悦app", not_know_start_time, not_know_end_time),
    newAmsActInfo("管家蚊子腿", "2021-06-17 00:00:00", "2021-07-17 23:59:59"),
    newAmsActInfo("qq视频蚊子腿", "2021-04-22 00:00:00", "2021-05-21 23:59:59"),
    newAmsActInfo("会员关怀", "2021-03-31 00:00:00", not_know_end_time),
    newAmsActInfo("超级会员", "2021-03-31 00:00:00", "2021-07-17 23:59:59"),
    newAmsActInfo("黄钻", "2021-03-31 00:00:00", "2021-07-17 23:59:59"),
    newAmsActInfo("集卡", "2021-06-03 00:00:00", "2021-07-10 23:59:59"),
    newAmsActInfo("DNF助手编年史", format_time(month_start_day), format_time(month_end_day)),
    newAmsActInfo("colg每日签到", "2021-06-18 00:00:00", "2021-07-21 23:59:59"),
]


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
        self.query_game_server_list = "https://gameact.qq.com/comm-htdocs/js/game_area/utf8verson/{bizcode}_server_select_utf8.js"
        self.query_game_server_list_for_web = "https://gameact.qq.com/comm-htdocs/js/game_area/{bizcode}_server_select.js"

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
        self.iActivityId_dnf_shanguang = "348607"  # DNF闪光杯第三期
        self.iActivityId_dnf_female_mage_awaken = "336524"  # 10月女法师三觉活动
        self.iActivityId_dnf_rank = "347456"  # DNF-2020年KOL榜单建设送黑钻
        self.iActivityId_dnf_carnival = "346329"  # DNF嘉年华页面主页面签到-pc
        self.iActivityId_dnf_carnival_live = "346830"  # DNF嘉年华直播页面-PC
        self.iActivityId_dnf_dianzan = "348845"  # DNF2020共创投票领礼包需求
        self.iActivityId_dnf_welfare = "215651"  # DNF福利中心兑换
        self.iActivityId_dnf_welfare_login_gifts = "385055"  # DNF福利中心-登陆游戏领福利
        self.iActivityId_xinyue_financing = "126962"  # 心悦app理财礼卡
        self.iActivityId_xinyue_cat = "141920"  # 心悦猫咪
        self.iActivityId_xinyue_weekly_gift = "155525"  # 心悦app周礼包
        self.iActivityId_dnf_drift = "348890"  # dnf漂流瓶
        self.iActivityId_majieluo = "380963"  # DNF马杰洛的规划
        self.iActivityId_dnf_helper = "370589"  # DNF助手活动
        self.iActivityId_warm_winter = "347445"  # 暖冬有礼
        self.iActivityId_qq_video_amesvr = "379977"  # qq视频-AME活动
        self.iActivityId_dnf_bbs = "374698"  # DNF论坛积分兑换活动
        self.iActivityId_dnf_bbs_dup = "384854"  # DNF论坛积分兑换活动
        self.iActivityId_dnf_luodiye = "382067"  # DNF落地页活动需求
        self.iActivityId_dnf_wegame = "382711"  # WeGame活动
        self.iActivityId_dnf_wegame_dup = "384137"  # WeGame活动
        self.iActivityId_spring_fudai = "354771"  # 新春福袋大作战
        self.iActivityId_dnf_fuqian = "362403"  # DNF福签大作战
        self.iActivityId_dnf_collection = "382255"  # DNF集合站
        self.iActivityId_dnf_collection_dup = "385269"  # DNF集合站
        self.iActivityId_firecrackers = "355187"  # 燃放爆竹活动
        self.iActivityId_dnf_ozma = "382419"  # DNF奥兹玛竞速
        self.iActivityId_hello_voice = "366492"  # hello语音奖励兑换
        self.iActivityId_dnf_pk = "370758"  # DNF格斗大赛
        self.iActivityId_dnf_xinyue_51 = "373457"  # DNF心悦51
        self.iActivityId_dnf_strong = "366330"  # DNF强者之路
        self.iActivityId_dnf_comic = "386057"  # DNF&腾讯动漫周年庆合作活动
        self.iActivityId_dnf_13 = "381033"  # DNF十三周年庆双端站点
        self.iActivityId_dnf_my_story = "382161"  # 我的dnf13周年活动
        self.iActivityId_dnf_reserve = "384604"  # 刃影预约活动
        self.iActivityId_dnf_anniversary = "382072"  # DNF周年庆登录活动
        self.iActivityId_dnf_kol = "387039"  # DNF KOL

        # amesvr通用活动系统配置
        # 需要手动额外传入参数：sMiloTag, sServiceDepartment, sServiceType
        self.amesvr = "https://{amesvr_host}/ams/ame/amesvr?ameVersion=0.3&sSDID={sSDID}&sMiloTag={sMiloTag}&sServiceType={sServiceType}&iActivityId={iActivityId}&sServiceDepartment={sServiceDepartment}&isXhrPost=true"
        # &sArea={sArea}&sRoleId={sRoleId}&uin={uin}&userId={userId}&token={token}&sRoleName={sRoleName}&serverId={serverId}&skey={skey}&nickName={nickName}
        # 需要手动额外传入参数：iFlowId/package_id/lqlevel/teamid, sServiceDepartment/sServiceType, sArea/serverId/nickName/sRoleId/sRoleName/uin/skey/userId/token, date
        self.amesvr_raw_data = "iActivityId={iActivityId}&g_tk={g_tk}&iFlowId={iFlowId}&package_id={package_id}&xhrPostKey=xhr_{millseconds}&eas_refer=http%3A%2F%2Fnoreferrer%2F%3Freqid%3D{uuid}%26version%3D23&lqlevel={lqlevel}&teamid={teamid}&weekDay={weekDay}&e_code=0&g_code=0&eas_url={eas_url}&xhr=1&sServiceDepartment={sServiceDepartment}&sServiceType={sServiceType}&sArea={sArea}&sRoleId={sRoleId}&uin={uin}&userId={userId}&token={token}&sRoleName={sRoleName}&serverId={serverId}&areaId={areaId}&skey={skey}&nickName={nickName}&date={date}&dzid={dzid}&page={page}&iPackageId={iPackageId}&plat={plat}&extraStr={extraStr}&sContent={sContent}&sPartition={sPartition}&sAreaName={sAreaName}&md5str={md5str}&ams_checkparam={ams_checkparam}&checkparam={checkparam}&type={type}&moduleId={moduleId}&giftId={giftId}&acceptId={acceptId}&invitee={invitee}&giftNum={giftNum}&sendQQ={sendQQ}&receiver={receiver}&receiverName={receiverName}&inviterName={inviterName}&user_area={user_area}&user_partition={user_partition}&user_areaName={user_areaName}&user_roleId={user_roleId}&user_roleName={user_roleName}&user_roleLevel={user_roleLevel}&user_checkparam={user_checkparam}&user_md5str={user_md5str}&user_sex={user_sex}&user_platId={user_platId}&cz={cz}&dj={dj}&siActivityId={siActivityId}&needADD={needADD}&dateInfo={dateInfo}&sId={sId}&userNum={userNum}&cardType={cardType}&inviteId={inviteId}&sendName={sendName}&receiveUin={receiveUin}&receiverUrl={receiverUrl}&index={index}&pageNow={pageNow}&pageSize={pageSize}&clickTime={clickTime}&username={username}&petId={petId}&skin_id={skin_id}&decoration_id={decoration_id}&fuin={fuin}&sCode={sCode}&sNickName={sNickName}&iId={iId}&sendPage={sendPage}&hello_id={hello_id}&prize={prize}&qd={qd}&iReceiveUin={iReceiveUin}&map1={map1}&map2={map2}&len={len}&itemIndex={itemIndex}&sRole={sRole}&loginNum={loginNum}"

        # DNF共创投票
        # 查询作品列表，额外参数：iCategory1、iCategory2、page、pagesize
        self.query_dianzan_contents = "https://apps.game.qq.com/cms/index.php?r={rand}&callback=jQuery191015906433451135138_{millseconds}&serviceType=dnf&sAction=showList&sModel=Ugc&actId=2&iCategory1={iCategory1}&iCategory2={iCategory2}&order=0&page={page}&pagesize={pagesize}&_=1608559950347"
        # 点赞，额外参数：iContentId
        self.dianzan = "https://apps.game.qq.com/cms/index.php?r={rand}&callback=jQuery19105114998760002998_{millseconds}&serviceType=dnf&actId=2&sModel=Zan&sAction=zanContent&iContentId={iContentId}&_={millseconds}"

        # 每月黑钻等级礼包
        self.heizuan_gift = "https://dnf.game.qq.com/mtask/lottery/?r={rand}&serviceType=dnf&channelId=1&actIdList=44c24e"

        # 信用星级礼包
        self.credit_gift = "https://dnf.game.qq.com/mtask/lottery/?r={rand}&serviceType=dnf&channelId=1&actIdList=13c48b"

        # 腾讯游戏信用，需要手动额外传入参数：gift_group
        self.credit_xinyue_gift = "https://gamecredit.qq.com/api/qq/proxy/credit_xinyue_gift?gift_group={gift_group}"

        # --QQ空间相关活动--
        self.qzone_activity = "https://activity.qzone.qq.com/fcg-bin/{api}?g_tk={g_tk}&r={rand}"
        self.qzone_activity_raw_data = "gameid={gameid}&actid={actid}&ruleid={ruleid}&area={area}&partition={partition}&roleid={roleid}&platform=pc&query={query}&act_name={act_name}&format=json&uin={uin}&countid={countid}"

        # 新的qq空间接口
        self.qzone_activity_new = "https://act.qzone.qq.com/v2/vip/tx/trpc/subact/ExecAct"

        # 抽卡相关
        self.ark_lottery_page = "https://act.qzone.qq.com/vip/2019/xcardv3?zz=8&verifyid=qq2021dnf13"
        # 查询次数信息：参数：to_qq, actName
        self.ark_lottery_query_left_times = 'https://proxy.vac.qq.com/cgi-bin/srfentry.fcgi?data={{"13320":{{"uin":{to_qq},"actName":"{actName}"}}}}&t={rand}&g_tk={g_tk}'
        # 赠送卡片：参数：cardId，from_qq，to_qq, actName
        self.ark_lottery_send_card = 'https://proxy.vac.qq.com/cgi-bin/srfentry.fcgi?data={{"13333":{{"cardId":{cardId},"fromUin":{from_qq},"toUin":{to_qq},"actName":"{actName}"}}}}&t={rand}&g_tk={g_tk}'

        # 阿拉德勇士征集令
        self.dnf_warriors_call_page = "https://act.qzone.qq.com/vip/2020/dnf1126"

        # qq视频活动
        self.qq_video = "https://activity.video.qq.com/fcgi-bin/asyn_activity?act_id={act_id}&module_id={module_id}&type={type}&option={option}&ptag=dnf&otype=xjson&_ts={millseconds}&task={task}&is_prepublish={is_prepublish}"

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
        self.dnf_helper_chronicle_mwegame = "https://mwegame.qq.com/act/GradeExp/ajax/{api}?userId={userId}&gameId=1006&sPartition={sPartition}&sRoleId={sRoleId}&game_code=dnf&actionId={actionId}"

        # hello语音，额外参数：api，hello_id，type，packid
        self.hello_voice = "https://ulink.game.qq.com/app/1164/c7028bb806cd2d6c/index.php?route=Raward/{api}&iActId=1192&ulenv=&game=dnf&hello_id={hello_id}&type={type}&packid={packid}"

        # dnf论坛签到，额外参数：formhash: 论坛formhash
        self.dnf_bbs_signin = "https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign&operation=qiandao&formhash={formhash}&format=empty"

        # 心悦app
        # 心悦猫咪api
        self.xinyue_cat_api = "https://apps.xinyue.qq.com/maomi/pet_api_info/{api}?skin_id={skin_id}&decoration_id={decoration_id}&uin={uin}&adLevel={adLevel}&adPower={adPower}"

        # colg
        self.colg_url = "https://bbs.colg.cn/forum-171-1.html"
        self.colg_sign_in_url = "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=passUserSign"
        self.colg_take_sign_in_credits = "https://bbs.colg.cn/plugin.php?id=colg_pass_activity&act=getUserCredit&aid={aid}&task_id={task_id}"

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

        act_infos = [f"{idx + 1:2d} {format_act(act, needPadding=True)}" for idx, act in enumerate(acts)]
        logger.info(color("bold_green") + '\n' + '\n'.join(act_infos))


@try_except()
def search_act(actId):
    actId = str(actId)
    act_desc_js = get_act_desc_js(actId)
    if act_desc_js == "":
        return None

    v = act_desc_js.strip().replace('\r', '\n').split('\n')

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

    act_cache_file = with_cache("act_desc", actId, cache_max_seconds=a_week_seconds, cache_miss_func=lambda: download_act_desc_js(actId))

    if not os.path.exists(act_cache_file):
        return ""

    with open(act_cache_file, 'r', encoding="utf-8") as f:
        return f.read()


def download_act_desc_js(actId: str) -> str:
    last_three = str(actId[-3:])
    act_cache_dir = f"{cached_dir}/actDesc/{last_three}/{actId}"
    act_cache_file = f"{act_cache_dir}/act.desc.js"

    # 然后从服务器获取活动信息
    actUrls = [
        f'https://dnf.qq.com/comm-htdocs/js/ams/actDesc/{last_three}/{actId}/act.desc.js',
        f'https://apps.game.qq.com/comm-htdocs/js/ams/actDesc/{last_three}/{actId}/act.desc.js',
        f'https://apps.game.qq.com/comm-htdocs/js/ams/v0.2R02/act/{actId}/act.desc.js',
    ]
    for url in actUrls:
        res = requests.get(url, timeout=1)
        if res.status_code != 200:
            continue

        make_sure_dir_exists(act_cache_dir)
        with open(act_cache_file, 'w', encoding="utf-8") as f:
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
        act_name = padLeftRight(act.sActivityName, 44, mode='left')

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


if __name__ == '__main__':
    urls = Urls()
    urls.show_current_valid_act_infos()
    # print(get_not_ams_act_desc("集卡"))
