import os
import uuid
from urllib.parse import quote

from const import *
from sign import getACSRFTokenForAMS, getDjcSignParams


def getSDeviceID():
    sDeviceIdFileName = ".sDeviceID.txt"

    if os.path.isfile(sDeviceIdFileName):
        with open(sDeviceIdFileName, "r", encoding="utf-8") as file:
            sDeviceID = file.read()
            if len(sDeviceID) == 36:
                # print("use cached sDeviceID", sDeviceID)
                return sDeviceID

    sDeviceID = str(uuid.uuid1())
    # print("create new sDeviceID", sDeviceID, len(sDeviceID))

    with open(sDeviceIdFileName, "w", encoding="utf-8") as file:
        file.write(sDeviceID)

    return sDeviceID


# ------------------------------切换账号后需要手动填写的配置（具体配置方法请通过文本编辑器阅读README.MD中的使用方法章节）------------------------------
# 腾讯系网页登录通用账号凭据与token
uin = "o123456789"
skey = "@a1b2c3d4e"

# 兑换dnf道具所需的dnf区服和角色信息
iZone = "11"  # 浙江一区，其他区服id可查阅reference_data/dnf_server_list.js
rolename = quote("DNF角色名")
lRoleId = "DNF角色ID"

# 完成《礼包达人》任务所需的剑网3:指尖江湖手游的区服和角色信息
jx3_area = 2  # QQ
jx3_platid = 1  # 安卓
jx3_partition = 20001  # 手Q1区，其他区服的id可查阅reference_data/jx3_server_list.js
jx3_roleid = '指尖江湖角色ID'
jx3_rolename = quote('指尖江湖玩家名')

# ------------------------------也许不用调整的配置------------------------------
sDeviceID = getSDeviceID()

# ------------------------------根据上述内容生成的签名和token------------------------------
aes_key = "84e6c6dc0f9p4a56"
rsa_public_key_file = "public_key.der"

g_tk = str(getACSRFTokenForAMS(skey))
sDjcSign = getDjcSignParams(aes_key, rsa_public_key_file, uin[1:], sDeviceID, appVersion)
