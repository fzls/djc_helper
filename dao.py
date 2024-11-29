from __future__ import annotations

from datetime import datetime, timedelta

from data_struct import ConfigInterface, to_raw_type


class DaoObject:
    def __repr__(self):
        return str(self.__dict__)


class GameInfo(DaoObject):
    def __init__(self, data: dict):
        self.bizName = data["bizName"]
        self.bizCode = data["bizCode"]
        self.gameCode = data["gameCode"]
        self.wxAppid = data["wxAppid"]
        self.type = data["type"]

    def is_mobile_game(self):
        return self.type == "1"


class GameRoleInfo(ConfigInterface):
    def __init__(self):
        self.sBizCode = "jx3"
        self.sOpenId = ""
        self.sRoleInfo = RoleInfo()
        self.dtUpdateTime = "2020-08-23 06:38:04"

    def is_mobile_game(self):
        return self.sRoleInfo.type == "1"


class RoleInfo(ConfigInterface):
    def __init__(self):
        # 端游
        # dnf
        self.roleCode = "71672841"
        self.roleName = "风之凌殇呀"
        self.systemKey = ""
        self.systemID = "1"
        self.serviceID = "11"
        self.serviceName = "浙江一区"
        self.channelName = ""
        self.channelID = ""
        self.channelKey = ""
        self.areaName = "浙江"
        self.areaID = "30"
        self.gameName = "地下城与勇士"
        self.bizCode = "dnf"
        self.showAreaName = ""
        self.accountId = "71672841"
        self.type = "0"
        self.isHasService = "1"

        # 命运方舟
        # self.roleCode = "5000000000004678510"
        # self.roleName = "风之凌殇"
        # self.systemKey = "pc"
        # self.systemID = "2"
        # self.serviceID = ""
        # self.serviceName = "卢佩恩"
        # self.channelName = "卢佩恩"
        # self.channelID = "50"
        # self.channelKey = ""
        # self.areaName = "卡丹"
        # self.areaID = "4"
        # self.gameName = "命运方舟"
        # self.bizCode = "fz"
        # self.showAreaName = "卡丹"
        # self.type = 0
        # self.isHasService = 0
        self.version = 3
        self.area = "50"
        self.platid = "2"
        self.partition = "4"

        # 手游
        # self.roleCode = "2814890504594928763"
        # self.roleName = "风之凌殇"
        # self.systemKey = "android"
        # self.systemID = "1"
        # self.serviceID = "20001"
        # self.serviceName = "梦江南"
        # self.channelName = "手Q"
        # self.channelID = "2"
        # self.channelKey = "qq"
        # self.areaName = "梦江南"
        # self.areaID = "20001"
        # self.gameName = "剑网3:指尖江湖"
        # self.bizCode = "jx3"
        # self.showAreaName = ""
        # self.accountId = "2814890504594928763"
        # self.type = "1"
        # self.isHasService = "0"

    def clone(self) -> RoleInfo:
        return RoleInfo().auto_update_config(to_raw_type(self))


class TemporaryChangeBindRoleInfo(ConfigInterface):
    def __init__(self):
        self.roleCode = "71672841"
        self.serviceID = "11"


class GoodsInfo(ConfigInterface):
    def __init__(self):
        self.type = "3"
        self.actId = "3"
        self.propId = "24074"
        self.propName = "曜-云鹰飞将"
        self.busId = "yxzj"
        self.propDesc = ""
        self.propImg = "http://ossweb-img.qq.com/images/daoju/app/yxzj/rectangle/13-52202-0-r684.jpg?_t=1596187484"
        self.propImg2 = ""
        self.propVideoId = ""
        self.propCoverId = ""
        self.limitPerOrder = "1"
        self.totalLimit = "0"
        self.recommend = "80"
        self.valiDate: list[GoodsValiDateInfo] = []
        self.heroSkin = []
        self.related = False
        self.category = GoodsCategoryInfo()
        self.isCombinPkg = 0
        self.IsOwn = 0

    def fields_to_fill(self):
        return [
            ("valiDate", GoodsValiDateInfo),
        ]


class GoodsValiDateInfo(ConfigInterface):
    def __init__(self):
        self.day = "永久"
        self.name = "曜-云鹰飞将"
        self.pic = "http://ossweb-img.qq.com/images/daoju/app/yxzj/rectangle/13-52202-0-r684.jpg?_t=1596187484"
        self.picMid = None
        self.code = "24074"
        self.gameCode = "52202"
        self.sendType = 13
        self.oldPrice = "16880"
        self.curPrice = "16880"
        self.iGoldPrice = "0"
        self.iDqPrice = "16880"
        self.rushBegin = "0000-00-00 00:00:00"
        self.rushEnd = "0000-00-00 00:00:00"
        self.isMobile = 0
        self.waterMark = 0
        self.label = ""
        self.rushPrice = 0
        self.gold_price_rush = 0
        self.dq_price_rush = 0
        self.twin_price = 0
        self.twin_dq_price = 0
        self.twin_code = ""
        self.isskin = 0
        self.left = "0"
        self.bought = "0"
        self.todayBought = 0
        self.award: dict[str, list] = {"list": []}
        self.isFunc = 0
        self.beanCut = 0
        self.maxBeanCutPrice = 0
        self.maxBeanCutNum = 0
        self.beanRush = 0
        self.beanBegin = "0000-00-00 00:00:00"
        self.beanEnd = "0000-00-00 00:00:00"
        self.acctPlat = "0"
        self.supportPresent = "1"
        self.supportCart = "1"
        self.pinPrice = 0
        self.pinDqPrice = 0
        self.pinBegin = "0000-00-00 00:00:00"
        self.pinEnd = "0000-00-00 00:00:00"


class GoodsCategoryInfo(ConfigInterface):
    def __init__(self):
        self.mainCategory = "170"
        self.subCategory = "0"


class DnfRoleInfoList(ConfigInterface):
    def __init__(self):
        self.role_list: list[DnfRoleInfo] = []

    def fields_to_fill(self):
        return [
            ("role_list", DnfRoleInfo),
        ]


class DnfRoleInfo(ConfigInterface):
    def __init__(self):
        self.roleid = "0"
        self.rolename = "风之凌殇"
        # 已知：0-男鬼剑，3-女魔法师，13-男枪士，14-女圣职者
        self.forceid = 0
        self.level = 110

    def update_params(self, roleid: str, rolename: str, forceid: str, level: str):
        self.roleid = str(roleid)
        self.rolename = str(rolename)
        self.forceid = int(forceid)
        self.level = int(level)

    def get_force_name(self) -> str:
        force_id_to_name = {
            0: "鬼剑士（男）",
            1: "格斗家（女）",
            2: "神枪手（男）",
            3: "魔法师（女）",
            4: "圣职者（男）",
            5: "神枪手（女）",
            6: "暗夜使者",
            7: "格斗家（男）",
            8: "魔法师（男）",
            9: "黑暗武士",
            10: "缔造者",
            11: "鬼剑士（女）",
            12: "守护者",
            13: "魔枪士",
            14: "圣职者（女）",
            15: "枪剑士",
        }
        if self.forceid not in force_id_to_name:
            return str(self.forceid)

        return force_id_to_name[self.forceid]


class MobileGameRoleInfo(DaoObject):
    def __init__(self, roleid, rolename):
        self.roleid = roleid
        self.rolename = rolename


class MobileGameGiftInfo(DaoObject):
    def __init__(self, sTask, iRuleId):
        self.sTask = sTask
        self.iRuleId = iRuleId


class UpdateInfo(DaoObject):
    def __init__(self):
        self.latest_version = ""
        self.netdisk_link = ""
        self.netdisk_passcode = ""
        self.update_message = ""


XIN_YUE_MIN_LEVEL = 3


class XinYueInfo(DaoObject):
    SPECIAL_MEMBER_LEVEL = 10

    level_to_name = {
        1: "游戏家",
        2: "游戏家PRO",
        3: "心悦VIP1",
        4: "心悦VIP2",
        5: "心悦VIP3",
        6: "心悦VIP4",
        7: "心悦VIP5",
        SPECIAL_MEMBER_LEVEL: "特邀会员",
    }

    def __init__(self):
        # 等级含义见上述描述
        self.xytype = 1
        self.xytype_str = "获取失败"
        # 特邀会员
        self.is_special_member = False
        # 勇士币
        self.ysb = 0
        # 成就点
        self.score = 0
        # 抽奖券
        self.ticket = 0
        # 用户名
        self.username = ""
        # 头像框地址
        self.usericon = ""
        # 登录QQ
        self.login_qq = ""

        # ------------- 赛利亚打工相关信息 -------------
        # 工作状态(-2:摸鱼状态，1:可以领取工资, 2: 打工人搬砖中)
        self.work_status = -2
        # 工作结束时间(unix时间戳，0时表示摸鱼状态)
        self.work_end_time = 0
        # 领取奖励结束时间
        self.take_award_end_time = 0

    def work_info(self) -> str:
        if self.work_status == -2:
            return "摸鱼中"
        elif self.work_status == 1:
            return "坐等领工资"
        else:
            return "打工仔搬砖中"

    def is_xinyue_or_special_member(self) -> bool:
        return self.xytype >= XIN_YUE_MIN_LEVEL or self.is_special_member

    def is_xinyue_level(self, *levels: int) -> bool:
        for level in levels:
            if self.xytype == XIN_YUE_MIN_LEVEL + level - 1:
                return True

        return False


class XinYueItemInfo(DaoObject):
    def __init__(
        self,
        total_obtain_two_score,
        used_two_score,
        total_obtain_free_do,
        used_free_do,
        total_obtain_refresh,
        used_refresh,
    ):
        # 免做卡
        self.免做卡 = int(total_obtain_free_do) - int(used_free_do)
        # 双倍卡
        self.双倍卡 = int(total_obtain_two_score) - int(used_two_score)
        # 免做卡
        self.刷新卡 = int(total_obtain_refresh) - int(used_refresh)

        # 总计获得的双倍卡
        self.total_obtain_two_score = total_obtain_two_score
        # 已使用的双倍卡
        self.used_two_score = used_two_score

        # 总计获得的免做卡
        self.total_obtain_free_do = total_obtain_free_do
        # 已使用的免做卡
        self.used_free_do = used_free_do

        # 总计获得的刷新卡
        self.total_obtain_refresh = total_obtain_refresh
        # 已使用的刷新卡
        self.used_refresh = used_refresh


