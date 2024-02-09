import json
import os

import requests

from config import config, load_config
from log import logger
from qq_login import QQLogin
from util import uin2qq


class WegameApi:
    login_url = "https://www.wegame.com.cn/api/middle/clientapi/auth/login_by_qq"
    common_url_prefix = "https://m.wegame.com.cn/api/mobile/lua/proxy/index/mwg_dnf_battle_record/"
    cached_dir = ".cached"
    cached_file = ".token.{}.json"

    def auto_login_with_password(self, common_cfg, account, password, account_name):
        cached = self.load_token(account)
        if cached is not None:
            api.set_uin_skey(cached["uin"], cached["skey"], cached["p_skey"])
            api.set_tgp_info(cached["tgp_id"], cached["tgp_ticket"])
            if self.is_token_still_valid():
                logger.info("use cached")
                return
            else:
                logger.warning("token invalided, try get new")

        ql = QQLogin(common_cfg)
        lr = ql.login(account, password, ql.login_mode_wegame, name=account_name)
        logger.info(lr)
        api.login(lr.uin, lr.skey, lr.p_skey)
        self.save_token(account)
        logger.info("new login, token saved")

    def load_token(self, account):
        if not os.path.isdir(self.cached_dir):
            return None

        if not os.path.isfile(self.get_token_file(account)):
            return None

        with open(self.get_token_file(account), encoding="utf-8") as f:
            return json.load(f)

    def save_token(self, account):
        if not os.path.isdir(self.cached_dir):
            os.mkdir(self.cached_dir)

        with open(self.get_token_file(account), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "uin": self.uin,
                    "skey": self.skey,
                    "p_skey": self.p_skey,
                    "tgp_id": self.tgp_id,
                    "tgp_ticket": self.tgp_ticket,
                },
                f,
                ensure_ascii=False,
            )

    def is_token_still_valid(self):
        res = self.get_player_role_list(print_res=False)
        return res["data"]["result"] == 0

    def get_token_file(self, account):
        return os.path.join(self.cached_dir, self.cached_file.format(account))

    def login(self, uin, skey, p_skey):
        self.set_uin_skey(skey, uin, p_skey)

        data = {
            "login_info": {
                "qq_info_type": 6,
                "uin": uin2qq(self.uin),
                "sig": self.p_skey,
                "qqinfo_ext": [
                    {
                        "qq_info_type": 3,
                        "sig": self.skey,
                    }
                ],
            },
            "config_params": {"lang_type": 0},
            "mappid": "10001",
            "mcode": "",
            "clienttype": "1000005",
        }
        headers = {
            "referer": "https://www.wegame.com.cn/middle/login/third_callback.html",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
        }
        res = requests.post(self.login_url, json=data, headers=headers, timeout=10)
        tgp_id, tgp_ticket = int(res.cookies.get("tgp_id")), res.cookies.get("tgp_ticket")
        self.set_tgp_info(tgp_id, tgp_ticket)

        logger.info(tgp_id)
        logger.info(tgp_ticket)

    def set_uin_skey(self, skey, uin, p_skey):
        self.uin = uin
        self.skey = skey
        self.p_skey = p_skey

    def set_tgp_info(self, tgp_id, tgp_ticket):
        self.tgp_id = tgp_id
        self.tgp_ticket = tgp_ticket
        # 需自行调用set_role_info设置
        self.area_id = 0
        self.role_name = ""
        self.common_headers = {
            "accept": "application/json",
            "cookie": "app_id=10001;tgp_id={tgp_id};platform=qq;account={account};skey={skey};tgp_ticket={tgp_ticket};machine_type=MIX+2;channel_number=5;app_version=1050602003;client_type=601".format(
                tgp_id=self.tgp_id,
                account=uin2qq(self.uin),
                skey=self.skey,
                tgp_ticket=self.tgp_ticket,
            ),
            "Content-Type": "application/json; charset=utf-8",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "User-Agent": "okhttp/3.11.0",
        }

    def get_player_role_list(self, print_res=True):
        """
        获取玩家所有区服的的角色列表
        """
        return self._post("get_player_role_list", need_role_info=False, print_res=print_res).json()

    def set_role_info(self, area_id, role_name):
        """
        调用下列接口前需要先调用该接口设置角色信息
        """
        self.area_id = int(area_id)
        self.role_name = str(role_name)

    def get_capacity_detail_info(self):
        """
        获取指定服务器的指定角色的战力信息
        """
        return self._post("get_capacity_detail_info").json()

    def get_player_fight_statistic_info(self):
        """
        获取指定服务器的指定角色的面板一览
        """
        return self._post("get_player_fight_statistic_info").json()

    def get_equip_description_image(self, equip_id):
        """
        获取指定装备的描述图片
        """
        return f"https://bb.img.qq.com/bbcdn/dnf/equips/equimg/{equip_id}.png"

    def get_equip_icon(self, equip_id):
        """
        获取指定装备的图标
        """
        return f"http://cdn.tgp.qq.com/DNF_picture/equip_icon/{equip_id}.png"

    def get_player_equipment_list(self):
        """
        获取指定服务器的指定角色的面板一览
        """
        return self._post("get_player_equipment_list").json()

    def get_player_role_detail(self):
        """
        获取指定服务器的指定角色的详细面板数据
        """
        return self._post("get_player_role_detail").json()

    def get_player_role_info(self, print_res=True):
        """
        获取指定服务器的指定角色的角色信息
        """
        return self._post("get_player_role_info", print_res=print_res).json()

    def get_player_recent_dungeon_list(self):
        """
        获取指定服务器的指定角色的最近副本伤害信息
        """
        role_info = api.get_player_role_info(print_res=False)
        return self._post(
            "get_player_recent_dungeon_list",
            json_data={
                "start_index": 0,
                "career": role_info["data"]["role_info"]["career"],
            },
        ).json()

    def _post(self, api_name, json_data=None, need_role_info=True, print_res=True):
        if need_role_info and len(self.role_name) == 0:
            logger.warning(
                "调用除查询角色列表外任意接口前请先调用set_role_info设置角色信息，若不知道角色信息，可以调用get_player_role_list获取角色信息"
            )
            exit(-1)

        base_json_data = {
            "target_tgpid": self.tgp_id,
            # "target_suid": "0",
            "area_id": self.area_id,
            "role": self.role_name,
            "role_name": self.role_name,
        }
        if json_data is None:
            json_data = {}
        res = requests.post(
            self.common_url_prefix + api_name,
            json={**base_json_data, **json_data},
            headers=self.common_headers,
            timeout=10,
        )

        if print_res:
            pd = json.dumps(res.json(), ensure_ascii=False, indent=2)
            logger.info(f"{api_name} \n{pd}\n")

        return res


if __name__ == "__main__":
    api = WegameApi()

    # # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()
    account = cfg.account_configs[0]
    acc = account.account_info
    api.auto_login_with_password(cfg.common, acc.account, acc.password, account.name)

    res = api.get_player_role_list()
    for idx, role in enumerate(res["data"]["role_list"]):
        logger.info(f"{str(idx):3s} 区服={role['area_id']:3d}\t角色名={role['role_name']}")
    default_role = res["data"]["role_list"][0]
    # default_role = list(filter(lambda role: role['area_id'] == 11 and role['role_name'] == "风之凌殇喵", res['data']['role_list']))[0]
    area_id, role_name = default_role["area_id"], default_role["role_name"]
    api.set_role_info(area_id, role_name)
    api.get_capacity_detail_info()
    api.get_player_fight_statistic_info()
    api.get_equip_description_image(100390332)
    api.get_equip_icon(100390332)
    api.get_player_equipment_list()
    api.get_player_role_detail()
    api.get_player_role_info()
    api.get_player_recent_dungeon_list()

    os.system("PAUSE")
