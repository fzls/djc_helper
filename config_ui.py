from __future__ import annotations

from log import logger, fileHandler, new_file_handler

logger.name = "config_ui"
logger.removeHandler(fileHandler)
logger.addHandler(new_file_handler())

from io import StringIO
from traceback import print_tb
from PyQt5.QtWidgets import (
    QApplication, QTabWidget, QStyleFactory,
    QMessageBox, QInputDialog, QFileDialog)
from PyQt5.QtGui import QIcon, QValidator
from PyQt5.QtCore import QCoreApplication, QThread

from qt_wrapper import *
from config import *
from setting import *
from game_info import get_name_2_mobile_game_info_map
from update import *
from main_def import has_any_account_in_normal_run, _show_head_line, has_buy_auto_updater_dlc, get_user_buy_info, disable_flag_file
from djc_helper import DjcHelper
from dao import CardSecret, DnfRoleInfo
from data_struct import to_raw_type
from usage_count import increase_counter
from ga import GA_REPORT_TYPE_PAGE_VIEW

# 客户端错误码
CHECK_RESULT_OK = "检查通过"

# 服务器错误码
RESULT_OK = "操作成功"
RESULT_INVALID = "卡密不存在或不匹配"
RESULT_QQ_NOT_SET = "未设置QQ"
RESULT_ALREADY_USED = "卡密已经使用过"
RESULT_ALREADY_BUY = "自动更新只需购买一次"


class PayRequest(ConfigInterface):
    def __init__(self):
        self.card_secret = CardSecret()  # 卡密信息
        self.qq = ""  # 使用QQ
        self.game_qqs = ""  # 附属游戏QQ


class PayResponse(ConfigInterface):
    def __init__(self):
        self.msg = "ok"


class BiDict():
    def __init__(self, original_dict: dict):
        self.key_to_val = dict({k: v for k, v in original_dict.items()})
        self.val_to_key = dict({v: k for k, v in original_dict.items()})


def list_to_str(vlist: List[str]):
    return ','.join(str(v) for v in vlist)


def str_to_list(str_list: str):
    str_list = str_list.strip(" ,")
    if str_list == "":
        return []

    return [s.strip() for s in str_list.split(',')]


class QQListValidator(QValidator):
    def validate(self, text: str, pos: int) -> Tuple['QValidator.State', str, int]:
        sl = str_to_list(text)

        for qq in sl:
            if not qq.isnumeric():
                return (QValidator.Invalid, text, pos)

        return (QValidator.Acceptable, text, pos)


def show_message(title, text):
    logger.info(f"{title} {text}")

    message_box = QMessageBox()
    message_box.setWindowTitle(title)
    message_box.setText(text)
    message_box.exec_()


class GetBuyInfoThread(QThread):
    signal_results = pyqtSignal(str, str, str)

    def __init__(self, parent, cfg: Config):
        super(GetBuyInfoThread, self).__init__(parent)

        self.cfg = cfg
        self.time_start = datetime.now()

    def __del__(self):
        self.exiting = True

    def run(self) -> None:
        self.update_progress("1/3 开始尝试更新各个账号的skey")
        self.check_all_skey_and_pskey()

        self.update_progress("2/3 开始尝试获取自动更新DLC的信息")
        has_buy_auto_update_dlc = has_buy_auto_updater_dlc(self.cfg.get_qq_accounts())

        self.update_progress("3/3 开始尝试获取按月付费的信息")
        user_buy_info = get_user_buy_info(self.cfg.get_qq_accounts())

        dlc_info = "注意：自动更新和按月付费是两个完全不同的东西，具体区别请看 付费指引/付费指引.docx\n"
        if has_buy_auto_update_dlc:
            dlc_info += "已购买自动更新DLC" \
                        "\n\t请注意这里的两月是指从2.8开始累积未付费时长最多允许为两个月，是给2.8以前购买DLC的朋友的小福利" \
                        "\n\t如果4.11以后才购买就享受不到这个的，因为购买时自2.8开始的累积未付费时长已经超过两个月"
        else:
            dlc_info += "当前所有账号均未购买自动更新DLC"
        monthly_pay_info = user_buy_info.description()

        logger.info(f"\n{dlc_info}\n\n{monthly_pay_info}")
        self.send_results(dlc_info, monthly_pay_info)

    def check_all_skey_and_pskey(self):
        if not has_any_account_in_normal_run(self.cfg):
            return
        _show_head_line("启动时检查各账号skey/pskey/openid是否过期")

        for _idx, account_config in enumerate(self.cfg.account_configs):
            idx = _idx + 1
            if not account_config.is_enabled():
                # 未启用的账户的账户不走该流程
                continue

            logger.warning(color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name})------------")
            self.update_progress(f"1/3 正在处理第{idx}/{len(self.cfg.account_configs)}个账户({account_config.name})，请耐心等候...")

            djcHelper = DjcHelper(account_config, self.cfg.common)
            djcHelper.fetch_pskey()
            djcHelper.check_skey_expired()

            self.update_progress(f"完成处理第{idx}个账户({account_config.name})")

    def update_progress(self, progress_message):
        ut = datetime.now() - self.time_start
        self.signal_results.emit(f"{progress_message}(目前共耗时{ut.total_seconds():.1f}秒)", "", "")

    def send_results(self, dlc_info, monthly_pay_info):
        self.signal_results.emit("", dlc_info, monthly_pay_info)


