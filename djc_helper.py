import calendar
import math
import platform
import random
import string
import subprocess
import webbrowser
from urllib.parse import quote_plus

import pyperclip
import win32api

import json_parser
from dao import *
from game_info import get_game_info, get_game_info_by_bizcode
from network import *
from qq_login import QQLogin, LoginResult
from qzone_activity import QzoneActivity
from setting import *
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

        self.zzconfig = zzconfig()

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
            role_info = GameRoleInfo().auto_update_config(roleinfo_dict)
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
            if not self.cfg.cannot_bind_dnf and "dnf" not in self.bizcode_2_bind_role_map:
                logger.warning(color("fg_bold_yellow") + "未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定")
                binded = False

            if self.cfg.mobile_game_role_info.enabled() and not self.check_mobile_game_bind():
                binded = False

        if binded:
            if self.cfg.function_switches.get_djc:
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
            else:
                logger.warning("当前账号未启用道聚城相关功能")

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

        # 心悦app理财礼卡
        self.xinyue_financing()

        # DNF共创投票
        self.dnf_dianzan()

        # dnf漂流瓶
        self.dnf_drift()

        # DNF马杰洛的规划第二期
        self.majieluo()

        # dnf助手双旦活动
        self.dnf_helper_christmas()

        # 暖冬好礼活动
        self.warm_winter()

        # DNF闪光杯第三期
        self.dnf_shanguang()

        # 管家蚊子腿
        self.guanjia()

        # 史诗之路来袭活动合集
        self.dnf_1224()

        # qq视频活动
        self.qq_video()

    # -- 已过期的一些活动
    def expired_activities(self):
        # wegame国庆活动【秋风送爽关怀常伴】
        self.wegame_guoqing()

        # 微信签到
        self.wx_checkin()

        # 10月女法师三觉
        self.dnf_female_mage_awaken()

        # dnf助手排行榜
        self.dnf_rank()

        # 2020DNF嘉年华页面主页面签到
        self.dnf_carnival()

        # DNF进击吧赛利亚
        self.xinyue_sailiyam()

        # 阿拉德勇士征集令
        self.dnf_warriors_call()

        # dnf助手编年史活动
        self.dnf_helper_chronicle()

        # hello语音网页礼包兑换
        self.hello_voice()

        # DNF福利中心兑换
        self.dnf_welfare()

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

        self.get("3.2 一键领取{}日常礼包-{}".format(role_info.gameName, giftInfo.sTask), self.urls.receive_game_gift,
                 bizcode=game_info.bizCode, iruleId=giftInfo.iRuleId,
                 systemID=role_info.systemID, sPartition=role_info.areaID, channelID=role_info.channelID, channelKey=role_info.channelKey,
                 roleCode=role_info.roleCode, sRoleName=quote_plus(role_info.roleName))

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

        propModel = GoodsInfo().auto_update_config(query_wish_item_list_res["data"]["goods"][0])

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
        return self.get(ctx, self.urls.exchangeItems, iGoodsSeqId=iGoodsSeqId, rolename=quote_plus(roleinfo.roleName), lRoleId=roleinfo.roleCode, iZone=roleinfo.serviceID)

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

    def bind_dnf_role(self, areaID="30", areaName="浙江", serviceID="11", serviceName="浙江一区", roleCode="22370088", roleName="∠木星新、"):
        roleInfo = {
            "areaID": areaID,
            "areaName": areaName,
            "bizCode": "dnf",
            "channelID": "",
            "channelKey": "",
            "channelName": "",
            "gameName": "地下城与勇士",
            "isHasService": 1,
            "roleCode": roleCode,
            "roleName": roleName,
            "serviceID": serviceID,
            "serviceName": serviceName,
            "systemID": "",
            "systemKey": "",
            "type": "0"
        }

        self.get("绑定账号-{}-{}".format(serviceName, roleName), self.urls.bind_role, role_info=json.dumps(roleInfo, ensure_ascii=False), is_jsonp=True)

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
        # 网站上特邀会员不论是游戏家G几，调用doAction(flowId,level)时level一律传1，而心悦会员则传入实际的567对应心悦123
        if lqlevel < 5:
            lqlevel = 1

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "xinyue", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20181101rights/",
                                   package_id=package_id, lqlevel=lqlevel, teamid=teamid,
                                   )

    # DNF进击吧赛利亚
    def xinyue_sailiyam(self):
        # https://xinyue.qq.com/act/a20201023sailiya/index.html
        show_head_line("DNF进击吧赛利亚")

        def sleep_to_avoid_ban():
            logger.info("等待五秒，防止提示操作太快")
            time.sleep(5)

        for dzid in self.common_cfg.sailiyam_visit_target_qqs:
            if dzid == uin2qq(self.cfg.account_info.uin):
                continue
            self.xinyue_sailiyam_op("拜访好友-{}".format(dzid), "714307", dzid=dzid)
            sleep_to_avoid_ban()

        if not self.cfg.function_switches.get_xinyue_sailiyam or self.disable_most_activities():
            logger.warning("未启用领取DNF进击吧赛利亚活动功能，将跳过")
            return

        self.check_xinyue_sailiyam()
        self.show_xinyue_sailiyam_kouling()
        self.xinyue_sailiyam_op("清空工作天数", "715579")

        sleep_to_avoid_ban()
        self.xinyue_sailiyam_op("领取蛋糕", "714230")
        self.xinyue_sailiyam_op("投喂蛋糕", "714251")

        logger.info("ps：打工在运行结束的时候统一处理，这样可以确保处理好各个其他账号的拜访，从而有足够的心情值进行打工")

    def get_xinyue_sailiyam_package_id(self):
        res = self.xinyue_sailiyam_op("打工显示", "715378", print_res=False)
        try:
            return res["modRet"]["jData"]["roleinfor"]["iPackageId"]
        except:
            return ""

    def get_xinyue_sailiyam_workinfo(self):
        res = self.xinyue_sailiyam_op("打工显示", "715378", print_res=False)
        try:
            workinfo = SailiyamWorkInfo().auto_update_config(res["modRet"]["jData"]["roleinfor"])

            work_message = ""

            if workinfo.status == 2:
                nowtime = get_now_unix()
                fromtimestamp = datetime.datetime.fromtimestamp
                if workinfo.endTime > nowtime:
                    lefttime = int(workinfo.endTime - nowtime)
                    work_message += "赛利亚打工倒计时：{:02d}:{:02d}:{:02d}".format(lefttime // 3600, lefttime % 3600 // 60, lefttime % 60)
                else:
                    work_message += "赛利亚已经完成今天的工作了"

                work_message += "。开始时间为{}，结束时间为{}，奖励最终领取时间为{}".format(fromtimestamp(workinfo.startTime), fromtimestamp(workinfo.endTime), fromtimestamp(workinfo.endLQtime))
            else:
                work_message += "赛利亚尚未出门工作"

            return work_message
        except Exception as e:
            logger.error("获取打工信息出错了", exc_info=e)
            return ""

    def get_xinyue_sailiyam_status(self):
        res = self.xinyue_sailiyam_op("查询状态", "714738", print_res=False)
        try:
            modRet = AmesvrCommonModRet().auto_update_config(res["modRet"])
            lingqudangao, touwei, _, baifang = modRet.sOutValue1.split('|')
            dangao = modRet.sOutValue2
            xinqingzhi = modRet.sOutValue3
            qiandaodate = modRet.sOutValue4
            return "领取蛋糕：{}, 投喂蛋糕: {}, 已拜访次数: {}/5, 剩余蛋糕: {}, 心情值: {}/100, 已连续签到: {}次".format(
                lingqudangao == "1", touwei == "1", baifang, dangao, xinqingzhi, qiandaodate
            )
        except:
            return ""

    def show_xinyue_sailiyam_work_log(self):
        res = self.xinyue_sailiyam_op("日志列表", "715201", print_res=False)
        try:
            logContents = {
                '2168440': '遇到需要紧急处理的工作，是时候证明真正的技术了，启动加班模式！工作时长加1小时；',
                '2168439': '愉快的一天又开始了，是不是该来一杯咖啡？',
                '2168442': '给流浪猫咪喂吃的导致工作迟到，奖励虽然下降 ，但是撸猫的心情依然美好；',
                '2168441': '工作效率超高，能力超强，全能MVP，优秀的你，当然需要发奖金啦，奖励up；'
            }
            logs = res["modRet"]["jData"]["loglist"]["list"]
            if len(logs) != 0:
                logger.info("赛利亚打工日志如下")
                for log in logs:
                    logger.info("{}月{}日：{}".format(log[0][:2], log[0][2:], logContents[log[2]]))
        except:
            pass

    def show_xinyue_sailiyam_kouling(self):
        res = self.xinyue_sailiyam_op("输出项", "714618", print_res=False)
        if 'modRet' in res:
            logger.info("分享口令为： {}".format(res["modRet"]["sOutValue2"]))

    def check_xinyue_sailiyam(self):
        res = self.xinyue_sailiyam_op("领取蛋糕", "714230", print_res=True)
        # {"ret": "99998", "msg": "请刷新页面，先绑定大区！谢谢！", "flowRet": {"iRet": "99998", "sLogSerialNum": "AMS-TGCLUB-1118215502-6NOW8h-339263-714230", "iAlertSerial": "0", "sMsg": "请刷新页面，先绑定大区！谢谢！"}}
        if int(res["ret"]) == 99998:
            self.guide_to_bind_account("DNF进击吧赛利亚", "https://xinyue.qq.com/act/a20201023sailiya/index.html")

    def xinyue_sailiyam_op(self, ctx, iFlowId, dzid="", iPackageId="", print_res=True):
        iActivityId = self.urls.iActivityId_xinyue_sailiyam

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20201023sailiyam/",
                                   dzid=dzid, page=1, iPackageId=iPackageId,
                                   )

    # --------------------------------------------黑钻--------------------------------------------
    def get_heizuan_gift(self):
        # https://dnf.qq.com/act/blackDiamond/gift.shtml
        show_head_line("黑钻礼包")

        if not self.cfg.function_switches.get_heizuan_gift or self.disable_most_activities():
            logger.warning("未启用领取每月黑钻等级礼包功能，将跳过")
            return

        res = self.get("领取每月黑钻等级礼包", self.urls.heizuan_gift)
        # 如果未绑定大区，提示前往绑定 "iRet": -50014, "sMsg": "抱歉，请先绑定大区后再试！"
        if res["iRet"] == -50014:
            self.guide_to_bind_account("每月黑钻等级礼包", "https://dnf.qq.com/act/blackDiamond/gift.shtml")

        return res

    # --------------------------------------------信用礼包--------------------------------------------
    def get_credit_xinyue_gift(self):
        show_head_line("腾讯游戏信用相关礼包")

        if not self.cfg.function_switches.get_credit_xinyue_gift or self.disable_most_activities():
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
        # note: 启用和废弃抽卡活动的流程如下
        #   1. 启用
        #   1.1 获取新配置   手机登录抽卡活动页面，然后抓包获得页面代码，从中搜索【window.syncData】找到逻辑数据和配置，将其值复制到【setting/ark_lottery.py】中，作为setting变量的值
        #   1.2 填写新链接   在urls.py中，替换self.ark_lottery_page的值为新版抽卡活动的链接（理论上应该只有zz和verifyid参数的值会变动，而且大概率是+1）
        #   1.3 重新启用代码
        #   1.3.1 在djc_helper.py中将ark_lottery的调用处从expired_activities移到normal_run
        #   1.3.2 在main.py中将main函数中取消注释show_lottery_status和auto_send_cards的调用处
        #
        # hack:
        #   2. 废弃
        #   2.1 在djc_helper.py中将ark_lottery的调用处从normal_run移到expired_activities
        #   2.2 在main.py中将main函数中注释show_lottery_status和auto_send_cards的调用处

        # https://act.qzone.qq.com/vip/2019/xcardv3?zz=5&verifyid=qqvipdnf10
        show_head_line("QQ空间抽卡 - {}_{}".format(self.zzconfig.actid, self.zzconfig.actName))

        if not self.cfg.function_switches.get_ark_lottery:
            logger.warning("未启用领取QQ空间抽卡功能，将跳过")
            return

        lr = self.fetch_pskey()
        if lr is None:
            return

        qa = QzoneActivity(self, lr)
        qa.ark_lottery()

    def ark_lottery_query_left_times(self, to_qq):
        ctx = "查询 {} 的剩余被赠送次数".format(to_qq)
        res = self.get(ctx, self.urls.ark_lottery_query_left_times, to_qq=to_qq, actName=self.zzconfig.actName, print_res=False)
        # # {"13320":{"data":{"uAccuPoint":4,"uPoint":3},"ret":0,"msg":"成功"},"ecode":0,"ts":1607934735801}
        if res['13320']['ret'] != 0:
            return 0
        return res['13320']['data']['uPoint']

    def send_card(self, card_name, cardId, to_qq, print_res=False):
        from_qq = uin2qq(self.cfg.account_info.uin)

        ctx = "{} 赠送卡片 {}({}) 给 {}".format(from_qq, card_name, cardId, to_qq)
        self.get(ctx, self.urls.ark_lottery_send_card, cardId=cardId, from_qq=from_qq, to_qq=to_qq, actName=self.zzconfig.actName, print_res=print_res)
        # # {"13333":{"data":{},"ret":0,"msg":"成功"},"ecode":0,"ts":1607934736057}

    def send_card_by_name(self, card_name, to_qq):
        card_info_map = parse_card_group_info_map(self.zzconfig)
        self.send_card(card_name, card_info_map[card_name].id, to_qq, print_res=True)

    def fetch_pskey(self):
        # 如果未启用qq空间相关的功能，则不需要这个
        any_enabled = False
        for activity_enabled in [
            self.cfg.function_switches.get_ark_lottery,
            # self.cfg.function_switches.get_dnf_warriors_call and not self.disable_most_activities(),
        ]:
            if activity_enabled:
                any_enabled = True
        if not any_enabled:
            logger.warning("未启用领取QQ空间相关的功能，将跳过")
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
        qa = QzoneActivity(self, lr)

        # pskey过期提示：{'code': -3000, 'subcode': -4001, 'message': '请登录', 'notice': 0, 'time': 1601004332, 'tips': 'EE8B-284'}
        # 由于活动过期的判定会优先于pskey判定，需要需要保证下面调用的是最新的活动~
        qa.fetch_dnf_warriors_call_data()
        res = qa.do_dnf_warriors_call("fcg_receive_reward", "测试pskey是否过期", qa.zz().actbossRule.buyVipPrize, gameid=qa.zz().gameid, print_res=False)
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

    # --------------------------------------------阿拉德勇士征集令--------------------------------------------
    def dnf_warriors_call(self):
        # https://act.qzone.qq.com/vip/2020/dnf1126
        show_head_line("阿拉德勇士征集令")

        if not self.cfg.function_switches.get_dnf_warriors_call or self.disable_most_activities():
            logger.warning("未启用领取阿拉德勇士征集令功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        lr = self.fetch_pskey()
        if lr is None:
            return

        qa = QzoneActivity(self, lr)
        qa.dnf_warriors_call()

    # --------------------------------------------wegame国庆活动【秋风送爽关怀常伴】--------------------------------------------
    def wegame_guoqing(self):
        # https://dnf.qq.com/lbact/a20200922wegame/index.html
        show_head_line("wegame国庆活动【秋风送爽关怀常伴】")

        if not self.cfg.function_switches.get_wegame_guoqing or self.disable_most_activities():
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
            self.guide_to_bind_account("wegame国庆", "https://dnf.qq.com/lbact/a20200922wegame/index.html")

    def wegame_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_wegame_guoqing

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20200922wegame/")

    # --------------------------------------------史诗之路来袭活动合集--------------------------------------------
    def dnf_1224(self):
        # https://dnf.qq.com/lbact/a20201224aggregate/index.html
        show_head_line("史诗之路来袭活动合集")

        if not self.cfg.function_switches.get_dnf_1224 or self.disable_most_activities():
            logger.warning("未启用领取史诗之路来袭活动合集功能，将跳过")
            return

        self.check_dnf_1224()

        self.dnf_1224_op("勇士礼包", "730665")

        self.dnf_1224_op("30分签到礼包", "730666")
        check_days = self.get_dnf_1224_checkin_days()
        logger.info(color("fg_bold_cyan") + "当前已累积签到 {} 天".format(check_days))
        self.dnf_1224_op("3日礼包", "730663")
        self.dnf_1224_op("7日礼包", "730667")
        self.dnf_1224_op("15日礼包", "730668")

    def get_dnf_1224_checkin_days(self):
        res = self.dnf_1224_op("查询签到信息", "730670")
        return int(res["modRet"]["total"])

    def check_dnf_1224(self):
        res = self.dnf_1224_op("查询是否绑定", "730660", print_res=False)
        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1212213814-q4VCJQ-346329-722055"}, "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
        if len(res["modRet"]["jData"]) == 0:
            self.guide_to_bind_account("史诗之路来袭活动合集", "https://dnf.qq.com/lbact/a20201224aggregate/index.html")

    def dnf_1224_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_1224
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20201224aggregate/")

    # --------------------------------------------DNF闪光杯第三期--------------------------------------------
    def dnf_shanguang(self):
        # http://xinyue.qq.com/act/a20201221sgbpc/index.html
        show_head_line("DNF闪光杯第三期")

        if not self.cfg.function_switches.get_dnf_shanguang or self.disable_most_activities():
            logger.warning("未启用领取DNF闪光杯第三期活动合集功能，将跳过")
            return

        self.check_dnf_shanguang()

        # self.dnf_shanguang_op("报名礼", "724862")
        # self.dnf_shanguang_op("app专属礼", "724877")
        logger.warning(color("fg_bold_cyan") + "不要忘记前往网页手动报名并领取报名礼以及前往app领取一次性礼包")

        logger.warning(color("bold_yellow") + "本周已获得指定装备{}件，具体装备可去活动页面查看".format(self.query_dnf_shanguang_equip_count()))

        self.dnf_shanguang_op("周周闪光好礼", "724878")

        for i in range(6):
            res = self.dnf_shanguang_op("周周开大奖", "724879")
            if int(res["ret"]) != 0:
                break
            time.sleep(5)

        self.dnf_shanguang_op("每日登录游戏", "724881")
        self.dnf_shanguang_op("每日登录app", "724882")
        # self.dnf_shanguang_op("每日网吧登录", "724883")

        lottery_times = self.get_dnf_shanguang_lottery_times()
        logger.info(color("fg_bold_cyan") + "当前剩余闪光夺宝次数为 {} ".format(lottery_times))
        for i in range(lottery_times):
            self.dnf_shanguang_op("闪光夺宝", "724880")
            time.sleep(5)

    def get_dnf_shanguang_lottery_times(self):
        res = self.dnf_shanguang_op("闪光夺宝次数", "724885")
        return int(res["modRet"]["sOutValue3"])

    def query_dnf_shanguang_equip_count(self, print_warning=True):
        res = self.dnf_shanguang_op("输出当前周期爆装信息", "724876", print_res=False)
        equip_count = 0
        if "modRet" in res:
            info = AmesvrCommonModRet().auto_update_config(res["modRet"])
            if info.sOutValue2 != "" and info.sOutValue2 != "0":
                equip_count = len(info.sOutValue2.split(","))
        else:
            if print_warning: logger.warning(color("bold_yellow") + "是不是还没有报名？")

        return equip_count

    def check_dnf_shanguang(self):
        res = self.dnf_shanguang_op("报名礼", "724862", print_res=False)
        # {"ret": "99998", "msg": "请刷新页面，先绑定大区！谢谢！", "flowRet": {"iRet": "99998", "sLogSerialNum": "AMS-DNF-0924120415-8k2lUH-331515-703512", "iAlertSerial": "0", "sMsg": "请刷新页面，先绑定大区！谢谢！"}}
        if int(res["ret"]) == 99998:
            self.guide_to_bind_account("DNF闪光杯第三期", "http://xinyue.qq.com/act/a20201221sgbpc/index.html")

    def dnf_shanguang_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_shanguang

        weekDay = get_this_week_monday()

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "https://xinyue.qq.com/act/a20201221sgb",
                                   weekDay=weekDay,
                                   )

    # --------------------------------------------qq视频活动--------------------------------------------
    def qq_video(self):
        # https://m.film.qq.com/magic-act/110254/index.html
        show_head_line("qq视频活动")

        if not self.cfg.function_switches.get_qq_video or self.disable_most_activities():
            logger.warning("未启用领取qq视频活动功能，将跳过")
            return

        # note: 接入新活动的流程如下
        #   1. 电脑打开fiddler，手机连接fiddler的代理
        #   2. 手机QQ打开活动界面
        #   3. 点击任意按钮，从query_string中获取最新的act_id
        #   4. 依次点击下面各个行为对应的按钮，从query_string中获取最新的module_id

        self.check_qq_video()

        self.qq_video_op("幸运勇士礼包", "129838")
        self.qq_video_op("勇士见面礼-礼包", "129879")
        self.qq_video_op("勇士见面礼-令牌", "129875")

        self.qq_video_op("每日抽奖1次(需在活动页面开通QQ视频会员)", "129873")

        self.qq_video_op("在线30分钟", "129877")
        self.qq_video_op("累积3天", "129881")
        self.qq_video_op("累积7天", "129883")
        self.qq_video_op("累积15天", "129882")

    def check_qq_video(self):
        res = self.qq_video_op("幸运勇士礼包", "129838", print_res=False)
        # {"frame_resp": {"failed_condition": {"condition_op": 3, "cur_value": 0, "data_type": 2, "exp_value": 0, "type": 100418}, "msg": "", "ret": 0, "security_verify": {"iRet": 0, "iUserType": 0, "sAppId": "", "sBusinessId": "", "sInnerMsg": "", "sUserMsg": ""}}, "act_id": 108810, "data": {"button_txt": "关闭", "cdkey": "", "custom_list": [], "end_timestamp": -1, "ext_url": "", "give_type": 0, "is_mask_cdkey": 0, "is_pop_jump": 0, "item_share_desc": "", "item_share_title": "", "item_share_url": "", "item_sponsor_title": "", "item_sponsor_url": "", "item_tips": "", "jump_url": "", "jump_url_web": "", "lottery_item_id": "1601827185657s2238078729s192396s1", "lottery_level": 0, "lottery_name": "", "lottery_num": 0, "lottery_result": 0, "lottery_txt": "您当前还未绑定游戏帐号，请先绑定哦~", "lottery_url": "", "lottery_url_ext": "", "lottery_url_ext1": "", "lottery_url_ext2": "", "msg_title": "告诉我怎么寄给你", "need_bind": 0, "next_type": 2, "pop_jump_btn_title": "", "pop_jump_url": "", "prize_give_info": {"prize_give_status": 0}, "property_detail_code": 0, "property_detail_msg": "", "property_type": 0, "share_txt": "", "share_url": "", "source": 0, "sys_code": -904, "url_lottery": "", "user_info": {"addr": "", "name": "", "tel": "", "uin": ""}}, "module_id": 125890, "msg": "", "ret": 0, "security_verify": {"iRet": 0, "iUserType": 0, "sAppId": "", "sBusinessId": "", "sInnerMsg": "", "sUserMsg": ""}}
        if int(res["data"]["sys_code"]) == -904 and res["data"]["lottery_txt"] == "您当前还未绑定游戏帐号，请先绑定哦~":
            msg = "未绑定角色，请打开https://m.film.qq.com/magic-act/110254/index.html（需要使用手机打开）进行绑定，然后重新运行程序\n若无需该功能，可前往配置文件自行关闭该功能"
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
        act_id = "110254"
        extra_cookies = "; ".join([
            "",
            "appid=3000501",
            "main_login=qq",
            "vuserid={vuserid}".format(vuserid=self.vuserid),
        ])
        return self.get(ctx, self.urls.qq_video, type=type, option=option, act_id=act_id, module_id=module_id,
                        print_res=print_res, extra_cookies=extra_cookies)

    # --------------------------------------------10月女法师三觉活动--------------------------------------------
    def dnf_female_mage_awaken(self):
        # https://mwegame.qq.com/act/dnf/Mageawaken/index?subGameId=10014&gameId=10014&gameId=1006
        show_head_line("10月女法师三觉")

        if not self.cfg.function_switches.get_dnf_female_mage_awaken or self.disable_most_activities():
            logger.warning("未启用领取10月女法师三觉活动合集功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # fixme: 这个之后签到几天后再看看各个outvalue到底是啥含义
        logger.warning("这个之后签到几天后再看看各个outvalue到底是啥含义")
        checkin_days = self.query_dnf_female_mage_awaken_info()
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

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        qq = uin2qq(self.cfg.account_info.uin)
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(ctx, "comm.ams.game.qq.com", "group_k", "bb", iActivityId, iFlowId, print_res, "http://mwegame.qq.com/act/dnf/mageawaken/index1/",
                                  sArea=roleinfo.serviceID, serverId=roleinfo.serviceID,
                                  sRoleId=roleinfo.roleCode, sRoleName=quote_plus(roleinfo.roleName),
                                  uin=qq, skey=self.cfg.account_info.skey,
                                  nickName=quote_plus(dnf_helper_info.nickName), userId=dnf_helper_info.userId, token=quote_plus(dnf_helper_info.token),
                                  )

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
        logger.warning(color("fg_bold_green") + (
            "\n"
            "如果上面这个活动在助手里找不到了，可以试试看其他的活动\n"
            "如果所有活动的转发链接里都找不到token，那么只能手动抓包，从请求的cookie或post data中获取token信息了，具体可以百度 安卓 https 抓包\n"
            "下面给出几种推荐的方案\n"
            "1. 安卓下使用HttpCanary来实现对dnf助手抓包（开启http canary抓包后，打开助手，点击任意一个活动页面，然后去链接或cookie中查找token），可参考\n"
            "    1.1 https://httpcanary.com/zh-hans/\n"
            "    1.2 抓包流程可参考我录制的操作视频 https://www.bilibili.com/video/BV1az4y1k7bH\n"
            "2. 安卓下 VirtualXposed+JustTrustMe，然后在这里面安装dnf助手和qq，之后挂fiddler的vpn来完成抓包操作，可参考\n"
            "    2.1 https://www.jianshu.com/p/a818a0d0aa9f\n"
            "    2.2 https://testerhome.com/articles/18609\n"
            "    2.3 https://juejin.im/post/6844903602209685517\n"
            "    2.4 https://blog.csdn.net/hebbely/article/details/79248077\n"
            "    2.5 https://juejin.im/post/6844903831579394055\n"
            "    ps：简单说明下，fiddler用于抓https包，由于助手对网络请求做了证书校验，所以需要安装VirtualXposed+JustTrustMe，并在VirtualXposed中去安装运行助手，从而使其校验失效，能够让请求成功\n"
        ))

    # --------------------------------------------dnf助手排行榜活动--------------------------------------------
    def dnf_rank(self):
        # https://mwegame.qq.com/dnf/rankv2/index.html
        show_head_line("dnf助手排行榜")

        if not self.cfg.function_switches.get_dnf_rank or self.disable_most_activities():
            logger.warning("未启用领取dnf助手排行榜活动合集功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        if self.cfg.dnf_helper_info.token == "":
            logger.warning(color("fg_bold_yellow") + "未配置dnf助手相关信息，无法进行dnf助手排行榜相关活动，请按照下列流程进行配置")
            self.show_dnf_helper_info_guide()
            return

        # note: 获取鲜花（使用autojs去操作）
        logger.warning("获取鲜花请使用auto.js等自动化工具来模拟打开助手去执行对应操作")

        # 赠送鲜花
        self.dnf_rank_send_score()

        # 领取黑钻
        if self.dnf_rank_get_user_info().canGift == 0:
            logger.warning("12月5日开放黑钻奖励领取~")
        else:
            self.dnf_rank_receive_diamond("3天", "7020")
            self.dnf_rank_receive_diamond("7天", "7021")
            self.dnf_rank_receive_diamond("15天", "7022")
            # 新的黑钻改为使用amesvr去发送，且阉割为只有一个奖励了
            self.dnf_rank_receive_diamond_amesvr("7天黑钻")

        # 结束时打印下最新状态
        self.dnf_rank_get_user_info(print_res=True)

    def dnf_rank_send_score(self):
        id = 7  # 大硕
        name = "疯奶丶大硕"
        total_score = int(self.dnf_rank_get_user_info().score)
        ctx = "给{}({})打榜{}鲜花".format(id, name, total_score)
        if total_score <= 0:
            logger.info("{} 没有多余的鲜花，暂时不能进行打榜~".format(ctx))
            return

        return self.dnf_rank_op(ctx, self.urls.rank_send_score, id=id, score=total_score)

    def dnf_rank_get_user_info(self, print_res=False):
        res = self.dnf_rank_op("查询信息", self.urls.rank_user_info, print_res=print_res)

        user_info = RankUserInfo()
        try:
            user_info.auto_update_config(res["data"])
        except Exception as e:
            # {"res": 201, "msg": "重新登录后重试", "data": []}
            logger.debug("dnf_rank_get_user_info exception={}".format(e))
        return user_info

    def dnf_rank_receive_diamond(self, gift_name, gift_id):
        return self.dnf_rank_op('领取黑钻-{}'.format(gift_name), self.urls.rank_receive_diamond, gift_id=gift_id)

    def dnf_rank_receive_diamond_amesvr(self, ctx):
        try:
            iActivityId = self.urls.iActivityId_dnf_rank
            iFlowId = "723192"

            roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
            qq = uin2qq(self.cfg.account_info.uin)
            dnf_helper_info = self.cfg.dnf_helper_info

            res = self.amesvr_request(ctx, "comm.ams.game.qq.com", "group_k", "bb", iActivityId, iFlowId, True, "https://mwegame.qq.com/dnf/rankv2/index.html/",
                                      sArea=roleinfo.serviceID, serverId=roleinfo.serviceID, areaId=roleinfo.serviceID,
                                      sRoleId=roleinfo.roleCode, sRoleName=quote_plus(roleinfo.roleName),
                                      uin=qq, skey=self.cfg.account_info.skey,
                                      nickName=quote_plus(dnf_helper_info.nickName), userId=dnf_helper_info.userId, token=quote_plus(dnf_helper_info.token),
                                      )
        except Exception as e:
            logger.exception("dnf_rank_receive_diamond_amesvr出错了", exc_info=e)

    def dnf_rank_op(self, ctx, url, **params):
        qq = uin2qq(self.cfg.account_info.uin)
        info = self.cfg.dnf_helper_info
        return self.get(ctx, url, uin=qq, userId=info.userId, token=quote_plus(info.token), **params)

    # --------------------------------------------dnf助手双旦活动--------------------------------------------
    def dnf_helper_christmas(self):
        # https://mwegame.qq.com/act/dnf/christmas/index.html?subGameId=10014&gameId=10014&&gameId=1006
        show_head_line("dnf助手双旦")

        if not self.cfg.function_switches.get_dnf_helper_christmas or self.disable_most_activities():
            logger.warning("未启用领取dnf助手双旦活动合集功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        if self.cfg.dnf_helper_info.token == "":
            logger.warning(color("fg_bold_yellow") + "未配置dnf助手相关信息，无法进行dnf助手双旦相关活动，请按照下列流程进行配置")
            self.show_dnf_helper_info_guide()
            return

        self.dnf_helper_christmas_op("每日签到", "726989")

        self.dnf_helper_christmas_op("圣诞节 12/25", "727621")
        self.dnf_helper_christmas_op("元旦节 1/1", "727622")

        self.dnf_helper_christmas_op("累计1次", "727623")
        self.dnf_helper_christmas_op("累计3次", "727624")
        self.dnf_helper_christmas_op("累计5次", "727625")
        self.dnf_helper_christmas_op("累计7次", "727626")
        self.dnf_helper_christmas_op("累计11次", "727627")
        self.dnf_helper_christmas_op("累计14次", "727628")
        self.dnf_helper_christmas_op("累计18次", "727629")
        self.dnf_helper_christmas_op("累计21次", "727630")

        self.dnf_helper_christmas_op("抽奖", "727631")
        logger.info(color("bold_cyan") + "请自行前往助手活动页面填写身份信息，否则领取到实物奖励会无法发放（虽然应该没几个人会中实物奖<_<）")

    def dnf_helper_christmas_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_helper_christmas

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        qq = uin2qq(self.cfg.account_info.uin)
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(ctx, "comm.ams.game.qq.com", "group_k", "bb", iActivityId, iFlowId, print_res, "https://mwegame.qq.com/act/dnf/christmas/index.html",
                                  sArea=roleinfo.serviceID, serverId=roleinfo.serviceID,
                                  sRoleId=roleinfo.roleCode, sRoleName=quote_plus(roleinfo.roleName),
                                  uin=qq, skey=self.cfg.account_info.skey,
                                  nickName=quote_plus(dnf_helper_info.nickName), userId=dnf_helper_info.userId, token=quote_plus(dnf_helper_info.token),
                                  )

        # 1000017016: 登录态失效,请重新登录
        if res["flowRet"]["iRet"] == "700" and res["flowRet"]["sMsg"] == "登录态失效,请重新登录":
            logger.warning(color("fg_bold_yellow") + "dnf助手的登录态已过期，目前需要手动更新，具体操作流程如下")
            self.show_dnf_helper_info_guide()

        return res

    # --------------------------------------------dnf助手编年史活动--------------------------------------------
    def dnf_helper_chronicle(self):
        # dnf助手左侧栏
        show_head_line("dnf助手编年史")

        if not self.cfg.function_switches.get_dnf_helper_chronicle or self.disable_most_activities():
            logger.warning("未启用领取dnf助手编年史活动功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # 为了不与其他函数名称冲突，切让函数名称短一些，写到函数内部~
        url_wang = self.urls.dnf_helper_chronicle_wang_xinyue
        url_mwegame = self.urls.dnf_helper_chronicle_mwegame
        dnf_helper_info = self.cfg.dnf_helper_info
        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        area = roleinfo.serviceID
        partition = roleinfo.serviceID
        roleid = roleinfo.roleCode

        common_params = {
            "userId": dnf_helper_info.userId,
            "sPartition": partition,
            "sRoleId": roleid,
            "print_res": False,
        }

        # ------ 查询各种信息 ------
        def exchange_list():
            res = self.get("可兑换道具列表", url_wang, api="list/exchange", **common_params)
            return DnfHelperChronicleExchangeList().auto_update_config(res)

        def basic_award_list():
            res = self.get("基础奖励与搭档奖励", url_wang, api="list/basic", **common_params)
            return DnfHelperChronicleBasicAwardList().auto_update_config(res)

        def lottery_list():
            res = self.get("碎片抽奖奖励", url_wang, api="lottery/receive", **common_params)
            return DnfHelperChronicleLotteryList().auto_update_config(res)

        def getUserActivityTopInfo():
            res = self.post("活动基础状态信息", url_mwegame, "", api="getUserActivityTopInfo", **common_params)
            return DnfHelperChronicleUserActivityTopInfo().auto_update_config(res.get("data", {}))

        def _getUserTaskList():
            return self.post("任务信息", url_mwegame, "", api="getUserTaskList", **common_params)

        def getUserTaskList():
            res = _getUserTaskList()
            return DnfHelperChronicleUserTaskList().auto_update_config(res.get("data", {}))

        # ------ 领取各种奖励 ------

        def takeTaskAward(suffix, taskName, actionId, status, exp):
            actionName = "[{}-{}]".format(taskName, suffix)

            if status in [0, 2]:
                # 0-未完成，2-已完成未领取，但是助手签到任务在未完成的时候可以直接领取，所以这俩一起处理，在内部根据回包进行区分
                doActionIncrExp(actionName, actionId, exp)
            else:
                # 1 表示已经领取过
                logger.info("{}已经领取过了".format(actionName))

        def doActionIncrExp(actionName, actionId, exp):
            res = self.post("领取任务经验", url_mwegame, "", api="doActionIncrExp", actionId=actionId, **common_params)
            data = res.get("data", 0)
            if data != 0:
                logger.info("领取{}-{}，获取经验为{}，回包data={}".format(actionName, actionId, exp, data))
            else:
                logger.warning("{}尚未完成，无法领取哦~".format(actionName))

        def take_basic_award(awardInfo: DnfHelperChronicleBasicAwardInfo, selfGift=True):
            if selfGift:
                mold = 1  # 自己
                side = "自己"
            else:
                mold = 2  # 队友
                side = "队友"
            res = self.get("领取基础奖励", url_wang, api="send/basic", **common_params,
                           isLock=awardInfo.isLock, amsid=awardInfo.sLbCode, iLbSel1=awardInfo.iLbSel1, num=1, mold=mold)
            logger.info("领取{}的第{}个基础奖励: {}".format(side, awardInfo.sName, res.get("giftName", "出错啦")))

        def exchange_award(giftInfo: DnfHelperChronicleExchangeGiftInfo):
            res = self.get("兑换奖励", url_wang, api="send/exchange", **common_params,
                           exNum=1, iCard=giftInfo.iCard, amsid=giftInfo.sLbcode, iNum=giftInfo.iNum, isLock=giftInfo.isLock)
            logger.info("兑换奖励: {}".format(res.get("giftName", "出错啦")))

        def lottery():
            res = self.get("抽奖", url_wang, api="send/lottery", **common_params, amsid="lottery_0007", iCard=10)
            gift = res.get("giftName", "出错啦")
            beforeMoney = res.get("money", 0)
            afterMoney = res.get("value", 0)
            logger.info("抽奖结果为: {}，年史诗片：{}->{}".format(gift, beforeMoney, afterMoney))

        # ------ 实际逻辑 ------

        # 检查一下userid是否真实存在
        if self.cfg.dnf_helper_info.userId == "" or len(_getUserTaskList().get("data", {})) == 0:
            logger.warning(color("fg_bold_yellow") + "dnf助手的userId未配置或配置有误，当前值为[{}]（本活动只需要这个，不需要token），无法进行dnf助手编年史活动，请按照下列流程进行配置".format(self.cfg.dnf_helper_info.userId))
            self.show_dnf_helper_info_guide()
            return

        # 做任务
        logger.warning("dnf助手签到任务和浏览咨询详情页请使用auto.js等自动化工具来模拟打开助手去执行对应操作，当然也可以每天手动打开助手点一点-。-")

        # 领取任务奖励的经验
        taskInfo = getUserTaskList()
        if taskInfo.hasPartner:
            logger.info("搭档为{}".format(taskInfo.pUserId))
        else:
            logger.warning("目前尚无搭档，建议找一个，可以多领点东西-。-")
        for task in taskInfo.taskList:
            takeTaskAward("自己", task.name, task.mActionId, task.mStatus, task.mExp)
            if taskInfo.hasPartner:
                takeTaskAward("队友", task.name, task.pActionId, task.pStatus, task.pExp)

        # 领取基础奖励
        basicAwardList = basic_award_list()
        listOfBasicList = [(True, basicAwardList.basic1List)]
        if basicAwardList.hasPartner:
            listOfBasicList.append((False, basicAwardList.basic2List))
        hasTakenAnyBasicAward = False
        for selfGift, basicList in listOfBasicList:
            for award in basicList:
                if award.isLock == 0 and award.isUsed == 0:
                    # 已解锁，且未领取，则尝试领取
                    take_basic_award(award, selfGift)
                    hasTakenAnyBasicAward = True
        if not hasTakenAnyBasicAward:
            logger.info("目前没有新的可以领取的基础奖励，只能等升级咯~")

        # 根据配置兑换奖励
        exchangeList = exchange_list()
        exchangeGiftMap = {}
        for gift in exchangeList.gifts:
            exchangeGiftMap[gift.sLbcode] = gift

        if len(self.cfg.dnf_helper_info.chronicle_exchange_items) != 0:
            all_exchanged = True
            for ei in self.cfg.dnf_helper_info.chronicle_exchange_items:
                if ei.sLbcode not in exchangeGiftMap:
                    logger.error("未找到兑换项{}对应的配置，请参考reference_data/dnf助手编年史活动_可兑换奖励列表.json".format(ei.sLbcode))
                    continue

                gift = exchangeGiftMap[ei.sLbcode]
                if gift.usedNum >= int(gift.iNum):
                    logger.warning("{}已经达到兑换上限{}次, 将跳过".format(gift.sName, gift.iNum))
                    continue

                userInfo = getUserActivityTopInfo()
                if userInfo.point < int(gift.iCard):
                    all_exchanged = False
                    logger.warning("目前年史碎片数目为{}，不够兑换{}所需的{}个，将跳过后续优先级较低的兑换奖励".format(userInfo.point, gift.sName, gift.iCard))
                    break

                for i in range(ei.count):
                    exchange_award(gift)

            if all_exchanged:
                logger.info(color("fg_bold_yellow") + "似乎配置的兑换列表已到达兑换上限，建议开启抽奖功能，避免浪费年史碎片~")
        else:
            logger.info("未配置dnf助手编年史活动的兑换列表，若需要兑换，可前往配置文件进行调整")

        if self.cfg.dnf_helper_info.chronicle_lottery:
            userInfo = getUserActivityTopInfo()
            totalLotteryTimes = userInfo.point // 10
            logger.info("当前共有{}年史诗片，将进行{}次抽奖".format(userInfo.point, totalLotteryTimes))
            for i in range(totalLotteryTimes):
                lottery()
        else:
            logger.info("当前未启用抽奖功能，若奖励兑换完毕时，建议开启抽奖功能~")

        userInfo = getUserActivityTopInfo()
        logger.warning(color("fg_bold_yellow") + "账号 {} 当前编年史等级为LV{}({}) 本级经验：{}/{} 当前总获取经验为{} 剩余年史碎片为{}".format(
            self.cfg.name, userInfo.level, userInfo.levelName, userInfo.currentExp, userInfo.levelExp, userInfo.totalExp, userInfo.point,
        ))

    # --------------------------------------------管家蚊子腿--------------------------------------------
    def guanjia(self):
        # http://guanjia.qq.com/act/cop/202012dnf/
        show_head_line("管家蚊子腿")

        if not self.cfg.function_switches.get_guanjia or self.disable_most_activities():
            logger.warning("未启用领取管家蚊子腿活动合集功能，将跳过")
            return

        lr = self.fetch_guanjia_openid()
        if lr is None:
            return
        self.guanjia_lr = lr
        # 等一会，避免报错
        time.sleep(self.common_cfg.retry.request_wait_time)

        self.guanjia_common_gifts_op("电脑管家特权礼包", giftId="7546")
        self.guanjia_common_gifts_op("游戏助手礼包", giftId="7547")
        self.guanjia_common_gifts_op("回归勇士礼包", giftId="7548")

        self.guanjia_common_gifts_op("下载安装并登录电脑管家", giftId="7549")

        self.guanjia_common_gifts_op("每日游戏在线30分钟", giftId="7550")
        self.guanjia_common_gifts_op("每日登录游戏助手", giftId="7551")

        for i in range(10):
            res = self.guanjia_lottery_gifts_op("抽奖")
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
        res = self.guanjia_common_gifts_op("每日登录游戏助手", giftId="7551", print_res=False)
        return res["code"] in [7005, 29]

    def guanjia_common_gifts_op(self, ctx, giftId="", print_res=True):
        return self.guanjia_op(ctx, "comjoin", "1121", giftId=giftId, print_res=print_res)

    def guanjia_lottery_gifts_op(self, ctx, print_res=True):
        return self.guanjia_op(ctx, "lottjoin", "1120", print_res=print_res)

    def guanjia_op(self, ctx, api_name, act_id, giftId="", print_res=True):
        api = "{}_{}".format(api_name, act_id)
        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        extra_cookies = "__qc__openid={openid}; __qc__k={access_key};".format(
            openid=self.guanjia_lr.qc_openid,
            access_key=self.guanjia_lr.qc_k
        )
        return self.get(ctx, self.urls.guanjia, api=api, giftId=giftId, area_id=roleinfo.serviceID, charac_no=roleinfo.roleCode, charac_name=quote_plus(roleinfo.roleName),
                        extra_cookies=extra_cookies, is_jsonp=True, is_normal_jsonp=True, print_res=print_res)

    def fetch_guanjia_openid(self, print_warning=True):
        # 检查是否启用管家相关活动
        any_enabled = False
        for activity_enabled in [
            self.cfg.function_switches.get_guanjia and not self.disable_most_activities(),
        ]:
            if activity_enabled:
                any_enabled = True
        if not any_enabled:
            if print_warning: logger.warning("未启用管家相关活动，将跳过")
            return

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

    # --------------------------------------------hello语音奖励兑换--------------------------------------------
    def hello_voice(self):
        # https://dnf.qq.com/act/1192/f19665d784ac041d/index.html  （从hello语音app中兑换奖励页点开网页）
        show_head_line("hello语音奖励兑换功能（仅兑换，不包含获取奖励的逻辑）")

        if not self.cfg.function_switches.get_hello_voice or self.disable_most_activities():
            logger.warning("未启用hello语音奖励兑换功能，将跳过")
            return

        if self.cfg.hello_voice.hello_id == "":
            logger.warning("未配置hello_id，若需要该功能，请前往配置文件查看说明并添加该配置")
            return

        if not self.check_hello_voice_bind_role():
            return

        # ------封装函数-----------

        def getDayDui(type, packid, ctx):
            return self.do_hello_voice(ctx, "lotteryHellob", type=type, packid=packid)

        def getActDui(packid, ctx):
            while True:
                res = self.do_hello_voice(ctx, "lotteryTicket", packid=packid)
                # {"iRet": 0, "sMsg": " 恭喜您获得“黑钻3天”！", "jData": {"afterStatus": 0, "helloTicketCount": 4, "packid": null, "packname": "黑钻3天"}, "sSerial": "ULINK-DNF-1207140536-6PNeKs-228919-394635"}
                if res["iRet"] == 0 and res["jData"]["afterStatus"] == 0:
                    # 仍有剩余兑换次数，继续兑换
                    continue

                # 无兑换次数或本次兑换结束后无剩余次数
                # {"iRet": -1014, "sMsg": "兑换券不足", "jData": [], "sSerial": "ULINK-DNF-1207140538-vs2JQk-228919-378934"}
                # {"iRet": 0, "sMsg": " 恭喜您获得“黑钻7天”！", "jData": {"afterStatus": -1, "helloTicketCount": 0, "packid": null, "packname": "黑钻7天"}, "sSerial": "ULINK-DNF-1207140537-5gDMvR-228919-718017"}
                break

        try:
            # ------实际逻辑-----------

            self.do_hello_voice("领取新人礼包", "lotteryGift")

            # # 每天兑换1次
            # getDayDui(1, 1, "每天兑换-神秘契约礼盒（1天） - 200 Hello贝")
            # getDayDui(1, 2, "每天兑换-装备品级调整箱 - 400 Hello贝")

            # # 每周兑换1次
            # getDayDui(2, 1, "每周兑换-复活币礼盒（1个） - 450 Hello贝")
            # getDayDui(2, 2, "每周兑换-装备品级调整箱 - 600 Hello贝")
            # getDayDui(2, 3, "每周兑换-黑钻3天 - 550 Hello贝")
            # getDayDui(2, 4, "每周兑换-抗疲劳秘药（5点） - 400 Hello贝")

            # 每月兑换1次
            getDayDui(3, 1, "每月兑换-装备提升礼盒 - 900 Hello贝")
            getDayDui(3, 2, "每月兑换-时间引导石10个 - 600 Hello贝")
            getDayDui(3, 3, "每月兑换-装备提升礼盒 - 900 Hello贝")
            getDayDui(3, 4, "每月兑换-装扮合成器 - 600 Hello贝")

            # 活动奖励兑换
            getActDui(1, "黑钻3天兑换券")
            getActDui(2, "黑钻7天兑换券")
            getActDui(3, "时间引导石（10个）兑换券")
            getActDui(4, "升级券*1（lv95-99）兑换券")
            getActDui(5, "智慧的引导通行证*1兑换券")
            getActDui(6, "装备提升礼盒*1兑换券")

        except Exception as e:
            logger.error("hello_voice exception={}".format(e))

    def check_hello_voice_bind_role(self):
        data = self.do_hello_voice("检查账号绑定信息", "getRole", print_res=False)
        if data["iRet"] == -1011:
            # 未选择大区
            logger.warning(color("fg_bold_yellow") + "未绑定角色，请前往hello语音，点击左下方【首页】->左上角【游戏】->左上方【福利中心】->【DNF活动奖励&hello贝兑换】->在打开的网页中进行角色绑定")
            return False
        else:
            # 已选择大区
            roleInfo = HelloVoiceDnfRoleInfo().auto_update_config(data["jData"])
            logger.info("绑定角色信息: {}".format(roleInfo))
            return True

    def do_hello_voice(self, ctx, api, type="", packid="", print_res=True):
        return self.get(ctx, self.urls.hello_voice, api=api, hello_id=self.cfg.hello_voice.hello_id, type=type, packid=packid, print_res=print_res)

    # --------------------------------------------微信签到--------------------------------------------
    def wx_checkin(self):
        # 目前通过autojs实现
        return

        show_head_line("微信签到--临时版本，仅本地使用")

        # if not self.cfg.function_switches.wx_checkin:
        #     logger.warning("未启用微信签到功能，将跳过")
        #     return

        # re: 继续研究如何获取微信稳定的登陆态，也就是下面这四个东西（顺带新请求看看这个东西会变不） @2020-10-30 11:03:36 By Chen Ji
        #   QQ的登录态(前两个)似乎非常稳定，似乎只需要处理后面那俩，根据今天的测试，早上十一点半获取的token，下午三点再次运行的时候已经提示：微信身份态过期（缓存找不到）
        wx_login_cookies = self.make_cookie({
            # ----------QQ登录态----------
            # 登录态（这个似乎可以长期不用改动）
            "fsza_sk_t_q_at_101482157": "01EHSGBKRZ9ECXXWPF589HFY2M",

            # ----------WX登录态----------
            # 登录态 undone: 这个两小时就会过期，需要搞定这个~
            "fsza_sk_t_at_wxa817069bb040f860": "5840d4fd0603367b6ac9737a346f0987fa8bc622f996f0f78095ff6887536d13",
        })

        self.post("微信签到", 'https://gw.gzh.qq.com/awp-signin/register?id=260', {}, extra_cookies=wx_login_cookies)

        self.get("微信签到信息", 'https://gw.gzh.qq.com/awp-signin/check?id=260', extra_cookies=wx_login_cookies)

    # --------------------------------------------2020DNF嘉年华页面主页面签到--------------------------------------------
    def dnf_carnival(self):
        # https://dnf.qq.com/cp/a20201203carnival/index.html
        show_head_line("2020DNF嘉年华页面主页面签到")

        if not self.cfg.function_switches.get_dnf_carnival or self.disable_most_activities():
            logger.warning("未启用领取2020DNF嘉年华页面主页面签到活动合集功能，将跳过")
            return

        self.check_dnf_carnival()

        self.dnf_carnival_op("12.11-12.14 阶段一签到", "721945")
        self.dnf_carnival_op("12.15-12.18 阶段二签到", "722198")
        self.dnf_carnival_op("12.19-12.26 阶段三与全勤", "722199")

    def check_dnf_carnival(self):
        res = self.dnf_carnival_op("查询是否绑定", "722055", print_res=False)
        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1212213814-q4VCJQ-346329-722055"}, "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
        if len(res["modRet"]["jData"]) == 0:
            self.guide_to_bind_account("2020DNF嘉年华页面主页面签到", "https://dnf.qq.com/cp/a20201203carnival/index.html")

    def dnf_carnival_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_carnival

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201203carnival/")

    # --------------------------------------------2020DNF嘉年华直播--------------------------------------------
    def dnf_carnival_live(self):
        if not self.common_cfg.test_mode:
            # 仅限测试模式运行
            return

        # # https://dnf.qq.com/cp/a20201203carnival/index.html
        # show_head_line("2020DNF嘉年华直播")

        if not self.cfg.function_switches.get_dnf_carnival_live or self.disable_most_activities():
            logger.warning("未启用领取2020DNF嘉年华直播活动合集功能，将跳过")
            return

        self.check_dnf_carnival_live()

        def query_watch_time():
            res = self.dnf_carnival_live_op("查询观看时间", "722482", print_res=False)
            info = AmesvrCommonModRet().auto_update_config(res["modRet"])
            return int(info.sOutValue3)

        def watch_remaining_time():
            self.dnf_carnival_live_op("记录完成一分钟观看", "722476")

            current_watch_time = query_watch_time()
            remaining_time = 15 * 8 - current_watch_time
            logger.info("账号 {} 当前已观看{}分钟，仍需观看{}分钟".format(self.cfg.name, current_watch_time, remaining_time))

        def query_used_lottery_times():
            res = self.dnf_carnival_live_op("查询获奖次数", "725567", print_res=False)
            info = AmesvrCommonModRet().auto_update_config(res["modRet"])
            return int(info.sOutValue1)

        def lottery_remaining_times():
            total_lottery_times = query_watch_time() // 15
            used_lottery_times = query_used_lottery_times()
            remaining_lottery_times = total_lottery_times - used_lottery_times
            logger.info("账号 {} 抽奖次数信息：总计={} 已使用={} 剩余={}".format(self.cfg.name, total_lottery_times, used_lottery_times, remaining_lottery_times))
            if remaining_lottery_times == 0:
                logger.warning("没有剩余次数，将不进行抽奖")
                return

            for i in range(remaining_lottery_times):
                res = self.dnf_carnival_live_op("{}. 抽奖".format(i + 1), "722473")
                if res["ret"] != "0":
                    logger.warning("出错了，停止抽奖，剩余抽奖次数为{}".format(remaining_lottery_times - i))
                    break

        watch_remaining_time()
        lottery_remaining_times()

    def check_dnf_carnival_live(self):
        res = self.dnf_carnival_live_op("查询是否绑定", "722472", print_res=False)
        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1212213814-q4VCJQ-346329-722055"}, "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
        if len(res["modRet"]["jData"]) == 0:
            self.guide_to_bind_account("2020DNF嘉年华直播", "https://dnf.qq.com/cp/a20201203carnival/index.html")

    def dnf_carnival_live_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_carnival_live

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201203carnival/")

    # --------------------------------------------DNF福利中心兑换--------------------------------------------
    def dnf_welfare(self):
        # http://dnf.qq.com/cp/a20190312welfare/index.htm
        show_head_line("DNF福利中心兑换")

        if not self.cfg.function_switches.get_dnf_welfare or self.disable_most_activities():
            logger.warning("未启用领取DNF福利中心兑换活动功能，将跳过")
            return

        self.check_dnf_welfare()

        def exchange_package(sContent):
            key = "dnf_welfare_exchange_package"

            # 检查是否已经兑换过
            account_db = load_db_for(self.cfg.name)
            if key in account_db and account_db[key].get(sContent, False):
                logger.warning("已经兑换过【{}】，不再尝试兑换".format(sContent))
                return

            self.dnf_welfare_op("兑换口令-{}".format(sContent), "558229", sContent=quote_plus(quote_plus(quote_plus(sContent))))

            # 本地标记已经兑换过
            def callback(account_db):
                if key not in account_db:
                    account_db[key] = {}

                account_db[key][sContent] = True

            update_db_for(self.cfg.name, callback)

        sContents = [
            "DNF1224",
            "你好啊勇士",
            "2021欧气满满",
            "321fight",
        ]
        for sContent in sContents:
            exchange_package(sContent)

        # 登陆游戏领福利
        self.dnf_welfare_login_gifts_op("第一个 2020.12.20 - 2020.12.23 登录游戏", "724929")
        self.dnf_welfare_login_gifts_op("第二个 2020.12.24 - 2020.12.26 登录游戏", "724930")
        self.dnf_welfare_login_gifts_op("第三个 2020.12.28 - 2021.01.03 登录游戏", "724936")

        # 分享礼包
        self.dnf_welfare_login_gifts_op("分享奖励领取", "724940")

    def get_dnf_welfare_userinfo(self):
        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo

        res = self.get("查询角色信息", self.urls.get_game_role_list, game="dnf", area=roleinfo.serviceID, sAMSTargetAppId="", platid="", partition="", print_res=False, is_jsonp=True, need_unquote=False)
        return AmesvrQueryRole().auto_update_config(res)

    def check_dnf_welfare(self):
        res = self.dnf_welfare_op("查询是否绑定", "558227", print_res=False)
        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1212213814-q4VCJQ-346329-722055"}, "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
        if len(res["modRet"]["jData"]) == 0:
            self.guide_to_bind_account("DNF福利中心兑换", "http://dnf.qq.com/cp/a20190312welfare/index.htm")

    def dnf_welfare_op(self, ctx, iFlowId, sContent="", print_res=True):
        iActivityId = self.urls.iActivityId_dnf_welfare

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20190312welfare/",
                                   sContent=sContent)

    def dnf_welfare_login_gifts_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_dnf_welfare_login_gifts

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        checkInfo = self.get_dnf_welfare_userinfo()

        checkparam = quote_plus(quote_plus(checkInfo.checkparam))

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20190312welfare/",
                                   sArea=roleinfo.serviceID, sPartition=roleinfo.serviceID, sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
                                   sRoleId=roleinfo.roleCode, sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
                                   md5str=checkInfo.md5str, ams_checkparam=checkparam, checkparam=checkparam)

    # --------------------------------------------DNF共创投票--------------------------------------------
    def dnf_dianzan(self):
        # https://dnf.qq.com/cp/a20201126version/index.shtml
        show_head_line("DNF共创投票")

        if not self.cfg.function_switches.get_dnf_dianzan or self.disable_most_activities():
            logger.warning("未启用领取DNF共创投票活动功能，将跳过")
            return

        self.check_dnf_dianzan()

        db_key = "dnf_dianzan"
        pagesize = 10

        # 投票
        def today_dianzan():
            account_db = load_db_for(self.cfg.name)
            today = get_today()

            if db_key not in account_db:
                account_db[db_key] = {}
            if today not in account_db[db_key]:
                account_db[db_key][today] = 0
            if "usedContentIds" not in account_db[db_key]:
                account_db[db_key]["usedContentIds"] = []

            dianzanSuccessCount = account_db[db_key][today]
            if dianzanSuccessCount >= 20:
                logger.info("今日之前的运行中，已经完成20次点赞了，本次将不执行")
                return

            for contentId in get_dianzan_contents_with_cache():
                # 不论投票是否成功，都标记为使用过的内容
                account_db[db_key]["usedContentIds"].append(contentId)
                if dianzan(dianzanSuccessCount + 1, contentId):
                    dianzanSuccessCount += 1
                    if dianzanSuccessCount >= 20:
                        logger.info("今日已经累计点赞20个，将停止点赞")
                        break

            account_db[db_key][today] = dianzanSuccessCount

            save_db_for(self.cfg.name, account_db)

        def get_dianzan_contents_with_cache():
            db = load_db()
            account_db = load_db_for(self.cfg.name)

            usedContentIds = []
            if db_key in account_db:
                usedContentIds = account_db[db_key].get("usedContentIds", [])

            def filter_used_contents(contentIds):
                validContentIds = []
                for contentId in contentIds:
                    if contentId not in usedContentIds:
                        validContentIds.append(contentId)

                logger.info(validContentIds)

                return validContentIds

            if db_key in db:
                contentIds = db[db_key]["contentIds"]

                validContentIds = filter_used_contents(contentIds)

                if len(validContentIds) >= 20:
                    # 本地仍有不少于20个内容可供点赞，直接使用本地内容
                    return validContentIds

            return filter_used_contents(get_dianzan_contents())

        def get_dianzan_contents():
            logger.info("本地无点赞目标，或缓存的点赞目标均已点赞过，需要重新拉取，请稍后~")
            contentIds = []

            for iCategory2 in range(1, 8 + 1):
                newContentIds, total = getWorksData(iCategory2, 1)
                contentIds.extend(newContentIds)

                # 获取剩余页面
                totalPage = math.ceil(total / 10)
                for page in range(2, totalPage):
                    newContentIds, _ = getWorksData(iCategory2, page)
                    contentIds.extend(newContentIds)

            logger.info("获取所有内容ID共计{}个，将保存到本地，具体如下：{}".format(len(contentIds), contentIds))

            def _update_db(db):
                if db_key not in db:
                    db[db_key] = {}

                db[db_key]["contentIds"] = contentIds

            update_db(_update_db)

            return contentIds

        def getWorksData(iCategory2, page):
            ctx = "查询点赞内容-{}-{}".format(iCategory2, page)
            res = self.get(ctx, self.urls.query_dianzan_contents, iCategory1=20, iCategory2=iCategory2, page=page, pagesize=pagesize, is_jsonp=True, is_normal_jsonp=True)
            return [v["iContentId"] for v in res["jData"]["data"]], int(res["jData"]["total"])

        def dianzan(idx, iContentId) -> bool:
            res = self.get("今日第{}次投票，目标为{}".format(idx, iContentId), self.urls.dianzan, iContentId=iContentId, is_jsonp=True, is_normal_jsonp=True)
            return int(res["iRet"]) == 0

        # 进行今天剩余的点赞操作
        today_dianzan()

        # 查询点赞信息
        self.query_dnf_dianzan()

        # 领取点赞奖励
        self.dnf_dianzan_op("累计 10票", "725276")
        self.dnf_dianzan_op("累计 25票", "725340")
        self.dnf_dianzan_op("累计100票", "725341")
        self.dnf_dianzan_op("累计200票", "725342")

    def query_dnf_dianzan(self):
        res = self.dnf_dianzan_op("查询点赞信息", "725348", print_res=False)
        info = AmesvrCommonModRet().auto_update_config(res["modRet"])

        logger.warning(color("fg_bold_yellow") + "DNF共创投票活动当前已投票{}次，奖励领取状态为{}".format(info.sOutValue1, info.sOutValue2))

    def check_dnf_dianzan(self):
        res = self.dnf_dianzan_op("查询是否绑定", "725330", print_res=False)
        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1212213814-q4VCJQ-346329-722055"}, "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
        if len(res["modRet"]["jData"]) == 0:
            self.guide_to_bind_account("DNF共创投票", "https://dnf.qq.com/cp/a20201126version/index.shtml")

    def dnf_dianzan_op(self, ctx, iFlowId, sContent="", print_res=True):
        iActivityId = self.urls.iActivityId_dnf_dianzan

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201126version/")

    # --------------------------------------------心悦app理财礼卡--------------------------------------------
    def xinyue_financing(self):
        if not self.common_cfg.test_mode:
            # undone: 心悦app理财礼卡活动似乎还有一些问题，先本地运行一段时间再放出去
            return

        # https://xinyue.qq.com/act/app/xyjf/a20171031lclk/index1.shtml
        show_head_line("心悦app理财礼卡")

        logger.info(color("fg_bold_yellow") + "TODO：等理财礼卡测试OK记得移除上面的测试模式限定，并把功能放出去（功能开关、理财卡列表配置项）")

        if not self.cfg.function_switches.get_xinyue_financing or self.disable_most_activities():
            logger.warning("未启用领取心悦app理财礼卡活动合集功能，将跳过")
            return

        selectedCards = self.cfg.xinyue_financing_card_names
        if len(selectedCards) == 0:
            logger.warning("未配置心悦app理财礼卡活动选择的理财卡类型(xinyue_financing_card_names)，将跳过")
            return

        logger.info(color("fg_bold_green") + "当前配置的理财卡列表为: {}".format(selectedCards))

        type2name = {
            "type1": "体验版周卡",
            "type2": "升级版周卡",
            "type3": "体验版月卡",
            "type4": "升级版月卡",
        }

        # ------------- 封装函数 ----------------
        def query_gpoints():
            res = AmesvrCommonModRet().auto_update_config(self.xinyue_financing_op("查询G分", "409361", print_res=False)["modRet"])
            return int(res.sOutValue2)

        def query_card_taken_map():
            res = AmesvrCommonModRet().auto_update_config(self.xinyue_financing_op("查询G分", "409361", print_res=False)["modRet"])
            statusList = res.sOutValue3.split('|')

            cardTakenMap = {}
            for i in range(1, 4 + 1):
                name = type2name["type{}".format(i)]
                if int(statusList[i]) > 0:
                    taken = True
                else:
                    taken = False

                cardTakenMap[name] = taken

            return cardTakenMap

        def show_financing_info():
            info_map = get_financing_info_map()

            heads = ["理财卡名称", "当前状态", "累计收益", "剩余天数", "结束日期"]
            colSizes = [10, 8, 8, 8, 10]
            logger.info(color("bold_green") + tableify(heads, colSizes))
            for name, info in info_map.items():
                if name not in selectedCards:
                    # 跳过未选择的卡
                    continue

                if info.buy:
                    status = "已购买"
                else:
                    status = "未购买"

                logger.info(color("fg_bold_cyan") + tableify([name, status, info.totalIncome, info.leftTime, info.endTime], colSizes))

        def get_financing_info_map():
            financingInfoMap = json.loads(self.xinyue_financing_op("查询各理财卡信息", "409714", print_res=False)["modRet"]["jData"]["arr"])  # type: dict
            financingTimeInfoMap = json.loads(self.xinyue_financing_op("查询理财礼卡天数信息", "409396", print_res=False)["modRet"]["jData"]["arr"])  # type: dict

            info_map = {}
            for typ, financingInfo in financingInfoMap.items():
                info = XinyueFinancingInfo()

                info.name = type2name[typ]
                if financingInfo["status"] == 0:
                    info.buy = False
                else:
                    info.buy = True
                info.totalIncome = financingInfo["totalIncome"]

                if typ in financingTimeInfoMap["alltype"]:
                    info.leftTime = financingTimeInfoMap["alltype"][typ]["leftime"]
                if "opened" in financingTimeInfoMap and typ in financingTimeInfoMap["opened"]:
                    info.endTime = financingTimeInfoMap["opened"][typ]["endtime"]

                info_map[info.name] = info

            return info_map

        # ------------- 正式逻辑 ----------------
        try:
            pass
            gPoints = query_gpoints()
            startPoints = gPoints
            logger.info("当前G分为{}".format(startPoints))

            # 活动规则
            # 1、购买理财礼卡：每次购买理财礼卡成功后，当日至其周期结束，每天可以领取相应的收益G分，当日如不领取，则视为放弃
            # 2、购买限制：每个帐号仅可同时拥有两种理财礼卡，到期后则可再次购买
            # ps：推荐购买体验版月卡和升级版月卡
            financingCardsToBuyAndMap = {
                ## 名称   购买价格   购买FlowId    领取FlowId
                "体验版周卡": (20, "408990", "507439"),  # 5分/7天/35-20=15/2分收益每天
                "升级版周卡": (80, "409517", "507441"),  # 20分/7天/140-80=60/8.6分收益每天
                "体验版月卡": (300, "409534", "507443"),  # 25分/30天/750-300=450/15分收益每天
                "升级版月卡": (600, "409537", "507444"),  # 60分/30天/1800-600=1200/40分收益每天
            }

            cardInfoMap = get_financing_info_map()
            cardTakenMap = query_card_taken_map()
            for cardName in selectedCards:
                if cardName not in financingCardsToBuyAndMap:
                    logger.warning("没有找到名为【{}】的理财卡，请确认是否配置错误".format(cardName))
                    continue

                buyPrice, buyFlowId, takeFlowId = financingCardsToBuyAndMap[cardName]
                cardInfo = cardInfoMap[cardName]
                taken = cardTakenMap[cardName]
                # 如果尚未购买（或过期），则购买
                if not cardInfo.buy:
                    if gPoints >= buyPrice:
                        self.xinyue_financing_op("购买{}".format(cardName), buyFlowId)
                        gPoints -= buyPrice
                    else:
                        logger.warning("积分不够，将跳过购买~，购买{}需要{}G分，当前仅有{}G分".format(cardName, buyPrice, gPoints))
                        continue

                # 此处以确保购买，尝试领取
                if taken:
                    logger.warning("今日已经领取过{}了，本次将跳过".format(cardName))
                else:
                    self.xinyue_financing_op("领取{}".format(cardName), takeFlowId)

            newGPoints = query_gpoints()
            delta = newGPoints - startPoints
            logger.warning("")
            logger.warning(color("fg_bold_yellow") + "账号 {} 本次心悦理财礼卡操作共获得 {} G分（ {} -> {} ）".format(self.cfg.name, delta, startPoints, newGPoints))
            logger.warning("")

            show_financing_info()
        except Exception as e:
            logger.error("处理心悦app理财礼卡出错了", exc_info=e)

    def xinyue_financing_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_xinyue_financing

        plat = 3  # app
        extraStr = quote_plus('"mod1":"1","mod2":"0","mod3":"x27"')

        return self.amesvr_request(ctx, "comm.ams.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "https://xinyue.qq.com/act/app/xyjf/a20171031lclk/index1.shtml",
                                   plat=plat, extraStr=extraStr)

    # --------------------------------------------dnf漂流瓶--------------------------------------------
    def dnf_drift(self):
        # https://dnf.qq.com/cp/a20201211driftm/index.html
        show_head_line("dnf漂流瓶")

        if not self.cfg.function_switches.get_dnf_drift or self.disable_most_activities():
            logger.warning("未启用领取dnf漂流瓶活动功能，将跳过")
            return

        self.check_dnf_drift()

        def send_friend_invitation(typStr, flowid, dayLimit):
            send_count = 0
            for sendQQ in self.cfg.drift_send_qq_list:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)
                res = self.dnf_drift_op("发送{}好友邀请-{}赠送2积分".format(typStr, sendQQ), flowid, sendQQ=sendQQ, moduleId="2")

                send_count += 1
                if int(res["ret"]) != 0 or send_count >= dayLimit:
                    logger.warning("已达到本日邀请上限({})，将停止邀请".format(dayLimit))
                    return

        def take_friend_awards(typStr, type, moduleId, take_points_flowid):
            page = 1
            while True:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)

                queryRes = self.dnf_drift_op("拉取接受的{}好友列表".format(typStr), "725358", page=str(page), type=type)
                if int(queryRes["ret"]) != 0 or queryRes["modRet"]["jData"]["iTotal"] == 0:
                    logger.warning("没有更多接收邀请的好友了，停止领取积分")
                    return

                for friend_info in queryRes["modRet"]["jData"]["jData"]:
                    takeRes = self.dnf_drift_op("邀请人领取{}邀请{}的积分".format(typStr, friend_info["iUin"]), take_points_flowid, acceptId=friend_info["id"], moduleId=moduleId)
                    if int(takeRes["ret"]) != 0:
                        logger.warning("似乎已达到今日上限，停止领取")
                        return
                    if takeRes["modRet"]["iRet"] != 0:
                        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1230002652-mtPJXE-348890-726267"}, "modRet": {"all_item_list": [], "bHasSendFailItem": "0", "bRealSendSucc": 1, "dTimeNow": "2020-12-30 00:26:52", "iActivityId": "381537", "iDbPackageAutoIncId": 0, "iLastMpResultCode": 2037540212, "iPackageGroupId": "", "iPackageId": "", "iPackageIdCnt": "", "iPackageNum": "1", "iReentry": 0, "iRet": 100002, "iWecatCardResultCode": 0, "isCmemReEntryOpen": "yes", "jData": {"iPackageId": "0", "sPackageName": ""}, "jExtend": "", "sAmsSerialNum": "AMS-DNF-1230002652-mtPJXE-348890-726267", "sItemMsg": null, "sMidasCouponRes": "null\n", "sMidasPresentRes": "null\n", "sMsg": "非常抱歉，您此次活动领取次数已达最大，不能领取！", "sPackageCDkey": "", "sPackageLimitCheckCode": "2227289:70008,", "sPackageName": "", "sPackageRealFlag": "0", "sVersion": "V1.0.1752b92.00a0875.20201210155534"}, "ret": "0", "msg": ""}
                        logger.warning("出错了，停止领取，具体原因请看上一行的sMsg")
                        return

                page += 5

        # 01 这一切都是命运的选择
        # 礼包海
        self.dnf_drift_op("捞一个", "725715")
        # 丢礼包，日限8次
        send_friend_invitation("普通", "725819", 8)
        take_friend_awards("普通", "1", "4", "726267")

        # 02 承认吧，这是友情的羁绊
        # 那些年错过的他，日限5次
        send_friend_invitation("流失", "726069", 5)
        take_friend_awards("流失", "2", "6", "726269")
        # 礼包领取站
        self.dnf_drift_op("流失用户领取礼包", "727230")

        # 03 来吧，吾之宝藏
        # 积分夺宝
        totalPoints, remainingPoints = self.query_dnf_drift_points()
        remainingLotteryTimes = remainingPoints // 4
        logger.info(color("bold_yellow") + "当前积分为{}，总计可进行{}次抽奖。历史累计获取积分数为{}".format(remainingPoints, remainingLotteryTimes, totalPoints))
        for i in range(remainingLotteryTimes):
            self.dnf_drift_op("开始夺宝 - 第{}次".format(i + 1), "726379")

        # 04 在线好礼站
        self.dnf_drift_op("在线30min", "725675", moduleId="2")
        self.dnf_drift_op("累计3天礼包", "725699", moduleId="0", giftId="1437440")
        self.dnf_drift_op("累计7天礼包", "725699", moduleId="0", giftId="1437441")
        self.dnf_drift_op("累计15天礼包", "725699", moduleId="0", giftId="1437442")

        # 分享
        self.dnf_drift_op("分享领取礼包", "726345")

    def query_dnf_drift_points(self):
        res = self.dnf_drift_op("查询基础信息", "726353")
        info = AmesvrCommonModRet().auto_update_config(res["modRet"])
        total, remaining = int(info.sOutValue2), int(info.sOutValue2) - int(info.sOutValue1) * 4
        return total, remaining

    def check_dnf_drift(self):
        res = self.dnf_drift_op("查询是否绑定", "725357", print_res=False)
        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1212213814-q4VCJQ-346329-722055"}, "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
        typ = random.choice([1, 2])
        activity_url = "https://dnf.qq.com/cp/a20201211driftm/index.html?sId=0252c9b811d66dc1f0c9c6284b378e40&type={}".format(typ)
        if len(res["modRet"]["jData"]) == 0:
            self.guide_to_bind_account("dnf漂流瓶", activity_url)

        if is_first_run("check_dnf_drift"):
            msg = "求帮忙做一下邀请任务0-0  只用在点击确定按钮后弹出的活动页面中点【确认接受邀请】就行啦（这条消息只会出现一次）"
            logger.warning(color("bold_cyan") + msg)
            win32api.MessageBox(0, msg, "帮忙接受一下邀请0-0", win32con.MB_ICONWARNING)
            webbrowser.open(activity_url)

    def dnf_drift_op(self, ctx, iFlowId, page="", type="", moduleId="", giftId="", acceptId="", sendQQ="", print_res=True):
        iActivityId = self.urls.iActivityId_dnf_drift

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201211driftm/",
                                   page=page, type=type, moduleId=moduleId, giftId=giftId, acceptId=acceptId, sendQQ=sendQQ)

    # --------------------------------------------DNF马杰洛的规划第二期--------------------------------------------
    def majieluo(self):
        # https://dnf.qq.com/cp/a20201224welfare/index.html
        show_head_line("DNF马杰洛的规划第二期")

        if not self.cfg.function_switches.get_majieluo or self.disable_most_activities():
            logger.warning("未启用领取DNF马杰洛的规划第二期活动功能，将跳过")
            return

        self.check_majieluo()

        def query_stone_count():
            res = self.majieluo_op("查询当前时间引导石数量", "727334", print_res=False)
            info = AmesvrCommonModRet().auto_update_config(res["modRet"])
            return int(info.sOutValue1)

        def take_share_award():
            queryRes = self.majieluo_op("【分享】查询已接受分享邀请的好友列表", "727340")
            if queryRes["modRet"]["jData"]["iTotal"] == 0:
                logger.warning("没有接收分享的好友，无法领取奖励")
                return

            for raw_friend_info in queryRes["modRet"]["jData"]["jData"]:
                friend_info = MajieluoShareInfo().auto_update_config(raw_friend_info)
                if friend_info.iShareLottery == '0':
                    self.majieluo_op("【分享】好友扫码，分享者+9", "727276", invitee=friend_info.iInvitee)
                if friend_info.iLostLottery == '0':
                    self.majieluo_op("【分享】好友为流失玩家，分享者额外+10", "727281", invitee=friend_info.iInvitee)
                if friend_info.iAssistLottery == '0':
                    self.majieluo_op("【分享】好友为流失玩家且登录游戏（即助力好友），额外再+10", "727285", invitee=friend_info.iInvitee)

        # 01 马杰洛的见面礼
        self.majieluo_op("领取见面礼", "727212")

        # 02 马杰洛的幸运骰子
        self.majieluo_op("【每日签到】摇一摇", "727213")
        self.majieluo_op("【每日签到】点数乘2倍", "727217")

        # 03 黑钻送好友
        for receiverQQ in self.cfg.majieluo_receiver_qq_list:
            logger.info("等待2秒，避免请求过快")
            time.sleep(2)
            # {"ret": "700", "msg": "非常抱歉，您还不满足参加该活动的条件！", "flowRet": {"iRet": "700", "sLogSerialNum": "AMS-DNF-1226165046-1QvZiG-350347-727218", "iAlertSerial": "0", "iCondNotMetId": "1412917", "sMsg": "您每天最多为2名好友赠送黑钻~", "sCondNotMetTips": "您每天最多为2名好友赠送黑钻~"}, "failedRet": {"793123": {"iRuleId": "793123", "jRuleFailedInfo": {"iFailedRet": 700, "iCondId": "1412917", "iCondParam": "sCondition1", "iCondRet": "2"}}}}
            res = self.majieluo_op("【赠礼】发送赠送邀请-{}".format(receiverQQ), "727218", receiver=receiverQQ, receiverName=quote_plus("小号"), inviterName=quote_plus("大号"))
            if int(res["ret"]) == 700:
                logger.warning("今日赠送上限已到达，将停止~")
                break

            self.majieluo_op("【赠礼】领取引导石+9", "727290", receiver=receiverQQ)

        # 04 分享得好礼（看看逻辑，可能不做）
        take_share_award()

        # 05 分享得好礼
        # 提取石头并领取提取奖励
        stoneCount = query_stone_count()
        logger.warning(color("bold_yellow") + "当前共有{}个引导石".format(stoneCount))

        now = datetime.datetime.now()
        thisMonthLastDay = calendar.monthrange(now.year, now.month)[1]

        takeStone = False
        if stoneCount >= 1000:
            # 达到1000个
            self.majieluo_op("提取时间引导石", "727229", giftNum="10")
            takeStone = True
        elif now.day == thisMonthLastDay or str(now.date()) == "2021-01-21":
            # 今天是本月最后一天（因为新的一个月会清零）或者是活动最后一天
            self.majieluo_op("提取时间引导石", "727229", giftNum=str(stoneCount // 100))
            takeStone = True
        else:
            logger.info("当前未到最后领取期限（本月末或活动结束时），且石头数目不足1000，故不尝试提取")

        if takeStone:
            self.majieluo_op("【提取福利】提取数量大于1000", "727246")
            self.majieluo_op("【提取福利】提取数量大于600小于1000", "727240")
            self.majieluo_op("【提取福利】提取数量<=600", "727232")

    def check_majieluo(self):
        res = self.majieluo_op("查询是否绑定", "727124", print_res=False)
        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1212213814-q4VCJQ-346329-722055"}, "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
        if len(res["modRet"]["jData"]) == 0:
            urls = [
                # 二维码分享
                "https://dnf.qq.com/cp/a20201224welfarem/index.html?inviter=1054073896&pt=1",
            ]
            self.guide_to_bind_account("DNF马杰洛的规划第二期", random.choice(urls))

    def majieluo_op(self, ctx, iFlowId, invitee="", giftNum="", receiver="", receiverName="", inviterName="", print_res=True):
        iActivityId = self.urls.iActivityId_majieluo

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201224welfare/",
                                   invitee=invitee, giftNum=giftNum, receiver=receiver, receiverName=receiverName, inviterName=inviterName)

    # --------------------------------------------暖冬好礼活动--------------------------------------------
    def warm_winter(self):
        # https://dnf.qq.com/lbact/a20200911lbz3dns/index.html
        show_head_line("暖冬好礼活动")

        if not self.cfg.function_switches.get_warm_winter or self.disable_most_activities():
            logger.warning("未启用领取暖冬好礼活动功能，将跳过")
            return

        self.check_warm_winter()

        def get_lottery_times():
            res = self.warm_winter_op("查询剩余抽奖次数", "728476", print_res=False)
            # "sOutValue1": "279:2:1",
            val = res["modRet"]["sOutValue1"]
            jfId, total, remaining = [int(v) for v in val.split(':')]
            return total, remaining

        def get_checkin_days():
            res = self.warm_winter_op("查询签到信息", "723178")
            return int(res["modRet"]["total"])

        # 01 勇士齐聚阿拉德
        self.warm_winter_op("四个礼盒随机抽取", "723167")

        # 02 累计签到领豪礼
        self.warm_winter_op("签到礼包", "723165")
        logger.info(color("fg_bold_cyan") + "当前已累积签到 {} 天".format(get_checkin_days()))
        self.warm_winter_op("签到3天礼包", "723170")
        self.warm_winter_op("签到5天礼包", "723171")
        self.warm_winter_op("签到7天礼包", "723172")
        self.warm_winter_op("签到10天礼包", "723173")
        self.warm_winter_op("签到15天礼包", "723174")

        # 03 累计签到抽大奖
        self.warm_winter_op("1.在WeGame启动DNF", "723175")
        self.warm_winter_op("2.游戏在线30分钟", "723176")
        total_lottery_times, lottery_times = get_lottery_times()
        logger.info(color("fg_bold_cyan") + "即将进行抽奖，当前剩余抽奖资格为{}，累计获取{}次抽奖机会".format(lottery_times, total_lottery_times))
        for i in range(lottery_times):
            res = self.warm_winter_op("每日抽奖", "723177")
            if res.get('ret', "0") == "600":
                # {"ret": "600", "msg": "非常抱歉，您的资格已经用尽！", "flowRet": {"iRet": "600", "sLogSerialNum": "AMS-DNF-1031000622-s0IQqN-331515-703957", "iAlertSerial": "0", "sMsg": "非常抱歉！您的资格已用尽！"}, "failedRet": {"762140": {"iRuleId": "762140", "jRuleFailedInfo": {"iFailedRet": 600}}}}
                break

    def check_warm_winter(self):
        res = self.warm_winter_op("查询是否绑定", "723162", print_res=False)
        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1212213814-q4VCJQ-346329-722055"}, "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
        if len(res["modRet"]["jData"]) == 0:
            self.guide_to_bind_account("暖冬好礼", "https://dnf.qq.com/lbact/a20200911lbz3dns/index.html")

    def warm_winter_op(self, ctx, iFlowId, print_res=True):
        iActivityId = self.urls.iActivityId_warm_winter

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20200911lbz3dns/")

    # --------------------------------------------辅助函数--------------------------------------------
    def get(self, ctx, url, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True, extra_cookies="", **params):
        return self.network.get(ctx, self.format(url, **params), pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote, extra_cookies)

    def post(self, ctx, url, data, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True, extra_cookies="", **params):
        return self.network.post(ctx, self.format(url, **params), data, pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote, extra_cookies)

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
            "sArea": "", "serverId": "", "areaId": "", "nickName": "", "sRoleId": "", "sRoleName": "", "uin": "", "skey": "", "userId": "", "token": "",
            "iActionId": "", "iGoodsId": "", "sBizCode": "", "partition": "", "iZoneId": "", "platid": "", "sZoneDesc": "", "sGetterDream": "",
            "date": date,
            "dzid": "",
            "page": "",
            "iPackageId": "",
            "isLock": "", "amsid": "", "iLbSel1": "", "num": "", "mold": "", "exNum": "", "iCard": "", "iNum": "", "actionId": "",
            "plat": "", "extraStr": "",
            "sContent": "", "sPartition": "", "sAreaName": "", "md5str": "", "ams_checkparam": "", "checkparam": "",
            "type": "", "moduleId": "", "giftId": "", "acceptId": "", "sendQQ": "",
            "invitee": "", "giftNum": "", "receiver": "", "receiverName": "", "inviterName": "",
        }

        # 首先将默认参数添加进去，避免format时报错
        merged_params = {**default_params, **params}

        # # 需要url encode一下，否则如果用户配置的值中包含&等符号时，会影响后续实际逻辑
        # quoted_params = {k: quote_plus(str(v)) for k, v in merged_params.items()}

        # 将参数全部填充到url的参数中
        urlRendered = url.format(**merged_params)

        # 过滤掉没有实际赋值的参数
        return filter_unused_params(urlRendered)

    def get_month(self):
        now = datetime.datetime.now()
        return "%4d%02d" % (now.year, now.month)

    def getMoneyFlowTime(self, year, month, day, hour, minute, second):
        return "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(year, month, day, hour, minute, second)

    def amesvr_request(self, ctx, amesvr_host, sServiceDepartment, sServiceType, iActivityId, iFlowId, print_res, eas_url, **data_extra_params):
        data = self.format(self.urls.amesvr_raw_data,
                           sServiceDepartment=sServiceDepartment, sServiceType=sServiceType, eas_url=quote_plus(eas_url),
                           iActivityId=iActivityId, iFlowId=iFlowId, **data_extra_params)

        return self.post(ctx, self.urls.amesvr, data,
                         amesvr_host=amesvr_host, sServiceDepartment=sServiceDepartment, sServiceType=sServiceType,
                         iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
                         print_res=print_res)

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

    def guide_to_bind_account(self, activity_name, activity_url):
        msg = "当前账号【{}】未在活动页面绑定角色，请点击右下角的【确定】按钮后，在自动弹出的【{}】活动页面进行绑定，然后重新运行程序\n若无需该功能，可前往配置文件自行关闭该功能".format(self.cfg.name, activity_name)
        logger.warning(color("bold_cyan") + msg)
        win32api.MessageBox(0, msg, "需绑定账号", win32con.MB_ICONWARNING)
        webbrowser.open(activity_url)
        exit(-1)

    def disable_most_activities(self):
        return self.cfg.function_switches.disable_most_activities


