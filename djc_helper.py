import platform
import random
import string
import subprocess
import webbrowser

import pyperclip
import win32api

import json_parser
from dao import *
from game_info import get_game_info, get_game_info_by_bizcode
from network import *
from qq_login import QQLogin
from sign import getMillSecondsUnix
from urls import Urls


# DNF蚊子腿小助手
class DjcHelper:
    first_run_flag_file = os.path.join(first_run_dir, "init")
    first_run_auto_login_mode_flag_file = os.path.join(first_run_dir, "auto_login_mode")
    first_run_promot_flag_file = os.path.join(first_run_dir, "promot")

    local_saved_skey_file = os.path.join(cached_dir, ".saved_skey.{}.json")

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
        sys.exit(-1)

    def update_skey_qr_login(self, query_data):
        qqLogin = QQLogin(self.common_cfg)
        loginResult = qqLogin.qr_login()
        self.save_uin_skey(loginResult.uin, loginResult.skey)

    def update_skey_auto_login(self, query_data):
        self.show_tip_on_first_run_auto_login_mode()

        qqLogin = QQLogin(self.common_cfg)
        ai = self.cfg.account_info
        loginResult = qqLogin.login(ai.account, ai.password)
        self.save_uin_skey(loginResult.uin, loginResult.skey)

    def save_uin_skey(self, uin, skey):
        self.memory_save_uin_skey(uin, skey)

        self.local_save_uin_skey(uin, skey)

    def local_save_uin_skey(self, uin, skey):
        # 本地缓存
        with open(self.get_local_saved_skey_file(), "w", encoding="utf-8") as sf:
            loginResult = {
                "uin": str(uin),
                "skey": str(skey),
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
            logger.debug("读取本地缓存的skey信息，具体内容如下：{}".format(loginResult))

    def get_local_saved_skey_file(self):
        return self.local_saved_skey_file.format(self.cfg.name)

    def memory_save_uin_skey(self, uin, skey):
        # 保存到内存中
        self.cfg.updateUinSkey(uin, skey)

        # uin, skey更新后重新初始化网络相关
        self.init_network()

    # --------------------------------------------获取角色信息和游戏信息--------------------------------------------

    def get_bind_role_list(self):
        # 查询全部绑定角色信息
        res = self.get("获取道聚城各游戏的绑定角色列表", self.urls.query_bind_role_list, print_res=False)
        self.bizcode_2_bind_role_map = {}
        for roleinfo_dict in res["data"]:
            role_info = GameRoleInfo()
            role_info.auto_update_config(roleinfo_dict)
            self.bizcode_2_bind_role_map[role_info.sBizCode] = role_info

        # 检查道聚城是否已绑定dnf角色信息，若未绑定则警告（这里不停止运行是因为可以不配置领取dnf的道具）
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定【地下城与勇士】的角色信息，请前往道聚城app进行绑定")

        if self.cfg.mobile_game_role_info.enabled():
            # 检查道聚城是否已绑定手游角色信息，若未绑定则警告并停止运行
            bizcode = self.get_mobile_game_info().bizCode
            if bizcode not in self.bizcode_2_bind_role_map:
                logger.warning("未在道聚城绑定【{}】的角色信息，请前往道聚城app进行绑定。若想绑定其他手游则调整配置中的手游名称，若不启用则将手游名称调整为无".format(get_game_info_by_bizcode(bizcode).bizName))
                subprocess.Popen("npp_portable/notepad++.exe -n63 config.toml")
                os.system("PAUSE")
                exit(-1)
            role_info = self.bizcode_2_bind_role_map[bizcode]
            if not role_info.is_mobile_game():
                logger.warning("【{}】是端游，不是手游。若想绑定其他手游则调整配置中的手游名称，若不启用则将手游名称调整为无".format(get_game_info_by_bizcode(bizcode).bizName))
                subprocess.Popen("npp_portable/notepad++.exe -n63 config.toml")
                os.system("PAUSE")
                exit(-1)

    def get_mobile_game_info(self):
        # 如果游戏名称设置为【任意手游】，则从绑定的手游中随便挑一个
        if self.cfg.mobile_game_role_info.use_any_binded_mobile_game():
            for bizcode, bind_role_info in self.bizcode_2_bind_role_map.items():
                if bind_role_info.is_mobile_game():
                    self.cfg.mobile_game_role_info.game_name = bind_role_info.sRoleInfo.gameName
                    logger.warning("当前游戏名称配置为任意手游，将从道聚城已绑定的手游中随便选一个，挑选为：{}".format(self.cfg.mobile_game_role_info.game_name))
                    break
        return get_game_info(self.cfg.mobile_game_role_info.game_name)

    # --------------------------------------------各种操作--------------------------------------------
    def run(self):
        self.check_first_run()

        run_mode_dict = {
            "pre_run": self.pre_run,
            "normal": self.normal_run,
        }
        run_mode_dict[self.cfg.run_mode]()

    def check_first_run(self):
        self.show_tip_on_first_run_promot()
        self.show_tip_on_first_run_any()

    # 预处理阶段
    def pre_run(self):
        logger.info("预处理阶段，请按照提示进行相关操作")

        # 指引获取uin/skey/角色信息等
        self.check_skey_expired()

        logger.info("uin/skey已经填写完成，请确保已正确填写手游的名称信息，并已在道聚城app中绑定dnf和该手游的角色信息后再进行后续流程")

        # 尝试获取绑定的角色信息
        self.get_bind_role_list()

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

        # 最后提示
        logger.warning("当前账号的基础配置已完成，请在自动打开的config.toml中将本账号({})的run_mode配置的值修改为normal并保存后，再次运行即可".format(self.cfg.name))
        logger.warning("更多信息，请查看README.md/CHANGELOG.md以及使用文档目录中相关文档")

        subprocess.Popen("npp_portable/notepad++.exe -n39 config.toml")

        os.system("PAUSE")

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
        # 心悦国庆活动
        self.xinyue_guoqing()

        # 黑钻礼包
        self.get_heizuan_gift()

        # 腾讯游戏信用相关礼包
        self.get_credit_xinyue_gift()

    # --------------------------------------------道聚城--------------------------------------------
    def djc_operations(self):
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
        logger.warning("账号 {} 本次道聚城操作共获得 {} 个豆子（历史总获取： {} -> {}  余额： {} -> {} ）".format(self.cfg.name, delta, old_allin, new_allin, old_balance, new_balance))

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

        # 完成《礼包达人》
        cfg = self.cfg.mobile_game_role_info
        if cfg.enabled():
            game_info = self.get_mobile_game_info()
            role_info = self.bizcode_2_bind_role_map[game_info.bizCode].sRoleInfo
            giftInfos = self.get_mobile_game_gifts()
            if len(giftInfos) == 0:
                logger.warning("未找到手游【{}】的有效七日签到配置，请换个手游，比如王者荣耀".format(game_info.bizName))
                return
            dayIndex = datetime.datetime.now().weekday()  # 0-周一...6-周日，恰好跟下标对应
            giftInfo = giftInfos[dayIndex]
            self.get("3.2 一键领取{}日常礼包-{}".format(cfg.game_name, giftInfo.sTask), self.urls.recieve_game_gift,
                     bizcode=game_info.bizCode, iruleId=giftInfo.iRuleId,
                     systemID=role_info.systemID, sPartition=role_info.areaID, channelID=role_info.channelID, channelKey=role_info.channelKey,
                     roleCode=role_info.roleCode, sRoleName=role_info.roleName)
        else:
            logger.info("未启用自动完成《礼包达人》任务功能")

    def take_task_awards_and_exchange_items(self):
        # 领取奖励
        # 领取《礼包达人》
        self.take_task_award("4.1.1", "100066", "礼包达人")
        # 领取《绝不错亿》
        self.take_task_award("4.1.2", "100040", "绝不错亿")
        # 领取《活跃度银宝箱》
        self.take_task_award("4.1.3", "100001", "活跃度银宝箱")
        # 领取《活跃度金宝箱》
        self.take_task_award("4.1.4", "100002", "活跃度金宝箱")

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

    def query_all_extra_info(self):
        """
        已废弃，不再需要手动查询该信息
        """
        # 获取玩家的dnf角色列表
        self.query_dnf_rolelist()
        # 获取玩家的手游角色列表
        self.query_mobile_game_rolelist()

        # # 显示所有可以兑换的道具列表，note：当不知道id时调用
        # self.query_dnf_gifts()

    def query_dnf_rolelist(self):
        """
        已废弃，不再需要手动查询该信息
        """
        ctx = "获取账号({})的dnf角色列表".format(self.cfg.name)
        game_info = get_game_info("地下城与勇士")
        roleinfo = self.bizcode_2_bind_role_map["dnf"].sRoleInfo
        roleListJsonRes = self.get(ctx, self.urls.get_game_role_list, game=game_info.gameCode, sAMSTargetAppId=game_info.wxAppid, area=roleinfo.serviceID, platid="", partition="", is_jsonp=True, print_res=False)
        roleLists = json_parser.parse_role_list(roleListJsonRes)
        lines = []
        lines.append("")
        lines.append("+" * 40)
        lines.append(ctx)
        if len(roleLists) != 0:
            for idx, role in enumerate(roleLists):
                lines.append("\t第{:2d}个角色信息：\tid = {}\t 名字 = {}".format(idx + 1, role.roleid, role.rolename))
        else:
            lines.append("\t未查到dnf服务器id={}上的角色信息，请确认服务器id已填写正确或者在对应区服已创建角色".format(roleinfo.serviceID))
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
        logger.warning("账号 {} 本次心悦相关操作共获得 {} 个成就点（ {} -> {} ）".format(self.cfg.name, delta, old_info.score, new_info.score))

        # 查询下心悦组队进度
        teaminfo = self.query_xinyue_teaminfo(print_res=False)
        if teaminfo.id != "":
            logger.warning("账号 {} 当前队伍进度为 {}/20".format(self.cfg.name, teaminfo.score))
        else:
            logger.warning("账号 {} 当前尚无有效心悦队伍，可考虑加入或查看文档使用本地心悦组队功能".format(self.cfg.name))

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
        return self.xinyue_op(ctx, self.urls.xinyue_iActivityId_battle_ground, iFlowId, package_id, print_res, lqlevel, teamid)

    def xinyue_op(self, ctx, iActivityId, iFlowId, package_id="", print_res=True, lqlevel=1, teamid=""):
        return self.post(ctx, self.urls.xinyue, self.xinyue_flow_data(iActivityId, iFlowId, package_id, lqlevel, teamid), iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId), print_res=print_res)

    def xinyue_flow_data(self, iActivityId, iFlowId, package_id="", lqlevel=1, teamid=""):
        # 网站上特邀会员不论是游戏家G几，调用doAction(flowId,level)时level一律传1，而心悦会员则传入实际的567对应心悦123
        if lqlevel < 5:
            lqlevel = 1
        return self.format(self.urls.xinyue_raw_data, iActivityId=iActivityId, iFlowId=iFlowId, package_id=package_id, lqlevel=lqlevel, teamid=teamid)

    # 心悦国庆活动
    def xinyue_guoqing(self):
        # https://xinyue.qq.com/act/a20200910dnf/index.html
        actId = self.urls.xinyue_iActivityId_guoqing
        self.xinyue_op("验证幸运用户", actId, "700301")
        self.xinyue_op("幸运勇士", actId, "700288")
        self.xinyue_op("特邀充值礼包", actId, "700433")
        self.xinyue_op("V1充值礼包", actId, "700452")
        self.xinyue_op("V2充值礼包", actId, "700454")
        self.xinyue_op("V3充值礼包", actId, "700455")
        self.xinyue_op("特邀升级礼", actId, "700456")
        self.xinyue_op("心悦会员礼", actId, "700457")
        self.xinyue_op("每日在线30分钟", actId, "700458")
        self.xinyue_op("国庆七日签到", actId, "700462")
        self.xinyue_op("惊喜礼包", actId, "700511")
        self.xinyue_op("App礼包", actId, "701088")

    # --------------------------------------------黑钻--------------------------------------------
    def get_heizuan_gift(self):
        # https://dnf.qq.com/act/blackDiamond/gift.shtml
        if not self.cfg.get_heizuan_gift:
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
        self.get("每月信用星级礼包", self.urls.credit_gift)
        # https://gamecredit.qq.com/static/web/index.html#/gift-pack
        self.get("腾讯游戏信用-高信用即享礼包", self.urls.credit_xinyue_gift, gift_group=1)
        self.get("腾讯游戏信用-高信用&游戏家即享礼包", self.urls.credit_xinyue_gift, gift_group=2)

    # --------------------------------------------辅助函数--------------------------------------------
    def get(self, ctx, url, pretty=False, print_res=True, is_jsonp=False, **params):
        return self.network.get(ctx, self.format(url, **params), pretty, print_res, is_jsonp)

    def post(self, ctx, url, data, pretty=False, print_res=True, is_jsonp=False, **params):
        return self.network.post(ctx, self.format(url, **params), data, pretty, print_res, is_jsonp)

    def format(self, url, **params):
        endTime = datetime.datetime.now()
        startTime = endTime - datetime.timedelta(days=int(365 / 12 * 5))
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


if __name__ == '__main__':
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    for idx, account_config in enumerate(cfg.account_configs):
        idx += 1
        logger.info("开始处理第{}个账户[{}]".format(idx, account_config.name))

        djcHelper = DjcHelper(account_config, cfg.common)
        # djcHelper.run()
        djcHelper.check_skey_expired()
        # djcHelper.query_all_extra_info()
        # djcHelper.exchange_items()
        # djcHelper.xinyue_operations()
        # djcHelper.try_join_fixed_xinyue_team()
        # djcHelper.get_heizuan_gift()
        # djcHelper.get_credit_xinyue_gift()
        # djcHelper.query_mobile_game_rolelist()
        # djcHelper.complete_tasks()
        djcHelper.get_bind_role_list()

        if cfg.common._debug_run_first_only or True:
            logger.warning("调试开关打开，不再处理后续账户")
            break