class XinYueMyTeamInfo(ConfigInterface):
    def __init__(self):
        self.ret = 0
        self.num = 0
        self.list: list[XinYueTeamMember] = []
        self.teamAllOpenId = ""  # "1054073896,qq_2"

        # self.result = 0
        # self.id = "" # note:新版的这个id需要通过查询 131104（自己队伍ID） 来获取
        # self.award_summary = "大大小|小中大"
        # self.members: list[XinYueTeamMember] = []

    def fields_to_fill(self):
        return [
            ("list", XinYueTeamMember),
        ]

    def is_team_full(self) -> bool:
        return self.num == 2


class XinYueTeamMember(ConfigInterface):
    def __init__(self):
        self.activityId = "15488"
        self.teamId = 166396
        self.isCaptain = 1
        self.avatar = "http://thirdqq.qlogo.cn/ek_qqapp/AQWLTKahHNrg5aEvmT7Y1ySCaia3aCJmJjicmcib1xYGR85uY9jTCAeNiaIHhHCAPYtApfXdoBMQ/40"
        self.nickName = "%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87"
        self.uid = "1054073896"
        self.role = {
            "area_id": 11,
            "partition_id": 11,
            "role_id": "71672841",
            "role_name": "",
            "plat_id": 2,
            "game_openid": "1054073896",
            "g_openid": "",
            "game_appid": "",
            "device": "pc",
        }

        # self.headurl = "http://thirdqq.qlogo.cn/g?b=oidb&k=KJKNiasFOwe0EGjTyHI7CLg&s=640&t=1556481203"
        # self.nickname = "%E6%9C%88%E4%B9%8B%E7%8E%84%E6%AE%87"
        # self.qq = ""
        # self.captain = 0
        # self.pak = ""
        # self.code = ""


class XinYueSummaryTeamInfo(ConfigInterface):
    def __init__(self):
        self.teamCode = "DNF_TEAM_NOT_FOUND"
        self.teamName = "%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87"
        self.teamLimit = 2
        self.teamMemberNum = 2


class SailiyamWorkInfo(ConfigInterface):
    def __init__(self):
        self.startTime = 0
        self.endTime = 0
        self.endLQtime = 0
        self.iPackageId = "2168441"
        self.status = 0
        self.nowtime = 0


class AmesvrCommonModRet(ConfigInterface):
    def __init__(self):
        self.iRet = "0"
        self.sMsg = "SUC"
        self.sOutValue1 = ""
        self.sOutValue2 = ""
        self.sOutValue3 = ""
        self.sOutValue4 = ""
        self.sOutValue5 = ""
        self.sOutValue6 = ""
        self.sOutValue7 = ""
        self.sOutValue8 = ""


def parse_amesvr_common_info(res) -> AmesvrCommonModRet:
    return AmesvrCommonModRet().auto_update_config(res["modRet"])


class AmesvrUserBindInfo(ConfigInterface):
    def __init__(self):
        self.Fid = "7179"
        self.Fuin = "1054073896"
        self.FnickName = ""
        self.FplatId = ""
        self.Ffarea = "0"
        self.Farea = "11"
        self.FareaName = "%E6%B5%99%E6%B1%9F%E4%B8%80%E5%8C%BA"
        self.FPartition = "11"
        self.Fsex = "11"
        self.FroleId = "71672841"
        self.FroleName = "%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%91%80"
        self.FroleLevel = "100"
        self.Fcheckparam = (
            "dnf|yes|1054073896|11|45168567*45230145*45481100*62889873*64327847*64327855*64333408*64333413*64349521*64349525*64370730*64370732*64632622*64632641*69837948*69837951*71672841*||||%E9%A3%8E%E4%B9%8B%E5%87%8C%E6"
            "%AE%87*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%96%B5*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%93%87*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87Meow*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%B8%80%E5%8F%B7*%E5%8D%A2%E5%8"
            "5%8B%E5%A5%B6%E5%A6%88%E4%BA%8C%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%B8%89%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E5%9B%9B%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%BA%94%E5%8F%B7*%E5"
            "%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E5%85%AD%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%B8%83%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E5%85%AB%E5%8F%B7*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%96%B5%E"
            "5%96%B5*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%96%B5%E5%91%9C*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%B9%9D%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E5%8D%81%E5%8F%B7*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87"
            "%E5%91%80*|0*3*13*14*14*14*14*14*14*14*14*14*3*3*14*14*11*||1600743086|"
        )
        self.Fmd5str = "FDAF0B1B1E51111CCC0AAD240317E96F"
        self.Fdate = "2020-09-22 10:51:29"
        self.FupdateDate = "2020-09-22 10:51:29"
        self.sAmsNewRoleId = ""
        self.sAmsSerial = "AMS-DNF-0922105129-ng2JeR-215651-558226"


class AmesvrQueryRole(ConfigInterface):
    def __init__(self):
        self.version = "V1.0.20201105.20201105101730"
        self.retCode = "0"
        self.serial_num = "AMS-DNF-1220171837-4zFGHv-348623-5381"
        self.data = (
            "_idip_req_id_=&_webplat_msg=21|45168567 风之凌殇 0 100|45230145 风之凌殇喵 3 100|45481100 风之凌殇哇 13 100|62889873 风之凌殇Meow 14 100|64327847 卢克奶妈一号 14 100|64327855 卢克奶妈二号 14 100|64333408 卢克奶妈三号 14 100"
            "|64333413 卢克奶妈四号 14 100|64349521 卢克奶妈五号 14 100|64349525 卢克奶妈六号 14 100|64370730 卢克奶妈七号 14 100|64370732 卢克奶妈八号 14 100|64632622 风之凌殇喵喵 3 100|64632641 风之凌殇喵呜 3 100|69837948 卢克奶妈九号 1"
            "4 100|69837951 卢克奶妈十号 14 100|71672841 风之凌殇呀 11 100|72282733 风之凌殇哦 4 100|72522431 风之凌殇咯 3 100|72574316 风之凌殇咩 3 100|72767454 风之凌殇嘿 3 100|&_webplat_msg_code=0&area=11&msg=21|45168567 风之凌殇 0 "
            "100|45230145 风之凌殇喵 3 100|45481100 风之凌殇哇 13 100|62889873 风之凌殇Meow 14 100|64327847 卢克奶妈一号 14 100|64327855 卢克奶妈二号 14 100|64333408 卢克奶妈三号 14 100|64333413 卢克奶妈四号 14 100|64349521 卢克奶妈五号 "
            "14 100|64349525 卢克奶妈六号 14 100|64370730 卢克奶妈七号 14 100|64370732 卢克奶妈八号 14 100|64632622 风之凌殇喵喵 3 100|64632641 风之凌殇喵呜 3 100|69837948 卢克奶妈九号 14 100|69837951 卢克奶妈十号 14 100|71672841 风之凌殇"
            "呀 11 100|72282733 风之凌殇哦 4 100|72522431 风之凌殇咯 3 100|72574316 风之凌殇咩 3 100|72767454 风之凌殇嘿 3 100|&result=0&uin=1054073896&"
        )
        self.msg = "success"
        self.checkparam = (
            "dnf|yes|1054073896|11|45168567*45230145*45481100*62889873*64327847*64327855*64333408*64333413*64349521*64349525*64370730*64370732*64632622*64632641*69837948*69837951*71672841*72282733*72522431*72574316*72767454"
            "*||||风之凌殇*风之凌殇喵*风之凌殇哇*风之凌殇Meow*卢克奶妈一号*卢克奶妈二号*卢克奶妈三号*卢克奶妈四号*卢克奶妈五号*卢克奶妈六号*卢克奶妈七号*卢克奶妈八号*风之凌殇喵喵*风之凌殇喵呜*卢克奶妈九号*卢克奶妈十号*风之凌殇呀*风之凌殇哦*风之"
            "凌殇咯*风之凌殇咩*风之凌殇嘿*|0*3*13*14*14*14*14*14*14*14*14*14*3*3*14*14*11*4*3*3*3*||1608455917|"
        )
        self.md5str = "3F7F5D5C92CF3E633A40E246A637CC0B"
        self.infostr = ""
        self.checkstr = ""


class RankUserInfo(ConfigInterface):
    def __init__(self):
        self.score = "10"
        self.sendScore = 0
        self.giftStatus = {}
        self.canGift = 0


class DnfWarriorsCallInfo(ConfigInterface):
    def __init__(self):
        self.page = "index"
        self.userInfo = DnfWarriorsCallUserInfo()
        self.zz = DnfWarriorsCallZZ()
        self.boss = DnfWarriorsCallBoss()
        self.isQQ = False
        self.isIOS = False
        self.isMobile = False


class DnfWarriorsCallUserInfo(ConfigInterface):
    def __init__(self):
        self.nick = "小号一号"
        self.avatar = "//qlogo3.store.qq.com/qzone/3036079506/3036079506/100"
        self.deluxe = 0
        self.level = 0
        self.now = 1606814238
        self.star_level = 0
        self.star_vip = 0
        self.uin = 3036079506
        self.vip = 0
        self.year = 0


class DnfWarriorsCallZZ(ConfigInterface):
    def __init__(self):
        self.title = "QQ会员阿拉德勇士征集令"
        self.desc = "阿拉德勇士征集令，瓜分大额Q币、现金大奖！"
        self.shareImage = "https://sola.gtimg.cn/aoi/sola/20200527195101_54WJymQ7wi.jpg"
        self.arkImage = ""
        self.time = "第一期时间：2020年11月30日——12月26日"
        self.tvImage = "http://qzonestyle.gtimg.cn/qzone/qzactStatics/imgs/20201201115645_06f20b.jpg"
        self.tvUrl = "https://dnf.qq.com/cp/a20201125dnf/index.html"
        self.txVideoId = "u3206474sp4"
        self.QRCode = "http://qzonestyle.gtimg.cn/qzone/qzactStatics/imgs/20201130213733_7bfd35.png"
        self.h5 = {}
        self.zZConfigerUpdateTime = 1606805575
        self.actid = 4117
        self.noRuleQuals = []
        self.gameid = "dnf"
        self.report = "act4071"
        self.aid = "act4071"
        self.gameActName = "dnf_huoyue_30s_saishi"
        self.actbossZige = DnfWarriorsCallZZBossZige()
        self.actbossRule = DnfWarriorsCallZZBossRule()


