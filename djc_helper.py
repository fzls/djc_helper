import string
from multiprocessing import Pool
from urllib.parse import quote_plus

import pyperclip

import json_parser
from black_list import check_in_black_list
from dao import *
from first_run import *
from game_info import get_game_info, get_game_info_by_bizcode
from network import *
from qq_login import QQLogin, LoginResult, GithubActionLoginException
from qzone_activity import QzoneActivity
from setting import *
from sign import getMillSecondsUnix
from urls import Urls, get_ams_act_desc, get_not_ams_act_desc, get_not_ams_act, search_act, not_know_end_time, not_know_start_time, get_ams_act


# DNF蚊子腿小助手
class DjcHelper:
    local_saved_skey_file = os.path.join(cached_dir, ".saved_skey.{}.json")
    local_saved_pskey_file = os.path.join(cached_dir, ".saved_pskey.{}.json")
    local_saved_guanjia_openid_file = os.path.join(cached_dir, ".saved_guanjia_openid.{}.json")

    local_saved_teamid_file = os.path.join(cached_dir, ".teamid_new.{}.json")

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
        self.network = Network(self.cfg.sDeviceID, self.uin(), self.cfg.account_info.skey, self.common_cfg)

    def check_skey_expired(self, window_index=1):
        query_data = self.query_balance("判断skey是否过期", print_res=False)
        if str(query_data['ret']) == "0":
            # skey尚未过期，则重新刷一遍，主要用于从qq空间获取的情况
            account_info = self.cfg.account_info
            self.save_uin_skey(account_info.uin, account_info.skey, self.vuserid)
        else:
            # 已过期，更新skey
            logger.info("")
            logger.warning(f"账号({self.cfg.name})的skey已过期，即将尝试更新skey")
            self.update_skey(query_data, window_index=window_index)

        # skey获取完毕后，检查是否在黑名单内
        check_in_black_list(self.uin())

    def update_skey(self, query_data, window_index=1):
        login_mode_dict = {
            "by_hand": self.update_skey_by_hand,
            "qr_login": self.update_skey_qr_login,
            "auto_login": self.update_skey_auto_login,
        }  # type: Dict[str, Callable[[Dict, int], None]]
        login_mode_dict[self.cfg.login_mode](query_data, window_index)

    def update_skey_by_hand(self, query_data, window_index=1):
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

    def update_skey_qr_login(self, query_data, window_index=1):
        qqLogin = QQLogin(self.common_cfg, window_index=window_index)
        loginResult = qqLogin.qr_login(name=self.cfg.name)
        self.save_uin_skey(loginResult.uin, loginResult.skey, loginResult.vuserid)

    def update_skey_auto_login(self, query_data, window_index=1):
        qqLogin = QQLogin(self.common_cfg, window_index=window_index)
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

    # 预处理阶段
    def check_djc_role_binding(self) -> bool:
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
                logger.warning(color("fg_bold_green") + "如果不需要做道聚城的手游任务和许愿任务（不做会少豆子），可以在配置工具里将手游名称设为无")
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

        # 运行活动
        activity_funcs_to_run = self.get_activity_funcs_to_run(user_buy_info)

        for act_name, activity_func in activity_funcs_to_run:
            activity_func()

        # # 以下为并行执行各个活动的调用方式
        # # 由于下列原因，该方式基本确定不会再使用
        # # 1. amesvr活动服务器会限制调用频率，如果短时间内请求过快，会返回401，并提示请求过快
        # #    而多进程处理活动的时候，会非常频繁的触发这种情况，感觉收益不大。另外频繁触发这个警报，感觉也有可能会被腾讯风控，到时候就得不偿失了
        # # 2. python的multiprocessing.pool.Pool不支持在子进程中再创建新的子进程
        # #    因此在不同账号已经在不同的进程下运行的前提下，子进程下不能再创建新的子进程了
        # async_run_all_act(self.cfg, self.common_cfg, activity_funcs_to_run)

    def get_activity_funcs_to_run(self, user_buy_info: BuyInfo) -> List[Tuple[str, Callable]]:
        activity_funcs_to_run = []
        activity_funcs_to_run.extend(self.free_activities())
        if user_buy_info.is_active():
            # 付费期间将付费活动也加入到执行列表中
            activity_funcs_to_run.extend(self.payed_activities())

        return activity_funcs_to_run

    def show_activities_summary(self, user_buy_info: BuyInfo):
        # 需要运行的活动
        free_activities = self.free_activities()
        paied_activities = self.payed_activities()

        # 展示活动的信息
        def get_activities_summary(categray: str, activities: list) -> str:
            activities_summary = ""
            if len(activities) != 0:
                activities_summary += f"\n目前的{categray}活动如下："
                for idx, name_and_func in enumerate(activities):
                    act_name, act_func = name_and_func

                    op_func_name = act_func.__name__ + '_op'

                    start_time = not_know_start_time
                    end_time = not_know_end_time
                    # 可能是非ams活动
                    act_info = get_not_ams_act(act_name)
                    if act_info is None and hasattr(self, op_func_name):
                        # 可能是ams活动
                        act_info = getattr(self, op_func_name)("获取活动信息", "", get_ams_act_info_only=True)

                    line_color = "bold_green"
                    if act_info is not None:
                        start_time = format_time(parse_time(act_info.dtBeginTime), "%Y-%m-%d")
                        end_time = format_time(parse_time(act_info.dtEndTime), "%Y-%m-%d")
                        if is_act_expired(act_info.dtEndTime):
                            line_color = "bold_black"

                    activities_summary += with_color(line_color, f'\n    {idx + 1:2d}. {start_time} {end_time} {act_name}')
            else:
                activities_summary += f"\n目前尚无{categray}活动，当新的{categray}活动出现时会及时加入~"

            return activities_summary

        # 免费活动信息
        free_activities_summary = get_activities_summary("长期免费", free_activities)
        show_head_line("以下为免费的长期活动", msg_color=color("bold_cyan"))
        logger.info(free_activities_summary)

        # 付费活动信息
        paied_activities_summary = get_activities_summary("短期付费", paied_activities)
        show_head_line("以下为付费期间才会运行的短期活动", msg_color=color("bold_cyan"))

        if not user_buy_info.is_active():
            if user_buy_info.total_buy_month != 0:
                msg = f"账号{user_buy_info.qq}的付费内容已到期，到期时间点为{user_buy_info.expire_at}。"
            else:
                msg = f"账号{user_buy_info.qq}未购买付费内容。"
            msg += "\n因此2021-02-06之后添加的短期新活动将被跳过，如果想要启用该部分内容，可查看目录中的【付费指引.docx】，目前定价为5元每月。"
            msg += "\n2021-02-06之前添加的所有活动不受影响，仍可继续使用。"
            msg += "\n具体受影响的活动内容如下"

            logger.warning(color("bold_yellow") + msg)

        logger.info(paied_activities_summary)

    def free_activities(self) -> List[Tuple[str, Callable]]:
        return [
            ("道聚城", self.djc_operations),
            ("DNF地下城与勇士心悦特权专区", self.xinyue_battle_ground),
            ("心悦app", self.xinyue_app_operations),
            ("黑钻礼包", self.get_heizuan_gift),
            ("腾讯游戏信用礼包", self.get_credit_xinyue_gift),
            ("心悦app理财礼卡", self.xinyue_financing),
            ("心悦猫咪", self.xinyue_cat),
            ("心悦app周礼包", self.xinyue_weekly_gift),
            ("dnf论坛签到", self.dnf_bbs),
        ]

    def payed_activities(self) -> List[Tuple[str, Callable]]:
        # re: 更新新的活动时记得更新urls.py的not_ams_activities
        return [
            ("DNF助手编年史", self.dnf_helper_chronicle),
            ("hello语音网页礼包兑换", self.hello_voice),
            ("DNF格斗大赛", self.dnf_pk),
            ("集卡", self.ark_lottery),
            ("DNF集合站", self.dnf_collection),
            ("DNF福利中心兑换", self.dnf_welfare),
            ("DNF漫画预约活动", self.dnf_comic),
            ("DNF落地页活动", self.dnf_luodiye),
            ("我的dnf13周年活动", self.dnf_my_story),
            ("刃影预约活动", self.dnf_reserve),
            ("DNF奥兹玛竞速", self.dnf_ozma),
            ("管家蚊子腿", self.guanjia_new),
            ("WeGame活动周年庆", self.dnf_wegame_dup),
            ("DNF集合站周年庆", self.dnf_collection_dup),
            ("DNF马杰洛的规划", self.majieluo),
            ("colg每日签到", self.colg_signin),
            ("KOL", self.dnf_kol),
            ("超级会员", self.dnf_super_vip),
            ("黄钻", self.dnf_yellow_diamond),
            ("qq视频蚊子腿", self.qq_video),
            ("WeGame活动", self.dnf_wegame),
        ]

    def expired_activities(self) -> List[Tuple[str, Callable]]:
        return [
            ("wegame国庆活动【秋风送爽关怀常伴】", self.wegame_guoqing),
            ("微信签到", self.wx_checkin),
            ("10月女法师三觉", self.dnf_female_mage_awaken),
            ("dnf助手排行榜", self.dnf_rank),
            ("2020DNF嘉年华页面主页面签到", self.dnf_carnival),
            ("DNF进击吧赛利亚", self.xinyue_sailiyam),
            ("阿拉德勇士征集令", self.dnf_warriors_call),
            ("dnf漂流瓶", self.dnf_drift),
            ("暖冬好礼活动", self.warm_winter),
            ("DNF共创投票", self.dnf_dianzan),
            ("史诗之路来袭活动合集", self.dnf_1224),
            ("DNF闪光杯第三期", self.dnf_shanguang),
            ("新春福袋大作战", self.spring_fudai),
            ("燃放爆竹活动", self.firecrackers),
            ("DNF福签大作战", self.dnf_fuqian),
            ("会员关怀", self.vip_mentor),
            ("DNF强者之路", self.dnf_strong),
            ("DNF心悦51", self.dnf_xinyue_51),
            ("dnf助手活动", self.dnf_helper),
            ("管家蚊子腿", self.guanjia),
            ("DNF十三周年庆活动", self.dnf_13),
            ("DNF周年庆登录活动", self.dnf_anniversary),
            ("qq视频-AME活动", self.qq_video_amesvr),
        ]

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
        wish_list_res = self.get("3.3.1 查询许愿列表", self.urls.query_wish, appUid=self.qq())

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

    def query_all_extra_info(self, dnfServerId: str):
        """
        已废弃，不再需要手动查询该信息
        """
        # 获取玩家的dnf角色列表
        self.query_dnf_rolelist(dnfServerId)
        # 获取玩家的手游角色列表
        self.query_mobile_game_rolelist()

        # # 显示所有可以兑换的道具列表，note：当不知道id时调用
        # self.query_dnf_gifts()

    def query_dnf_rolelist(self, dnfServerId: str, need_print=True) -> List[DnfRoleInfo]:
        ctx = f"获取账号({self.cfg.name})在服务器({dnf_server_id_to_name(dnfServerId)})的dnf角色列表"
        game_info = get_game_info("地下城与勇士")
        roleListJsonRes = self.get(ctx, self.urls.get_game_role_list, game=game_info.gameCode, sAMSTargetAppId=game_info.wxAppid, area=dnfServerId, platid="", partition="", is_jsonp=True, print_res=False)
        roleLists = json_parser.parse_role_list(roleListJsonRes)

        if need_print:
            lines = []
            lines.append("")
            lines.append("+" * 40)
            lines.append(ctx)
            if len(roleLists) != 0:
                for idx, role in enumerate(roleLists):
                    formatted_force_name = padLeftRight(role.get_force_name(), 10, mode='left')
                    formatted_role_name = padLeftRight(role.rolename, 26, mode='left')
                    lines.append(f"\t第{idx + 1:2d}个角色信息：\tid = {role.roleid:10s} \t名字 = {formatted_role_name} \t职业 = {formatted_force_name} \t等级 = {role.level:3d}")
            else:
                lines.append(f"\t未查到dnf服务器id={dnfServerId}上的角色信息，请确认服务器id已填写正确或者在对应区服已创建角色")
                lines.append("\t区服id可查看稍后打开的reference_data/dnf_server_list.js，详情参见config.toml的对应注释")
                lines.append("\t区服(partition)的id可运行程序在自动打开的reference_data/dnf_server_list或手动打开这个文件， 查看 STD_DATA中对应区服的v")
                subprocess.Popen("npp_portable/notepad++.exe reference_data/dnf_server_list.js")
            lines.append("+" * 40)
            logger.info("\n".join(lines))

        return roleLists

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
        res = requests.get(self.urls.query_game_server_list.format(bizcode=game_info.bizCode), timeout=10)
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
    def xinyue_battle_ground(self):
        """
        https://xinyue.qq.com/act/a20210317dnf/index_pc.html
        根据配置进行心悦相关操作
        具体活动信息可以查阅reference_data/心悦活动备注.txt
        """
        show_head_line("DNF地下城与勇士心悦特权专区")
        self.show_amesvr_act_info(self.xinyue_battle_ground_op)

        if not self.cfg.function_switches.get_xinyue:
            logger.warning("未启用领取心悦特权专区功能，将跳过")
            return

        self.check_xinyue_battle_ground()

        # self.xinyue_battle_ground_op("周期获奖记录", "747508")
        # self.xinyue_battle_ground_op("花园获奖记录", "747563")
        # self.xinyue_battle_ground_op("充值获奖记录", "747719")

        # 查询成就点信息
        old_info = self.query_xinyue_info("6.1 操作前查询成就点信息")

        default_xinyue_operations = [
            ("747791", "回流礼"),
        ]

        # 尝试根据心悦级别领取对应周期礼包
        if old_info.xytype < 5:
            default_xinyue_operations.extend([
                ("747507", "周礼包_特邀会员"),
                ("747539", "月礼包_特邀会员"),
            ])
        else:
            default_xinyue_operations.extend([
                ("747534", "周礼包_心悦会员"),
                ("747541", "月礼包_心悦会员"),
            ])

        xinyue_operations = []
        op_set = set()

        def try_add_op(op: XinYueOperationConfig):
            op_key = f"{op.iFlowId} {op.sFlowName}"
            if op_key in op_set:
                return

            xinyue_operations.append(op)
            op_set.add(op_key)

        for gift in default_xinyue_operations:
            op = XinYueOperationConfig()
            op.iFlowId, op.sFlowName = gift
            op.count = 1
            try_add_op(op)

        # 与配置文件中配置的去重后叠加
        for op in self.cfg.xinyue_operations:
            try_add_op(op)

        # 进行相应的心悦操作
        for op in xinyue_operations:
            self.do_xinyue_op(old_info.xytype, op)

        # ------------ 赛利亚打工 -----------------
        info = self.query_xinyue_info("查询打工信息", print_res=False)
        # 可能的状态如下
        # 工作状态 描述 结束时间 领取结束时间 可进行操作
        #    -2   待机    0                  可打工（若本周总次数未用完），之后状态变为2
        #    2    打工中  a         b        在结束时间a之前，不能进行任何操作，a之后状态变为1
        #    1    领工资  a         b        在结束时间b之前，可以领取奖励。领取后状态变为-2
        if info.work_status == -2:
            self.xinyue_battle_ground_op("打工仔去打工", "748050")
        elif info.work_status == 2:
            logger.info(color("bold_green") + f"赛利亚正在打工中~ 结束时间为{datetime.datetime.fromtimestamp(info.work_end_time)}")
        elif info.work_status == 1:
            self.xinyue_battle_ground_op("搬砖人领工资", "748077")
            self.xinyue_battle_ground_op("打工仔去打工", "748050")

        # 然后尝试抽奖
        info = self.query_xinyue_info("查询抽奖次数", print_res=False)
        logger.info(color("bold_yellow") + f"当前剩余抽奖次数为 {info.ticket}")
        for idx in range(info.ticket):
            self.xinyue_battle_ground_op(f"第{idx + 1}次抽奖券抽奖", "749081")

        # 再次查询成就点信息，展示本次操作得到的数目
        new_info = self.query_xinyue_info("6.3 操作完成后查询成就点信息")
        delta = new_info.score - old_info.score
        logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 本次心悦相关操作共获得 {delta} 个成就点（ {old_info.score} -> {new_info.score} ）")
        logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 当前是 {new_info.xytype_str} , 最新勇士币数目为 {new_info.ysb}")

        # 查询下心悦组队进度
        teaminfo = self.query_xinyue_teaminfo()
        if teaminfo.id != "":
            logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 当前队伍奖励概览 {teaminfo.award_summary}")
        else:
            logger.warning(color("fg_bold_yellow") + f"账号 {self.cfg.name} 当前尚无有效心悦队伍，可考虑加入或查看文档使用本地心悦组队功能")

    def do_xinyue_op(self, xytype, op):
        """
        执行具体的心悦操作
        :type op: XinYueOperationConfig
        """
        retryCfg = self.common_cfg.retry
        # 最少等待5秒
        wait_time = max(retryCfg.request_wait_time, 5)
        now = datetime.datetime.now()
        current_hour = now.hour
        for i in range(op.count):
            ctx = f"6.2 心悦操作： {op.sFlowName}({i + 1}/{op.count})"

            for try_index in range(retryCfg.max_retry_count):
                res = self.xinyue_battle_ground_op(ctx, op.iFlowId, package_id=op.package_id, lqlevel=xytype)
                # if int(res.get('ret', '0')) == -9905:
                #     logger.warning(f"兑换 {op.sGoodsName} 时提示 {res.get('msg')} ，等待{retryCfg.retry_wait_time}s后重试（{try_index + 1}/{retryCfg.max_retry_count})")
                #     time.sleep(retryCfg.retry_wait_time)
                #     continue

                logger.debug(f"心悦操作 {op.sFlowName} ok，等待{wait_time}s，避免请求过快报错")
                time.sleep(wait_time)
                break

    @try_except(show_exception_info=False)
    def try_join_fixed_xinyue_team(self):
        # 检查是否有固定队伍
        fixed_team = self.get_fixed_team()

        if fixed_team is None:
            logger.warning("未找到本地固定队伍信息，跳过队伍相关流程")
            return

        logger.info(f"当前账号的本地固定队信息为{fixed_team}")

        self.check_xinyue_battle_ground()

        teaminfo = self.query_xinyue_teaminfo(print_res=True)
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
        qq_number = self.qq()
        fixed_team = None
        for team in self.common_cfg.fixed_teams:
            if not team.enable:
                continue
            if qq_number not in team.members:
                continue
            if not team.check():
                logger.warning(f"本地固定队伍={team.id}的队伍成员({team.members})不符合要求，请确保是两个有效的qq号")
                continue

            fixed_team = team
            break

        return fixed_team

    @try_except(return_val_on_except=XinYueTeamInfo(), show_exception_info=False)
    def query_xinyue_teaminfo(self, print_res=False):
        data = self.xinyue_battle_ground_op("查询我的心悦队伍信息", "748075", print_res=print_res)
        jdata = data["modRet"]["jData"]

        return self.parse_teaminfo(jdata)

    def query_xinyue_teaminfo_by_id(self, remote_teamid):
        # 748071	传入小队ID查询队伍信息
        data = self.xinyue_battle_ground_op("查询特定id的心悦队伍信息", "748071", teamid=remote_teamid)
        jdata = data["modRet"]["jData"]
        teaminfo = self.parse_teaminfo(jdata)
        return teaminfo

    def join_xinyue_team(self, remote_teamid):
        # 748069	加入小队
        data = self.xinyue_battle_ground_op("尝试加入小队", "748069", teamid=remote_teamid)
        if int(data["flowRet"]["iRet"]) == 700:
            # 小队已经解散
            return None

        return self.query_xinyue_teaminfo()

    def create_xinyue_team(self):
        # 748052	创建小队
        data = self.xinyue_battle_ground_op("尝试创建小队", "748052")

        return self.query_xinyue_teaminfo()

    def parse_teaminfo(self, jdata):
        teamInfo = XinYueTeamInfo()
        teamInfo.result = jdata["result"]
        if teamInfo.result == 0:
            teamInfo.ttl_time = jdata.get("ttl_time", 0)
            teamInfo.id = jdata.get("code", "")  # 根据code查询时从这获取

            # 解析队伍信息
            team_list = jdata["team_list"]
            for member_json_str in jdata["team_list"]:
                member = XinYueTeamMember().auto_update_config(json.loads(member_json_str))
                teamInfo.members.append(member)
                if member.code != "":
                    teamInfo.id = member.code  # 而查询自己的队伍信息时，则需要从队员信息中获取

            # 解析奖励状态
            awardIdToName = {
                "2373983": "大",  # 20
                "2373988": "中",  # 15
                "2373987": "小",  # 10
            }

            award_summarys = []
            for member in teamInfo.members:
                # 尚未有奖励时将会是false
                if member.pak == "" or member.pak == False:
                    continue

                award_names = []

                pak_list = member.pak.split("|")
                for pak in pak_list:
                    award_id, idx = pak.split('_')
                    award_name = awardIdToName[award_id]

                    award_names.append(award_name)

                award_summarys.append(''.join(award_names))
            teamInfo.award_summary = '|'.join(award_summarys)

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

    @try_except(return_val_on_except=XinYueInfo())
    def query_xinyue_info(self, ctx, print_res=True):
        res = self.xinyue_battle_ground_op(ctx, "748082", print_res=print_res)
        raw_info = parse_amesvr_common_info(res)

        info = XinYueInfo()
        info.xytype = int(raw_info.sOutValue1)
        if info.xytype < 5:
            info.xytype_str = f"游戏家G{info.xytype}"
        else:
            info.xytype_str = f"心悦VIP{info.xytype - 4}"
        info.is_special_member = int(raw_info.sOutValue2) == 1
        info.ysb, info.score, info.ticket = [int(val) for val in raw_info.sOutValue3.split('|')]
        info.username, info.usericon = raw_info.sOutValue4.split('|')
        info.username = unquote_plus(info.username)
        info.login_qq = raw_info.sOutValue5
        info.work_status = int(raw_info.sOutValue6 or "0")
        info.work_end_time = int(raw_info.sOutValue7 or "0")
        info.take_award_end_time = int(raw_info.sOutValue8 or "0")

        return info

    def check_xinyue_battle_ground(self):
        self.check_bind_account("心悦战场", "https://xinyue.qq.com/act/a20210317dnf/index_pc.html",
                                activity_op_func=self.xinyue_battle_ground_op, query_bind_flowid="748044", commit_bind_flowid="748043")

    def xinyue_battle_ground_op(self, ctx, iFlowId, package_id="", print_res=True, lqlevel=1, teamid="", **extra_params):
        return self.xinyue_op(ctx, self.urls.iActivityId_xinyue_battle_ground, iFlowId, package_id, print_res, lqlevel, teamid, **extra_params)

    def xinyue_op(self, ctx, iActivityId, iFlowId, package_id="", print_res=True, lqlevel=1, teamid="", **extra_params):
        # 网站上特邀会员不论是游戏家G几，调用doAction(flowId,level)时level一律传1，而心悦会员则传入实际的567对应心悦123
        if lqlevel < 5:
            lqlevel = 1

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "xinyue", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20181101rights/",
                                   package_id=package_id, lqlevel=lqlevel, teamid=teamid,
                                   **extra_params)

    # --------------------------------------------心悦app--------------------------------------------
    @try_except()
    def xinyue_app_operations(self):
        """
        根据配置进行心悦app相关操作
        """
        show_head_line("心悦app")
        self.show_not_ams_act_info("心悦app")

        if not self.cfg.function_switches.get_xinyue_app:
            logger.warning("未启用领取心悦app功能，将跳过")
            return

        if len(self.cfg.xinyue_app_operations) == 0:
            logger.warning("未配置心悦app相关操作，将跳过。如需使用，请打开config.toml.example搜索 心悦app相关操作 查看示例配置和说明，然后手动填写到config.toml中对应位置(如果搞不来，就请手动操作~)")
            return

        lr = self.fetch_xinyue_login_info("心悦app")
        access_token = lr.xinyue_access_token
        openid = lr.openid
        if access_token == "" or openid == "":
            logger.warning(f"心悦app的票据未能成功获取。access_token={access_token}, openid={openid}")
            return

        # 请求体目前看来每次请求包可以保持一致
        # note：获取方式，抓包获取http body。如fiddler，抓包，找到对应请求（body大小为150的请求），右侧点Inspector/HexView，选中Http Body部分的字节码（未标蓝部分），右击Copy/Copy as 0x##，然后粘贴出来，将其中的bytes复制到下列对应数组位置

        url = "https://a.xinyue.qq.com/"
        headers = {
            "Cookie": f"xyapp_login_type=qc;access_token={access_token};openid={openid};appid=101484782",
            "Accept": "application/json",
            "Referer": "http://apps.game.qq.com/php/tgclub/v2/",
            "User-Agent": "tgclub/5.7.6.81(Xiaomi MIX 2;android 9;Scale/440;android;865737030437124)",
            "Charset": "UTF-8",
            "Accept-Language": "zh-Hans-US;q=1,en-US;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        for op in self.cfg.xinyue_app_operations:
            res = requests.post(url, bytes(op.encrypted_raw_http_body), headers=headers, timeout=10)
            logger.info(f"心悦app操作：{op.name} 返回码={res.status_code}, 请求结果={res.content}")

        logger.info(color("bold_yellow") + f"当前心悦app相关操作处于测试阶段，请前往心悦app自行确认是否兑换成功~")

    # DNF进击吧赛利亚
    def xinyue_sailiyam(self):
        # https://xinyue.qq.com/act/a20201023sailiya/index.html
        show_head_line("DNF进击吧赛利亚")
        self.show_amesvr_act_info(self.xinyue_sailiyam_op)

        def sleep_to_avoid_ban():
            logger.info("等待五秒，防止提示操作太快")
            time.sleep(5)

        for dzid in self.common_cfg.sailiyam_visit_target_qqs:
            if dzid == self.qq():
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
        #   1.2 填写新链接   在 urls.py 中，替换self.ark_lottery_page 的值为新版抽卡活动的链接（理论上应该只有 zz 和 verifyid 参数的值会变动，而且大概率是+1）
        #   1.3 重新启用代码
        #   1.3.1 在 djc_helper.py 中将 ark_lottery 的调用处从 expired_activities 移到 payed_activities
        #   1.3.2 在 main.py 中将 main 函数中将 enable_card_lottery 设置为true
        #   1.3.3 在 config.toml.example 中 act_id_to_cost_all_cards_and_do_lottery 中增加新集卡活动的默认开关
        #   1.3.4 在 djc_helper.py 中将 fetch_pskey 的 p_skey 的判断条件取消注释
        #   1.4 更新 urls.py 中 not_ams_activities 中集卡活动的时间
        #
        # hack:
        #   2. 废弃
        #   2.1 在 djc_helper.py 中将 ark_lottery 的调用处从 normal_run 移到 expired_activities
        #   2.2 在 main.py 中将main函数中将 enable_card_lottery 设置为 false
        #   2.3 在 djc_helper.py 中将 fetch_pskey 的 p_skey 的判断条件注释

        # https://act.qzone.qq.com/vip/2019/xcardv3?zz=8&verifyid=qq2021dnf13
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
        from_qq = self.qq()

        ctx = f"{from_qq} 赠送卡片 {card_name}({cardId}) 给 {to_qq}"
        return self.get(ctx, self.urls.ark_lottery_send_card, cardId=cardId, from_qq=from_qq, to_qq=to_qq, actName=self.zzconfig.actName, print_res=print_res)
        # # {"13333":{"data":{},"ret":0,"msg":"成功"},"ecode":0,"ts":1607934736057}

    def send_card_by_name(self, card_name, to_qq):
        card_info_map = parse_card_group_info_map(self.zzconfig)
        return self.send_card(card_name, card_info_map[card_name].id, to_qq, print_res=True)

    def fetch_pskey(self, force=False, window_index=1):
        # 如果未启用qq空间相关的功能，则不需要这个
        any_enabled = False
        for activity_enabled in [
            self.cfg.function_switches.get_ark_lottery,
            # self.cfg.function_switches.get_dnf_warriors_call and not self.disable_most_activities(),
            self.cfg.function_switches.get_vip_mentor and not self.disable_most_activities(),
        ]:
            if activity_enabled:
                any_enabled = True
        if not force and not any_enabled:
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
            ql = QQLogin(self.common_cfg, window_index=window_index)
            try:
                if self.cfg.login_mode == "qr_login":
                    # 扫码登录
                    lr = ql.qr_login(login_mode=ql.login_mode_qzone, name=self.cfg.name)
                else:
                    # 自动登录
                    lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode=ql.login_mode_qzone, name=self.cfg.name)
            except GithubActionLoginException as e:
                logger.error("在github action环境下qq空间登录失败了，很大可能是因为该网络环境与日常环境不一致导致的（qq空间检查的很严），只能将qq空间相关配置禁用咯")
                self.cfg.function_switches.get_ark_lottery = False
                self.cfg.function_switches.get_dnf_warriors_call = False
                self.cfg.function_switches.get_vip_mentor = False
                return

            # 保存
            self.save_uin_pskey(lr.uin, lr.p_skey, lr.skey, lr.vuserid)
        else:
            lr = LoginResult(uin=cached_pskey["p_uin"], p_skey=cached_pskey["p_skey"], skey=cached_pskey["skey"], vuserid=cached_pskey["vuserid"])

        if lr.skey != "" and lr.vuserid != "":
            self.memory_save_uin_skey(lr.uin, lr.skey)
            self.vuserid = lr.vuserid

        return lr

    @try_except(extra_msg="检查p_skey是否过期失败，视为已过期", return_val_on_except=True)
    def is_pskey_expired(self, cached_pskey) -> bool:
        if cached_pskey is None:
            return True

        lr = LoginResult(uin=cached_pskey["p_uin"], p_skey=cached_pskey["p_skey"])

        # QQ空间集卡系活动
        # pskey过期提示：{'code': -3000, 'subcode': -4001, 'message': '请登录', 'notice': 0, 'time': 1601004332, 'tips': 'EE8B-284'}
        # 由于活动过期的判定会优先于pskey判定，需要需要保证下面调用的是最新的活动~

        def check_by_ark_lottery() -> bool:
            al = QzoneActivity(self, lr)
            res = al.do_ark_lottery("fcg_qzact_present", "增加抽卡次数-每日登陆页面", 25970, print_res=False)
            return res['code'] == -3000 and res['subcode'] == -4001

        def check_by_warriors_call() -> bool:
            qa = QzoneActivity(self, lr)
            qa.fetch_dnf_warriors_call_data()
            res = qa.do_dnf_warriors_call("fcg_receive_reward", "测试pskey是否过期", qa.zz().actbossRule.buyVipPrize, gameid=qa.zz().gameid, print_res=False)
            return res['code'] == -3000 and res['subcode'] == -4001

        ## QQ空间新版活动
        # pskey过期提示：分享领取礼包	{"code": -3000, "message": "未登录"}
        # 这个活动优先判定pskey

        def check_by_super_vip() -> bool:
            self.lr = lr
            res = self.qzone_act_op("幸运勇士礼包", "5353_75244d03", print_res=False)
            return res.get('code', 0) == -3000

        def check_by_yellow_diamond() -> bool:
            self.lr = lr
            res = self.qzone_act_op("幸运勇士礼包", "5328_63fbbb7d", print_res=False)
            return res.get('code', 0) == -3000

        # 用于按顺序检测p_skey是否过期的函数列表
        check_p_skey_expired_func_list = [
            check_by_super_vip,
            check_by_yellow_diamond,
            check_by_warriors_call,
            check_by_ark_lottery,
        ]

        for check_func in check_p_skey_expired_func_list:
            try:
                is_expired = check_func()
                return is_expired
            except Exception as e:
                # 如果这个活动挂了，就打印日志后，尝试下一个
                logFunc = logger.debug
                if use_by_myself():
                    logFunc = logger.warning
                logFunc(f"{check_func.__name__} 活动似乎挂了，将尝试使用下一个活动来判定，异常为 {e}")

        return True

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

    # --------------------------------------------QQ空间超级会员--------------------------------------------
    def dnf_super_vip(self):
        # https://act.qzone.qq.com/v2/vip/tx/p/1443_dc5df0f6
        show_head_line("QQ空间超级会员")
        self.show_not_ams_act_info("超级会员")

        if not self.cfg.function_switches.get_dnf_super_vip or self.disable_most_activities():
            logger.warning("未启用领取QQ空间超级会员功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        lr = self.fetch_pskey()
        if lr is None:
            return
        self.lr = lr

        self.qzone_act_op("幸运勇士礼包", "5353_75244d03")
        self.qzone_act_op("勇士见面礼", "5419_2c0ff022")
        if not self.cfg.function_switches.disable_share and is_first_run(f"dnf_super_vip_分享_{self.uin()}"):
            self.qzone_act_op("分享给自己", "5500_e8b39ea3", act_req_data={
                "receivers": [
                    self.qq(),
                ]
            })
        self.qzone_act_op("分享领取礼包", "5501_c70d8e0f")

    # --------------------------------------------QQ空间黄钻--------------------------------------------
    def dnf_yellow_diamond(self):
        # https://act.qzone.qq.com/v2/vip/tx/p/1442_36d9b930
        show_head_line("QQ空间黄钻")
        self.show_not_ams_act_info("黄钻")

        if not self.cfg.function_switches.get_dnf_yellow_diamond or self.disable_most_activities():
            logger.warning("未启用领取QQ空间黄钻功能，将跳过")
            return

        # 检查是否已在道聚城绑定
        if "dnf" not in self.bizcode_2_bind_role_map:
            logger.warning("未在道聚城绑定dnf角色信息，将跳过本活动，请移除配置或前往绑定")
            return

        lr = self.fetch_pskey()
        if lr is None:
            return
        self.lr = lr

        self.qzone_act_op("幸运勇士礼包", "5328_63fbbb7d")
        self.qzone_act_op("勇士见面礼", "5418_9f4ec626")
        if not self.cfg.function_switches.disable_share and is_first_run(f"dnf_yellow_diamond_分享_{self.uin()}"):
            self.qzone_act_op("分享给自己", "5497_319e33c3", act_req_data={
                "receivers": [
                    self.qq(),
                ]
            })
        self.qzone_act_op("分享领取礼包", "5499_4574810b")

    def qzone_act_op(self, ctx, sub_act_id, act_req_data=None, print_res=True):
        if act_req_data is None:
            roleinfo = RoleInfo()
            roleinfo.roleCode = "123456"
            try:
                roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
            except:
                pass
            act_req_data = {
                "role_info": {
                    "area": roleinfo.serviceID,
                    "partition": roleinfo.serviceID,
                    "role": roleinfo.roleCode,
                    "clientPlat": 3,
                    "game_id": "dnf"
                }
            }

        body = {
            "SubActId": sub_act_id,
            "ActReqData": json.dumps(act_req_data),
            "g_tk": getACSRFTokenForAMS(self.lr.p_skey),
        }
        extra_cookies = f"p_skey={self.lr.p_skey}; "

        return self.post(ctx, self.urls.qzone_activity_new, json=body, extra_cookies=extra_cookies, print_res=print_res)

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

    # --------------------------------------------DNF漫画预约活动--------------------------------------------
    @try_except()
    def dnf_comic(self):
        # https://dnf.qq.com/lbact/a20210617comic/
        show_head_line("DNF漫画预约活动")
        self.show_amesvr_act_info(self.dnf_comic_op)

        if not self.cfg.function_switches.get_dnf_comic or self.disable_most_activities():
            logger.warning("未启用领取DNF漫画预约活动功能，将跳过")
            return

        self.check_dnf_comic()

        def query_star_count():
            res = self.dnf_comic_op("查询星星数目", "774820", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            for info in raw_info.sOutValue1.split('|'):
                count_id, total_get, current = info.split(':')
                if int(count_id) == 324:
                    return int(total_get), int(current)

            return 0, 0

        self.dnf_comic_op("预约资格领取", "774765")
        self.dnf_comic_op("预约资格消耗", "774768")

        self.dnf_comic_op("13件福利任你抽", "774817")

        watch_comic_flowids = [
            "774769", "774770", "774771", "774772", "774773", "774774", "774775", "774776", "774777", "774778",
            "774779", "774780", "774781", "774782", "774783", "774784", "774785", "774786", "774787", "774788",
            "774789", "774790", "774791", "774792", "774793", "774794", "774795", "774796", "774797", "774798",
            "774799", "774800",
        ]
        # note: 当前更新至（定期刷新这个值）
        current_updated = 11
        for _idx, flowid in enumerate(watch_comic_flowids):
            idx = _idx + 1
            if idx > current_updated:
                logger.info(color("bold_yellow") + f"当前活动页面更新至第{current_updated}，不执行后续部分，避免被钓鱼<_<")
                break

            if is_first_run(f"comic_watch_{self.uin()}_{idx}"):
                self.dnf_comic_op(f"观看资格领取_第{idx}话", flowid)

        self.dnf_comic_op("观看礼包资格消耗", "775253")

        self.dnf_comic_op("每日在线好礼", "774826")

        total_get, star_count = query_star_count()
        msg = f"当前共有{star_count}颗星星（累积获得{total_get}颗），因为兑换道具比较多，请自行定期来活动页面确定领取啥~ https://dnf.qq.com/lbact/a20210617comic/"
        logger.info(color("bold_yellow") + msg)
        if is_weekly_first_run("提示领道具"):
            async_message_box(msg, "漫画活动提示", open_url="https://dnf.qq.com/lbact/a20210617comic/")

        if use_by_myself():
            # 我自己进行兑换~
            self.dnf_comic_op("兑换-装备提升礼盒", "774806")
            self.dnf_comic_op("兑换-灿烂的徽章神秘礼盒", "774803")

            # self.dnf_comic_op("兑换-升级券", "774802")
            # self.dnf_comic_op("兑换-黑钻15天", "774805")
            # self.dnf_comic_op("兑换-黑钻7天", "774807")
            # self.dnf_comic_op("兑换-抗疲劳秘药 (20点)(lv50-100)", "774808")
            # self.dnf_comic_op("兑换-华丽的徽章神秘礼盒", "774809")
            # self.dnf_comic_op("兑换-诺斯匹斯的文书礼盒 (150个)", "774811")
            # self.dnf_comic_op("兑换-[期限]时间引导石礼盒 (10个)", "774812")
            # self.dnf_comic_op("兑换-抗疲劳秘药 (10点)(lv50-100)", "774813")
            # self.dnf_comic_op("兑换-黑钻3天", "774814")
            # self.dnf_comic_op("兑换-成长胶囊 (10百分比)(lv50-99)", "774815")
            # self.dnf_comic_op("兑换-宠物饲料礼袋 (20个)", "774816")

            # self.dnf_comic_op("星星夺宝", "774818")

    def check_dnf_comic(self):
        self.check_bind_account("qq视频-DNF漫画预约活动", "https://dnf.qq.com/lbact/a20210617comic/",
                                activity_op_func=self.dnf_comic_op, query_bind_flowid="774762", commit_bind_flowid="774761")

    def dnf_comic_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_comic
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/lbact/a20210617comic/",
                                   **extra_params)

    # --------------------------------------------DNF十三周年庆活动--------------------------------------------
    @try_except()
    def dnf_13(self):
        # https://dnf.qq.com/cp/a20210524fete/index.html
        show_head_line("DNF十三周年庆活动")
        self.show_amesvr_act_info(self.dnf_13_op)

        if not self.cfg.function_switches.get_dnf_13 or self.disable_most_activities():
            logger.warning("未启用领取DNF十三周年庆活动功能，将跳过")
            return

        self.check_dnf_13()

        def query_lottery_count():
            res = self.dnf_13_op("查询剩余抽奖次数", "772683", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue1)

        for idx in range_from_one(5):
            self.dnf_13_op(f"点击第{idx}个icon，领取抽奖机会", "769465", index=idx)

        send_list = self.cfg.dnf_13_send_qq_list
        if len(send_list) == 0:
            logger.info("在配置工具中添加13周年赠送QQ列表（最多三个），可额外领取抽奖次数")
        elif len(send_list) > 3:
            send_list = self.cfg.dnf_13_send_qq_list[:3]

        if not self.cfg.function_switches.disable_share:
            for qq in send_list:
                self.dnf_13_op(f"发送分享消息，额外增加抽奖机会-{qq}", "771230", receiveUin=qq)

        lc = query_lottery_count()
        logger.info(f"当前剩余抽奖次数为{lc}次")
        for idx in range_from_one(lc):
            self.dnf_13_op(f"第{idx}/{lc}次抽奖", "771234")

    def check_dnf_13(self):
        self.check_bind_account("qq视频-DNF十三周年庆活动", "https://dnf.qq.com/cp/a20210524fete/index.html",
                                activity_op_func=self.dnf_13_op, query_bind_flowid="768385", commit_bind_flowid="768384")

    def dnf_13_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_13
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/cp/a20210524fete",
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

    # --------------------------------------------DNF奥兹玛竞速--------------------------------------------
    @try_except()
    def dnf_ozma(self):
        # https://xinyue.qq.com/act/a20210526znqhd/index.html
        show_head_line("DNF奥兹玛竞速")
        self.show_amesvr_act_info(self.dnf_ozma_op)

        if not self.cfg.function_switches.get_dnf_ozma or self.disable_most_activities():
            logger.warning("未启用领取DNF奥兹玛竞速活动合集功能，将跳过")
            return

        self.check_dnf_ozma()

        def query_info():
            res = self.dnf_ozma_op("查询信息", "770021", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = DnfHeiyaInfo()
            info.lottery_count = int(raw_info.sOutValue1)
            info.box_score = int(raw_info.sOutValue2)

            return info

        def take_lottery_counts():
            if not (self.common_cfg.try_auto_bind_new_activity and self.common_cfg.force_sync_bind_with_djc):
                logger.info("未开启自动绑定活动和强制同步功能，将不尝试切换角色来领取抽奖券")
                self.dnf_ozma_op("领取通关奥兹玛赠送抽奖券", "770026")
                return

            ignore_rolename_list = self.cfg.ozma_ignored_rolename_list

            logger.info(color("bold_green") + f"尝试使用当前区服的所有100级角色来领取抽奖次数，目前配置为不参与尝试的角色列表为 {ignore_rolename_list}，如需变更可修改配置工具中当前账号的该选项")
            djc_roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo

            # 复刻一份道聚城绑定角色信息，用于临时修改，同时确保不会影响到其他活动
            take_lottery_count_role_info = RoleInfo().auto_update_config(to_raw_type(djc_roleinfo))
            valid_roles = query_level_100_roles(ignore_rolename_list)
            for idx, role in enumerate(valid_roles):
                # 临时更新绑定角色为该角色
                logger.info("")
                logger.info(color("bold_cyan") + f"[{idx + 1}/{len(valid_roles)}] 尝试临时切换领取角色为 {role.rolename} 来领取本周通关奥兹玛可获取的抽奖次数")

                take_lottery_count_role_info.roleCode = role.roleid
                take_lottery_count_role_info.roleName = role.rolename
                self.check_dnf_ozma(roleinfo=take_lottery_count_role_info, roleinfo_source="临时切换的领取角色")

                # 领奖
                idx = 0
                while True:
                    idx += 1
                    res = self.dnf_ozma_op(f"领取 {role.rolename} 本周第{idx}次 通关奥兹玛赠送抽奖券", "770026")
                    if int(res["ret"]) != 0:
                        break

            # 切换回原有绑定角色
            logger.info(color("bold_green") + "所有符合条件的角色尝试领取抽奖次数完毕，切换为原有绑定角色")
            self.check_dnf_ozma()

        def query_level_100_roles(ignore_rolename_list: List[str]) -> List[DnfRoleInfo]:
            djc_roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo

            valid_roles = []

            roles = self.query_dnf_rolelist(djc_roleinfo.serviceID)
            for role in roles:
                if role.level < 100:
                    # 未到100级必定不可能通关奥兹玛
                    continue

                if role.rolename in ignore_rolename_list:
                    # 设置为忽略的也跳过
                    continue

                valid_roles.append(role)

            return valid_roles

        self.dnf_ozma_op("周年庆登录礼包", "770194")
        self.dnf_ozma_op("周年庆130元充值礼", "770201")

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        checkInfo = self.get_dnf_roleinfo()
        checkparam = quote_plus(quote_plus(checkInfo.checkparam))
        self.dnf_ozma_op("报名礼包", "770017",
                         sArea=roleinfo.serviceID, sPartition=roleinfo.serviceID, sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
                         sRoleId=roleinfo.roleCode, sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
                         md5str=checkInfo.md5str, ams_checkparam=checkparam, checkparam=checkparam, )

        take_lottery_counts()

        info = query_info()
        logger.info(f"当前有{info.lottery_count}张抽奖券")
        for idx in range(info.lottery_count):
            self.dnf_ozma_op(f"第{idx + 1}次抽奖", "770027")
            if idx != info.lottery_count:
                time.sleep(5)

        self.dnf_ozma_op("每日登录游戏送开箱积分", "770028")
        self.dnf_ozma_op("每日登录心悦APP送开箱积分", "770029")
        self.dnf_ozma_op("每日网吧登录送开箱积分", "770030")
        endTime = "20210721"
        info = query_info()
        logger.info(color("bold_cyan") + f"当前开箱积分为{info.box_score}。PS：最高级宝箱需要60分~")
        # 不确定是否跟勇者征集令一样宝箱互斥，保底期间，最后一天再全领，在这之前则是先只尝试领取第五个
        # 青铜宝箱 4-19分
        # 白银宝箱 20-29分
        # 黄金宝箱 30-44分
        # 钻石宝箱 45-59分
        # 泰拉宝箱 60分
        if info.box_score >= 60:
            self.dnf_ozma_op(f"开启宝箱-level=5", "770031", level=5)
        if get_today() == endTime:
            logger.info("已到活动最后一天，尝试从高到低领取每个宝箱")
            for level in range(5, 0, -1):
                self.dnf_ozma_op(f"开启宝箱-level={level}", "770031", level=level)

        self.dnf_ozma_op("登录心悦APP送礼包", "770032")

    def check_dnf_ozma(self, roleinfo=None, roleinfo_source="道聚城所绑定的角色"):
        self.check_bind_account("DNF奥兹玛竞速", "https://xinyue.qq.com/act/a20210526znqhd/index.html",
                                activity_op_func=self.dnf_ozma_op, query_bind_flowid="770020", commit_bind_flowid="770019",
                                roleinfo=roleinfo, roleinfo_source=roleinfo_source)

    def dnf_ozma_op(self, ctx, iFlowId, weekDay="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_ozma

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "https://xinyue.qq.com/act/a20210526znqhd/index.html",
                                   **extra_params)

    # --------------------------------------------qq视频活动--------------------------------------------
    # note: 接入新qq视频活动的流程如下
    #   1. chrome打开devtools，激活手机模式，并在过滤栏中输入 option=100
    #   2. 打开活动页面 https://m.film.qq.com/magic-act/113645/1_index_index.html
    #   3. 点击任意按钮，从query_string中获取最新的act_id (其实就是上面 magic-act/ 和 /index.html 中间这一串字符
    qq_video_act_id = "113645"
    #   note:4. 依次点击下面各个行为对应的按钮，从query_string中获取最新的module_id，如果某个请求的type参数不是21，也需要专门调整对应值
    qq_video_module_id_lucky_user = "140786"  # 幸运勇士礼包
    # qq_video_module_id_first_meet_gift = "zjyk7dlgj23jk7egsofqaj3hk9"  # 勇士见面礼-礼包
    # qq_video_module_id_first_meet_token = "4c43cws9i4721uq01ghu02l3fl"  # 勇士见面礼-令牌
    qq_video_module_id_lottery = "140779"  # 每日抽奖1次(需在活动页面开通QQ视频会员)
    qq_video_module_id_online_30_minutes = "140771"  # 在线30分钟
    qq_video_module_id_online_3_days = "140774"  # 累积3天
    qq_video_module_id_online_7_days = "140775"  # 累积7天
    qq_video_module_id_online_15_days = "140778"  # 累积15天

    qq_video_module_id_card_gift_1 = "140780"  # 使用1张卡兑换奖励
    qq_video_module_id_card_gift_2 = "140783"  # 使用2张卡兑换奖励
    qq_video_module_id_card_gift_3 = "140784"  # 使用3张卡兑换奖励
    qq_video_module_id_card_gift_4 = "140785"  # 使用4张卡兑换奖励

    #   note:5. 以下的请求则是根据现有的代码中对应参数，刷新页面过滤出对应请求
    qq_video_module_id_query_card_info = "140767"  # 查询卡片信息

    qq_video_module_id_enter_page = "140769"  # 首次进入页面
    qq_video_module_id_take_enter_page_card = "140770"  # 领取进入页面的卡片

    @try_except()
    def qq_video(self):
        show_head_line("qq视频活动")
        self.show_not_ams_act_info("qq视频蚊子腿")

        if not self.cfg.function_switches.get_qq_video or self.disable_most_activities():
            logger.warning("未启用领取qq视频活动功能，将跳过")
            return

        self.check_qq_video()

        @try_except()
        def query_card_info(ctx):
            show_head_line(ctx, msg_color=color("bold_cyan"))

            res = self.qq_video_op("查询卡片信息", self.qq_video_module_id_query_card_info, option="111", type="71", is_prepublish="0", print_res=False)

            heads = ["名称", "数目"]
            colSizes = [20, 4]
            logger.info(tableify(heads, colSizes))
            for card in res["do_act"]["score_list"]:
                cols = [card["score_name"], card["score_num"]]
                logger.info(tableify(cols, colSizes))

        # 正式逻辑

        self.qq_video_op("首次进入页面", self.qq_video_module_id_enter_page, type="51", option="1", task="51")
        self.qq_video_op("领取页面卡片", self.qq_video_module_id_take_enter_page_card, type="59", option="1")

        self.qq_video_op("幸运勇士礼包", self.qq_video_module_id_lucky_user, type="100112")
        # self.qq_video_op("勇士见面礼-礼包", self.qq_video_module_id_first_meet_gift, type="100112")
        # self.qq_video_op("勇士见面礼-令牌", self.qq_video_module_id_first_meet_token)

        self.qq_video_op("每日抽奖1次(需在活动页面开通QQ视频会员)", self.qq_video_module_id_lottery)

        self.qq_video_op("在线30分钟", self.qq_video_module_id_online_30_minutes)
        self.qq_video_op("累积3天", self.qq_video_module_id_online_3_days)
        self.qq_video_op("累积7天", self.qq_video_module_id_online_7_days)
        self.qq_video_op("累积10天", self.qq_video_module_id_online_15_days)

        logger.warning("如果【在线30分钟】提示你未在线30分钟，但你实际已在线超过30分钟，也切换过频道了，不妨试试退出游戏，有时候在退出游戏的时候才会刷新这个数据")

        # 首先尝试按照优先级领取
        res = self.qq_video_op("使用4张卡兑换奖励（限1次）", self.qq_video_module_id_card_gift_4)
        if res['data']['lottery_txt'] == '您当前尚未集齐卡片哦~':
            logger.info("尚未兑换至尊礼包，先跳过其他礼包")
        else:
            res = self.qq_video_op("使用3张卡兑换奖励（限1次）", self.qq_video_module_id_card_gift_3)
            if res['data']['lottery_txt'] == '您当前尚未集齐卡片哦~':
                logger.info("尚未兑换高级礼包，先跳过其他礼包")
            else:
                self.qq_video_op("使用2张卡兑换奖励（限10次）", self.qq_video_module_id_card_gift_2)
                self.qq_video_op("使用1张卡兑换奖励（限10次）", self.qq_video_module_id_card_gift_1)

        # 如果到了最后一天，就尝试领取所有可以领取的奖励
        actInfo = get_not_ams_act("qq视频蚊子腿")
        if format_time(parse_time(actInfo.dtEndTime), "%Y%m%d") == get_today():
            logger.info("已到活动最后一天，尝试领取所有可以领取的奖励")
            gifts = [
                (4, self.qq_video_module_id_card_gift_4),
                (3, self.qq_video_module_id_card_gift_3),
                (2, self.qq_video_module_id_card_gift_2),
                (1, self.qq_video_module_id_card_gift_1),
            ]
            for card_count, module_id in gifts:
                for i in range(10):
                    res = self.qq_video_op(f"使用{card_count}张卡兑换奖励", module_id)
                    if res['data']['sys_code'] != 0:
                        break

        # 查询一遍集卡信息
        query_card_info("最新卡片信息")

    def check_qq_video(self):
        while True:
            res = self.qq_video_op("幸运勇士礼包", self.qq_video_module_id_lucky_user, type="100112", print_res=False)
            # {"frame_resp": {"failed_condition": {"condition_op": 3, "cur_value": 0, "data_type": 2, "exp_value": 0, "type": 100418}, "msg": "", "ret": 0, "security_verify": {"iRet": 0, "iUserType": 0, "sAppId": "", "sBusinessId": "", "sInnerMsg": "", "sUserMsg": ""}}, "act_id": 108810, "data": {"button_txt": "关闭", "cdkey": "", "custom_list": [], "end_timestamp": -1, "ext_url": "", "give_type": 0, "is_mask_cdkey": 0, "is_pop_jump": 0, "item_share_desc": "", "item_share_title": "", "item_share_url": "", "item_sponsor_title": "", "item_sponsor_url": "", "item_tips": "", "jump_url": "", "jump_url_web": "", "lottery_item_id": "1601827185657s2238078729s192396s1", "lottery_level": 0, "lottery_name": "", "lottery_num": 0, "lottery_result": 0, "lottery_txt": "您当前还未绑定游戏帐号，请先绑定哦~", "lottery_url": "", "lottery_url_ext": "", "lottery_url_ext1": "", "lottery_url_ext2": "", "msg_title": "告诉我怎么寄给你", "need_bind": 0, "next_type": 2, "pop_jump_btn_title": "", "pop_jump_url": "", "prize_give_info": {"prize_give_status": 0}, "property_detail_code": 0, "property_detail_msg": "", "property_type": 0, "share_txt": "", "share_url": "", "source": 0, "sys_code": -904, "url_lottery": "", "user_info": {"addr": "", "name": "", "tel": "", "uin": ""}}, "module_id": 125890, "msg": "", "ret": 0, "security_verify": {"iRet": 0, "iUserType": 0, "sAppId": "", "sBusinessId": "", "sInnerMsg": "", "sUserMsg": ""}}
            if int(res["data"]["sys_code"]) == -904 and extract_qq_video_message(res) == "您当前还未绑定游戏帐号，请先绑定哦~":
                self.guide_to_bind_account("qq视频活动", "https://m.film.qq.com/magic-act/110254/index.html", activity_op_func=None)
                continue

            return res

    def qq_video_op(self, ctx, module_id, option="100", type="21", task="", is_prepublish="", print_res=True):
        res = self._qq_video_op(ctx, type, option, module_id, task, is_prepublish, print_res)

        if "data" in res and int(res["data"].get("sys_code", res['ret'])) == -1010 and extract_qq_video_message(res) == "系统错误":
            msg = "【需要修复这个】不知道为啥这个操作失败了，试试连上fiddler然后手动操作看看请求哪里对不上"
            logger.warning(color("fg_bold_yellow") + msg)

        return res

    def _qq_video_op(self, ctx, type, option, module_id, task, is_prepublish, print_res=True):
        extra_cookies = "; ".join([
            "",
            "appid=3000501",
            "main_login=qq",
            f"vuserid={self.vuserid}",
        ])
        return self.get(ctx, self.urls.qq_video, type=type, option=option, act_id=self.qq_video_act_id, module_id=module_id, task=task, is_prepublish=is_prepublish,
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
        qq = self.qq()
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
        qq = self.qq()
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(ctx, "comm.ams.game.qq.com", "group_k", "bb", iActivityId, iFlowId, True, "https://mwegame.qq.com/dnf/rankv2/index.html/",
                                  sArea=roleinfo.serviceID, serverId=roleinfo.serviceID, areaId=roleinfo.serviceID,
                                  sRoleId=roleinfo.roleCode, sRoleName=quote_plus(roleinfo.roleName),
                                  uin=qq, skey=self.cfg.account_info.skey,
                                  nickName=quote_plus(dnf_helper_info.nickName), userId=dnf_helper_info.userId, token=quote_plus(dnf_helper_info.token),
                                  **extra_params)

    def dnf_rank_op(self, ctx, url, **params):
        qq = self.qq()
        info = self.cfg.dnf_helper_info
        return self.get(ctx, url, uin=qq, userId=info.userId, token=quote_plus(info.token), **params)

    # --------------------------------------------dnf助手活动(后续活动都在这个基础上改)--------------------------------------------
    @try_except()
    def dnf_helper(self):
        # https://mwegame.qq.com/act/dnf/Time2021/index
        show_head_line("dnf助手")
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

        def query_info():
            res = self.dnf_helper_op("查询", "753432", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = DnfHelperInfo()
            info.unlocked_maps.add(1)
            for idx, v in enumerate(raw_info.sOutValue2.split(';')):
                if int(v) > 0:
                    info.unlocked_maps.add(idx + 2)
            info.remaining_play_times = int(raw_info.sOutValue3)

            return info

        def query_game_info():
            qq = self.qq()
            url = f"https://mwegame.qq.com/act/dnf/Time2021/ajax/init?uin={qq}"
            res = self.post("查询小游戏信息", url, {}, print_res=False)

            info = DnfHelperGameInfo().auto_update_config(res['data'])

            return info

        self.dnf_helper_op("每天加游戏次数", "753415")

        logger.info(color("bold_cyan") + "当前仅支持单人模式，组队模式请手动完成")

        stage_infos = [
            (6, 17, 19, "天空之城", "754337", "754138"),
            (5, 14, 16, "天际", "759384", "753758"),
            (4, 13, 13, "地轨", "759386", "754076"),
            (3, 9, 12, "能源之地", "759388", "754078"),
            (2, 6, 8, "时空之门", "759393", "754083"),
            (1, 4, 5, "天界", "759395", "754085"),
            (0, 0, 3, "远古", "759397", "754080"),
        ]

        remaining_play_times = query_info().remaining_play_times
        for play_idx in range_from_one(remaining_play_times):
            info = query_info()
            logger.info(color("bold_green") + f"开始{play_idx}/{remaining_play_times}次小游戏，当前解锁关卡为{info.unlocked_maps}")
            for stage_idx in range(7, 0, -1):
                if stage_idx not in info.unlocked_maps:
                    continue

                mapIndex, oImgsIndex_min, oImgsIndex_max, stage_name, start_flowid, end_flowid = stage_infos[stage_idx - 1]

                oImgsIndex = random.randrange(oImgsIndex_min, oImgsIndex_max + 1)
                oIndex = oImgsIndex - oImgsIndex_min

                stage = f"{stage_name}-{mapIndex}-{oImgsIndex}"

                logger.info(color("bold_cyan") + f"开始 {stage}")
                self.dnf_helper_op(f"开始游戏(单人)---{stage}", start_flowid, map1=mapIndex, map2=oImgsIndex, len=oIndex)
                count_down(color("bold_green") + "等待小游戏完成", 8 * 60 + 1)
                self.dnf_helper_op(f"领取奖励(单人)---{stage}", end_flowid, map1=mapIndex, map2=oImgsIndex, len=oIndex)

                break

        # self.dnf_helper_op("开始游戏(单人)---天空之城", "754337")
        # self.dnf_helper_op("开始游戏(单人)---决战天际", "759384")
        # self.dnf_helper_op("开始游戏(单人)---地轨", "759386")
        # self.dnf_helper_op("开始游戏(单人)---能源之地", "759388")
        # self.dnf_helper_op("开始游戏(单人)---时空之门", "759393")
        # self.dnf_helper_op("开始游戏(单人)---天界", "759395")
        # self.dnf_helper_op("开始游戏(单人)---远古", "759397")
        #
        # self.dnf_helper_op("决战天空之城游戏模式(单人)", "754138")
        # self.dnf_helper_op("决战天际游戏模式(单人)", "753758")
        # self.dnf_helper_op("决战地轨者游戏模式(单人)", "754076")
        # self.dnf_helper_op("决战能源之地游戏模式(单人)", "754078")
        # self.dnf_helper_op("决战时空之门游戏模式(单人)", "754083")
        # self.dnf_helper_op("决战天界游戏模式(单人)", "754085")
        # self.dnf_helper_op("决战远古游戏模式(单人)", "754080")

        # self.dnf_helper_op("提前结束游戏", "755483")

        # self.dnf_helper_op("邀请组队", "754338")
        #
        # self.dnf_helper_op("开始游戏(组队)----天空之城", "756737")
        # self.dnf_helper_op("开始游戏(组队)----决战天际", "759385")
        # self.dnf_helper_op("开始游戏(组队)----地轨", "759387")
        # self.dnf_helper_op("开始游戏(组队)----能源", "759389")
        # self.dnf_helper_op("开始游戏(组队)----时空之门", "759394")
        # self.dnf_helper_op("开始游戏(组队)----天界", "759396")
        # self.dnf_helper_op("开始游戏(组队)----远古", "759398")
        #
        # self.dnf_helper_op("决战天际游戏模式(组队)", "754075")
        # self.dnf_helper_op("决战地轨者游戏模式(组队)", "754077")
        # self.dnf_helper_op("决战能源之地游戏模式(组队)", "754079")
        # self.dnf_helper_op("决战远古游戏模式(组队)", "754081")
        # self.dnf_helper_op("决战时空之门游戏模式(组队)", "754084")
        # self.dnf_helper_op("决战天界游戏模式(组队)", "754086")
        # self.dnf_helper_op("决战天空之城游戏模式(组队)", "754139")
        #
        ## self.dnf_helper_op("提前结束游戏_from755483", "755485")

        self.dnf_helper_op("最终奖励", "756324")

        game_times = int(query_game_info().GameTimes)
        for need_game_times, name, flowid in [
            (9, "解锁9次(决战天际)", "753695"),
            (15, "解锁15次(决战地轨者)", "753749"),
            (21, "解锁21次(决战能源之地)", "753750"),
            (30, "解锁30次(决战时空之门)", "753751"),
            (45, "解锁45次(决战天界)", "753752"),
            (60, "解锁60次(决战远古)", "753753"),

            (9, "解锁9次(决战天际)_from753695", "755230"),
            (15, "解锁15次(决战地轨者)_from753749", "755232"),
            (21, "解锁21次(决战能源之地)_from753750", "755234"),
            (30, "解锁30次(决战时空之门)_from753751", "755235"),
            (45, "解锁45次(决战天界)_from753752", "755236"),
            (60, "解锁60次(决战远古)_from753753", "755237"),
        ]:
            if game_times < need_game_times:
                continue
            self.dnf_helper_op(name, flowid)

    # def check_dnf_helper(self):
    #     self.check_bind_account("dnf助手活动", "https://mwegame.qq.com/act/dnf/Time2021/index",
    #                             activity_op_func=self.dnf_helper_op, query_bind_flowid="736842", commit_bind_flowid="736841")

    def dnf_helper_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_helper

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        qq = self.qq()
        dnf_helper_info = self.cfg.dnf_helper_info

        res = self.amesvr_request(ctx, "comm.ams.game.qq.com", "group_k", "bb", iActivityId, iFlowId, print_res, "https://mwegame.qq.com/act/dnf/Time2021/index",
                                  sArea=roleinfo.serviceID, serverId=roleinfo.serviceID,
                                  sRoleId=roleinfo.roleCode, sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
                                  uin=qq, skey=self.cfg.account_info.skey,
                                  nickName=quote_plus(quote_plus(dnf_helper_info.nickName)), userId=dnf_helper_info.userId, token=quote_plus(quote_plus(dnf_helper_info.token)),
                                  **extra_params)

        # 1000017016: 登录态失效,请重新登录
        if res is not None and res["flowRet"]["iRet"] == "700" and "登录态失效" in res["flowRet"]["sMsg"]:
            extra_msg = "dnf助手的登录态已过期，目前需要手动更新，具体操作流程如下"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_helper_expired_" + get_today())

            raise RuntimeError("dnf助手token过期，请重试获取")

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
            "uin": self.qq(),
            "token": dnf_helper_info.token,
            "uniqueRoleId": dnf_helper_info.uniqueRoleId,
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
            logger.info(f"领取{side}的第{awardInfo.sName}个基础奖励: {res.get('giftName', f'出错啦-{res}')}")
            if res.get('msg', "") == '登录态异常':
                msg = f"账号 {self.cfg.name} 的 dnf助手鉴权信息不对，将无法领取奖励。请将配置工具中dnf助手的四个参数全部填写。"
                async_message_box(msg, "助手鉴权失败", show_once=True)

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
            extra_msg = f"dnf助手的userId未配置或配置有误，当前值为[{self.cfg.dnf_helper_info.userId}]，无法进行dnf助手编年史活动，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_helper_chronicle")
            return

        # 检查领奖额外需要的参数
        if self.cfg.dnf_helper_info.token == "" or self.cfg.dnf_helper_info.uniqueRoleId == "":
            extra_msg = f"dnf助手的token/uniqueRoleId未配置，将无法领取等级奖励（其他似乎不受影响）。若想要自动领奖，请按照下列流程进行配置"
            self.show_dnf_helper_info_guide(extra_msg, show_message_box_once_key="dnf_helper_chronicle")
            # 不通过也继续走，只是领奖会失败而已

        # 提示做任务
        msg = "dnf助手签到任务和浏览咨询详情页请使用auto.js等自动化工具来模拟打开助手去执行对应操作，当然也可以每天手动打开助手点一点-。-"
        if is_monthly_first_run("dnf_helper_chronicle_task_tips_month_monthly"):
            async_message_box(msg, "编年史任务提示")
        else:
            logger.warning(color("bold_cyan") + msg)

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
    #   1. 打开新活动的页面 https://guanjia.qq.com/act/cop/20210425dnf/pc/
    #   2. 按F12，在Console中输入 console.log(JSON.stringify(GLOBAL_AMP_CONFIG))，将结果复制到 format_json.json 中格式化，方便查看
    #   3. 在json中搜索 comGifts，定位到各个礼包的信息，并将下列变量的数值更新为新版本
    guanjia_common_gifts_act_id = "1160"  # 礼包活动ID
    guanjia_gift_id_special_rights = "7761"  # 电脑管家特权礼包
    guanjia_gift_id_sign_in_2_days = "7762"  # 连续签到2天礼包
    guanjia_gift_id_return_user = "7763"  # 幸运勇士礼包
    guanjia_gift_id_download_and_login_this_version_guanjia = "7764"  # 下载登录管家任务
    guanjia_gift_id_game_online_30_minutes = "7765"  # 每日游戏在线30分钟任务
    guanjia_gift_id_sign_in = "7766"  # 每日签到任务
    # note: 4. 在json中搜索 lotGifts，定位到抽奖的信息，并将下列变量的数值更新为新版本
    guanjia_lottery_gifts_act_id = "1159"  # 抽奖活动ID

    # note: 5. 启用时取消注释fetch_guanjia_openid中开关，废弃时则注释掉
    # note: 6. 调整urls中管家蚊子腿的起止时间
    # note: 7. 调整config_ui中管家开关
    # note: 8. 修改qq_login中管家活动的url（搜索 /act/cop 即可，共两处，login函数和实际跳转处）

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
        self.guanjia_common_gifts_op("连续签到2天礼包", giftId=self.guanjia_gift_id_sign_in_2_days)
        self.guanjia_common_gifts_op("幸运勇士礼包", giftId=self.guanjia_gift_id_return_user)

        self.guanjia_common_gifts_op("下载安装并登录电脑管家", giftId=self.guanjia_gift_id_download_and_login_this_version_guanjia)

        self.guanjia_common_gifts_op("每日游戏在线30分钟", giftId=self.guanjia_gift_id_game_online_30_minutes)
        self.guanjia_common_gifts_op("每日签到任务", giftId=self.guanjia_gift_id_sign_in)

        for i in range(10):
            res = self.guanjia_lottery_gifts_op("抽奖")
            # {"code": 4101, "msg": "积分不够", "result": []}
            if res["code"] != 0:
                break
            time.sleep(self.common_cfg.retry.request_wait_time)

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

    # --------------------------------------------新管家蚊子腿--------------------------------------------
    # note: 新管家活动接入流程：
    #   1. 打开新活动的页面 https://sdi.3g.qq.com/v/2021061115132511816
    #   2. 按F12，输入过滤关键词为 -speed -pv? -cap_ -white
    #   3. 随便点个活动按钮，点开过滤出的请求，其中的aid就是活动id
    guanjia_new_act_id = "2021061115132511816"  # 活动ID
    # note: 4. 按照下面的顺序依次点击对应活动按钮，最后按顺序将请求中的lid复制出来
    guanjia_new_gift_id_special_rights = "224"  # 电脑管家特权礼包
    guanjia_new_gift_id_sign_in_2_days = "222"  # 连续签到2天礼包
    guanjia_new_gift_id_return_user = "220"  # 幸运勇士礼包
    guanjia_new_gift_id_download_and_login_this_version_guanjia = "223"  # 下载登录管家任务
    guanjia_new_gift_id_game_online_30_minutes = "225"  # 每日游戏在线30分钟任务
    guanjia_new_gift_id_sign_in = "226"  # 每日签到任务
    # note: 4. 在json中搜索 lotGifts，定位到抽奖的信息，并将下列变量的数值更新为新版本
    guanjia_new_lottery_gifts_act_id = "176"  # 抽奖活动ID

    # note: 5. 启用时取消注释fetch_guanjia_openid中开关，废弃时则注释掉
    # note: 6. 调整urls中管家蚊子腿的起止时间
    # note: 7. 调整config_ui中管家开关
    # note: 8. 修改qq_login中管家活动的url（搜索 /act/cop 即可，共两处，login函数和实际跳转处）
    @try_except()
    def guanjia_new(self):
        show_head_line("管家蚊子腿")
        self.show_not_ams_act_info("管家蚊子腿")

        if not self.cfg.function_switches.get_guanjia or self.disable_most_activities():
            logger.warning("未启用领取管家蚊子腿活动合集功能，将跳过")
            return

        logger.warning("管家的活动只负责领取奖励，具体任务条件，如登录管家、签到等请自行完成")

        lr = self.fetch_guanjia_openid()
        if lr is None:
            return
        self.guanjia_lr = lr
        # 等一会，避免报错
        time.sleep(self.common_cfg.retry.request_wait_time)

        def receive(ctx, lid):
            return self.guanjia_new_op(ctx, "pc_sdi_receive/receive", lid)

        def add_draw_pool(ctx, lid):
            return self.guanjia_new_op(ctx, "pc_sdi_receive/add_draw_pool", lid)

        def take_unclaimed_awards():
            raw_res = self.guanjia_new_op(f"查询领奖信息", "lottery.do?method=myNew", "", page_index=1, page_size=1000, domain_name="sdi.3g.qq.com", print_res=False)
            info = GuanjiaNewQueryLotteryInfo().auto_update_config(raw_res)
            for lr in info.result:
                if lr.has_taken():
                    continue

                # 之前抽奖了，但未领奖
                _take_lottery_award(f"补领取奖励-{lr.drawLogId}-{lr.presentId}-{lr.comment}", lr.drawLogId)

        def lottery(ctx) -> bool:
            lottrey_raw_res = self.guanjia_new_op(f"{ctx}-抽奖阶段", "sdi_lottery/lottery", self.guanjia_new_lottery_gifts_act_id)
            lottery_res = GuanjiaNewLotteryResult().auto_update_config(lottrey_raw_res)
            success = lottery_res.success == 0
            if success:
                data = lottery_res.data
                _take_lottery_award(f"{ctx}-领奖阶段-{data.drawLogId}-{data.presentId}-{data.comment}", data.drawLogId)

            return success

        def _take_lottery_award(ctx: str, draw_log_id: int):
            self.guanjia_new_op(ctx, "lottery.do?method=take", self.guanjia_new_lottery_gifts_act_id, draw_log_id=draw_log_id, domain_name="sdi.3g.qq.com")

        receive("电脑管家特权礼包", self.guanjia_new_gift_id_special_rights)
        receive("连续签到2天礼包", self.guanjia_new_gift_id_sign_in_2_days)
        receive("幸运勇士礼包", self.guanjia_new_gift_id_return_user)

        add_draw_pool("下载安装并登录电脑管家", self.guanjia_new_gift_id_download_and_login_this_version_guanjia)

        add_draw_pool("每日游戏在线30分钟", self.guanjia_new_gift_id_game_online_30_minutes)
        add_draw_pool("每日签到任务", self.guanjia_new_gift_id_sign_in)

        for i in range(10):
            success = lottery("抽奖")
            if not success:
                break
            time.sleep(self.common_cfg.retry.request_wait_time)

        # 补领取之前未领取的奖励
        take_unclaimed_awards()

    def guanjia_new_op(self, ctx: str, api_name: str, lid: str, draw_log_id=0, page_index=1, page_size=1000, domain_name="sdi.m.qq.com", print_res=True):
        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo

        act_id = self.guanjia_new_act_id
        openid = self.guanjia_lr.qc_openid
        nickname = self.guanjia_lr.qc_nickname()
        key = self.guanjia_lr.qc_access_token

        extra_cookies = f"__qc__openid={self.guanjia_lr.qc_openid}; __qc__k={self.guanjia_lr.qc_k};"

        req = GuanjiaNewRequest()
        req.aid = req.bid = act_id
        req.lid = lid
        req.openid = req.account = req.gjid = openid
        req.nickname = nickname
        req.key = req.accessToken = req.token = key
        req.accessToken = "QQ"
        req.loginType = "qq"
        req.outVeri = 1
        req.roleArea = req.area = str(roleinfo.serviceID)
        req.roleid = str(roleinfo.roleCode)
        req.check = 0
        req.drawLogId = draw_log_id
        req.pageIndex = page_index
        req.pageSize = page_size

        return self.post(ctx, self.urls.guanjia_new, domain_name=domain_name, api=api_name, json=to_raw_type(req),
                         extra_cookies=extra_cookies, print_res=print_res)

    def fetch_guanjia_openid(self, print_warning=True):
        # 检查当前是否管家活动在生效中
        enabled_payed_act_funcs = [func for name, func in self.payed_activities()]
        if not self.guanjia in enabled_payed_act_funcs and not self.guanjia_new in enabled_payed_act_funcs:
            logger.debug("管家活动当前未生效，无需尝试更新p_skey")
            return

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

        cached_guanjia_login_result = self.load_guanjia_login_result()
        need_update = cached_guanjia_login_result is None or self.is_guanjia_openid_expired(cached_guanjia_login_result) or cached_guanjia_login_result.guanjia_skey_version != guanjia_skey_version

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
            self.save_guanjia_login_result(lr)
        else:
            lr = cached_guanjia_login_result

        return lr

    def is_guanjia_openid_expired(self, cached_guanjia_login_result: LoginResult):
        if cached_guanjia_login_result is None:
            return True

        self.guanjia_lr = cached_guanjia_login_result

        # {"code": 7005, "msg": "获取accToken失败", "result": []}
        # {"code": 29, "msg": "请求包参数错误", "result": []}
        res = self.guanjia_common_gifts_op("每日签到任务", giftId=self.guanjia_gift_id_sign_in, print_res=False)
        return res["code"] in [7005, 29]

    def save_guanjia_login_result(self, lr: LoginResult):
        # 本地缓存
        lr.guanjia_skey_version = guanjia_skey_version
        lr.save_to_json_file(self.get_local_saved_guanjia_openid_file())
        logger.debug(f"本地保存管家openid信息，具体内容如下：{lr}")

    def load_guanjia_login_result(self) -> Optional[LoginResult]:
        # 仅二维码登录和自动登录模式需要尝试在本地获取缓存的信息
        if self.cfg.login_mode not in ["qr_login", "auto_login"]:
            return None

        # 若未有缓存文件，则跳过
        if not os.path.isfile(self.get_local_saved_guanjia_openid_file()):
            return None

        with open(self.get_local_saved_guanjia_openid_file(), "r", encoding="utf-8") as f:
            raw_loginResult = json.load(f)
            loginResult = LoginResult().auto_update_config(raw_loginResult)
            logger.debug(f"读取本地缓存的管家openid信息，具体内容如下：{loginResult}")
            return loginResult

    def get_local_saved_guanjia_openid_file(self):
        return self.local_saved_guanjia_openid_file.format(self.cfg.name)

    # --------------------------------------------hello语音奖励兑换--------------------------------------------
    @try_except()
    def hello_voice(self):
        # https://dnf.qq.com/cp/a20210312hello/index.html  （从hello语音app中兑换奖励页点开网页）
        show_head_line("hello语音奖励兑换功能（仅兑换，不包含获取奖励的逻辑）")
        self.show_amesvr_act_info(self.hello_voice_op)

        if not self.cfg.function_switches.get_hello_voice or self.disable_most_activities():
            logger.warning("未启用hello语音奖励兑换功能，将跳过")
            return

        if self.cfg.hello_voice.hello_id == "":
            logger.warning("未配置hello_id，若需要该功能，请前往配置文件查看说明并添加该配置")
            return

        self.check_hello_voice()

        def query_coin():
            res = self.hello_voice_op("hello贝查询", "747516", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue1)

        def query_ticket():
            res = self.hello_voice_op("兑换券查询", "747515", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            ticket = 0
            for idx in range(1, 7 + 1):
                ticket += int(getattr(raw_info, f"sOutValue{idx}"))

            return ticket

        # ------ 专属福利区 ------
        # Hello见面礼
        self.hello_voice_op("hello见面礼包", "749289")
        # hello专属周礼包
        self.hello_voice_op("hello专属周礼包", "749297")
        # hello专属月礼包
        self.hello_voice_op("hello专属月礼包", "749301")
        # hello专属特权礼包
        self.hello_voice_op("hello专属特权礼包", "750502", "1539248")

        # ------ Hello贝兑换区 ------
        # Hello贝兑换
        logger.info(color("bold_green") + "下面Hello贝可兑换的内容已写死，如需调整，请自行修改源码")
        # self.hello_voice_op("神秘契约礼盒(1天)(150Hello贝)(日限1)", "750307", "1539249")
        # self.hello_voice_op("闪亮的雷米援助礼盒(5个)(150Hello贝)(日限1)", "750307", "1539250")
        # self.hello_voice_op("远古精灵的超级秘药(150Hello贝)(日限1)", "750307", "1539252")
        # self.hello_voice_op("本职业符文神秘礼盒(高级~稀有)(600Hello贝)(周限1)", "750499", "1539253")
        self.hello_voice_op("黑钻3天(550Hello贝)(周限1)", "750499", "1539254")
        self.hello_voice_op("抗疲劳秘药(5点)(300Hello贝)(周限1)", "750499", "1539256")
        self.hello_voice_op("装备提升礼盒*5(800Hello贝)(月限1)", "750500", "1539257")
        self.hello_voice_op("时间引导石*20(550Hello贝)(月限1)", "750500", "1539258")
        # self.hello_voice_op("升级券(lv50~99)(2000Hello贝)(月限1)", "750500", "1539259")

        # 活动奖励兑换
        self.hello_voice_op("时间引导石*20(日限1)", "750352", "1539260")
        self.hello_voice_op("神秘契约礼盒(1天)(日限1)", "750352", "1539263")
        self.hello_voice_op("黑钻3天(周限1)", "750501", "1539262")
        self.hello_voice_op("神器守护珠神秘礼盒(周限1)", "750501", "1539273")
        self.hello_voice_op("装备提升礼盒*5(月限1)", "750502", "1539274")
        self.hello_voice_op("升级券(Lv50~99)(月限1)", "750502", "1539275")

        # 打印最新信息
        logger.info(color("bold_yellow") + f"Hello贝：{query_coin()}    兑换券：{query_ticket()}")

        logger.info(color("bold_cyan") + "小助手只进行hello语音的奖励领取流程，具体活动任务的完成请手动完成或者使用autojs脚本来实现自动化嗷")

    def check_hello_voice(self):
        self.check_bind_account("hello语音奖励兑换", "https://dnf.qq.com/cp/a20210312hello/index.html",
                                activity_op_func=self.hello_voice_op, query_bind_flowid="748063", commit_bind_flowid="748062")

    def hello_voice_op(self, ctx, iFlowId, prize="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_hello_voice

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210312hello/",
                                   hello_id=self.cfg.hello_voice.hello_id, prize=prize,
                                   **extra_params)

    # --------------------------------------------DNF格斗大赛--------------------------------------------
    @try_except()
    def dnf_pk(self):
        # https://dnf.qq.com/cp/a20210405pk/
        show_head_line("DNF格斗大赛功能")
        self.show_amesvr_act_info(self.dnf_pk_op)

        if not self.cfg.function_switches.get_dnf_pk or self.disable_most_activities():
            logger.warning("未启用DNF格斗大赛功能，将跳过")
            return

        self.check_dnf_pk()

        def query_ticket_count():
            res = self.dnf_pk_op("查询数据", "752272", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue3)

        self.dnf_pk_op("每日在线30分钟（827960）", "752270")
        self.dnf_pk_op("每日PK（828682）", "752644")
        self.dnf_pk_op("每日特权网吧登陆（828687）", "752650")

        ticket = query_ticket_count()
        logger.info(color("bold_cyan") + f"当前剩余抽奖券数目为：{ticket}")
        for idx in range_from_one(ticket):
            self.dnf_pk_op(f"[{idx}/{ticket}]幸运夺宝", "752651")
            if idx != ticket:
                time.sleep(5)

        self.dnf_pk_op("海选普发奖励（828715）", "752679")
        self.dnf_pk_op("决赛普发奖励（830335）", "753784")
        self.dnf_pk_op("周赛晋级奖励（828689）", "752652")
        self.dnf_pk_op("决赛冠军奖励（828714）", "752678")

    def check_dnf_pk(self):
        self.check_bind_account("DNF格斗大赛", "https://dnf.qq.com/cp/a20210405pk/",
                                activity_op_func=self.dnf_pk_op, query_bind_flowid="752161", commit_bind_flowid="752160")

    def dnf_pk_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_pk

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210405pk/",
                                   **extra_params)

    # --------------------------------------------DNF强者之路--------------------------------------------
    @try_except()
    def dnf_strong(self):
        # https://dnf.qq.com/cp/a20210312Strong/index.html
        show_head_line("DNF强者之路功能")
        self.show_amesvr_act_info(self.dnf_strong_op)

        if not self.cfg.function_switches.get_dnf_strong or self.disable_most_activities():
            logger.warning("未启用DNF强者之路功能，将跳过")
            return

        self.check_dnf_strong()

        def query_ticket_count():
            res = self.dnf_strong_op("查询数据", "747206", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            return int(raw_info.sOutValue2)

        self.dnf_strong_op("领取报名礼包", "747207")
        self.dnf_strong_op("领取排行礼包", "747208")

        self.dnf_strong_op("每日在线30分钟", "747222")
        self.dnf_strong_op("通关一次强者之路 （试炼模式）", "747227")
        self.dnf_strong_op("每日特权网吧登陆", "747228")

        ticket = query_ticket_count()
        logger.info(color("bold_cyan") + f"当前剩余抽奖券数目为：{ticket}")
        for idx in range_from_one(ticket):
            self.dnf_strong_op(f"[{idx}/{ticket}]幸运夺宝", "747209")
            if idx != ticket:
                time.sleep(5)

        self.dnf_strong_op("决赛普发礼包", "761894")
        self.dnf_strong_op("决赛冠军礼包", "761893")

    def check_dnf_strong(self):
        self.check_bind_account("DNF强者之路", "http://dnf.qq.com/cp/a20210312strong/",
                                activity_op_func=self.dnf_strong_op, query_bind_flowid="747146", commit_bind_flowid="747145")

    def dnf_strong_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_strong

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210312strong/",
                                   **extra_params)

    # --------------------------------------------DNF心悦51--------------------------------------------
    @try_except()
    def dnf_xinyue_51(self):
        # https://xinyue.qq.com/act/a20210413ldjm/index_zs.html
        show_head_line("DNF心悦51")
        self.show_amesvr_act_info(self.dnf_xinyue_51_op)

        if not self.cfg.function_switches.get_dnf_xinyue_51 or self.disable_most_activities():
            logger.warning("未启用领取DNF心悦51活动合集功能，将跳过")
            return

        self.check_dnf_xinyue_51()

        self.dnf_xinyue_51_op("查询信息", "756145")

        xinyue_info = self.query_xinyue_info("查询心悦信息", print_res=False)
        if xinyue_info.xytype < 5:
            self.dnf_xinyue_51_op("特邀充值礼", "756071")
        else:
            self.dnf_xinyue_51_op("VIP充值礼", "756146", cz=xinyue_info.xytype)

        self.dnf_xinyue_51_op("抽奖", "756160")

        self.dnf_xinyue_51_op("全员礼包1", "756175")
        self.dnf_xinyue_51_op("全员礼包2", "756183")
        self.dnf_xinyue_51_op("全员礼包3", "756184")

        logger.info("可以用260/220去兑换一个宠物，有兴趣的可以自行去心悦app兑换")
        # self.dnf_xinyue_51_op("特邀兑换", "756195")
        # self.dnf_xinyue_51_op("VIP兑换", "756196")

        self.dnf_xinyue_51_op("签到", "756204")
        self.dnf_xinyue_51_op("累计签到礼-3天", "756207", qd="3")
        time.sleep(5)
        self.dnf_xinyue_51_op("累计签到礼-7天", "756207", qd="7")
        time.sleep(5)
        self.dnf_xinyue_51_op("累计签到礼-10天", "756207", qd="10")
        time.sleep(5)
        self.dnf_xinyue_51_op("累计签到礼-15天", "756207", qd="15")
        time.sleep(5)
        self.dnf_xinyue_51_op("累计签到礼-21天", "756207", qd="21")

        # self.dnf_xinyue_51_op("app专属礼", "756223")
        logger.warning(color("fg_bold_cyan") + "不要忘记前往app领取一次性礼包")

    def check_dnf_xinyue_51(self):
        self.check_bind_account("DNF心悦51", "https://xinyue.qq.com/act/a20210413ldjm/index_zs.html",
                                activity_op_func=self.dnf_xinyue_51_op, query_bind_flowid="756075", commit_bind_flowid="756074")

    def dnf_xinyue_51_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_xinyue_51

        return self.amesvr_request(ctx, "act.game.qq.com", "xinyue", "tgclub", iActivityId, iFlowId, print_res, "http://xinyue.qq.com/act/a20210413ldjm/index_zs.html",
                                   **extra_params)

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

        # note: 这里面的奖励都需要先登陆过游戏才可以领取

        # note: 新版本一定要记得刷新这个版本号~（不刷似乎也行- -）
        db = WelfareDB().with_context("v3").load()
        account_db = WelfareDB().with_context(f"v3/{self.cfg.name}").load()

        def exchange_package(sContent: str):
            # 检查是否已经兑换过
            if sContent in account_db.exchanged_dict:
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
            def callback(val: WelfareDB):
                val.exchanged_dict[sContent] = True

            account_db.update(callback)

            try:
                shareCode = res["modRet"]["jData"]["shareCode"]
                if shareCode != "":
                    def callback(val: WelfareDB):
                        if shareCode not in val.share_code_list:
                            val.share_code_list.append(shareCode)

                    db.update(callback)
            except Exception as e:
                pass

        @try_except(return_val_on_except="19", show_exception_info=False)
        def query_siActivityId():
            res = self.dnf_welfare_op(f"查询我的分享码状态", "649261", print_res=False)
            return res["modRet"]["jData"]["siActivityId"]

        # 正式逻辑
        shareCodeList = db.share_code_list

        sContents = [
            "DNF520",
            "DNF1314",
        ]
        random.shuffle(sContents)
        sContents = [*shareCodeList, *sContents]
        for sContent in sContents:
            exchange_package(sContent)

        # 登陆游戏领福利
        self.dnf_welfare_login_gifts_op("第一个 2020.06.17 - 2020.06.19 登录游戏", "773403")
        self.dnf_welfare_login_gifts_op("第二个 2020.06.20 - 2020.06.23 登录游戏", "773404")
        self.dnf_welfare_login_gifts_op("第三个 2020.06.24 - 2021.06.30 登录游戏", "773405")

        # 分享礼包
        self.dnf_welfare_login_gifts_op("分享奖励领取", "773406", siActivityId=query_siActivityId())

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

        db = DianzanDB().load()
        account_db = DianzanDB().with_context(self.cfg.name).load()

        # 投票
        def today_dianzan():
            today = get_today()

            if today not in account_db.day_to_dianzan_count:
                account_db.day_to_dianzan_count[today] = 0

            dianzanSuccessCount = account_db.day_to_dianzan_count[today]
            if dianzanSuccessCount >= 20:
                logger.info("今日之前的运行中，已经完成20次点赞了，本次将不执行")
                return

            for contentId in get_dianzan_contents_with_cache():
                # 不论投票是否成功，都标记为使用过的内容
                account_db.used_content_ids.append(contentId)
                if dianzan(dianzanSuccessCount + 1, contentId):
                    dianzanSuccessCount += 1
                    if dianzanSuccessCount >= 20:
                        logger.info("今日已经累计点赞20个，将停止点赞")
                        break

            account_db.day_to_dianzan_count[today] = dianzanSuccessCount

            account_db.save()

        def get_dianzan_contents_with_cache():
            usedContentIds = account_db.used_content_ids

            def filter_used_contents(contentIds):
                validContentIds = []
                for contentId in contentIds:
                    if contentId not in usedContentIds:
                        validContentIds.append(contentId)

                logger.info(validContentIds)

                return validContentIds

            contentIds = db.content_ids

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

            def _update_db(var: DianzanDB):
                var.content_ids = contentIds

            db.update(_update_db)

            return contentIds

        def getWorksData(iCategory2, page):
            ctx = f"查询点赞内容-{iCategory2}-{page}"
            res = self.get(ctx, self.urls.query_dianzan_contents, iCategory1=20, iCategory2=iCategory2, page=page, pagesize=10, is_jsonp=True, is_normal_jsonp=True)
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
        res = self.dnf_drift_op("查询基础信息", "726353", print_res=False)
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
        # https://dnf.qq.com/cp/a20210525care/index.html
        show_head_line("DNF马杰洛的规划")
        self.show_amesvr_act_info(self.majieluo_op)

        if not self.cfg.function_switches.get_majieluo or self.disable_most_activities():
            logger.warning("未启用领取DNF马杰洛的规划活动功能，将跳过")
            return

        self.check_majieluo()

        # 马杰洛的见面礼
        self.majieluo_op("验证是否幸运用户", "768204")
        self.majieluo_op("领取见面礼", "768190")

        # 马杰洛的特殊任务
        self.majieluo_op("登录游戏 石头*5", "768191")
        self.majieluo_op("通关副本 石头*5", "768193")
        for day in [7, 14, 21]:
            self.majieluo_op(f"连续完成任务一(登录游戏){day}次奖励", "768200", loginNum=str(day))

        logger.info(color("bold_cyan") + "深渊礼盒不能绑定固定人，所以请自行完成~")
        self.majieluo_op("累计赠送好友成功领取礼包", "770884")

        # 提取得福利
        stoneCount = self.query_stone_count()
        logger.warning(color("bold_yellow") + f"当前共有{stoneCount}个引导石")

        now = datetime.datetime.now()
        endTime = "20210616"

        takeStone = False
        takeStoneActId = "768194"
        maxStoneCount = 1500
        if stoneCount >= maxStoneCount:
            # 达到上限
            self.majieluo_op("提取时间引导石", takeStoneActId, giftNum=str(maxStoneCount // 100))
            takeStone = True
        elif get_today() == endTime:
            # 今天是活动最后一天
            self.majieluo_op("提取时间引导石", takeStoneActId, giftNum=str(stoneCount // 100))
            takeStone = True
        else:
            logger.info(f"当前未到最后领取期限（活动结束时-{endTime} 23:59:59），且石头数目({stoneCount})不足{maxStoneCount}，故不尝试提取")

        if takeStone:
            self.majieluo_op("提取福利", "768196")
            self.majieluo_op("分享得好礼", "769008")

    @try_except(return_val_on_except=0, show_exception_info=False)
    def query_stone_count(self):
        res = self.majieluo_op("查询当前时间引导石数量", "768197", print_res=False)
        info = parse_amesvr_common_info(res)
        return int(info.sOutValue1)

    def check_majieluo(self):
        self.check_bind_account("DNF马杰洛的规划", "https://dnf.qq.com/cp/a20210525care/index.html",
                                activity_op_func=self.majieluo_op, query_bind_flowid="768187", commit_bind_flowid="768186")

    def majieluo_op(self, ctx, iFlowId, cardType="", inviteId="", sendName="", receiveUin="", receiver="", receiverName="", receiverUrl="", giftNum="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_majieluo

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/cp/a20210525care/",
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

    # --------------------------------------------qq视频-AME活动--------------------------------------------
    @try_except()
    def qq_video_amesvr(self):
        # https://dnf.qq.com/cp/a20210519video/index.html
        show_head_line("qq视频-AME活动")
        self.show_amesvr_act_info(self.qq_video_amesvr_op)

        if not self.cfg.function_switches.get_qq_video_amesvr or self.disable_most_activities():
            logger.warning("未启用领取qq视频-AME活动活动合集功能，将跳过")
            return

        self.check_qq_video_amesvr()

        def query_signin_days():
            res = self.qq_video_amesvr_op("查询签到状态", "767552", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue3)

        self.qq_video_amesvr_op("验证幸运用户", "767315")
        self.qq_video_amesvr_op("幸运用户礼包", "766796")
        self.qq_video_amesvr_op("勇士见面礼包", "767594")
        self.qq_video_amesvr_op("分享领取", "767168")

        self.qq_video_amesvr_op("在线30分钟礼包", "766800")
        logger.warning(color("bold_yellow") + f"累计已签到{query_signin_days()}天")
        self.qq_video_amesvr_op("签到3天礼包", "766801")
        self.qq_video_amesvr_op("签到7天礼包", "766804")
        self.qq_video_amesvr_op("签到10天礼包", "768009")
        self.qq_video_amesvr_op("签到15天礼包", "766817")
        self.qq_video_amesvr_op("签到21天礼包", "766818")

    def check_qq_video_amesvr(self):
        self.check_bind_account("qq视频-AME活动", "https://dnf.qq.com/cp/a20210519video/index.html",
                                activity_op_func=self.qq_video_amesvr_op, query_bind_flowid="766781", commit_bind_flowid="766780")

    def qq_video_amesvr_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_qq_video_amesvr

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210519video/",
                                   **extra_params)

    # --------------------------------------------dnf论坛签到--------------------------------------------
    @try_except()
    def dnf_bbs(self):
        # https://dnf.gamebbs.qq.com/plugin.php?id=k_misign:sign
        show_head_line("dnf官方论坛签到")
        self.show_amesvr_act_info(self.dnf_bbs_op)

        if not self.cfg.function_switches.get_dnf_bbs_signin or self.disable_most_activities():
            logger.warning("未启用领取dnf官方论坛签到活动合集功能，将跳过")
            return

        if self.cfg.dnf_bbs_cookie == "" or self.cfg.dnf_bbs_formhash == "":
            logger.warning("未配置dnf官方论坛的cookie或formhash，将跳过（dnf官方论坛相关的配置会配置就配置，不会就不要配置，我不会回答关于这俩如何获取的问题）")
            return

        self.check_dnf_bbs()
        self.check_dnf_bbs_dup()

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

                    res = requests.post(url, headers=headers, timeout=10)
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
            res = self.dnf_bbs_dup_op("查询代币券", "774036", print_res=False)
            info = parse_amesvr_common_info(res)
            return int(info.sOutValue1)

        # 可能有多个活动并行
        # https://dnf.qq.com/act/a20210420act/index.html
        # https://dnf.qq.com/act/a20210611act/index.html
        def query_remaining_quota():
            res = self.dnf_bbs_op("查询礼包剩余量", "758279", print_res=False)
            info = parse_amesvr_common_info(res)

            logger.info('\n'.join([
                "当前礼包全局剩余量如下",
                f"\t装备提升礼盒: {info.sOutValue1}",
                f"\t抗疲劳秘药: {info.sOutValue2}",
                f"\t时间引导石礼盒: {info.sOutValue3}",
                f"\t暗魂水晶礼盒: {info.sOutValue4}",
                f"\t华丽的徽章自选礼盒: {info.sOutValue5}",
                f"\t灿烂的徽章自选礼盒: {info.sOutValue6}",
            ]))

            res = self.dnf_bbs_dup_op("查询礼包剩余量 1-8", "774037", print_res=False)
            info = parse_amesvr_common_info(res)
            res = self.dnf_bbs_dup_op("查询礼包剩余量 9-10", "774235", print_res=False)
            info_2 = parse_amesvr_common_info(res)

            logger.info('\n'.join([
                "当前礼包全局剩余量如下",
                f"\t抗疲劳秘药 (10点): {info.sOutValue1}",
                f"\t宠物饲料礼袋 (20个): {info.sOutValue2}",
                f"\t一次性继承装置: {info.sOutValue3}",
                f"\t装备提升礼盒: {info.sOutValue4}",
                f"\t华丽的徽章神秘礼盒: {info.sOutValue5}",
                f"\t胜 · 深渊之鳞武器自选礼盒: {info.sOutValue6}",
                f"\tLv100传说装备自选礼盒: {info.sOutValue7}",
                f"\t+10 装备强化券: {info.sOutValue8}",
                f"\t灿烂的徽章神秘礼盒: {info_2.sOutValue1}",
                f"\t灿烂的徽章自选礼盒: {info_2.sOutValue2}",
            ]))

        def try_exchange():
            operations = [
                (self.dnf_bbs_dup_op, "灿烂的徽章自选礼盒【50代币券】", "774055", 1),
                (self.dnf_bbs_op, "灿烂的徽章自选礼盒<官方论坛活动>【100代币券】", "758258", 1),
                (self.dnf_bbs_dup_op, "+10 装备强化券【25代币券】", "774053", 1),
                (self.dnf_bbs_dup_op, "装备提升礼盒【2代币券】", "774049", 5),
                (self.dnf_bbs_op, "装备提升礼盒<官方论坛活动>【2代币券】", "758113", 5),
                (self.dnf_bbs_dup_op, "一次性继承装置【2代币券】", "774048", 5),
                (self.dnf_bbs_dup_op, "宠物饲料礼袋 (20个)【2代币券】", "774047", 2),
                (self.dnf_bbs_dup_op, "灿烂的徽章神秘礼盒【25代币券】", "774054", 1),
                (self.dnf_bbs_dup_op, "胜 · 深渊之鳞武器自选礼盒【12代币券】", "774051", 1),
                (self.dnf_bbs_dup_op, "Lv100传说装备自选礼盒【12代币券】", "774052", 1),
                (self.dnf_bbs_dup_op, "华丽的徽章神秘礼盒【12代币券】", "774050", 2),
                (self.dnf_bbs_dup_op, "抗疲劳秘药 (10点)【5代币券】", "774033", 5),
                (self.dnf_bbs_op, "抗疲劳秘药 (20点)<官方论坛活动>【20代币券】", "758253", 1),
                (self.dnf_bbs_op, "华丽的徽章自选礼盒<官方论坛活动>【25代币券】", "758257", 1),
                (self.dnf_bbs_op, "[期限]时间引导石礼盒 (10个)<官方论坛活动>【5代币券】", "758254", 2),
                (self.dnf_bbs_op, "暗魂水晶礼盒 (100个)<官方论坛活动>【15代币券】", "758255", 2),
            ]

            for op_func, name, flowid, count in operations:
                print(op_func, name, flowid, count)

                for i in range(count):
                    res = op_func(name, flowid)
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
        query_remaining_quota()
        try_exchange()

        after_exchange_dbq = query_dbq()
        logger.warning(color("bold_yellow") + f"账号 {self.cfg.name} 本次论坛签到获得 {after_sign_dbq - old_dbq} 个代币券，兑换道具消耗了 {after_exchange_dbq - after_sign_dbq} 个代币券，余额：{old_dbq} => {after_exchange_dbq}")

    def check_dnf_bbs(self):
        self.check_bind_account("DNF论坛积分兑换活动", "https://dnf.qq.com/act/a20210420act/index.html",
                                activity_op_func=self.dnf_bbs_op, query_bind_flowid="758117", commit_bind_flowid="758116")

    def dnf_bbs_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_bbs

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/act/a20210420act/",
                                   **extra_params)

    def check_dnf_bbs_dup(self):
        self.check_bind_account("DNF论坛积分兑换活动", "https://dnf.qq.com/act/a20210611act/index.html",
                                activity_op_func=self.dnf_bbs_dup_op, query_bind_flowid="774035", commit_bind_flowid="774034")

    def dnf_bbs_dup_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_bbs_dup

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/act/a20210611act/",
                                   **extra_params)

    # --------------------------------------------colg每日签到--------------------------------------------
    @try_except()
    def colg_signin(self):
        # https://bbs.colg.cn/forum-171-1.html
        show_head_line("colg每日签到")
        self.show_not_ams_act_info("colg每日签到")

        if not self.cfg.function_switches.get_colg_signin or self.disable_most_activities():
            logger.warning("未启用colg每日签到功能，将跳过")
            return

        if self.cfg.colg_cookie == "":
            logger.warning("未配置colg的cookie，将跳过（colg相关的配置会配置就配置，不会就不要配置，我不会回答关于这玩意如何获取的问题）")
            return

        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,en-GB;q=0.6,ja;q=0.5",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://bbs.colg.cn",
            "referer": "https://bbs.colg.cn/forum-171-1.html",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
            "cookie": self.cfg.colg_cookie,
        }

        session = requests.session()
        session.headers = headers

        def query_info() -> ColgBattlePassInfo:
            res = session.get(self.urls.colg_url, timeout=10)
            html = res.text

            activity_id = extract_between(html, "var activity_id = '", "';", str)
            lv_score = extract_between(html, "var lvScore = ", ";", int)
            tasks = json.loads(extract_between(html, "var tasks = ", ";", str))['list']
            rewards = json.loads(extract_between(html, "var rewardListData = ", ";", str))

            info = ColgBattlePassInfo().auto_update_config({
                'activity_id': activity_id,
                'lv_score': lv_score,
                'tasks': tasks,
                'rewards': rewards,
            })

            return info

        info = query_info()

        for task in info.tasks:
            if not task.status:
                logger.info(f"任务 {task.task_name} 暂未开始，将跳过")
                continue

            if not task.is_finish:
                if task.sub_type == "1":
                    # 如果是签到任务，额外签到
                    signin_res = session.post(self.urls.colg_sign_in_url, data=f"task_id={task.id}", timeout=10)
                    logger.info(color("bold_green") + f"colg每日签到 {signin_res.json()}")
                    task.is_finish = True
                else:
                    # 如果任务未完成，则跳过
                    logger.warning(f"任务 {task.task_name} 条件尚未完成，请自行前往colg进行完成")
                    continue

            # 如果任务已领取，则跳过
            if task.is_get:
                logger.info(f"任务 {task.task_name} 的 积分奖励({task.task_reward}) 已经领取过，将跳过")
                continue

            # 尝试领取任务奖励
            res = session.get(self.urls.colg_take_sign_in_credits.format(aid=info.activity_id, task_id=task.id), timeout=10)
            logger.info(color("bold_green") + f"领取 {task.task_name} 的 积分奖励({task.task_reward})， 结果={res.json()}")

        info = query_info()
        untaken_awards = info.untaken_rewards()
        msg = f"Colg活跃值已经达到{info.lv_score}了咯"
        if len(untaken_awards) > 0:
            msg += f"，目前有以下奖励可以领取，记得去Colg领取哦\n{untaken_awards}"
        else:
            msg += "，目前暂无未领取的奖励"
        logger.info(color("bold_green") + msg)

        if len(untaken_awards) > 0 and is_weekly_first_run("colg_领取奖励_每周提醒"):
            async_message_box(msg, "可以领奖励啦", open_url="https://bbs.colg.cn/forum-171-1.html", print_log=False)

        logger.info(color("bold_cyan") + "除签到外的任务条件，以及各个奖励的领取，请自己前往colg进行嗷")

        logger.info(color("bold_cyan") + "colg社区活跃任务右侧有个【前往商城】，请自行完成相关活动后点进去自行兑换奖品")

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

    # --------------------------------------------DNF落地页活动--------------------------------------------
    @try_except()
    def dnf_luodiye(self):
        # https://dnf.qq.com/cp/a20210618index/
        show_head_line("DNF落地页活动")
        self.show_amesvr_act_info(self.dnf_luodiye_op)

        if not self.cfg.function_switches.get_dnf_luodiye or self.disable_most_activities():
            logger.warning("未启用领取DNF落地页活动功能，将跳过")
            return

        self.check_dnf_luodiye()

        self.dnf_luodiye_op("登陆领取积分", "770771")
        if not self.cfg.function_switches.disable_share and is_first_run(f"dnf_luodiye_分享_{self.uin()}"):
            self.dnf_luodiye_op("分享", "770783", iReceiveUin=self.qq(), p_skey=self.fetch_share_p_skey("领取分享奖励"))
        self.dnf_luodiye_op("登陆活动页送积分", "770812")

        for i in range(4):
            res = self.dnf_luodiye_op("领取自选道具-装备提升礼盒*2", "770042", itemIndex="8")
            if int(res["ret"]) != 0:
                break
            time.sleep(1)

    def check_dnf_luodiye(self):
        self.check_bind_account("DNF落地页活动", "https://dnf.qq.com/cp/a20210618index/",
                                activity_op_func=self.dnf_luodiye_op, query_bind_flowid="769490", commit_bind_flowid="769489")

    def dnf_luodiye_op(self, ctx, iFlowId, p_skey="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_luodiye

        # roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        # checkInfo = self.get_dnf_roleinfo()
        #
        # checkparam = quote_plus(quote_plus(checkInfo.checkparam))

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/cp/a20210618index/",
                                   # sArea=roleinfo.serviceID, sPartition=roleinfo.serviceID, sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
                                   # sRoleId=roleinfo.roleCode, sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
                                   # md5str=checkInfo.md5str, ams_checkparam=checkparam, checkparam=checkparam,
                                   **extra_params,
                                   extra_cookies=f"p_skey={p_skey}"
                                   )

    # --------------------------------------------WeGame活动--------------------------------------------
    @try_except()
    def dnf_wegame(self):
        # https://dnf.qq.com/lbact/a20210708WG/index.html
        show_head_line("WeGame活动")
        self.show_amesvr_act_info(self.dnf_wegame_op)

        if not self.cfg.function_switches.get_dnf_wegame or self.disable_most_activities():
            logger.warning("未启用领取WeGame活动功能，将跳过")
            return

        self.check_dnf_wegame()

        # def query_signin_days():
        #     res = self.dnf_wegame_op("查询签到天数-condOutput", "770457", print_res=False)
        #     return self.parse_condOutput(res, "e0c747b4b51392caf0c99162e69125d8")

        def query_lottery_times():
            res = self.dnf_wegame_op("查询抽奖次数-jifenOutput", "779714", print_res=False)
            return self.parse_jifenOutput(res, "332")

        def query_signin_lottery_times():
            res = self.dnf_wegame_op("查询抽奖次数-jifenOutput", "779714", print_res=False)
            return self.parse_jifenOutput(res, "333")

        # 阿拉德盲盒限时抽
        self.dnf_wegame_op("分享获得盲盒", "779703")
        self.dnf_wegame_op("页面签到获得盲盒", "779700")
        self.dnf_wegame_op("在线30min获得盲盒", "779701")
        totalLotteryTimes, remainingLotteryTimes = query_lottery_times()
        logger.info(color("bold_yellow") + f"累计获得{totalLotteryTimes}次抽奖次数，目前剩余{remainingLotteryTimes}次抽奖次数")
        for i in range(remainingLotteryTimes):
            self.dnf_wegame_op(f"第{i + 1}次盲盒抽奖-4礼包抽奖", "779692")

        # 升级
        self.dnf_wegame_op("创角礼包", "780919")
        self.dnf_wegame_op("升级礼包-1-50级", "780920")
        self.dnf_wegame_op("升级礼包-51-75级", "780921")
        self.dnf_wegame_op("升级礼包-76-99", "780922")
        self.dnf_wegame_op("满级礼包-100级", "780923")

        # 勇士齐聚阿拉德
        check_in_flow_id = "779702"
        self.dnf_wegame_op("在线30min签到", check_in_flow_id)
        self.dnf_wegame_op("领取签到礼包", check_in_flow_id)

        totalLotteryTimes, remainingLotteryTimes = query_signin_lottery_times()
        logger.info(color("bold_yellow") + f"累计获得{totalLotteryTimes}次签到抽奖次数，目前剩余{remainingLotteryTimes}次抽奖次数")
        for i in range(remainingLotteryTimes):
            self.dnf_wegame_op(f"第{i + 1}次签到抽奖", "779699")

        # logger.info(color("bold_yellow") + f"目前已累计签到{query_signin_days()}天")
        # self.dnf_wegame_op("签到3天礼包", "770437")
        # self.dnf_wegame_op("签到7天礼包", "770438")
        # self.dnf_wegame_op("签到10天礼包", "771272")
        # self.dnf_wegame_op("签到15天礼包", "770439")

        self.dnf_wegame_op("每日抽奖", "779699")

    def check_dnf_wegame(self):
        self.check_bind_account("WeGame活动", "https://dnf.qq.com/lbact/a20210708WG/index.html",
                                activity_op_func=self.dnf_wegame_op, query_bind_flowid="779689", commit_bind_flowid="779688")

    def dnf_wegame_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_wegame
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/lbact/a20210708WG/",
                                   **extra_params)

    # --------------------------------------------WeGame活动--------------------------------------------
    @try_except()
    def dnf_wegame_dup(self):
        # https://dnf.qq.com/lbact/a20210617lbw4msr/index.html
        show_head_line("WeGame活动")
        self.show_amesvr_act_info(self.dnf_wegame_dup_op)

        if not self.cfg.function_switches.get_dnf_wegame or self.disable_most_activities():
            logger.warning("未启用领取WeGame活动功能，将跳过")
            return

        self.check_dnf_wegame_dup()

        def query_signin_days():
            res = self.dnf_wegame_dup_op("查询签到天数-condOutput", "772148", print_res=False)
            info = parse_amesvr_common_info(res)
            # "sOutValue1": "e0c747b4b51392caf0c99162e69125d8:iRet:0|b1ecb3ecd311175835723e484f2d8d88:iRet:0",
            parts = info.sOutValue1.split('|')[0].split(':')
            days = int(parts[2])
            return days

        def query_lottery_times(count_id: int):
            res = self.dnf_wegame_dup_op("查询抽奖次数-jifenOutput", "774234", print_res=False)
            info = parse_amesvr_common_info(res)
            # "sOutValue1": "239:16:4|240:8:1",
            for count_info in info.sOutValue1.split('|'):
                cid, total, remaining = count_info.split(':')
                if int(cid) == count_id:
                    return int(total), int(remaining)

            return 0, 0

        self.dnf_wegame_dup_op("通关奥兹玛副本获得吹蜡烛次数", "772139")
        self.dnf_wegame_dup_op("页面签到获得吹蜡烛次数", "772140")
        self.dnf_wegame_dup_op("通关智慧的引导副本获得吹蜡烛次数", "772141")
        totalLotteryTimes, remainingLotteryTimes = query_lottery_times(326)
        logger.info(color("bold_yellow") + f"累计获得{totalLotteryTimes}次吹蜡烛次数，目前剩余{remainingLotteryTimes}次吹蜡烛次数")
        for i in range(remainingLotteryTimes):
            self.dnf_wegame_dup_op(f"第{i + 1}次吹蜡烛抽蛋糕-4礼包抽奖", "772128")

        # 升级
        self.dnf_wegame_dup_op("幸运勇士获得抽奖次数", "774231")
        self.dnf_wegame_dup_op("每日登录游戏获得抽奖", "774230")
        totalLotteryTimes, remainingLotteryTimes = query_lottery_times(327)
        logger.info(color("bold_yellow") + f"累计获得{totalLotteryTimes}次抽奖次数，目前剩余{remainingLotteryTimes}次抽奖次数")
        for i in range(remainingLotteryTimes):
            self.dnf_wegame_dup_op(f"第{i + 1}次每日抽奖", "774232")

        # 勇士齐聚阿拉德
        self.dnf_wegame_dup_op("在线30min签到", "772142")
        self.dnf_wegame_dup_op("领取签到礼包", "772142")
        logger.info(color("bold_yellow") + f"目前已累计签到{query_signin_days()}天")
        self.dnf_wegame_dup_op("签到3天礼包", "772131")
        self.dnf_wegame_dup_op("签到7天礼包", "772132")
        self.dnf_wegame_dup_op("签到10天礼包", "774229")
        self.dnf_wegame_dup_op("签到15天礼包", "772133")

    def check_dnf_wegame_dup(self):
        self.check_bind_account("WeGame活动", "https://dnf.qq.com/lbact/a20210617lbw4msr/index.html",
                                activity_op_func=self.dnf_wegame_dup_op, query_bind_flowid="772123", commit_bind_flowid="772122")

    def dnf_wegame_dup_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_wegame_dup
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/lbact/a20210617lbw4msr/",
                                   **extra_params)

    # --------------------------------------------我的dnf13周年活动--------------------------------------------
    @try_except()
    def dnf_my_story(self):
        # https://dnf.qq.com/cp/a20210604history/index.html
        show_head_line("我的dnf13周年活动")
        self.show_amesvr_act_info(self.dnf_my_story_op)

        if not self.cfg.function_switches.get_dnf_my_story or self.disable_most_activities():
            logger.warning("未启用领取我的dnf13周年活动功能，将跳过")
            return

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo

        self.dnf_my_story_op("查询历史回顾数据", "769681", sArea=roleinfo.serviceID, sRole=roleinfo.roleCode)
        self.dnf_my_story_op("领取奖励（854922）", "770900", sArea=roleinfo.serviceID, sRole=roleinfo.roleCode)

    def dnf_my_story_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_my_story
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/cp/a20210604history/",
                                   **extra_params)

    # --------------------------------------------刃影预约活动--------------------------------------------
    @try_except()
    def dnf_reserve(self):
        # https://dnf.qq.com/cp/a20210618reserve/index.html
        show_head_line("刃影预约活动")

        if not self.cfg.function_switches.get_dnf_reserve or self.disable_most_activities():
            logger.warning("未启用领取刃影预约活动功能，将跳过")
            return

        self.show_amesvr_act_info(self.dnf_reserve_op)

        self.dnf_reserve_op("预约领奖", "773111")

    def dnf_reserve_op(self, ctx, iFlowId, p_skey="", print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_reserve

        roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
        checkInfo = self.get_dnf_roleinfo()

        checkparam = quote_plus(quote_plus(checkInfo.checkparam))

        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/cp/a20210618reserve/index.html",
                                   sArea=roleinfo.serviceID, sPartition=roleinfo.serviceID, sAreaName=quote_plus(quote_plus(roleinfo.serviceName)),
                                   sRoleId=roleinfo.roleCode, sRoleName=quote_plus(quote_plus(roleinfo.roleName)),
                                   md5str=checkInfo.md5str, ams_checkparam=checkparam, checkparam=checkparam,
                                   **extra_params,
                                   extra_cookies=f"p_skey={p_skey}"
                                   )

    # --------------------------------------------DNF周年庆登录活动--------------------------------------------
    @try_except()
    def dnf_anniversary(self):
        # https://dnf.qq.com/cp/a20210618anniversary/index.html
        show_head_line("DNF周年庆登录活动")
        self.show_amesvr_act_info(self.dnf_anniversary_op)

        if now_in_range("2021-06-19 06:00:00", "2021-06-21 05:59:59") and is_daily_first_run("DNF周年庆登录活动_提示登录"):
            async_message_box("周年庆是否所有需要领奖励的号都已经登录了？如果没有的话，记得去一个个登录哦~", "周年庆登录")

        if self.disable_most_activities():
            logger.warning("未启用领取DNF周年庆登录活动功能，将跳过")
            return

        if not self.cfg.function_switches.get_dnf_anniversary:
            async_message_box((
                "为了保持仪式感，默认不领取DNF周年庆登录活动功能，将跳过，如需自动领取，请打开该开关~\n"
                "另外请不要忘记在2021年6月19日06:00~2021年6月21日05:59期间至少登录一次游戏，否则将无法领取奖励~"
            ), "周年庆提示", show_once=True)

            if now_in_range("2021-06-24 06:00:00", "2021-07-01 05:59:59") and is_daily_first_run("DNF周年庆登录活动_提示领奖"):
                async_message_box("今天是否去周年庆网页领奖了吗~，不要忘记哦~", "提示领奖", open_url="https://dnf.qq.com/cp/a20210618anniversary/index.html")

            return

        self.check_dnf_anniversary()

        gifts = [
            ("第一弹", "769503", "2021-06-24 16:00:00"),
            ("第二弹", "769700", "2021-06-25 00:00:00"),
            ("第三弹", "769718", "2021-06-26 00:00:00"),
            ("第四弹", "769719", "2021-06-27 00:00:00"),
        ]

        now = get_now()
        for name, flowid, can_take_time in gifts:
            if now >= parse_time(can_take_time):
                self.dnf_anniversary_op(name, flowid)
            else:
                logger.warning(f"当前未到{can_take_time}，无法领取{name}")

    def check_dnf_anniversary(self):
        self.check_bind_account("DNF周年庆登录活动", "https://dnf.qq.com/cp/a20210618anniversary/index.html",
                                activity_op_func=self.dnf_anniversary_op, query_bind_flowid="769502", commit_bind_flowid="769501")

    def dnf_anniversary_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_anniversary
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/cp/a20210618anniversary/",
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

            spring_fudai_pskey = self.fetch_share_p_skey("赠送福袋")

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

    # --------------------------------------------DNF集合站--------------------------------------------
    @try_except()
    def dnf_collection(self):
        # https://dnf.qq.com/lbact/a20210603lbniyox/index.html
        show_head_line("DNF集合站")
        self.show_amesvr_act_info(self.dnf_collection_op)

        if not self.cfg.function_switches.get_dnf_collection or self.disable_most_activities():
            logger.warning("未启用领取DNF集合站功能，将跳过")
            return

        self.check_dnf_collection()

        def query_signin_days():
            res = self.dnf_collection_op("查询", "769802", print_res=False)
            info = AmesvrSigninInfo().auto_update_config(res["modRet"])
            return int(info.total)

        self.dnf_collection_op("勇士礼包", "769796")
        self.dnf_collection_op("全民参与礼包", "769801")

        self.dnf_collection_op("30分签到礼包", "769798")
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {query_signin_days()} 天")
        self.dnf_collection_op("3日礼包", "769794")
        self.dnf_collection_op("7日礼包", "769799")
        self.dnf_collection_op("10日礼包", "769800")

    def check_dnf_collection(self):
        self.check_bind_account("DNF集合站", "https://dnf.qq.com/lbact/a20210603lbniyox/index.html",
                                activity_op_func=self.dnf_collection_op, query_bind_flowid="769791", commit_bind_flowid="769790")

    def dnf_collection_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_collection
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/lbact/a20210603lbniyox/",
                                   **extra_params)

    # --------------------------------------------DNF集合站--------------------------------------------
    @try_except()
    def dnf_collection_dup(self):
        # https://dnf.qq.com/lbact/a20210617lbpqopr/index.html
        show_head_line("DNF集合站")
        self.show_amesvr_act_info(self.dnf_collection_dup_op)

        if not self.cfg.function_switches.get_dnf_collection or self.disable_most_activities():
            logger.warning("未启用领取DNF集合站功能，将跳过")
            return

        self.check_dnf_collection_dup()

        def query_signin_days():
            res = self.dnf_collection_dup_op("查询", "773668", print_res=False)
            info = AmesvrSigninInfo().auto_update_config(res["modRet"])
            return int(info.total)

        self.dnf_collection_dup_op("勇士礼包", "773660")
        self.dnf_collection_dup_op("全民参与礼包", "773665")

        self.dnf_collection_dup_op("30分签到礼包", "773661")
        logger.info(color("fg_bold_cyan") + f"当前已累积签到 {query_signin_days()} 天")
        self.dnf_collection_dup_op("3日礼包", "773658")
        self.dnf_collection_dup_op("7日礼包", "773662")
        self.dnf_collection_dup_op("10日礼包", "773666")
        self.dnf_collection_dup_op("15日礼包", "773663")
        self.dnf_collection_dup_op("21日礼包", "773667")

    def check_dnf_collection_dup(self):
        self.check_bind_account("DNF集合站", "https://dnf.qq.com/lbact/a20210617lbpqopr/index.html",
                                activity_op_func=self.dnf_collection_dup_op, query_bind_flowid="773655", commit_bind_flowid="773654")

    def dnf_collection_dup_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_collection_dup
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/lbact/a20210617lbpqopr/",
                                   **extra_params)

    # --------------------------------------------KOL--------------------------------------------
    @try_except()
    def dnf_kol(self):
        # https://dnf.qq.com/lbact/a20210610kol/zzx.html
        show_head_line("KOL")
        self.show_amesvr_act_info(self.dnf_kol_op)

        if not self.cfg.function_switches.get_dnf_kol or self.disable_most_activities():
            logger.warning("未启用领取KOL功能，将跳过")
            return

        self.check_dnf_kol()

        def query_lottery_times():
            res = self.dnf_kol_op("jifenOutput", "776073", print_res=False)
            return self.parse_jifenOutput(res, "329")

        self.dnf_kol_op("点亮助力", "776067")
        self.dnf_kol_op("领取助力礼包", "776071")

        self.dnf_kol_op("分享计数", "776069")

        total, remaining = query_lottery_times()
        logger.info(f"当前剩余抽奖次数为{remaining}，累积获得{total}")
        for idx in range_from_one(remaining):
            self.dnf_kol_op(f"第{idx}次抽奖", "776070")

    def check_dnf_kol(self):
        self.check_bind_account("KOL", "https://dnf.qq.com/lbact/a20210610kol/zzx.html",
                                activity_op_func=self.dnf_kol_op, query_bind_flowid="776064", commit_bind_flowid="776063")

    def dnf_kol_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_kol
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "https://dnf.qq.com/lbact/a20210610kol/",
                                   **extra_params)

    # --------------------------------------------DNF福签大作战--------------------------------------------
    @try_except()
    def dnf_fuqian(self):
        # https://dnf.qq.com/cp/a20210325sjlbv3pc/index.html
        show_head_line("DNF福签大作战")
        self.show_amesvr_act_info(self.dnf_fuqian_op)

        if not self.cfg.function_switches.get_dnf_fuqian or self.disable_most_activities():
            logger.warning("未启用领取DNF福签大作战功能，将跳过")
            return

        self.check_dnf_fuqian()

        def query_info():
            res = self.dnf_fuqian_op("查询资格", "742112", print_res=False)
            raw_info = parse_amesvr_common_info(res)

            info = DnfCollectionInfo()
            info.has_init = raw_info.sOutValue2 != "0"
            info.send_total = int(raw_info.sOutValue3)
            info.total_page = math.ceil(info.send_total / 6)
            info.luckyCount = int(raw_info.sOutValue5)
            info.scoreCount = int(raw_info.sOutValue6)
            info.openLuckyCount = int(raw_info.sOutValue7)

            return info

        def take_invite_awards():
            act_info = search_act(self.urls.iActivityId_dnf_fuqian)
            is_last_day = False
            if act_info is not None and act_info.is_last_day():
                is_last_day = True

            if not is_last_day and not is_weekly_first_run(f"fuqian_take_invite_awards_{self.cfg.name}"):
                logger.warning("本周已运行过领取邀请奖励，暂不继续领取~")
                return

            info = query_info()
            for page in range(1, info.total_page + 1):
                res = self.dnf_fuqian_op(f"查询第{page}/{info.total_page}页邀请成功的列表", "744443", sendPage=str(page))
                data = res["modRet"]["jData"]
                logger.info(data["iTotal"])
                if data["iTotal"] > 0:
                    for invite_info in data["jData"]:
                        if invite_info["iGet"] == "0":
                            uin = invite_info["iUin2"]
                            iId = invite_info["iId"]
                            self.dnf_fuqian_op(f"领取第{page}页积分奖励-{uin}", "743861", iId=iId)
                else:
                    logger.info("没有更多已邀请好友了，将跳过~")
                    return

        # 正式逻辑如下

        info = query_info()
        if not info.has_init:
            self.dnf_fuqian_op("初次赠送一个福签积分", "742513")
        self.dnf_fuqian_op("随机抽一个福签", "742491")

        self.dnf_fuqian_op("幸运玩家礼包领取", "742315")

        for sCode in [
            "4f739a998cb44201484a8fa7d4e9eaed58e1576e312b70a2cbf17214e19a2ec0",
            "c79fd5c303d0d9a8421a427badae87fd58e1576e312b70a2cbf17214e19a2ec0",
            *self.common_cfg.scode_list_accept_give,
        ]:
            self.dnf_fuqian_op("接受福签赠送", "742846",
                               sCode=sCode,
                               sNickName=quote_plus(quote_plus(quote_plus("小号"))))
        for sCode in [
            "f3256878f5744a90d9efe0ee6f4d3c3158e1576e312b70a2cbf17214e19a2ec0",
            "f43f1d4d525f55ccd88ff03b60638e0058e1576e312b70a2cbf17214e19a2ec0",
            *self.common_cfg.scode_list_accept_ask,
        ]:
            self.dnf_fuqian_op("接受福签索要", "742927",
                               sCode=sCode)

        if len(self.cfg.spring_fudai_receiver_qq_list) != 0:
            share_pskey = self.fetch_share_p_skey("福签赠送")
            for qq in self.cfg.spring_fudai_receiver_qq_list:
                self.dnf_fuqian_op(f"福签赠送-{qq}", "742115", fuin=str(qq), extra_cookies=f"p_skey={share_pskey}")
                self.dnf_fuqian_op(f"福签索要-{qq}", "742824", fuin=str(qq), extra_cookies=f"p_skey={share_pskey}")
        else:
            logger.warning(color("bold_yellow") + f"未配置新春福袋大作战邀请列表, 将跳过赠送福签")

        take_invite_awards()

        self.dnf_fuqian_op("福签累计奖励1", "742728")
        self.dnf_fuqian_op("福签累计奖励2", "742732")
        self.dnf_fuqian_op("福签累计奖励3", "742733")
        self.dnf_fuqian_op("福签累计奖励4", "742734")
        self.dnf_fuqian_op("福签累计奖励5", "742735")
        self.dnf_fuqian_op("福签累计奖励6", "742736")
        self.dnf_fuqian_op("福签累计奖励7", "742737")
        self.dnf_fuqian_op("福签累计奖励20", "742738")

        info = query_info()
        logger.info(color("bold_cyan") + f"当前共有{info.scoreCount}个积分")
        for idx in range(info.scoreCount):
            self.dnf_fuqian_op(f"第{idx + 1}次积分夺宝并等待5秒", "742740")
            time.sleep(5)

        self.dnf_fuqian_op("分享奖励", "742742")

    def check_dnf_fuqian(self):
        self.check_bind_account("DNF福签大作战", "https://dnf.qq.com/cp/a20210325sjlbv3pc/index.html",
                                activity_op_func=self.dnf_fuqian_op, query_bind_flowid="742110", commit_bind_flowid="742109")

    def dnf_fuqian_op(self, ctx, iFlowId, print_res=True, **extra_params):
        iActivityId = self.urls.iActivityId_dnf_fuqian
        return self.amesvr_request(ctx, "x6m5.ams.game.qq.com", "group_3", "dnf", iActivityId, iFlowId, print_res, "http://dnf.qq.com/cp/a20210325sjlbv3pc/",
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

        account_db = FireCrackersDB().with_context(self.cfg.name).load()

        def qeury_not_invited_friends_with_cache():
            invited_friends = query_invited_friends()

            def filter_not_invited_friends(friendQQs):
                validFriendQQs = []
                for friendQQ in friendQQs:
                    if friendQQ not in invited_friends:
                        validFriendQQs.append(friendQQ)

                return validFriendQQs

            friendQQs = account_db.friend_qqs

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

            def _update_db(db: FireCrackersDB):
                db.friend_qqs = friendQQs

            account_db.update(_update_db)

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
    def get(self, ctx, url, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True, extra_cookies="", check_fn: Callable[[requests.Response], Optional[Exception]] = None, **params):
        return self.network.get(ctx, self.format(url, **params), pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote, extra_cookies, check_fn)

    def post(self, ctx, url, data=None, json=None, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True, extra_cookies="", check_fn: Callable[[requests.Response], Optional[Exception]] = None, **params):
        return self.network.post(ctx, self.format(url, **params), data, json, pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote, extra_cookies, check_fn)

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
            "username", "petId",
            "fuin", "sCode", "sNickName", "iId", "sendPage",
            "hello_id", "prize",
            "qd",
            "iReceiveUin",
            "map1", "map2", "len",
            "itemIndex",
            "sRole",
            "loginNum",
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

    def amesvr_request(self, ctx, amesvr_host, sServiceDepartment, sServiceType, iActivityId, iFlowId, print_res, eas_url:str, extra_cookies="",
                       show_info_only=False, get_ams_act_info_only=False, **data_extra_params):
        if show_info_only:
            self.show_ams_act_info(iActivityId)
            return
        if get_ams_act_info_only:
            return get_ams_act(iActivityId)

        data = self.format(self.urls.amesvr_raw_data,
                           sServiceDepartment=sServiceDepartment, sServiceType=sServiceType, eas_url=quote_plus(remove_suffix(eas_url, 'index.html')),
                           iActivityId=iActivityId, iFlowId=iFlowId, **data_extra_params)

        def _check(response: requests.Response) -> Optional[Exception]:
            if response.status_code == 401 and '您的速度过快或参数非法，请重试哦' in response.text:
                # res.status=401, Unauthorized <Response [401]>
                #
                # <html>
                # <head><title>Tencent Game 401</title></head>
                # <meta charset="utf-8" />
                # <body bgcolor="white">
                # <center><h1>Welcome Tencent Game 401</h1></center>
                # <center><h1>您的速度过快或参数非法，请重试哦</h1></center>
                # <hr><center>Welcome Tencent Game</center>
                # </body>
                # </html>
                #
                wait_seconds = 0.1 + random.random()
                logger.warning(f"请求过快，等待{wait_seconds:.2f}秒后重试")
                time.sleep(wait_seconds)
                return Exception("请求过快")

            return None

        return self.post(ctx, self.urls.amesvr, data,
                         amesvr_host=amesvr_host, sServiceDepartment=sServiceDepartment, sServiceType=sServiceType,
                         iActivityId=iActivityId, sMiloTag=self.make_s_milo_tag(iActivityId, iFlowId),
                         print_res=print_res, extra_cookies=extra_cookies, check_fn=_check)

    def show_ams_act_info(self, iActivityId):
        logger.info(color("bold_green") + get_ams_act_desc(iActivityId))

    def show_not_ams_act_info(self, act_name):
        logger.info(color("bold_green") + get_not_ams_act_desc(act_name))

    def make_s_milo_tag(self, iActivityId, iFlowId):
        return f"AMS-MILO-{iActivityId}-{iFlowId}-{self.uin()}-{getMillSecondsUnix()}-{self.rand6()}"

    def rand6(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=6))

    def make_cookie(self, map: dict):
        return '; '.join([f'{k}={v}' for k, v in map.items()])

    def check_bind_account(self, activity_name, activity_url, activity_op_func, query_bind_flowid, commit_bind_flowid, try_auto_bind=True, roleinfo: RoleInfo = None, roleinfo_source="道聚城所绑定的角色"):
        while True:
            res = activity_op_func(f"查询是否绑定-尝试自动({try_auto_bind})", query_bind_flowid, print_res=False)
            # {"flowRet": {"iRet": "0", "sMsg": "MODULE OK", "modRet": {"iRet": 0, "sMsg": "ok", "jData": [], "sAMSSerial": "AMS-DNF-1212213814-q4VCJQ-346329-722055", "commitId": "722054"}, "ret": "0", "msg": ""}
            need_bind = False
            bind_reason = ""
            if len(res["modRet"]["jData"]) == 0:
                # 未绑定角色
                need_bind = True
                bind_reason = "未绑定角色"
            elif self.common_cfg.force_sync_bind_with_djc:
                if roleinfo is None:
                    # 若未从外部传入roleinfo，则使用道聚城绑定的信息
                    roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
                bindinfo = AmesvrUserBindInfo().auto_update_config(res["modRet"]["jData"]["data"])

                if roleinfo.serviceID != bindinfo.Farea or roleinfo.roleCode != bindinfo.FroleId:
                    current_account = f"{unquote_plus(bindinfo.FareaName)}-{unquote_plus(bindinfo.FroleName)}-{bindinfo.FroleId}"
                    djc_account = f"{roleinfo.serviceName}-{roleinfo.roleName}-{roleinfo.roleCode}"

                    need_bind = True
                    bind_reason = f"当前绑定账号({current_account})与{roleinfo_source}({djc_account})不一致"

            if need_bind:
                self.guide_to_bind_account(activity_name, activity_url, activity_op_func=activity_op_func,
                                           query_bind_flowid=query_bind_flowid, commit_bind_flowid=commit_bind_flowid, try_auto_bind=try_auto_bind, bind_reason=bind_reason, roleinfo=roleinfo, roleinfo_source=roleinfo_source)
            else:
                # 已经绑定
                break

    def guide_to_bind_account(self, activity_name, activity_url, activity_op_func=None, query_bind_flowid="", commit_bind_flowid="", try_auto_bind=False, bind_reason="未绑定角色", roleinfo: RoleInfo = None, roleinfo_source="道聚城所绑定的角色"):
        if try_auto_bind and self.common_cfg.try_auto_bind_new_activity and activity_op_func is not None and commit_bind_flowid != "":
            if 'dnf' in self.bizcode_2_bind_role_map:
                # 若道聚城已绑定dnf角色，则尝试绑定这个角色
                if roleinfo is None:
                    # 若未从外部传入roleinfo，则使用道聚城绑定的信息
                    roleinfo = self.bizcode_2_bind_role_map['dnf'].sRoleInfo
                checkInfo = self.get_dnf_roleinfo()

                def double_quote(strToQuote):
                    return quote_plus(quote_plus(strToQuote))

                logger.warning(color("bold_yellow") + f"活动【{activity_name}】{bind_reason}，当前配置为自动绑定模式，将尝试绑定为{roleinfo_source}({roleinfo.serviceName}-{roleinfo.roleName})")
                activity_op_func("提交绑定大区", commit_bind_flowid, True,
                                 user_area=roleinfo.serviceID, user_partition=roleinfo.serviceID, user_areaName=double_quote(roleinfo.serviceName),
                                 user_roleId=roleinfo.roleCode, user_roleName=double_quote(roleinfo.roleName), user_roleLevel="100",
                                 user_checkparam=double_quote(checkInfo.checkparam), user_md5str=checkInfo.md5str, user_sex="", user_platId="")
            else:
                logger.warning(color("bold_yellow") + f"活动【{activity_name}】{bind_reason}，当前配置为自动绑定模式，但道聚城未绑定角色，因此无法应用自动绑定，将使用手动绑定方案")

            # 绑定完毕，再次检测，这次如果检测仍未绑定，则不再尝试自动绑定
            self.check_bind_account(activity_name, activity_url, activity_op_func, query_bind_flowid, commit_bind_flowid, try_auto_bind=False, roleinfo=roleinfo, roleinfo_source=roleinfo_source)
        else:
            msg = (
                f"当前账号【{self.cfg.name}】{bind_reason}，且未开启自动绑定模式，请点击右下角的【确定】按钮后，在自动弹出的【{activity_name}】活动页面进行绑定，然后按任意键继续\n"
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

    def fetch_share_p_skey(self, ctx) -> str:
        logger.warning(color("bold_yellow") + f"开启了{ctx}功能，因此需要登录活动页面来获取p_skey，请稍候~")

        ql = QQLogin(self.common_cfg)
        login_mode = ql.login_mode_normal
        if self.cfg.login_mode == "qr_login":
            # 扫码登录
            lr = ql.qr_login(login_mode=login_mode, name=self.cfg.name)
        else:
            # 自动登录
            lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode=login_mode, name=self.cfg.name)

        return lr.apps_p_skey

    def fetch_xinyue_login_info(self, ctx) -> LoginResult:
        logger.warning(color("bold_yellow") + f"开启了{ctx}功能，因此需要登录心悦页面来获取心悦相关信息，请稍候~")

        ql = QQLogin(self.common_cfg)
        login_mode = ql.login_mode_xinyue
        if self.cfg.login_mode == "qr_login":
            # 扫码登录
            lr = ql.qr_login(login_mode=login_mode, name=self.cfg.name)
        else:
            # 自动登录
            lr = ql.login(self.cfg.account_info.account, self.cfg.account_info.password, login_mode=login_mode, name=self.cfg.name)

        return lr

    def parse_condOutput(self, res: dict, cond_id: str) -> int:
        """
        解析并返回对应的数目
        """
        info = parse_amesvr_common_info(res)
        # "sOutValue1": "e0c747b4b51392caf0c99162e69125d8:iRet:0|b1ecb3ecd311175835723e484f2d8d88:iRet:0",
        for cond_info in info.sOutValue1.split('|'):
            cid, name, val = cond_info.split(':')
            if cid == cond_id:
                return int(val)

        return 0

    def parse_jifenOutput(self, res: dict, count_id: str) -> Tuple[int, int]:
        """
        解析并返回对应的总数和剩余值
        """
        info = parse_amesvr_common_info(res)
        # "sOutValue1": "239:16:4|240:8:1",
        for count_info in info.sOutValue1.split('|'):
            cid, total, remaining = count_info.split(':')
            if cid == count_id:
                return int(total), int(remaining)

        return 0, 0

    def uin(self) -> str:
        return self.cfg.account_info.uin

    def qq(self) -> str:
        return uin2qq(self.uin())


