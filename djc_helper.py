import platform
import random
import string
import subprocess
import webbrowser
from sys import exit
from urllib.parse import quote_plus

import pyperclip
import win32api

import json_parser
from ark_lottery import ArkLottery
from dao import *
from game_info import get_game_info, get_game_info_by_bizcode
from network import *
from qq_login import QQLogin, LoginResult
from sign import getMillSecondsUnix
from urls import Urls
from util import show_head_line, get_this_week_monday


# DNF蚊子腿小助手
class DjcHelper:
    first_run_flag_file = os.path.join(first_run_dir, "init")
    first_run_auto_login_mode_flag_file = os.path.join(first_run_dir, "auto_login_mode")
    first_run_promot_flag_file = os.path.join(first_run_dir, "promot")
    first_run_document_flag_file = os.path.join(first_run_dir, "document")
    first_run_use_old_config_flag_file = os.path.join(first_run_dir, "use_old_config")

    local_saved_skey_file = os.path.join(cached_dir, ".saved_skey.{}.json")
    local_saved_pskey_file = os.path.join(cached_dir, ".saved_pskey.{}.json")
    local_saved_guanjia_openid_file = os.path.join(cached_dir, ".saved_guanjia_openid.{}.json")

    local_saved_teamid_file = os.path.join(db_dir, ".teamid.{}.json")

    def __init__(self, account_config, common_config):
        self.cfg = account_config  # type: AccountConfig
        self.common_cfg = common_config  # type: CommonConfig

        # 配置加载后，尝试读取本地缓存的skey
        self.local_load_uin_skey()

        # 初始化网络相关设置
        self.init_network()

        # 相关链接
        self.urls = Urls()

    # --------------------------------------------一些辅助函数--------------------------------------------

    def init_network(self):
        self.network = Network(self.cfg.sDeviceID, self.cfg.account_info.uin, self.cfg.account_info.skey, self.common_cfg)

    def show_tip_on_first_run_any(self):
        filename = self.first_run_flag_file
        title = "使用须知"
        tips = """# 『重要』与个人隐私有关的skey相关说明
        1. skey是腾讯系应用的通用鉴权票据，个中风险，请Google搜索《腾讯skey》后自行评估
        2. skey有过期时间，目前根据测试来看应该是一天。目前已实现手动登录、扫码登录（默认）、自动登录。手动登录需要自行在网页中登录并获取skey填写到配置表。扫码登录则会在每次过期时打开网页让你签到，无需手动填写。自动登录则设置过一次账号密码后续无需再操作。
        3. 本脚本仅使用skey进行必要操作，用以实现自动化查询、签到、领奖和兑换等逻辑，不会上传到与此无关的网站，请自行阅读源码进行审阅
        4. 如果感觉有风险，请及时停止使用本软件，避免后续问题
                """
        loginfo = "首次运行，弹出使用须知"

        self.show_tip_on_first_run(filename, title, tips, loginfo)

    def show_tip_on_first_run_auto_login_mode(self):
        filename = self.first_run_auto_login_mode_flag_file
        title = "自动登录须知"
        tips = """自动登录需要在本地配置文件明文保存账号和密码，利弊如下，请仔细权衡后再决定是否适用
        弊：
            1. 需要填写账号和密码，有潜在泄漏风险
            2. 需要明文保存到本地，可能被他人窥伺
            3. 涉及账号密码，总之很危险<_<
        利：
            1. 无需手动操作，一劳永逸
            
        若觉得有任何不妥，强烈建议改回其他需要手动操作的登录模式
                """
        loginfo = "首次运行自动登录模式，弹出利弊分析"

        self.show_tip_on_first_run(filename, title, tips, loginfo, show_count=3)

    def show_tip_on_first_run_promot(self):
        filename = self.first_run_promot_flag_file
        title = "宣传"
        tips = """
        如果觉得好用的话，可否帮忙宣传一下哈(*^▽^*)
        或者扫描二维码打赏一下也是极好的φ(>ω<*) 
                """
        loginfo = "首次运行弹出宣传弹窗"

        self.show_tip_on_first_run(filename, title, tips, loginfo)

    def show_tip_on_first_run_document(self):
        filename = self.first_run_document_flag_file
        title = "引导查看相关教程"
        tips = """
        如果使用过程中有任何疑惑，或者相关功能想要调整，都请先好好看看以下现有资源后再来提问~（如不想完整查看对应文档，请善用搜索功能，查找可能的关键词）
            1. 使用教程/使用文档.docx
            2. 使用教程/道聚城自动化助手使用视频教程.url
            3. config.toml以及config.toml.example中各个配置项说明
                """
        loginfo = "首次运行弹出提示查看教程"

        self.show_tip_on_first_run(filename, title, tips, loginfo, show_count=3)

    def show_tip_on_first_run_use_old_config(self):
        filename = self.first_run_use_old_config_flag_file
        title = "继承配置"
        tips = """
        如果是从旧版本升级过来的，则不需要再完整走一遍配置流程，直接将旧版本目录中的config.toml文件复制过来，替换新版本的这个文件就行。
        新版本可能新增一些配置，可查看更新日志或者自行对比新旧版本配置文件。如果未配置，则会使用设定的默认配置。
        更多信息可查看使用教程/使用文档.docx中背景知识章节中关于继承存档的描述
                """
        loginfo = "首次运行弹出提示继承以前配置"

        self.show_tip_on_first_run(filename, title, tips, loginfo)

    def show_tip_on_first_run(self, filename, title, tips, loginfo, show_count=1):
        if os.path.isfile(filename):
            return

        # 仅在window系统下检查
        if platform.system() != "Windows":
            return

        # 若不存在该文件，则说明是首次运行，提示相关信息
        logger.info(loginfo)

        for i in range(show_count):
            _title = title
            if show_count != 1:
                _title = "第{}/{}次提示 {}".format(i + 1, show_count, title)
            win32api.MessageBox(0, tips, _title, win32con.MB_ICONWARNING)

        # 创建该文件，从而避免再次弹出错误
        with open(filename, "w", encoding="utf-8") as f:
            f.write("ok")

    def check_skey_expired(self):
        query_data = self.query_balance("判断skey是否过期", print_res=False)
        if str(query_data['ret']) == "0":
            # skey尚未过期
            return

        # 更新skey
        logger.info("")
        logger.warning("账号({})的skey已过期，即将尝试更新skey".format(self.cfg.name))
        self.update_skey(query_data)

    def update_skey(self, query_data):
        login_mode_dict = {
            "by_hand": self.update_skey_by_hand,
            "qr_login": self.update_skey_qr_login,
            "auto_login": self.update_skey_auto_login,
        }
        login_mode_dict[self.cfg.login_mode](query_data)

    def update_skey_by_hand(self, query_data):
        js_code = """cookies=Object.fromEntries(document.cookie.split(/; */).map(cookie => cookie.split('=', 2)));console.log("uin="+cookies.uin+"\\nskey="+cookies.skey+"\\n");"""
        fallback_js_code = """document.cookie.split(/; */);"""
        logger.error((
                         "skey过期，请按下列步骤获取最新skey并更新到配置中\n"
                         "1. 在本脚本自动打开的活动网页中使用通用登录组件完成登录操作\n"
                         "   1.1 指点击（亲爱的玩家，请【登录】）中的登录按钮，并完成后续登录操作\n"
                         "2. 点击F12，将默认打开DevTools（开发者工具界面）的Console界面\n"
                         "       如果默认不是该界面，则点击上方第二个tab（Console）（中文版这个tab的名称可能是命令行？）\n"
                         "3. 在下方输入区输入下列内容来从cookie中获取uin和skey（或者直接粘贴，默认已复制到系统剪贴板里了）\n"
                         "       {js_code}\n"
                         "-- 如果上述代码执行报错，可能是因为浏览器不支持，这时候可以复制下面的代码进行上述操作\n"
                         "  执行后，应该会显示一个可点开的内容，戳一下会显示各个cookie的内容，然后手动在里面查找uin和skey即可\n"
                         "       {fallback_js_code}\n"
                         "3. 将uin/skey的值分别填写到config.toml中对应配置的值中即可\n"
                         "4. 填写dnf的区服和手游的区服信息到config.toml中\n"
                         "5. 正常使用还需要填写完成后再次运行脚本，获得角色相关信息，并将信息填入到config.toml中\n"
                         "\n"
                         "具体信息为：ret={ret} msg={msg}"
                     ).format(js_code=js_code, fallback_js_code=fallback_js_code, ret=query_data['ret'], msg=query_data['msg']))
        # 打开配置界面
        cfgFile = "./config.toml"
        localCfgFile = "./config.toml.local"
        if os.path.isfile(localCfgFile):
            cfgFile = localCfgFile
        subprocess.Popen("npp_portable/notepad++.exe -n53 {}".format(cfgFile))
        # 复制js代码到剪贴板，方便复制
        pyperclip.copy(js_code)
        # 打开活动界面
        os.popen("start https://dnf.qq.com/lbact/a20200716wgmhz/index.html?wg_ad_from=loginfloatad")
        # 提示
        input("\n完成上述操作后点击回车键即可退出程序，重新运行即可...")
        exit(-1)

    def update_skey_qr_login(self, query_data):
        qqLogin = QQLogin(self.common_cfg)
        loginResult = qqLogin.qr_login()
        self.save_uin_skey(loginResult.uin, loginResult.skey, loginResult.vuserid)

    def update_skey_auto_login(self, query_data):
        self.show_tip_on_first_run_auto_login_mode()

        qqLogin = QQLogin(self.common_cfg)
        ai = self.cfg.account_info
        loginResult = qqLogin.login(ai.account, ai.password)
        self.save_uin_skey(loginResult.uin, loginResult.skey, loginResult.vuserid)

    def save_uin_skey(self, uin, skey, vuserid):
        self.memory_save_uin_skey(uin, skey)

        self.local_save_uin_skey(uin, skey, vuserid)

    def local_save_uin_skey(self, uin, skey, vuserid):
        # 本地缓存
        self.vuserid = vuserid
        with open(self.get_local_saved_skey_file(), "w", encoding="utf-8") as sf:
            loginResult = {
                "uin": str(uin),
                "skey": str(skey),
                "vuserid": str(vuserid),
            }
            json.dump(loginResult, sf)
            logger.debug("本地保存skey信息，具体内容如下：{}".format(loginResult))

    def local_load_uin_skey(self):
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_skey_file()):
            return

        with open(self.get_local_saved_skey_file(), "r", encoding="utf-8") as f:
            loginResult = json.load(f)
            self.memory_save_uin_skey(loginResult["uin"], loginResult["skey"])
            self.vuserid = loginResult.get("vuserid", "")
            logger.debug("读取本地缓存的skey信息，具体内容如下：{}".format(loginResult))

    def get_local_saved_skey_file(self):
        return self.local_saved_skey_file.format(self.cfg.name)

    def memory_save_uin_skey(self, uin, skey):
        # 保存到内存中
        self.cfg.updateUinSkey(uin, skey)

        # uin, skey更新后重新初始化网络相关
        self.init_network()

    # --------------------------------------------获取角色信息和游戏信息--------------------------------------------

    def get_bind_role_list(self, print_warning=True):
        # 查询全部绑定角色信息
        res = self.get("获取道聚城各游戏的绑定角色列表", self.urls.query_bind_role_list, print_res=False)
        self.bizcode_2_bind_role_map = {}
        for roleinfo_dict in res["data"]:
            role_info = GameRoleInfo()
            role_info.auto_update_config(roleinfo_dict)
            self.bizcode_2_bind_role_map[role_info.sBizCode] = role_info

    def get_mobile_game_info(self):
        # 如果游戏名称设置为【任意手游】，则从绑定的手游中随便挑一个
        if self.cfg.mobile_game_role_info.use_any_binded_mobile_game():
            found_binded_game = False
            for bizcode, bind_role_info in self.bizcode_2_bind_role_map.items():
                if bind_role_info.is_mobile_game():
                    self.cfg.mobile_game_role_info.game_name = bind_role_info.sRoleInfo.gameName
                    found_binded_game = True
                    logger.warning("当前游戏名称配置为任意手游，将从道聚城已绑定的手游中随便选一个，挑选为：{}".format(self.cfg.mobile_game_role_info.game_name))
                    break

            if not found_binded_game:
                return None

        return get_game_info(self.cfg.mobile_game_role_info.game_name)

    # --------------------------------------------各种操作--------------------------------------------
    def run(self):
        self.normal_run()

    def check_first_run(self):
        self.show_tip_on_first_run_promot()
        self.show_tip_on_first_run_any()
        self.show_tip_on_first_run_document()
        self.show_tip_on_first_run_use_old_config()

    # 预处理阶段
    def check_djc_role_binding(self) -> bool:
        self.check_first_run()

        # 指引获取uin/skey/角色信息等
        self.check_skey_expired()

        # 尝试获取绑定的角色信息
        self.get_bind_role_list()

        # 检查绑定信息
        binded = True
        if self.cfg.function_switches.get_djc:
            # 检查道聚城是否已绑定dnf角色信息，若未绑定则警告（这里不停止运行是因为可以不配置领取dnf的道具）
            if not self.cfg.cannot_band_dnf and "dnf" not in self.bizcode_2_bind_role_map:
                logger.warning(color("fg_bold_yellow") + "未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定")
                binded = False

            if self.cfg.mobile_game_role_info.enabled() and not self.check_mobile_game_bind():
                binded = False

        if binded:
            # 打印dnf和手游的绑定角色信息
            logger.info("已获取道聚城目前绑定的角色信息如下")
            games = []
            if "dnf" in self.bizcode_2_bind_role_map:
                games.append("dnf")
            if self.cfg.mobile_game_role_info.enabled():
                games.append(self.get_mobile_game_info().bizCode)

            for bizcode in games:
                roleinfo = self.bizcode_2_bind_role_map[bizcode].sRoleInfo
                logger.info("{game}: ({server}-{name}-{id})".format(
                    game=roleinfo.gameName, server=roleinfo.serviceName, name=roleinfo.roleName, id=roleinfo.roleCode,
                ))

        return binded

    def check_mobile_game_bind(self):
        # 检查配置的手游是否有效
        gameinfo = self.get_mobile_game_info()
        if gameinfo is None:
            logger.warning(color("fg_bold_yellow") + "当前游戏名称配置为【任意手游】，但未在道聚城找到任何绑定的手游，请前往道聚城绑定任意一个手游，如王者荣耀")
            return False

        # 检查道聚城是否已绑定该手游的角色，若未绑定则警告并停止运行
        bizcode = gameinfo.bizCode
        if bizcode not in self.bizcode_2_bind_role_map:
            logger.warning(color("fg_bold_yellow") + "未在道聚城绑定【{}】的角色信息，请前往道聚城app进行绑定。".format(get_game_info_by_bizcode(bizcode).bizName))
            logger.warning(color("fg_bold_cyan") + "若想绑定其他手游则调整config.toml配置中的手游名称，" + color("fg_bold_blue") + "若不启用则将手游名称调整为无")
            return False

        # 检查这个游戏是否是手游
        role_info = self.bizcode_2_bind_role_map[bizcode]
        if not role_info.is_mobile_game():
            logger.warning(color("fg_bold_yellow") + "【{}】是端游，不是手游。".format(get_game_info_by_bizcode(bizcode).bizName))
            logger.warning(color("fg_bold_cyan") + "若想绑定其他手游则调整config.toml配置中的手游名称，" + color("fg_bold_blue") + "若不启用则将手游名称调整为无")
            return False

        return True

    # 正式运行阶段
    def normal_run(self):
        # 检查skey是否过期
        self.check_skey_expired()

        # 获取dnf和手游的绑定信息
        self.get_bind_role_list()

        # 执行道聚城相关操作
        self.djc_operations()

        # 执行心悦相关操作
        # DNF地下城与勇士心悦特权专区
        self.xinyue_operations()

        # 黑钻礼包
        self.get_heizuan_gift()

        # 腾讯游戏信用相关礼包
        self.get_credit_xinyue_gift()

        # QQ空间抽卡
        self.ark_lottery()

        # wegame国庆活动【秋风送爽关怀常伴】
        self.wegame_guoqing()

        # 阿拉德集合站活动合集
        self.dnf_922()

        # 10月女法师三觉
        self.dnf_female_mage_awaken()

        # 微信签到
        self.wx_checkin()

    # -- 已过期的一些活动
    def expired_activities(self):
        # 心悦国庆活动【DNF金秋送福心悦有礼】
        self.xinyue_guoqing()

        # 2020DNF闪光杯返场赛
        self.dnf_shanguang()

        # qq视频活动
        self.qq_video()

        # 管家蚊子腿
        self.guanjia()

    # --------------------------------------------道聚城--------------------------------------------
    def djc_operations(self):
        show_head_line("开始道聚城相关操作")

        if not self.cfg.function_switches.get_djc:
            logger.warning("未启用领取道聚城功能，将跳过")
            return

        # ------------------------------初始工作------------------------------
        old_info = self.query_balance("1. 操作前：查询余额")["data"]
        old_allin, old_balance = int(old_info['allin']), int(old_info['balance'])
        # self.query_money_flow("1.1 操作前：查一遍流水")

        # ------------------------------核心逻辑------------------------------
        # 自动签到
        self.sign_in_and_take_awards()

        # 完成任务
        self.complete_tasks()

        # 领取奖励并兑换道具
        self.take_task_awards_and_exchange_items()

        # ------------------------------清理工作------------------------------
        new_info = self.query_balance("5. 操作全部完成后：查询余额")["data"]
        new_allin, new_balance = int(new_info['allin']), int(new_info['balance'])
        # self.query_money_flow("5.1 操作全部完成后：查一遍流水")

        delta = new_allin - old_allin
        logger.warning(color("fg_bold_yellow") + "账号 {} 本次道聚城操作共获得 {} 个豆子（历史总获取： {} -> {}  余额： {} -> {} ）".format(self.cfg.name, delta, old_allin, new_allin, old_balance, new_balance))

    def query_balance(self, ctx, print_res=True):
        return self.get(ctx, self.urls.balance, print_res=print_res)

    def query_money_flow(self, ctx):
        return self.get(ctx, self.urls.money_flow)

    def sign_in_and_take_awards(self):
        # 发送登录事件，否则无法领取签到赠送的聚豆，报：对不起，请在掌上道聚城app内进行签到
        self.get("2.1.1 发送imsdk登录事件", self.urls.imsdk_login)
        self.get("2.1.2 发送app登录事件", self.urls.user_login_event)
        # 签到
        self.post("2.2 签到", self.urls.sign, self.sign_flow_data("96939"))
        # 领取本日签到赠送的聚豆
        self.post("2.3 领取签到赠送的聚豆", self.urls.sign, self.sign_flow_data("324410"))

        # 尝试领取自动签到的奖励
        # 查询本月签到的日期列表
        signinDates = self.post("2.3.1 查询签到日期列表", self.urls.sign, self.sign_flow_data("96938"), print_res=False)
        month_total_signed_days = len(signinDates["modRet"]["data"])
        # 根据本月已签到数，领取符合条件的每月签到若干日的奖励（也就是聚豆页面最上面的那个横条）
        for sign_reward_rule in self.get("2.3.2 查询连续签到奖励规则", self.urls.sign_reward_rule, print_res=False)["data"]:
            if sign_reward_rule["iCanUse"] == 1 and month_total_signed_days >= int(sign_reward_rule["iDays"]):
                ctx = "2.3.3 领取连续签到{}天奖励".format(sign_reward_rule["iDays"])
                self.post(ctx, self.urls.sign, self.sign_flow_data(str(sign_reward_rule["iFlowId"])))

    def sign_flow_data(self, iFlowId):
        return self.format(self.urls.sign_raw_data, iFlowId=iFlowId)

    def complete_tasks(self):
        # 完成《绝不错亿》
        self.get("3.1 模拟点开活动中心", self.urls.task_report, task_type="activity_center")

        if self.cfg.mobile_game_role_info.enabled():
            # 完成《礼包达人》
            self.take_mobile_game_gift()
        else:
            logger.info("未启用自动完成《礼包达人》任务功能")

        if self.cfg.function_switches.make_wish:
            # 完成《有理想》
            self.make_wish()
        else:
            logger.info("未启用自动完成《有理想》任务功能")

    def take_mobile_game_gift(self):
        game_info = self.get_mobile_game_info()
        role_info = self.bizcode_2_bind_role_map[game_info.bizCode].sRoleInfo

        giftInfos = self.get_mobile_game_gifts()
        if len(giftInfos) == 0:
            logger.warning("未找到手游【{}】的有效七日签到配置，请换个手游，比如王者荣耀".format(game_info.bizName))
            return

        dayIndex = datetime.datetime.now().weekday()  # 0-周一...6-周日，恰好跟下标对应
        giftInfo = giftInfos[dayIndex]

        self.get("3.2 一键领取{}日常礼包-{}".format(role_info.gameName, giftInfo.sTask), self.urls.recieve_game_gift,
                 bizcode=game_info.bizCode, iruleId=giftInfo.iRuleId,
                 systemID=role_info.systemID, sPartition=role_info.areaID, channelID=role_info.channelID, channelKey=role_info.channelKey,
                 roleCode=role_info.roleCode, sRoleName=role_info.roleName)

    def make_wish(self):
        bizCode = "yxzj"
        if bizCode not in self.bizcode_2_bind_role_map:
            logger.warning(color("fg_bold_cyan") + "未在道聚城绑定王者荣耀，将跳过许愿功能。建议使用安卓模拟器下载道聚城，在上面绑定王者荣耀")
            return

        roleModel = self.bizcode_2_bind_role_map[bizCode].sRoleInfo
        if '苹果' in roleModel.channelKey:
            logger.warning(color("fg_bold_cyan") + "ios端不能许愿手游，建议使用安卓模拟器下载道聚城，在上面绑定王者荣耀。roleModel={}".format(roleModel))
            return

        # 查询许愿道具信息
        query_wish_item_list_res = self.get("3.3.0  查询许愿道具", self.urls.query_wish_goods_list, plat=roleModel.systemID, biz=roleModel.bizCode, print_res=False)
        if "data" not in query_wish_item_list_res or len(query_wish_item_list_res["data"]) == 0:
            logger.warning("在{}上游戏【{}】暂不支持许愿，query_wish_item_list_res={}".format(roleModel.systemKey, roleModel.gameName, query_wish_item_list_res))
            return

        propModel = GoodsInfo()
        propModel.auto_update_config(query_wish_item_list_res["data"]["goods"][0])

        # 查询许愿列表
        wish_list_res = self.get("3.3.1 查询许愿列表", self.urls.query_wish, appUid=uin2qq(self.cfg.account_info.uin))

        # 删除已经许愿的列表，确保许愿成功
        for wish_info in wish_list_res["data"]["list"]:
            ctx = "3.3.2 删除已有许愿-{}-{}".format(wish_info["bizName"], wish_info["sGoodsName"])
            self.get(ctx, self.urls.delete_wish, sKeyId=wish_info["sKeyId"])

        # 许愿
        param = {
            "iActionId": propModel.type,
            "iGoodsId": propModel.valiDate[0].code,
            "sBizCode": roleModel.bizCode,
        }
        if roleModel.type == "0":
            # 端游
            if roleModel.serviceID != "":
                param["iZoneId"] = roleModel.serviceID
            else:
                param["iZoneId"] = roleModel.areaID
            param['sZoneDesc'] = quote_plus(roleModel.serviceName)
        else:
            # 手游
            if roleModel.serviceID != "" and roleModel.serviceID != "0":
                param['partition'] = roleModel.serviceID
            elif roleModel.areaID != "" and roleModel.areaID != "0":
                param['partition'] = roleModel.areaID
            param['iZoneId'] = roleModel.channelID
            if int(roleModel.systemID) < 0:
                param['platid'] = 0
            else:
                param['platid'] = roleModel.systemID
            param['sZoneDesc'] = quote_plus(roleModel.serviceName)

        if roleModel.bizCode == 'lol' and roleModel.accountId != "":
            param['sRoleId'] = roleModel.accountId
        else:
            param['sRoleId'] = roleModel.roleCode

        param['sRoleName'] = quote_plus(roleModel.roleName)
        param['sGetterDream'] = quote_plus("不要888！不要488！9.98带回家")

        wish_res = self.get("3.3.3 完成许愿任务", self.urls.make_wish, **param)
        # 检查是否不支持许愿
        # {"ret": "-8735", "msg": "该业务暂未开放许愿", "sandbox": false, "serverTime": 1601375249, "event_id": "DJC-DJ-0929182729-P8DDy9-3-534144", "data": []}
        if wish_res["ret"] == "-8735":
            logger.warning("游戏【{}】暂未开放许愿，请换个道聚城许愿界面中支持的游戏来进行许愿哦，比如王者荣耀~".format(roleModel.gameName))

    def take_task_awards_and_exchange_items(self):
        # 领取奖励
        # 领取《礼包达人》
        self.take_task_award("4.1.1", "100066", "礼包达人")
        # 领取《绝不错亿》
        self.take_task_award("4.1.2", "100040", "绝不错亿")
        # 领取《有理想》
        self.take_task_award("4.1.3", "302124", "有理想")
        # 领取《活跃度银宝箱》
        self.take_task_award("4.1.4", "100001", "活跃度银宝箱")
        # 领取《活跃度金宝箱》
        self.take_task_award("4.1.5", "100002", "活跃度金宝箱")

        # 兑换所需道具
        self.exchange_items()

        # 领取《兑换有礼》
        self.take_task_award("4.3.1", "327091", "兑换有礼")

    def take_task_award(self, prefix, iRuleId, taskName=""):
        ctx = "{} 查询当前任务状态".format(prefix)
        taskinfo = self.get(ctx, self.urls.usertask, print_res=False)

        if self.can_take_task_award(taskinfo, iRuleId):
            ctx = "{} 领取任务-{}-奖励".format(prefix, taskName)
            self.get(ctx, self.urls.take_task_reward, iruleId=iRuleId)

    # 尝试领取每日任务奖励
    def can_take_task_award(self, taskinfo, iRuleId):
        opt_tasks = taskinfo["data"]["list"]["day"].copy()
        for id, task in taskinfo["data"]["chest_list"].items():
            opt_tasks.append(task)
        for tinfo in opt_tasks:
            if int(iRuleId) == int(tinfo["iruleId"]):
                return int(tinfo["iCurrentNum"]) >= int(tinfo["iCompleteNum"])

        return False

    def exchange_items(self):
        if len(self.cfg.exchange_items) == 0:
            logger.warning("未配置dnf的兑换道具，跳过该流程")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，却配置了兑换dnf道具，请移除配置或前往绑定")
            return

        retryCfg = self.common_cfg.retry
        for ei in self.cfg.exchange_items:
            for i in range(ei.count):
                for try_index in range(retryCfg.max_retry_count):
                    res = self.exchange_item("4.2 兑换 {}".format(ei.sGoodsName), ei.iGoodsId)
                    if int(res.get('ret', '0')) == -9905:
                        logger.warning("兑换 {} 时提示 {} ，等待{}s后重试（{}/{})".format(ei.sGoodsName, res.get('msg'), retryCfg.retry_wait_time, try_index + 1, retryCfg.max_retry_count))
                        time.sleep(retryCfg.retry_wait_time)
                        continue

                    logger.debug("领取 {} ok，等待{}s，避免请求过快报错".format(ei.sGoodsName, retryCfg.request_wait_time))
                    time.sleep(retryCfg.request_wait_time)
                    break

    def exchange_item(self, ctx, iGoodsSeqId):
        roleinfo = self.bizcode_2_bind_role_map["dnf"].sRoleInfo
        return self.get(ctx, self.urls.exchangeItems, iGoodsSeqId=iGoodsSeqId, rolename=roleinfo.roleName, lRoleId=roleinfo.roleCode, iZone=roleinfo.serviceID)

    def query_all_extra_info(self, dnfServerId):
        """
        已废弃，不再需要手动查询该信息
        """
        # 获取玩家的dnf角色列表
        self.query_dnf_rolelist(dnfServerId)
        # 获取玩家的手游角色列表
        self.query_mobile_game_rolelist()

        # # 显示所有可以兑换的道具列表，note：当不知道id时调用
        # self.query_dnf_gifts()

    def query_dnf_rolelist(self, dnfServerId):
        ctx = "获取账号({})的dnf角色列表".format(self.cfg.name)
        game_info = get_game_info("地下城与勇士")
        roleListJsonRes = self.get(ctx, self.urls.get_game_role_list, game=game_info.gameCode, sAMSTargetAppId=game_info.wxAppid, area=dnfServerId, platid="", partition="", is_jsonp=True, print_res=False)
        roleLists = json_parser.parse_role_list(roleListJsonRes)
        lines = []
        lines.append("")
        lines.append("+" * 40)
        lines.append(ctx)
        if len(roleLists) != 0:
            for idx, role in enumerate(roleLists):
                lines.append("\t第{:2d}个角色信息：\tid = {}\t 名字 = {}".format(idx + 1, role.roleid, role.rolename))
        else:
            lines.append("\t未查到dnf服务器id={}上的角色信息，请确认服务器id已填写正确或者在对应区服已创建角色".format(dnfServerId))
            lines.append("\t区服id可查看稍后打开的reference_data/dnf_server_list.js，详情参见config.toml的对应注释")
            lines.append("\t区服(partition)的id可运行程序在自动打开的reference_data/dnf_server_list或手动打开这个文件， 查看 STD_DATA中对应区服的v")
            subprocess.Popen("npp_portable/notepad++.exe reference_data/dnf_server_list.js")
        lines.append("+" * 40)
        logger.info("\n".join(lines))

    def query_mobile_game_rolelist(self):
        """
        已废弃，不再需要手动查询该信息
        """
        cfg = self.cfg.mobile_game_role_info
        game_info = self.get_mobile_game_info()
        ctx = "获取账号({})的{}角色列表".format(self.cfg.name, cfg.game_name)
        if not cfg.enabled():
            logger.info("未启用自动完成《礼包达人》任务功能")
            return

        roleListJsonRes = self.get(ctx, self.urls.get_game_role_list, game=game_info.gameCode, sAMSTargetAppId=game_info.wxAppid, area=cfg.area, platid=cfg.platid, partition=cfg.partition, is_jsonp=True, print_res=False)
        roleList = json_parser.parse_mobile_game_role_list(roleListJsonRes)
        lines = []
        lines.append("")
        lines.append("+" * 40)
        lines.append(ctx)
        if len(roleList) != 0:
            for idx, role in enumerate(roleList):
                lines.append("\t第{:2d}个角色信息：\tid = {}\t 名字 = {}".format(idx + 1, role.roleid, role.rolename))
        else:
            lines.append("\t未查到{} 平台={} 渠道={} 区服={}上的角色信息，请确认这些信息已填写正确或者在对应区服已创建角色".format(cfg.game_name, cfg.platid, cfg.area, cfg.partition))
            lines.append("\t上述id的列表可查阅稍后自动打开的server_list_{bizName}.js，详情参见config.toml的对应注释".format(bizName=game_info.bizName))
            lines.append("\t渠道(area)的id可运行程序在自动打开的reference_data/server_list_{bizName}.js或手动打开这个文件， 查看 STD_CHANNEL_DATA中对应渠道的v".format(bizName=game_info.bizName))
            lines.append("\t平台(platid)的id可运行程序在自动打开的reference_data/server_list_{bizName}.js或手动打开这个文件， 查看 STD_SYSTEM_DATA中对应平台的v".format(bizName=game_info.bizName))
            lines.append("\t区服(partition)的id可运行程序在自动打开的reference_data/server_list_{bizName}.js或手动打开这个文件， 查看 STD_DATA中对应区服的v".format(bizName=game_info.bizName))
            self.open_mobile_game_server_list()
        lines.append("+" * 40)
        logger.info("\n".join(lines))

    def open_mobile_game_server_list(self):
        game_info = self.get_mobile_game_info()
        res = requests.get(self.urls.query_game_server_list.format(bizcode=game_info.bizCode))
        server_list_file = "reference_data/server_list_{bizName}.js".format(bizName=game_info.bizName)
        with open(server_list_file, 'w', encoding='utf-8') as f:
            f.write(res.text)
        subprocess.Popen("npp_portable/notepad++.exe {}".format(server_list_file))

    def query_dnf_gifts(self):
        self.get("查询可兑换道具列表", self.urls.show_exchange_item_list)

    def get_mobile_game_gifts(self):
        game_info = self.get_mobile_game_info()
        data = self.get("查询{}礼包信息".format(game_info), self.urls.query_game_gift_bags, bizcode=game_info.bizCode, print_res=False)

        sign_in_gifts = []
        for raw_gift in data["data"]["list"]["data"]:
            # iCategory 0-普通礼包 1- 签到礼包 2 -等级礼包  3-登录礼包 4- 任务礼包 5-新版本福利 6-新手礼包 7-道聚城专属礼包 9-抽奖礼包 10-新版签到礼包（支持聚豆补签、严格对应周一到周日）11-好友助力礼包 12-预约中的礼包 13-上线后的礼包
            if int(raw_gift["iCategory"]) == 10:
                sign_in_gifts.append(raw_gift)
        sign_in_gifts.sort(key=lambda gift: gift["iSort"])

        gifts = []
        for gift in sign_in_gifts:
            gifts.append(MobileGameGiftInfo(gift["sTask"], gift["iruleId"]))
        return gifts

    # --------------------------------------------心悦dnf游戏特权--------------------------------------------
    def xinyue_operations(self):
        """
        https://xinyue.qq.com/act/a20181101rights/index.html
        根据配置进行心悦相关操作
        具体活动信息可以查阅reference_data/心悦活动备注.txt
        """
        show_head_line("DNF地下城与勇士心悦特权专区")

        if not self.cfg.function_switches.get_xinyue:
            logger.warning("未启用领取心悦特权专区功能，将跳过")
            return

        if len(self.cfg.xinyue_operations) == 0:
            logger.warning("未设置心悦相关操作信息，将跳过")
            return

        # 查询道具信息
        old_itemInfo = self.query_xinyue_items("6.1.0 操作前查询各种道具信息")
        logger.info("查询到的心悦道具信息为：{}".format(old_itemInfo))

        # 查询成就点信息
        old_info = self.query_xinyue_info("6.1 操作前查询成就点信息")

        # 查询白名单
        is_white_list = self.query_xinyue_whitelist("6.2 查询心悦白名单")

        # 尝试根据心悦级别领取对应周期礼包
        if old_info.xytype < 5:
            # 513581	Y600周礼包_特邀会员
            # 673270	月礼包_特邀会员_20200610后使用
            week_month_gifts = [("513581", "Y600周礼包_特邀会员"), ("673270", "月礼包_特邀会员_20200610后使用")]
        else:
            if is_white_list:
                # 673262	周礼包_白名单用户
                # 673264	月礼包_白名单用户
                week_month_gifts = [("673262", "周礼包_白名单用户"), ("673264", "月礼包_白名单用户")]
            else:
                # 513573	Y600周礼包
                # 673269	月礼包_20200610后使用
                week_month_gifts = [("513573", "Y600周礼包"), ("673269", "月礼包_20200610后使用")]

        # 513585	累计宝箱
        week_month_gifts.append(("513585", "累计宝箱"))

        xinyue_operations = []
        for gift in week_month_gifts:
            op = XinYueOperationConfig()
            op.iFlowId, op.sFlowName = gift
            op.count = 1
            xinyue_operations.append(op)

        # 加上其他的配置
        xinyue_operations.extend(self.cfg.xinyue_operations)

        # 进行相应的心悦操作
        for op in xinyue_operations:
            self.do_xinyue_op(old_info.xytype, op)

        # 查询道具信息
        new_itemInfo = self.query_xinyue_items("6.3.0 操作完成后查询各种道具信息")
        logger.info("查询到的心悦道具信息为：{}".format(new_itemInfo))

        # 再次查询成就点信息，展示本次操作得到的数目
        new_info = self.query_xinyue_info("6.3 操作完成后查询成就点信息")
        delta = new_info.score - old_info.score
        logger.warning(color("fg_bold_yellow") + "账号 {} 本次心悦相关操作共获得 {} 个成就点（ {} -> {} ）".format(self.cfg.name, delta, old_info.score, new_info.score))

        # 查询下心悦组队进度
        teaminfo = self.query_xinyue_teaminfo(print_res=False)
        if teaminfo.id != "":
            logger.warning(color("fg_bold_yellow") + "账号 {} 当前队伍进度为 {}/20".format(self.cfg.name, teaminfo.score))
        else:
            logger.warning(color("fg_bold_yellow") + "账号 {} 当前尚无有效心悦队伍，可考虑加入或查看文档使用本地心悦组队功能".format(self.cfg.name))

    def do_xinyue_op(self, xytype, op):
        """
        执行具体的心悦操作
        :type op: XinYueOperationConfig
        """
        retryCfg = self.common_cfg.retry
        now = datetime.datetime.now()
        current_hour = now.hour
        required_hour = self.common_cfg.xinyue.submit_task_after
        for i in range(op.count):
            ctx = "6.2 心悦操作： {}({}/{})".format(op.sFlowName, i + 1, op.count)
            if current_hour < required_hour:
                logger.warning("当前时间为{}，在本日{}点之前，将不执行操作: {}".format(now, required_hour, ctx))
                continue

            for try_index in range(retryCfg.max_retry_count):
                res = self.xinyue_battle_ground_op(ctx, op.iFlowId, package_id=op.package_id, lqlevel=xytype)
                # if int(res.get('ret', '0')) == -9905:
                #     logger.warning("兑换 {} 时提示 {} ，等待{}s后重试（{}/{})".format(op.sGoodsName, res.get('msg'), retryCfg.retry_wait_time, try_index + 1, retryCfg.max_retry_count))
                #     time.sleep(retryCfg.retry_wait_time)
                #     continue

                logger.debug("心悦操作 {} ok，等待{}s，避免请求过快报错".format(op.sFlowName, retryCfg.request_wait_time))
                time.sleep(retryCfg.request_wait_time)
                break

    def try_join_fixed_xinyue_team(self):
        try:
            self._try_join_fixed_xinyue_team()
        except Exception as e:
            logger.exception("加入固定心悦队伍出现异常", exc_info=e)

    def _try_join_fixed_xinyue_team(self):
        # 检查是否有固定队伍
        fixed_team = self.get_fixed_team()

        if fixed_team is None:
            logger.warning("未找到本地固定队伍信息，跳过队伍相关流程")
            return

        logger.info("当前账号的本地固定队信息为{}".format(fixed_team))

        teaminfo = self.query_xinyue_teaminfo()
        if teaminfo.id != "":
            logger.info("目前已有队伍={}".format(teaminfo))
            # 本地保存一下
            self.save_teamid(fixed_team.id, teaminfo.id)
            return

        logger.info("尝试从本地查找当前固定队对应的远程队伍ID")
        remote_teamid = self.load_teamid(fixed_team.id)
        if remote_teamid != "":
            # 尝试加入远程队伍
            logger.info("尝试加入远程队伍id={}".format(remote_teamid))
            teaminfo = self.query_xinyue_teaminfo_by_id(remote_teamid)
            # 如果队伍仍有效则加入
            if teaminfo.id == remote_teamid:
                teaminfo = self.join_xinyue_team(remote_teamid)
                if teaminfo is not None:
                    logger.info("成功加入远程队伍，队伍信息为{}".format(teaminfo))
                    return

            logger.info("远程队伍={}已失效，应该是新的一周自动解散了，将重新创建队伍".format(remote_teamid))

        # 尝试创建小队并保存到本地
        teaminfo = self.create_xinyue_team()
        self.save_teamid(fixed_team.id, teaminfo.id)
        logger.info("创建小队并保存到本地成功，队伍信息={}".format(teaminfo))

    def get_fixed_team(self):
        """
        :rtype: FixedTeamConfig|None
        """
        qq_number = uin2qq(self.cfg.account_info.uin)
        fixed_team = None
        for team in self.common_cfg.fixed_teams:
            if not team.enable:
                continue
            if qq_number not in team.members:
                continue
            if not team.check():
                logger.warning("本地调试日志：本地固定队伍={}的队伍成员({})不符合要求，请确保是三个有效的qq号".format(team.id, team.members))
                continue

            fixed_team = team
            break

        return fixed_team

    def query_xinyue_teaminfo(self, print_res=True):
        data = self.xinyue_battle_ground_op("查询我的心悦队伍信息", "513818", print_res=print_res)
        jdata = data["modRet"]["jData"]

        return self.parse_teaminfo(jdata)

    def query_xinyue_teaminfo_by_id(self, remote_teamid):
        # 513919	传入小队ID查询队伍信息
        data = self.xinyue_battle_ground_op("查询特定id的心悦队伍信息", "513919", teamid=remote_teamid)
        jdata = data["modRet"]["jData"]
        teaminfo = self.parse_teaminfo(jdata)
        return teaminfo

    def join_xinyue_team(self, remote_teamid):
        # 513803	加入小队
        data = self.xinyue_battle_ground_op("尝试加入小队", "513803", teamid=remote_teamid)
        if int(data["flowRet"]["iRet"]) == 700:
            # 小队已经解散
            return None

        jdata = data["modRet"]["jData"]
        teaminfo = self.parse_teaminfo(jdata)
        return teaminfo

    def create_xinyue_team(self):
        # 513512	创建小队
        data = self.xinyue_battle_ground_op("尝试创建小队", "513512")
        jdata = data["modRet"]["jData"]
        teaminfo = self.parse_teaminfo(jdata)
        return teaminfo

    def parse_teaminfo(self, jdata):
        teamInfo = XinYueTeamInfo()
        teamInfo.result = jdata["result"]
        if teamInfo.result == 0:
            teamInfo.score = jdata["score"]
            teamid = jdata["teamid"]
            if type(teamid) == str:
                teamInfo.id = teamid
            else:
                for id in jdata["teamid"]:
                    teamInfo.id = id
            for member_json_str in jdata["teaminfo"]:
                member_json = json.loads(member_json_str)
                member = XinYueTeamMember(member_json["sqq"], unquote_plus(member_json["nickname"]), member_json["score"])
                teamInfo.members.append(member)
        return teamInfo

    def save_teamid(self, fixed_teamid, remote_teamid):
        fname = self.local_saved_teamid_file.format(fixed_teamid)
        with open(fname, "w", encoding="utf-8") as sf:
            teamidInfo = {
                "fixed_teamid": fixed_teamid,
                "remote_teamid": remote_teamid,
            }
            json.dump(teamidInfo, sf)
            logger.debug("本地保存固定队信息，具体内容如下：{}".format(teamidInfo))

    def load_teamid(self, fixed_teamid):
        fname = self.local_saved_teamid_file.format(fixed_teamid)

        if not os.path.isfile(fname):
            return ""

        with open(fname, "r", encoding="utf-8") as f:
            teamidInfo = json.load(f)
            logger.debug("读取本地缓存的固定队信息，具体内容如下：{}".format(teamidInfo))
            return teamidInfo["remote_teamid"]

    def query_xinyue_whitelist(self, ctx, print_res=True):
        data = self.xinyue_battle_ground_op(ctx, "673280", print_res=print_res)
        r = data["modRet"]
        user_is_white = int(r["sOutValue1"]) != 0
        return user_is_white

    def query_xinyue_items(self, ctx):
        data = self.xinyue_battle_ground_op(ctx, "512407")
        r = data["modRet"]
        total_obtain_two_score, used_two_score, total_obtain_free_do, used_free_do, total_obtain_refresh, used_refresh = r["sOutValue1"], r["sOutValue5"], r["sOutValue3"], r["sOutValue4"], r["sOutValue6"], r["sOutValue7"]
        return XinYueItemInfo(total_obtain_two_score, used_two_score, total_obtain_free_do, used_free_do, total_obtain_refresh, used_refresh)

    def query_xinyue_info(self, ctx, print_res=True):
        data = self.xinyue_battle_ground_op(ctx, "512411", print_res=print_res)
        r = data["modRet"]
        score, ysb, xytype, specialMember, username, usericon = r["sOutValue1"], r["sOutValue2"], r["sOutValue3"], r["sOutValue4"], r["sOutValue5"], r["sOutValue6"]
        return XinYueInfo(score, ysb, xytype, specialMember, username, usericon)

    def xinyue_battle_ground_op(self, ctx, iFlowId, package_id="", print_res=True, lqlevel=1, teamid=""):
        return self.xinyue_op(ctx, self.urls.iActivityId_xinyue_battle_ground, iFlowId, package_id, print_res, lqlevel, teamid)

    def xinyue_op(self, ctx, iActivityId, iFlowId, package_id="", print_res=True, lqlevel=1, teamid=""):
        return self.post(ctx, self.urls.amesvr, self.xinyue_flow_data(iActivityId, iFlowId, package_id, lqlevel, teamid),
                         amesvr_host="act.game.qq.com", sServiceDepartment="xinyue", sServiceType="xinyue",
                         iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
                         print_res=print_res)

    def xinyue_flow_data(self, iActivityId, iFlowId, package_id="", lqlevel=1, teamid=""):
        # 网站上特邀会员不论是游戏家G几，调用doAction(flowId,level)时level一律传1，而心悦会员则传入实际的567对应心悦123
        if lqlevel < 5:
            lqlevel = 1
        return self.format(self.urls.amesvr_raw_data,
                           sServiceDepartment="xinyue", sServiceType="xinyue", eas_url=quote_plus("http://xinyue.qq.com/act/a20181101rights/"),
                           iActivityId=iActivityId, iFlowId=iFlowId, package_id=package_id, lqlevel=lqlevel, teamid=teamid)

    # 心悦国庆活动【DNF金秋送福心悦有礼】
    def xinyue_guoqing(self):
        # https://xinyue.qq.com/act/a20200910dnf/index.html
        show_head_line("心悦国庆活动【DNF金秋送福心悦有礼】")

        if not self.cfg.function_switches.get_xinyue_guoqing:
            logger.warning("未启用领取心悦国庆活动功能，将跳过")
            return

        self.check_xinyue_guoqing()

        # 验证是否回流顺带检查是否未绑定大区
        self.xinyue_guoqing_op("验证幸运用户", "700301")
        self.xinyue_guoqing_op("幸运勇士", "700288")

        # 查询成就点信息
        xinyue_info = self.query_xinyue_info("查询心悦信息", print_res=False)

        # 1-4=游戏家G1-4，5-7=心悦VIP1-3
        if xinyue_info.xytype < 5:
            # 特邀
            self.xinyue_guoqing_op("特邀充值礼包", "700433")
        else:
            # 心悦
            if xinyue_info.xytype == 5:
                self.xinyue_guoqing_op("V1充值礼包", "700452")
            elif xinyue_info.xytype == 6:
                self.xinyue_guoqing_op("V2充值礼包", "700454")
            else:
                self.xinyue_guoqing_op("V3充值礼包", "700455")

            self.xinyue_guoqing_op("特邀升级礼", "700456")

        # 心悦特邀都可以领取的奖励
        self.xinyue_guoqing_op("心悦会员礼", "700457")
        self.xinyue_guoqing_op("每日在线30分钟", "700458")
        # self.xinyue_guoqing_op("国庆七日签到", "700462")
        self.xinyue_guoqing_op("惊喜礼包", "700511")
        # self.xinyue_guoqing_op("App礼包", "701088")

    def check_xinyue_guoqing(self):
        res = self.xinyue_guoqing_op("幸运勇士", "700288", print_res=False)
        # {"ret": "99998", "msg": "请刷新页面，先绑定大区！谢谢！", "flowRet": {"iRet": "99998", "sLogSerialNum": "AMS-TGCLUB-0924025126-AZmFbj-329456-700288", "iAlertSerial": "0", "sMsg": "请刷新页面，先绑定大区！谢谢！"}}
        if int(res["ret"]) == 99998:
            webbrowser.open("https://xinyue.qq.com/act/a20200910dnf/index.html")
            msg = "未绑定角色，请前往心悦国庆活动界面进行绑定，然后重新运行程序\n若无需该功能，可前往配置文件自行关闭该功能"
            win32api.MessageBox(0, msg, "提示", win32con.MB_ICONWARNING)
            exit(-1)

    def xinyue_guoqing_op(self, ctx, iFlowId, print_res=True):
        return self.xinyue_op(ctx, self.urls.iActivityId_xinyue_guoqing, iFlowId, print_res=print_res)

    # --------------------------------------------黑钻--------------------------------------------
    def get_heizuan_gift(self):
        # https://dnf.qq.com/act/blackDiamond/gift.shtml
        show_head_line("黑钻礼包")

        if not self.cfg.function_switches.get_heizuan_gift:
            logger.warning("未启用领取每月黑钻等级礼包功能，将跳过")
            return

        res = self.get("领取每月黑钻等级礼包", self.urls.heizuan_gift)
        # 如果未绑定大区，提示前往绑定 "iRet": -50014, "sMsg": "抱歉，请先绑定大区后再试！"
        if res["iRet"] == -50014:
            msg = "领取每月黑钻等级礼包失败，请先前往黑钻页面绑定角色信息\n若无需该功能，可前往配置文件自行关闭该功能"
            win32api.MessageBox(0, msg, "提示", win32con.MB_ICONWARNING)
            webbrowser.open("https://dnf.qq.com/act/blackDiamond/gift.shtml")
        return res

    # --------------------------------------------信用礼包--------------------------------------------
    def get_credit_xinyue_gift(self):
        show_head_line("腾讯游戏信用相关礼包")

        if not self.cfg.function_switches.get_credit_xinyue_gift:
            logger.warning("未启用领取腾讯游戏信用相关礼包功能，将跳过")
            return

        self.get("每月信用星级礼包", self.urls.credit_gift)
        try:
            # https://gamecredit.qq.com/static/web/index.html#/gift-pack
            self.get("腾讯游戏信用-高信用即享礼包", self.urls.credit_xinyue_gift, gift_group=1)
            # 等待一会
            time.sleep(self.common_cfg.retry.request_wait_time)
            self.get("腾讯游戏信用-高信用&游戏家即享礼包", self.urls.credit_xinyue_gift, gift_group=2)
        except Exception as e:
            logger.exception("腾讯游戏信用这个经常挂掉<_<不过问题不大，反正每月只能领一次", exc_info=e)

    # --------------------------------------------QQ空间抽卡--------------------------------------------
    def ark_lottery(self):
        # https://act.qzone.qq.com/vip/2019/xcardv3?zz=4&verifyid=qqvipdnf9
        show_head_line("QQ空间抽卡")

        if not self.cfg.function_switches.get_ark_lottery:
            logger.warning("未启用领取QQ空间抽卡功能，将跳过")
            return

        lr = self.fetch_pskey()
        if lr is None:
            return

        al = ArkLottery(self, lr)
        al.ark_lottery()

    def fetch_pskey(self):
        # 如果未启用抽卡功能，则不需要这个
        if not self.cfg.function_switches.get_ark_lottery:
            logger.warning("未启用领取QQ空间抽卡功能，将跳过")
            return

        # 仅支持扫码登录和自动登录
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            logger.warning("抽卡功能目前仅支持扫码登录和自动登录，请修改登录方式，否则将跳过该功能")
            return None

        cached_pskey = self.load_uin_pskey()
        need_update = self.is_pskey_expired(cached_pskey)

        if need_update:
            # 抽卡走的账号体系是使用pskey的，不与其他业务共用登录态，需要单独获取QQ空间业务的p_skey。参考链接：https://cloud.tencent.com/developer/article/1008901
            logger.warning("pskey需要更新，将尝试重新登录QQ空间获取并保存到本地")
            # 重新获取
            ql = QQLogin(self.common_cfg)
            if self.cfg.login_mode == "qr_login":
                # 扫码登录
                lr = ql.qr_login(login_mode=ql.login_mode_qzone)
            else:
                # 自动登录
                lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode=ql.login_mode_qzone)
            # 保存
            self.save_uin_pskey(lr.uin, lr.p_skey)
        else:
            lr = LoginResult(uin=cached_pskey["p_uin"], p_skey=cached_pskey["p_skey"])

        return lr

    def is_pskey_expired(self, cached_pskey):
        if cached_pskey is None:
            return True

        lr = LoginResult(uin=cached_pskey["p_uin"], p_skey=cached_pskey["p_skey"])
        al = ArkLottery(self, lr)

        # pskey过期提示：{'code': -3000, 'subcode': -4001, 'message': '请登录', 'notice': 0, 'time': 1601004332, 'tips': 'EE8B-284'}
        res = al.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日登陆页面", 25970, print_res=False)
        return res['code'] == -3000 and res['subcode'] == -4001

    def save_uin_pskey(self, uin, pskey):
        # 本地缓存
        with open(self.get_local_saved_pskey_file(), "w", encoding="utf-8") as sf:
            loginResult = {
                "p_uin": str(uin),
                "p_skey": str(pskey),
            }
            json.dump(loginResult, sf)
            logger.debug("本地保存pskey信息，具体内容如下：{}".format(loginResult))

    def load_uin_pskey(self):
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_pskey_file()):
            return

        with open(self.get_local_saved_pskey_file(), "r", encoding="utf-8") as f:
            loginResult = json.load(f)
            logger.debug("读取本地缓存的pskey信息，具体内容如下：{}".format(loginResult))
            return loginResult

    def get_local_saved_pskey_file(self):
        return self.local_saved_pskey_file.format(self.cfg.name)

    def ark_lottery_query_left_times(self, to_qq):
        ctx = "查询 {} 的剩余被赠送次数".format(to_qq)
        res = self.get(ctx, self.urls.ark_lottery_query_left_times, to_qq=to_qq, print_res=False)
        if res['13320']['ret'] != 0:
            return 0
        return res['13320']['data']['uPoint']

    def send_card(self, cardId, to_qq):
        from_qq = uin2qq(self.cfg.account_info.uin)

        ctx = "{} 赠送卡片 {} 给 {}".format(from_qq, cardId, to_qq)
        self.get(ctx, self.urls.ark_lottery_send_card, cardId=cardId, from_qq=from_qq, to_qq=to_qq, print_res=False)

    def send_card_by_name(self, card_name, to_qq):
        card_name_to_id = {
            "多人配合新挑战": "116193", "丰富机制闯难关": "116192", "新剧情视听盛宴": "116191", "单人成团战不停": "116190",
            "回归奖励大升级": "116189", "秒升Lv96刷深渊": "116188", "灿烂自选回归领": "116187", "告别酱油变大佬": "116186",
            "单人爽刷新玩法": "116185", "独立成团打副本": "116184", "海量福利金秋享": "116183", "超强奖励等你拿": "116182",
        }
        self.send_card(card_name_to_id[card_name], target_qq)

    # --------------------------------------------wegame国庆活动【秋风送爽关怀常伴】--------------------------------------------
    def wegame_guoqing(self):
        # https://dnf.qq.com/lbact/a20200922wegame/index.html
        show_head_line("wegame国庆活动【秋风送爽关怀常伴】")

        if not self.cfg.function_switches.get_wegame_guoqing:
            logger.warning("未启用领取wegame国庆活动功能，将跳过")
            return

        self.check_wegame_guoqing()

        # 一次性奖励
        self.wegame_op("金秋有礼抽奖", "703512")

        # 阿拉德智慧星-答题
        self.wegame_op("答题左上", "703514")
        self.wegame_op("答题左下", "703515")
        self.wegame_op("答题右上", "703516")
        self.wegame_op("答题右下", "703517")

        # 阿拉德智慧星-兑换奖励
        star_count, _ = self.get_wegame_star_count_lottery_times()
        logger.info(color("fg_bold_cyan") + "即将进行兑换道具，当前剩余智慧星为{}".format(star_count))
        self.wegame_exchange_items()

        # 签到抽大奖
        self.wegame_op("抽奖资格-每日签到（在WeGame启动DNF）", "703519")
        self.wegame_op("抽奖资格-30分钟签到（游戏在线30分钟）", "703527")
        _, lottery_times = self.get_wegame_star_count_lottery_times()
        logger.info(color("fg_bold_cyan") + "即将进行抽奖，当前剩余抽奖资格为{}".format(lottery_times))
        for i in range(lottery_times):
            res = self.wegame_op("抽奖", "703957")
            if res.get('ret', "0") == "600":
                # {"ret": "600", "msg": "非常抱歉，您的资格已经用尽！", "flowRet": {"iRet": "600", "sLogSerialNum": "AMS-DNF-1031000622-s0IQqN-331515-703957", "iAlertSerial": "0", "sMsg": "非常抱歉！您的资格已用尽！"}, "failedRet": {"762140": {"iRuleId": "762140", "jRuleFailedInfo": {"iFailedRet": 600}}}}
                break

        # 在线得好礼
        self.wegame_op("累计在线30分钟签到", "703529")
        check_days = self.get_wegame_checkin_days()
        logger.info(color("fg_bold_cyan") + "当前已累积签到 {} 天".format(check_days))
        self.wegame_op("签到3天礼包", "703530")
        self.wegame_op("签到5天礼包", "703531")
        self.wegame_op("签到7天礼包", "703532")
        self.wegame_op("签到10天礼包", "703533")
        self.wegame_op("签到15天礼包", "703534")

    def get_wegame_star_count_lottery_times(self):
        res = self.wegame_op("查询剩余抽奖次数", "703542", print_res=False)
        # "sOutValue1": "239:16:4|240:8:1",
        val = res["modRet"]["sOutValue1"]
        star_count, lottery_times = [int(jifen.split(':')[-1]) for jifen in val.split('|')]
        return star_count, lottery_times

    def get_wegame_checkin_days(self):
        res = self.wegame_op("查询签到信息", "703539")
        return res["modRet"]["total"]

    def wegame_exchange_items(self):
        for ei in self.cfg.wegame_guoqing_exchange_items:
            for i in range(ei.count):
                # 700-幸运星数目不足，600-已经达到最大兑换次数
                res = self.wegame_op("兑换 {}".format(ei.sGoodsName), ei.iFlowId)
                if res["ret"] == "700":
                    # 默认先兑换完前面的所有道具的最大上限，才会尝试兑换后面的道具
                    logger.warning("兑换第{}个【{}】的时候幸运星剩余数量不足，将停止兑换流程，从而确保排在前面的兑换道具达到最大兑换次数后才尝试后面的道具".format(i + 1, ei.sGoodsName))
                    return

    def check_wegame_guoqing(self):
        res = self.wegame_op("金秋有礼抽奖", "703512", print_res=False)
        # {"ret": "99998", "msg": "请刷新页面，先绑定大区！谢谢！", "flowRet": {"iRet": "99998", "sLogSerialNum": "AMS-DNF-0924120415-8k2lUH-331515-703512", "iAlertSerial": "0", "sMsg": "请刷新页面，先绑定大区！谢谢！"}}
        if int(res["ret"]) == 99998:
            webbrowser.open("https://dnf.qq.com/lbact/a20200922wegame/index.html")
            msg = "未绑定角色，请前往wegame国庆活动界面进行绑定，然后重新运行程序\n若无需该功能，可前往配置文件自行关闭该功能"
            win32api.MessageBox(0, msg, "提示", win32con.MB_ICONWARNING)
            exit(-1)

    def wegame_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_wegame_guoqing
        return self.post(ctx, self.urls.amesvr, self.wegame_flow_data(iActivityId, iFlowId),
                         amesvr_host="x6m5.ams.game.qq.com", sServiceDepartment="group_3", sServiceType="dnf",
                         iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
                         print_res=print_res)

    def wegame_flow_data(self, iActivityId, iFlowId):
        return self.format(self.urls.amesvr_raw_data,
                           sServiceDepartment="group_3", sServiceType="dnf", eas_url=quote_plus("http://dnf.qq.com/lbact/a20200922wegame/"),
                           iActivityId=iActivityId, iFlowId=iFlowId)

    # --------------------------------------------阿拉德集合站活动合集--------------------------------------------
    def dnf_922(self):
        # https://dnf.qq.com/lbact/a20200922hdjh/index.html
        show_head_line("阿拉德集合站活动合集")

        if not self.cfg.function_switches.get_dnf_922:
            logger.warning("未启用领取阿拉德集合站活动合集功能，将跳过")
            return

        self.check_dnf_922()

        self.dnf_922_op("勇士礼包", "703172")

        self.dnf_922_op("30分签到礼包", "703173")
        check_days = self.get_dnf_922_checkin_days()
        logger.info(color("fg_bold_cyan") + "当前已累积签到 {} 天".format(check_days))
        self.dnf_922_op("3日礼包", "703168")
        self.dnf_922_op("7日礼包", "703174")
        self.dnf_922_op("15日礼包", "703175")

    def get_dnf_922_checkin_days(self):
        res = self.dnf_922_op("查询签到信息", "703177")
        return res["modRet"]["total"]

    def check_dnf_922(self):
        res = self.dnf_922_op("30分签到礼包", "703173", print_res=False)
        # {"ret": "99998", "msg": "请刷新页面，先绑定大区！谢谢！", "flowRet": {"iRet": "99998", "sLogSerialNum": "AMS-DNF-0924120415-8k2lUH-331515-703512", "iAlertSerial": "0", "sMsg": "请刷新页面，先绑定大区！谢谢！"}}
        if int(res["ret"]) == 99998:
            webbrowser.open("https://dnf.qq.com/lbact/a20200922hdjh/index.html")
            msg = "未绑定角色，请前往阿拉德集合站活动界面进行绑定，然后重新运行程序\n若无需该功能，可前往配置文件自行关闭该功能"
            win32api.MessageBox(0, msg, "提示", win32con.MB_ICONWARNING)
            exit(-1)

    def dnf_922_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_922
        return self.post(ctx, self.urls.amesvr, self.dnf_922_flow_data(iActivityId, iFlowId),
                         amesvr_host="x6m5.ams.game.qq.com", sServiceDepartment="group_3", sServiceType="dnf",
                         iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
                         print_res=print_res)

    def dnf_922_flow_data(self, iActivityId, iFlowId):
        return self.format(self.urls.amesvr_raw_data,
                           sServiceDepartment="group_3", sServiceType="dnf", eas_url=quote_plus("http://dnf.qq.com/lbact/a20200922hdjh/"),
                           iActivityId=iActivityId, iFlowId=iFlowId)

    # --------------------------------------------2020DNF闪光杯返场赛--------------------------------------------
    def dnf_shanguang(self):
        # https://xinyue.qq.com/act/a20200907sgbpc/index.html
        show_head_line("2020DNF闪光杯返场赛")

        if not self.cfg.function_switches.get_dnf_shanguang:
            logger.warning("未启用领取2020DNF闪光杯返场赛活动合集功能，将跳过")
            return

        self.check_dnf_shanguang()

        # self.dnf_shanguang_op("报名礼", "698607")
        # self.dnf_shanguang_op("app专属礼", "698910")
        logger.warning(color("fg_bold_cyan") + "不要忘记前往网页手动报名并领取报名礼以及前往app领取一次性礼包")

        self.dnf_shanguang_op("周周闪光好礼", "698913")

        for i in range(6):
            res = self.dnf_shanguang_op("周周开大奖", "698914")
            # 1326109: 开奖次数已用完
            # 1326106: 很遗憾，你没有获得本次开奖机会
            # 1326105: 仅限每周三可以参与
            if res["flowRet"].get("iCondNotMetId", "0") in ["1326109", "1326106", "1326105"]:
                break
            time.sleep(5)

        self.dnf_shanguang_op("每日登录游戏", "699136")
        self.dnf_shanguang_op("每日登录app", "699137")
        # self.dnf_shanguang_op("每日网吧登录", "699140")

        lottery_times = self.get_dnf_shanguang_lottery_times()
        logger.info(color("fg_bold_cyan") + "当前剩余闪光夺宝次数为 {} ".format(lottery_times))
        for i in range(lottery_times):
            self.dnf_shanguang_op("闪光夺宝", "698915")
            time.sleep(5)

    def get_dnf_shanguang_lottery_times(self):
        res = self.dnf_shanguang_op("闪光夺宝次数", "699142")
        return int(res["modRet"]["sOutValue3"])

    def check_dnf_shanguang(self):
        res = self.dnf_shanguang_op("报名礼", "698607", print_res=False)
        # {"ret": "99998", "msg": "请刷新页面，先绑定大区！谢谢！", "flowRet": {"iRet": "99998", "sLogSerialNum": "AMS-DNF-0924120415-8k2lUH-331515-703512", "iAlertSerial": "0", "sMsg": "请刷新页面，先绑定大区！谢谢！"}}
        if int(res["ret"]) == 99998:
            webbrowser.open("https://xinyue.qq.com/act/a20200907sgbpc/index.html")
            msg = "未绑定角色，请前往2020DNF闪光杯返场赛活动界面进行绑定，然后重新运行程序\n若无需该功能，可前往配置文件自行关闭该功能"
            win32api.MessageBox(0, msg, "提示", win32con.MB_ICONWARNING)
            exit(-1)

    def dnf_shanguang_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_shanguang
        return self.post(ctx, self.urls.amesvr, self.dnf_shanguang_flow_data(iActivityId, iFlowId),
                         amesvr_host="act.game.qq.com", sServiceDepartment="xinyue", sServiceType="tgclub",
                         iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
                         print_res=print_res)

    def dnf_shanguang_flow_data(self, iActivityId, iFlowId):
        weekDay = get_this_week_monday()
        return self.format(self.urls.amesvr_raw_data,
                           sServiceDepartment="xinyue", sServiceType="tgclub", eas_url=quote_plus("http://xinyue.qq.com/act/a20200907sgbpc/"),
                           iActivityId=iActivityId, iFlowId=iFlowId,
                           weekDay=weekDay)

    # --------------------------------------------qq视频活动--------------------------------------------
    def qq_video(self):
        # https://film.qq.com/film/p/topic/dnf922/index.html
        show_head_line("qq视频活动")

        if not self.cfg.function_switches.get_qq_video:
            logger.warning("未启用领取qq视频活动功能，将跳过")
            return

        self.check_qq_video()

        self.qq_video_op("幸运勇士礼包", "125888")
        self.qq_video_op("勇士见面礼-礼包", "125890")
        self.qq_video_op("勇士见面礼-令牌", "125911")

        self.qq_video_op("在线30分钟", "125905")
        self.qq_video_op("累积3天", "125906")
        self.qq_video_op("累积7天", "125908")
        self.qq_video_op("累积15天", "125907")

    def check_qq_video(self):
        res = self.qq_video_op("幸运勇士礼包", "125888", print_res=False)
        # {"frame_resp": {"failed_condition": {"condition_op": 3, "cur_value": 0, "data_type": 2, "exp_value": 0, "type": 100418}, "msg": "", "ret": 0, "security_verify": {"iRet": 0, "iUserType": 0, "sAppId": "", "sBusinessId": "", "sInnerMsg": "", "sUserMsg": ""}}, "act_id": 108810, "data": {"button_txt": "关闭", "cdkey": "", "custom_list": [], "end_timestamp": -1, "ext_url": "", "give_type": 0, "is_mask_cdkey": 0, "is_pop_jump": 0, "item_share_desc": "", "item_share_title": "", "item_share_url": "", "item_sponsor_title": "", "item_sponsor_url": "", "item_tips": "", "jump_url": "", "jump_url_web": "", "lottery_item_id": "1601827185657s2238078729s192396s1", "lottery_level": 0, "lottery_name": "", "lottery_num": 0, "lottery_result": 0, "lottery_txt": "您当前还未绑定游戏帐号，请先绑定哦~", "lottery_url": "", "lottery_url_ext": "", "lottery_url_ext1": "", "lottery_url_ext2": "", "msg_title": "告诉我怎么寄给你", "need_bind": 0, "next_type": 2, "pop_jump_btn_title": "", "pop_jump_url": "", "prize_give_info": {"prize_give_status": 0}, "property_detail_code": 0, "property_detail_msg": "", "property_type": 0, "share_txt": "", "share_url": "", "source": 0, "sys_code": -904, "url_lottery": "", "user_info": {"addr": "", "name": "", "tel": "", "uin": ""}}, "module_id": 125890, "msg": "", "ret": 0, "security_verify": {"iRet": 0, "iUserType": 0, "sAppId": "", "sBusinessId": "", "sInnerMsg": "", "sUserMsg": ""}}
        if int(res["data"]["sys_code"]) == -904 and res["data"]["lottery_txt"] == "您当前还未绑定游戏帐号，请先绑定哦~":
            msg = "未绑定角色，请打开dnf助手->活动->前往【征战新团本，共享好时光】活动界面进行绑定，然后重新运行程序\n若无需该功能，可前往配置文件自行关闭该功能"
            logger.warning(color("fg_bold_cyan") + msg)

    def qq_video_op(self, ctx, module_id, print_res=True):
        res = self._qq_video_op(ctx, "21", "100", module_id, print_res)
        # self._qq_video_op(ctx, "71", "111", "125909", False)
        # self._qq_video_op(ctx, "21", "104", module_id, False)

        if int(res["data"]["sys_code"]) == -1010 and res["data"]["lottery_txt"] == "系统错误":
            msg = "【需要修复这个】不知道为啥这个操作失败了，试试连上fiddler然后手动操作看看请求哪里对不上"
            logger.warning(color("fg_bold_yellow") + msg)

        return res

    def _qq_video_op(self, ctx, type, option, module_id, print_res=True):
        extra_cookies = "; ".join([
            "",
            "appid=3000501",
            "main_login=qq",
            "vuserid={vuserid}".format(vuserid=self.vuserid),
        ])
        return self.get(ctx, self.urls.qq_video, type=type, option=option, act_id="108810", module_id=module_id,
                        print_res=print_res, extra_cookies=extra_cookies)

    # --------------------------------------------10月女法师三觉活动--------------------------------------------
    def dnf_female_mage_awaken(self):
        # https://mwegame.qq.com/act/dnf/Mageawaken/index?subGameId=10014&gameId=10014&gameId=1006
        show_head_line("10月女法师三觉")

        if not self.cfg.function_switches.get_dnf_female_mage_awaken:
            logger.warning("未启用领取10月女法师三觉活动合集功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # fixme: 这个之后签到几天后再看看各个outvalue到底是啥含义
        logger.warning("这个之后签到几天后再看看各个outvalue到底是啥含义")
        # checkin_days = self.query_dnf_female_mage_awaken_info()
        # logger.warning(color("fg_bold_cyan") + "已累计签到 {} 天".format(checkin_days))

        if self.cfg.dnf_helper_info.token == "":
            logger.warning(color("fg_bold_yellow") + "未配置dnf助手相关信息，无法进行10月女法师三觉相关活动，请按照下列流程进行配置")
            self.show_dnf_helper_info_guide()
            return

        self.dnf_female_mage_awaken_op("时间的引导石 * 10", "712951")
        self.dnf_female_mage_awaken_op("魂灭结晶礼盒 (200个)", "712970")
        self.dnf_female_mage_awaken_op("神秘契约礼盒 (1天)", "712971")
        self.dnf_female_mage_awaken_op("抗疲劳秘药 (10点)", "712972")
        self.dnf_female_mage_awaken_op("装备品级调整箱礼盒 (1个)", "712973")
        self.dnf_female_mage_awaken_op("复活币礼盒 (1个)", "712974")
        self.dnf_female_mage_awaken_op("神秘的符文原石", "712975")
        self.dnf_female_mage_awaken_op("成长胶囊 (50百分比) (Lv50~99)", "712977")
        self.dnf_female_mage_awaken_op("黑钻(3天)", "712978")
        self.dnf_female_mage_awaken_op("本职业稀有护石神秘礼盒", "712981")

        self.dnf_female_mage_awaken_op("每周签到3/5/7次时获得娃娃机抽奖次数", "713370")
        self.dnf_female_mage_awaken_op("娃娃机抽奖", "712623")

        self.dnf_female_mage_awaken_op("回归礼包", "710474")

    def query_dnf_female_mage_awaken_info(self):
        res = self.dnf_female_mage_awaken_op("查询", "712497")
        sOutValue1, sOutValue2, sOutValue3 = res["modRet"]["sOutValue1"], res["modRet"]["sOutValue2"], res["modRet"]["sOutValue3"]

        # _, checkin_days = sOutValue1.split(';')
        # can_checkin_7, can_checkin_14, can_checkin_21, can_checkin_28 = sOutValue2.split(';')
        #
        # return checkin_days

    def dnf_female_mage_awaken_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_female_mage_awaken
        res = self.post(ctx, self.urls.amesvr, self.dnf_female_mage_awaken_flow_data(iActivityId, iFlowId),
                        amesvr_host="comm.ams.game.qq.com", sServiceDepartment="group_k", sServiceType="bb",
                        iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
                        print_res=print_res)

        # 1000017016: 登录态失效,请重新登录
        if res["flowRet"]["iRet"] == "700" and res["flowRet"]["sMsg"] == "登录态失效,请重新登录":
            logger.warning(color("fg_bold_yellow") + "dnf助手的登录态已过期，目前需要手动更新，具体操作流程如下")
            self.show_dnf_helper_info_guide()

        return res

    def show_dnf_helper_info_guide(self):
        logger.warning(color("fg_bold_yellow") + "1. 打开dnf助手并确保已登录账户，点击活动，找到【艾丽丝的密室，塔罗牌游戏】并点开，点击右上角分享，选择QQ好友，发送给【我的电脑】")
        logger.warning(color("fg_bold_yellow") + "2. 在我的电脑聊天框中的链接中找到请求中的token（形如&token=tW7AbaM7，则token为tW7AbaM7），将其进行更新到配置文件中【dnf助手信息】配置中")
        logger.warning(color("fg_bold_yellow") + "ps: nickName/userId的获取方式为，点开dnf助手中点开右下角的【我的】，然后点击右上角的【编辑】按钮，则昵称即为nickname，社区ID即为userId，如我的这俩值为风之凌殇、504051073")
        logger.warning(color("fg_bold_yellow") + "_")
        logger.warning(color("fg_bold_yellow") + "如果你刚刚按照上述步骤操作过，但这次运行还是提示你过期了，很大概率是你想要多个账号一起用这个功能，然后在手机上依次登陆登出这些账号，按照上述操作获取token。实际上这样是无效的，因为你在登陆下一个账号的时候，之前的账号的token就因为登出而失效了")
        logger.warning(color("fg_bold_yellow") + "有这个需求的话，请使用安卓模拟器的多开功能来多开dnf助手去登陆各个账号。如果手机支持多开app，也可以使用对应功能。具体多开流程请自行百度搜索： 手机 app 多开")

    def dnf_female_mage_awaken_flow_data(self, iActivityId, iFlowId):
        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        qq = uin2qq(self.cfg.account_info.uin)
        dnf_helper_info = self.cfg.dnf_helper_info
        return self.format(self.urls.amesvr_raw_data,
                           sServiceDepartment="group_k", sServiceType="bb", eas_url=quote_plus("http://mwegame.qq.com/act/dnf/mageawaken/index1/"),
                           iActivityId=iActivityId, iFlowId=iFlowId,
                           sArea=roleinfo.serviceID, serverId=roleinfo.serviceID,
                           sRoleId=roleinfo.roleCode, sRoleName=quote_plus(roleinfo.roleName),
                           uin=qq, skey=self.cfg.account_info.skey,
                           nickName=quote_plus(dnf_helper_info.nickName), userId=dnf_helper_info.userId, token=dnf_helper_info.token,
                           )

    # --------------------------------------------管家蚊子腿--------------------------------------------
    def guanjia(self):
        # https://guanjia.qq.com/act/cop/202010dnf/
        show_head_line("管家蚊子腿")

        if not self.cfg.function_switches.get_guanjia:
            logger.warning("未启用领取管家蚊子腿活动合集功能，将跳过")
            return

        lr = self.fetch_guanjia_openid()
        if lr is None:
            return
        self.guanjia_lr = lr
        # 等一会，避免报错
        time.sleep(self.common_cfg.retry.request_wait_time)

        self.guanjia_op("下载礼包", "comjoin_1059", giftId="7094")
        self.guanjia_op("连续签到两天礼包", "comjoin_1059", giftId="7095")

        self.guanjia_op("回归勇士礼包", "comjoin_1059", giftId="7096")
        self.guanjia_op("每日游戏在线30分钟", "comjoin_1059", giftId="7099")
        self.guanjia_op("管家个人中心签到", "comjoin_1059", giftId="7098")

        for i in range(10):
            res = self.guanjia_op("抽奖", "lottjoin_1058")
            # {"code": 4101, "msg": "积分不够", "result": []}
            if res["code"] == 4101:
                break
            time.sleep(self.common_cfg.retry.request_wait_time)

    def is_guanjia_openid_expired(self, cached_guanjia_openid):
        if cached_guanjia_openid is None:
            return True

        lr = LoginResult(qc_openid=cached_guanjia_openid["qc_openid"], qc_k=cached_guanjia_openid["qc_k"])
        self.guanjia_lr = lr

        # {"code": 7005, "msg": "获取accToken失败", "result": []}
        # {"code": 29, "msg": "请求包参数错误", "result": []}
        res = self.guanjia_op("管家个人中心签到", "comjoin_1059", giftId="7098", print_res=False)
        return res["code"] in [7005, 29]

    def guanjia_op(self, ctx, api, giftId="", print_res=True):
        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        extra_cookies = "__qc__openid={openid}; __qc__k={access_key};".format(
            openid=self.guanjia_lr.qc_openid,
            access_key=self.guanjia_lr.qc_k
        )
        return self.get(ctx, self.urls.guanjia, api=api, giftId=giftId, area_id=roleinfo.serviceID, charac_no=roleinfo.roleCode, charac_name=quote_plus(roleinfo.roleName),
                        extra_cookies=extra_cookies, is_jsonp=True, is_normal_jsonp=True, print_res=print_res)

    def fetch_guanjia_openid(self, print_warning=True):
        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            if print_warning: logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # 仅支持扫码登录和自动登录
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            if print_warning: logger.warning("目前仅支持扫码登录和自动登录，请修改登录方式，否则将跳过该功能")
            return None

        cached_guanjia_openid = self.load_guanjia_openid()
        need_update = self.is_guanjia_openid_expired(cached_guanjia_openid)

        if need_update:
            logger.warning("管家openid需要更新，将尝试重新登录电脑管家网页获取并保存到本地")
            # 重新获取
            ql = QQLogin(self.common_cfg)
            if self.cfg.login_mode == "qr_login":
                # 扫码登录
                lr = ql.qr_login(login_mode=ql.login_mode_guanjia)
            else:
                # 自动登录
                lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode=ql.login_mode_guanjia)
            # 保存
            self.save_guanjia_openid(lr.qc_openid, lr.qc_k)
        else:
            lr = LoginResult(qc_openid=cached_guanjia_openid["qc_openid"], qc_k=cached_guanjia_openid["qc_k"])

        return lr

    def save_guanjia_openid(self, qc_openid, qc_k):
        # 本地缓存
        with open(self.get_local_saved_guanjia_openid_file(), "w", encoding="utf-8") as sf:
            loginResult = {
                "qc_openid": str(qc_openid),
                "qc_k": str(qc_k),
            }
            json.dump(loginResult, sf)
            logger.debug("本地保存管家openid信息，具体内容如下：{}".format(loginResult))

    def load_guanjia_openid(self):
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_guanjia_openid_file()):
            return

        with open(self.get_local_saved_guanjia_openid_file(), "r", encoding="utf-8") as f:
            loginResult = json.load(f)
            logger.debug("读取本地缓存的管家openid信息，具体内容如下：{}".format(loginResult))
            return loginResult

    def get_local_saved_guanjia_openid_file(self):
        return self.local_saved_guanjia_openid_file.format(self.cfg.name)

    # --------------------------------------------微信签到--------------------------------------------
    def wx_checkin(self):
        # fixme: 开发完成后移除这个
        if not self.cfg.test_mode:
            return

        show_head_line("微信签到--临时版本，仅本地使用")

        # if not self.cfg.function_switches.wx_checkin:
        #     logger.warning("未启用微信签到功能，将跳过")
        #     return

        self.post("微信签到", 'https://gw.gzh.qq.com/awp-signin/register?id=260', {},
                  extra_cookies=self.make_cookie({
                      "fsza_sk_s_q_at_101482157": "1599657594",
                      "fsza_sk_t_q_at_101482157": "01EHSGBKRZ9ECXXWPF589HFY2M",
                      "fsza_sk_t_at_wxa817069bb040f860": "84db8359ff1faf4b2a4afe499d62aaf8415f6933ace0b3975fe256a8def52231",
                      "fsza_sk_s_at_wxa817069bb040f860": "1604028769",
                  }))

    # --------------------------------------------辅助函数--------------------------------------------
    def get(self, ctx, url, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, extra_cookies="", **params):
        return self.network.get(ctx, self.format(url, **params), pretty, print_res, is_jsonp, is_normal_jsonp, extra_cookies)

    def post(self, ctx, url, data, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, extra_cookies="", **params):
        return self.network.post(ctx, self.format(url, **params), data, pretty, print_res, is_jsonp, is_normal_jsonp, extra_cookies)

    def format(self, url, **params):
        endTime = datetime.datetime.now()
        startTime = endTime - datetime.timedelta(days=int(365 / 12 * 5))
        date = get_today()
        default_params = {
            "appVersion": appVersion,
            "p_tk": self.cfg.g_tk,
            "g_tk": self.cfg.g_tk,
            "sDeviceID": self.cfg.sDeviceID,
            "sDjcSign": self.cfg.sDjcSign,
            "callback": jsonp_callback_flag,
            "month": self.get_month(),
            "starttime": self.getMoneyFlowTime(startTime.year, startTime.month, startTime.day, startTime.hour, startTime.minute, startTime.second),
            "endtime": self.getMoneyFlowTime(endTime.year, endTime.month, endTime.day, endTime.hour, endTime.minute, endTime.second),
            "sSDID": self.cfg.sDeviceID.replace('-', ''),
            "uuid": self.cfg.sDeviceID,
            "millseconds": getMillSecondsUnix(),
            "rand": random.random(),
            "package_id": "", "lqlevel": "", "teamid": "",
            "weekDay": "",
            "sArea": "", "serverId": "", "nickName": "", "sRoleId": "", "sRoleName": "", "uin": "", "skey": "", "userId": "", "token": "",
            "iActionId": "", "iGoodsId": "", "sBizCode": "", "partition": "", "iZoneId": "", "platid": "", "sZoneDesc": "", "sGetterDream": "",
            "date": date,
        }
        return url.format(**{**default_params, **params})

    def get_month(self):
        now = datetime.datetime.now()
        return "%4d%02d" % (now.year, now.month)

    def getMoneyFlowTime(self, year, month, day, hour, minute, second):
        return "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(year, month, day, hour, minute, second)

    def make_s_milo_tag(self, iActivityId, iFlowId):
        return "AMS-MILO-{iActivityId}-{iFlowId}-{id}-{millseconds}-{rand6}".format(
            iActivityId=iActivityId,
            iFlowId=iFlowId,
            id=self.cfg.account_info.uin,
            millseconds=getMillSecondsUnix(),
            rand6=self.rand6()
        )

    def rand6(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=6))

    def make_cookie(self, map: dict):
        return '; '.join(['{}={}'.format(k, v) for k, v in map.items()])