class DnfWarriorsCallZZBossZige(ConfigInterface):
    def __init__(self):
        self.registerPackage = 117926
        self.buyVip = 117928
        self.buyVipPrize = 117929
        self.lottery = 117925
        self.pfPrize1 = 117950
        self.pfPrize2 = 117951
        self.pfPrize3 = 117952
        self.pfPrize4 = 117953
        self.jsPrize1 = 117938
        self.jsPrize2 = 117939
        self.jsPrize3 = 117940
        self.online = 118003
        self.wangba = 118001
        self.box1 = 117957
        self.box2 = 117958
        self.box3 = 117970
        self.box4 = 117971
        self.box5 = 117972
        self.share1 = 118066
        self.share2 = 117927
        self.onlyOneBox = 118067
        self.score = 117942


class DnfWarriorsCallZZBossRule(ConfigInterface):
    def __init__(self):
        self.registerPackage = 28172
        self.iosPay = "28158"
        self.h5Pay = "28157_35300de17aee936b7593b1dcadedc52a4117"
        self.buyVipPrize = 28174
        self.lottery = 28208
        self.pfPrize1 = 28258
        self.pfPrize2 = 28260
        self.pfPrize3 = 28259
        self.pfPrize4 = 28262
        self.jsPrize1 = 28177
        self.jsPrize2 = 28178
        self.jsPrize3 = 28179
        self.wangba = 28207
        self.getBox1 = 28167
        self.getBox2 = 28168
        self.getBox3 = 28169
        self.getBox4 = 28170
        self.getBox5 = 28171
        self.box1 = 28182
        self.box2 = 28180
        self.box3 = 28183
        self.box4 = 28184
        self.box5 = 28185
        self.share = 28156
        self.share1 = 28156
        self.share2 = 28173


class DnfWarriorsCallBoss(ConfigInterface):
    def __init__(self):
        self.left = {"117925": 0, "117926": 0, "undefined": 0}
        self.used = {"117925": 0, "117926": 1, "undefined": 0}


class QzoneActivityResponse(ConfigInterface):
    def __init__(self):
        self.code = -10000
        self.subcode = -1
        self.message = "不符合领取条件"
        self.notice = 0
        self.time = 1606839612
        self.tips = "6871-284"


class DnfHelperChronicleExchangeList(ConfigInterface):
    def __init__(self):
        self.code = 200
        self.exp = 0
        self.gifts: list[DnfHelperChronicleExchangeGiftInfo] = []
        self.hasPartner = False
        self.level = 1
        self.msg = "success"

    def fields_to_fill(self):
        return [
            ("gifts", DnfHelperChronicleExchangeGiftInfo),
        ]


class DnfHelperChronicleExchangeGiftInfo(ConfigInterface):
    def __init__(self):
        self.sIdentifyId = ""
        self.sName = "一次性材质转换器"
        self.iCard = "20"
        self.iNum = "5"
        self.iLevel = "1"
        self.sLbcode = "ex_0001"
        self.sPic1 = "https://mcdn.gtimg.com/bbcdn/dnf/Scorelb/sPic1/icons/20201130165705.png?version=5705"
        self.isLock = 0
        self.usedNum = 0
        self.iLbSel = "1"
        self.sExpire = ""
        self.SubGifts: list[DnfHelperChronicleExchangeSubGiftInfo] = []
        self.iIsOpen = "2"
        self.sAndroidUrl = ""
        self.sIOSUrl = ""
        self.sExperienceNum = "0"

    def fields_to_fill(self):
        return [
            ("SubGifts", DnfHelperChronicleExchangeSubGiftInfo),
        ]


class DnfHelperChronicleExchangeSubGiftInfo(ConfigInterface):
    def __init__(self):
        self.GiftName = "鬼剑士·女"
        self.GiftId = " 62"


class DnfHelperChronicleBasicAwardList(ConfigInterface):
    def __init__(self):
        self.basic1List: list[DnfHelperChronicleBasicAwardInfo] = []
        self.basic2List: list[DnfHelperChronicleBasicAwardInfo] = []
        self.code = 200
        self.hasPartner = False
        self.msg = "success"

    def fields_to_fill(self):
        return [
            ("basic1List", DnfHelperChronicleBasicAwardInfo),
            ("basic2List", DnfHelperChronicleBasicAwardInfo),
        ]


class DnfHelperChronicleBasicAwardInfo(ConfigInterface):
    def __init__(self):
        self.sIdentifyId = ""
        self.giftName = "时间的引导石10个礼盒"
        self.giftNum = 1
        self.isLock = 1
        self.isUsed = 0
        self.sPic = "https://mcdn.gtimg.com/bbcdn/dnf/Scorereward/sLbPic2/icons/202011262233175fbfbcad13bc7.png"
        self.sName = "1"
        self.iLbSel1 = 1
        self.sLbCode = "basic_0001"


class DnfHelperChronicleLotteryList(ConfigInterface):
    def __init__(self):
        self.code = 200
        self.gifts: list[DnfHelperChronicleLotteryGiftInfo] = []
        self.msg = "success"

    def fields_to_fill(self):
        return [
            ("gifts", DnfHelperChronicleLotteryGiftInfo),
        ]


class DnfHelperChronicleLotteryGiftInfo(ConfigInterface):
    def __init__(self):
        self.sIdentifyId = ""
        self.sName = "+8 装备增幅券*1"
        self.fChance = "0.001"
        self.iCard = "10"
        self.sLbCode = "lottery_0007"
        self.sLbPic = "https://mcdn.gtimg.com/bbcdn/dnf/Scorelottery/sLbPic/icons/20201127103006.png?version=3007"
        self.iRank = "1"
        self.iAction = "1"


class DnfHelperChronicleUserActivityTopInfo(ConfigInterface):
    def __init__(self):
        self.des = "十二月 · 卡恩"
        self.bImage = "https://mcdn.gtimg.com/bbcdn/dnf/Scoretheme/sPic2/icons/20201130165539.png?version=5540"
        self.startTime = "2021-01-01 02:00:00"
        self.point = 0
        self.level = 1
        self.levelName = "初级"
        self.levelIcon = "https://mcdn.gtimg.com/bbcdn/dnf/Scorelevelname/sPic1/icons/20201111145754.png?version=5754"
        self.totalExp = 0
        self.currentExp = 0
        self.levelExp = 5
        self.giftImage = "https://mcdn.gtimg.com/bbcdn/dnf/Scorereward/sLbPic2/icons/202011262233235fbfbcb30af65.png"
        self.isClose = False
        self.signCardNum = "3"

    def get_level_info_and_points_to_show(self) -> tuple[str, int]:
        levelInfo = f"LV{self.level}({self.currentExp}/{self.levelExp})"
        chronicle_points = self.point
        if self.totalExp == 0:
            levelInfo = ""
            chronicle_points = 0

        return levelInfo, chronicle_points

    def is_full_level(self) -> bool:
        return self.level == 30


class DnfHelperChronicleUserTaskList(ConfigInterface):
    def __init__(self):
        self.pUserId = ""
        self.pEncodeUserId = "ab1a9a478692"
        self.pNickname = "风之凌殇（私聊这个号）"
        self.mNickname = "风之凌殇"
        self.mIcon = "http://q.qlogo.cn/qqapp/1104466820/8F5DF4AB0D1CBAC3281E8549D6334034/100"
        self.pIcon = "https://q.qlogo.cn/qqapp/1105742785/FF795385EA973689A70CAD79514374D3/100"
        self.hasPartner = False
        self.hasRedDot = False
        self.isTip = False
        self.taskList: list[DnfHelperChronicleUserTaskInfo] = []

    def get_partner_info(self, dnf_helper_info) -> str:
        from config import DnfHelperInfoConfig
        dnf_helper_info: DnfHelperInfoConfig

        partner_name = ""
        if dnf_helper_info.pNickName != "":
            partner_name += f"{dnf_helper_info.pNickName}-本地匹配"
        elif dnf_helper_info.enable_auto_match_dnf_chronicle:
            partner_name += f"{self.pNickname}-自动匹配"

        return partner_name

    def fields_to_fill(self):
        return [
            ("taskList", DnfHelperChronicleUserTaskInfo),
        ]


class DnfHelperChronicleUserTaskInfo(ConfigInterface):
    def __init__(self):
        self.mActionId = "001"
        self.name = "DNF助手签到"
        self.mExp = 11
        self.mStatus = 0
        self.jumpUrl = ""
        self.pActionId = "013"
        self.pExp = 5
        self.pStatus = 0


class DnfHelperChronicleSignList(ConfigInterface):
    def __init__(self):
        self.code = 200
        self.gifts: list[DnfHelperChronicleSignGiftInfo] = []
        self.msg = "success"

    def fields_to_fill(self):
        return [
            ("gifts", DnfHelperChronicleSignGiftInfo),
        ]


class DnfHelperChronicleSignGiftInfo(ConfigInterface):
    def __init__(self):
        self.sIdentifyId = "20221121"
        self.sName = "神秘契约礼包 (1天)"
        self.sLbcode = ""
        self.sDays = "20221121"
        self.sPic1 = "https://mcdn.gtimg.com/bbcdn/dnf/Scoresign/sPic1/icons/20221101104652.png?version=4652"
        self.iRank = ""
        self.iNum = "1"
        self.status = 1
        self.iLbSel = "1"
        self.sExpire = ""
        self.iId = "0"
        self.SubGifts = []
        self.iIsOpen = "2"
        self.sAndroidUrl = ""
        self.sIOSUrl = ""
        self.num = 1
        self.date = "2022-11-21"


class HelloVoiceDnfRoleInfo(ConfigInterface):
    def __init__(self):
        self.area = "11"
        self.areaName = "浙江一区"
        self.roleId = "71672841"
        self.roleName = "风之凌殇呀"
        self.qq = "1054073896"


class XinyueFinancingInfo(ConfigInterface):
    def __init__(self):
        self.name = "体验版周卡"
        self.buy = False
        self.totalIncome = 0
        self.leftTime = 0
        self.endTime = ""


class MajieluoShareInfo(ConfigInterface):
    def __init__(self):
        self.iInvitee = "386596804"
        self.iShareLottery = "0"
        self.iLostLottery = "0"
        self.iAssistLottery = "0"


class DnfSpringInfo(ConfigInterface):
    def __init__(self):
        # 1月21日9:00至2月20日23:59充值DNF的金额
        self.recharge_money = 0
        # 累计获取汤勺数目
        self.total_spoon_count = 0
        # 当前剩余汤勺数目
        self.current_spoon_count = 0
        # 捞饺子次数
        self.laojiaozi_count = 0
        # 整个活动专属附带激活的总数目
        self.total_take_fudai = 0