def watch_live():
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    RunAll = True
    indexes = [1]
    if RunAll:
        indexes = [i + 1 for i in range(len(cfg.account_configs))]

    totalTime = 2 * 60 + 5  # 为了保险起见，多执行5分钟
    logger.info("totalTime={}".format(totalTime))

    for t in range(totalTime):
        timeStart = datetime.datetime.now()
        logger.info(color("bold_yellow") + "开始执行第{}分钟的流程".format(t + 1))
        for idx in indexes:  # 从1开始，第i个
            account_config = cfg.account_configs[idx - 1]
            if not account_config.is_enabled() or account_config.cannot_bind_dnf:
                logger.warning("账号被禁用或无法绑定DNF，将跳过")
                continue

            djcHelper = DjcHelper(account_config, cfg.common)
            djcHelper.check_skey_expired()

            djcHelper.dnf_carnival_live()

        totalUsed = (datetime.datetime.now() - timeStart).total_seconds()
        if totalUsed < 60:
            waitTime = 60.1 - totalUsed
            logger.info(color("bold_cyan") + "本轮累积用时{}秒，将休息{}秒".format(totalUsed, waitTime))
            time.sleep(waitTime)


if __name__ == '__main__':
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    RunAll = False
    indexes = [1]
    if RunAll:
        indexes = [i + 1 for i in range(len(cfg.account_configs))]

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]

        show_head_line("预先获取第{}个账户[{}]的skey".format(idx, account_config.name), color("fg_bold_yellow"))

        if not account_config.is_enabled():
            logger.warning("账号被禁用，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]

        show_head_line("开始处理第{}个账户[{}]".format(idx, account_config.name), color("fg_bold_yellow"))

        if not account_config.is_enabled():
            logger.warning("账号被禁用，将跳过")
            continue

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
        # djcHelper.wegame_guoqing()
        # djcHelper.djc_operations()
        # djcHelper.dnf_female_mage_awaken()
        # djcHelper.send_card_by_name("独立成团打副本", "1054073896")
        # djcHelper.wx_checkin()
        # djcHelper.dnf_female_mage_awaken()
        # djcHelper.xinyue_sailiyam()
        # djcHelper.dnf_rank()
        # djcHelper.dnf_warriors_call()
        # djcHelper.dnf_helper_chronicle()
        # djcHelper.hello_voice()
        # djcHelper.dnf_carnival()
        # djcHelper.ark_lottery()
        # djcHelper.xinyue_financing()
        # djcHelper.dnf_carnival_live()
        # djcHelper.dnf_welfare()
        # djcHelper.dnf_dianzan()
        # djcHelper.dnf_drift()
        # djcHelper.majieluo()
        # djcHelper.dnf_helper_christmas()
        # djcHelper.dnf_shanguang()
        # djcHelper.warm_winter()
        # djcHelper.guanjia()
        # djcHelper.dnf_1224()
        djcHelper.qq_video()