if __name__ == '__main__':
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    idx = 1  # 从1开始，第i个
    account_config = cfg.account_configs[idx - 1]

    logger.info("开始处理第{}个账户[{}]".format(idx, account_config.name))

    djcHelper = DjcHelper(account_config, cfg.common)
    # djcHelper.run()
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list()

    # djcHelper.query_all_extra_info()
    # djcHelper.exchange_items()
    # djcHelper.xinyue_operations()
    # djcHelper.try_join_fixed_xinyue_team()
    # djcHelper.get_heizuan_gift()
    # djcHelper.get_credit_xinyue_gift()
    # djcHelper.query_mobile_game_rolelist()
    # djcHelper.complete_tasks()
    # djcHelper.xinyue_guoqing()
    # djcHelper.ark_lottery()
    # djcHelper.wegame_guoqing()
    # djcHelper.dnf_922()
    # djcHelper.dnf_shanguang()
    # djcHelper.qq_video()
    # djcHelper.djc_operations()
    # djcHelper.dnf_female_mage_awaken()
    # djcHelper.guanjia()
    # djcHelper.dnf_shanguang()
    # djcHelper.send_card_by_name("独立成团打副本", "1054073896")
    # djcHelper.wx_checkin()
    djcHelper.dnf_female_mage_awaken()
