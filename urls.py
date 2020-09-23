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

        # 查询道聚城绑定的各游戏角色列表，dnf的角色信息和选定手游的角色信息将从这里获取
        self.query_bind_role_list = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.role.bind_list&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&type=1&output_format=json&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 查询服务器列表，需要手动额外传入参数：bizcode。具体游戏参数可查阅djc_biz_list.json
        self.query_game_server_list = "https://gameact.qq.com/comm-htdocs/js/game_area/utf8verson/{bizcode}_server_select_utf8.js"
        self.query_game_server_list_for_web = "https://gameact.qq.com/comm-htdocs/js/game_area/{bizcode}_server_select.js"

        # 查询手游礼包礼包，需要手动额外传入参数：bizcode
        self.query_game_gift_bags = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.package.list&bizcode={bizcode}&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&output_format=json&optype=get_user_package_list&appid=1001&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&showType=qq&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 查询手游角色列表，需要手动额外传入参数：game(game_info.gameCode)、sAMSTargetAppId(game_info.wxAppid)、area(roleinfo.channelID)、platid(roleinfo.systemID)、partition(areaID)
        self.get_game_role_list = "https://comm.aci.game.qq.com/main?sCloudApiName=ams.gameattr.role&game={game}&sAMSTargetAppId={sAMSTargetAppId}&appVersion={appVersion}&area={area}&platid={platid}&partition={partition}&callback={callback}&p_tk={p_tk}&sDeviceID={sDeviceID}&&sAMSAcctype=pt&&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 一键领取手游礼包，需要手动额外传入参数：bizcode、iruleId、systemID、sPartition(areaID)、channelID、channelKey、roleCode、sRoleName
        self.recieve_game_gift = "https://djcapp.game.qq.com/daoju/igw/main/?_service=app.package.receive&bizcode={bizcode}&appVersion={appVersion}&iruleId={iruleId}&sPartition={sPartition}&roleCode={roleCode}&sRoleName={sRoleName}&channelID={channelID}&channelKey={channelKey}&systemID={systemID}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&&weexVersion=0.9.4&platform=android&deviceModel=MIX%202&appid=1001&output_format=json&optype=receive_usertask_game&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 兑换道具，需要手动额外传入参数：iGoodsSeqId、rolename、lRoleId、iZone(roleinfo.serviceID)
        self.exchangeItems = "https://apps.game.qq.com/cgi-bin/daoju/v3/hs/i_buy.cgi?&weexVersion=0.9.4&appVersion={appVersion}&iGoodsSeqId={iGoodsSeqId}&iZone={iZone}&lRoleId={lRoleId}&rolename={rolename}&p_tk={p_tk}&sDeviceID={sDeviceID}&sDjcSign={sDjcSign}&platform=android&deviceModel=MIX%202&&&_output_fmt=1&_plug_id=9800&_from=app&iActionId=2594&iActionType=26&_biz_code=dnf&biz=dnf&appid=1003&_app_id=1003&_cs=2&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"
        # 获取所有可兑换的道具的列表
        self.show_exchange_item_list = "https://app.daoju.qq.com/jd/js/dnf_index_list_dj_info_json.js?&weexVersion=0.9.4&appVersion={appVersion}&p_tk={p_tk}&sDeviceID={sDeviceID}&platform=android&deviceModel=MIX%202&&osVersion=Android-28&ch=10003&sVersionName=v4.1.6.0&appSource=android"

        # 心悦相关接口的入口
        self.xinyue_iActivityId_battle_ground = "166962"  # DNF地下城与勇士心悦特权专区
        self.xinyue_iActivityId_guoqing = "329456"  # 心悦国庆活动
        # 需要手动额外传入参数：sMiloTag
        self.xinyue = "https://act.game.qq.com/ams/ame/amesvr?ameVersion=0.3&sSDID={sSDID}&sMiloTag={sMiloTag}&sServiceType=tgclub&iActivityId={iActivityId}&sServiceDepartment=xinyue&isXhrPost=true"
        # 需要手动额外传入参数：iFlowId/package_id/lqlevel/teamid
        self.xinyue_raw_data = "iActivityId={iActivityId}&g_tk={g_tk}&iFlowId={iFlowId}&package_id={package_id}&xhrPostKey=xhr_{millseconds}&eas_refer=http%3A%2F%2Fnoreferrer%2F%3Freqid%3D{uuid}%26version%3D23&lqlevel={lqlevel}&teamid={teamid}&e_code=0&g_code=0&eas_url=http%3A%2F%2Fxinyue.qq.com%2Fact%2Fa20181101rights%2F&xhr=1&sServiceDepartment=xinyue&sServiceType=tgclub"

        # 每月黑钻等级礼包
        self.heizuan_gift = "https://dnf.game.qq.com/mtask/lottery/?r={rand}&serviceType=dnf&channelId=1&actIdList=44c24e"

        # 信用星级礼包
        self.credit_gift = "https://dnf.game.qq.com/mtask/lottery/?r={rand}&serviceType=dnf&channelId=1&actIdList=13c48b"

        # 腾讯游戏信用，需要手动额外传入参数：gift_group
        self.credit_xinyue_gift = "https://gamecredit.qq.com/api/qq/proxy/credit_xinyue_gift?gift_group={gift_group}"

        # 抽卡相关
        self.ark_lottery_page = "https://act.qzone.qq.com/vip/2019/xcardv3?zz=4&verifyid=qqvipdnf9"
        self.ark_lottery = "https://activity.qzone.qq.com/fcg-bin/{api}?g_tk={g_tk}&r={rand}"
        self.ark_lottery_raw_data = "gameid={gameid}&actid={actid}&ruleid={ruleid}&area={area}&partition={partition}&roleid={roleid}&platform=pc&query={query}&act_name={act_name}&format=json&uin={uin}"
