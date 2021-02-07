from typing import List
from urllib.parse import unquote_plus
from datetime import datetime
from util import parse_time, run_from_src

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

    def fields_to_fill(self):
        return [
            ('valiDate', GoodsValiDateInfo),
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
            self.xytype_str = f"游戏家G{xytype}"
        else:
            self.xytype_str = f"心悦VIP{xytype - 4}"
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
        self.Fcheckparam = "dnf|yes|1054073896|11|45168567*45230145*45481100*62889873*64327847*64327855*64333408*64333413*64349521*64349525*64370730*64370732*64632622*64632641*69837948*69837951*71672841*||||%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%96%B5*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%93%87*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87Meow*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%B8%80%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%BA%8C%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%B8%89%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E5%9B%9B%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%BA%94%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E5%85%AD%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%B8%83%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E5%85%AB%E5%8F%B7*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%96%B5%E5%96%B5*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%96%B5%E5%91%9C*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E4%B9%9D%E5%8F%B7*%E5%8D%A2%E5%85%8B%E5%A5%B6%E5%A6%88%E5%8D%81%E5%8F%B7*%E9%A3%8E%E4%B9%8B%E5%87%8C%E6%AE%87%E5%91%80*|0*3*13*14*14*14*14*14*14*14*14*14*3*3*14*14*11*||1600743086|"
        self.Fmd5str = "FDAF0B1B1E51111CCC0AAD240317E96F"
        self.Fdate = "2020-09-22 10:51:29"
        self.FupdateDate = "2020-09-22 10:51:29"
        self.sAmsNewRoleId = ""
        self.sAmsSerial = "AMS-DNF-0922105129-ng2JeR-215651-558226"


class AmesvrQueryRole(ConfigInterface):
    def __init__(self):
        self.version = 'V1.0.20201105.20201105101730'
        self.retCode = '0'
        self.serial_num = 'AMS-DNF-1220171837-4zFGHv-348623-5381'
        self.data = '_idip_req_id_=&_webplat_msg=21|45168567 风之凌殇 0 100|45230145 风之凌殇喵 3 100|45481100 风之凌殇哇 13 100|62889873 风之凌殇Meow 14 100|64327847 卢克奶妈一号 14 100|64327855 卢克奶妈二号 14 100|64333408 卢克奶妈三号 14 100|64333413 卢克奶妈四号 14 100|64349521 卢克奶妈五号 14 100|64349525 卢克奶妈六号 14 100|64370730 卢克奶妈七号 14 100|64370732 卢克奶妈八号 14 100|64632622 风之凌殇喵喵 3 100|64632641 风之凌殇喵呜 3 100|69837948 卢克奶妈九号 14 100|69837951 卢克奶妈十号 14 100|71672841 风之凌殇呀 11 100|72282733 风之凌殇哦 4 100|72522431 风之凌殇咯 3 100|72574316 风之凌殇咩 3 100|72767454 风之凌殇嘿 3 100|&_webplat_msg_code=0&area=11&msg=21|45168567 风之凌殇 0 100|45230145 风之凌殇喵 3 100|45481100 风之凌殇哇 13 100|62889873 风之凌殇Meow 14 100|64327847 卢克奶妈一号 14 100|64327855 卢克奶妈二号 14 100|64333408 卢克奶妈三号 14 100|64333413 卢克奶妈四号 14 100|64349521 卢克奶妈五号 14 100|64349525 卢克奶妈六号 14 100|64370730 卢克奶妈七号 14 100|64370732 卢克奶妈八号 14 100|64632622 风之凌殇喵喵 3 100|64632641 风之凌殇喵呜 3 100|69837948 卢克奶妈九号 14 100|69837951 卢克奶妈十号 14 100|71672841 风之凌殇呀 11 100|72282733 风之凌殇哦 4 100|72522431 风之凌殇咯 3 100|72574316 风之凌殇咩 3 100|72767454 风之凌殇嘿 3 100|&result=0&uin=1054073896&'
        self.msg = 'success'
        self.checkparam = 'dnf|yes|1054073896|11|45168567*45230145*45481100*62889873*64327847*64327855*64333408*64333413*64349521*64349525*64370730*64370732*64632622*64632641*69837948*69837951*71672841*72282733*72522431*72574316*72767454*||||风之凌殇*风之凌殇喵*风之凌殇哇*风之凌殇Meow*卢克奶妈一号*卢克奶妈二号*卢克奶妈三号*卢克奶妈四号*卢克奶妈五号*卢克奶妈六号*卢克奶妈七号*卢克奶妈八号*风之凌殇喵喵*风之凌殇喵呜*卢克奶妈九号*卢克奶妈十号*风之凌殇呀*风之凌殇哦*风之凌殇咯*风之凌殇咩*风之凌殇嘿*|0*3*13*14*14*14*14*14*14*14*14*14*3*3*14*14*11*4*3*3*3*||1608455917|'
        self.md5str = '3F7F5D5C92CF3E633A40E246A637CC0B'
        self.infostr = ''
        self.checkstr = ''


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


class DnfHelperChronicleExchangeList(ConfigInterface):
    def __init__(self):
        self.code = 200
        self.exp = 0
        self.gifts = []  # type: List[DnfHelperChronicleExchangeGiftInfo]
        self.hasPartner = False
        self.level = 1
        self.msg = "success"

    def fields_to_fill(self):
        return [
            ('gifts', DnfHelperChronicleExchangeGiftInfo),
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


class DnfHelperChronicleBasicAwardList(ConfigInterface):
    def __init__(self):
        self.basic1List = []  # type: List[DnfHelperChronicleBasicAwardInfo]
        self.basic2List = []  # type: List[DnfHelperChronicleBasicAwardInfo]
        self.code = 200
        self.hasPartner = False
        self.msg = "success"

    def fields_to_fill(self):
        return [
            ('basic1List', DnfHelperChronicleBasicAwardInfo),
            ('basic2List', DnfHelperChronicleBasicAwardInfo),
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
        self.gifts = []  # type: List[DnfHelperChronicleLotteryGiftInfo]
        self.msg = "success"

    def fields_to_fill(self):
        return [
            ('gifts', DnfHelperChronicleLotteryGiftInfo),
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


class DnfHelperChronicleUserTaskList(ConfigInterface):
    def __init__(self):
        self.pUserId = ""
        self.mIcon = "http://q.qlogo.cn/qqapp/1104466820/0E82A1DBAE746043CF3AEF95EC39FC2B/100"
        self.pIcon = ""
        self.hasPartner = False
        self.taskList = []  # type: List[DnfHelperChronicleUserTaskInfo]

    def fields_to_fill(self):
        return [
            ('taskList', DnfHelperChronicleUserTaskInfo),
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
        self.gifts = []  # type: List[DnfHelperChronicleSignGiftInfo]
        self.msg = "success"

    def fields_to_fill(self):
        return [
            ('gifts', DnfHelperChronicleSignGiftInfo),
        ]


class DnfHelperChronicleSignGiftInfo(ConfigInterface):
    def __init__(self):
        self.sIdentifyId = ""
        self.sName = "时间引导石礼盒 (5个)"
        self.sLbcode = "sign_0001_1"
        self.sDays = "第1天"
        self.sPic1 = "https://mcdn.gtimg.com/bbcdn/dnf/Scorelb/sPic1/icons/20210128145952.png?version=5952"
        self.iRank = "7"
        self.iNum = "1"
        self.status = 2  # 2-未完成，0-已完成未领取，1-已领取
        self.iLbSel = "1"


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
        self.list = []  # type: List[AmesvrFriendInfo]

    def fields_to_fill(self):
        return [
            ('list', AmesvrFriendInfo),
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
        self.buy_records = []  # type: List[BuyRecord]

    def fields_to_fill(self):
        return [
            ('buy_records', BuyRecord),
        ]

    def is_active(self):
        if run_from_src():
            # 使用源码运行不受限制
            return True

        now = datetime.now()
        return now <= parse_time(self.expire_at)


class BuyRecord(ConfigInterface):
    def __init__(self):
        self.buy_month = 1
        self.buy_at = "2020-02-06 12:30:15"
        self.reason = "购买"


class OrderInfo(ConfigInterface):
    def __init__(self):
        self.qq = "1234567"
        self.game_qqs = []
        self.buy_month = 1