class Dnf0121Info(ConfigInterface):
    def __init__(self):
        self.sItemIds = []
        self.lottery_times = 0
        self.hasTakeShare = False
        self.hasTakeBind = False
        self.hasTakeLogin = False


class SpringFuDaiInfo(ConfigInterface):
    def __init__(self):
        # 今日是否已打开过福袋
        self.today_has_take_fudai = False
        # 拥有的福袋数目
        self.fudai_count = 0
        # 是否已领取绑定区服赠送的福袋
        self.has_take_bind_award = False
        # 已经邀请成功的流失好友数
        self.invited_ok_liushi_friends = 0
        # 是否已经领取过分享奖励
        self.has_take_share_award = False
        # 累积抽奖数目
        self.total_lottery_times = 0
        # 当前抽奖数目
        self.lottery_times = 0
        # 请求时传参用的一个参数
        self.date_info = 0


class AmesvrSigninInfo(ConfigInterface):
    def __init__(self):
        self.nick_name = "1054073896"
        self.uin = "1054073896"
        self.data = []
        self.total = "0"
        self.msg = "OK"
        self.sMsg = "OK"
        self.ret = "0"
        self.iRet = "0"


class AmesvrQueryFriendsInfo(ConfigInterface):
    def __init__(self):
        self.sMsg = "ok"
        self.iRet = 0
        self.retcode = 0
        self.page = 1
        self.pageSize = 4
        self.total = 90
        self.list: list[AmesvrFriendInfo] = []

    def fields_to_fill(self):
        return [
            ("list", AmesvrFriendInfo),
        ]


class AmesvrFriendInfo(ConfigInterface):
    def __init__(self):
        self.uin = 56885028
        self.nick = "追风"
        self.label = ""
        self.lost = 1
        self.iProba = "0.8625"


class GuanhuaiActInfo(DaoObject):
    def __init__(self, act_name, ruleid):
        self.act_name = act_name
        self.ruleid = ruleid


class BuyInfo(ConfigInterface):
    def __init__(self):
        self.qq = ""
        self.game_qqs = []
        self.expire_at = "2020-01-01 00:00:00"
        self.total_buy_month = 0
        self.buy_records: list[BuyRecord] = []

    def fields_to_fill(self):
        return [
            ("buy_records", BuyRecord),
        ]

    def merge(self, other: BuyInfo):
        from util import format_time, parse_time

        if other.total_buy_month == 0:
            return

        if other.qq != self.qq and other.qq not in self.game_qqs:
            self.game_qqs.append(other.qq)

        for qq in other.game_qqs:
            if qq not in self.game_qqs:
                self.game_qqs.append(qq)

        self.total_buy_month += other.total_buy_month

        records: list[BuyRecord] = [*self.buy_records, *other.buy_records]
        records.sort(key=lambda br: br.buy_at)

        # 重新计算时长
        expired_at = parse_time(records[0].buy_at)
        for record in records:
            now = parse_time(record.buy_at)
            if now > expired_at:
                # 已过期，从当前时间开始重新计算
                start_time = now
            else:
                # 续期，从之前结束时间叠加
                start_time = expired_at

            expired_at = start_time + record.buy_month * timedelta(days=31)

        self.expire_at = format_time(expired_at)
        self.buy_records = records

    def append_records_and_recompute(self, new_records: list[BuyRecord]):
        other = BuyInfo()
        other.qq = self.qq
        other.buy_records = new_records
        for record in other.buy_records:
            if record.is_dlc_reward():
                continue
            other.total_buy_month += record.buy_month

        # 复用merge函数
        self.merge(other)

    def is_active(self, bypass_run_from_src=True):
        return not self.will_expire_in_days(0, bypass_run_from_src)

    def will_expire_in_days(self, days: int, bypass_run_from_src=True) -> bool:
        from util import parse_time, run_from_src

        if run_from_src() and bypass_run_from_src:
            # 使用源码运行不受限制
            return False

        return datetime.now() + timedelta(days=days) > parse_time(self.expire_at)

    def remaining_time(self):
        from util import parse_time

        now = datetime.now()
        expire_at = parse_time(self.expire_at)

        if now < expire_at:
            return expire_at - now
        else:
            return timedelta()

    def description(self) -> str:
        from util import exists_flag_file

        show_all_records_flag_file = "展示全部购买记录"

        buy_accounts = self.qq

        msg = f"主QQ {buy_accounts} 付费内容过期时间为{self.expire_at}，累计购买{self.total_buy_month}个月。"
        if len(self.game_qqs) != 0:
            msg += f"\n附属QQ {', '.join(self.game_qqs)}"

        if len(self.buy_records) != 0:
            record_description_list: list[str] = []
            if len(self.buy_records) <= 5 or exists_flag_file(show_all_records_flag_file):
                # 较少的记录，或者强制开启时，展示全部记录
                record_description_list = [record.description() for record in self.buy_records]
            else:
                # 记录过多时，略过中间部分
                front_count = 2
                back_count = 3

                # 开始的照常显示
                for record in self.buy_records[:front_count]:
                    record_description_list.append(record.description())

                # 中间的藏起来
                mid_date_placeholder = "." * 10
                mid_time_placeholder = "." * 8
                mid_total_month = sum(record.buy_month for record in self.buy_records[front_count:-back_count])
                record_description_list.append(
                    f"{mid_date_placeholder} {mid_time_placeholder} 由于篇幅原因，中间购买的 {mid_total_month} 个月将不显示，可创建名为 {show_all_records_flag_file} 的文件或目录 来强制显示全部记录"
                )

                # 末尾的也照常显示
                for record in self.buy_records[-back_count:]:
                    record_description_list.append(record.description())

            # 拼接记录
            msg += "\n购买详情如下：\n" + "\n".join("\t" + desc for desc in record_description_list)

        msg += "\n"
        msg += "\n通过配置工具直接购买或者使用卡密购买，无需私聊告知，等待10到20分钟左右后即可到账。目前有缓存机制，可能不能及时查询到最新信息~"
        msg += "\n"
        msg += (
            "\n如果是扫【DLC付款码.png】付款的，请私聊 【付款信息、购买内容、需要使用的所有QQ】给我的小号【1870465547】"
        )
        msg += "\n出于效率和QQ被冻结风险的综合考量，不会回复QQ私聊。一般每天会统一处理一到两次，届时看到你的私聊时肯定会处理"
        msg += "\n如果私聊一天（24小时）后仍未看到对应充值记录，可以私聊我提醒下，看到肯定会处理的"

        return msg

    def infer_has_buy_dlc(self) -> bool:
        if len(self.buy_records) == 0:
            return False

        return self.buy_records[0].is_dlc_reward()

    def get_normal_buy_records(self) -> list[BuyRecord]:
        if self.infer_has_buy_dlc():
            return self.buy_records[1:]

        return self.buy_records


class BuyRecord(ConfigInterface):
    def __init__(self):
        self.buy_month = 1
        self.buy_at = "2020-02-06 12:30:15"
        self.reason = "购买"

    def is_dlc_reward(self) -> bool:
        return self.reason.startswith("自动更新DLC赠送")

    def description(self) -> str:
        return f"{self.buy_at} {self.reason} {self.buy_month} 月"


class OrderInfo(ConfigInterface):
    def __init__(self):
        self.qq = "1234567"
        self.game_qqs = []
        self.buy_month = 1


class CardSecret(ConfigInterface):
    def __init__(self):
        self.card = "auto_update-20210310174054-00001"
        self.secret = "cUtsSx0CwVF1p1VurbKuiI4WHQuKP3uz"


class CardSecretUseDetail(ConfigInterface):
    def __init__(self):
        self.card_secret = CardSecret()  # 卡密信息
        self.qq = ""  # 使用QQ
        self.game_qqs = ""  # 附属游戏QQ
        self.use_at = "2020-03-13 12:30:15"  # 使用时间点


class ActCommonInfo(ConfigInterface):
    def __init__(self):
        self.iActivityId = "354870"
        self.sActivityName = "马杰洛的关怀第三期活动"
        self.dtBeginTime = "2021-01-21 10:30:00"
        self.dtEndTime = "2021-02-23 23:59:59"


class AmsActInfo(ConfigInterface):
    def __init__(self):
        self.iActivityId = "354870"
        self.sActivityName = "马杰洛的关怀第三期活动"
        self.iActivityStatus = "3.70"
        self.sServiceType = "dnf"
        self.sServiceDepartment = "group_3"
        self.sClientType = "2"
        self.sAccountType = "1"
        self.dtBeginTime = "2021-01-21 10:30:00"
        self.dtEndTime = "2021-02-23 23:59:59"
        self.tOpenTime = "00:00:00"
        self.tCloseTime = "23:59:59"
        self.iTableNum = "100"
        self.iShutdown = "0"
        self.sBeginFailPrompted = ""
        self.sEndFailPrompted = ""
        self.sNotAllowPrompted = ""
        self.sSDID = "defd4f0ba2d8d6ae2fd0d915f0df1fdf"
        self.sAMSTrusteeship = 0
        self.sAmePcUrl = "x6m5.ams.game.qq.com/ams/ame/amesvr"
        self.sAmeMobileUrl = "x6m5.ams.game.qq.com/ams/ame/amesvr"
        self.capAppId = ""
        self.iAreaRoleModId = "15640"
        self.iAreaModIsNew = 1
        self.iAreaRoleFlowId = "732626"
        self.iAreaRoleAppId = {"qq_appid": "", "wx_appid": "wxb30cf8a19c708c2a"}
        self.flows: dict[str, AmsActFlowInfo] = {}  # flowid => info

    def dict_fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [("flows", AmsActFlowInfo)]

    def is_last_day(self):
        from util import format_time, get_today, parse_time

        return format_time(parse_time(self.get_endtime()), "%Y%m%d") == get_today()

    def get_endtime(self) -> str:
        return self.dtEndTime

    def get_common_info(self) -> ActCommonInfo:
        info = ActCommonInfo()
        info.iActivityId = self.iActivityId
        info.sActivityName = self.sActivityName
        info.dtBeginTime = self.dtBeginTime
        info.dtEndTime = self.dtEndTime

        return info


class AmsActFlowInfo(ConfigInterface):
    def __init__(self):
        self.sFlowName = "输出项"
        self.iNeedLogin = "1"
        self.sFlowAccountType = "undefined"
        self.iAreaCheck = "0"
        self.iNeedAreaRole = "0"
        self.iNeedAreaRoleService = ""
        self.openToOpen = {}
        self.iCap = "0"
        self.functions = []


