import math
import string
import subprocess
from urllib.parse import quote_plus

import pyperclip

import json_parser
from black_list import check_in_black_list
from dao import *
from game_info import get_game_info, get_game_info_by_bizcode
from network import *
from qq_login import QQLogin, LoginResult
from qzone_activity import QzoneActivity
from setting import *
from sign import getMillSecondsUnix
from urls import Urls, get_ams_act_desc, get_not_ams_act_desc
from util import show_head_line, get_this_week_monday


# DNF蚊子腿小助手
class DjcHelper:
    first_run_flag_file = os.path.join(first_run_dir, "init")
    first_run_auto_login_mode_flag_file = os.path.join(first_run_dir, "auto_login_mode")
    first_run_promot_flag_file = os.path.join(first_run_dir, "promot")
    first_run_document_flag_file = os.path.join(first_run_dir, "document")
    first_run_use_old_config_flag_file = os.path.join(first_run_dir, "use_old_config")
    first_run_config_ui_flag_file = os.path.join(first_run_dir, "config_ui")

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
            4. DNF蚊子腿小助手配置工具.exe
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

    def show_tip_on_first_run_config_ui(self):
        filename = self.first_run_config_ui_flag_file
        title = "配置工具"
        tips = """
        现已添加简易版配置工具，大家可以双击【DNF蚊子腿小助手配置工具.exe】进行体验~
                """
        loginfo = "首次运行弹出配置工具提示"

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
                _title = f"第{i + 1}/{show_count}次提示 {title}"
            win32api.MessageBox(0, tips, _title, win32con.MB_ICONWARNING)

        # 创建该文件，从而避免再次弹出错误
        with open(filename, "w", encoding="utf-8") as f:
            f.write("ok")

    def check_skey_expired(self):
        query_data = self.query_balance("判断skey是否过期", print_res=False)
        if str(query_data['ret']) == "0":
            # skey尚未过期，则重新刷一遍，主要用于从qq空间获取的情况
            account_info = self.cfg.account_info
            self.save_uin_skey(account_info.uin, account_info.skey, self.vuserid)
        else:
            # 已过期，更新skey
            logger.info("")
            logger.warning(f"账号({self.cfg.name})的skey已过期，即将尝试更新skey")
            self.update_skey(query_data)

        # skey获取完毕后，检查是否在黑名单内
        check_in_black_list(self.cfg.account_info.uin)

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
            f"       {js_code}\n"
            "-- 如果上述代码执行报错，可能是因为浏览器不支持，这时候可以复制下面的代码进行上述操作\n"
            "  执行后，应该会显示一个可点开的内容，戳一下会显示各个cookie的内容，然后手动在里面查找uin和skey即可\n"
            f"       {fallback_js_code}\n"
            "3. 将uin/skey的值分别填写到config.toml中对应配置的值中即可\n"
            "4. 填写dnf的区服和手游的区服信息到config.toml中\n"
            "5. 正常使用还需要填写完成后再次运行脚本，获得角色相关信息，并将信息填入到config.toml中\n"
            "\n"
            f"具体信息为：ret={query_data['ret']} msg={query_data['msg']}"
        ))
        # 打开配置界面
        cfgFile = "./config.toml"
        localCfgFile = "./config.toml.local"
        if os.path.isfile(localCfgFile):
            cfgFile = localCfgFile
        subprocess.Popen(f"npp_portable/notepad++.exe -n53 {cfgFile}")
        # 复制js代码到剪贴板，方便复制
        pyperclip.copy(js_code)
        # 打开活动界面
        os.popen("start https://dnf.qq.com/lbact/a20200716wgmhz/index.html?wg_ad_from=loginfloatad")
        # 提示
        input("\n完成上述操作后点击回车键即可退出程序，重新运行即可...")
        exit(-1)

    def update_skey_qr_login(self, query_data):
        qqLogin = QQLogin(self.common_cfg)
        loginResult = qqLogin.qr_login(name=self.cfg.name)
        self.save_uin_skey(loginResult.uin, loginResult.skey, loginResult.vuserid)

    def update_skey_auto_login(self, query_data):
        self.show_tip_on_first_run_auto_login_mode()

        qqLogin = QQLogin(self.common_cfg)
        ai = self.cfg.account_info
        loginResult = qqLogin.login(ai.account, ai.password, name=self.cfg.name)
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
            logger.debug(f"本地保存skey信息，具体内容如下：{loginResult}")

    def local_load_uin_skey(self):
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_skey_file()):
            return

        with open(self.get_local_saved_skey_file(), "r", encoding="utf-8") as f:
            try:
                loginResult = json.load(f)
            except json.decoder.JSONDecodeError as e:
                logger.error(f"账号 {self.cfg.name} 的skey缓存已损坏，将视为已过期")
                return

            self.memory_save_uin_skey(loginResult["uin"], loginResult["skey"])
            self.vuserid = loginResult.get("vuserid", "")
            logger.debug(f"读取本地缓存的skey信息，具体内容如下：{loginResult}")

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
                    logger.warning(f"当前手游名称配置为任意手游，将从道聚城已绑定的手游中随便选一个，挑选为：{self.cfg.mobile_game_role_info.game_name}")
                    break

            if not found_binded_game:
                return None

        return get_game_info(self.cfg.mobile_game_role_info.game_name)

    # --------------------------------------------各种操作--------------------------------------------
    def run(self, user_buy_info: BuyInfo):
        self.normal_run(user_buy_info)

    def check_first_run(self):
        self.show_tip_on_first_run_config_ui()
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
                logger.warning(color("fg_bold_green") + "！！！请注意，我说的是手游，不是DNF！！！")
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
                    logger.info(f"{roleinfo.gameName}: ({roleinfo.serviceName}-{roleinfo.roleName}-{roleinfo.roleCode})")
            else:
                logger.warning("当前账号未启用道聚城相关功能")

        return binded

    def check_mobile_game_bind(self):
        # 检查配置的手游是否有效
        gameinfo = self.get_mobile_game_info()
        if gameinfo is None:
            logger.warning(color("fg_bold_yellow") + "当前手游名称配置为【任意手游】，但未在道聚城找到任何绑定的手游，请前往道聚城绑定任意一个手游，如王者荣耀")
            return False

        # 检查道聚城是否已绑定该手游的角色，若未绑定则警告并停止运行
        bizcode = gameinfo.bizCode
        if bizcode not in self.bizcode_2_bind_role_map:
            logger.warning(color("fg_bold_yellow") + f"未在道聚城绑定手游【{get_game_info_by_bizcode(bizcode).bizName}】的角色信息，请前往道聚城app进行绑定。")
            logger.warning(color("fg_bold_cyan") + "若想绑定其他手游则调整config.toml配置中的手游名称，" + color("fg_bold_blue") + "若不启用则将手游名称调整为无")
            return False

        # 检查这个游戏是否是手游
        role_info = self.bizcode_2_bind_role_map[bizcode]
        if not role_info.is_mobile_game():
            logger.warning(color("fg_bold_yellow") + f"【{get_game_info_by_bizcode(bizcode).bizName}】是端游，不是手游。")
            logger.warning(color("fg_bold_cyan") + "若想绑定其他手游则调整config.toml配置中的手游名称，" + color("fg_bold_blue") + "若不启用则将手游名称调整为无")
            return False

        return True

    # 正式运行阶段
    def normal_run(self, user_buy_info: BuyInfo):
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

        # 心悦app理财礼卡
        self.xinyue_financing()

        # 心悦猫咪
        self.xinyue_cat()

        # 心悦app周礼包
        self.xinyue_weekly_gift()

        # dnf论坛签到
        self.dnf_bbs_signin()

        # 会员关怀
        self.vip_mentor()

        # DNF福利中心兑换
        self.dnf_welfare()

        if user_buy_info.is_active():
            show_head_line("以下为付费期间才会运行的短期活动", msg_color=color("bold_cyan"))
            self.paied_activities()
        else:
            if user_buy_info.total_buy_month != 0:
                msg = f"账号{user_buy_info.qq}的付费内容已到期，到期时间点为{user_buy_info.expire_at}。"
            else:
                msg = f"账号{user_buy_info.qq}未购买付费内容。"
            msg += "\n因此2021-02-06之后添加的短期新活动将被跳过，如果想要启用该部分内容，可扫描目录中的付款码付费激活。目前定价为5元每月，购买后QQ私聊我付款截图、使用QQ即可。"
            msg += "\n2021-02-06之前添加的所有活动不受影响，仍可继续使用。"
            # note: 更新新的活动时记得更新这个列表
            paied_activities = [
                "dnf助手编年史活动",
                "管家蚊子腿",
                "DNF马杰洛的规划",
            ]
            if len(paied_activities) != 0:
                msg += "\n目前受影响的活动如下："
                msg += "\n" + "\n".join([f'    {idx + 1:2d}. {act_name}' for idx, act_name in enumerate(paied_activities)])
            else:
                msg += "\n目前尚无需要付费的短期活动，当新的短期活动出现时会及时加入~"
            logger.warning(color("bold_yellow") + msg)

    def paied_activities(self):
        # re: 更新新的活动时记得更新上面的列表，以及urls.py的not_ams_activities

        # dnf助手编年史活动
        self.dnf_helper_chronicle()

        # 管家蚊子腿
        self.guanjia()

        # DNF马杰洛的规划
        self.majieluo()

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

        # dnf漂流瓶
        self.dnf_drift()

        # 暖冬好礼活动
        self.warm_winter()

        # DNF共创投票
        self.dnf_dianzan()

        # 史诗之路来袭活动合集
        self.dnf_1224()

        # hello语音网页礼包兑换
        self.hello_voice()

        # DNF闪光杯第三期
        self.dnf_shanguang()

        # DNF新春夺宝大作战
        self.dnf_spring()

        # 新春福袋大作战
        self.spring_fudai()

        # 燃放爆竹活动
        self.firecrackers()

        # WeGame春节活动
        self.wegame_spring()

        # qq视频-看江湖有翡
        self.youfei()

        # QQ空间集卡
        self.ark_lottery()

        # DNF新春福利集合站
        self.spring_collection()

        # 暂时屏蔽
        # # DNF0121新春落地页活动
        # self.dnf_0121()

        # dnf助手活动
        self.dnf_helper()

        # qq视频活动
        self.qq_video()

    # --------------------------------------------道聚城--------------------------------------------
    @try_except()
    def djc_operations(self):
        show_head_line("开始道聚城相关操作")
        self.show_not_ams_act_info("道聚城")

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
        logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 本次道聚城操作共获得 {delta} 个豆子（历史总获取： {old_allin} -> {new_allin}  余额： {old_balance} -> {new_balance} ）")

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
                ctx = f"2.3.3 领取连续签到{sign_reward_rule['iDays']}天奖励"
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
            logger.warning(f"未找到手游【{game_info.bizName}】的有效七日签到配置，请换个手游，比如王者荣耀")
            return

        dayIndex = datetime.datetime.now().weekday()  # 0-周一...6-周日，恰好跟下标对应
        giftInfo = giftInfos[dayIndex]

        self.get(f"3.2 一键领取{role_info.gameName}日常礼包-{giftInfo.sTask}", self.urls.receive_game_gift,
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
            logger.warning(color("fg_bold_cyan") + f"ios端不能许愿手游，建议使用安卓模拟器下载道聚城，在上面绑定王者荣耀。roleModel={roleModel}")
            return

        # 查询许愿道具信息
        query_wish_item_list_res = self.get("3.3.0  查询许愿道具", self.urls.query_wish_goods_list, plat=roleModel.systemID, biz=roleModel.bizCode, print_res=False)
        if "data" not in query_wish_item_list_res or len(query_wish_item_list_res["data"]) == 0:
            logger.warning(f"在{roleModel.systemKey}上游戏【{roleModel.gameName}】暂不支持许愿，query_wish_item_list_res={query_wish_item_list_res}")
            return

        propModel = GoodsInfo().auto_update_config(query_wish_item_list_res["data"]["goods"][0])

        # 查询许愿列表
        wish_list_res = self.get("3.3.1 查询许愿列表", self.urls.query_wish, appUid=uin2qq(self.cfg.account_info.uin))

        # 删除已经许愿的列表，确保许愿成功
        for wish_info in wish_list_res["data"]["list"]:
            ctx = f"3.3.2 删除已有许愿-{wish_info['bizName']}-{wish_info['sGoodsName']}"
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
            logger.warning(f"游戏【{roleModel.gameName}】暂未开放许愿，请换个道聚城许愿界面中支持的游戏来进行许愿哦，比如王者荣耀~")

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
        ctx = f"{prefix} 查询当前任务状态"
        taskinfo = self.get(ctx, self.urls.usertask, print_res=False)

        if self.can_take_task_award(taskinfo, iRuleId):
            ctx = f"{prefix} 领取任务-{taskName}-奖励"
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
                    res = self.exchange_item(f"4.2 兑换 {ei.sGoodsName}", ei.iGoodsId)
                    if int(res.get('ret', '0')) == -9905:
                        logger.warning(f"兑换 {ei.sGoodsName} 时提示 {res.get('msg')} ，等待{retryCfg.retry_wait_time}s后重试（{try_index + 1}/{retryCfg.max_retry_count})")
                        time.sleep(retryCfg.retry_wait_time)
                        continue

                    logger.debug(f"领取 {ei.sGoodsName} ok，等待{retryCfg.request_wait_time}s，避免请求过快报错")
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
        ctx = f"获取账号({self.cfg.name})的dnf角色列表"
        game_info = get_game_info("地下城与勇士")
        roleListJsonRes = self.get(ctx, self.urls.get_game_role_list, game=game_info.gameCode, sAMSTargetAppId=game_info.wxAppid, area=dnfServerId, platid="", partition="", is_jsonp=True, print_res=False)
        roleLists = json_parser.parse_role_list(roleListJsonRes)
        lines = []
        lines.append("")
        lines.append("+" * 40)
        lines.append(ctx)
        if len(roleLists) != 0:
            for idx, role in enumerate(roleLists):
                lines.append(f"\t第{idx + 1:2d}个角色信息：\tid = {role.roleid}\t 名字 = {role.rolename}")
        else:
            lines.append(f"\t未查到dnf服务器id={dnfServerId}上的角色信息，请确认服务器id已填写正确或者在对应区服已创建角色")
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
        ctx = f"获取账号({self.cfg.name})的{cfg.game_name}角色列表"
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
                lines.append(f"\t第{idx + 1:2d}个角色信息：\tid = {role.roleid}\t 名字 = {role.rolename}")
        else:
            lines.append(f"\t未查到{cfg.game_name} 平台={cfg.platid} 渠道={cfg.area} 区服={cfg.partition}上的角色信息，请确认这些信息已填写正确或者在对应区服已创建角色")
            lines.append(f"\t上述id的列表可查阅稍后自动打开的server_list_{game_info.bizName}.js，详情参见config.toml的对应注释")
            lines.append(f"\t渠道(area)的id可运行程序在自动打开的reference_data/server_list_{game_info.bizName}.js或手动打开这个文件， 查看 STD_CHANNEL_DATA中对应渠道的v")
            lines.append(f"\t平台(platid)的id可运行程序在自动打开的reference_data/server_list_{game_info.bizName}.js或手动打开这个文件， 查看 STD_SYSTEM_DATA中对应平台的v")
            lines.append(f"\t区服(partition)的id可运行程序在自动打开的reference_data/server_list_{game_info.bizName}.js或手动打开这个文件， 查看 STD_DATA中对应区服的v")
            self.open_mobile_game_server_list()
        lines.append("+" * 40)
        logger.info("\n".join(lines))

    def open_mobile_game_server_list(self):
        game_info = self.get_mobile_game_info()
        res = requests.get(self.urls.query_game_server_list.format(bizcode=game_info.bizCode))
        server_list_file = f"reference_data/server_list_{game_info.bizName}.js"
        with open(server_list_file, 'w', encoding='utf-8') as f:
            f.write(res.text)
        subprocess.Popen(f"npp_portable/notepad++.exe {server_list_file}")

    def query_dnf_gifts(self):
        self.get("查询可兑换道具列表", self.urls.show_exchange_item_list)

    def get_mobile_game_gifts(self):
        game_info = self.get_mobile_game_info()
        data = self.get(f"查询{game_info}礼包信息", self.urls.query_game_gift_bags, bizcode=game_info.bizCode, print_res=False)

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

        self.get(f"绑定账号-{serviceName}-{roleName}", self.urls.bind_role, role_info=json.dumps(roleInfo, ensure_ascii=False), is_jsonp=True)

    # --------------------------------------------心悦dnf游戏特权--------------------------------------------
    @try_except()
    def xinyue_operations(self):
        """
        https://xinyue.qq.com/act/a20181101rights/index.html
        根据配置进行心悦相关操作
        具体活动信息可以查阅reference_data/心悦活动备注.txt
        """
        show_head_line("DNF地下城与勇士心悦特权专区")
        self.show_amesvr_act_info(self.xinyue_battle_ground_op)

        if not self.cfg.function_switches.get_xinyue:
            logger.warning("未启用领取心悦特权专区功能，将跳过")
            return

        if len(self.cfg.xinyue_operations) == 0:
            logger.warning("未设置心悦相关操作信息，将跳过")
            return

        # 查询道具信息
        old_itemInfo = self.query_xinyue_items("6.1.0 操作前查询各种道具信息")
        logger.info(f"查询到的心悦道具信息为：{old_itemInfo}")

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
        logger.info(f"查询到的心悦道具信息为：{new_itemInfo}")

        # 再次查询成就点信息，展示本次操作得到的数目
        new_info = self.query_xinyue_info("6.3 操作完成后查询成就点信息")
        delta = new_info.score - old_info.score
        logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 本次心悦相关操作共获得 {delta} 个成就点（ {old_info.score} -> {new_info.score} ）")

        # 查询下心悦组队进度
        teaminfo = self.query_xinyue_teaminfo(print_res=False)
        if teaminfo.id != "":
            logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 当前队伍进度为 {teaminfo.score}/20")
        else:
            logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 当前尚无有效心悦队伍，可考虑加入或查看文档使用本地心悦组队功能")

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
            ctx = f"6.2 心悦操作： {op.sFlowName}({i + 1}/{op.count})"
            if current_hour < required_hour:
                logger.warning(f"当前时间为{now}，在本日{required_hour}点之前，将不执行操作: {ctx}")
                continue

            for try_index in range(retryCfg.max_retry_count):
                res = self.xinyue_battle_ground_op(ctx, op.iFlowId, package_id=op.package_id, lqlevel=xytype)
                # if int(res.get('ret', '0')) == -9905:
                #     logger.warning(f"兑换 {op.sGoodsName} 时提示 {res.get('msg')} ，等待{retryCfg.retry_wait_time}s后重试（{try_index + 1}/{retryCfg.max_retry_count})")
                #     time.sleep(retryCfg.retry_wait_time)
                #     continue

                logger.debug(f"心悦操作 {op.sFlowName} ok，等待{retryCfg.request_wait_time}s，避免请求过快报错")
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

        logger.info(f"当前账号的本地固定队信息为{fixed_team}")

        teaminfo = self.query_xinyue_teaminfo()
        if teaminfo.id != "":
            logger.info(f"目前已有队伍={teaminfo}")
            # 本地保存一下
            self.save_teamid(fixed_team.id, teaminfo.id)
            return

        logger.info("尝试从本地查找当前固定队对应的远程队伍ID")
        remote_teamid = self.load_teamid(fixed_team.id)
        if remote_teamid != "":
            # 尝试加入远程队伍
            logger.info(f"尝试加入远程队伍id={remote_teamid}")
            teaminfo = self.query_xinyue_teaminfo_by_id(remote_teamid)
            # 如果队伍仍有效则加入
            if teaminfo.id == remote_teamid:
                teaminfo = self.join_xinyue_team(remote_teamid)
                if teaminfo is not None:
                    logger.info(f"成功加入远程队伍，队伍信息为{teaminfo}")
                    return

            logger.info(f"远程队伍={remote_teamid}已失效，应该是新的一周自动解散了，将重新创建队伍")

        # 尝试创建小队并保存到本地
        teaminfo = self.create_xinyue_team()
        self.save_teamid(fixed_team.id, teaminfo.id)
        logger.info(f"创建小队并保存到本地成功，队伍信息={teaminfo}")

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
                logger.warning(f"本地调试日志：本地固定队伍={team.id}的队伍成员({team.members})不符合要求，请确保是三个有效的qq号")
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
            logger.debug(f"本地保存固定队信息，具体内容如下：{teamidInfo}")

    def load_teamid(self, fixed_teamid):
        fname = self.local_saved_teamid_file.format(fixed_teamid)

        if not os.path.isfile(fname):
            return ""

        with open(fname, "r", encoding="utf-8") as f:
            teamidInfo = json.load(f)
            logger.debug(f"读取本地缓存的固定队信息，具体内容如下：{teamidInfo}")
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
        if "modRet" in data:
            r = data["modRet"]
            score, ysb, xytype, specialMember, username, usericon = r["sOutValue1"], r["sOutValue2"], r["sOutValue3"], r["sOutValue4"], r["sOutValue5"], r["sOutValue6"]
        else:
            score, ysb, xytype, specialMember, username, usericon = "0", "0", "1", "0", "查询失败了", ""
        return XinYueInfo(score, ysb, xytype, specialMember, username, usericon)

    def xinyue_battle_ground_op(self, ctx, iFlowId, package_id="", print_res=True, lqlevel=1, teamid="", **extra_params):
        return self.xinyue_op(ctx, self.urls.iActivityId_xinyue_battle_ground, iFlowId, package_id, print_res, lqlevel, teamid, **extra_params)

    def xinyue_op(self, ctx, iActivityId, iFlowId, package_id="", print_res=True, lqlevel=1, teamid="", **extra_params):
        # 网站上特邀会员不论是游戏家G几，调用doAction(flowId,level)时level一律传1，而心悦会员则传入实际的567对应心悦123
        if lqlevel < 5:
            lqlevel = 1

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "xinyue", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20181101rights/",
                                   package_id=package_id, lqlevel=lqlevel, teamid=teamid,
                                   **extra_params)

    # DNF进击吧赛利亚
    def xinyue_sailiyam(self):
        # https://xinyue.qq.com/act/a20201023sailiya/index.html
        show_head_line("DNF进击吧赛利亚")
        self.show_amesvr_act_info(self.xinyue_sailiyam_op)

        def sleep_to_avoid_ban():
            logger.info("等待五秒，防止提示操作太快")
            time.sleep(5)

        for dzid in self.common_cfg.sailiyam_visit_target_qqs:
            if dzid == uin2qq(self.cfg.account_info.uin):
                continue
            self.xinyue_sailiyam_op(f"拜访好友-{dzid}", "714307", dzid=dzid)
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

    @try_except(return_val_on_except="")
    def get_xinyue_sailiyam_package_id(self):
        res = self.xinyue_sailiyam_op("打工显示", "715378", print_res=False)
        return res["modRet"]["jData"]["roleinfor"]["iPackageId"]

    @try_except(return_val_on_except="")
    def get_xinyue_sailiyam_workinfo(self):
        res = self.xinyue_sailiyam_op("打工显示", "715378", print_res=False)
        workinfo = SailiyamWorkInfo().auto_update_config(res["modRet"]["jData"]["roleinfor"])

        work_message = ""

        if workinfo.status == 2:
            nowtime = get_now_unix()
            fromtimestamp = datetime.datetime.fromtimestamp
            if workinfo.endTime > nowtime:
                lefttime = int(workinfo.endTime - nowtime)
                hour, minute, second = lefttime // 3600, lefttime % 3600 // 60, lefttime % 60
                work_message += f"赛利亚打工倒计时：{hour:02d}:{minute:02d}:{second:02d}"
            else:
                work_message += "赛利亚已经完成今天的工作了"

            work_message += f"。开始时间为{fromtimestamp(workinfo.startTime)}，结束时间为{fromtimestamp(workinfo.endTime)}，奖励最终领取时间为{fromtimestamp(workinfo.endLQtime)}"
        else:
            work_message += "赛利亚尚未出门工作"

        return work_message

    @try_except(return_val_on_except="")
    def get_xinyue_sailiyam_status(self):
        res = self.xinyue_sailiyam_op("查询状态", "714738", print_res=False)
        modRet = parse_amesvr_common_info(res)
        lingqudangao, touwei, _, baifang = modRet.sOutValue1.split('|')
        dangao = modRet.sOutValue2
        xinqingzhi = modRet.sOutValue3
        qiandaodate = modRet.sOutValue4
        return f"领取蛋糕：{lingqudangao == '1'}, 投喂蛋糕: {touwei == '1'}, 已拜访次数: {baifang}/5, 剩余蛋糕: {dangao}, 心情值: {xinqingzhi}/100, 已连续签到: {qiandaodate}次"

    @try_except()
    def show_xinyue_sailiyam_work_log(self):
        res = self.xinyue_sailiyam_op("日志列表", "715201", print_res=False)
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
                month, day, message = log[0][:2], log[0][2:], logContents[log[2]]
                logger.info(f"{month}月{day}日：{message}")

    def show_xinyue_sailiyam_kouling(self):
        res = self.xinyue_sailiyam_op("输出项", "714618", print_res=False)
        if 'modRet' in res:
            logger.info(f"分享口令为： {res['modRet']['sOutValue2']}")

    def check_xinyue_sailiyam(self):
        self.check_bind_account("DNF进击吧赛利亚", "https://xinyue.qq.com/act/a20201023sailiya/index.html",
                                activity_op_func=self.xinyue_sailiyam_op, query_bind_flowid="714234", commit_bind_flowid="714233")

    def xinyue_sailiyam_op(self, ctx, iFlowId, dzid="", iPackageId="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_xinyue_sailiyam

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20201023sailiyam/",
                                   dzid=dzid, page=1, iPackageId=iPackageId,
                                   **extra_params)

    # --------------------------------------------黑钻--------------------------------------------
    @try_except()
    def get_heizuan_gift(self):
        # https://dnf.qq.com/act/blackDiamond/gift.shtml
        show_head_line("黑钻礼包")
        self.show_not_ams_act_info("黑钻礼包")

        if not self.cfg.function_switches.get_heizuan_gift or self.disable_most_activities():
            logger.warning("未启用领取每月黑钻等级礼包功能，将跳过")
            return

        while True:
            res = self.get("领取每月黑钻等级礼包", self.urls.heizuan_gift)
            # 如果未绑定大区，提示前往绑定 "iRet": -50014, "sMsg": "抱歉，请先绑定大区后再试！"
            if res["iRet"] == -50014:
                self.guide_to_bind_account("每月黑钻等级礼包", "https://dnf.qq.com/act/blackDiamond/gift.shtml", activity_op_func=None)
                continue

            return res

    # --------------------------------------------信用礼包--------------------------------------------
    @try_except()
    def get_credit_xinyue_gift(self):
        show_head_line("腾讯游戏信用相关礼包")
        self.show_not_ams_act_info("腾讯游戏信用礼包")

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

    # --------------------------------------------QQ空间集卡--------------------------------------------
    @try_except()
    def ark_lottery(self):
        # note: 启用和废弃抽卡活动的流程如下
        #   1. 启用
        #   1.1 获取新配置   手机登录抽卡活动页面，然后抓包获得页面代码，从中搜索【window.syncData】找到逻辑数据和配置，将其值复制到【setting/ark_lottery.py】中，作为setting变量的值
        #   1.2 填写新链接   在urls.py中，替换self.ark_lottery_page的值为新版抽卡活动的链接（理论上应该只有zz和verifyid参数的值会变动，而且大概率是+1）
        #   1.3 重新启用代码
        #   1.3.1 在djc_helper.py中将ark_lottery的调用处从expired_activities移到normal_run
        #   1.3.2 在main.py中将main函数中取消注释show_lottery_status和auto_send_cards的调用处
        #   1.3.3 在config.toml/example中act_id_to_cost_all_cards_and_do_lottery中增加新集卡活动的默认开关
        #   1.3.4 在djc_helper.py中将fetch_pskey的p_skey的判断条件取消注释
        #   1.4 更新 urls.py 中 not_ams_activities 中集卡活动的时间
        #
        # hack:
        #   2. 废弃
        #   2.1 在djc_helper.py中将ark_lottery的调用处从normal_run移到expired_activities
        #   2.2 在main.py中将main函数中注释show_lottery_status和auto_send_cards的调用处
        #   2.3 在djc_helper.py中将fetch_pskey的p_skey的判断条件注释

        # https://act.qzone.qq.com/vip/2019/xcardv3?zz=6&verifyid=qqvipdnf11
        show_head_line(f"QQ空间集卡 - {self.zzconfig.actid}_{self.zzconfig.actName}")
        self.show_not_ams_act_info("集卡")

        if not self.cfg.function_switches.get_ark_lottery:
            logger.warning("未启用领取QQ空间集卡功能，将跳过")
            return

        lr = self.fetch_pskey()
        if lr is None:
            return

        qa = QzoneActivity(self, lr)
        qa.ark_lottery()

    def ark_lottery_query_left_times(self, to_qq):
        ctx = f"查询 {to_qq} 的剩余被赠送次数"
        res = self.get(ctx, self.urls.ark_lottery_query_left_times, to_qq=to_qq, actName=self.zzconfig.actName, print_res=False)
        # # {"13320":{"data":{"uAccuPoint":4,"uPoint":3},"ret":0,"msg":"成功"},"ecode":0,"ts":1607934735801}
        if res['13320']['ret'] != 0:
            return 0
        return res['13320']['data']['uPoint']

    def send_card(self, card_name, cardId, to_qq, print_res=False):
        from_qq = uin2qq(self.cfg.account_info.uin)

        ctx = f"{from_qq} 赠送卡片 {card_name}({cardId}) 给 {to_qq}"
        self.get(ctx, self.urls.ark_lottery_send_card, cardId=cardId, from_qq=from_qq, to_qq=to_qq, actName=self.zzconfig.actName, print_res=print_res)
        # # {"13333":{"data":{},"ret":0,"msg":"成功"},"ecode":0,"ts":1607934736057}

    def send_card_by_name(self, card_name, to_qq):
        card_info_map = parse_card_group_info_map(self.zzconfig)
        self.send_card(card_name, card_info_map[card_name].id, to_qq, print_res=True)

    def fetch_pskey(self):
        # 如果未启用qq空间相关的功能，则不需要这个
        any_enabled = False
        for activity_enabled in [
            # self.cfg.function_switches.get_ark_lottery,
            # self.cfg.function_switches.get_dnf_warriors_call and not self.disable_most_activities(),
            self.cfg.function_switches.get_vip_mentor and not self.disable_most_activities(),
        ]:
            if activity_enabled:
                any_enabled = True
        if not any_enabled:
            logger.warning("未启用领取QQ空间相关的功能，将跳过尝试更新QQ空间的p_skey的流程")
            return

        # 仅支持扫码登录和自动登录
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            logger.warning("抽卡功能目前仅支持扫码登录和自动登录，请修改登录方式，否则将跳过该功能")
            return

        cached_pskey = self.load_uin_pskey()
        need_update = self.is_pskey_expired(cached_pskey)

        # qq空间登录也需要获取skey后，若是旧版本存档，视作已过期
        if not need_update and (cached_pskey is None or "skey" not in cached_pskey or "vuserid" not in cached_pskey):
            logger.warning("qq空间登录改版后，需要有skey和vuserid。当前为旧版本cache，需要重新拉取")
            need_update = True

        if need_update:
            # 抽卡走的账号体系是使用pskey的，不与其他业务共用登录态，需要单独获取QQ空间业务的p_skey。参考链接：https://cloud.tencent.com/developer/article/1008901
            logger.warning("pskey需要更新，将尝试重新登录QQ空间获取并保存到本地")
            # 重新获取
            ql = QQLogin(self.common_cfg)
            if self.cfg.login_mode == "qr_login":
                # 扫码登录
                lr = ql.qr_login(login_mode=ql.login_mode_qzone, name=self.cfg.name)
            else:
                # 自动登录
                lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode=ql.login_mode_qzone, name=self.cfg.name)
            # 保存
            self.save_uin_pskey(lr.uin, lr.p_skey, lr.skey, lr.vuserid)
        else:
            lr = LoginResult(uin=cached_pskey["p_uin"], p_skey=cached_pskey["p_skey"], skey=cached_pskey["skey"], vuserid=cached_pskey["vuserid"])

        if lr.skey != "" and lr.vuserid != "":
            self.memory_save_uin_skey(lr.uin, lr.skey)
            self.vuserid = lr.vuserid

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

    def save_uin_pskey(self, uin, pskey, skey, vuserid):
        # 本地缓存
        with open(self.get_local_saved_pskey_file(), "w", encoding="utf-8") as sf:
            loginResult = {
                "p_uin": str(uin),
                "p_skey": str(pskey),
                "skey": str(skey),
                "vuserid": str(vuserid),
            }
            json.dump(loginResult, sf)
            logger.debug(f"本地保存pskey信息，具体内容如下：{loginResult}")

    def load_uin_pskey(self):
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_pskey_file()):
            return

        with open(self.get_local_saved_pskey_file(), "r", encoding="utf-8") as f:
            loginResult = json.load(f)
            logger.debug(f"读取本地缓存的pskey信息，具体内容如下：{loginResult}")
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
        self.show_amesvr_act_info(self.wegame_op)

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
        logger.info(color("fg_bold_cyan") + f"即将进行兑换道具，当前剩余智慧星为{star_count}")
        self.wegame_exchange_items()

        # 签到抽大奖
        self.wegame_op("抽奖资格-每日签到（在WeGame启动DNF）", "703519")
        self.wegame_op("抽奖资格-30分钟签到（游戏在线30分钟）", "703527")
        _, lottery_times = self.get_wegame_star_count_lottery_times()
        logger.info(color("fg_bold_cyan") + f"即将进行抽奖，当前剩余抽奖资格为{lottery_times}")
        for i in range(lottery_times):
            res = self.wegame_op("抽奖", "703957")
            if res.get('ret', "0") == "600":
                # {"ret": "600", "msg": "非常抱歉，您的资格已经用尽！", "flowRet": {"iRet": "600", "sLogSerialNum": "AMS-DNF-1031000622-s0IQqN-331515-703957", "iAlertSerial": "0", "sMsg": "非常抱歉！您的资格已用尽！"}, "failedRet": {"762140": {"iRuleId": "762140", "jRuleFailedInfo": {"iFailedRet": 600}}}}
                break

        # 在线得好礼
        self.wegame_op("累计在线30分钟签到", "703529")
        check_days = self.get_wegame_checkin_days()
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {check_days} 天")
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
                res = self.wegame_op(f"兑换 {ei.sGoodsName}", ei.iFlowId)
                if res["ret"] == "700":
                    # 默认先兑换完前面的所有道具的最大上限，才会尝试兑换后面的道具
                    logger.warning(f"兑换第{i + 1}个【{ei.sGoodsName}】的时候幸运星剩余数量不足，将停止兑换流程，从而确保排在前面的兑换道具达到最大兑换次数后才尝试后面的道具")
                    return

    def check_wegame_guoqing(self):
        self.check_bind_account("wegame国庆", "https://dnf.qq.com/lbact/a20200922wegame/index.html",
                                activity_op_func=self.wegame_op, query_bind_flowid="703509", commit_bind_flowid="703508")

    def wegame_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_wegame_guoqing

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20200922wegame/",
                                   **extra_params)

    # --------------------------------------------史诗之路来袭活动合集--------------------------------------------
    @try_except()
    def dnf_1224(self):
        # https://dnf.qq.com/lbact/a20201224aggregate/index.html
        show_head_line("史诗之路来袭活动合集")
        self.show_amesvr_act_info(self.dnf_1224_op)

        if not self.cfg.function_switches.get_dnf_1224 or self.disable_most_activities():
            logger.warning("未启用领取史诗之路来袭活动合集功能，将跳过")
            return

        self.check_dnf_1224()

        self.dnf_1224_op("勇士礼包", "730665")

        self.dnf_1224_op("30分签到礼包", "730666")
        check_days = self.get_dnf_1224_checkin_days()
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {check_days} 天")
        self.dnf_1224_op("3日礼包", "730663")
        self.dnf_1224_op("7日礼包", "730667")
        self.dnf_1224_op("15日礼包", "730668")

    def get_dnf_1224_checkin_days(self):
        res = self.dnf_1224_op("查询签到信息", "730670", print_res=False)
        return int(res["modRet"]["total"])

    def check_dnf_1224(self):
        self.check_bind_account("qq视频-史诗之路来袭活动合集", "https://dnf.qq.com/lbact/a20201224aggregate/index.html",
                                activity_op_func=self.dnf_1224_op, query_bind_flowid="730660", commit_bind_flowid="730659")

    def dnf_1224_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_1224
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20201224aggregate/",
                                   **extra_params)

    # --------------------------------------------DNF闪光杯第三期--------------------------------------------
    @try_except()
    def dnf_shanguang(self):
        # http://xinyue.qq.com/act/a20201221sgbpc/index.html
        show_head_line("DNF闪光杯第三期")
        self.show_amesvr_act_info(self.dnf_shanguang_op)

        if not self.cfg.function_switches.get_dnf_shanguang or self.disable_most_activities():
            logger.warning("未启用领取DNF闪光杯第三期活动合集功能，将跳过")
            return

        self.check_dnf_shanguang()

        # self.dnf_shanguang_op("报名礼", "724862")
        # self.dnf_shanguang_op("app专属礼", "724877")
        logger.warning(color("fg_bold_cyan") + "不要忘记前往网页手动报名并领取报名礼以及前往app领取一次性礼包")

        logger.warning(color("bold_yellow") + f"本周已获得指定装备{self.query_dnf_shanguang_equip_count()}件，具体装备可去活动页面查看")

        self.dnf_shanguang_op("周周闪光好礼", "724878", weekDay=get_last_week_monday())

        for i in range(6):
            res = self.dnf_shanguang_op("周周开大奖", "724879")
            if int(res["ret"]) != 0:
                break
            time.sleep(5)

        self.dnf_shanguang_op("每日登录游戏", "724881")
        self.dnf_shanguang_op("每日登录app", "724882")
        # self.dnf_shanguang_op("每日网吧登录", "724883")

        lottery_times = self.get_dnf_shanguang_lottery_times()
        logger.info(color("fg_bold_cyan") + f"当前剩余闪光夺宝次数为 {lottery_times} ")
        for i in range(lottery_times):
            self.dnf_shanguang_op("闪光夺宝", "724880")
            time.sleep(5)

    def get_dnf_shanguang_lottery_times(self):
        res = self.dnf_shanguang_op("闪光夺宝次数", "724885", print_res=False)
        return int(res["modRet"]["sOutValue3"])

    def query_dnf_shanguang_equip_count(self, print_warning=True):
        res = self.dnf_shanguang_op("输出当前周期爆装信息", "724876", weekDay=get_this_week_monday(), print_res=False)
        equip_count = 0
        if "modRet" in res:
            info = parse_amesvr_common_info(res)
            if info.sOutValue2 != "" and info.sOutValue2 != "0":
                equip_count = len(info.sOutValue2.split(","))
        else:
            if print_warning: logger.warning(color("bold_yellow") + "是不是还没有报名？")

        return equip_count

    def check_dnf_shanguang(self):
        self.check_bind_account("DNF闪光杯第三期", "http://xinyue.qq.com/act/a20201221sgbpc/index.html",
                                activity_op_func=self.dnf_shanguang_op, query_bind_flowid="724871", commit_bind_flowid="724870")

    def dnf_shanguang_op(self, ctx, iFlowId, weekDay="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_shanguang

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "https://xinyue.qq.com/act/a20201221sgb",
                                   weekDay=weekDay,
                                   **extra_params)

    # --------------------------------------------qq视频活动--------------------------------------------
    # note: 接入新qq视频活动的流程如下
    #   1. chrome打开devtools，激活手机模式，并在过滤栏中输入 option=100
    #   2. 打开活动页面 https://m.film.qq.com/magic-act/zrayedj8q888yf2rq6z6rcuwsu/index.html
    #   3. 点击任意按钮，从query_string中获取最新的act_id (其实就是上面 magic-act/ 和 /index.html 中间这一串字符
    qq_video_act_id = "zrayedj8q888yf2rq6z6rcuwsu"
    #   note:4. 依次点击下面各个行为对应的按钮，从query_string中获取最新的module_id，如果某个请求的type参数不是21，也需要专门调整对应值
    qq_video_module_id_lucky_user = "91fp08t6uqaaaoqejrauqg2s05"  # 幸运勇士礼包
    qq_video_module_id_first_meet_gift = "zjyk7dlgj23jk7egsofqaj3hk9"  # 勇士见面礼-礼包
    qq_video_module_id_first_meet_token = "4c43cws9i4721uq01ghu02l3fl"  # 勇士见面礼-令牌
    qq_video_module_id_lottery = "4g10wjqfz666i6rjgysryiowtu"  # 每日抽奖1次(需在活动页面开通QQ视频会员)
    qq_video_module_id_online_30_minutes = "14p5563e1fc4khr94px1te9yp9"  # 在线30分钟
    qq_video_module_id_online_3_days = "sl2l0redd0wrid3e2ps17is0il"  # 累积3天
    qq_video_module_id_online_7_days = "ui7hp23tr46ae07poruw2uf5xe"  # 累积7天
    qq_video_module_id_online_15_days = "h1y2e73itl1ej4cy6l7ilzd001"  # 累积15天

    @try_except()
    def qq_video(self):
        show_head_line("qq视频活动")
        self.show_not_ams_act_info("qq视频蚊子腿")

        if not self.cfg.function_switches.get_qq_video or self.disable_most_activities():
            logger.warning("未启用领取qq视频活动功能，将跳过")
            return

        self.check_qq_video()

        self.qq_video_op("幸运勇士礼包", self.qq_video_module_id_lucky_user, type="100112")
        self.qq_video_op("勇士见面礼-礼包", self.qq_video_module_id_first_meet_gift, type="100112")
        self.qq_video_op("勇士见面礼-令牌", self.qq_video_module_id_first_meet_token)

        self.qq_video_op("每日抽奖1次(需在活动页面开通QQ视频会员)", self.qq_video_module_id_lottery)

        self.qq_video_op("在线30分钟", self.qq_video_module_id_online_30_minutes)
        self.qq_video_op("累积3天", self.qq_video_module_id_online_3_days)
        self.qq_video_op("累积7天", self.qq_video_module_id_online_7_days)
        self.qq_video_op("累积15天", self.qq_video_module_id_online_15_days)

        logger.warning("如果【在线30分钟】提示你未在线30分钟，但你实际已在线超过30分钟，也切换过频道了，不妨试试退出游戏，有时候在退出游戏的时候才会刷新这个数据")

    def check_qq_video(self):
        while True:
            res = self.qq_video_op("幸运勇士礼包", self.qq_video_module_id_lucky_user, type="100112", print_res=False)
            # {"frame_resp": {"failed_condition": {"condition_op": 3, "cur_value": 0, "data_type": 2, "exp_value": 0, "type": 100418}, "msg": "", "ret": 0, "security_verify": {"iRet": 0, "iUserType": 0, "sAppId": "", "sBusinessId": "", "sInnerMsg": "", "sUserMsg": ""}}, "act_id": 108810, "data": {"button_txt": "关闭", "cdkey": "", "custom_list": [], "end_timestamp": -1, "ext_url": "", "give_type": 0, "is_mask_cdkey": 0, "is_pop_jump": 0, "item_share_desc": "", "item_share_title": "", "item_share_url": "", "item_sponsor_title": "", "item_sponsor_url": "", "item_tips": "", "jump_url": "", "jump_url_web": "", "lottery_item_id": "1601827185657s2238078729s192396s1", "lottery_level": 0, "lottery_name": "", "lottery_num": 0, "lottery_result": 0, "lottery_txt": "您当前还未绑定游戏帐号，请先绑定哦~", "lottery_url": "", "lottery_url_ext": "", "lottery_url_ext1": "", "lottery_url_ext2": "", "msg_title": "告诉我怎么寄给你", "need_bind": 0, "next_type": 2, "pop_jump_btn_title": "", "pop_jump_url": "", "prize_give_info": {"prize_give_status": 0}, "property_detail_code": 0, "property_detail_msg": "", "property_type": 0, "share_txt": "", "share_url": "", "source": 0, "sys_code": -904, "url_lottery": "", "user_info": {"addr": "", "name": "", "tel": "", "uin": ""}}, "module_id": 125890, "msg": "", "ret": 0, "security_verify": {"iRet": 0, "iUserType": 0, "sAppId": "", "sBusinessId": "", "sInnerMsg": "", "sUserMsg": ""}}
            if int(res["data"]["sys_code"]) == -904 and extract_qq_video_message(res) == "您当前还未绑定游戏帐号，请先绑定哦~":
                self.guide_to_bind_account("qq视频活动", "https://m.film.qq.com/magic-act/110254/index.html", activity_op_func=None)
                continue

            return res

    def qq_video_op(self, ctx, module_id, type="21", print_res=True):
        res = self._qq_video_op(ctx, type, "100", module_id, print_res)

        if int(res["data"]["sys_code"]) == -1010 and extract_qq_video_message(res) == "系统错误":
            msg = "【需要修复这个】不知道为啥这个操作失败了，试试连上fiddler然后手动操作看看请求哪里对不上"
            logger.warning(color("fg_bold_yellow") + msg)

        return res

    def _qq_video_op(self, ctx, type, option, module_id, print_res=True):
        extra_cookies = "; ".join([
            "",
            "appid=3000501",
            "main_login=qq",
            f"vuserid={self.vuserid}",
        ])
        return self.get(ctx, self.urls.qq_video, type=type, option=option, act_id=self.qq_video_act_id, module_id=module_id,
                        print_res=print_res, extra_cookies=extra_cookies)

    # --------------------------------------------10月女法师三觉活动--------------------------------------------
    def dnf_female_mage_awaken(self):
        # https://mwegame.qq.com/act/dnf/Mageawaken/index?subGameId=10014&gameId=10014&gameId=1006
        show_head_line("10月女法师三觉")
        self.show_amesvr_act_info(self.dnf_female_mage_awaken_op)

        if not self.cfg.function_switches.get_dnf_female_mage_awaken or self.disable_most_activities():
            logger.warning("未启用领取10月女法师三觉活动合集功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # checkin_days = self.query_dnf_female_mage_awaken_info()
        # logger.warning(color("fg_bold_cyan") + f"已累计签到 {checkin_days} 天")

        if self.cfg.dnf_helper_info.token == "":
            extra_msg = "未配置dnf助手相关信息，无法进行10月女法师三觉相关活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_female_mage_awaken")
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

    def dnf_female_mage_awaken_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_female_mage_awaken

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        qq = uin2qq(self.cfg.account_info.uin)
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(ctx, "comm.ams.game.qq.com", "group_k", "bb", iActivityId, iFlowId, print_res, "http://mwegame.qq.com/act/dnf/mageawaken/index1/",
                                  sArea=roleinfo.serviceID, serverId=roleinfo.serviceID,
                                  sRoleId=roleinfo.roleCode, sRoleName=quote_plus(roleinfo.roleName),
                                  uin=qq, skey=self.cfg.account_info.skey,
                                  nickName=quote_plus(dnf_helper_info.nickName), userId=dnf_helper_info.userId, token=quote_plus(dnf_helper_info.token),
                                  **extra_params)

        # 1000017016: 登录态失效,请重新登录
        if res is not None and res["flowRet"]["iRet"] == "700" and "登录态失效" in res["flowRet"]["sMsg"]:
            extra_msg = "dnf助手的登录态已过期，目前需要手动更新，具体操作流程如下"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_female_mage_awaken_expired_" + get_today())

        return res

    def show_dnf_helper_info_guide(self, extra_msg="", show_message_box_once_key="", always_show_message_box=False):
        if extra_msg != "":
            logger.warning(color("fg_bold_green") + extra_msg)

        tips_from_url = '\n'.join([
            "1. 打开dnf助手并确保已登录账户，点击活动，找到【艾丽丝的密室，塔罗牌游戏】并点开，点击右上角分享，选择QQ好友，发送给【我的电脑】",
            "2. 在我的电脑聊天框中的链接中找到请求中的token（形如&serverId=11&token=6C6bNrA4&isMainRole=0&subGameId=10014，因为&是参数分隔符，所以token部分为token=6C6bNrA4，所以token为6C6bNrA4, ps: 如果参数形如&serverId=&token=&isMainRole=&subGameId=，那么token部分参数为token=，说明这个活动助手没有把token放到链接里，需要尝试下一个），将其进行更新到配置文件中【dnf助手信息】配置中",
            "ps: nickName/userId的获取方式为，点开dnf助手中点开右下角的【我的】，然后点击右上角的【编辑】按钮，则昵称即为nickname，社区ID即为userId，如我的这俩值为风之凌殇、504051073",
            "如果你刚刚按照上述步骤操作过，但这次运行还是提示你过期了，很大概率是你想要多个账号一起用这个功能，然后在手机上依次登陆登出这些账号，按照上述操作获取token。实际上这样是无效的，因为你在登陆下一个账号的时候，之前的账号的token就因为登出而失效了",
            "有这个需求的话，请使用安卓模拟器的多开功能来多开dnf助手去登陆各个账号。如果手机支持多开app，也可以使用对应功能。具体多开流程请自行百度搜索： 手机 app 多开",
        ])

        tips_from_zhuabao = '\n'.join([
            "",
            "如果上面这个活动在助手里找不到了，可以试试看其他的活动",
            "如果所有活动的转发链接里都找不到token，那么只能手动抓包，从请求的cookie或post data中获取token信息了，具体可以百度 安卓 https 抓包",
            "下面给出几种推荐的方案",
            "1. 安卓下使用HttpCanary来实现对dnf助手抓包（开启http canary抓包后，打开助手，点击任意一个活动页面，然后去链接或cookie中查找token），可参考",
            "    1.1 https://httpcanary.com/zh-hans/",
            "    1.2 抓包流程可参考我录制的操作视频 https://www.bilibili.com/video/BV1az4y1k7bH",
            "2. 安卓下 VirtualXposed+JustTrustMe，然后在这里面安装dnf助手和qq，之后挂fiddler的vpn来完成抓包操作，可参考",
            "    2.1 https://www.jianshu.com/p/a818a0d0aa9f",
            "    2.2 https://testerhome.com/articles/18609",
            "    2.3 https://juejin.im/post/6844903602209685517",
            "    2.4 https://blog.csdn.net/hebbely/article/details/79248077",
            "    2.5 https://juejin.im/post/6844903831579394055",
            "    ps：简单说明下，fiddler用于抓https包，由于助手对网络请求做了证书校验，所以需要安装VirtualXposed+JustTrustMe，并在VirtualXposed中去安装运行助手，从而使其校验失效，能够让请求成功",

        ])

        logger.warning(
            '\n' +
            color("fg_bold_yellow") + tips_from_url +
            '\n' +
            color("fg_bold_green") + tips_from_zhuabao
        )
        # 首次在对应场景时弹窗
        if always_show_message_box or (show_message_box_once_key != "" and is_first_run(f"show_dnf_helper_info_guide_{show_message_box_once_key}")):
            async_message_box(tips_from_url + '\n' + tips_from_zhuabao, "助手信息获取指引", print_log=False)

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
            extra_msg = "未配置dnf助手相关信息，无法进行dnf助手排行榜相关活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_rank")
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
        ctx = f"给{id}({name})打榜{total_score}鲜花"
        if total_score <= 0:
            logger.info(f"{ctx} 没有多余的鲜花，暂时不能进行打榜~")
            return

        return self.dnf_rank_op(ctx, self.urls.rank_send_score, id=id, score=total_score)

    @try_except(return_val_on_except=RankUserInfo())
    def dnf_rank_get_user_info(self, print_res=False):
        res = self.dnf_rank_op("查询信息", self.urls.rank_user_info, print_res=print_res)

        return RankUserInfo().auto_update_config(res["data"])

    def dnf_rank_receive_diamond(self, gift_name, gift_id):
        return self.dnf_rank_op(f'领取黑钻-{gift_name}', self.urls.rank_receive_diamond, gift_id=gift_id)

    @try_except()
    def dnf_rank_receive_diamond_amesvr(self, ctx, **extra_params):
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
                                  **extra_params)

    def dnf_rank_op(self, ctx, url, **params):
        qq = uin2qq(self.cfg.account_info.uin)
        info = self.cfg.dnf_helper_info
        return self.get(ctx, url, uin=qq, userId=info.userId, token=quote_plus(info.token), **params)

    # --------------------------------------------dnf助手活动(后续活动都在这个基础上改)--------------------------------------------
    @try_except()
    def dnf_helper(self):
        # https://mwegame.qq.com/act/dnf/SpringFestival21/indexNew
        show_head_line("dnf助手 牛气冲天迎新年")
        self.show_amesvr_act_info(self.dnf_helper_op)

        if not self.cfg.function_switches.get_dnf_helper or self.disable_most_activities():
            logger.warning("未启用领取dnf助手活动功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        if self.cfg.dnf_helper_info.token == "":
            extra_msg = "未配置dnf助手相关信息，无法进行dnf助手相关活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_helper")
            return

        def query_signin_info():
            res = self.dnf_helper_op("查询", "734421", print_res=False)
            raw_info = parse_amesvr_common_info(res)
            temp = raw_info.sOutValue1.split(';')
            signin_days = int(temp[0])
            today_signed = temp[1] == "1"

            return signin_days, today_signed

        def query_card_info():
            res = self.dnf_helper_op("查询", "734421", print_res=False)
            raw_info = parse_amesvr_common_info(res)
            return raw_info.sOutValue3

        datetime_fmt = "%Y-%m-%d %H:%M:%S"
        red_packet_configs = [
            ("小年2月5", "736620", datetime.datetime.strptime("2021-02-05 00:00:00", datetime_fmt)),
            ("除夕2月11", "736634", datetime.datetime.strptime("2021-02-11 00:00:00", datetime_fmt)),
            ("春节2月12", "736635", datetime.datetime.strptime("2021-02-12 00:00:00", datetime_fmt)),
            ("情人节2月14", "736636", datetime.datetime.strptime("2021-02-14 00:00:00", datetime_fmt)),
            ("初五2月16", "736637", datetime.datetime.strptime("2021-02-16 00:00:00", datetime_fmt)),
            ("初八2月19", "736638", datetime.datetime.strptime("2021-02-19 00:00:00", datetime_fmt)),
            ("元宵2月26", "736639", datetime.datetime.strptime("2021-02-26 00:00:00", datetime_fmt)),
        ]
        now = datetime.datetime.now()
        for name, flowid, expected_datetime in red_packet_configs:
            if now.month != expected_datetime.month or now.day != expected_datetime.day:
                logger.warning(f"当前不是{expected_datetime}，跳过领取{name}的红包")
                continue

            self.dnf_helper_op(name, flowid, clickTime=str(random.randint(10, 15)))

        signin_configs = [
            (1, "734422", "一次性材质转换器", ""),
            (2, "735136", "神秘契约礼盒(1天)", ""),
            (3, "735395", "魂灭结晶礼盒（100个）", ""),
            (4, "735405", "智慧的引导通行证", ""),
            (5, "735431", "黑钻3天", "索西亚"),
            (6, "735410", "装备提升礼盒", ""),
            (7, "735414", "雷米的援助", ""),
            (8, "735434", "德洛斯矿山追加入场自选礼盒", "赛丽亚"),
            (9, "734422", "一次性材质转换器", ""),
            (10, "735136", "神秘契约礼盒(1天)", ""),
            (11, "735435", "装备提升礼盒", "花之女王"),
            (12, "735395", "魂灭结晶礼盒（100个）", ""),
            (13, "735405", "智慧的引导通行证", ""),
            (14, "735410", "装备提升礼盒", ""),
            (15, "735436", "黑钻7天", "凯丽"),
            (16, "735414", "雷米的援助", ""),
            (17, "734422", "一次性材质转换器", ""),
            (18, "735136", "神秘契约礼盒(1天)", ""),
            (19, "735395", "魂灭结晶礼盒（100个）", ""),
            (20, "735437", "时间引导石礼盒(50个)", "敏泰"),
            (21, "735405", "智慧的引导通行证", ""),
            (22, "735410", "装备提升礼盒", ""),
            (23, "735438", "+11黑铁装备强化券", "歌兰蒂斯"),
        ]
        signin_days, today_signed = query_signin_info()
        if signin_days >= len(signin_configs):
            logger.info("已经完全全部签到~")
        elif today_signed:
            logger.info("今日已经签到过")
        else:
            logger.info(f"尝试签到第{signin_days + 1}天")
            index, flowid, name, npc_name = signin_configs[signin_days]
            if npc_name != "":
                name = f"{npc_name} 赠送的 {name}"
            self.dnf_helper_op(name, flowid)
            signin_days += 1

        logger.info(color("bold_yellow") + f"当前已签到{signin_days}天，卡片信息：{query_card_info()}")

        self.dnf_helper_op("鸿运红包", "735719")

    def check_dnf_helper(self):
        self.check_bind_account("dnf助手活动", "https://mwegame.qq.com/act/dnf/SpringFestival21/indexNew",
                                activity_op_func=self.dnf_helper_op, query_bind_flowid="736842", commit_bind_flowid="736841")

    def dnf_helper_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_helper

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        qq = uin2qq(self.cfg.account_info.uin)
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(ctx, "comm.ams.game.qq.com", "group_k", "bb", iActivityId, iFlowId, print_res, "https://mwegame.qq.com/act/dnf/SpringFestival21/indexNew",
                                  sArea=roleinfo.serviceID, serverId=roleinfo.serviceID,
                                  sRoleId=roleinfo.roleCode, sRoleName=quote_plus(roleinfo.roleName),
                                  uin=qq, skey=self.cfg.account_info.skey,
                                  nickName=quote_plus(dnf_helper_info.nickName), userId=dnf_helper_info.userId, token=quote_plus(dnf_helper_info.token),
                                  **extra_params)

        # 1000017016: 登录态失效,请重新登录
        if res is not None and res["flowRet"]["iRet"] == "700" and "登录态失效" in res["flowRet"]["sMsg"]:
            extra_msg = "dnf助手的登录态已过期，目前需要手动更新，具体操作流程如下"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_helper_expired_" + get_today())

        return res

    # --------------------------------------------dnf助手编年史活动--------------------------------------------
    @try_except()
    def dnf_helper_chronicle(self):
        # dnf助手左侧栏
        show_head_line("dnf助手编年史")
        self.show_not_ams_act_info("DNF助手编年史")

        if not self.cfg.function_switches.get_dnf_helper_chronicle or self.disable_most_activities():
            logger.warning("未启用领取dnf助手编年史活动功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        # 为了不与其他函数名称冲突，且让函数名称短一些，写到函数内部~
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

        def sign_gifts_list():
            res = self.get("连续签到奖励列表", url_wang, api="list/sign", **common_params)
            return DnfHelperChronicleSignList().auto_update_config(res)

        # ------ 领取各种奖励 ------
        extra_msg = color("bold_green") + "很可能是编年史尚未正式开始，导致无法领取游戏内奖励~"

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def takeTaskAwards():
            taskInfo = getUserTaskList()
            if taskInfo.hasPartner:
                logger.info(f"搭档为{taskInfo.pUserId}")
            else:
                logger.warning("目前尚无搭档，建议找一个，可以多领点东西-。-")

            logger.info("首先尝试完成接到身上的任务")
            normal_tasks = set()
            for task in taskInfo.taskList:
                takeTaskAward_op("自己", task.name, task.mActionId, task.mStatus, task.mExp)
                normal_tasks.add(task.mActionId)
                if taskInfo.hasPartner:
                    takeTaskAward_op("队友", task.name, task.pActionId, task.pStatus, task.pExp)
                    normal_tasks.add(task.pActionId)

            logger.info("与心悦战场类似，即使未展示在接取列表内的任务，只要满足条件就可以领取奖励。因此接下来尝试领取其余任务(ps：这种情况下日志提示未完成也有可能是因为已经领取过~）")
            all_task = (
                ("001", 11, "013", 5, "DNF助手签到"),
                ("002", 11, "014", 6, "浏览资讯详情页"),
                ("003", 11, "015", 6, "浏览动态详情页"),
                ("004", 11, "016", 6, "浏览视频详情页"),
                ("005", 17, "017", 10, "登陆游戏"),
                ("007", 17, "019", 10, "进入游戏30分钟"),
                ("008", 17, "020", 10, "分享助手周报"),
                ("011", 23, "023", 11, "进入游戏超过1小时"),
            )
            for mActionId, mExp, pActionId, pExp, name in all_task:
                if mActionId not in normal_tasks:
                    takeTaskAward_op("自己", name, mActionId, 0, mExp)
                if taskInfo.hasPartner and pActionId not in normal_tasks:
                    takeTaskAward_op("队友", name, pActionId, 0, pExp)

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def takeTaskAward_op(suffix, taskName, actionId, status, exp):
            actionName = f"[{taskName}-{suffix}]"

            if status in [0, 2]:
                # 0-未完成，2-已完成未领取，但是助手签到任务在未完成的时候可以直接领取，所以这俩一起处理，在内部根据回包进行区分
                doActionIncrExp(actionName, actionId, exp)
            else:
                # 1 表示已经领取过
                logger.info(f"{actionName}已经领取过了")

        def doActionIncrExp(actionName, actionId, exp):
            res = self.post("领取任务经验", url_mwegame, "", api="doActionIncrExp", actionId=actionId, **common_params)
            data = res.get("data", 0)
            if data != 0:
                logger.info(f"领取{actionName}-{actionId}，获取经验为{exp}，回包data={data}")
            else:
                logger.warning(f"{actionName}尚未完成，无法领取哦~")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def take_continuous_signin_gifts():
            signGiftsList = sign_gifts_list()
            hasTakenAnySignGift = False
            for signGift in signGiftsList.gifts:
                # 2-未完成，0-已完成未领取，1-已领取
                if signGift.status in [0]:
                    # 0-已完成未领取
                    take_continuous_signin_gift_op(signGift)
                    hasTakenAnySignGift = True
                else:
                    # 2-未完成，1-已领取
                    pass
            if not hasTakenAnySignGift:
                logger.info("连续签到均已领取")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def take_continuous_signin_gift_op(giftInfo: DnfHelperChronicleSignGiftInfo):
            res = self.get("领取签到奖励", url_wang, api="send/sign", **common_params,
                           amsid=giftInfo.sLbcode)
            logger.info(f"领取连续签到{giftInfo.sDays}的奖励: {res.get('giftName', '出错啦')}")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def take_basic_awards():
            basicAwardList = basic_award_list()
            listOfBasicList = [(True, basicAwardList.basic1List)]
            if basicAwardList.hasPartner:
                listOfBasicList.append((False, basicAwardList.basic2List))
            hasTakenAnyBasicAward = False
            for selfGift, basicList in listOfBasicList:
                for award in basicList:
                    if award.isLock == 0 and award.isUsed == 0:
                        # 已解锁，且未领取，则尝试领取
                        take_basic_award_op(award, selfGift)
                        hasTakenAnyBasicAward = True
            if not hasTakenAnyBasicAward:
                logger.info("目前没有新的可以领取的基础奖励，只能等升级咯~")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def take_basic_award_op(awardInfo: DnfHelperChronicleBasicAwardInfo, selfGift=True):
            if selfGift:
                mold = 1  # 自己
                side = "自己"
            else:
                mold = 2  # 队友
                side = "队友"
            res = self.get("领取基础奖励", url_wang, api="send/basic", **common_params,
                           isLock=awardInfo.isLock, amsid=awardInfo.sLbCode, iLbSel1=awardInfo.iLbSel1, num=1, mold=mold)
            logger.info(f"领取{side}的第{awardInfo.sName}个基础奖励: {res.get('giftName', '出错啦')}")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def exchange_awards():
            exchangeList = exchange_list()
            exchangeGiftMap = {}
            for gift in exchangeList.gifts:
                exchangeGiftMap[gift.sLbcode] = gift

            if len(self.cfg.dnf_helper_info.chronicle_exchange_items) != 0:
                all_exchanged = True
                for ei in self.cfg.dnf_helper_info.chronicle_exchange_items:
                    if ei.sLbcode not in exchangeGiftMap:
                        logger.error(f"未找到兑换项{ei.sLbcode}对应的配置，请参考reference_data/dnf助手编年史活动_可兑换奖励列表.json")
                        continue

                    gift = exchangeGiftMap[ei.sLbcode]
                    if gift.usedNum >= int(gift.iNum):
                        logger.warning(f"{gift.sName}已经达到兑换上限{gift.iNum}次, 将跳过")
                        continue

                    userInfo = getUserActivityTopInfo()
                    if userInfo.level < int(gift.iLevel):
                        all_exchanged = False
                        logger.warning(f"目前等级为{userInfo.level}，不够兑换{gift.sName}所需的{gift.iLevel}级，将跳过后续优先级较低的兑换奖励")
                        break
                    if userInfo.point < int(gift.iCard):
                        all_exchanged = False
                        logger.warning(f"目前年史碎片数目为{userInfo.point}，不够兑换{gift.sName}所需的{gift.iCard}个，将跳过后续优先级较低的兑换奖励")
                        break

                    for i in range(ei.count):
                        exchange_award_op(gift)

                if all_exchanged:
                    logger.info(color("fg_bold_yellow") + "似乎配置的兑换列表已到达兑换上限，建议开启抽奖功能，避免浪费年史碎片~")
            else:
                logger.info("未配置dnf助手编年史活动的兑换列表，若需要兑换，可前往配置文件进行调整")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def exchange_award_op(giftInfo: DnfHelperChronicleExchangeGiftInfo):
            res = self.get("兑换奖励", url_wang, api="send/exchange", **common_params,
                           exNum=1, iCard=giftInfo.iCard, amsid=giftInfo.sLbcode, iNum=giftInfo.iNum, isLock=giftInfo.isLock)
            logger.info(f"兑换奖励: {res.get('giftName', '出错啦')}")

        @try_except(show_last_process_result=False, extra_msg=extra_msg)
        def lottery():
            if self.cfg.dnf_helper_info.chronicle_lottery:
                userInfo = getUserActivityTopInfo()
                totalLotteryTimes = userInfo.point // 10
                logger.info(f"当前共有{userInfo.point}年史诗片，将进行{totalLotteryTimes}次抽奖")
                for i in range(totalLotteryTimes):
                    op_lottery()
            else:
                logger.info("当前未启用抽奖功能，若奖励兑换完毕时，建议开启抽奖功能~")

        def op_lottery():
            res = self.get("抽奖", url_wang, api="send/lottery", **common_params, amsid="lottery_0007", iCard=10)
            gift = res.get("giftName", "出错啦")
            beforeMoney = res.get("money", 0)
            afterMoney = res.get("value", 0)
            logger.info(f"抽奖结果为: {gift}，年史诗片：{beforeMoney}->{afterMoney}")

        # ------ 实际逻辑 ------

        # 检查一下userid是否真实存在
        if self.cfg.dnf_helper_info.userId == "" or len(_getUserTaskList().get("data", {})) == 0:
            extra_msg = f"dnf助手的userId未配置或配置有误，当前值为[{self.cfg.dnf_helper_info.userId}]（本活动只需要这个，不需要token），无法进行dnf助手编年史活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_helper_chronicle")
            return

        # 提示做任务
        msg = "dnf助手签到任务和浏览咨询详情页请使用auto.js等自动化工具来模拟打开助手去执行对应操作，当然也可以每天手动打开助手点一点-。-"
        if is_first_run("dnf_helper_chronicle_task_tips_month_3"):
            async_message_box(msg, "编年史任务提示")
        else:
            logger.warning(msg)

        # 领取任务奖励的经验
        takeTaskAwards()

        # 领取连续签到奖励
        take_continuous_signin_gifts()

        # 领取基础奖励
        take_basic_awards()

        # 根据配置兑换奖励
        exchange_awards()

        # 抽奖
        lottery()

        ui = getUserActivityTopInfo()
        logger.warning(
            color("fg_bold_yellow") +
            f"账号 {self.cfg.name} 当前编年史等级为LV{ui.level}({ui.levelName}) 本级经验：{ui.currentExp}/{ui.levelExp} 当前总获取经验为{ui.totalExp} 剩余年史碎片为{ui.point}"
        )

    @try_except(show_exception_info=False, return_val_on_except=DnfHelperChronicleUserActivityTopInfo())
    def query_dnf_helper_chronicle_info(self):
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
        res = self.post("活动基础状态信息", url_mwegame, "", api="getUserActivityTopInfo", **common_params)
        return DnfHelperChronicleUserActivityTopInfo().auto_update_config(res.get("data", {}))

    # --------------------------------------------管家蚊子腿--------------------------------------------
    # note: 管家活动接入流程：
    #   1. 打开新活动的页面 https://guanjia.qq.com/act/cop/20210303dnf/index.html
    #   2. 按F12，在Console中输入 console.log(JSON.stringify(GLOBAL_AMP_CONFIG))，将结果复制到 format_json.json 中格式化，方便查看
    #   3. 在json中搜索 comGifts，定位到各个礼包的信息，并将下列变量的数值更新为新版本
    guanjia_common_gifts_act_id = "1146"  # 礼包活动ID
    guanjia_gift_id_special_rights = "7688"  # 电脑管家特权礼包
    guanjia_gift_id_game_helper = "7689"  # 游戏助手礼包
    guanjia_gift_id_return_user = "7690"  # 回归勇士礼包
    guanjia_gift_id_download_and_login_this_version_guanjia = "7691"  # 下载登录管家任务
    guanjia_gift_id_game_online_30_minutes = "7692"  # 每日游戏在线30分钟任务
    guanjia_gift_id_login_game_helper = "7693"  # 每日登录游戏助手任务
    # note: 4. 在json中搜索 lotGifts，定位到抽奖的信息，并将下列变量的数值更新为新版本
    guanjia_lottery_gifts_act_id = "1145"  # 抽奖活动ID

    # note: 5. 启用时取消注释fetch_guanjia_openid中开关，废弃时则注释掉
    # note: 6. 调整urls中管家蚊子腿的起止时间
    # note: 7. 调整config_ui中管家开关

    @try_except()
    def guanjia(self):
        show_head_line("管家蚊子腿")
        self.show_not_ams_act_info("管家蚊子腿")

        if not self.cfg.function_switches.get_guanjia or self.disable_most_activities():
            logger.warning("未启用领取管家蚊子腿活动合集功能，将跳过")
            return

        lr = self.fetch_guanjia_openid()
        if lr is None:
            return
        self.guanjia_lr = lr
        # 等一会，避免报错
        time.sleep(self.common_cfg.retry.request_wait_time)

        self.guanjia_common_gifts_op("电脑管家特权礼包", giftId=self.guanjia_gift_id_special_rights)
        self.guanjia_common_gifts_op("游戏助手礼包", giftId=self.guanjia_gift_id_game_helper)
        self.guanjia_common_gifts_op("回归勇士礼包", giftId=self.guanjia_gift_id_return_user)

        self.guanjia_common_gifts_op("下载安装并登录电脑管家", giftId=self.guanjia_gift_id_download_and_login_this_version_guanjia)

        self.guanjia_common_gifts_op("每日游戏在线30分钟", giftId=self.guanjia_gift_id_game_online_30_minutes)
        self.guanjia_common_gifts_op("每日登录游戏助手", giftId=self.guanjia_gift_id_login_game_helper)

        for i in range(10):
            res = self.guanjia_lottery_gifts_op("抽奖")
            # {"code": 4101, "msg": "积分不够", "result": []}
            if res["code"] != 0:
                break
            time.sleep(self.common_cfg.retry.request_wait_time)

    def is_guanjia_openid_expired(self, cached_guanjia_openid):
        if cached_guanjia_openid is None:
            return True

        lr = LoginResult(qc_openid=cached_guanjia_openid["qc_openid"], qc_k=cached_guanjia_openid["qc_k"])
        self.guanjia_lr = lr

        # {"code": 7005, "msg": "获取accToken失败", "result": []}
        # {"code": 29, "msg": "请求包参数错误", "result": []}
        res = self.guanjia_common_gifts_op("每日登录游戏助手", giftId=self.guanjia_gift_id_login_game_helper, print_res=False)
        return res["code"] in [7005, 29]

    def guanjia_common_gifts_op(self, ctx, giftId="", print_res=True):
        return self.guanjia_op(ctx, "comjoin", self.guanjia_common_gifts_act_id, giftId=giftId, print_res=print_res)

    def guanjia_lottery_gifts_op(self, ctx, print_res=True):
        return self.guanjia_op(ctx, "lottjoin", self.guanjia_lottery_gifts_act_id, print_res=print_res)

    def guanjia_op(self, ctx, api_name, act_id, giftId="", print_res=True):
        api = f"{api_name}_{act_id}"
        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        extra_cookies = f"__qc__openid={self.guanjia_lr.qc_openid}; __qc__k={self.guanjia_lr.qc_k};"
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
            if print_warning: logger.warning("未启用管家相关活动，将跳过尝试更新管家p_skey流程")
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
            logger.warning(color("bold_cyan") + "如果一直卡在管家登录流程，可能是你网不行，建议多试几次，真不行就关闭管家活动的开关~")
            # 重新获取
            ql = QQLogin(self.common_cfg)
            if self.cfg.login_mode == "qr_login":
                # 扫码登录
                lr = ql.qr_login(login_mode=ql.login_mode_guanjia, name=self.cfg.name)
            else:
                # 自动登录
                lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode=ql.login_mode_guanjia, name=self.cfg.name)
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
            logger.debug(f"本地保存管家openid信息，具体内容如下：{loginResult}")

    def load_guanjia_openid(self):
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_guanjia_openid_file()):
            return

        with open(self.get_local_saved_guanjia_openid_file(), "r", encoding="utf-8") as f:
            loginResult = json.load(f)
            logger.debug(f"读取本地缓存的管家openid信息，具体内容如下：{loginResult}")
            return loginResult

    def get_local_saved_guanjia_openid_file(self):
        return self.local_saved_guanjia_openid_file.format(self.cfg.name)

    # --------------------------------------------hello语音奖励兑换--------------------------------------------
    @try_except()
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

    def check_hello_voice_bind_role(self):
        data = self.do_hello_voice("检查账号绑定信息", "getRole", print_res=False)
        if data["iRet"] == -1011:
            # 未选择大区
            logger.warning(color("fg_bold_yellow") + "未绑定角色，请前往hello语音，点击左下方【首页】->左上角【游戏】->左上方【福利中心】->【DNF活动奖励&hello贝兑换】->在打开的网页中进行角色绑定")
            return False
        else:
            # 已选择大区
            roleInfo = HelloVoiceDnfRoleInfo().auto_update_config(data["jData"])
            logger.info(f"绑定角色信息: {roleInfo}")
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
        self.show_amesvr_act_info(self.dnf_carnival_op)

        if not self.cfg.function_switches.get_dnf_carnival or self.disable_most_activities():
            logger.warning("未启用领取2020DNF嘉年华页面主页面签到活动合集功能，将跳过")
            return

        self.check_dnf_carnival()

        self.dnf_carnival_op("12.11-12.14 阶段一签到", "721945")
        self.dnf_carnival_op("12.15-12.18 阶段二签到", "722198")
        self.dnf_carnival_op("12.19-12.26 阶段三与全勤", "722199")

    def check_dnf_carnival(self):
        self.check_bind_account("2020DNF嘉年华页面主页面签到", "https://dnf.qq.com/cp/a20201203carnival/index.html",
                                activity_op_func=self.dnf_carnival_op, query_bind_flowid="722055", commit_bind_flowid="722054")

    def dnf_carnival_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_carnival

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201203carnival/",
                                   **extra_params)

    # --------------------------------------------2020DNF嘉年华直播--------------------------------------------
    def dnf_carnival_live(self):
        if not self.common_cfg.test_mode:
            # 仅限测试模式运行
            return

        # https://dnf.qq.com/cp/a20201203carnival/index.html
        show_head_line("2020DNF嘉年华直播")
        self.show_amesvr_act_info(self.dnf_carnival_live_op)

        if not self.cfg.function_switches.get_dnf_carnival_live or self.disable_most_activities():
            logger.warning("未启用领取2020DNF嘉年华直播活动合集功能，将跳过")
            return

        self.check_dnf_carnival_live()

        def query_watch_time():
            res = self.dnf_carnival_live_op("查询观看时间", "722482", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue3)

        def watch_remaining_time():
            self.dnf_carnival_live_op("记录完成一分钟观看", "722476")

            current_watch_time = query_watch_time()
            remaining_time = 15 * 8 - current_watch_time
            logger.info(f"账号 {self.cfg.name} 当前已观看{current_watch_time}分钟，仍需观看{remaining_time}分钟")

        def query_used_lottery_times():
            res = self.dnf_carnival_live_op("查询获奖次数", "725567", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue1)

        def lottery_remaining_times():
            total_lottery_times = query_watch_time() // 15
            used_lottery_times = query_used_lottery_times()
            remaining_lottery_times = total_lottery_times - used_lottery_times
            logger.info(f"账号 {self.cfg.name} 抽奖次数信息：总计={total_lottery_times} 已使用={used_lottery_times} 剩余={remaining_lottery_times}")
            if remaining_lottery_times == 0:
                logger.warning("没有剩余次数，将不进行抽奖")
                return

            for i in range(remaining_lottery_times):
                res = self.dnf_carnival_live_op(f"{i + 1}. 抽奖", "722473")
                if res["ret"] != "0":
                    logger.warning(f"出错了，停止抽奖，剩余抽奖次数为{remaining_lottery_times - i}")
                    break

        watch_remaining_time()
        lottery_remaining_times()

    def check_dnf_carnival_live(self):
        self.check_bind_account("2020DNF嘉年华直播", "https://dnf.qq.com/cp/a20201203carnival/index.html",
                                activity_op_func=self.dnf_carnival_live_op, query_bind_flowid="722472", commit_bind_flowid="722471")

    def dnf_carnival_live_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_carnival_live

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201203carnival/",
                                   **extra_params)

    # --------------------------------------------DNF福利中心兑换--------------------------------------------
    @try_except()
    def dnf_welfare(self):
        # http://dnf.qq.com/cp/a20190312welfare/index.htm
        show_head_line("DNF福利中心兑换")
        self.show_amesvr_act_info(self.dnf_welfare_op)

        if not self.cfg.function_switches.get_dnf_welfare or self.disable_most_activities():
            logger.warning("未启用领取DNF福利中心兑换活动功能，将跳过")
            return

        self.check_dnf_welfare()

        key_shareCodes = "shareCodes"

        def exchange_package(sContent):
            key = "dnf_welfare_exchange_package"

            # 检查是否已经兑换过
            account_db = load_db_for(self.cfg.name)
            if key in account_db and account_db[key].get(sContent, False):
                logger.warning(f"已经兑换过【{sContent}】，不再尝试兑换")
                return

            reg = '^[0-9]+-[0-9A-Za-z]{18}$'
            if re.fullmatch(reg, sContent) is not None:
                siActivityId, sContent = sContent.split('-')
                res = self.dnf_welfare_op(f"兑换分享口令-{siActivityId}-{sContent}", "649260", siActivityId=siActivityId, sContent=quote_plus(quote_plus(quote_plus(sContent))))
            else:
                res = self.dnf_welfare_op(f"兑换口令-{sContent}", "558229", sContent=quote_plus(quote_plus(quote_plus(sContent))))
            if int(res["ret"]) != 0 or int(res["modRet"]["iRet"]) != 0:
                return

            # 本地标记已经兑换过
            def callback(account_db):
                if key not in account_db:
                    account_db[key] = {}

                account_db[key][sContent] = True

            update_db_for(self.cfg.name, callback)

            try:
                shareCode = res["modRet"]["jData"]["shareCode"]
                if shareCode != "":
                    db = load_db()

                    if key_shareCodes not in db:
                        db[key_shareCodes] = []
                    shareCodeList = db[key_shareCodes]

                    if shareCode not in shareCodeList:
                        shareCodeList.append(shareCode)

                    save_db(db)
            except Exception as e:
                pass

        db = load_db()
        shareCodeList = db.get(key_shareCodes, [])

        sContents = [
            "dnf2021",
            "寒冬雪人加持三觉助力新春",
            "来COLG百万勇士在线交友",
            "YZZ2021",
            "dnf121",
            "客服新春版本献礼",
            "客服恭祝春节快乐",
            "小酱油新春版本献礼",
            "官方论坛献豪礼",
            "神话尽从柱中来",
        ]
        random.shuffle(sContents)
        sContents = [*shareCodeList, *sContents]
        for sContent in sContents:
            exchange_package(sContent)

        # 登陆游戏领福利
        self.dnf_welfare_login_gifts_op("第一个 2020.01.21 - 2020.01.24 登录游戏", "732812")
        self.dnf_welfare_login_gifts_op("第二个 2020.01.25 - 2020.01.28 登录游戏", "732821")
        self.dnf_welfare_login_gifts_op("第三个 2020.01.29 - 2021.02.07 登录游戏", "732822")

        # 分享礼包
        self.dnf_welfare_login_gifts_op("分享奖励领取", "732820", siActivityId="19")

    def check_dnf_welfare(self):
        self.check_bind_account("DNF福利中心兑换", "http://dnf.qq.com/cp/a20190312welfare/index.htm",
                                activity_op_func=self.dnf_welfare_op, query_bind_flowid="558227", commit_bind_flowid="558226")

    def dnf_welfare_op(self, ctx, iFlowId, siActivityId="", sContent="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_welfare

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20190312welfare/",
                                   siActivityId=siActivityId, sContent=sContent,
                                   **extra_params)

    def dnf_welfare_login_gifts_op(self, ctx, iFlowId, siActivityId="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_welfare_login_gifts

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        checkInfo = self.get_dnf_roleinfo()

        checkparam = quote_plus(quote_plus(checkInfo.checkparam))

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20190312welfare/",
                                   sArea=roleinfo.serviceID, sPartition=roleinfo.serviceID, sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
                                   sRoleId=roleinfo.roleCode, sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
                                   md5str=checkInfo.md5str, ams_checkparam=checkparam, checkparam=checkparam,
                                   siActivityId=siActivityId,
                                   **extra_params)

    # --------------------------------------------DNF共创投票--------------------------------------------
    @try_except()
    def dnf_dianzan(self):
        # https://dnf.qq.com/cp/a20201126version/index.shtml
        show_head_line("DNF共创投票")
        self.show_amesvr_act_info(self.dnf_dianzan_op)

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

            logger.info(f"获取所有内容ID共计{len(contentIds)}个，将保存到本地，具体如下：{contentIds}")

            def _update_db(db):
                if db_key not in db:
                    db[db_key] = {}

                db[db_key]["contentIds"] = contentIds

            update_db(_update_db)

            return contentIds

        def getWorksData(iCategory2, page):
            ctx = f"查询点赞内容-{iCategory2}-{page}"
            res = self.get(ctx, self.urls.query_dianzan_contents, iCategory1=20, iCategory2=iCategory2, page=page, pagesize=pagesize, is_jsonp=True, is_normal_jsonp=True)
            return [v["iContentId"] for v in res["jData"]["data"]], int(res["jData"]["total"])

        def dianzan(idx, iContentId) -> bool:
            res = self.get(f"今日第{idx}次投票，目标为{iContentId}", self.urls.dianzan, iContentId=iContentId, is_jsonp=True, is_normal_jsonp=True)
            return int(res["iRet"]) == 0

        totalDianZanCount, _ = self.query_dnf_dianzan()
        if totalDianZanCount < 200:
            # 进行今天剩余的点赞操作
            today_dianzan()
        else:
            logger.warning("累积投票已经超过200次，无需再投票")

        # 查询点赞信息
        totalDianZanCount, rewardTakenInfo = self.query_dnf_dianzan()
        logger.warning(color("fg_bold_yellow") + f"DNF共创投票活动当前已投票{totalDianZanCount}次，奖励领取状态为{rewardTakenInfo}")

        # 领取点赞奖励
        self.dnf_dianzan_op("累计 10票", "725276")
        self.dnf_dianzan_op("累计 25票", "725340")
        self.dnf_dianzan_op("累计100票", "725341")
        self.dnf_dianzan_op("累计200票", "725342")

    def query_dnf_dianzan(self):
        res = self.dnf_dianzan_op("查询点赞信息", "725348", print_res=False)
        info = parse_amesvr_common_info(res)

        return int(info.sOutValue1), info.sOutValue2

    def check_dnf_dianzan(self):
        self.check_bind_account("DNF共创投票", "https://dnf.qq.com/cp/a20201126version/index.shtml",
                                activity_op_func=self.dnf_dianzan_op, query_bind_flowid="725330", commit_bind_flowid="725329")

    def dnf_dianzan_op(self, ctx, iFlowId, sContent="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_dianzan

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201126version/",
                                   **extra_params)

    # --------------------------------------------心悦app理财礼卡--------------------------------------------
    @try_except()
    def xinyue_financing(self):
        # https://xinyue.qq.com/act/app/xyjf/a20171031lclk/index1.shtml
        show_head_line("心悦app理财礼卡")
        self.show_amesvr_act_info(self.xinyue_financing_op)

        if not self.cfg.function_switches.get_xinyue_financing:
            logger.warning("未启用领取心悦app理财礼卡活动合集功能，将跳过")
            return

        selectedCards = ["升级版月卡", "体验版月卡", "升级版周卡", "体验版周卡"]
        logger.info(color("fg_bold_green") + f"当前设定的理财卡优先列表为: {selectedCards}")

        type2name = {
            "type1": "体验版周卡",
            "type2": "升级版周卡",
            "type3": "体验版月卡",
            "type4": "升级版月卡",
        }

        # ------------- 封装函数 ----------------

        def query_card_taken_map():
            res = AmesvrCommonModRet().auto_update_config(self.xinyue_financing_op("查询G分", "409361", print_res=False)["modRet"])
            statusList = res.sOutValue3.split('|')

            cardTakenMap = {}
            for i in range(1, 4 + 1):
                name = type2name[f"type{i}"]
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
        gPoints = self.query_gpoints()
        startPoints = gPoints
        logger.info(f"当前G分为{startPoints}")

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
                logger.warning(f"没有找到名为【{cardName}】的理财卡，请确认是否配置错误")
                continue

            buyPrice, buyFlowId, takeFlowId = financingCardsToBuyAndMap[cardName]
            cardInfo = cardInfoMap[cardName]
            taken = cardTakenMap[cardName]
            # 如果尚未购买（或过期），则购买
            if not cardInfo.buy:
                if gPoints >= buyPrice:
                    self.xinyue_financing_op(f"购买{cardName}", buyFlowId)
                    gPoints -= buyPrice
                else:
                    logger.warning(f"积分不够，将跳过购买~，购买{cardName}需要{buyPrice}G分，当前仅有{gPoints}G分")
                    continue

            # 此处以确保购买，尝试领取
            if taken:
                logger.warning(f"今日已经领取过{cardName}了，本次将跳过")
            else:
                self.xinyue_financing_op(f"领取{cardName}", takeFlowId)

        newGPoints = self.query_gpoints()
        delta = newGPoints - startPoints
        logger.warning("")
        logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 本次心悦理财礼卡操作共获得 {delta} G分（ {startPoints} -> {newGPoints} ）")
        logger.warning("")

        show_financing_info()

    @try_except(return_val_on_except=0)
    def query_gpoints(self):
        res = AmesvrCommonModRet().auto_update_config(self.xinyue_financing_op("查询G分", "409361", print_res=False)["modRet"])
        return int(res.sOutValue2)

    def xinyue_financing_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_xinyue_financing

        plat = 3  # app
        extraStr = quote_plus('"mod1":"1","mod2":"0","mod3":"x27"')

        return self.amesvr_request(ctx, "comm.ams.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "https://xinyue.qq.com/act/app/xyjf/a20171031lclk/index1.shtml",
                                   plat=plat, extraStr=extraStr,
                                   **extra_params)

    # --------------------------------------------心悦猫咪--------------------------------------------
    @try_except()
    def xinyue_cat(self):
        # https://xinyue.qq.com/act/a20180912tgclubcat/index.html
        show_head_line("心悦猫咪")
        self.show_amesvr_act_info(self.xinyue_cat_op)

        if not self.cfg.function_switches.get_xinyue_cat:
            logger.warning("未启用领取心悦猫咪活动合集功能，将跳过")
            return

        # --------------- 封装接口 ---------------

        def queryUserInfo():
            res = self.xinyue_cat_op("查询用户信息", "449169", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = XinyueCatUserInfo()
            info.name = unquote_plus(raw_info.sOutValue1.split('|')[0])
            info.gpoints = int(raw_info.sOutValue2)
            info.account = raw_info.sOutValue4
            info.vipLevel = int(raw_info.sOutValue6)
            info.has_cat = raw_info.sOutValue8 == "1"

            return info

        def getPetFinghtInfo():
            res = self.xinyue_cat_op("查询心悦猫咪信息", "532974", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = XinyueCatInfo()
            info.fighting_capacity = int(raw_info.sOutValue1)
            info.yuanqi = int(raw_info.sOutValue2)

            return info

        def get_skin_list():
            return self.xinyue_cat_app_op("查询心悦猫咪皮肤列表", api="get_skin_list")

        def use_skin(skin_id):
            return self.xinyue_cat_app_op("使用皮肤", api="use_skin", skin_id=skin_id)

        def get_decoration_list():
            return self.xinyue_cat_app_op("查询心悦猫咪装饰列表", api="get_decoration_list")

        def use_decoration(decoration_id):
            return self.xinyue_cat_app_op("使用装饰", api="use_decoration", decoration_id=decoration_id)

        def make_money_new(uin, adLevel, adPower):
            return self.xinyue_cat_app_op("历练", api="make_money_new", uin=uin, adLevel=adLevel, adPower=adPower)

        def queryCatInfoFromApp():
            res = self.xinyue_cat_app_op("从app接口查询心悦猫咪信息", api="get_user", print_res=False)
            info = XinyueCatInfoFromApp().auto_update_config(res["data"])

            return info

        def queryPetId():
            return queryCatInfoFromApp().pet_id

        def fight(ctx, username):
            res = self.xinyue_cat_op(f"{ctx}-匹配", "471145")
            wait()

            result = XinyueCatMatchResult().auto_update_config(res["modRet"]["jData"])
            if result.ending == 1:
                self.xinyue_cat_op(f"{ctx}-结算-胜利", "508006", username=quote_plus(username))
            else:
                self.xinyue_cat_op(f"{ctx}-结算-失败", "471383", username=quote_plus(username))

            wait()

        def wait():
            time.sleep(5)

        # --------------- 正式逻辑 ---------------

        old_user_info = queryUserInfo()
        old_pet_info = getPetFinghtInfo()

        # 查询相关信息
        if not old_user_info.has_cat:
            self.xinyue_cat_op("领取猫咪", "532871")
        else:
            logger.info("已经领取过猫咪，无需再次领取")

        # 领取历练奖励
        self.xinyue_cat_op("每日首次进入页面增加元气值", "497774")
        self.xinyue_cat_op("领取历练奖励", "532968")

        # 妆容和装饰（小橘子和贤德昭仪）
        petId = queryPetId()
        skin_id = "8"  # 贤德昭仪
        decoration_id = "7"  # 小橘子

        # 尝试购买
        self.xinyue_cat_op("G分购买猫咪皮肤-贤德昭仪", "507986", petId=petId, skin_id=skin_id)
        wait()
        self.xinyue_cat_op("G分购买装饰-小橘子", "508072", petId=petId, decoration_id=decoration_id)
        wait()

        # 尝试穿戴妆容和装饰
        use_skin(skin_id)
        wait()
        use_decoration(decoration_id)
        wait()

        # 战斗
        pet_info = getPetFinghtInfo()
        total_fight_times = pet_info.yuanqi // 20
        logger.warning(color("fg_bold_yellow") + f"当前元气为{pet_info.yuanqi}，共可进行{total_fight_times}次战斗")
        for i in range(total_fight_times):
            fight(f"第{i + 1}/{total_fight_times}次战斗", old_user_info.name)

        # 历练
        user_info = queryUserInfo()
        pet_info = getPetFinghtInfo()
        for adLevel in [4, 3, 2, 1]:
            make_money_new(user_info.account, adLevel, pet_info.fighting_capacity)

        new_user_info = queryUserInfo()
        new_pet_info = getPetFinghtInfo()

        delta = new_user_info.gpoints - old_user_info.gpoints
        fc_delta = new_pet_info.fighting_capacity - old_pet_info.fighting_capacity
        logger.warning("")
        logger.warning(color("fg_bold_yellow") + (
            f"账号 {self.cfg.name} 本次心悦猫咪操作共获得 {delta} G分（ {old_user_info.gpoints} -> {new_user_info.gpoints} ）"
            f"，战力增加 {fc_delta}（ {old_pet_info.fighting_capacity} -> {new_pet_info.fighting_capacity} ）"
        ))
        logger.warning("")

    def xinyue_cat_app_op(self, ctx, api, skin_id="", decoration_id="", uin="", adLevel="", adPower="", print_res=True):
        return self.get(ctx, self.urls.xinyue_cat_api, api=api,
                        skin_id=skin_id, decoration_id=decoration_id,
                        uin=uin, adLevel=adLevel, adPower=adPower,
                        print_res=print_res)

    def xinyue_cat_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_xinyue_cat

        extraStr = quote_plus('"mod1":"1","mod2":"0","mod3":"x42"')

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20180912tgclubcat/",
                                   extraStr=extraStr,
                                   **extra_params)

    # --------------------------------------------心悦app周礼包--------------------------------------------
    @try_except()
    def xinyue_weekly_gift(self):
        # https://xinyue.qq.com/act/a20180906gifts/index.html
        show_head_line("心悦app周礼包")
        self.show_amesvr_act_info(self.xinyue_weekly_gift_op)

        if not self.cfg.function_switches.get_xinyue_weekly_gift:
            logger.warning("未启用领取心悦app周礼包活动合集功能，将跳过")
            return

        def query_info():
            res = self.xinyue_weekly_gift_op("查询信息", "484520", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = XinyueWeeklyGiftInfo()
            info.qq = raw_info.sOutValue1
            info.iLevel = int(raw_info.sOutValue2)
            info.sLevel = raw_info.sOutValue3
            info.tTicket = int(raw_info.sOutValue4) + int(raw_info.sOutValue5)
            info.gift_got_list = raw_info.sOutValue6.split('|')

            return info

        def query_gpoints_info():
            res = self.xinyue_weekly_gift_op("查询G分信息", "603392", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = XinyueWeeklyGPointsInfo()
            info.nickname = unquote_plus(raw_info.sOutValue1)
            info.gpoints = int(raw_info.sOutValue2)

            return info

        @try_except()
        def take_all_gifts():
            # note: 因为已经有一键领取的接口，暂不接入单个领取的接口
            # self.xinyue_weekly_gift_op("领取单个周礼包", "508441", PackId="1")

            self.xinyue_weekly_gift_op("一键领取周礼包", "508440")
            logger.info("这个一键领取接口似乎有时候请求会提示仅限心悦用户参与，实际上任何级别都可以的，一周总有一次会成功的-。-")

        old_gpoints_info = query_gpoints_info()

        take_all_gifts()

        info = query_info()
        logger.info(f"当前剩余免G分抽奖券数目为{info.tTicket}")
        for idx in range(info.tTicket):
            self.xinyue_weekly_gift_op(f"第{idx + 1}/{info.tTicket}次免费抽奖并等待五秒", "603340")
            if idx != info.tTicket - 1:
                time.sleep(5)

        new_gpoints_info = query_gpoints_info()

        delta = new_gpoints_info.gpoints - old_gpoints_info.gpoints
        logger.warning("")
        logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 本次心悦周礼包操作共免费抽奖{info.tTicket}次，共获得 {delta} G分（ {old_gpoints_info.gpoints} -> {new_gpoints_info.gpoints} ）")
        logger.warning("")

    def xinyue_weekly_gift_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_xinyue_weekly_gift

        extraStr = quote_plus('"mod1":"1","mod2":"4","mod3":"x48"')

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20180906gifts/",
                                   extraStr=extraStr,
                                   **extra_params)

    # --------------------------------------------dnf漂流瓶--------------------------------------------
    @try_except()
    def dnf_drift(self):
        # https://dnf.qq.com/cp/a20201211driftm/index.html
        show_head_line("dnf漂流瓶")
        self.show_amesvr_act_info(self.dnf_drift_op)

        if not self.cfg.function_switches.get_dnf_drift or self.disable_most_activities():
            logger.warning("未启用领取dnf漂流瓶活动功能，将跳过")
            return

        self.check_dnf_drift()

        def send_friend_invitation(typStr, flowid, dayLimit):
            send_count = 0
            for sendQQ in self.cfg.drift_send_qq_list:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)
                res = self.dnf_drift_op(f"发送{typStr}好友邀请-{sendQQ}赠送2积分", flowid, sendQQ=sendQQ, moduleId="2")

                send_count += 1
                if int(res["ret"]) != 0 or send_count >= dayLimit:
                    logger.warning(f"已达到本日邀请上限({dayLimit})，将停止邀请")
                    return

        def take_friend_awards(typStr, type, moduleId, take_points_flowid):
            page = 1
            while True:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)

                queryRes = self.dnf_drift_op(f"拉取接受的{typStr}好友列表", "725358", page=str(page), type=type)
                if int(queryRes["ret"]) != 0 or queryRes["modRet"]["jData"]["iTotal"] == 0:
                    logger.warning("没有更多接收邀请的好友了，停止领取积分")
                    return

                for friend_info in queryRes["modRet"]["jData"]["jData"]:
                    takeRes = self.dnf_drift_op(f"邀请人领取{typStr}邀请{friend_info['iUin']}的积分", take_points_flowid, acceptId=friend_info["id"], moduleId=moduleId)
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
        logger.info(color("bold_yellow") + f"当前积分为{remainingPoints}，总计可进行{remainingLotteryTimes}次抽奖。历史累计获取积分数为{totalPoints}")
        for i in range(remainingLotteryTimes):
            self.dnf_drift_op(f"开始夺宝 - 第{i + 1}次", "726379")

        # 04 在线好礼站
        self.dnf_drift_op("在线30min", "725675", moduleId="2")
        self.dnf_drift_op("累计3天礼包", "725699", moduleId="0", giftId="1437440")
        self.dnf_drift_op("累计7天礼包", "725699", moduleId="0", giftId="1437441")
        self.dnf_drift_op("累计15天礼包", "725699", moduleId="0", giftId="1437442")

        # 分享
        self.dnf_drift_op("分享领取礼包", "726345")

    def query_dnf_drift_points(self):
        res = self.dnf_drift_op("查询基础信息", "726353")
        info = parse_amesvr_common_info(res)
        total, remaining = int(info.sOutValue2), int(info.sOutValue2) - int(info.sOutValue1) * 4
        return total, remaining

    def check_dnf_drift(self):
        typ = random.choice([1, 2])
        activity_url = f"https://dnf.qq.com/cp/a20201211driftm/index.html?sId=0252c9b811d66dc1f0c9c6284b378e40&type={typ}"

        self.check_bind_account("dnf漂流瓶", activity_url,
                                activity_op_func=self.dnf_drift_op, query_bind_flowid="725357", commit_bind_flowid="725356")

        if is_first_run("check_dnf_drift"):
            msg = "求帮忙做一下邀请任务0-0  只用在点击确定按钮后弹出的活动页面中点【确认接受邀请】就行啦（这条消息只会出现一次）"
            async_message_box(msg, "帮忙接受一下邀请0-0", open_url=activity_url)

    def dnf_drift_op(self, ctx, iFlowId, page="", type="", moduleId="", giftId="", acceptId="", sendQQ="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_drift

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201211driftm/",
                                   page=page, type=type, moduleId=moduleId, giftId=giftId, acceptId=acceptId, sendQQ=sendQQ,
                                   **extra_params)

    # --------------------------------------------DNF马杰洛的规划--------------------------------------------
    @try_except()
    def majieluo(self):
        # https://dnf.qq.com/cp/a20210311welfare/index.html
        show_head_line("DNF马杰洛的规划")
        self.show_amesvr_act_info(self.majieluo_op)

        if not self.cfg.function_switches.get_majieluo or self.disable_most_activities():
            logger.warning("未启用领取DNF马杰洛的规划活动功能，将跳过")
            return

        self.check_majieluo()

        friend_db_key = "majieluoFriendQQs"
        local_invited_friends_db_key = "majieluo_local_invited_friend_v4"
        invited_by_other_db_key = "majieluo_invited_by_other_list_v4"
        award_taken_friends_db_key = "majieluo_award_taken_friends_v4"

        def qeury_not_invited_friends_with_cache():
            account_db = load_db_for(self.cfg.name)

            invited_friends = query_invited_friends()
            invited_by_other = query_invited_by_other_list()

            def filter_not_invited_friends(friendQQs):
                validFriendQQs = []
                for friendQQ in friendQQs:
                    if friendQQ not in invited_friends and friendQQ not in invited_by_other:
                        validFriendQQs.append(friendQQ)

                return validFriendQQs

            if friend_db_key in account_db:
                friendQQs = account_db[friend_db_key]

                return filter_not_invited_friends(friendQQs)

            return filter_not_invited_friends(qeury_not_invited_friends())

        def query_invited_friends():
            res = self.majieluo_op("查询已邀请的好友列表", "744194", print_res=False)

            invited_friends = query_local_invited_friends()
            try:
                for info in res["modRet"]["jData"]["jData"]:
                    qq = info["sendToQQ"]
                    if qq not in invited_friends:
                        invited_friends.append(qq)
            except:
                # 如果没有邀请过任何人，上面这样获取似乎是会报错的。手头上暂时没有这种号，先兼容下吧。
                pass

            return invited_friends

        def qeury_not_invited_friends():
            logger.info("本地无好友名单，或缓存的好友均已邀请过，需要重新拉取，请稍后~")
            friendQQs = []

            page = 1
            page_size = 6
            while True:
                info = query_friends(page, page_size)
                if len(info.list) == 0:
                    # 没有未邀请的好友了
                    break
                for friend in info.list:
                    friendQQs.append(str(friend.uin))

                page += 1

            logger.info(f"获取好友名单共计{len(friendQQs)}个，将保存到本地，具体如下：{friendQQs}")

            def _update_db(udb):
                udb[friend_db_key] = friendQQs

            update_db_for(self.cfg.name, _update_db)

            return friendQQs

        def query_friends(page, page_size):
            res = self.majieluo_op("查询好友列表（赠送）", "744184", pageNow=str(page), pageSize=str(page_size), print_res=True)
            info = AmesvrQueryFriendsInfo().auto_update_config(res["modRet"]["jData"])
            return info

        def update_invited_by_other_list(qq):
            def _update_db(udb):
                if invited_by_other_db_key not in udb:
                    udb[invited_by_other_db_key] = []

                if qq not in udb[invited_by_other_db_key]:
                    udb[invited_by_other_db_key].append(qq)

            update_db_for(self.cfg.name, _update_db)

        def query_invited_by_other_list():
            udb = load_db_for(self.cfg.name)

            return udb.get(invited_by_other_db_key, [])

        def update_local_invited_friends(qq):
            def _update_db(udb):
                if local_invited_friends_db_key not in udb:
                    udb[local_invited_friends_db_key] = []

                if qq not in udb[local_invited_friends_db_key]:
                    udb[local_invited_friends_db_key].append(qq)

            update_db_for(self.cfg.name, _update_db)

        def query_local_invited_friends():
            udb = load_db_for(self.cfg.name)

            return udb.get(local_invited_friends_db_key, [])

        def update_award_taken_friends(qq):
            def _update_db(udb):
                if award_taken_friends_db_key not in udb:
                    udb[award_taken_friends_db_key] = []

                if qq not in udb[award_taken_friends_db_key]:
                    udb[award_taken_friends_db_key].append(qq)

            update_db_for(self.cfg.name, _update_db)

        def query_award_taken_friends():
            udb = load_db_for(self.cfg.name)

            return udb.get(award_taken_friends_db_key, [])

        # 马杰洛的见面礼
        self.majieluo_op("领取见面礼", "744170")

        # 赛利亚的新春祝福
        self.majieluo_op("抽取卡片", "744173")
        cards = [1, 2, 3, 4, 5]
        random.shuffle(cards)
        receiveUin = self.common_cfg.majieluo_send_card_target_qq
        if receiveUin != "" and receiveUin != uin2qq(self.cfg.account_info.uin):
            for cardType in cards:
                self.majieluo_op(f"赠送好友卡片-{cardType}", "744175", sendName=quote_plus(self.cfg.name), cardType=str(cardType), receiveUin=receiveUin)

        logger.info(color("bold_yellow") + f"当前拥有的卡牌为{self.query_majieluo_card_info()}")
        self.majieluo_op("集齐五个赛利亚，兑换200个时间引导石", "744171")

        # 马杰洛的特殊任务
        self.majieluo_op("【登录游戏】抽取时间引导石", "744172")
        self.majieluo_op("【通关任意一次副本】奖励翻倍", "744178")
        self.majieluo_op("连续登录7天额外领取100个时间引导石", "744337")

        # 黑钻送好友
        if self.cfg.enable_majieluo_invite_friend:
            not_invited_friends = qeury_not_invited_friends_with_cache()
            if len(not_invited_friends) > 0:
                logger.info(color("bold_green") + f"接下来将尝试给总计{len(not_invited_friends)}个好友发送黑钻邀请（不会实际发送消息，不必担心社死<_<）")

            for idx, receiverQQ in enumerate(not_invited_friends):
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)
                # {"ret": "700", "msg": "非常抱歉，您还不满足参加该活动的条件！", "flowRet": {"iRet": "700", "sLogSerialNum": "AMS-DNF-1226165046-1QvZiG-350347-727218", "iAlertSerial": "0", "iCondNotMetId": "1412917", "sMsg": "您每天最多为2名好友赠送黑钻~", "sCondNotMetTips": "您每天最多为2名好友赠送黑钻~"}, "failedRet": {"793123": {"iRuleId": "793123", "jRuleFailedInfo": {"iFailedRet": 700, "iCondId": "1412917", "iCondParam": "sCondition1", "iCondRet": "2"}}}}
                res = self.majieluo_op(f"{idx + 1}/{len(not_invited_friends)} 【赠礼】发送赠送黑钻邀请-{receiverQQ}(不会实际发消息)", "744186", receiver=receiverQQ, receiverName=quote_plus("小号"))
                if int(res["ret"]) == 700:
                    if res["flowRet"]["sMsg"] == "该好友已被其他玩家邀请，请重新选择想邀请的好友或刷新好友列表~":
                        update_invited_by_other_list(receiverQQ)
                        continue
                    elif res["flowRet"]["sMsg"] == "您已经给该好友发过消息了~":
                        update_local_invited_friends(receiverQQ)
                        continue
                    else:
                        logger.warning("今日赠送上限已到达，将停止~")
                        break
                else:
                    update_local_invited_friends(receiverQQ)

            award_taken_friends = query_award_taken_friends()
            for receiverQQ in query_invited_friends():
                if receiverQQ in award_taken_friends:
                    continue
                res = self.majieluo_op("赠送黑钻后，领取9个时间引导石", "744179", receiver=receiverQQ)
                if int(res["ret"]) == 600 and res["flowRet"]["sMsg"] == "抱歉，您已经领取过该奖励了~":
                    update_award_taken_friends(receiverQQ)
                    continue
                elif int(res["ret"]) == 0 and res["modRet"]["sMsg"] == "非常抱歉，您今日领取次数已达最大，请明日再来领取！":
                    break
                else:
                    update_award_taken_friends(receiverQQ)
        else:
            logger.info("未启用马杰洛黑钻送好友功能，将跳过~")

        self.majieluo_op("接受好友赠送邀请，领取黑钻", "744180", inviteId="239125", receiverUrl=quote_plus("https://game.gtimg.cn/images/dnf/cp/a20210121welfare/share.png"))

        # 提取得福利
        stoneCount = self.query_stone_count()
        logger.warning(color("bold_yellow") + f"当前共有{stoneCount}个引导石")

        now = datetime.datetime.now()
        # 无视活动中的月底清空那句话
        # note：根据1.21这次的经验，如果标记是1.21，当天就结束了，需要在1.20去领取奖励
        endTime = "20210411"

        takeStone = False
        takeStoneActId = "744181"
        if stoneCount >= 1000:
            # 达到1000个
            self.majieluo_op("提取时间引导石", takeStoneActId, giftNum="10")
            takeStone = True
        elif get_today() == endTime:
            # 今天是活动最后一天
            self.majieluo_op("提取时间引导石", takeStoneActId, giftNum=str(stoneCount // 100))
            takeStone = True
        else:
            logger.info(f"当前未到最后领取期限（活动结束时-{endTime} 23:59:59），且石头数目({stoneCount})不足1000，故不尝试提取")

        if takeStone:
            self.majieluo_op("提取福利（1000）", "744189")
            self.majieluo_op("提取福利（700、800、900）", "744188")
            self.majieluo_op("提取福利（300、400、500、600）", "744182")

    @try_except(return_val_on_except=0, show_exception_info=False)
    def query_stone_count(self):
        res = self.majieluo_op("查询当前时间引导石数量", "744195", print_res=False)
        info = parse_amesvr_common_info(res)
        return int(info.sOutValue1)

    @try_except(return_val_on_except="", show_exception_info=False)
    def query_majieluo_card_info(self):
        res = self.majieluo_op("查询信息", "744177", print_res=False)

        card_info = ""
        info = parse_amesvr_common_info(res)
        # 默认排序与表现一致，改为跟ui表现一致
        # 守护者 | 龙骑士三觉 | 帕拉丁三觉 | 混沌魔灵三觉 | 精灵骑士三觉
        temp = info.sOutValue1.split('|')
        order = [1, 3, 2, 5, 4]
        actual = []
        for idx in order:
            actual.append(temp[idx - 1])

        card_info = '|'.join(actual)

        return card_info

    def check_majieluo(self):
        self.check_bind_account("DNF马杰洛的规划", "https://dnf.qq.com/cp/a20210311welfare/index.html",
                                activity_op_func=self.majieluo_op, query_bind_flowid="744167", commit_bind_flowid="744166")

    def majieluo_op(self, ctx, iFlowId, cardType="", inviteId="", sendName="", receiveUin="", receiver="", receiverName="", receiverUrl="", giftNum="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_majieluo

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210311welfare/",
                                   cardType=cardType, inviteId=inviteId, sendName=sendName, receiveUin=receiveUin,
                                   receiver=receiver, receiverName=receiverName, receiverUrl=receiverUrl, giftNum=giftNum,
                                   **extra_params)

    # --------------------------------------------暖冬好礼活动--------------------------------------------
    @try_except()
    def warm_winter(self):
        # https://dnf.qq.com/lbact/a20200911lbz3dns/index.html
        show_head_line("暖冬好礼活动")
        self.show_amesvr_act_info(self.warm_winter_op)

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
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {get_checkin_days()} 天")
        self.warm_winter_op("签到3天礼包", "723170")
        self.warm_winter_op("签到5天礼包", "723171")
        self.warm_winter_op("签到7天礼包", "723172")
        self.warm_winter_op("签到10天礼包", "723173")
        self.warm_winter_op("签到15天礼包", "723174")

        # 03 累计签到抽大奖
        self.warm_winter_op("1.在WeGame启动DNF", "723175")
        self.warm_winter_op("2.游戏在线30分钟", "723176")
        total_lottery_times, lottery_times = get_lottery_times()
        logger.info(color("fg_bold_cyan") + f"即将进行抽奖，当前剩余抽奖资格为{lottery_times}，累计获取{total_lottery_times}次抽奖机会")
        for i in range(lottery_times):
            res = self.warm_winter_op("每日抽奖", "723177")
            if res.get('ret', "0") == "600":
                # {"ret": "600", "msg": "非常抱歉，您的资格已经用尽！", "flowRet": {"iRet": "600", "sLogSerialNum": "AMS-DNF-1031000622-s0IQqN-331515-703957", "iAlertSerial": "0", "sMsg": "非常抱歉！您的资格已用尽！"}, "failedRet": {"762140": {"iRuleId": "762140", "jRuleFailedInfo": {"iFailedRet": 600}}}}
                break

    def check_warm_winter(self):
        self.check_bind_account("暖冬好礼", "https://dnf.qq.com/lbact/a20200911lbz3dns/index.html",
                                activity_op_func=self.warm_winter_op, query_bind_flowid="723162", commit_bind_flowid="723161")

    def warm_winter_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_warm_winter

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20200911lbz3dns/",
                                   **extra_params)

    # --------------------------------------------qq视频-看江湖有翡--------------------------------------------
    @try_except()
    def youfei(self):
        # https://dnf.qq.com/cp/a20201227youfeim/index.html
        show_head_line("qq视频-看江湖有翡")
        self.show_amesvr_act_info(self.youfei_op)

        if not self.cfg.function_switches.get_youfei or self.disable_most_activities():
            logger.warning("未启用领取qq视频-看江湖有翡活动合集功能，将跳过")
            return

        self.check_youfei()

        def query_signin_days():
            res = self.youfei_op("查询签到状态", "728501", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue1)

        self.youfei_op("幸运用户礼包", "728407")
        self.youfei_op("勇士见面礼包", "731400")
        self.youfei_op("分享领取", "730006")

        self.youfei_op("在线30分钟礼包", "728419")
        logger.warning(color("bold_yellow") + f"累计已签到{query_signin_days()}天")
        self.youfei_op("签到3天礼包", "728420")
        self.youfei_op("签到7天礼包", "728450")
        self.youfei_op("签到15天礼包", "728451")

    def check_youfei(self):
        self.check_bind_account("qq视频-看江湖有翡", "https://dnf.qq.com/cp/a20201227youfeim/index.html",
                                activity_op_func=self.youfei_op, query_bind_flowid="727498", commit_bind_flowid="727497")

    def youfei_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_youfei

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20201227youfeim/",
                                   **extra_params)

    # --------------------------------------------dnf论坛签到--------------------------------------------
    @try_except()
    def dnf_bbs_signin(self):
        # https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign
        show_head_line("dnf官方论坛签到")
        self.show_amesvr_act_info(self.dnf_bbs_op)

        if not self.cfg.function_switches.get_dnf_bbs_signin or self.disable_most_activities():
            logger.warning("未启用领取dnf官方论坛签到活动合集功能，将跳过")
            return

        if self.cfg.dnf_bbs_cookie == "" or self.cfg.dnf_bbs_formhash == "":
            logger.warning("未配置dnf官方论坛的cookie或formhash，将跳过（dnf官方论坛相关的配置会配置就配置，不会就不要配置，我不会回答关于这俩如何获取的问题）")
            return

        def signin():
            retryCfg = self.common_cfg.retry
            for idx in range(retryCfg.max_retry_count):
                try:
                    url = self.urls.dnf_bbs_signin.format(formhash=self.cfg.dnf_bbs_formhash)
                    headers = {
                        "cookie": self.cfg.dnf_bbs_cookie,
                        "accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                        "accept-encoding": 'gzip, deflate, br',
                        "accept-language": 'en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,en-GB;q=0.6,ja;q=0.5',
                        "cache-control": 'max-age=0',
                        "content-type": 'application/x-www-form-urlencoded',
                        "dnt": '1',
                        "origin": 'https://dnf.gamebbs.qq.com',
                        "referer": 'https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign',
                        "sec-ch-ua": '"Google Chrome";v="87", " Not;A Brand";v="99", "Chromium";v="87"',
                        "sec-ch-ua-mobile": '?0',
                        "sec-fetch-dest": 'document',
                        "sec-fetch-mode": 'navigate',
                        "sec-fetch-site": 'same-origin',
                        "sec-fetch-user": '?1',
                        "upgrade-insecure-requests": '1',
                        "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
                    }

                    res = requests.post(url, headers=headers)
                    html_text = res.text

                    prefixes = [
                        '<div id="messagetext" class="alert_right">\n<p>',
                        '<div id="messagetext" class="alert_info">\n<p>',
                    ]
                    suffix = '</p>'
                    for prefix in prefixes:
                        if prefix in html_text:
                            prefix_idx = html_text.index(prefix) + len(prefix)
                            suffix_idx = html_text.index(suffix, prefix_idx)
                            logger.info(f"论坛签到OK: {html_text[prefix_idx:suffix_idx]}")
                            return

                    logger.warning(color("bold_yellow") + "不知道为啥没有这个前缀，请去日志文件查看具体请求返回的结果是啥。将等待一会，然后重试")
                    logger.debug(f"不在预期内的签到返回内容如下：\n{html_text}")
                    time.sleep(retryCfg.retry_wait_time)
                except Exception as e:
                    logger.exception(f"第{idx + 1}次尝试论坛签到失败了，等待一会", exc_info=e)
                    time.sleep(retryCfg.retry_wait_time)

        def query_dbq():
            res = self.dnf_bbs_op("查询代币券", "730277", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue1)

        def query_remaining_quota():
            res = self.dnf_bbs_op("查询礼包剩余量", "730763", print_res=False)
            info = parse_amesvr_common_info(res)

            logger.info('\n'.join([
                "当前礼包全局剩余量如下",
                f"\t便携式锻造炉: {info.sOutValue1}",
                f"\t一次性增幅器: {info.sOutValue2}",
                f"\t凯丽的强化器: {info.sOutValue3}",
                f"\t抗疲劳秘药(10点): {info.sOutValue4}",
                f"\t时间引导石礼盒 (10个): {info.sOutValue5}",
                f"\t抗疲劳秘药 (5点): {info.sOutValue6}",
            ]))

        def try_exchange():
            operations = [
                ("抗疲劳秘药10点兑换", "728541", 2),
                ("抗疲劳秘药5点兑换", "728543", 2),
                ("时间引导石兑换", "728542", 2),
                ("凯丽的强化器兑换", "728540", 6),
                ("一次性增幅器兑换", "728539", 6),
                ("便携锻造炉兑换", "728494", 6),
            ]

            for name, flowid, count in operations:
                print(name, flowid, count)

                for i in range(count):
                    res = self.dnf_bbs_op(name, flowid)
                    if res["ret"] == "700":
                        msg = res["flowRet"]["sMsg"]
                        if msg in ["您的该礼包兑换次数已达上限~", "抱歉，该礼包已被领完~"]:
                            # {"ret": "700", "flowRet": {"iRet": "700", "iCondNotMetId": "1425065", "sMsg": "您的该礼包兑换次数已达上限~", "sCondNotMetTips": "您的该礼包兑换次数已达上限~"}}
                            # 已达到兑换上限，尝试下一个
                            break
                        elif msg == "您的代币券不足~":
                            # {"ret": "700", "flowRet": {"iRet": "700", "iCondNotMetId": "1423792", "sMsg": "您的代币券不足~", "sCondNotMetTips": "您的代币券不足~"}}
                            logger.warning("代币券不足，直接退出，确保优先级高的兑换后才会兑换低优先级的")
                            return

        # ================= 实际逻辑 =================
        old_dbq = query_dbq()

        # 签到
        signin()

        after_sign_dbq = query_dbq()

        # 兑换签到奖励
        self.check_dnf_bbs()
        query_remaining_quota()
        try_exchange()

        after_exchange_dbq = query_dbq()
        logger.warning(color("bold_yellow") + f"账号 {self.cfg.name} 本次论坛签到获得 {after_sign_dbq - old_dbq} 个代币券，兑换道具消耗了 {after_exchange_dbq - after_sign_dbq} 个代币券，余额：{old_dbq} => {after_exchange_dbq}")

    def check_dnf_bbs(self):
        self.check_bind_account("DNF论坛积分兑换活动", "https://dnf.qq.com/act/a20201229act/index.html",
                                activity_op_func=self.dnf_bbs_op, query_bind_flowid="728503", commit_bind_flowid="728502")

    def dnf_bbs_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_bbs

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/act/a20201229act/",
                                   **extra_params)

    # --------------------------------------------会员关怀--------------------------------------------
    @try_except()
    def vip_mentor(self):
        show_head_line("会员关怀")
        self.show_not_ams_act_info("会员关怀")

        if not self.cfg.function_switches.get_vip_mentor or self.disable_most_activities():
            logger.warning("未启用领取会员关怀功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        lr = self.fetch_pskey()
        if lr is None:
            return

        qa = QzoneActivity(self, lr)
        qa.vip_mentor()

    # --------------------------------------------DNF新春夺宝大作战--------------------------------------------
    @try_except()
    def dnf_spring(self):
        # https://xinyue.qq.com/act/a20210104cjhdh5/index.html
        show_head_line("DNF新春夺宝大作战")
        self.show_amesvr_act_info(self.dnf_spring_op)

        if not self.cfg.function_switches.get_dnf_spring or self.disable_most_activities():
            logger.warning("未启用领取DNF新春夺宝大作战活动合集功能，将跳过")
            return

        self.check_dnf_spring()

        xinyue_info = self.query_xinyue_info("查询心悦信息", print_res=False)
        today = get_today()

        if today >= "20210121":
            # 会员专属 开买就送
            if xinyue_info.xytype < 5:
                self.dnf_spring_op("特邀充值礼", "730772")
            else:
                self.dnf_spring_op("VIP充值礼", "730800", cz=xinyue_info.xytype)

            # 全民夺宝 追忆天空
            info = self.query_dnf_spring_info()
            logger.warning(color("bold_yellow") +
                           f"活动期间共充值DNF{info.recharge_money}元, 目前有{info.current_spoon_count}个汤勺，历史共获取{info.total_spoon_count}个汤勺")

            for i in range(info.current_spoon_count):
                self.dnf_spring_op(f"第{i + 1}次捞饺子", "731311")

            # 刷新一下
            info = self.query_dnf_spring_info()
            logger.warning(color("bold_yellow") + f"累积捞饺子{info.laojiaozi_count}次")

            if info.laojiaozi_count >= 24:
                self.dnf_spring_op("福袋激活", "731492")
                self.dnf_spring_op("专属福袋", "731858")

            # 再刷新一下
            info = self.query_dnf_spring_info()
            if info.total_take_fudai >= 10000:
                self.dnf_spring_op("福袋B级", "731863")
            if info.total_take_fudai >= 50000:
                self.dnf_spring_op("福袋A级", "731867")
            if info.total_take_fudai >= 500000:
                self.dnf_spring_op("福袋S级", "731870")
        else:
            logger.info("充值礼、捞饺子和福袋1.21后才开始，先跳过")

        # 会员专享新年礼
        if xinyue_info.xytype < 5:
            self.dnf_spring_op("特邀专享礼", "730801")
        else:
            self.dnf_spring_op("VIP专享礼", "730803", dj=xinyue_info.xytype)
        self.dnf_spring_op("成为心悦礼", "730806")

        # 累计签到福利大升级
        if "20210121" <= today <= "20210127":
            self.dnf_spring_op("签到", "730822", weekDay=today)
            self.dnf_spring_op("连续签到三天", "731160")
            self.dnf_spring_op("连续签到七天", "731161")
        else:
            logger.info("签到仅限1.21到1.27，先跳过")

    def query_dnf_spring_info(self):
        springInfo = DnfSpringInfo()

        # 查询第一部分
        res = self.dnf_spring_op("输出", "731313", print_res=False)
        info = parse_amesvr_common_info(res)

        springInfo.recharge_money = int(info.sOutValue1) // 100

        springInfo.total_spoon_count = int(info.sOutValue1) // 35000
        springInfo.current_spoon_count = springInfo.total_spoon_count - int(info.sOutValue2)
        if springInfo.current_spoon_count <= 0:
            springInfo.current_spoon_count = 0

        springInfo.laojiaozi_count = int(info.sOutValue3)

        # 查询第二部分
        res = self.dnf_spring_op("输出二", "731854", print_res=False)
        info = parse_amesvr_common_info(res)

        springInfo.total_take_fudai = int(info.sOutValue1)

        return springInfo

    def check_dnf_spring(self):
        self.check_bind_account("DNF新春夺宝大作战", "https://xinyue.qq.com/act/a20210104cjhdh5/index.html",
                                activity_op_func=self.dnf_spring_op, query_bind_flowid="730793", commit_bind_flowid="730792")

    def dnf_spring_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_spring

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20210104cjhdh5/",
                                   **extra_params)

    # --------------------------------------------DNF0121新春落地页活动--------------------------------------------
    @try_except()
    def dnf_0121(self):
        # https://dnf.qq.com/cp/a20210121index/
        show_head_line("DNF0121新春落地页活动")
        self.show_amesvr_act_info(self.dnf_0121_op)

        if not self.cfg.function_switches.get_dnf_0121 or self.disable_most_activities():
            logger.warning("未启用领取DNF0121新春落地页活动功能，将跳过")
            return

        self.check_dnf_0121()

        def query_info():
            res = self.dnf_0121_op("查询用户信息", "733258", print_res=False)
            common_info = parse_amesvr_common_info(res)

            info = Dnf0121Info()
            info.sItemIds = common_info.sOutValue1.split(",")
            info.lottery_times = int(common_info.sOutValue2)
            info.hasTakeShare = common_info.sOutValue3 == "1"
            info.hasTakeBind = common_info.sOutValue4 == "1"
            info.hasTakeLogin = common_info.sOutValue5 == "1"

            return info

        info = query_info()
        if not info.hasTakeShare:
            self.dnf_0121_op("领取分享资格", "732634")
        if not info.hasTakeBind:
            self.dnf_0121_op("绑定大区领取资格", "732636")
        if not info.hasTakeLogin:
            self.dnf_0121_op("登录游戏领取资格", "732637")

        for i in range(info.lottery_times):
            self.dnf_0121_op(f"第{i + 1}次抽奖", "732593")

    def check_dnf_0121(self):
        self.check_bind_account("DNF0121新春落地页活动", "https://dnf.qq.com/cp/a20210121index/",
                                activity_op_func=self.dnf_0121_op, query_bind_flowid="732631", commit_bind_flowid="732630")

    def dnf_0121_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_0121
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210121index/",
                                   **extra_params)

    # --------------------------------------------WeGame春节活动--------------------------------------------
    @try_except()
    def wegame_spring(self):
        # https://dnf.qq.com/lbact/a20210121wegamepc/index.html
        show_head_line("WeGame春节活动")
        self.show_amesvr_act_info(self.wegame_spring_op)

        if not self.cfg.function_switches.get_wegame_spring or self.disable_most_activities():
            logger.warning("未启用领取WeGame春节活动功能，将跳过")
            return

        self.check_wegame_spring()

        def query_signin_days():
            res = self.wegame_spring_op("查询签到天数", "736307", print_res=False)
            info = parse_amesvr_common_info(res)
            # "sOutValue1": "e0c747b4b51392caf0c99162e69125d8:iRet:0|b1ecb3ecd311175835723e484f2d8d88:iRet:0",
            parts = info.sOutValue1.split('|')[0].split(':')
            days = int(parts[2])
            return days

        def query_lottery_times():
            res = self.wegame_spring_op("查询抽奖次数", "736306", print_res=False)
            info = parse_amesvr_common_info(res)
            # "sOutValue1": "239:16:4|240:8:1",
            parts = info.sOutValue1.split('|')[0].split(':')
            total, remaining = int(parts[1]), int(parts[2])
            return total, remaining

        # 阿拉德盲盒限时抽
        self.wegame_spring_op("新春盲盒抽奖-4礼包抽奖", "736265")

        # 勇士齐聚阿拉德
        self.wegame_spring_op("签到", "736263")
        logger.info(color("bold_yellow") + f"目前已累计签到{query_signin_days()}天")
        self.wegame_spring_op("签到3天礼包", "736266")
        self.wegame_spring_op("签到7天礼包", "736268")
        self.wegame_spring_op("签到15天礼包", "736270")

        self.wegame_spring_op("1.在WeGame启动DNF", "736271")
        self.wegame_spring_op("2.游戏在线30分钟", "736272")
        totalLotteryTimes, remainingLotteryTimes = query_lottery_times()
        logger.info(color("bold_yellow") + f"累计获得{totalLotteryTimes}次抽奖次数，目前剩余{remainingLotteryTimes}次抽奖次数")
        for i in range(remainingLotteryTimes):
            self.wegame_spring_op(f"每日抽奖-第{i + 1}次", "736274")

    def check_wegame_spring(self):
        self.check_bind_account("WeGame春节活动", "https://dnf.qq.com/lbact/a20210121wegamepc/index.html",
                                activity_op_func=self.wegame_spring_op, query_bind_flowid="736260", commit_bind_flowid="736259")

    def wegame_spring_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_wegame_spring
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20210121wegame/",
                                   **extra_params)

    # --------------------------------------------新春福袋大作战--------------------------------------------
    @try_except()
    def spring_fudai(self):
        # https://dnf.qq.com/cp/a20210108luckym/index.html
        show_head_line("新春福袋大作战")
        self.show_amesvr_act_info(self.spring_fudai_op)

        if not self.cfg.function_switches.get_spring_fudai or self.disable_most_activities():
            logger.warning("未启用领取新春福袋大作战功能，将跳过")
            return

        self.check_spring_fudai()

        inviter_sid = "0252c9b811d66dc1f0c9c6284b378e40"
        if is_first_run("fudai_invite"):
            msg = (
                "Hello~，可否在稍后弹出的福袋大作战活动页面点一下确认接收哇（不会损失任何东西）\n"
                "(〃'▽'〃)"
                "（本消息只会弹出一次）\n"
            )
            async_message_box(msg, "帮忙点一点", open_url=f"https://dnf.qq.com/cp/a20210108luckym/index.html?type=2&sId={inviter_sid}")

        def query_info():
            # {"sOutValue1": "1|1|0", "sOutValue2": "1", "sOutValue3": "0", "sOutValue4": "0",
            # "sOutValue5": "0252c9b811d66dc1f0c9c6284b378e40", "sOutValue6": "", "sOutValue7": "0", "sOutValue8": "4"}
            res = self.spring_fudai_op("查询各种数据", "733432", print_res=False)
            raw_info = parse_amesvr_common_info(res)
            info = SpringFuDaiInfo()

            temp = raw_info.sOutValue1.split('|')
            info.today_has_take_fudai = temp[0] == "1"
            info.fudai_count = int(raw_info.sOutValue4)
            info.has_take_bind_award = raw_info.sOutValue2 == "1"
            info.invited_ok_liushi_friends = int(raw_info.sOutValue7)
            info.has_take_share_award = temp[1] == "1"
            info.total_lottery_times = int(raw_info.sOutValue3)
            info.lottery_times = info.total_lottery_times - int(temp[2])
            info.date_info = int(raw_info.sOutValue8)

            return info

        info = query_info()

        def send_friend_invitation(typStr, flowid, dayLimit):
            if len(self.cfg.spring_fudai_receiver_qq_list) == 0:
                return

            logger.warning(color("bold_yellow") + "开启了赠送福袋功能，因此需要登录活动页面来获取p_skey，请稍候~")
            ql = QQLogin(self.common_cfg)
            if self.cfg.login_mode == "qr_login":
                # 扫码登录
                lr = ql.qr_login(login_mode=ql.login_mode_normal, name=self.cfg.name)
            else:
                # 自动登录
                lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode=ql.login_mode_normal, name=self.cfg.name)
            spring_fudai_pskey = lr.p_skey

            send_count = 0
            for sendQQ in self.cfg.spring_fudai_receiver_qq_list:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)
                res = self.spring_fudai_op(f"发送{typStr}好友邀请-{sendQQ}赠送2积分", flowid, sendQQ=sendQQ, dateInfo=str(info.date_info), p_skey=spring_fudai_pskey)

                send_count += 1
                if int(res["ret"]) != 0 or send_count >= dayLimit:
                    logger.warning(f"已达到本日邀请上限({dayLimit})，将停止邀请")
                    return

        def take_friend_awards(typStr, type, take_points_flowid):
            page = 1
            while True:
                logger.info("等待2秒，避免请求过快")
                time.sleep(2)

                queryRes = self.spring_fudai_op(f"拉取接受的{typStr}好友列表", "733413", page=str(page), type=type)
                if int(queryRes["ret"]) != 0 or queryRes["modRet"]["jData"]["iTotal"] == 0:
                    logger.warning("没有更多接收邀请的好友了，停止领取积分")
                    return

                for friend_info in queryRes["modRet"]["jData"]["jData"]:
                    takeRes = self.spring_fudai_op(f"邀请人领取{typStr}邀请{friend_info['iUin']}的积分", take_points_flowid, acceptId=friend_info["id"], needADD="2")
                    if int(takeRes["ret"]) != 0:
                        logger.warning("似乎已达到今日上限，停止领取")
                        return
                    if takeRes["modRet"]["iRet"] != 0:
                        # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "iAlertSerial": "0", "sLogSerialNum": "AMS-DNF-1230002652-mtPJXE-348890-726267"}, "modRet": {"all_item_list": [], "bHasSendFailItem": "0", "bRealSendSucc": 1, "dTimeNow": "2020-12-30 00:26:52", "iActivityId": "381537", "iDbPackageAutoIncId": 0, "iLastMpResultCode": 2037540212, "iPackageGroupId": "", "iPackageId": "", "iPackageIdCnt": "", "iPackageNum": "1", "iReentry": 0, "iRet": 100002, "iWecatCardResultCode": 0, "isCmemReEntryOpen": "yes", "jData": {"iPackageId": "0", "sPackageName": ""}, "jExtend": "", "sAmsSerialNum": "AMS-DNF-1230002652-mtPJXE-348890-726267", "sItemMsg": null, "sMidasCouponRes": "null\n", "sMidasPresentRes": "null\n", "sMsg": "非常抱歉，您此次活动领取次数已达最大，不能领取！", "sPackageCDkey": "", "sPackageLimitCheckCode": "2227289:70008,", "sPackageName": "", "sPackageRealFlag": "0", "sVersion": "V1.0.1752b92.00a0875.20201210155534"}, "ret": "0", "msg": ""}
                        logger.warning("出错了，停止领取，具体原因请看上一行的sMsg")
                        return

                page += 5

        if not info.has_take_share_award:
            self.spring_fudai_op("分享领取礼包", "733412")

        # 邀请普通玩家（福袋）
        if not info.has_take_bind_award:
            self.spring_fudai_op("绑定大区获得1次获取福袋机会", "732406")
        if not info.today_has_take_fudai:
            self.spring_fudai_op("打开一个福袋", "732405")

        self.spring_fudai_op(f"赠送好友福袋-{inviter_sid}", "733380", sId=inviter_sid)

        send_friend_invitation("普通", "732407", 8)
        take_friend_awards("普通", "1", "732550")
        self.spring_fudai_op("普通好友接受邀请", "732548", sId=inviter_sid)
        # 更新下数据
        info = query_info()
        logger.info(color("bold_yellow") + f"当前拥有{info.fudai_count}个福袋")

        # 邀请流失玩家和领奖
        self.spring_fudai_op("流失用户领取礼包", "732597")
        self.spring_fudai_op("流失好友接受邀请", "732635", sId=inviter_sid)
        for num in range(1, 6 + 1):
            self.spring_fudai_op(f"邀请人领取邀请{num}个流失用户的接受礼包", "733369", userNum=str(num))
        # 更新下数据
        info = query_info()
        logger.info(color("bold_yellow") + f"已成功邀请{info.invited_ok_liushi_friends}个流失好友")

        # 抽奖
        logger.info(color("bold_yellow") + f"当前共有{info.lottery_times}抽奖积分，历史累计获取数目为{info.total_lottery_times}抽奖积分")
        for i in range(info.lottery_times):
            self.spring_fudai_op(f"第{i + 1}次积分抽奖", "733411")

        # 签到
        self.spring_fudai_op("在线30min礼包", "732400", needADD="1")
        self.spring_fudai_op("累计3天礼包", "732404", giftId="1470919")
        self.spring_fudai_op("累计7天礼包", "732404", giftId="1470920")
        self.spring_fudai_op("累计15天礼包", "732404", giftId="1470921")

    def check_spring_fudai(self):
        self.check_bind_account("新春福袋大作战", "https://dnf.qq.com/cp/a20210108luckym/index.html",
                                activity_op_func=self.spring_fudai_op, query_bind_flowid="732399", commit_bind_flowid="732398")

    def spring_fudai_op(self, ctx, iFlowId, needADD="0", page="", type="", dateInfo="", sendQQ="", sId="", acceptId="", userNum="", giftId="", p_skey="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_spring_fudai
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210108luckym/",
                                   needADD=needADD, page=page, type=type, dateInfo=dateInfo, sendQQ=sendQQ, sId=sId, acceptId=acceptId, userNum=userNum, giftId=giftId,
                                   **extra_params,
                                   extra_cookies=f"p_skey={p_skey}")

    # --------------------------------------------DNF新春福利集合站--------------------------------------------
    @try_except()
    def spring_collection(self):
        # https://dnf.qq.com/lbact/a20210121hdhj/index.html
        show_head_line("DNF新春福利集合站")
        self.show_amesvr_act_info(self.spring_collection_op)

        if not self.cfg.function_switches.get_spring_collection or self.disable_most_activities():
            logger.warning("未启用领取DNF新春福利集合站功能，将跳过")
            return

        self.check_spring_collection()

        def query_signin_days():
            res = self.spring_collection_op("查询", "736591", print_res=False)
            info = AmesvrSigninInfo().auto_update_config(res["modRet"])
            return int(info.total)

        self.spring_collection_op("验证白名单", "736590")
        self.spring_collection_op("勇士礼包", "736585")

        self.spring_collection_op("在线30min", "736586")
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {query_signin_days()} 天")
        self.spring_collection_op("签到满3天", "736583")
        self.spring_collection_op("签到满7天", "736587")
        self.spring_collection_op("签到满15天", "736589")

    def check_spring_collection(self):
        self.check_bind_account("DNF新春福利集合站", "https://dnf.qq.com/lbact/a20210121hdhj/index.html",
                                activity_op_func=self.spring_collection_op, query_bind_flowid="736580", commit_bind_flowid="736579")

    def spring_collection_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_spring_collection
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20210121hdhj/",
                                   **extra_params)

    # --------------------------------------------燃放爆竹活动--------------------------------------------
    @try_except()
    def firecrackers(self):
        # https://dnf.qq.com/cp/a20210118rfbz/index.html
        show_head_line("燃放爆竹活动")
        self.show_amesvr_act_info(self.firecrackers_op)

        if not self.cfg.function_switches.get_firecrackers or self.disable_most_activities():
            logger.warning("未启用领取燃放爆竹活动功能，将跳过")
            return

        self.check_firecrackers()

        def query_count():
            res = self.firecrackers_op("查询剩余爆竹数", "733395", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue1)

        def today_has_invite_friend():
            res = self.firecrackers_op("查询各个任务状态", "733392", print_res=False)
            raw_info = parse_amesvr_common_info(res)
            taskStatus = raw_info.sOutValue1.split(',')

            return int(taskStatus[3]) >= 1

        @try_except(return_val_on_except=[])
        def query_invited_friends():
            res = self.firecrackers_op("查询成功邀请好友列表", "735412", print_res=False)

            invited_friends = []
            for info in res["modRet"]["jData"]["jData"]:
                invited_friends.append(info["sendToQQ"])

            return invited_friends

        friend_db_key = "friendQQs"

        def qeury_not_invited_friends_with_cache():
            account_db = load_db_for(self.cfg.name)

            invited_friends = query_invited_friends()

            def filter_not_invited_friends(friendQQs):
                validFriendQQs = []
                for friendQQ in friendQQs:
                    if friendQQ not in invited_friends:
                        validFriendQQs.append(friendQQ)

                return validFriendQQs

            if friend_db_key in account_db:
                friendQQs = account_db[friend_db_key]

                validFriendQQs = filter_not_invited_friends(friendQQs)

                if len(validFriendQQs) > 0:
                    return validFriendQQs

            return filter_not_invited_friends(qeury_not_invited_friends())

        def qeury_not_invited_friends():
            logger.info("本地无好友名单，或缓存的好友均已邀请过，需要重新拉取，请稍后~")
            friendQQs = []

            page = 1
            page_size = 4
            while True:
                info = query_friends(page, page_size)
                if len(info.list) == 0:
                    # 没有未邀请的好友了
                    break
                for friend in info.list:
                    friendQQs.append(str(friend.uin))

                page += 1

            logger.info(f"获取好友名单共计{len(friendQQs)}个，将保存到本地，具体如下：{friendQQs}")

            def _update_db(udb):
                udb[friend_db_key] = friendQQs

            update_db_for(self.cfg.name, _update_db)

            return friendQQs

        def query_friends(page, page_size):
            res = self.firecrackers_op("查询好友列表", "735262", pageNow=str(page), pageSize=str(page_size), print_res=True)
            info = AmesvrQueryFriendsInfo().auto_update_config(res["modRet"]["jData"])
            return info

        def get_one_not_invited_friend():
            friends = qeury_not_invited_friends_with_cache()
            if len(friends) == 0:
                return None

            return friends[0]

        def invite_one_friend():
            friendQQ = get_one_not_invited_friend()
            if friendQQ is None:
                logger.warning("没有更多未邀请过的好友了=、=每个好友目前限制只能邀请一次")
                return
            self.firecrackers_op(f"发送好友邀请给{friendQQ}", "735263", receiveUin=str(friendQQ))

        # 完成 分享好友 任务
        if self.cfg.enable_firecrackers_invite_friend:
            if not today_has_invite_friend():
                logger.info("尝试挑选一个未邀请过的好友进行邀请~")
                invite_one_friend()
            else:
                logger.info("今日已经邀请过好友，不必再次进行")
        else:
            logger.info("未启用燃放爆竹邀请好友功能，将跳过~")

        # 完成任务获取爆竹
        self.firecrackers_op("获取爆竹*1-今日游戏在线", "733098")
        self.firecrackers_op("获取爆竹*1-累计在线30分钟", "733125")
        self.firecrackers_op("获取爆竹*2-通关推荐副本2次", "733127")
        self.firecrackers_op("获取爆竹*1-每日分享好友", "733129")

        firecrackers_count = query_count()
        logger.info(color("bold_cyan") + f"经过上述操作，当前爆竹数目为{firecrackers_count}个")
        for i in range(firecrackers_count):
            self.firecrackers_op(f"第{i + 1}次燃放鞭炮获取积分，并等待一秒", "733132")
            time.sleep(1)

        show_end_time("2021-02-23 00:00:00")

        # 积分兑换奖励
        points = self.query_firecrackers_points()
        points_to_120_need_days = (120 - points + 4) // 5
        logger.info(color("bold_cyan") + f"当前积分为{points}，距离兑换自选灿烂所需120预计还需要{points_to_120_need_days}天")

        if len(self.cfg.firecrackers.exchange_items) != 0:
            logger.info("将尝试按照配置的优先级兑换奖励")
            for ei in self.cfg.firecrackers.exchange_items:
                res = self.firecrackers_op(f"道具兑换-{ei.need_points}积分-{ei.name}", "733133", index=str(ei.index))
                if res["ret"] == "700" and res["flowRet"]["iCondNotMetId"] == "1432184":
                    logger.warning("当前奖励积分不够，将跳过后续奖励")
                    break
        else:
            logger.info("当前未配置兑换道具，请根据需要自行配置需要兑换的道具列表")

        # 积分抽奖
        if self.cfg.firecrackers.enable_lottery:
            points = self.query_firecrackers_points()
            logger.info(color("bold_cyan") + f"当前积分为{points}，将进行{points // 2}次抽奖")
            for i in range(points // 2):
                self.firecrackers_op(f"第{i + 1}次积分抽奖，并等待五秒", "733134")
                time.sleep(5)
        else:
            logger.info(color("bold_green") + "如果已经兑换完所有奖励，建议开启使用积分抽奖功能")

    @try_except(return_val_on_except=0)
    def query_firecrackers_points(self):
        res = self.firecrackers_op("查询剩余积分数", "733396", print_res=False)
        raw_info = parse_amesvr_common_info(res)

        return int(raw_info.sOutValue1)

    def check_firecrackers(self):
        self.check_bind_account("燃放爆竹活动", "https://dnf.qq.com/cp/a20210118rfbz/index.html",
                                activity_op_func=self.firecrackers_op, query_bind_flowid="733400", commit_bind_flowid="733399")

    def firecrackers_op(self, ctx, iFlowId, index="", pageNow="", pageSize="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_firecrackers
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210118rfbz/",
                                   index=index, pageNow=pageNow, pageSize=pageSize,
                                   **extra_params)

    # --------------------------------------------辅助函数--------------------------------------------
    def get(self, ctx, url, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True, extra_cookies="", **params):
        return self.network.get(ctx, self.format(url, **params), pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote, extra_cookies)

    def post(self, ctx, url, data, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True, extra_cookies="", **params):
        return self.network.post(ctx, self.format(url, **params), data, pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote, extra_cookies)

    def format(self, url, **params):
        endTime = datetime.datetime.now()
        startTime = endTime - datetime.timedelta(days=int(365 / 12 * 5))
        date = get_today()

        # 有值的默认值
        default_valued_params = {
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
            "date": date,
        }

        # 无值的默认值
        default_empty_params = {key: "" for key in [
            "package_id", "lqlevel", "teamid",
            "weekDay",
            "sArea", "serverId", "areaId", "nickName", "sRoleId", "sRoleName", "uin", "skey", "userId", "token",
            "iActionId", "iGoodsId", "sBizCode", "partition", "iZoneId", "platid", "sZoneDesc", "sGetterDream",
            "dzid",
            "page",
            "iPackageId",
            "isLock", "amsid", "iLbSel1", "num", "mold", "exNum", "iCard", "iNum", "actionId",
            "plat", "extraStr",
            "sContent", "sPartition", "sAreaName", "md5str", "ams_checkparam", "checkparam",
            "type", "moduleId", "giftId", "acceptId", "sendQQ",
            "cardType", "giftNum", "inviteId", "inviterName", "sendName", "invitee", "receiveUin", "receiver", "receiverName", "receiverUrl",
            "user_area", "user_partition", "user_areaName", "user_roleId", "user_roleName",
            "user_roleLevel", "user_checkparam", "user_md5str", "user_sex", "user_platId",
            "cz", "dj",
            "siActivityId",
            "needADD", "dateInfo", "sId", "userNum",
            "index",
            "pageNow", "pageSize",
            "clickTime",
            "skin_id", "decoration_id", "adLevel", "adPower",
            "username", "petId"
        ]}

        # 整合得到所有默认值
        default_params = {**default_valued_params, **default_empty_params}

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
        return f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}"

    def show_amesvr_act_info(self, activity_op_func):
        activity_op_func("查询活动信息", "", show_info_only=True)

    def amesvr_request(self, ctx, amesvr_host, sServiceDepartment, sServiceType, iActivityId, iFlowId, print_res, eas_url, extra_cookies="", show_info_only=False, **data_extra_params):
        if show_info_only:
            self.show_ams_act_info(iActivityId)
            return

        data = self.format(self.urls.amesvr_raw_data,
                           sServiceDepartment=sServiceDepartment, sServiceType=sServiceType, eas_url=quote_plus(eas_url),
                           iActivityId=iActivityId, iFlowId=iFlowId, **data_extra_params)

        return self.post(ctx, self.urls.amesvr, data,
                         amesvr_host=amesvr_host, sServiceDepartment=sServiceDepartment, sServiceType=sServiceType,
                         iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
                         print_res=print_res, extra_cookies=extra_cookies)

    def show_ams_act_info(self, iActivityId):
        logger.info(color("bold_green") + get_ams_act_desc(iActivityId))

    def show_not_ams_act_info(self, act_name):
        logger.info(color("bold_green") + get_not_ams_act_desc(act_name))

    def make_s_milo_tag(self, iActivityId, iFlowId):
        return f"AMS-MILO-{iActivityId}-{iFlowId}-{self.cfg.account_info.uin}-{getMillSecondsUnix()}-{self.rand6()}"

    def rand6(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=6))

    def make_cookie(self, map: dict):
        return '; '.join([f'{k}={v}' for k, v in map.items()])

    def check_bind_account(self, activity_name, activity_url, activity_op_func, query_bind_flowid, commit_bind_flowid, try_auto_bind=True):
        while True:
            res = activity_op_func(f"查询是否绑定-尝试自动({try_auto_bind})", query_bind_flowid, print_res=False)
            # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
            if len(res["modRet"]["jData"]) == 0:
                self.guide_to_bind_account(activity_name, activity_url, activity_op_func=activity_op_func,
                                           query_bind_flowid=query_bind_flowid, commit_bind_flowid=commit_bind_flowid, try_auto_bind=try_auto_bind)
            else:
                # 已经绑定
                break

    def guide_to_bind_account(self, activity_name, activity_url, activity_op_func=None, query_bind_flowid="", commit_bind_flowid="", try_auto_bind=False):
        if try_auto_bind and self.common_cfg.try_auto_bind_new_activity and activity_op_func is not None and commit_bind_flowid != "":
            if 'dnf' in self.bizcode_2_bind_role_map:
                # 若道聚城已绑定dnf角色，则尝试绑定这个角色
                roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
                checkInfo = self.get_dnf_roleinfo()

                def double_quote(strToQuote):
                    return quote_plus(quote_plus(strToQuote))

                logger.warning(color("bold_yellow") + f"活动【{activity_name}】未绑定角色，当前配置为自动绑定模式，将尝试绑定为道聚城所绑定的角色({roleinfo.serviceName}-{roleinfo.roleName})")
                activity_op_func("提交绑定大区", commit_bind_flowid, True,
                                 user_area=roleinfo.serviceID, user_partition=roleinfo.serviceID, user_areaName=double_quote(roleinfo.serviceName),
                                 user_roleId=roleinfo.roleCode, user_roleName=double_quote(roleinfo.roleName), user_roleLevel="100",
                                 user_checkparam=double_quote(checkInfo.checkparam), user_md5str=checkInfo.md5str, user_sex="", user_platId="")
            else:
                logger.warning(color("bold_yellow") + f"活动【{activity_name}】未绑定角色，当前配置为自动绑定模式，但道聚城未绑定角色，因此无法应用自动绑定，将使用手动绑定方案")

            # 绑定完毕，再次检测，这次如果检测仍未绑定，则不再尝试自动绑定
            self.check_bind_account(activity_name, activity_url, activity_op_func, query_bind_flowid, commit_bind_flowid, try_auto_bind=False)
        else:
            msg = (
                f"当前账号【{self.cfg.name}】未在活动页面绑定角色，且未开启自动绑定模式，请点击右下角的【确定】按钮后，在自动弹出的【{activity_name}】活动页面进行绑定，然后按任意键继续\n"
                "若无需该功能，可关闭工具，然后前往配置文件自行关闭该功能\n"
                "若默认浏览器打不开该页面，请自行在手机或其他浏览器打开下面的页面\n"
                f"{activity_url}\n"
            )
            logger.warning(color("bold_cyan") + msg)
            win32api.MessageBox(0, msg, "需绑定账号", win32con.MB_ICONWARNING)
            webbrowser.open(activity_url)
            logger.info(color("bold_yellow") + "请在完成绑定后按任意键继续")
            os.system("PAUSE")

    def disable_most_activities(self):
        return self.cfg.function_switches.disable_most_activities

    def get_dnf_roleinfo(self):
        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo

        res = self.get("查询角色信息", self.urls.get_game_role_list, game="dnf", area=roleinfo.serviceID, sAMSTargetAppId="", platid="", partition="", print_res=False, is_jsonp=True, need_unquote=False)
        return AmesvrQueryRole().auto_update_config(res)


