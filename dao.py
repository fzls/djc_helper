from typing import List
from urllib.parse import unquote_plus

from data_struct import ConfigInterface


class DaoObject:
    def __repr__(self):
        return str(self.__dict__)


class GameInfo(DaoObject):
    def __init__(self, data):
        self.bizName = data["bizName"]
        self.bizCode = data["bizCode"]
        self.gameCode = data["gameCode"]
        self.wxAppid = data["wxAppid"]


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
        self.accountId = "2814890506666666666"
        self.areaID = "20001"
        self.areaName = "梦江南"
        self.bizCode = "jx3"
        self.channelID = "2"
        self.channelKey = "qq"
        self.channelName = "手Q"
        self.ext_param = ""
        self.gameName = "剑网3:指尖江湖"
        self.isHasService = "0"
        self.roleCode = "2814890506666666666"
        self.roleName = "风之凌殇"
        self.serviceID = "20001"
        self.serviceName = "梦江南"
        self.systemID = "1"
        self.systemKey = "android"
        self.type = "1"


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
        self.valiDate = []  # type: List[GoodsValiDateInfo]
        self.heroSkin = []
        self.related = False
        self.category = GoodsCategoryInfo()
        self.isCombinPkg = 0
        self.IsOwn = 0

    def auto_update_config(self, raw_config: dict):
        super().auto_update_config(raw_config)

        if 'valiDate' in raw_config:
            self.valiDate = []
            for cfg in raw_config["valiDate"]:
                ei = GoodsValiDateInfo()
                ei.auto_update_config(cfg)
                self.valiDate.append(ei)


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
        self.award = {"list": []}
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


class DnfRoleInfo(DaoObject):
    def __init__(self, roleid, rolename, forceid, level):
        self.roleid = int(roleid)
        self.rolename = str(rolename)
        # 已知：0-男鬼剑，3-女魔法师，13-男枪士，14-女圣职者
        self.forceid = int(forceid)
        self.level = int(level)


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


class XinYueInfo(DaoObject):
    def __init__(self, score, ysb, xytype, specialMember, username, usericon):
        # 成就点
        self.score = int(score)
        # 勇士币
        self.ysb = int(ysb)
        # 1-4=游戏家G1-4，5-7=心悦VIP1-3
        xytype = int(xytype)
        self.xytype = xytype
        if xytype < 5:
            self.xytype_str = "游戏家G{}".format(xytype)
        else:
            self.xytype_str = "心悦VIP{}".format(xytype - 4)
        # 特邀会员
        self.is_special_member = int(specialMember) == 1
        # 用户名
        self.username = unquote_plus(username)
        # 用户头像
        self.usericon_url = usericon


class XinYueItemInfo(DaoObject):
    def __init__(self, total_obtain_two_score, used_two_score, total_obtain_free_do, used_free_do, total_obtain_refresh, used_refresh):
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


class XinYueTeamInfo(DaoObject):
    def __init__(self):
        self.result = 0
        self.id = ""
        self.score = 0
        self.members = []  # type: List[XinYueTeamMember]


class XinYueTeamMember(DaoObject):
    def __init__(self, qq, nickname, score):
        self.qq = qq
        self.nickname = nickname
        self.score = score


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
        self.left = {
            "117925": 0,
            "117926": 0,
            "undefined": 0
        }
        self.used = {
            "117925": 0,
            "117926": 1,
            "undefined": 0
        }


class QzoneActivityResponse(ConfigInterface):
    def __init__(self):
        self.code = -10000
        self.subcode = -1
        self.message = "不符合领取条件"
        self.notice = 0
        self.time = 1606839612
        self.tips = "6871-284"