class IdeActInfo(ConfigInterface):
    def __init__(self):
        self.iRet = 0
        self.sMsg = "ok"
        self.tokens: dict[str, str] = {}  # token => flowid
        self.dev = IdeDevInfo()
        self.flows: dict[str, IdeFlowInfo] = {}  # flowid => info
        self.default_tpls: list[IdeTPLInfo] = []
        self.iPaaSId = "434671"

    def fields_to_fill(self):
        return [
            ("default_tpls", IdeTPLInfo),
        ]

    def dict_fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [("flows", IdeFlowInfo)]

    def is_last_day(self):
        from util import format_time, get_today, parse_time

        return format_time(parse_time(self.get_endtime()), "%Y%m%d") == get_today()

    def get_endtime(self) -> str:
        return self.dev.action.sDownDate

    def get_common_info(self, act_id="") -> ActCommonInfo:
        action = self.dev.action

        info = ActCommonInfo()
        info.iActivityId = act_id
        info.sActivityName = action.sName
        info.dtBeginTime = action.sUpDate
        info.dtEndTime = action.sDownDate

        return info

    def get_bind_config(self) -> IdeTPLInfo | None:
        """
        获取绑定配置
        """
        for tpl in self.default_tpls:
            if tpl.tpl == "bind_area":
                return tpl

        return None


class IdeDevInfo(ConfigInterface):
    def __init__(self):
        self.host = "9.140.210.216 comm.ams.game.qq.com ; 9.25.7.222 apps.game.qq.com ; 9.25.7.222 ossweb-img.qq.com（若有未发布的iHub文件）"
        self.action = IdeActionInfo()


class IdeActionInfo(ConfigInterface):
    def __init__(self):
        from urls import not_know_end_time____, not_know_start_time__

        self.sName = "无法获取活动名称"
        self.sUpDate: str = not_know_start_time__
        self.sDownDate: str = not_know_end_time____


class IdeFlowInfo(ConfigInterface):
    def __init__(self):
        self.sIdeToken = "JKiTtc"
        self.sAccountType = "1"
        self.isLogin = "1"
        self.sName = "接受礼盒"
        self.iAreaChooseType = "1"
        self.sServiceType = "dnf"
        self.sTplType = "default"
        self.iType = "1"
        self.targetAppId = ""
        self.sAMSTrusteeship = "0"
        self.appName = ""
        self.inputParams = []
        self.iCustom = "1"
        self.sAreaService = "dnf"


class IdeTPLInfo(ConfigInterface):
    def __init__(self):
        self.tpl = "bind_area"
        self.tpl_name = "大区角色绑定"
        self.query_map_id = "113789"
        self.query_map_token = "FfPhWA"
        self.bind_map_id = "113790"
        self.bind_map_token = "ii77aT"
        self.sServiceType = "dnf"


class XinyueWeeklyGiftInfo(ConfigInterface):
    def __init__(self):
        self.qq = "123456"
        self.iLevel = 4
        self.sLevel = "4"
        self.tTicket = 0
        self.gift_got_list = ["1", "1", "1", "1", "0", "0", "0"]


class XinyueWeeklyGPointsInfo(ConfigInterface):
    def __init__(self):
        self.nickname = "风之凌殇"
        self.gpoints = 6666


class XinyueCatUserInfo(ConfigInterface):
    def __init__(self):
        self.name = "风之凌殇"
        self.account = "12345678"
        self.gpoints = 6666
        self.vipLevel = 4
        self.has_cat = False


class XinyueCatInfo(ConfigInterface):
    def __init__(self):
        self.fighting_capacity = 233
        self.yuanqi = 100


class XinyueCatInfoFromApp(ConfigInterface):
    def __init__(self):
        self.id = "12345"
        self.user_id = "1234567"
        self.user_group = "4"
        self.pet_id = "pet95f5xxxxxxxxxxxxx317530"
        self.create_time = "1600112292"
        self.deleted = "0"
        self.update_time = "0"
        self.ext1 = None
        self.ext2 = None
        self.pet = {}
        self.makeMoneyCount = 0
        self.mSkinId = 8
        self.mLevel = "2"
        self.mPower = "230"
        self.mDecorationId = "7"
        self.sendV = 0
        self.sendP = 0


class XinyueCatMatchResult(ConfigInterface):
    def __init__(self):
        self.iRet = 0
        self.result = 1
        self.matchId = "ojl_Pwosr1KLPgphP3LkcoowmHyI"
        self.matchPower = "231"
        self.matchSkinId = 0
        self.matchPetName = "猫星人"
        self.ending = 1
        self.matchVitality = 300


class DnfCollectionInfo(ConfigInterface):
    def __init__(self):
        self.has_init = False
        self.luckyCount = 0
        self.scoreCount = 0
        self.openLuckyCount = 0
        self.send_total = 0
        self.total_page = 0


class DnfHeiyaInfo(ConfigInterface):
    def __init__(self):
        self.lottery_count = 0
        self.box_score = 0


class DnfHelperInfo(ConfigInterface):
    def __init__(self):
        self.unlocked_maps = set()
        self.remaining_play_times = 0


class DnfHelperGameInfo(ConfigInterface):
    def __init__(self):
        self.shareeuin = "f566PsFtrpanByrpzzhpcc6TLZ80qf83r8mY3GcjsQWLgAoBSWrj"
        self.shareenickname = "41c1-JYm0PG0NvcdHzyR_DkOqUrgaKW61rCo8VI4AlJ3RMPDRmxZw9C9c_eHt-ol5tqASsiNfuW6Dffq7QFgjcWxKmPO9GovbtfZ46dxAw3Ln1lDWNAvmvolFcl-CZ7oNVLmivPVL7bY8spbjJEhNI0"
        self.GameTimes = "3"
        self.lastTime = -1
        self.gametype = 0
        self.map1 = -1
        self.map2 = -1
        self.len = -1
        self.euin = -1
        self.enickname = -1
        self.bindeuin = -1
        self.bindenickname = -1
        self.finishArrRes = []
        self.bindStatus = False
        self.bindTime = 1619576495
        self.bindLastTime = 0


class GuanjiaNewRequest(ConfigInterface):
    def __init__(self):
        self.aid = "2021061115132511816"
        self.bid = "2021061115132511816"
        self.lid = "220"
        self.openid = "992EAAA8B47EA71D469EF9F6A09B6666"
        self.nickname = "风之凌殇"
        self.account = "992EAAA8B47EA71D469EF9F6A09B6666"
        self.key = "5B18A7C95B9502523D8CFDE667BDABCD"
        self.accountType = "QQ"
        self.loginType = "qq"
        self.outVeri = 1
        self.roleArea = "11"
        self.roleid = "71676666"
        self.check = 0

        self.drawLogId = 2262427132
        self.area = "11"
        self.accessToken = "5B18A7C95B9502523D8CFDE667BDABCD"
        self.gjid = "992EAAA8B47EA71D469EF9F6A09B6666"
        self.token = "5B18A7C95B9502523D8CFDE667BDABCD"

        self.pageIndex = 1
        self.pageSize = 1000


class GuanjiaNewQueryLotteryInfo(ConfigInterface):
    def __init__(self):
        self.success = 0
        self.message = ""
        self._id = ""
        self.result: list[GuanjiaNewQueryLotteryResult] = []

    def fields_to_fill(self):
        return [
            ("result", GuanjiaNewQueryLotteryResult),
        ]


class GuanjiaNewQueryLotteryResult(ConfigInterface):
    def __init__(self):
        self.expireTime = ""
        self.string5 = ""
        self.simpleCardId = ""
        self.string2 = ""
        self.string1 = ""
        self.string4 = ""
        self.string3 = ""
        self.state = 3
        self.subcomment = ""
        self.type = "yxlb"
        self.receiverAddress = ""
        self.wxNum = "992EAAA8B47EA71D469EF9F6A09B5786"
        self.drawLogId = 2262427132
        self.activityId = "61705"
        self.presentId = "IEGAMS-385698-412372"
        self.receiverName = ""
        self.qq = ""
        self.receiverPhone = ""
        self.issueTime = "2021-06-27 18:01:06.0"
        self.image = "https://webcdn.m.qq.com/shuidi/bonus/61705/1623658802936.png"
        self.seqId = "2021062718010579b670423368425b9272805903e08482"
        self.pkgname = "none_dnf"
        self.jump = ""
        self.bonusId = "230"
        self.ruleId = "1646112"
        self.extInfo = ""
        self.autoIssue = 0
        self.tips = ""
        self.spaBonus = ""
        self.comment = "抗疲劳秘药(5点)（LV80-100)*1"
        self.mobile = ""

    def has_taken(self) -> bool:
        return self.issueTime != ""


class GuanjiaNewLotteryResult(ConfigInterface):
    def __init__(self):
        self.success = 0
        self.message = ""
        self.data = GuanjiaNewLotteryResultData()


class GuanjiaNewLotteryResultData(ConfigInterface):
    def __init__(self):
        self.expireTime = ""
        self.string5 = ""
        self.string2 = ""
        self.string1 = ""
        self.string4 = ""
        self.string3 = ""
        self.state = -1
        self.issueTime = ""
        self.subcomment = ""
        self.image = "https://webcdn.m.qq.com/shuidi/bonus/61705/1623658802936.png"
        self.type = "yxlb"
        self.seqId = "202106271200354d8c4f1d1a6c4e3cb2b135c7828629f9"
        self.pkgname = "none_dnf"
        self.drawLogId = 2262368993
        self.jump = ""
        self.bonusId = "230"
        self.presentId = "IEGAMS-385698-412372"
        self.ruleId = "1646112"
        self.extInfo = ""
        self.autoIssue = 0
        self.tips = ""
        self.spaBonus = ""
        self.comment = "抗疲劳秘药(5点)（LV80-100)*1"


class ColgBattlePassQueryInfo(ConfigInterface):
    def __init__(self):
        # 兑换币
        self.cm_token = 0
        # 商城链接
        self.cmall_url = ""
        # 活跃值
        self.user_credit = 0
        # 奖励列表
        self.user_reward_list: list[ColgBattlePassRewardInfo] = []
        # 任务列表
        self.user_task_list = ColgBattlePassUserTaskList()

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("user_reward_list", ColgBattlePassRewardInfo),
        ]


