import re

from dao import DnfRoleInfo, Jx3RoleInfo


def parse_role_list(jsonRes):
    role_reg = r"\d+ \w+ \d+ \d+"
    rolemap = {}

    for item in jsonRes["data"].split("|"):
        if re.match(role_reg, item):
            roleid, rolename, forceid, level = item.split(" ")
            if roleid not in rolemap:
                rolemap[roleid] = DnfRoleInfo(roleid, rolename, forceid, level)

    return list(rolemap.values())


def parse_jx3_role_list(jsonRes):
    jx3_role_reg = r"\d+ \w+"
    rolemap = {}

    for item in jsonRes["data"].split("|"):
        if re.match(jx3_role_reg, item):
            item = item.strip().split(" ")
            if len(item) == 2:
                roleid, rolename = item
                if roleid not in rolemap:
                    rolemap[roleid] = Jx3RoleInfo(roleid, rolename)

    return list(rolemap.values())
