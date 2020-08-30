class DnfRoleInfo:
    def __init__(self, roleid, rolename, forceid, level):
        self.roleid = int(roleid)
        self.rolename = str(rolename)
        # 已知：0-男鬼剑，3-女魔法师，13-男枪士，14-女圣职者
        self.forceid = int(forceid)
        self.level = int(level)

    def __repr__(self):
        return str(self.__dict__)


class Jx3RoleInfo:
    def __init__(self, roleid, rolename):
        self.roleid = roleid
        self.rolename = rolename

    def __repr__(self):
        return str(self.__dict__)


class Jx3GiftInfo:
    def __init__(self, sTask, iRuleId):
        self.sTask = sTask
        self.iRuleId = iRuleId


class UpdateInfo:
    def __init__(self):
        self.latest_version = ""
        self.netdisk_link = ""
        self.netdisk_passcode = ""
        self.update_message = ""

    def __str__(self):
        return str(self.__dict__)