class ColgBattlePassUserTaskList(ConfigInterface):
    def __init__(self):
        # 任务列表
        self.list: list[ColgBattlePassTaskInfo] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("list", ColgBattlePassTaskInfo),
        ]


class ColgBattlePassInfo(ConfigInterface):
    def __init__(self):
        # 战令ID
        self.activity_id = "4"
        # 活跃值
        self.lv_score = 0
        # 兑换币
        self.conversion = 0
        # 任务列表
        self.tasks: list[ColgBattlePassTaskInfo] = []
        # 奖励列表
        self.rewards: list[ColgBattlePassRewardInfo] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("tasks", ColgBattlePassTaskInfo),
            ("rewards", ColgBattlePassRewardInfo),
        ]

    def untaken_rewards(self) -> list[str]:
        untaken_rewards = []

        for reward in self.rewards:
            if reward.is_finish and not reward.is_get:
                untaken_rewards.append(reward.reward_name)

        return untaken_rewards


class ColgBattlePassTaskInfo(ConfigInterface):
    def __init__(self):
        self.id = "96"
        self.task_name = "登入论坛"
        self.task_reward = "15"
        self.task_url = ""
        self.credits_type = "0"
        self.sub_type = "1"
        self.task_qid = 0
        self.is_finish = False
        self.is_get = False
        self.status = False
        self.remark = "<p>1、登入APP同样可以完成该任务哦！</p>\n<p>2、任务完成后记得点击领取来获得活跃值</p>"
        self.task_msg = ""
        self.exchange_credits = 0
        self.sort_id = 1
        self.is_highlight = "0"


class ColgBattlePassRewardInfo(ConfigInterface):
    def __init__(self):
        self.lv = "51"
        self.reward_img = "https://img-cos.colg.cn/uploads/images/202106/202106091826325699.png/ori_png"
        self.reward_pic = "https://img-cos.colg.cn/uploads/images/202106/202106171733228771.png/ori_png"
        self.reward_name = "+10装备强化券"
        self.reward_count = "750"
        self.is_get = False
        self.is_finish = False
        self.is_display = "1"
        self.is_clog = False
        self.sort_id = 12


class ColgYearlySigninInfo(ConfigInterface):
    def __init__(self):
        # 活动id
        self.activity_id = "9"
        # 已签到天数
        self.signin_days = 0
        # 奖励列表
        self.rewards: list[ColgYearlySigninRewardInfo] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("rewards", ColgYearlySigninRewardInfo),
        ]


class ColgYearlySigninRewardInfo(ConfigInterface):
    def __init__(self):
        # 奖励id
        self.reward_bag_id = "32"
        # 奖励名称
        self.title = "累计签到3天"
        # 奖励类别
        self.type = "9"
        # 签到天数
        self.days = "3"
        # 奖励列表
        self.list = []
        # 0-可领取 1-已领取 2-不可领取
        self.status = 1

    def get_reward_name_list(self) -> list[str]:
        name_list = []
        for reward in self.list:
            name_list.append(reward["gift"])

        return name_list


class ResponseInfo(ConfigInterface):
    def __init__(self):
        self.status_code = 200
        self.reason = "ok"
        self.text = ""


class XiaojiangyouInfo(ConfigInterface):
    def __init__(self):
        self.source = "xy_games"
        self.user_id = "1054073896"
        self.game_id = "1"
        self.acctype = "qq"
        self.intervene_msg = XiaojiangyouInterveneMsg()
        self.intervene_msg_count = 0
        self.hot_question = []
        self.user_info = XiaojiangyouUserInfo()
        self.role_info = XiaojiangyouRoleInfo()
        self.history_page_count = 10
        self.certificate = "600eac0a8be98459477c30971c23f25cd63de6cc"
        self.user_profile = {"robot_use_status": 1, "wx_img": ""}


class XiaojiangyouInterveneMsg(ConfigInterface):
    def __init__(self):
        self.answer = []
        self.option = []


class XiaojiangyouUserInfo(ConfigInterface):
    def __init__(self):
        self.headimgurl = ""
        self.nickname = ""
        self.level = 0


class XiaojiangyouRoleInfo(ConfigInterface):
    def __init__(self):
        self.source = "xy_games"
        self.game_id = "1"
        self.role_id = "6b712e00f376b8b46c4db8aab2bcba19"
        self.role_name = "风之凌殇呀"
        self.system_id = 2
        self.region_id = 1
        self.area_id = 1
        self.plat_id = 1
        self.partition_id = "11"
        self.acctype = ""


class XiaojiangyouUserProfile(ConfigInterface):
    def __init__(self):
        self.robot_use_status = 1
        self.wx_img = ""


class XiaojiangyouPackageInfo(ConfigInterface):
    def __init__(self):
        self.ams_id = "IEGAMS-369679-398942"
        self.package_group_id = "1550778"
        self.card_image = "//ossweb-img.qq.com/images/xiaoyue/pc/dnf/zhoulb.jpg"
        self.tool_id = 1371
        self.token = "0c316d84b848b72985eade54a57d1c31"


class NewArkLotteryLotteryCountInfo(ConfigInterface):
    def __init__(self):
        self.ID = 6792
        self.name = "消耗"
        self.init = 0
        self.extra = 0
        self.add = 6
        self.sub = 6
        self.left = 0
        self.need = 1
        self.enough = False


class NewArkLotteryCardCountInfo(ConfigInterface):
    def __init__(self):
        self.id = "1"
        self.num = 0


class NewArkLotterySendCardResult(ConfigInterface):
    def __init__(self):
        self.code = 0
        self.message = "succ"
        self.data = NewArkLotterySendCardResultData()

    def is_ok(self) -> bool:
        return self.code == 0 and self.data.code == 0


class NewArkLotterySendCardResultData(ConfigInterface):
    def __init__(self):
        self.code = 0
        self.message = ""


class NewArkLotteryRequestCardResult(ConfigInterface):
    def __init__(self):
        self.code = 0
        self.message = "succ"
        self.data = NewArkLotteryRequestCardResultData()


class NewArkLotteryRequestCardResultData(ConfigInterface):
    def __init__(self):
        self.token = ""


class NewArkLotteryAgreeRequestCardResult(ConfigInterface):
    def __init__(self):
        self.code = 0
        self.message = "succ"
        self.data = NewArkLotteryAgreeRequestCardResultData()

    def is_ok(self) -> bool:
        return self.code == 0 and self.data.code == 0


class NewArkLotteryAgreeRequestCardResultData(ConfigInterface):
    def __init__(self):
        self.code = 0
        self.message = ""


class DnfHelperQueryInfo(ConfigInterface):
    def __init__(self):
        self.hasfinish = 0
        self.taskId = 797903
        self.inittask = [797807, 797903, 797908]
        self.tasknums = 0
        self.todayhastask = 0


class HuyaActTaskInfo(ConfigInterface):
    def __init__(self):
        self.taskId = 16234
        self.actId = 4210
        self.taskName = "我爱看直播"
        self.taskAttr = 1
        self.taskType = 2
        self.taskFrequency = 2
        self.taskParams = "watchId=2108&timeLimit=5"
        self.taskTarget = "5"
        self.taskUrl = ""
        self.taskIcon = ""
        self.taskDesc = "每日观看DNF专区5分钟"
        self.isFinalTask = 0
        self.actCount = -1
        self.taskStartTime = 0
        self.taskEndTime = 0
        self.prizeList = []


class HuyaUserTaskInfo(ConfigInterface):
    def __init__(self):
        self.taskId = 16234
        self.actId = 4210
        self.taskStatus = 1
        self.prizeStatus = 0
        self.taskValue = "17"
        self.taskCount = 0
        self.prizeCount = 0


class GuanJiaUserInfo(ConfigInterface):
    def __init__(self):
        self.province = ""
        self.city = ""
        self.year = "19XX"
        self.openid = "XXXXXX"
        self.sex = 1
        self.nickname = "XXXXXX"
        self.headimgurl = "http://thirdqq.qlogo.cn/g?b=oidb&k=XXXXXX&s=100&t=1556477786"
        self.key = "XXXXXX"


class XinYueTeamAwardInfo(ConfigInterface):
    def __init__(self):
        self.partition_name = "5rWZ5rGf5LiA5Yy6"
        self.role_name = "6aOO5LmL5YeM5q6H5ZGA"
        self.gift_name = "高级运镖令奖励"
        self.created = "1703615940"
        self.gift_time = "2023-12-27 02:39:00"
        self.package_real_flag = "0"
        self.id = "1231500205"
        self.gift_id = "4748280"
        self.package_cdkey = ""
        self.req_serial = "sm-cm5hrgo7n68iksapqlrg"

        # self.dtGetPackageTime = "2021-10-29 21:32:38"
        # self.iBroadcastFlag = "0"
        # self.iChildModuleId = "0"
        # self.iModuleId = "397009"
        # self.iPackageGroupId = "1537766"
        # self.iPackageId = "2374025"
        # self.iPackageNum = "1"
        # self.iPackagePrice = "5000"
        # self.iStatus = "2"
        # self.id = "69353284"
        # self.jIdipExtendReplace = ""
        # self.sAreaName = "浙江一区"
        # self.sCdkey = ""
        # self.sExtend1 = "11"
        # self.sExtend2 = ""
        # self.sExtend3 = "490022110"
        # self.sExtend4 = ""
        # self.sExtend5 = ""
        # self.sGender = "11"
        # self.sItemType = "11"
        # self.sMediacySerial = ""
        # self.sPackageName = "装备提升礼盒"
        # self.sPlatId = "0"
        # self.sRelativeIps = ""
        # self.sRoleArea = "11"
        # self.sRoleId = ""
        # self.sRoleName = ""
        # self.sRolePartition = "11"
        # self.sSerialNum = "AMS-TGCLUB-1029213238-N4BKmM-366480-747693"
        # self.sUin = ""


class XinYueTeamGroupInfo(ConfigInterface):
    def __init__(self):
        self.team_name = ""
        self.is_local = True


class XinYueMatchServerAddTeamRequest(ConfigInterface):
    def __init__(self):
        self.leader_qq = ""
        self.team_id = ""


class XinYueMatchServerCommonResponse(ConfigInterface):
    def __init__(self):
        self.code = 0
        self.message = ""
        self.data = None


class XinYueMatchServerRequestTeamRequest(ConfigInterface):
    def __init__(self):
        self.request_qq = ""


class XinYueMatchServerRequestTeamResponse(ConfigInterface):
    def __init__(self):
        self.team_id = ""