class ConfigUi(QFrame):
    def __init__(self, parent=None):
        super(ConfigUi, self).__init__(parent)

        self.resize(1080, 780)
        title = f"DNF蚊子腿小助手 简易配置工具 v{now_version} by风之凌殇 {get_random_face()}"
        self.setWindowTitle(title)

        self.setStyleSheet(f"font-family: Microsoft YaHei")
        self.setWindowIcon(QIcon("utils/icons/config_ui.ico"))

        self.setWhatsThis("简易配置工具")

        self.load()

        logger.info(f"配置工具启动成功，版本号为v{now_version}")

    def load(self):
        self.from_config(self.load_config())

        logger.info("已读取成功，请按需调整配置，调整完记得点下保存~")

    def load_old_version(self):
        # 弹窗提示选择旧版本的小助手exe所在目录
        msg = "打开旧版本的【DNF蚊子腿小助手.exe】所在的目录，形如【DNF蚊子腿小助手_v10.5.0_by风之凌殇】"
        # show_message("操作指引", msg)
        old_version_dir = QFileDialog.getExistingDirectory(self, msg,
                                                           os.path.realpath(".."),
                                                           QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if old_version_dir == '':
            logger.info("未选择任何目录")
            return

        # 通过判断目录中是否存在【DNF蚊子腿小助手.exe】来判定选择的目录是否是正确的目录
        djc_helper_exe = 'DNF蚊子腿小助手.exe'
        if not os.path.isfile(os.path.join(old_version_dir, djc_helper_exe)):
            show_message("出错啦", f"未在选中的目录 {old_version_dir} 中发现 {djc_helper_exe} ，请重新点击按钮进行选择~")
            return

        # 将特定文件和目录复制过来覆盖新版本的目录
        new_version_dir = os.getcwd()
        sync_configs(old_version_dir, new_version_dir)

        logger.info("继承旧版本配置完成，将重启配置工具以使改动生效")
        report_click_event("load_old_version")
        self.restart()

    def restart_to_load(self, checked=False):
        self.restart()
        report_click_event("load_config")

    def restart(self):
        if run_from_src():
            python = sys.executable
            os.execl(python, python, *sys.argv)
        else:
            os.startfile(sys.argv[0])

        kill_process(os.getpid())

    def save(self, checked=False, show_message_box=True):
        self.save_config(self.to_config())
        if show_message_box:
            show_message("保存成功", "已保存成功\nconfig.toml已不再有注释信息，如有需要，可去config.example.toml查看注释")
            report_click_event("save_config")

    def load_config(self) -> Config:
        load_config(local_config_path="", reset_before_load=True)
        # load_config(local_config_path="config.toml.local", reset_before_load=True)
        return config()

    def save_config(self, cfg: Config):
        save_config(cfg)

    def from_config(self, cfg: Config):
        # 根据配置初始化ui
        top_layout = QVBoxLayout()

        self.create_buttons(top_layout)
        self.create_tabs(cfg, top_layout)

        # 设置一些关联事件
        self.common.checkbox_auto_update_on_start.clicked.connect(self.on_click_auto_update)
        self.on_click_auto_update(self.common.checkbox_auto_update_on_start.isChecked())

        self.setLayout(top_layout)

    def create_buttons(self, top_layout: QVBoxLayout):
        # note: 配色可参考 https://www.computerhope.com/htmcolor.htm
        #   https://www.computerhope.com/jargon/w/w3c-color-names.htm

        btn_load_old_version = create_pushbutton("继承旧版本配置", "Aquamarine")
        btn_load = create_pushbutton("读取配置", "Aquamarine")
        btn_save = create_pushbutton("保存配置", "Aquamarine")

        btn_load_old_version.clicked.connect(self.load_old_version)
        btn_load.clicked.connect(self.restart_to_load)
        btn_save.clicked.connect(self.save)

        layout = QHBoxLayout()
        layout.addWidget(btn_load_old_version)
        layout.addWidget(btn_load)
        layout.addWidget(btn_save)
        top_layout.addLayout(layout)
        top_layout.addWidget(QHLine())

        btn_add_account = create_pushbutton("添加账号", "Chartreuse")
        btn_del_account = create_pushbutton("删除账号", "lightgreen")
        btn_clear_login_status = create_pushbutton("清除登录状态", "DarkCyan", "登录错账户，或者想要登录其他账户时，点击这个即可清除登录状态")
        btn_add_group = create_pushbutton("加群反馈问题/交流", "Orange")

        btn_add_account.clicked.connect(self.add_account)
        btn_del_account.clicked.connect(self.del_account)
        btn_clear_login_status.clicked.connect(self.clear_login_status)
        btn_add_group.clicked.connect(self.add_group)

        layout = QHBoxLayout()
        layout.addWidget(btn_add_account)
        layout.addWidget(btn_del_account)
        layout.addWidget(btn_clear_login_status)
        layout.addWidget(btn_add_group)
        top_layout.addLayout(layout)
        top_layout.addWidget(QHLine())

        btn_open_pay_guide = create_pushbutton("查看付费指引", "SpringGreen")
        btn_open_usage_guide = create_pushbutton("查看使用教程（文字版）", "SpringGreen")
        btn_open_usage_video = create_pushbutton("查看使用教程（视频版）", "SpringGreen")
        btn_open_autojs = create_pushbutton("查看autojs版", "PaleGreen")

        btn_open_pay_guide.clicked.connect(self.open_pay_guide)
        btn_open_usage_guide.clicked.connect(self.open_usage_guide)
        btn_open_usage_video.clicked.connect(self.open_usage_video)
        btn_open_autojs.clicked.connect(self.open_autojs)

        layout = QHBoxLayout()
        layout.addWidget(btn_open_pay_guide)
        layout.addWidget(btn_open_usage_guide)
        layout.addWidget(btn_open_usage_video)
        layout.addWidget(btn_open_autojs)
        top_layout.addLayout(layout)
        top_layout.addWidget(QHLine())

        self.btn_run_djc_helper = create_pushbutton("保存配置，然后运行小助手并退出配置工具", "cyan")
        self.btn_run_djc_helper.clicked.connect(self.run_djc_helper)
        top_layout.addWidget(self.btn_run_djc_helper)
        top_layout.addWidget(QHLine())

    def open_pay_guide(self):
        webbrowser.open(os.path.realpath("付费指引/付费指引.docx"))
        report_click_event("open_pay_guide")

    def open_usage_guide(self):
        webbrowser.open(os.path.realpath("使用教程/使用文档.docx"))
        report_click_event("open_usage_guide")

    def open_usage_video(self):
        webbrowser.open(os.path.realpath("使用教程/视频教程_合集.url"))
        report_click_event("open_usage_video")

    def open_autojs(self):
        webbrowser.open("https://github.com/fzls/autojs")
        report_click_event("open_autojs")

    def support(self, checked=False):
        show_message(get_random_face(), "纳尼，真的要打钱吗？还有这种好事，搓手手0-0")
        self.popen(os.path.realpath("付费指引/支持一下.png"))

        report_click_event("support")

    def check_update(self, checked=False):
        cfg = self.to_config().common

        try:
            ui = get_update_info(cfg)
            if not try_manaual_update(ui):
                show_message("无需更新", "当前已经是最新版本~")
        except Exception as err:
            update_fallback(cfg)

        report_click_event("check_update")

    def on_click_auto_update(self, checked=False):
        if checked:
            self.btn_run_djc_helper.setText("保存配置，然后运行小助手并退出配置工具")
        else:
            self.btn_run_djc_helper.setText("保存配置，然后运行小助手")

    def run_djc_helper(self, checked=False):
        logger.info("运行小助手前自动保存配置")
        self.save(show_message_box=False)

        exe_path = self.get_djc_helper_path()
        start_djc_helper(exe_path)

        if self.common.checkbox_auto_update_on_start.isChecked():
            logger.info("当前已启用自动更新功能，为确保自动更新时配置工具不被占用，将退出配置工具")
            QCoreApplication.exit()

        report_click_event("run_djc_helper")

    def get_djc_helper_path(self):
        exe_path = "DNF蚊子腿小助手.exe"
        if run_from_src():
            exe_path = "main.py"

        return os.path.realpath(exe_path)

    def popen(self, args, cwd="."):
        if type(args) is list:
            args = [str(arg) for arg in args]

        subprocess.Popen(args, cwd=cwd, shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def clear_login_status(self, checked=False):
        clear_login_status()

        show_message("清除完毕", "登录状态已经清除完毕，可使用新账号重新运行~")
        report_click_event("clear_login_status")

    def add_group(self, checked=False):
        # note: 如果群 444193814 满了，到 https://qun.qq.com/join.html 获取新群的加群链接 @2021-02-13 01:41:03 By Chen Ji
        webbrowser.open("https://qm.qq.com/cgi-bin/qm/qr?k=vSEAVsoTbqJOKqp4bVpxnExEYOahOjcZ&jump_from=webapi")
        self.popen("DNF蚊子腿小助手交流群群二维码.jpg")
        report_click_event("add_group")

    def add_account(self, checked=False):
        account_name, ok = QInputDialog.getText(self, "添加账号", "要添加的账号名称", QLineEdit.Normal, f"默认账号名-{len(self.accounts) + 1}")
        if ok:
            logger.info(f"尝试添加账号 {account_name} ...")

            if account_name == "":
                show_message("添加失败", f"未填写账号名称，请重新操作~")
                return

            for account in self.accounts:
                if account.lineedit_name.text() == account_name:
                    show_message("添加失败", f"已存在名称为 {account_name} 的账号，请重新操作~")
                    return

            account_config = AccountConfig()
            # 调用下这个函数，确保读取配置时的回调的一些参数能够生成，避免刚创建账号时执行一些操作会报错
            account_config.auto_update_config({})
            account_config.name = account_name
            account_ui = AccountConfigUi(account_config, self.to_config().common)
            self.add_account_tab(account_ui)
            self.tabs.setCurrentWidget(account_ui)

            show_message("添加成功", "请继续进行其他操作~ 全部操作完成后记得保存~")

            report_click_event("add_account")

    def del_account(self, checked=False):
        account_name, ok = QInputDialog.getText(self, "删除账号", "要删除的账号名称", QLineEdit.Normal, "")
        if ok:
            logger.info(f"尝试删除账号 {account_name} ...")

            account_to_delete = None
            for account in self.accounts:
                if account.lineedit_name.text() == account_name:
                    account_to_delete = account
                    break

            if account_to_delete is None:
                show_message("删除失败", f"未找到名称为 {account_name} 的账号，请重新操作~")
                return

            self.accounts.remove(account_to_delete)
            self.tabs.removeTab(self.tabs.indexOf(account_to_delete))
            show_message("删除成功", "请继续进行其他操作~ 全部操作完成后记得保存~")
        report_click_event("del_account")

    def create_tabs(self, cfg: Config, top_layout: QVBoxLayout):
        self.tabs = QTabWidget()

        self.create_userinfo_tab(cfg)
        self.create_others_tab(cfg)
        self.create_common_tab(cfg)
        self.create_account_tabs(cfg)

        # 设置默认页
        self.tabs.setCurrentWidget(self.common)
        if len(self.accounts) != 0:
            # 如果有账号信息，则默认启动时聚焦首个账号配置
            self.tabs.setCurrentWidget(self.accounts[0])

        top_layout.addWidget(self.tabs)

    def create_userinfo_tab(self, cfg: Config):
        tab = QFrame()
        tab.setStyleSheet("font-size: 18px; font-weight: bold;")
        top_layout = QVBoxLayout()
        top_layout.setAlignment(Qt.AlignCenter)

        # -------------- 区域：购买卡密 --------------
        self.collapsible_box_buy_card_secret = create_collapsible_box_add_to_parent_layout("购买卡密(不会操作可点击左上方的【查看付费指引】按钮)", top_layout, title_backgroup_color="Chartreuse")
        hbox_layout = QHBoxLayout()
        self.collapsible_box_buy_card_secret.setContentLayout(hbox_layout)

        btn_buy_auto_updater_dlc = create_pushbutton("购买自动更新DLC的卡密", "DeepSkyBlue", "10.24元，一次性付费，永久激活自动更新功能，需去网盘或群文件下载auto_updater.exe放到utils目录，详情可见付费指引/付费指引.docx")
        btn_pay_by_month = create_pushbutton("购买按月付费的卡密", "DeepSkyBlue", "5元/月(31天)，付费生效期间可以激活2020.2.6及之后加入的短期活动，可从账号概览区域看到付费情况，详情可见付费指引/付费指引.docx")

        btn_buy_auto_updater_dlc.clicked.connect(self.buy_auto_updater_dlc)
        btn_pay_by_month.clicked.connect(self.pay_by_month)

        hbox_layout.addWidget(btn_buy_auto_updater_dlc)
        hbox_layout.addWidget(btn_pay_by_month)

        # -------------- 区域：使用卡密 --------------
        self.collapsible_box_use_card_secret = create_collapsible_box_add_to_parent_layout("使用卡密", top_layout, title_backgroup_color="MediumSpringGreen")
        vbox_layout = QVBoxLayout()
        self.collapsible_box_use_card_secret.setContentLayout(vbox_layout)

        form_layout = QFormLayout()
        vbox_layout.addLayout(form_layout)

        self.lineedit_card = create_lineedit("", placeholder_text="填入在卡密网站付款后得到的卡号，形如 auto_update-20210313133230-00001")
        form_layout.addRow("卡号", self.lineedit_card)

        self.lineedit_secret = create_lineedit("", placeholder_text="填入在卡密网站付款后得到的密码，形如 BF8h0y1Zcb8ukY6rsn5YFhkh0Nbe9hit")
        form_layout.addRow("卡密", self.lineedit_secret)

        self.lineedit_qq = create_lineedit("", placeholder_text="形如 1234567")
        form_layout.addRow("主QQ", self.lineedit_qq)

        self.lineedit_game_qqs = create_lineedit("", placeholder_text="最多5个，使用英文逗号分隔，形如 123,456,789,12,13")
        self.lineedit_game_qqs.setValidator(QQListValidator())
        form_layout.addRow("其他要使用的QQ", self.lineedit_game_qqs)

        btn_pay_by_card_and_secret = create_pushbutton("使用卡密购买对应服务", "MediumSpringGreen")
        vbox_layout.addWidget(btn_pay_by_card_and_secret)

        btn_pay_by_card_and_secret.clicked.connect(self.pay_by_card_and_secret)

        # -------------- 区域：查询信息 --------------
        add_vbox_seperator(top_layout, "查询信息")
        vbox_layout = QVBoxLayout()
        top_layout.addLayout(vbox_layout)

        # 显示付费相关内容
        self.btn_show_buy_info = create_pushbutton("显示付费相关信息(点击后将登录所有账户，可能需要较长时间，请耐心等候)")
        self.btn_show_buy_info.clicked.connect(self.show_buy_info)
        vbox_layout.addWidget(self.btn_show_buy_info)

        self.label_auto_udpate_info = QLabel("点击登录按钮后可显示是否购买自动更新DLC")
        self.label_auto_udpate_info.setVisible(False)
        self.label_auto_udpate_info.setStyleSheet("color : DarkSlateGray; ")
        vbox_layout.addWidget(self.label_auto_udpate_info)

        self.label_monthly_pay_info = QLabel("点击登录按钮后可显示按月付费信息")
        self.label_monthly_pay_info.setVisible(False)
        self.label_monthly_pay_info.setStyleSheet("color : DarkCyan; ")
        vbox_layout.addWidget(self.label_monthly_pay_info)

        # -------------- 区域代码结束 --------------
        tab.setLayout(make_scroll_layout(top_layout))
        self.tabs.addTab(tab, "付费相关")

        init_collapsible_box_size(self)

    def buy_auto_updater_dlc(self, checked=False):
        if not self.check_pay_server():
            return

        message_box = QMessageBox()
        message_box.setWindowTitle("友情提示")
        message_box.setText("自动更新DLC的唯一作用仅仅是【自动更新】，不会给你带来付费活动的使用资格的哦，请确认你想要购买的是这个功能后再点击【确认】按钮进行购买-。-")
        message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        ret = message_box.exec_()
        if ret == QMessageBox.Cancel:
            logger.info("取消购买")
            return

        message_box = QMessageBox()
        message_box.setWindowTitle("友情提示")
        message_box.setText("自动更新DLC只需购买一次，请确认从未购买过后再点击【确认】按钮进行购买")
        message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        ret = message_box.exec_()
        if ret == QMessageBox.Cancel:
            logger.info("取消购买")
            return

        webbrowser.open(self.load_config().common.auto_updater_dlc_purchase_url)
        increase_counter(ga_category="open_pay_webpage", name="auto_updater_dlc")

    def pay_by_month(self, checked=False):
        if not self.check_pay_server():
            return

        webbrowser.open(self.load_config().common.pay_by_month_purchase_url)
        increase_counter(ga_category="open_pay_webpage", name="pay_buy_month")

    def pay_by_card_and_secret(self, checked=False):
        card = self.lineedit_card.text().strip()
        secret = self.lineedit_secret.text().strip()
        qq = self.lineedit_qq.text().strip()
        game_qqs = str_to_list(self.lineedit_game_qqs.text().strip())

        msg = self.check_pay_params(card, secret, qq, game_qqs)
        if msg != CHECK_RESULT_OK:
            show_message("出错了", msg)
            return

        message_box = QMessageBox()
        message_box.setWindowTitle("请确认账号信息")
        message_box.setText((
            "请确认输入的账号信息是否无误，避免充错账号~\n\n"
            f"主QQ：{qq}\n"
            f"其他QQ列表：{game_qqs}\n"
        ))
        message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        ret = message_box.exec_()
        if ret == QMessageBox.Cancel:
            logger.info("取消使用卡密")
            return

        if not self.check_pay_server():
            return

        try:
            self.do_pay_request(card, secret, qq, game_qqs)
        except Exception as e:
            show_message("出错了", f"请求出现异常，报错如下:\n{e}")

        # 点击付费按钮后重置cache
        reset_cache(cache_name_download)

    def check_pay_params(self, card: str, secret: str, qq: str, game_qqs: List[str]) -> str:
        if len(card.split('-')) != 3:
            return "无效的卡号"

        if len(secret) != 32:
            return "无效的卡密"

        for qq_to_check in [qq, *game_qqs]:
            if not is_valid_qq(qq_to_check):
                return f"无效的QQ：{qq_to_check}"

        if len(game_qqs) > 5:
            return f"最多五个QQ哦，如果有更多QQ，建议用配置工具添加多个账号一起使用（任意一个有权限就可以），无需全部填写~"

        return CHECK_RESULT_OK

    def do_pay_request(self, card: str, secret: str, qq: str, game_qqs: List[str]):
        req = PayRequest()
        req.card_secret.card = card
        req.card_secret.secret = secret
        req.qq = qq
        req.game_qqs = game_qqs

        server_addr = self.get_pay_server_addr()
        raw_res = requests.post(f"{server_addr}/pay", json=to_raw_type(req), timeout=20)
        if raw_res.status_code != 200:
            show_message("出错了", "服务器似乎暂时挂掉了, 请稍后再试试")
            return

        res = PayResponse().auto_update_config(raw_res.json())
        show_message("服务器处理结果", res.msg)

        if res.msg == RESULT_OK:
            self.lineedit_card.clear()
            self.lineedit_secret.clear()

            # 自动更新购买完成后提示去网盘下载
            if card.startswith("auto_update"):
                show_message("提示", "自动更新已激活，请前往网盘下载auto_updater.exe，具体操作流程请看【付费指引/付费指引.docx】（或者直接运行小助手也可以，现在支持尝试自动下载dlc到本地）")

            self.report_use_card_secret(card)

    @try_except(return_val_on_except=False)
    def report_use_card_secret(self, card: str):
        increase_counter(ga_category="use_card_secret", name=card.split('-')[0])

    @try_except(return_val_on_except=False)
    def check_pay_server(self) -> bool:
        server_not_online_message = "无法访问服务器，若非最新版本，请尝试更新小助手版本~ 保底可使用扫码付费后私聊的方式购买，具体流程请参考【付费指引/付费指引.docx】"
        try:
            res = requests.get(self.get_pay_server_addr(), timeout=3)
            if res.status_code == 200:
                return True
            elif res.status_code == 403:
                show_message("请求过快", "请不要频繁点击按钮，小水管撑不住的<_<")
                return False
            else:
                show_message("出错了", server_not_online_message)
                return False
        except Exception as e:
            show_message("出错了", server_not_online_message)
            return False

    def get_pay_server_addr(self) -> str:
        return get_pay_server_addr()

    def create_others_tab(self, cfg: Config):
        top_layout = QVBoxLayout()

        btn_support = create_pushbutton("作者很胖胖，我要给他买罐肥宅快乐水！", "DodgerBlue", "有钱就是任性.jpeg")
        btn_check_update = create_pushbutton("检查更新", "SpringGreen")

        btn_support.clicked.connect(self.support)
        btn_check_update.clicked.connect(self.check_update)

        layout = QHBoxLayout()
        layout.addWidget(btn_support)
        layout.addWidget(btn_check_update)
        top_layout.addLayout(layout)

        btn_auto_run_on_login = create_pushbutton("开机自启", "MediumTurquoise")
        btn_stop_auto_run_on_login = create_pushbutton("取消自启", "MediumTurquoise")

        btn_auto_run_on_login.clicked.connect(self.auto_run_on_login)
        btn_stop_auto_run_on_login.clicked.connect(self.stop_auto_run_on_login)

        layout = QHBoxLayout()
        layout.addWidget(btn_auto_run_on_login)
        layout.addWidget(btn_stop_auto_run_on_login)
        top_layout.addLayout(layout)

        self.others = QFrame()
        self.others.setLayout(make_scroll_layout(top_layout))

        self.tabs.addTab(self.others, "其他功能")

    def auto_run_on_login(self):
        self.popen([
            "reg",
            "add", "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run",
            "/v", "DNF蚊子腿小助手",
            "/t", "reg_sz",
            "/d", self.get_djc_helper_path(),
            "/f",
        ])
        show_message("设置完毕", "已设置为开机自动启动~\n若想定时运行，请打开【使用教程/使用文档.docx】，参照【定时自动运行】章节（目前在第21页）设置")

        report_click_event("auto_run_on_login")

    def stop_auto_run_on_login(self):
        self.popen([
            "reg",
            "delete", "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run",
            "/v", "DNF蚊子腿小助手",
            "/f",
        ])
        show_message("设置完毕", "已取消开机自动启动~")

        report_click_event("stop_auto_run_on_login")

    def create_common_tab(self, cfg: Config):
        self.common = CommonConfigUi(cfg.common)
        self.tabs.addTab(self.common, "公共配置")

    def create_account_tabs(self, cfg: Config):
        self.accounts = []  # type: List[AccountConfigUi]
        for account in cfg.account_configs:
            account_ui = AccountConfigUi(account, self.to_config().common)
            self.add_account_tab(account_ui)

    def add_account_tab(self, account_ui: AccountConfigUi):
        self.accounts.append(account_ui)
        self.tabs.addTab(account_ui, account_ui.lineedit_name.text())

        # 记录当前账号名，用于同步修改tab名称
        account_ui.old_name = account_ui.lineedit_name.text()

        # 当修改账号名时，根据之前的账号名，定位并同步修改tab名称
        def update_tab_name(new_account_name: str):
            for tab_index in range(self.tabs.count()):
                if self.tabs.tabText(tab_index) == account_ui.old_name:
                    self.tabs.setTabText(tab_index, new_account_name)
                    account_ui.old_name = new_account_name
                    break

        account_ui.lineedit_name.textChanged.connect(update_tab_name)

    def show_buy_info(self, clicked=False):
        cfg = self.to_config()

        worker = GetBuyInfoThread(self, cfg)
        worker.signal_results.connect(self.on_get_buy_info)
        worker.start()

        report_click_event("show_buy_info")

    def on_get_buy_info(self, progress_message: str, dlc_info: str, monthly_pay_info: str):
        if progress_message != "":
            # 更新进度
            self.btn_show_buy_info.setText(progress_message)
        else:
            # 发送最终结果
            self.label_auto_udpate_info.setText(dlc_info)
            self.label_monthly_pay_info.setText(monthly_pay_info)

            self.btn_show_buy_info.setVisible(False)
            self.label_auto_udpate_info.setVisible(True)
            self.label_monthly_pay_info.setVisible(True)

    def to_config(self) -> Config:
        cfg = self.load_config()

        if hasattr(self, "common") and hasattr(self, "accounts"):
            self.common.update_config(cfg.common)

            account_configs = []
            for idx, account in enumerate(self.accounts):
                # 以在账号中的次序作为唯一定位key，从而获取当前配置中该账号的配置，以便能保留一些配置工具中未涉及的配置，可以与文本编辑器改动兼容
                if idx < len(cfg.account_configs):
                    account_config = cfg.account_configs[idx]
                else:
                    account_config = AccountConfig()

                account.update_config(account_config)
                account_configs.append(account_config)

            cfg.account_configs = account_configs

        return cfg


class CommonConfigUi(QFrame):
    def __init__(self, cfg: CommonConfig, parent=None):
        super(CommonConfigUi, self).__init__(parent)

        self.from_config(cfg)

    def from_config(self, cfg: CommonConfig):
        top_layout = QVBoxLayout()

        form_layout = QFormLayout()
        top_layout.addLayout(form_layout)

        # -------------- 区域：角色绑定与同步 --------------
        self.collapsible_box_role_binding_sync, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("角色绑定与同步", top_layout)

        self.checkbox_try_auto_bind_new_activity = create_checkbox(cfg.try_auto_bind_new_activity)
        add_row(form_layout, "尝试自动绑定新活动", self.checkbox_try_auto_bind_new_activity)

        self.checkbox_force_sync_bind_with_djc = create_checkbox(cfg.force_sync_bind_with_djc)
        add_row(form_layout, "是否强制与道聚城的绑定角色同步", self.checkbox_force_sync_bind_with_djc)

        # -------------- 区域：集卡 --------------
        self.collapsible_box_ark_lottery, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("集卡", top_layout)

        self.lineedit_auto_send_card_target_qqs = create_lineedit(list_to_str(cfg.auto_send_card_target_qqs), "填写要接收卡片的qq号列表，使用英文逗号分开，示例：123, 456, 789")
        self.lineedit_auto_send_card_target_qqs.setValidator(QQListValidator())
        add_row(form_layout, "自动赠送卡片的目标QQ数组(这些QQ将接收来自其他QQ赠送的卡片)", self.lineedit_auto_send_card_target_qqs)

        # -------------- 区域：心悦 --------------
        self.collapsible_box_xinyue, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("心悦", top_layout)

        self.fixed_teams = []
        for team in cfg.fixed_teams:
            self.fixed_teams.append(FixedTeamConfigUi(form_layout, team))

        # -------------- 区域：更新 --------------
        self.collapsible_box_update, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("更新", top_layout)

        self.checkbox_check_update_on_start = create_checkbox(cfg.check_update_on_start)
        add_row(form_layout, "启动时检查更新", self.checkbox_check_update_on_start)

        self.checkbox_check_update_on_end = create_checkbox(cfg.check_update_on_end)
        add_row(form_layout, "结束前检查更新", self.checkbox_check_update_on_end)

        self.checkbox_auto_update_on_start = create_checkbox(cfg.auto_update_on_start)
        add_row(form_layout, "自动更新（需要购买DLC才可生效）", self.checkbox_auto_update_on_start)

        # -------------- 区域：多进程 --------------
        self.collapsible_box_multiprocessing, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("多进程", top_layout)

        self.checkbox_enable_multiprocessing = create_checkbox(cfg.enable_multiprocessing)
        add_row(form_layout, "是否启用多进程功能", self.checkbox_enable_multiprocessing)

        self.checkbox_enable_super_fast_mode = create_checkbox(cfg.enable_super_fast_mode)
        add_row(form_layout, "是否启用超快速模式（并行活动）", self.checkbox_enable_super_fast_mode)

        self.spinbox_multiprocessing_pool_size = create_spin_box(cfg.multiprocessing_pool_size, minimum=-1)
        add_row(form_layout, "进程池大小(0=cpu核心数,-1=当前账号数(普通)/4*cpu(超快速),其他=进程数)", self.spinbox_multiprocessing_pool_size)

        # -------------- 区域：登录 --------------
        self.collapsible_box_login, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("登录", top_layout)

        self.checkbox_force_use_portable_chrome = create_checkbox(cfg.force_use_portable_chrome)
        add_row(form_layout, "强制使用便携版chrome", self.checkbox_force_use_portable_chrome)

        self.spinbox_force_use_chrome_major_version = create_spin_box(cfg.force_use_chrome_major_version)
        add_row(form_layout, "强制使用特定大版本的chrome（0表示默认版本）", self.spinbox_force_use_chrome_major_version)

        self.checkbox_run_in_headless_mode = create_checkbox(cfg.run_in_headless_mode)
        add_row(form_layout, "自动登录模式不显示浏览器界面", self.checkbox_run_in_headless_mode)

        self.login = LoginConfigUi(form_layout, cfg.login)

        # -------------- 区域：窗口大小调整 --------------
        self.collapsible_box_window_size, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("窗口大小调整", top_layout)

        self.checkbox_enable_change_cmd_buffer = create_checkbox(cfg.enable_change_cmd_buffer)
        add_row(form_layout, "是否修改命令行缓存大小，以避免运行日志被截断", self.checkbox_enable_change_cmd_buffer)

        self.checkbox_enable_max_console = create_checkbox(cfg.enable_max_console)
        add_row(form_layout, "是否最大化窗口", self.checkbox_enable_max_console)

        self.checkbox_enable_min_console = create_checkbox(cfg.enable_min_console)
        add_row(form_layout, "是否最小化窗口", self.checkbox_enable_min_console)

        # -------------- 区域：其他 --------------
        self.collapsible_box_others, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("其他", top_layout)

        self.checkbox_config_ui_enable_high_dpi = create_checkbox(cfg.config_ui_enable_high_dpi)
        add_row(form_layout, "是否启用高DPI模式（如4k屏，启用后请重启配置工具）", self.checkbox_config_ui_enable_high_dpi)

        self.checkbox_disable_cmd_quick_edit = create_checkbox(cfg.disable_cmd_quick_edit)
        add_row(form_layout, "是否禁用cmd命令行的快速编辑模式", self.checkbox_disable_cmd_quick_edit)

        self.checkbox_disable_sync_configs = create_checkbox(os.path.exists(disable_flag_file))
        add_row(form_layout, "是否禁用在本机自动备份还原配置功能", self.checkbox_disable_sync_configs)

        self.spinbox_notify_pay_expired_in_days = create_spin_box(cfg.notify_pay_expired_in_days, minimum=0)
        add_row(form_layout, "提前多少天提示付费过期", self.spinbox_notify_pay_expired_in_days)

        self.checkbox_allow_only_one_instance = create_checkbox(cfg.allow_only_one_instance)
        add_row(form_layout, "是否仅允许单个运行实例", self.checkbox_allow_only_one_instance)

        self.lineedit_majieluo_send_card_target_qq = create_lineedit(cfg.majieluo_send_card_target_qq, "填写要接收卡片的qq号")
        add_row(form_layout, "马杰洛新春版本赠送卡片目标QQ", self.lineedit_majieluo_send_card_target_qq)

        self.lineedit_majieluo_invite_uin_list = create_lineedit(list_to_str(cfg.majieluo_invite_uin_list),
                                                                 "填写马杰洛赠送礼包inviteUin列表，点赠送后查看链接中的inviteUin参数可知，使用英文逗号分开，示例：a34354ec3f37f2d8accd5766f549c36b, a34354ec3f37f2d8accd5766f549c36b, a34354ec3f37f2d8accd5766f549c36b")
        add_row(form_layout, "马杰洛赠送礼包inviteUin列表", self.lineedit_majieluo_invite_uin_list)

        self.combobox_log_level = create_combobox(cfg.log_level, [
            "debug",
            "info",
            "warning",
            "error",
            "critical",
        ])
        add_row(form_layout, "日志级别", self.combobox_log_level)

        self.spinbox_http_timeout = create_spin_box(cfg.http_timeout)
        add_row(form_layout, "HTTP超时（秒）", self.spinbox_http_timeout)

        self.retry = RetryConfigUi(form_layout, cfg.retry)

        self.setLayout(make_scroll_layout(top_layout))

        init_collapsible_box_size(self)

    def update_config(self, cfg: CommonConfig):
        cfg.force_use_portable_chrome = self.checkbox_force_use_portable_chrome.isChecked()
        cfg.force_use_chrome_major_version = self.spinbox_force_use_chrome_major_version.value()
        cfg.run_in_headless_mode = self.checkbox_run_in_headless_mode.isChecked()
        cfg.config_ui_enable_high_dpi = self.checkbox_config_ui_enable_high_dpi.isChecked()
        cfg.disable_cmd_quick_edit = self.checkbox_disable_cmd_quick_edit.isChecked()
        cfg.enable_change_cmd_buffer = self.checkbox_enable_change_cmd_buffer.isChecked()
        cfg.enable_max_console = self.checkbox_enable_max_console.isChecked()
        cfg.enable_min_console = self.checkbox_enable_min_console.isChecked()
        cfg.enable_multiprocessing = self.checkbox_enable_multiprocessing.isChecked()
        cfg.enable_super_fast_mode = self.checkbox_enable_super_fast_mode.isChecked()
        cfg.multiprocessing_pool_size = self.spinbox_multiprocessing_pool_size.value()
        cfg.check_update_on_start = self.checkbox_check_update_on_start.isChecked()
        cfg.check_update_on_end = self.checkbox_check_update_on_end.isChecked()
        cfg.auto_update_on_start = self.checkbox_auto_update_on_start.isChecked()
        cfg.notify_pay_expired_in_days = self.spinbox_notify_pay_expired_in_days.value()
        cfg.allow_only_one_instance = self.checkbox_allow_only_one_instance.isChecked()
        cfg.try_auto_bind_new_activity = self.checkbox_try_auto_bind_new_activity.isChecked()
        cfg.force_sync_bind_with_djc = self.checkbox_force_sync_bind_with_djc.isChecked()

        cfg.http_timeout = self.spinbox_http_timeout.value()
        cfg.log_level = self.combobox_log_level.currentText()
        cfg.majieluo_send_card_target_qq = self.lineedit_majieluo_send_card_target_qq.text()
        cfg.auto_send_card_target_qqs = str_to_list(self.lineedit_auto_send_card_target_qqs.text())
        cfg.majieluo_invite_uin_list = str_to_list(self.lineedit_majieluo_invite_uin_list.text())

        self.login.update_config(cfg.login)
        self.retry.update_config(cfg.retry)
        for idx, team in enumerate(self.fixed_teams):
            team.update_config(cfg.fixed_teams[idx])

        # 特殊处理基于标记文件的开关
        if self.checkbox_disable_sync_configs.isChecked():
            if not os.path.exists(disable_flag_file):
                with open(disable_flag_file, 'w', encoding='utf-8') as f:
                    f.write('ok')
        else:
            if os.path.exists(disable_flag_file):
                if os.path.isfile(disable_flag_file):
                    os.remove(disable_flag_file)
                else:
                    shutil.rmtree(disable_flag_file, ignore_errors=True)


class LoginConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: LoginConfig, parent=None):
        super(LoginConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: LoginConfig):
        add_form_seperator(form_layout, "超时时长(秒)")

        self.spinbox_max_retry_count = create_spin_box(cfg.max_retry_count)
        add_row(form_layout, "重试次数", self.spinbox_max_retry_count)

        self.spinbox_retry_wait_time = create_spin_box(cfg.retry_wait_time)
        add_row(form_layout, "重试间隔时间", self.spinbox_retry_wait_time)

        self.spinbox_open_url_wait_time = create_spin_box(cfg.open_url_wait_time)
        add_row(form_layout, "打开网页后等待时长", self.spinbox_open_url_wait_time)

        self.spinbox_load_page_timeout = create_spin_box(cfg.load_page_timeout)
        add_row(form_layout, "加载页面的超时时间", self.spinbox_load_page_timeout)

        self.spinbox_load_login_iframe_timeout = create_spin_box(cfg.load_login_iframe_timeout)
        add_row(form_layout, "点击登录按钮后的超时时间", self.spinbox_load_login_iframe_timeout)

        self.spinbox_login_timeout = create_spin_box(cfg.login_timeout)
        add_row(form_layout, "登录的超时时间", self.spinbox_login_timeout)

        self.spinbox_login_finished_timeout = create_spin_box(cfg.login_finished_timeout)
        add_row(form_layout, "等待登录完成的超时时间", self.spinbox_login_finished_timeout)

        add_form_seperator(form_layout, "自动处理滑动验证码")

        self.checkbox_auto_resolve_captcha = create_checkbox(cfg.auto_resolve_captcha)
        add_row(form_layout, "启用", self.checkbox_auto_resolve_captcha)

        self.doublespinbox_move_captcha_delta_width_rate = create_double_spin_box(cfg.move_captcha_delta_width_rate)
        self.doublespinbox_move_captcha_delta_width_rate.setSingleStep(0.01)
        add_row(form_layout, "每次尝试滑动验证码多少倍滑块宽度的偏移值", self.doublespinbox_move_captcha_delta_width_rate)

    def update_config(self, cfg: LoginConfig):
        cfg.max_retry_count = self.spinbox_max_retry_count.value()
        cfg.retry_wait_time = self.spinbox_retry_wait_time.value()
        cfg.open_url_wait_time = self.spinbox_open_url_wait_time.value()
        cfg.load_page_timeout = self.spinbox_load_page_timeout.value()
        cfg.load_login_iframe_timeout = self.spinbox_load_login_iframe_timeout.value()
        cfg.login_timeout = self.spinbox_login_timeout.value()
        cfg.login_finished_timeout = self.spinbox_login_finished_timeout.value()
        cfg.auto_resolve_captcha = self.checkbox_auto_resolve_captcha.isChecked()
        cfg.move_captcha_delta_width_rate = self.doublespinbox_move_captcha_delta_width_rate.value()


class RetryConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: RetryConfig, parent=None):
        super(RetryConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: RetryConfig):
        self.spinbox_request_wait_time = create_spin_box(cfg.request_wait_time)
        add_row(form_layout, "请求间隔时间", self.spinbox_request_wait_time)

        self.spinbox_max_retry_count = create_spin_box(cfg.max_retry_count)
        add_row(form_layout, "最大重试次数", self.spinbox_max_retry_count)

        self.spinbox_retry_wait_time = create_spin_box(cfg.retry_wait_time)
        add_row(form_layout, "重试间隔时间", self.spinbox_retry_wait_time)

    def update_config(self, cfg: RetryConfig):
        cfg.request_wait_time = self.spinbox_request_wait_time.value()
        cfg.max_retry_count = self.spinbox_max_retry_count.value()
        cfg.retry_wait_time = self.spinbox_retry_wait_time.value()


class FixedTeamConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: FixedTeamConfig, parent=None):
        super(FixedTeamConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: FixedTeamConfig):
        add_form_seperator(form_layout, f"心悦战场固定队 - {cfg.id}")

        self.checkbox_enable = create_checkbox(cfg.enable)
        add_row(form_layout, "启用", self.checkbox_enable)

        self.lineedit_id = create_lineedit(cfg.id, "固定队伍id，仅用于本地区分用")
        add_row(form_layout, "队伍id", self.lineedit_id)

        self.lineedit_members = create_lineedit(list_to_str(cfg.members), "固定队成员，必须是两个，则必须都配置在本地的账号列表中了，否则将报错，不生效")
        self.lineedit_members.setValidator(QQListValidator())
        add_row(form_layout, "成员", self.lineedit_members)

    def update_config(self, cfg: FixedTeamConfig):
        cfg.enable = self.checkbox_enable.isChecked()
        cfg.id = self.lineedit_id.text()
        cfg.members = str_to_list(self.lineedit_members.text())


class AccountConfigUi(QWidget):
    login_mode_bidict = BiDict({
        # "手动登录": "by_hand",
        "扫码/点击头像登录": "qr_login",
        "账号密码自动登录": "auto_login",
    })

    def __init__(self, cfg: AccountConfig, common_cfg: CommonConfig, parent=None):
        super(AccountConfigUi, self).__init__(parent)

        self.common_cfg = common_cfg

        self.from_config(cfg)

    def from_config(self, cfg: AccountConfig):
        top_layout = QVBoxLayout()

        # -------------- 区域：账号信息 --------------
        form_layout = QFormLayout()
        top_layout.addLayout(form_layout)

        self.checkbox_enable = create_checkbox(cfg.enable)
        add_row(form_layout, "启用该账号", self.checkbox_enable)

        self.lineedit_name = create_lineedit(cfg.name, "账号名称，仅用于区分不同账号，请确保不同账号名称不一样")
        add_row(form_layout, "账号名称", self.lineedit_name)

        self.combobox_login_mode = create_combobox(self.login_mode_bidict.val_to_key.get(cfg.login_mode, "扫码/点击头像登录"), list(self.login_mode_bidict.key_to_val.keys()))
        add_row(form_layout, "登录模式", self.combobox_login_mode)

        # -------------- 区域：QQ信息 --------------
        self.collapsible_box_account_password, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("账号密码", top_layout)

        self.account_info = AccountInfoConfigUi(form_layout, cfg.account_info)

        self.combobox_login_mode.currentTextChanged.connect(self.on_login_mode_change)
        self.on_login_mode_change(self.combobox_login_mode.currentText(), in_init_step=True)

        # -------------- 区域：选填和必填分割线 --------------
        add_vbox_seperator(top_layout, "以下内容为选填内容，不填仍可正常运行，不过部分活动将无法领取")

        # -------------- 区域：道聚城 --------------
        self.collapsible_box_djc, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("道聚城", top_layout)

        self.checkbox_cannot_bind_dnf = create_checkbox(cfg.cannot_bind_dnf)
        add_row(form_layout, "无法在道聚城绑定dnf", self.checkbox_cannot_bind_dnf)

        self.mobile_game_role_info = MobileGameRoleInfoConfigUi(form_layout, cfg.mobile_game_role_info)

        # -------------- 区域：道聚城兑换 --------------
        self.collapsible_box_djc_exchange, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("道聚城兑换", top_layout)

        self.try_set_default_exchange_items_for_cfg(cfg)
        self.exchange_items = {}
        for exchange_item in cfg.exchange_items:
            self.exchange_items[exchange_item.iGoodsId] = ExchangeItemConfigUi(form_layout, exchange_item)

        # -------------- 区域：心悦特权专区兑换 --------------
        self.collapsible_box_djc_exchange, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("心悦特权专区兑换", top_layout)

        self.try_set_default_xinyue_exchange_items_for_cfg(cfg)
        self.xinyue_exchange_items = {}
        for exchange_item in cfg.xinyue_operations:
            self.xinyue_exchange_items[exchange_item.unique_key()] = XinyueOperationConfigUi(form_layout, exchange_item)

        # -------------- 区域：集卡 --------------
        self.collapsible_box_ark_lottery, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("集卡", top_layout)
        self.ark_lottery = ArkLotteryConfigUi(form_layout, cfg.ark_lottery, cfg, self.common_cfg)

        # -------------- 区域：dnf助手 --------------
        self.collapsible_box_dnf_helper_info, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("dnf助手", top_layout)
        self.dnf_helper_info = DnfHelperInfoConfigUi(form_layout, cfg.dnf_helper_info)

        # -------------- 区域：dnf论坛 --------------
        self.collapsible_box_dnf_bbs, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("dnf论坛", top_layout)

        self.lineedit_dnf_bbs_formhash = create_lineedit(cfg.dnf_bbs_formhash, "形如：8df1d678，具体获取方式请看config.example.toml示例配置文件中dnf_bbs_formhash字段的说明")
        add_row(form_layout, "dnf论坛签到formhash", self.lineedit_dnf_bbs_formhash)

        self.lineedit_dnf_bbs_cookie = create_lineedit(cfg.dnf_bbs_cookie, "请填写论坛请求的完整cookie串，具体获取方式请看config.example.toml示例配置文件中dnf_bbs_cookie字段的说明")
        add_row(form_layout, "dnf论坛cookie", self.lineedit_dnf_bbs_cookie)

        self.lineedit_colg_cookie = create_lineedit(cfg.colg_cookie, "请填写论坛请求的完整cookie串，具体获取方式请看config.example.toml示例配置文件中colg_cookie字段的说明")
        add_row(form_layout, "colg cookie", self.lineedit_colg_cookie)

        # -------------- 区域：会员关怀 --------------
        self.collapsible_box_vip_mentor, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("会员关怀", top_layout)
        self.vip_mentor = VipMentorConfigUi(form_layout, cfg.vip_mentor, cfg, self.common_cfg)

        # -------------- 区域：hello语音 --------------
        self.collapsible_box_hello_voice, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("hello语音", top_layout)
        self.hello_voice = HelloVoiceInfoConfigUi(form_layout, cfg.hello_voice)

        # -------------- 区域：其他 --------------
        self.collapsible_box_others, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("其他", top_layout)

        self.lineedit_ozma_ignored_rolename_list = create_lineedit(list_to_str(cfg.ozma_ignored_rolename_list), "填写角色名列表，使用英文逗号分开，示例：卢克奶妈一号, 卢克奶妈二号, 卢克奶妈三号")
        add_row(form_layout, "不参与奥兹玛竞速活动切换角色的角色名列表", self.lineedit_ozma_ignored_rolename_list)

        self.checkbox_comic_lottery = create_checkbox(cfg.comic_lottery)
        add_row(form_layout, "漫画活动是否自动抽奖（建议手动领完需要的活动后开启该开关）", self.checkbox_comic_lottery)

        # -------------- 区域：活动开关 --------------
        self.collapsible_box_function_switches, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("活动开关", top_layout)
        self.function_switches = FunctionSwitchesConfigUi(form_layout, cfg.function_switches)

        # -------------- 区域代码结束 --------------
        self.setLayout(make_scroll_layout(top_layout))

        init_collapsible_box_size(self)

    def update_config(self, cfg: AccountConfig):
        cfg.enable = self.checkbox_enable.isChecked()
        cfg.name = self.lineedit_name.text()
        cfg.login_mode = self.login_mode_bidict.key_to_val[self.combobox_login_mode.currentText()]
        cfg.cannot_bind_dnf = self.checkbox_cannot_bind_dnf.isChecked()

        cfg.ozma_ignored_rolename_list = str_to_list(self.lineedit_ozma_ignored_rolename_list.text())
        cfg.comic_lottery = self.checkbox_comic_lottery.isChecked()

        cfg.dnf_bbs_formhash = self.lineedit_dnf_bbs_formhash.text()
        cfg.dnf_bbs_cookie = self.lineedit_dnf_bbs_cookie.text()
        cfg.colg_cookie = self.lineedit_colg_cookie.text()

        self.account_info.update_config(cfg.account_info)
        self.function_switches.update_config(cfg.function_switches)
        self.mobile_game_role_info.update_config(cfg.mobile_game_role_info)

        self.try_set_default_exchange_items_for_cfg(cfg)
        for iGoodsId, exchange_item in self.exchange_items.items():
            item_cfg = cfg.get_exchange_item_by_iGoodsId(iGoodsId)
            if item_cfg is None:
                continue

            exchange_item.update_config(item_cfg)

        self.try_set_default_xinyue_exchange_items_for_cfg(cfg)
        for unique_key, exchange_item in self.xinyue_exchange_items.items():
            item_cfg = cfg.get_xinyue_exchange_item_by_unique_key(unique_key)
            if item_cfg is None:
                continue

            exchange_item.update_config(item_cfg)

        self.ark_lottery.update_config(cfg.ark_lottery)
        self.vip_mentor.update_config(cfg.vip_mentor)
        self.dnf_helper_info.update_config(cfg.dnf_helper_info)
        self.hello_voice.update_config(cfg.hello_voice)

        # 这些是动态生成的，不需要保存到配置表中
        for attr in ["sDjcSign"]:
            if not hasattr(cfg, attr):
                continue
            delattr(cfg, attr)

    def try_set_default_exchange_items_for_cfg(self, cfg: AccountConfig):
        all_item_ids = set()
        for item in cfg.exchange_items:
            all_item_ids.add(item.iGoodsId)

        # 特殊处理下道聚城兑换，若相应配置不存在，咋加上默认不领取的配置，确保界面显示出来
        default_items = [
            ("111", "高级装扮兑换券（无期限）"),
            ("753", "装备品级调整箱（5个）"),
            ("755", "魔界抗疲劳秘药（10点）"),
            ("107", "达人之契约（3天）"),
            ("110", "成长之契约（3天）"),
            ("382", "晶之契约（3天）"),
        ]
        for iGoodsId, sGoodsName in default_items:
            if iGoodsId in all_item_ids:
                continue

            item = ExchangeItemConfig()
            item.iGoodsId = iGoodsId
            item.sGoodsName = sGoodsName
            item.count = 0
            cfg.exchange_items.append(item)

    def try_set_default_xinyue_exchange_items_for_cfg(self, cfg: AccountConfig):
        all_item_keys = set()
        for item in cfg.xinyue_operations:
            all_item_keys.add(item.unique_key())

        # 特殊处理下心悦兑换，若相应配置不存在，咋加上默认不领取的配置，确保界面显示出来
        default_items = [
            ("747693", "1537766", "装备提升礼盒(需10点成就点)"),
            ("747759", "1537690", "装备提升礼盒(需30点勇士币)(每日20次)"),
        ]
        for iFlowId, package_id, sFlowName in default_items:
            item = XinYueOperationConfig()
            item.iFlowId = iFlowId
            item.package_id = package_id
            item.sFlowName = sFlowName
            item.count = 0

            if item.unique_key() in all_item_keys:
                continue

            cfg.xinyue_operations.append(item)

    def on_login_mode_change(self, text, in_init_step=False):
        disable = text != self.login_mode_bidict.val_to_key['auto_login']

        # 需要排除一个特例：
        # 启动时界面还未显示时，所有组件都是hidden状态
        # 此时如果是自动登录模式，不需要特别调用setHidden(False)，因为组件在gui初始化完毕后都默认是启用的
        # 此时如果调用了，会出现在主窗口弹出来之前，快速显示并消失各个账号的账号密码登录窗口，看上去很奇怪
        need_set_hidden = not (in_init_step and not disable)
        if need_set_hidden:
            self.collapsible_box_account_password.setHidden(disable)
        self.collapsible_box_account_password.set_fold(disable)
        self.account_info.setDisabled(disable)


class AccountInfoConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: AccountInfoConfig, parent=None):
        super(AccountInfoConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: AccountInfoConfig):
        self.lineedit_account = create_lineedit(cfg.account)
        add_row(form_layout, "QQ账号", self.lineedit_account)

        self.lineedit_password = create_lineedit(cfg.password, "使用账号密码自动登录有风险_请理解这个功能到底如何使用你的账号密码后再决定是否使用")
        self.lineedit_password.setEchoMode(QLineEdit.Password)

        btn_show_password = create_pushbutton("按住显示密码")
        btn_show_password.pressed.connect(self.show_password)
        btn_show_password.released.connect(self.hide_password)

        layout = QHBoxLayout()
        layout.addWidget(self.lineedit_password)
        layout.addWidget(btn_show_password)
        add_row(form_layout, "QQ密码", layout)

    def show_password(self):
        self.lineedit_password.setEchoMode(QLineEdit.Normal)

    def hide_password(self):
        self.lineedit_password.setEchoMode(QLineEdit.Password)

    def update_config(self, cfg: AccountInfoConfig):
        cfg.account = self.lineedit_account.text()
        cfg.password = self.lineedit_password.text()

    def setDisabled(self, disabled: bool) -> None:
        super().setDisabled(disabled)

        self.lineedit_account.setDisabled(disabled)
        self.lineedit_password.setDisabled(disabled)


class FunctionSwitchesConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: FunctionSwitchesConfig, parent=None):
        super(FunctionSwitchesConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: FunctionSwitchesConfig):
        add_form_seperator(form_layout, f"各功能开关")

        self.checkbox_disable_most_activities = create_checkbox(cfg.disable_most_activities)
        add_row(form_layout, "禁用绝大部分活动", self.checkbox_disable_most_activities)

        self.checkbox_disable_share = create_checkbox(cfg.disable_share)
        add_row(form_layout, "禁用分享功能", self.checkbox_disable_share)

        # ----------------------------------------------------------
        add_form_seperator(form_layout, "普通skey")

        self.checkbox_get_djc = create_checkbox(cfg.get_djc)
        add_row(form_layout, "领取道聚城", self.checkbox_get_djc)

        self.checkbox_make_wish = create_checkbox(cfg.make_wish)
        add_row(form_layout, "道聚城许愿", self.checkbox_make_wish)

        self.checkbox_get_xinyue = create_checkbox(cfg.get_xinyue)
        add_row(form_layout, "心悦特权专区", self.checkbox_get_xinyue)

        self.checkbox_get_credit_xinyue_gift = create_checkbox(cfg.get_credit_xinyue_gift)
        add_row(form_layout, "腾讯游戏信用相关礼包", self.checkbox_get_credit_xinyue_gift)

        self.checkbox_get_heizuan_gift = create_checkbox(cfg.get_heizuan_gift)
        add_row(form_layout, "每月黑钻等级礼包", self.checkbox_get_heizuan_gift)

        # self.checkbox_get_dnf_shanguang = create_checkbox(cfg.get_dnf_shanguang)
        # add_row(form_layout, "DNF闪光杯第三期", self.checkbox_get_dnf_shanguang)

        self.checkbox_get_qq_video = create_checkbox(cfg.get_qq_video)
        add_row(form_layout, "qq视频活动", self.checkbox_get_qq_video)

        self.checkbox_get_qq_video_amesvr = create_checkbox(cfg.get_qq_video_amesvr)
        add_row(form_layout, "qq视频-AME活动", self.checkbox_get_qq_video_amesvr)

        self.checkbox_get_dnf_helper_chronicle = create_checkbox(cfg.get_dnf_helper_chronicle)
        add_row(form_layout, "dnf助手编年史（需配置助手userId和token和uniqueRoleId）", self.checkbox_get_dnf_helper_chronicle)

        self.checkbox_get_dnf_helper = create_checkbox(cfg.get_dnf_helper)
        add_row(form_layout, "dnf助手活动（需配置助手userId和token）", self.checkbox_get_dnf_helper)

        self.checkbox_get_hello_voice = create_checkbox(cfg.get_hello_voice)
        add_row(form_layout, "hello语音奖励兑换（需配置hello语音的用户ID）", self.checkbox_get_hello_voice)

        self.checkbox_get_dnf_welfare = create_checkbox(cfg.get_dnf_welfare)
        add_row(form_layout, "DNF福利中心兑换", self.checkbox_get_dnf_welfare)

        self.checkbox_get_xinyue_financing = create_checkbox(cfg.get_xinyue_financing)
        add_row(form_layout, "心悦app理财礼卡", self.checkbox_get_xinyue_financing)

        self.checkbox_get_xinyue_cat = create_checkbox(cfg.get_xinyue_cat)
        add_row(form_layout, "心悦猫咪", self.checkbox_get_xinyue_cat)

        self.checkbox_get_xinyue_weekly_gift = create_checkbox(cfg.get_xinyue_weekly_gift)
        add_row(form_layout, "心悦app周礼包", self.checkbox_get_xinyue_weekly_gift)

        self.checkbox_get_majieluo = create_checkbox(cfg.get_majieluo)
        add_row(form_layout, "DNF马杰洛的规划", self.checkbox_get_majieluo)

        self.checkbox_get_dnf_bbs_signin = create_checkbox(cfg.get_dnf_bbs_signin)
        add_row(form_layout, "dnf论坛签到", self.checkbox_get_dnf_bbs_signin)

        self.checkbox_get_dnf_luodiye = create_checkbox(cfg.get_dnf_luodiye)
        add_row(form_layout, "DNF落地页", self.checkbox_get_dnf_luodiye)

        self.checkbox_get_dnf_wegame = create_checkbox(cfg.get_dnf_wegame)
        add_row(form_layout, "WeGame", self.checkbox_get_dnf_wegame)

        self.checkbox_get_dnf_collection = create_checkbox(cfg.get_dnf_collection)
        add_row(form_layout, "DNF集合站", self.checkbox_get_dnf_collection)

        self.checkbox_get_dnf_fuqian = create_checkbox(cfg.get_dnf_fuqian)
        add_row(form_layout, "DNF福签大作战", self.checkbox_get_dnf_fuqian)

        self.checkbox_get_dnf_ozma = create_checkbox(cfg.get_dnf_ozma)
        add_row(form_layout, "DNF奥兹玛竞速", self.checkbox_get_dnf_ozma)

        self.checkbox_get_colg_signin = create_checkbox(cfg.get_colg_signin)
        add_row(form_layout, "colg每日签到和积分领取", self.checkbox_get_colg_signin)

        self.checkbox_get_xinyue_app = create_checkbox(cfg.get_xinyue_app)
        add_row(form_layout, "心悦app兑换", self.checkbox_get_xinyue_app)

        self.checkbox_get_dnf_pk = create_checkbox(cfg.get_dnf_pk)
        add_row(form_layout, "DNF格斗大赛", self.checkbox_get_dnf_pk)

        self.checkbox_get_dnf_xinyue = create_checkbox(cfg.get_dnf_xinyue)
        add_row(form_layout, "心悦", self.checkbox_get_dnf_xinyue)

        self.checkbox_get_dnf_strong = create_checkbox(cfg.get_dnf_strong)
        add_row(form_layout, "DNF强者之路", self.checkbox_get_dnf_strong)

        self.checkbox_get_dnf_comic = create_checkbox(cfg.get_dnf_comic)
        add_row(form_layout, "DNF漫画", self.checkbox_get_dnf_comic)

        self.checkbox_get_dnf_13 = create_checkbox(cfg.get_dnf_13)
        add_row(form_layout, "DNF十三周年庆", self.checkbox_get_dnf_13)

        self.checkbox_get_dnf_my_story = create_checkbox(cfg.get_dnf_my_story)
        add_row(form_layout, "我的dnf13周年活动", self.checkbox_get_dnf_my_story)

        self.checkbox_get_dnf_reserve = create_checkbox(cfg.get_dnf_reserve)
        add_row(form_layout, "刃影预约活动", self.checkbox_get_dnf_reserve)

        self.checkbox_get_dnf_anniversary = create_checkbox(cfg.get_dnf_anniversary)
        add_row(form_layout, "DNF周年庆登录活动", self.checkbox_get_dnf_anniversary)

        self.checkbox_get_dnf_kol = create_checkbox(cfg.get_dnf_kol)
        add_row(form_layout, "KOL", self.checkbox_get_dnf_kol)

        self.checkbox_get_maoxian = create_checkbox(cfg.get_maoxian)
        add_row(form_layout, "勇士的冒险补给", self.checkbox_get_maoxian)

        # ----------------------------------------------------------
        add_form_seperator(form_layout, "QQ空间pskey")

        self.checkbox_get_ark_lottery = create_checkbox(cfg.get_ark_lottery)
        add_row(form_layout, "集卡", self.checkbox_get_ark_lottery)

        self.checkbox_get_vip_mentor = create_checkbox(cfg.get_vip_mentor)
        add_row(form_layout, "会员关怀", self.checkbox_get_vip_mentor)

        self.checkbox_get_dnf_super_vip = create_checkbox(cfg.get_dnf_super_vip)
        add_row(form_layout, "超级会员", self.checkbox_get_dnf_super_vip)

        self.checkbox_get_dnf_yellow_diamond = create_checkbox(cfg.get_dnf_yellow_diamond)
        add_row(form_layout, "黄钻", self.checkbox_get_dnf_yellow_diamond)

        # ----------------------------------------------------------
        add_form_seperator(form_layout, "安全管家pskey")

        self.checkbox_get_guanjia = create_checkbox(cfg.get_guanjia)
        add_row(form_layout, "管家蚊子腿", self.checkbox_get_guanjia)

    def update_config(self, cfg: FunctionSwitchesConfig):
        cfg.disable_most_activities = self.checkbox_disable_most_activities.isChecked()
        cfg.disable_share = self.checkbox_disable_share.isChecked()

        cfg.get_djc = self.checkbox_get_djc.isChecked()
        cfg.make_wish = self.checkbox_make_wish.isChecked()
        cfg.get_xinyue = self.checkbox_get_xinyue.isChecked()
        cfg.get_credit_xinyue_gift = self.checkbox_get_credit_xinyue_gift.isChecked()
        cfg.get_heizuan_gift = self.checkbox_get_heizuan_gift.isChecked()
        # cfg.get_dnf_shanguang = self.checkbox_get_dnf_shanguang.isChecked()
        cfg.get_qq_video = self.checkbox_get_qq_video.isChecked()
        cfg.get_qq_video_amesvr = self.checkbox_get_qq_video_amesvr.isChecked()
        cfg.get_dnf_helper_chronicle = self.checkbox_get_dnf_helper_chronicle.isChecked()
        cfg.get_dnf_helper = self.checkbox_get_dnf_helper.isChecked()
        cfg.get_hello_voice = self.checkbox_get_hello_voice.isChecked()
        cfg.get_dnf_welfare = self.checkbox_get_dnf_welfare.isChecked()
        cfg.get_xinyue_financing = self.checkbox_get_xinyue_financing.isChecked()
        cfg.get_xinyue_cat = self.checkbox_get_xinyue_cat.isChecked()
        cfg.get_xinyue_weekly_gift = self.checkbox_get_xinyue_weekly_gift.isChecked()
        cfg.get_majieluo = self.checkbox_get_majieluo.isChecked()
        cfg.get_dnf_bbs_signin = self.checkbox_get_dnf_bbs_signin.isChecked()
        cfg.get_dnf_luodiye = self.checkbox_get_dnf_luodiye.isChecked()
        cfg.get_dnf_wegame = self.checkbox_get_dnf_wegame.isChecked()
        cfg.get_dnf_collection = self.checkbox_get_dnf_collection.isChecked()
        cfg.get_dnf_fuqian = self.checkbox_get_dnf_fuqian.isChecked()
        cfg.get_dnf_ozma = self.checkbox_get_dnf_ozma.isChecked()
        cfg.get_colg_signin = self.checkbox_get_colg_signin.isChecked()
        cfg.get_xinyue_app = self.checkbox_get_xinyue_app.isChecked()
        cfg.get_dnf_pk = self.checkbox_get_dnf_pk.isChecked()
        cfg.get_dnf_xinyue = self.checkbox_get_dnf_xinyue.isChecked()
        cfg.get_dnf_strong = self.checkbox_get_dnf_strong.isChecked()
        cfg.get_dnf_comic = self.checkbox_get_dnf_comic.isChecked()
        cfg.get_dnf_13 = self.checkbox_get_dnf_13.isChecked()
        cfg.get_dnf_my_story = self.checkbox_get_dnf_my_story.isChecked()
        cfg.get_dnf_reserve = self.checkbox_get_dnf_reserve.isChecked()
        cfg.get_dnf_anniversary = self.checkbox_get_dnf_anniversary.isChecked()
        cfg.get_dnf_kol = self.checkbox_get_dnf_kol.isChecked()
        cfg.get_maoxian = self.checkbox_get_maoxian.isChecked()

        cfg.get_ark_lottery = self.checkbox_get_ark_lottery.isChecked()
        cfg.get_vip_mentor = self.checkbox_get_vip_mentor.isChecked()
        cfg.get_dnf_super_vip = self.checkbox_get_dnf_super_vip.isChecked()
        cfg.get_dnf_yellow_diamond = self.checkbox_get_dnf_yellow_diamond.isChecked()

        cfg.get_guanjia = self.checkbox_get_guanjia.isChecked()


class MobileGameRoleInfoConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: MobileGameRoleInfoConfig, parent=None):
        super(MobileGameRoleInfoConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: MobileGameRoleInfoConfig):
        self.combobox_game_name = create_combobox(cfg.game_name, ['无', '任意手游', *sorted(get_name_2_mobile_game_info_map().keys())])
        add_row(form_layout, "完成礼包达人任务的手游名称", self.combobox_game_name)

    def update_config(self, cfg: MobileGameRoleInfoConfig):
        cfg.game_name = self.combobox_game_name.currentText()


class ExchangeItemConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: ExchangeItemConfig, parent=None):
        super(ExchangeItemConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: ExchangeItemConfig):
        self.spinbox_count = create_spin_box(cfg.count, 10)
        add_row(form_layout, f"{cfg.sGoodsName}", self.spinbox_count)

    def update_config(self, cfg: ExchangeItemConfig):
        cfg.count = self.spinbox_count.value()


class XinyueOperationConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: XinYueOperationConfig, parent=None):
        super(XinyueOperationConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: XinYueOperationConfig):
        self.spinbox_count = create_spin_box(cfg.count, 99)
        add_row(form_layout, f"{cfg.sFlowName}", self.spinbox_count)

    def update_config(self, cfg: XinYueOperationConfig):
        cfg.count = self.spinbox_count.value()


class ArkLotteryConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: ArkLotteryConfig, account_cfg: AccountConfig, common_cfg: CommonConfig, parent=None):
        super(ArkLotteryConfigUi, self).__init__(parent)

        self.account_cfg = account_cfg
        self.common_cfg = common_cfg

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: ArkLotteryConfig):
        self.combobox_lucky_dnf_server_name = create_combobox(dnf_server_id_to_name(cfg.lucky_dnf_server_id), dnf_server_name_list())
        add_row(form_layout, "幸运勇士区服名称", self.combobox_lucky_dnf_server_name)

        self.lineedit_lucky_dnf_role_id = create_lineedit(cfg.lucky_dnf_role_id, "角色ID（不是角色名称！！！），形如 1282822，可以点击下面的选项框来选择角色（需登录）")
        add_row(form_layout, "幸运勇士角色ID", self.lineedit_lucky_dnf_role_id)

        self.role_selector = RoleSelector("幸运勇士", self.combobox_lucky_dnf_server_name, self.lineedit_lucky_dnf_role_id, self.account_cfg, self.common_cfg)
        add_row(form_layout, "查询角色（需要登录）", self.role_selector.combobox_role_name)

        self.checkbox_need_take_awards = create_checkbox(cfg.need_take_awards)
        add_row(form_layout, "领取礼包", self.checkbox_need_take_awards)

        cost_all_cards_and_do_lottery = cfg.act_id_to_cost_all_cards_and_do_lottery.get(zzconfig().actid, False)
        self.checkbox_cost_all_cards_and_do_lottery = create_checkbox(cost_all_cards_and_do_lottery)
        add_row(form_layout, "是否消耗所有卡牌来抽奖", self.checkbox_cost_all_cards_and_do_lottery)

    def update_config(self, cfg: ArkLotteryConfig):
        cfg.lucky_dnf_server_id = dnf_server_name_to_id(self.combobox_lucky_dnf_server_name.currentText())
        cfg.lucky_dnf_role_id = self.lineedit_lucky_dnf_role_id.text()

        cfg.need_take_awards = self.checkbox_need_take_awards.isChecked()

        cfg.act_id_to_cost_all_cards_and_do_lottery[zzconfig().actid] = self.checkbox_cost_all_cards_and_do_lottery.isChecked()


class VipMentorConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: VipMentorConfig, account_cfg: AccountConfig, common_cfg: CommonConfig, parent=None):
        super(VipMentorConfigUi, self).__init__(parent)

        self.account_cfg = account_cfg
        self.common_cfg = common_cfg

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: VipMentorConfig):
        self.spinbox_take_index = create_spin_box(cfg.take_index, 3, 1)
        add_row(form_layout, "兑换数目", self.spinbox_take_index)

        self.combobox_guanhuai_dnf_server_name = create_combobox(dnf_server_id_to_name(cfg.guanhuai_dnf_server_id), dnf_server_name_list())
        add_row(form_layout, "关怀礼包角色区服名称", self.combobox_guanhuai_dnf_server_name)

        self.lineedit_guanhuai_dnf_role_id = create_lineedit(cfg.guanhuai_dnf_role_id, "角色ID（不是角色名称！！！），形如 1282822，可以点击下面的选项框来选择角色（需登录）")
        add_row(form_layout, "关怀礼包角色角色ID", self.lineedit_guanhuai_dnf_role_id)

        self.role_selector = RoleSelector("会员关怀", self.combobox_guanhuai_dnf_server_name, self.lineedit_guanhuai_dnf_role_id, self.account_cfg, self.common_cfg)
        add_row(form_layout, "查询角色（需要登录）", self.role_selector.combobox_role_name)

    def update_config(self, cfg: VipMentorConfig):
        cfg.take_index = self.spinbox_take_index.value()

        cfg.guanhuai_dnf_server_id = dnf_server_name_to_id(self.combobox_guanhuai_dnf_server_name.currentText())
        cfg.guanhuai_dnf_role_id = self.lineedit_guanhuai_dnf_role_id.text()


class RoleSelector(QWidget):
    combobox_role_name_placeholder = "点我查询当前服务器的角色列表，可能会卡一会"

    def __init__(self, ctx, combobox_server_name: MyComboBox, lineedit_role_id: QLineEdit, account_cfg: AccountConfig, common_cfg: CommonConfig, parent=None):
        super(RoleSelector, self).__init__(parent)

        self.ctx = ctx
        self.combobox_server_name = combobox_server_name
        self.lineedit_role_id = lineedit_role_id
        self.account_cfg = account_cfg
        self.common_cfg = common_cfg

        self.server_id_to_roles = {}  # type: Dict[str, List[DnfRoleInfo]]

        self.combobox_role_name = create_combobox(self.combobox_role_name_placeholder, [self.combobox_role_name_placeholder])
        self.combobox_role_name.clicked.connect(self.on_role_name_clicked)
        self.combobox_role_name.activated.connect(self.on_role_name_select)

        self.combobox_server_name.activated.connect(self.on_server_select)

    def on_role_name_clicked(self):
        server_id = self.get_server_id()
        if server_id == "":
            show_message("出错了", f"请先选择{self.ctx}服务器")
            return

        if len(self.get_roles()) == 0:
            logger.info("需要查询角色信息")

            djcHelper = DjcHelper(self.account_cfg, self.common_cfg)
            djcHelper.fetch_pskey()
            djcHelper.check_skey_expired()
            djcHelper.get_bind_role_list()

            self.server_id_to_roles[server_id] = djcHelper.query_dnf_rolelist(server_id)

            self.update_role_names()

    def on_role_name_select(self, index: int):
        roles = self.get_roles()
        if len(roles) == 0:
            return

        role = roles[index]
        logging.info(f"选择的幸运角色为{role}，将更新到角色id框中")

        self.lineedit_role_id.setText(role.roleid)

    def on_server_select(self, index):
        self.lineedit_role_id.clear()
        self.update_role_names()

    def update_role_names(self):
        self.combobox_role_name.clear()
        roles = self.get_roles()
        if len(roles) != 0:
            self.combobox_role_name.addItems([role.rolename for role in roles])
        else:
            self.combobox_role_name.addItems([self.combobox_role_name_placeholder])

    def get_server_id(self) -> str:
        return dnf_server_name_to_id(self.combobox_server_name.currentText())

    def rolename_to_roleid(self, role_name) -> str:
        for role in self.get_roles():
            if role.rolename == role_name:
                return role.roleid

        return ""

    def get_roles(self) -> List[DnfRoleInfo]:
        server_id = self.get_server_id()
        if server_id not in self.server_id_to_roles:
            return []

        return self.server_id_to_roles[server_id]


class DnfHelperInfoConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: DnfHelperInfoConfig, parent=None):
        super(DnfHelperInfoConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: DnfHelperInfoConfig):
        self.checkbox_chronicle_lottery = create_checkbox(cfg.chronicle_lottery)
        add_row(form_layout, "编年史开启抽奖", self.checkbox_chronicle_lottery)

        self.lineedit_userId = create_lineedit(cfg.userId, "dnf助手->我的->编辑->社区ID")
        add_row(form_layout, "社区ID(userId)", self.lineedit_userId)

        self.lineedit_nickName = create_lineedit(cfg.nickName, "dnf助手->我的->编辑->昵称")
        add_row(form_layout, "昵称(nickName)", self.lineedit_nickName)

        self.lineedit_token = create_lineedit(cfg.token, "形如 sSfsEtDH，抓包或分享链接可得（ps：不知道咋操作，就到群里大喊一句：助手token，就会有好心的机器人来为你指路")
        add_row(form_layout, "登陆票据(token)", self.lineedit_token)

        self.lineedit_uniqueRoleId = create_lineedit(cfg.uniqueRoleId, "形如 3482436497，抓包或分享链接可得（ps：不知道咋操作，就到群里大喊一句：助手token，就会有好心的机器人来为你指路")
        add_row(form_layout, "唯一角色ID(uniqueRoleId)", self.lineedit_uniqueRoleId)

    def update_config(self, cfg: DnfHelperInfoConfig):
        cfg.userId = self.lineedit_userId.text()
        cfg.nickName = self.lineedit_nickName.text()
        cfg.token = self.lineedit_token.text()
        cfg.uniqueRoleId = self.lineedit_uniqueRoleId.text()

        cfg.chronicle_lottery = self.checkbox_chronicle_lottery.isChecked()


class HelloVoiceInfoConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: HelloVoiceInfoConfig, parent=None):
        super(HelloVoiceInfoConfigUi, self).__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: HelloVoiceInfoConfig):
        self.lineedit_hello_id = create_lineedit(cfg.hello_id, "hello语音->我的->头像右侧，昵称下方的【ID：XXXXXX】中的XXX那部分")
        add_row(form_layout, "hello语音的用户ID", self.lineedit_hello_id)

    def update_config(self, cfg: HelloVoiceInfoConfig):
        cfg.hello_id = self.lineedit_hello_id.text()


def report_click_event(event: str):
    increase_counter(ga_category="click_in_config_ui", name=event)


def main():
    increase_counter(name="config_ui", ga_type=GA_REPORT_TYPE_PAGE_VIEW)

    def catch_exceptions(t, val, tb):
        result = StringIO()
        v3 = print_tb(tb, file=result)
        msg = f"{t} {val}:\n{result.getvalue()}"
        logger.error(msg)
        QMessageBox.critical(None, "出错了", msg)
        old_hook(t, val, tb)

    old_hook = sys.excepthook
    sys.excepthook = catch_exceptions

    if config().common.config_ui_enable_high_dpi:
        logger.info("已启用高DPI模式")
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication([])

    app.setStyle(QStyleFactory.create("fusion"))

    ui = ConfigUi()
    ui.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
