from __future__ import annotations

from urls import get_act_url, newNotAmsActInfo, not_know_end_time____, not_know_start_time__

# 将几乎可以确定不再会重新上线的活动代码挪到这里，从而减少 urls.py 的行数


not_ams_activities_tomb = [
    newNotAmsActInfo("2021-09-19 00:00:00", "2021-10-05 23:59:59", "qq会员杯"),
    newNotAmsActInfo("2022-01-20 00:00:00", "2022-02-28 23:59:59", "管家蚊子腿"),
    newNotAmsActInfo("2021-07-04 00:00:00", not_know_end_time____, "会员关怀"),
    newNotAmsActInfo("2021-09-11 00:00:00", "2021-10-13 23:59:59", "虎牙"),
    newNotAmsActInfo("2021-10-18 00:00:00", "2021-11-18 23:59:59", "qq视频蚊子腿"),
    newNotAmsActInfo("2021-12-13 00:00:00", "2021-12-31 23:59:59", "WeGame活动_新版"),
    newNotAmsActInfo("2022-11-24 00:00:00", "2022-12-23 23:59:59", "黄钻"),
    newNotAmsActInfo(not_know_start_time__, not_know_end_time____, "幸运勇士"),
    newNotAmsActInfo("2022-09-22 00:00:00", "2022-10-21 23:59:59", "DNF集合站_ide"),
    newNotAmsActInfo("2022-09-22 00:00:00", "2022-10-21 23:59:59", "我的小屋"),
    newNotAmsActInfo("2022-09-22 00:00:00", "2022-10-19 23:59:59", "超享玩"),
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
    "暖冬好礼活动": "https://dnf.qq.com/lbact/a20200911lbz3dns/index.html",
    "dnf漂流瓶": "https://dnf.qq.com/cp/a20201211driftm/index.html",
    "阿拉德勇士征集令": "https://act.qzone.qq.com/vip/2020/dnf1126",
    "DNF进击吧赛利亚": "https://xinyue.qq.com/act/a20201023sailiya/index.html",
    "2020DNF嘉年华页面主页面签到": "https://dnf.qq.com/cp/a20201203carnival/index.html",
    "dnf助手排行榜": "https://mwegame.qq.com/dnf/rankv2/index.html",
    "10月女法师三觉": "https://mwegame.qq.com/act/dnf/Mageawaken/index?subGameId=10014&gameId=10014&gameId=1006",
    "微信签到": "微信DNF公众号",
    "wegame国庆活动【秋风送爽关怀常伴】": "https://dnf.qq.com/lbact/a20200922wegame/index.html",
    "虎牙": "https://www.huya.com/367967",
    "命运的抉择挑战赛": "https://dnf.qq.com/cp/a20210826fate/index.html",
    "轻松之路": "https://dnf.qq.com/cp/a20210914qszlm/index.html",
    "WeGameDup": "https://dnf.qq.com/lbact/a20211014wg/index.html",
    "qq视频蚊子腿": "https://m.film.qq.com/magic-act/yauhs87ql00t63xttwkas8papl/index_index.html",
    "DNF名人堂": "https://dnf.qq.com/cp/hof20211123/index.html",
    "DNF记忆": "https://dnf.qq.com/cp/a20211203dnfmem/index.html",
    "关怀活动": "https://dnf.qq.com/lbact/a20211118care/index.html",
    "DNF公会活动": "https://dnf.qq.com/cp/a20211028GH/index.html",
    "WeGame活动_新版": "https://act.wegame.com.cn/wand/danji/a20211201DNFCarnival/",
    "新职业预约活动": "https://dnf.qq.com/cp/a20211130reserve/index.html",
    "组队拜年": "https://dnf.qq.com/cp/a20211221BN/index.html",
    "hello语音（皮皮蟹）网页礼包兑换": "https://dnf.qq.com/cp/a20210806dnf/",
    "翻牌活动": "https://dnf.qq.com/cp/a20220420cardflip/index.html",
    "DNF共创投票": "https://dnf.qq.com/cp/a20210914design/list-end.html",
    "DNF互动站": "https://dnf.qq.com/cp/a20220609fete/index.html",
    "心悦猫咪": "https://xinyue.qq.com/act/a20180912tgclubcat/index.html",  # userAgent: tgclub/5.7.11.85(Xiaomi MIX 2;android 9;Scale/440;android;865737030437124)
    "黄钻": "https://act.qzone.qq.com/v2/vip/tx/p/41784_f68ffe5f",
    "KOL": "https://dnf.qq.com/cp/a20220526kol/index.html",
    "幸运勇士": "https://dnf.qq.com/cp/a20191114wastage/index.html",
    "DNF集合站_ide": "https://dnf.qq.com/cp/jinqiu0922jiheye/index.html",
    "我的小屋": "https://dnf.qq.com/act/a20220910farm/index.html?pt=1",
    "超享玩": "https://act.supercore.qq.com/supercore/act/ac2cb66d798da4d71bd33c7a2ec1a7efb/index.html",
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
        self.iActivityId_warm_winter = "347445"  # 暖冬有礼
        self.iActivityId_dnf_drift = "348890"  # dnf漂流瓶
        self.iActivityId_xinyue_sailiyam = "339263"  # DNF进击吧赛利亚
        self.iActivityId_dnf_carnival = "346329"  # DNF嘉年华页面主页面签到-pc
        self.iActivityId_dnf_carnival_live = "346830"  # DNF嘉年华直播页面-PC
        self.iActivityId_dnf_rank = "347456"  # DNF-2020年KOL榜单建设送黑钻
        self.iActivityId_dnf_female_mage_awaken = "336524"  # 10月女法师三觉活动
        self.iActivityId_wegame_guoqing = "331515"  # wegame国庆活动【秋风送爽关怀常伴】
        self.iActivityId_dnf_mingyun_jueze = "405654"  # 命运的抉择挑战赛
        self.iActivityId_dnf_relax_road = "407354"  # 轻松之路
        self.iActivityId_dnf_wegame_dup = "415808"  # WeGame活动
        self.iActivityId_dnf_vote = "428587"  # DNF名人堂
        self.iActivityId_dnf_memory = "431712"  # DNF记忆
        self.iActivityId_dnf_guanhuai = "421327"  # 关怀活动
        self.iActivityId_dnf_gonghui = "421277"  # DNF公会活动
        self.iActivityId_dnf_reserve = "430779"  # 新职业预约活动
        self.iActivityId_team_happy_new_year = "438251"  # 组队拜年
        self.iActivityId_hello_voice = "438826"  # hello语音（皮皮蟹）奖励兑换
        self.iActivityId_dnf_card_flip = "458381"  # 翻牌活动
        self.iActivityId_dnf_dianzan = "472877"  # DNF2020共创投票领礼包需求
        self.iActivityId_dnf_interactive = "469840"  # DNF互动站
        self.iActivityId_xinyue_cat = "141920"  # 心悦猫咪
        self.iActivityId_dnf_kol = "472448"  # DNF KOL


        # ide通用活动
        self.ide_iActivityId_collection = "57_vA2NDv"  # 集合站
        self.ide_iActivityId_dnf_my_home = "83_WFf5TE"  # 我的小屋

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

        # 阿拉德勇士征集令
        self.dnf_warriors_call_page = "https://act.qzone.qq.com/vip/2020/dnf1126"

        # 助手排行榜活动
        # 查询，额外参数：uin(qq)、userId/token
        self.rank_user_info = "https://mwegame.qq.com/dnf/kolTopV2/ajax/getUserInfo?uin={uin}&userId={userId}&token={token}&serverId=0&gameId=10014"
        # 打榜，额外参数：uin(qq)、userId/token、id/score
        self.rank_send_score = "https://mwegame.qq.com/dnf/kolTopV2/ajax/sendScore?uin={uin}&userId={userId}&token={token}&serverId=0&gameId=10014&id={id}&type=single1&score={score}"
        # 领取黑钻，额外参数：uin(qq)、userId/token，gift_id[7020, 7021, 7022]
        self.rank_receive_diamond = "https://mwegame.qq.com/ams/send/handle?uin={uin}&userId={userId}&token={token}&serverId=0&gameId=10014&gift_id={gift_id}"

        # qq视频活动
        self.qq_video = "https://activity.video.qq.com/fcgi-bin/asyn_activity?act_id={act_id}&module_id={module_id}&type={type}&option={option}&ptag=dnf&otype=xjson&_ts={millseconds}&task={task}&is_prepublish={is_prepublish}"

        # WeGame新版活动，需要填写 flow_id
        # md5签名内容
        #   /service/flow/v1/parse/Wand-20211206100115-Fde55ab61e52f?u=7636ee76-dc95-42e2-ac8c-af7f07982dfd&a=10004&ts=1639583575&appkey=wegame!#act$2020
        # 计算md5签名之后
        #   /service/flow/v1/parse/Wand-20211206100115-Fde55ab61e52f?u=7636ee76-dc95-42e2-ac8c-af7f07982dfd&a=10004&ts=1639583575&s=7f2eeec828830f249a7694d09833c50d
        self.wegame_new_host = "https://act.wegame.com.cn"
        self.wegame_new_api = "/service/flow/v1/parse/{flow_id}?u={uuid4}&a=10004&ts={seconds}"
        self.wegame_new_appkey = "--todo--"

        # DNF共创投票
        # 查询作品列表，额外参数：iCategory1、iCategory2、page、pagesize
        self.query_dianzan_contents = "https://apps.game.qq.com/cms/index.php?r={rand}&callback=jQuery191015906433451135138_{millseconds}&serviceType=dnf&sAction=showList&sModel=Ugc&actId=2&iCategory1={iCategory1}&iCategory2={iCategory2}&order=0&page={page}&pagesize={pagesize}&_=1608559950347"
        # 点赞，额外参数：iContentId
        self.dianzan = "https://apps.game.qq.com/cms/index.php?r={rand}&callback=jQuery19105114998760002998_{millseconds}&serviceType=dnf&actId=2&sModel=Zan&sAction=zanContent&iContentId={iContentId}&_={millseconds}"

        # 心悦app
        # 心悦猫咪api
        self.xinyue_cat_api = "https://apps.xinyue.qq.com/maomi/pet_api_info/{api}?skin_id={skin_id}&decoration_id={decoration_id}&uin={uin}&adLevel={adLevel}&adPower={adPower}"

        # 幸运勇士
        self.lucky_user = (
            "https://nloss.native.qq.com/{api}?iAreaId={iAreaId}&iRoleId={iRoleId}"
            "&taskId={taskId}&point={point}"
            "&randomSeed={randomSeed}"
        )

        # 超享玩
        self.super_core_api = "https://agw.xinyue.qq.com/amp2.WPESrv/WPEIndex?flowId={flowId}"