class DnfChronicleMatchServerAddUserRequest(ConfigInterface):
    def __init__(self):
        self.user_id = ""
        self.qq = ""


class DnfChronicleMatchServerCommonResponse(ConfigInterface):
    def __init__(self):
        self.code = 0
        self.message = ""
        self.data = None


class DnfChronicleMatchServerRequestUserRequest(ConfigInterface):
    def __init__(self):
        self.request_user_id = ""
        self.request_qq = ""


class DnfChronicleMatchServerRequestUserResponse(ConfigInterface):
    def __init__(self):
        self.user_id = ""


class CreateWorkListInfo(ConfigInterface):
    def __init__(self):
        self.total = "0"
        self.list: list[CreateWorkInfo] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("list", CreateWorkInfo),
        ]


class CreateWorkInfo(ConfigInterface):
    def __init__(self):
        self.iInfoId = 1774933
        self.tglAuthorID = 2190051
        self.iBizUserId = ""
        self.sVid = ""
        self.iGameId = 453
        self.iPlayTimes = 0
        self.iStaus = 30
        self.iStatus = 30
        self.sTypeName = ""
        self.sSubTypeName = ""
        self.sKeyWord = ""
        self.sUserCreator = "夕尘"
        self.sCreator = "1051866291"
        self.sUserQQ = "1051866291"
        self.sUserAvatar = "http://thirdqq.qlogo.cn/g?b=oidb&k=XbfGAJwqEjUmz2pia57EzSA&s=100&t=1586250435"
        self.sAuthorLevel = "C"
        self.kol = ""
        self.sFromUrl = ""
        self.sTitle = "魔界人元气满满防尘口罩"
        self.sContent = (
            "<p><melo-data></melo-data></p><div><h1>魔界人口罩</h1><p>卖点：生活刚需，成本低下，展示个性。</p><p><img src='https://img.tgl.qq.com/cover/20211005/3f244bb8bee2ee6ef63d89fb235cf086_1633411914.png' style='max-width: "
            "100%; height: auto;'  /><br  /></p><p><br  /></p><p>设计：考虑到防疫口罩拥有极高的安全等级，因此推荐制作常规的装饰级口罩。<br  /></p><p><img src='https://img.tgl.qq.com/cover/20211005/5423e9635781cb5d4f54b8a6dbfcfb77_"
            "1633414580.png' style='max-width: 100%; height: auto;'  /><br  /></p><p><br  /></p><p>·背景：</p><p>疫情时代下，口罩成为了人们的必需品。</p><p>2021年春节期间，五菱宏光为春晚独家提供了口罩支持，使其成为了当时春晚最成功的营"
            "销品牌之一。</p><p>看人先看脸，口罩作为戴在人们脸上的挂件，是最受人们关注的产品之一。一个好看的口罩，不仅可以让佩戴者心情愉悦，同时还可以广泛吸引其他人眼光。</p><p><img src='https://img.tgl.qq.com/cover/20211005/c19b96a1605df6"
            "57c7f9252e3612df64_1633412019.png' style='max-width: 100%; height: auto;'  /><br  /></p><p><br  /></p><p>案例：</p><p>著名游戏《最终幻想》系列厂商——史克威尔工作室就曾经推出过一款简单的文字口罩，作为周边商城满单赠送礼物，"
            "引发游戏圈不小讨论。</p><p><img src='https://img.tgl.qq.com/source/open/20211005/16334120477ad1d9973bb26993.jpg' style='max-width: 100%; height: auto;' data-origin='https%3A%2F%2Fimg1.gamersky.com%2Fimage2020%2F0"
            "5%2F20200512_zty_412_4%2Fgamersky_02origin_03_202051210515B8.jpg'  /><br  /></p><p><br  /></p><p><br  /></p></div><img style='width:1px;height:1px;border:none' forstat='1'  src='https://itea-stat.qq.com/img/sta"
            "t?cid=tgleb0db07909bad&aid=1774933'>"
        )
        self.sDetailUrl = ""
        self.sInfoImageAddr = "https://img.tgl.qq.com/cover/20211005/e0d739e75c6b71b43f13ae1f92515c2b_1633414545.png"
        self.sInfoBigImageAddr = "https://img.tgl.qq.com/cover/20211005/e0d739e75c6b71b43f13ae1f92515c2b_1633414545.png"
        self.sSubContent = "魔界人元气满满防尘口罩"
        self.description = ""
        self.sArticleType = 0
        self.sHourLong = ""
        self.dtCreateTime = "2021-10-05 14:16:42"
        self.dtModifyTime = "2021-11-10 18:11:40"
        self.statUrl = (
            "http://itea-cdn.qq.com/file/tgl/js/tgl_moni.js?aid=1774933&gid=453&cid=tgleb0db07909bad&_t=1637424000"
        )
        self.iDeliverSource = 6
        self.atlas = ""
        self.covers = []
        self.feedCovers = []
        self.infoImages = {}
        self.autoAudit = False
        self.firstRelease = False
        self.sUserIDCard = "1b92f36d5446553be2680ba65b232e78"
        self.themeId = "12"
        self.isShortVideo = 0
        self.extra_info = ""
        self.original = 1
        self.source = "0"
        self.weChat = ""
        self.mediaUser = None
        self.mediaUserUid = ""
        self.iPubInIu = 0
        self.albumId = 0
        self.category = 2
        self.SubCategory = 12
        self.audioUrl = ""
        self.videoDirection = 0
        self.iGlanceNum = "50"
        self.iPraiseNum = "528"


class MoJieRenInfo(ConfigInterface):
    def __init__(self):
        self.iRet = "0"
        self.sMsg = "ok"
        self.iCurrPos = "9"
        self.iCurrRound = "1"
        self.iTaskType = 0
        self.iMagic = "0"
        self.iTreasure = "0"
        self.jHolds = MoJieRenHoldInfo()
        self.isAuth = "1"
        self.iTaskStatus = {}

    def on_config_update(self, raw_config: dict):
        # 首次查询时，部分字段会是null，需要修改为正确的值，确保后续逻辑无误
        # "iCurrPos": null, "iCurrRound": null, "iExploreTimes": null
        self.iCurrPos = self.iCurrPos or "1"
        self.iCurrRound = self.iCurrRound or "1"
        self.iTaskStatus = self.iTaskStatus or {}


class MoJieRenHoldInfo(ConfigInterface):
    def __init__(self):
        self.hold_total_round_1 = MoJieRenHoldItem()
        self.hold_total_round_2 = MoJieRenHoldItem()
        self.hold_total_round_3 = MoJieRenHoldItem()
        self.hold_total_adventure = MoJieRenHoldItem()


class MoJieRenHoldItem(ConfigInterface):
    def __init__(self):
        self.iRet = 0
        self.sMsg = "succ"
        self.iLeftNum = 0
        self.iUsedNum = 0
        self.iTotalNum = "0"
        self.arrExtData = {}


card_id_to_action_id = {
    0: "566",
    1: "565",
    2: "564",
    3: "567",
    4: "568",
}


class MaJieLuoInfo(ConfigInterface):
    def __init__(self):
        self.iRet = "0"
        self.sMsg = "ok"
        self.luckCard = "0"
        self.hitCard = "0"
        self.itemInfo = []
        self.totalCard = None
        self.isLuck = "1"
        self.itemUin = "1054073896"
        self.isAuth = "1"
        self.jHolds = {}
        self.isLogin = 1
        self.isLive = 0
        self.iPass = "0"
        self.isBakar = "0"
        self.isDimensional = "0"
        self.isNightmare = "0"


class VoteWorkList(ConfigInterface):
    def __init__(self):
        self.iRet = "0"
        self.sMsg = "ok"
        self.data: list[VoteWorkInfo] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("data", VoteWorkInfo),
        ]


class VoteWorkInfo(ConfigInterface):
    def __init__(self):
        self.tickets = 9064
        self.title = "鹿王本生-女鬼剑士"
        self.workId = "21"


class VoteEndWorkList(ConfigInterface):
    def __init__(self):
        self.iRet = "0"
        self.data: dict[int, str] = {}


class VoteEndWorkInfo(ConfigInterface):
    def __init__(self):
        self.tickets = 9064
        self.workId = "21"


class DnfHelperChronicleBindInfo(ConfigInterface):
    def __init__(self):
        self.is_need_transfer = True
        self.is_allow_enter = False
        self.is_roleid_bind_userid_match = False
        self.tip = ""
        self.tip_title = ""


class MyHomeInfo(ConfigInterface):
    def __init__(self):
        self.iRet = "0"
        self.sMsg = "ok"
        self.isLogin = 1
        self.sNick = "风***呢"
        self.iJoin = True
        self.iTask = "0"
        self.iRice = "0"
        self.iRefresh = "0"
        self.iOnline = 0
        self.iPassed = "0"
        self.iFatigue = 0
        self.iOpenPoints = "10"
        self.iLuckyNum = "9"
        self.iLucky = "0"
        self.isUser = 1


class MyHomeFarmInfo(ConfigInterface):
    def __init__(self):
        self.sFarmland = "a1Vqam1HM2FqSnBPenNENGs3OUQ3QTk4UmxXNzdJSlJOY0VVTEdQTnpUbz0."
        self.iNum = "10"
        self.iUsedNum = "0"
        self.dtMatureTime = 1663900268000

    def is_mature(self) -> bool:
        now_unix_mills = int(datetime.now().timestamp() * 1000)

        return now_unix_mills >= self.dtMatureTime

    def mature_time(self) -> str:
        from util import format_timestamp

        return format_timestamp(self.dtMatureTime / 1000)


class MyHomeGiftList(ConfigInterface):
    def __init__(self):
        self.jData: list[MyHomeGift] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("jData", MyHomeGift),
        ]


class MyHomeGift(ConfigInterface):
    def __init__(self):
        self.id = "176718"
        self.iUin = "1054073896"
        self.iPropId = "2109723"
        self.sPropName = "+10 装备增幅券"
        self.iType = "2"
        self.iPoints = "1600"
        self.iTimes = "1"
        self.iUsedNum = "0"
        self.discount = "100"
        self.dDate = "2022-06-16"
        self.dtCreateAt = "2022-06-16 21:07:14"

    def is_valuable_gift(self) -> bool:
        price = int(self.iPoints)

        # 原价大于1000的是稀有奖励，包含下列奖励
        #   1. 次元穿梭光环兑换券	1200 积分
        #   2. +10 装备增幅券	1600 积分
        #   3. 第3期稀有装扮1部位自选礼盒	1800 积分
        #   4. 原初职业白金徽章礼盒	1800 积分
        return price > 1000

    def is_extra_wanted(self, extra_wanted_gift_name_list: list[str]) -> bool:
        for gift_name in extra_wanted_gift_name_list:
            if gift_name in self.sPropName:
                return True

        return False

    def price_after_discount(self) -> int:
        price_after_discount = int(int(self.iPoints) * int(self.discount) / 100)

        return price_after_discount

    def format_discount(self) -> str:
        return f"{int(self.discount) // 10}折"


