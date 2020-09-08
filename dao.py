from typing import List
from urllib.parse import unquote_plus


class DaoObject:
    def __repr__(self):
        return str(self.__dict__)


class DnfRoleInfo(DaoObject):
    def __init__(self, roleid, rolename, forceid, level):
        self.roleid = int(roleid)
        self.rolename = str(rolename)
        # 已知：0-男鬼剑，3-女魔法师，13-男枪士，14-女圣职者
        self.forceid = int(forceid)
        self.level = int(level)

    def __repr__(self):
        return str(self.__dict__)


class Jx3RoleInfo(DaoObject):
    def __init__(self, roleid, rolename):
        self.roleid = roleid
        self.rolename = rolename

    def __repr__(self):
        return str(self.__dict__)


class Jx3GiftInfo(DaoObject):
    def __init__(self, sTask, iRuleId):
        self.sTask = sTask
        self.iRuleId = iRuleId


class UpdateInfo(DaoObject):
    def __init__(self):
        self.latest_version = ""
        self.netdisk_link = ""
        self.netdisk_passcode = ""
        self.update_message = ""

    def __str__(self):
        return str(self.__dict__)


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
