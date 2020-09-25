import random
import re

import requests

from dao import RoleInfo
from log import logger
from network import process_result
from qq_login import LoginResult
from sign import getACSRFTokenForAMS
from urls import Urls
from util import uin2qq


class ArkLottery:
    def __init__(self, djc_helper, lr):
        """
        :type djc_helper: DjcHelper
        :type lr: LoginResult
        :type roleinfo: RoleInfo
        """
        # 即使没绑定dnf角色，也放行，方便领取分享奖励
        roleinfo = None
        try:
            if 'dnf' in djc_helper.bizcode_2_bind_role_map:
                roleinfo = djc_helper.bizcode_2_bind_role_map['dnf'].sRoleInfo
        except:
            pass
        self.roleinfo = roleinfo

        self.djc_helper = djc_helper
        self.lr = lr

        self.cfg = djc_helper.cfg

        self.g_tk = getACSRFTokenForAMS(lr.p_skey)
        self.urls = Urls()
        # 使用QQ空间登录态进行抽卡活动
        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; MIX 2 Build/PKQ1.190118.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045332 Mobile Safari/537.36 V1_AND_SQ_8.4.8_1492_YYB_D QQ/8.4.8.4810 NetType/WIFI WebP/0.3.0 Pixel/1080 StatusBarHeight/76 SimpleUISwitch/0 QQTheme/1000 InMagicWin/0",
            "Cookie": "p_uin={p_uin}; p_skey={pskey}; ".format(p_uin=self.lr.uin, pskey=self.lr.p_skey),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

    def ark_lottery(self):
        if self.roleinfo is None:
            logger.warning("未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定，否则每日登录游戏和幸运勇士的增加抽卡次数将无法成功进行。")

        # 增加次数
        self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日登陆页面", 25970)
        self.do_ark_lottery("v2/fcg_yvip_game_pull_flow", "增加抽卡次数-每日登陆游戏", 25968, query="0", act_name="act_dnf_ark9")
        self.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日分享", 25938)

        # 幸运勇士
        server_id, roleid = "", ""
        if self.cfg.ark_lottery.lucky_dnf_server_id == "":
            logger.warning("未配置抽卡的幸运勇士的区服和角色信息，将使用道聚城绑定的角色信息")
        else:
            if self.cfg.ark_lottery.lucky_dnf_role_id == "":
                logger.warning("配置了抽卡幸运勇士的区服ID为{}，但未配置角色ID，将打印该服所有角色信息如下，请将合适的角色ID填到配置表".format(self.cfg.ark_lottery.lucky_dnf_server_id))
                self.djc_helper.query_dnf_rolelist(self.cfg.ark_lottery.lucky_dnf_server_id)
            else:
                logger.info("使用配置的区服和角色信息来进行幸运勇士加次数")
                cfg = self.cfg.ark_lottery
                server_id, roleid = cfg.lucky_dnf_server_id, cfg.lucky_dnf_role_id

        self.do_ark_lottery("v2/fcg_yvip_game_pull_flow", "增加抽卡次数-幸运勇士", 25969, query="0", act_name="act_dnf_xinyun3",
                            area=server_id, partition=server_id, roleid=roleid)

        # 抽卡
        count = self.remaining_lottery_times()
        logger.info("上述操作完毕后，最新抽卡次数为{}，将全部用来抽卡".format(count))
        for idx in range(count):
            self.do_ark_lottery("fcg_qzact_lottery", "抽卡-第{}次".format(idx + 1), "25940")

        # # 领取集卡奖励
        if len(self.cfg.ark_lottery.take_awards) != 0:
            for award in self.cfg.ark_lottery.take_awards:
                for idx in range(award.count):
                    self.do_ark_lottery("fcg_receive_reward", award.name, award.ruleid, gameid="dnf")
        else:
            logger.warning("未设置领取集卡礼包奖励，也许是小号，请记得定期手动登录小号来给大号赠送缺失的卡")

        # 使用卡片抽奖-25949 # note: 为啥没传卡片id- -也许是因为还没正式开启？之后再试试
        # for idx in range(self.cfg.ark_lottery.lottery_using_cards_count):
        #     self.do_ark_lottery("fcg_prize_lottery", "消耗卡片抽奖", "25949", gameid="dnf")

        # undone: 暂时未处理：
        #  分享-发送消息
        #  赠送给他人

        #  undone: 可能会做的：
        #   根据大号缺的卡片内容，赠送给大号

    def remaining_lottery_times(self):
        res = requests.post(self.urls.ark_lottery_page, headers=self.headers)
        reg = "剩余抽卡次数：<span class=\"count\">(\d+)</span>"

        count = 0
        match = re.search(reg, res.text)
        if match is not None:
            count = int(match.group(1))

        return count

    def do_ark_lottery(self, api, ctx, ruleid, query="", act_name="", gameid="", area="", partition="", roleid="", pretty=False, print_res=True):
        url = self.urls.ark_lottery.format(
            api=api,
            g_tk=self.g_tk,
            rand=random.random(),
        )
        if self.roleinfo is not None:
            area = area or self.roleinfo.serviceID
            partition = partition or self.roleinfo.serviceID
            roleid = roleid or self.roleinfo.roleCode

        raw_data = self.urls.ark_lottery_raw_data.format(
            actid=3886,
            ruleid=ruleid,
            area=area,
            partition=partition,
            roleid=roleid,
            query=query,
            act_name=act_name,
            gameid=gameid,
            uin=uin2qq(self.lr.uin),
        )

        res = requests.post(url, raw_data, headers=self.headers)
        return process_result(ctx, res, pretty, print_res)