class MyHomeValueGift:
    def __init__(self, page: int, owner: str, gift: MyHomeGift):
        self.page = page
        self.owner = owner
        self.gift = gift


class MyHomeFriendList(ConfigInterface):
    def __init__(self):
        self.iRet = "0"
        self.sMsg = "ok"
        self.total = "22"
        self.iPage = "1"
        self.list: list[MyHomeFriendInfo] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("list", MyHomeFriendInfo),
        ]


class MyHomeFriendInfo(ConfigInterface):
    def __init__(self):
        self.id = "724663"
        self.iUin = "32***07"
        self.sNick = "风***鬼"
        self.dDate = "2022-09-26"
        self.dtCreateAt = "2022-09-26 19:35:04"
        self.sUin = "UjNWMGVkMGVVQlZZTnlrOVFHQ1MwZz09"

    def description(self) -> str:
        return f"{self.sNick}({self.iUin})"


class MyHomeFriendDetail(ConfigInterface):
    def __init__(self):
        self.page = 1
        self.info = MyHomeFriendInfo()
        self.gifts: list[MyHomeGift] = []
        self.farm_dict: dict[str, MyHomeFarmInfo] = {}

    def get_qq(self) -> str:
        if len(self.gifts) == 0:
            return ""

        return self.gifts[0].iUin


class LuckyUserInfo(ConfigInterface):
    def __init__(self):
        self.lossType = "1"
        self.point = "2"
        self.pointConf: list[LuckyUserPointConf] = []
        self.pointPackFlow = []
        self.signConf: list[LuckyUserSignConf] = []
        self.syncDate = "20220711"
        self.taskConf: list[LuckyUserTaskConf] = []
        self.taskPackFlow: list[LuckyUserTaskPackFlow] = []
        self.taskStatus = "1-12"
        self.todaySignNum = 1
        self.totalSignNum = 1
        self.week = "1"

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("pointConf", LuckyUserPointConf),
            ("signConf", LuckyUserSignConf),
            ("taskConf", LuckyUserTaskConf),
            ("taskPackFlow", LuckyUserTaskPackFlow),
        ]


class LuckyUserPointConf(ConfigInterface):
    def __init__(self):
        self.editTime = "2022-06-07 15:38:58"
        self.editUser = "eddyzou"
        self.iPackageGroupId = "2130655"
        self.iconName = "王者契约1天*3"
        self.iconUrl = "//odp-public-1-1256315284.file.myqcloud.com/dnfNoloss/202206/629f00927dc49.png"
        self.id = "1"
        self.mrms = "IEGAMS-476084-487803"
        self.point = "7"
        self.sGroupName = "7积分兑换奖励"
        self.serviceType = "dnf"
        self.status = "0"


class LuckyUserSignConf(ConfigInterface):
    def __init__(self):
        self.editTime = "2022-06-07 16:05:08"
        self.editUser = "eddyzou"
        self.iPackageGroupId = "2130635"
        self.iconName = "华丽徽章神秘礼盒*1"
        self.iconUrl = "//odp-public-1-1256315284.file.myqcloud.com/dnfNoloss/202206/629f06b411b75.png"
        self.id = "1"
        self.mrms = "IEGAMS-476081-487800"
        self.num = "1"
        self.sGroupName = "第一天"
        self.serviceType = "dnf"
        self.status = "0"


class LuckyUserTaskConf(ConfigInterface):
    def __init__(self):
        self.apiId = "2"
        self.args = "100"
        self.cmd = "1185"
        self.editTime = "2022-06-08 20:06:58"
        self.editUser = "eddyzou"
        self.iPackageGroupId = "2130618"
        self.iconName = "王者契约1天*1"
        self.iconUrl = "//odp-public-1-1256315284.file.myqcloud.com/dnfNoloss/202206/62a090e2913ec.png"
        self.id = "10"
        self.isL5 = "0"
        self.l5 = '{\n    "l5_mod": null,\n    "l5_cmd": null\n}'
        self.mergeType = "0"
        self.mrms = "IEGAMS-476067-487787"
        self.name = "消耗疲劳100点"
        self.point = "2"
        self.returnIndex = "&.use_fatigue"
        self.returns = "100"
        self.sGroupName = "王者契约1天*1"
        self.serviceType = "dnf"
        self.status = "0"
        self.taskResult = "190"
        self.title = "消耗疲劳100点"
        self.type = "2"
        self.url = ""
        self.userArgs = '[\n    "area",\n    "charac_no"\n]'


class LuckyUserTaskPackFlow(ConfigInterface):
    def __init__(self):
        self.addDate = "2022-07-11"
        self.addTime = "2022-07-11 10:31:43"
        self.flowAction = "20"
        self.flowType = "2"
        self.iArea = "11"
        self.iRoleId = "71672841"
        self.iUin = "1054073896"
        self.id = "505264"
        self.isDel = "0"
        self.packInfo = "487787:2130615"
        self.pointStatus = "1"
        self.rData = '{"iRet":0,"sMsg":"恭喜您获得了礼包： 共鸣的先兆水晶*15个 ","iPackageGroupId":"2130615","iPackageId":"3293528","iPackageNum":"1","sPackageName":"共鸣的先兆水晶*15个","sAmsSerialNum":"AMS-DNF-0711103143-Wqeapt-98250-98627"}'
        self.uid = "19010"


class XinYueBgwUserInfo(ConfigInterface):
    def __init__(self):
        self.gfen = 4441
        self.mobile = ""
        self.nickname = "风之凌殇"
        self.point = 23315
        self.type = 2
        self.gender = 1
        self.headimgurl = "http://thirdqq.qlogo.cn/ek_qqapp/AQWLTKahHNrg5aEvmT7Y1ySCaia3aCJmJjicmcib1xYGR85uY9jTCAeNiaIHhHCAPYtApfXdoBMQ/100"
        self.country = "中国"
        self.province = "广东"


class ComicDataList(ConfigInterface):
    """额外封装一层，方便cache时序列化"""

    def __init__(self):
        self.comic_list: list[ComicData] = []

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("comic_list", ComicData),
        ]

    def get_current_update_progress(self) -> int:
        """获取当前更新进度"""
        update_count = 0
        for comic in self.comic_list:
            if comic.has_updated():
                update_count += 1

        return update_count


class ComicData(ConfigInterface):
    def __init__(self):
        self.id = "1"
        self.updateStatus = "1"
        self.comicUrl = "https://ac.qq.com/ComicView/index/id/654947/seqno/2"

    def has_updated(self) -> bool:
        return self.updateStatus == "1"


class ShenJieGrowUpInfo(ConfigInterface):
    def __init__(self):
        self.curStageData = ShenJieGrowUpCurStageData()
        self.allStagePack: list[ShenJieGrowUpStagePack] = []
        self.taskData: dict[str, ShenJieGrowUpTaskData] = {}

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("allStagePack", ShenJieGrowUpStagePack),
        ]

    def dict_fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [("taskData", ShenJieGrowUpTaskData)]


class ShenJieGrowUpCurStageData(ConfigInterface):
    def __init__(self):
        self.id = "233464"
        self.iUin = "1054073896"
        self.iAreaId = "11"
        self.sRoleId = "45230145"
        self.sRoleName = "%25E9%25A3%258E%25E4%25B9%258B%25E5%2587%258C%25E6%25AE%2587%25E5%2596%25B5"
        self.roleJob = "350"
        self.stage = "2"
        self.stageTask = "0"
        self.stagePack = "0"
        self.task1 = "0"
        self.task2 = "0"
        self.task3 = "0"
        self.task4 = "0"
        self.task5 = "0"
        self.lastTaskDoneTime = "1970-01-01 00:00:00"
        self.initDateTime = "2024-02-08 00:00:18"
        self.initPeriodSday = "20240208"


class ShenJieGrowUpStagePack(ConfigInterface):
    def __init__(self):
        self.stage = "2"
        self.packStatus = 0


class ShenJieGrowUpTaskData(ConfigInterface):
    def __init__(self):
        self.doneNum = 0
        self.needNum = 1
        self.giftStatus = "0"


class XinYueBattleGroundWpeGetBindRoleResult(ConfigInterface):
    def __init__(self):
        self.ret = 0
        self.msg = ""
        self.roles: list[XinYueBattleGroundWpeBindRole] = []
        self.next_page_no = -1
        self.game_info = None

    def fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [
            ("roles", XinYueBattleGroundWpeBindRole),
        ]


class XinYueBattleGroundWpeBindRole(ConfigInterface):
    def __init__(self):
        self.game_open_id = "1054073896"
        self.game_app_id = ""
        self.area_id = 11
        self.plat_id = 2
        self.partition_id = 11
        self.partition_name = "5rWZ5rGf5LiA5Yy6"
        self.role_id = "45230145"
        self.role_name = "6aOO5LmL5YeM5q6H5Za1"
        self.device = "pc"


if __name__ == "__main__":
    from util import format_time, parse_time

    a = BuyInfo()
    a.qq = "11"
    a.game_qqs = ["12", "13"]
    a.total_buy_month = 3
    a.buy_records = [
        BuyRecord().auto_update_config({"buy_at": "2020-02-06 12:30:15"}),
        BuyRecord().auto_update_config({"buy_at": "2021-02-08 12:30:15", "buy_month": 2}),
    ]
    a.expire_at = format_time(parse_time("2020-02-06 12:30:15") + timedelta(days=31 * 3))

    b = BuyInfo()
    b.qq = "11"
    b.game_qqs = ["12", "14"]
    b.total_buy_month = 2
    b.buy_records = [
        BuyRecord().auto_update_config({"buy_at": "2020-02-06 12:30:15"}),
        BuyRecord().auto_update_config({"buy_at": "2021-02-08 12:30:15"}),
    ]
    b.expire_at = format_time(parse_time("2020-02-06 12:30:15") + timedelta(days=31 * 2))

    print(a)
    print(b)

    a.merge(b)
    print(a)