def async_run_all_act(account_config: AccountConfig, common_config: CommonConfig, activity_funcs_to_run: List[Tuple[str, Callable]]):
    pool_size = len(activity_funcs_to_run)
    logger.warning(color("bold_yellow") + f"将使用{pool_size}个进程并行运行{len(activity_funcs_to_run)}个活动")
    act_pool = Pool(pool_size)
    act_pool.starmap(run_act, [(account_config, common_config, act_name, act_func.__name__) for act_name, act_func in activity_funcs_to_run])


def run_act(account_config: AccountConfig, common_config: CommonConfig, act_name: str, act_func_name: str):
    djcHelper = DjcHelper(account_config, common_config)
    djcHelper.fetch_pskey()
    djcHelper.check_skey_expired()
    djcHelper.get_bind_role_list()

    getattr(djcHelper, act_func_name)()


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

    RunAll = False
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

        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()
        #
        # from main_def import get_user_buy_info
        #
        # user_buy_info = get_user_buy_info(cfg.get_qq_accounts())
        # djcHelper.run(user_buy_info)

        # djcHelper.query_all_extra_info()
        # djcHelper.exchange_items()
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
        # djcHelper.dnf_carnival()
        # djcHelper.xinyue_financing()
        # djcHelper.dnf_carnival_live()
        # djcHelper.dnf_dianzan()
        # djcHelper.dnf_drift()
        # djcHelper.dnf_shanguang()
        # djcHelper.warm_winter()
        # djcHelper.dnf_1224()
        # djcHelper.spring_fudai()
        # djcHelper.firecrackers()
        # djcHelper.xinyue_weekly_gift()
        # djcHelper.xinyue_cat()
        # djcHelper.dnf_fuqian()
        # djcHelper.vip_mentor()
        # djcHelper.hello_voice()
        # djcHelper.xinyue_operations()
        # djcHelper.try_join_fixed_xinyue_team()
        # djcHelper.xinyue_app_operations()
        # djcHelper.dnf_pk()
        # djcHelper.dnf_xinyue_51()
        # djcHelper.dnf_helper()
        # djcHelper.dnf_bbs()
        # djcHelper.guanjia()
        # djcHelper.dnf_strong()
        # djcHelper.ark_lottery()
        # djcHelper.dnf_collection()
        # djcHelper.qq_video_amesvr()
        # djcHelper.dnf_13()
        # djcHelper.dnf_helper_chronicle()
        # djcHelper.dnf_luodiye()
        # djcHelper.dnf_my_story()
        # djcHelper.dnf_reserve()
        # djcHelper.dnf_anniversary()
        # djcHelper.dnf_wegame_dup()
        # djcHelper.dnf_collection_dup()
        # djcHelper.majieluo()
        # djcHelper.dnf_kol()
        # djcHelper.dnf_comic()
        # djcHelper.dnf_super_vip()
        # djcHelper.dnf_yellow_diamond()
        # djcHelper.dnf_welfare()
        # djcHelper.guanjia_new()
        # djcHelper.colg_signin()
        # djcHelper.qq_video()
        djcHelper.dnf_wegame()