def watch_live():
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    RunAll = True
    indexes = [1]
    if RunAll:
        indexes = [i + 1 for i in range(len(cfg.account_configs))]

    totalTime = 2 * 60 + 5  # 为了保险起见，多执行5分钟
    logger.info(f"totalTime={totalTime}")

    for t in range(totalTime):
        timeStart = datetime.datetime.now()
        logger.info(color("bold_yellow") + f"开始执行第{t + 1}分钟的流程")
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
            logger.info(color("bold_cyan") + f"本轮累积用时{totalUsed}秒，将休息{waitTime}秒")
            time.sleep(waitTime)


if __name__ == '__main__':
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    RunAll = True
    indexes = [1]
    if RunAll:
        indexes = [i + 1 for i in range(len(cfg.account_configs))]

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]

        show_head_line(f"预先获取第{idx}个账户[{account_config.name}]的skey", color("fg_bold_yellow"))

        if not account_config.is_enabled():
            logger.warning("账号被禁用，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]

        show_head_line(f"开始处理第{idx}个账户[{account_config.name}]", color("fg_bold_yellow"))

        if not account_config.is_enabled():
            logger.warning("账号被禁用，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)

        # from main_def import get_user_buy_info, show_buy_info
        #
        # user_buy_info = get_user_buy_info(cfg)
        # show_buy_info(user_buy_info)
        # djcHelper.run(user_buy_info)

        djcHelper.fetch_pskey()
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
        # djcHelper.hello_voice()
        # djcHelper.dnf_carnival()
        # djcHelper.xinyue_financing()
        # djcHelper.dnf_carnival_live()
        # djcHelper.dnf_dianzan()
        # djcHelper.dnf_drift()
        # djcHelper.dnf_shanguang()
        # djcHelper.warm_winter()
        # djcHelper.dnf_1224()
        # djcHelper.youfei()
        # djcHelper.dnf_bbs_signin()
        # djcHelper.ark_lottery()
        # djcHelper.dnf_spring()
        # djcHelper.dnf_0121()
        # djcHelper.wegame_spring()
        # djcHelper.dnf_welfare()
        # djcHelper.spring_fudai()
        # djcHelper.spring_collection()
        # djcHelper.firecrackers()
        # djcHelper.vip_mentor()
        # djcHelper.qq_video()
        # djcHelper.dnf_helper()
        # djcHelper.xinyue_weekly_gift()
        # djcHelper.dnf_helper_chronicle()
        # djcHelper.xinyue_cat()
        # djcHelper.guanjia()
        djcHelper.majieluo()
