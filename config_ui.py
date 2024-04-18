from __future__ import annotations

import functools
import logging
import random
import shutil
import subprocess
import sys
import time
import webbrowser
from datetime import datetime

import requests

from config import (
    AccountConfig,
    AccountInfoConfig,
    ArkLotteryConfig,
    BindRoleConfig,
    ComicConfig,
    ComicExchangeItemConfig,
    CommonConfig,
    Config,
    DnfHelperChronicleExchangeItemConfig,
    DnfHelperInfoConfig,
    ExchangeItemConfig,
    FixedTeamConfig,
    FunctionSwitchesConfig,
    HelloVoiceInfoConfig,
    LoginConfig,
    MajieluoConfig,
    MobileGameRoleInfoConfig,
    RetryConfig,
    VipMentorConfig,
    XinYueAppOperationConfig,
    XinYueOperationConfig,
    config,
    load_config,
    save_config,
)
from config_cloud import config_cloud
from db import DnfHelperChronicleExchangeListDB
from first_run import is_first_run
from log import color, fileHandler, logger, new_file_handler
from notice import Notice, NoticeManager
from qt_wrapper import (
    DNFRoleIdValidator,
    MyComboBox,
    QHLine,
    QQListValidator,
    QQValidator,
    add_form_seperator,
    add_row,
    add_vbox_seperator,
    create_checkbox,
    create_collapsible_box_add_to_parent_layout,
    create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout,
    create_combobox,
    create_double_spin_box,
    create_lineedit,
    create_push_button_grid_layout,
    create_pushbutton,
    create_spin_box,
    init_collapsible_box_size,
    list_to_str,
    make_scroll_layout,
    show_confirm_message_box,
    show_message,
    str_to_list,
)
from setting import dnf_server_id_to_name, dnf_server_name_list, dnf_server_name_to_id, zzconfig
from update import get_update_info, try_manaual_update, update_fallback
from version import now_version, ver_time

logger.name = "config_ui"
logger.removeHandler(fileHandler)
logger.addHandler(new_file_handler())

import os.path
from io import StringIO
from traceback import print_tb

from PyQt5.QtCore import QCoreApplication, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QStyleFactory,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dao import CardSecret, DnfRoleInfo
from data_struct import ConfigInterface, to_raw_type
from djc_helper import DjcHelper, is_new_version_ark_lottery
from ga import GA_REPORT_TYPE_PAGE_VIEW
from game_info import get_name_2_mobile_game_info_map
from main_def import (
    _show_head_line,
    disable_flag_file,
    get_config_backup_dir,
    get_user_buy_info,
    has_any_account_in_normal_run,
    has_buy_auto_updater_dlc,
)
from network import process_result
from server import get_pay_server_addr
from urls import Urls
from usage_count import increase_counter
from util import (
    bytes_arr_to_hex_str,
    cache_name_download,
    cache_name_user_buy_info,
    clear_login_status,
    get_random_face,
    hex_str_to_bytes_arr,
    is_valid_qq,
    kill_process,
    open_with_default_app,
    parse_scode,
    parse_url_param,
    range_from_one,
    remove_suffix,
    reset_cache,
    run_from_src,
    start_djc_helper,
    sync_configs,
    try_except,
    use_new_pay_method,
)

# 客户端错误码
CHECK_RESULT_OK = "检查通过"

# 服务器错误码
RESULT_OK = "操作成功"
RESULT_INVALID = "卡密不存在或不匹配"
RESULT_QQ_NOT_SET = "未设置QQ"
RESULT_ALREADY_USED = "卡密已经使用过"
RESULT_ALREADY_BUY = "自动更新只需购买一次"

# 定义一些信息
pay_item_item_auto_updater = "自动更新DLC"

all_pay_item_names = [
    "按月付费1个月",
    "按月付费2个月",
    "按月付费3个月",
    "按月付费6个月",
    "按月付费12个月",
    pay_item_item_auto_updater,
]

item_name_to_money_map = {
    pay_item_item_auto_updater: 10.24,
    "按月付费1个月": 5 * 1,
    "按月付费2个月": 5 * 2,
    "按月付费3个月": 5 * 3,
    "按月付费6个月": 5 * 6,
    "按月付费12个月": 5 * 12,
}

all_pay_type_names = [
    "支付宝",
    "微信支付",
    "QQ钱包",
]

pay_type_name_to_type = {
    "支付宝": "alipay",
    "QQ钱包": "qqpay",
    "微信支付": "wxpay",
    # "财付通": "tenpay",
}


class PayRequest(ConfigInterface):
    def __init__(self):
        self.card_secret = CardSecret()  # 卡密信息
        self.qq = ""  # 使用QQ
        self.game_qqs = []  # 附属游戏QQ
        self.recommender_qq = ""  # 推荐人QQ


class PayResponse(ConfigInterface):
    def __init__(self):
        self.msg = RESULT_OK


class SubmitOrderRequest(ConfigInterface):
    def __init__(self):
        self.qq = ""  # 使用QQ
        self.game_qqs = []  # 附属游戏QQ
        self.recommender_qq = ""  # 推荐人QQ

        self.pay_type = "alipay"
        self.item_name = "按月付费1个月"


class SubmitOrderResponse(ConfigInterface):
    def __init__(self):
        self.msg = RESULT_OK
        self.order_url = ""


class BiDict:
    def __init__(self, original_dict: dict):
        self.key_to_val = dict({k: v for k, v in original_dict.items()})
        self.val_to_key = dict({v: k for k, v in original_dict.items()})


class GetBuyInfoThread(QThread):
    signal_results = pyqtSignal(str, str, str)

    def __init__(self, parent, cfg: Config):
        super().__init__(parent)

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
            dlc_info += (
                "已购买自动更新DLC"
                "\n\t请注意这里的两月是指从2.8开始累积未付费时长最多允许为两个月，是给2.8以前购买DLC的朋友的小福利"
                "\n\t如果4.11以后才购买就享受不到这个的，因为购买时自2.8开始的累积未付费时长已经超过两个月"
            )
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

            logger.warning(
                color("fg_bold_yellow") + f"------------检查第{idx}个账户({account_config.name})------------"
            )
            self.update_progress(
                f"1/3 正在处理第{idx}/{len(self.cfg.account_configs)}个账户({account_config.name})，请耐心等候..."
            )

            djcHelper = DjcHelper(account_config, self.cfg.common)
            djcHelper.fetch_pskey()
            djcHelper.check_skey_expired()

            self.update_progress(f"完成处理第{idx}个账户({account_config.name})")

    def update_progress(self, progress_message):
        ut = datetime.now() - self.time_start
        self.signal_results.emit(f"{progress_message}(目前共耗时{ut.total_seconds():.1f}秒)", "", "")

    def send_results(self, dlc_info, monthly_pay_info):
        self.signal_results.emit("", dlc_info, monthly_pay_info)


class NoticeUi(QFrame):
    def __init__(self, parent=None):
        super().__init__()

        self.setWindowTitle("历史公告")

        self.resize(540, 390)

        self.load_notices()

        self.init_ui()

    def load_notices(self):
        self.current_notice_index = 0

        # 当前的公告
        self.notice_manager = NoticeManager(download_only_if_not_exists=True)

        # 额外加载存档的公告
        self.notice_manager.file_name = self.notice_manager.archived_notices_file_name
        self.notice_manager.load(download_only_if_not_exists=True)

        # 按照实际降序排列，先展示最近的
        self.notice_manager.notices.sort(key=lambda notice: notice.send_at, reverse=True)

    @property
    def notices(self) -> list[Notice]:
        return self.notice_manager.notices

    def init_ui(self):
        top_layout = QVBoxLayout()

        self.label_title = QLabel("默认标题")
        self.label_time = QLabel("发送时间")

        self.label_content = QTextEdit("默认内容")
        self.label_content.setReadOnly(True)

        self.update_current_notice()

        top_layout.addWidget(self.label_title, alignment=Qt.AlignHCenter)
        top_layout.addWidget(self.label_time, alignment=Qt.AlignHCenter)
        top_layout.addWidget(self.label_content)

        layout = QHBoxLayout()

        btn_previous = create_pushbutton("上一个")

        combobox_notice_title = create_combobox(
            self.notices[0].title,
            [notice.title for notice in self.notices],
        )

        btn_next = create_pushbutton("下一个")

        btn_previous.clicked.connect(self.show_previous_notice)
        combobox_notice_title.currentTextChanged.connect(self.on_select_notice_title)
        btn_next.clicked.connect(self.show_next_notice)

        layout.addWidget(btn_previous)
        layout.addWidget(combobox_notice_title)
        layout.addWidget(btn_next)

        top_layout.addLayout(layout)

        self.setLayout(top_layout)

    def update_current_notice(self):
        notice_count = len(self.notices)

        idx = self.current_notice_index
        current_notice = self.notices[idx]

        message = current_notice.message
        if current_notice.open_url != "" and current_notice.open_url not in message:
            message += "\n" + current_notice.open_url

        self.label_title.setText(f"[{idx + 1}/{notice_count}] {current_notice.title}")
        self.label_time.setText(current_notice.send_at)
        self.label_content.setText(message)

    def show_previous_notice(self, checked=False):
        self.current_notice_index = (self.current_notice_index + len(self.notices) - 1) % len(self.notices)
        self.update_current_notice()

    def show_next_notice(self, checked=False):
        self.current_notice_index = (self.current_notice_index + 1) % len(self.notices)
        self.update_current_notice()

    def on_select_notice_title(self, title: str):
        for idx, notice in enumerate(self.notices):
            if notice.title == title:
                self.current_notice_index = idx
                break

        self.update_current_notice()


class ConfigUi(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.resize(1080, 780)
        title = f"DNF蚊子腿小助手 简易配置工具 v{now_version} {ver_time} by风之凌殇 {get_random_face()}"
        self.setWindowTitle(title)

        self.setStyleSheet("font-family: Microsoft YaHei")
        self.setWindowIcon(QIcon("utils/icons/config_ui.ico"))

        self.setWhatsThis("简易配置工具")

        self.load()

        logger.info(f"配置工具启动成功，版本号为v{now_version} {ver_time}")

    def load(self):
        self.from_config(self.load_config())

        logger.info("已读取成功，请按需调整配置，调整完记得点下保存~")

    def load_old_version(self):
        # 弹窗提示选择旧版本的小助手exe所在目录
        msg = "打开旧版本的【DNF蚊子腿小助手.exe】所在的目录，形如【DNF蚊子腿小助手_v10.5.0_by风之凌殇】"
        # show_message("操作指引", msg)
        old_version_dir = QFileDialog.getExistingDirectory(
            self, msg, os.path.realpath(".."), QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if old_version_dir == "":
            logger.info("未选择任何目录")
            return

        # 通过判断目录中是否存在【DNF蚊子腿小助手.exe】来判定选择的目录是否是正确的目录
        djc_helper_exe = "DNF蚊子腿小助手.exe"
        if not os.path.isfile(os.path.join(old_version_dir, djc_helper_exe)):
            show_message(
                "出错啦", f"未在选中的目录 {old_version_dir} 中发现 {djc_helper_exe} ，请重新点击按钮进行选择~"
            )
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
        cfg = self.to_config()
        self.remove_dynamic_attrs(cfg)
        self.save_config(cfg)
        if show_message_box:
            show_message(
                "保存成功", "已保存成功\nconfig.toml已不再有注释信息，如有需要，可去config.example.toml查看注释"
            )
            report_click_event("save_config")

    def open_backups(self):
        config_backup_dir = get_config_backup_dir()

        show_message(
            "使用说明",
            (
                "在稍后打开的目录中可看到最近一段时间成功运行后备份的配置，目录名为备份时间，里面为对应配置\n"
                "可通过左边的【继承旧版本配置】按钮，并将目录指定为你想要还原的时间点的配置的目录，点击继承即可还原配置~"
            ),
        )
        report_click_event("open_backups")

        open_with_default_app(config_backup_dir)

    def load_config(self) -> Config:
        # load_config(local_config_path="", reset_before_load=True)
        load_config(local_config_path="config.toml.local", reset_before_load=True)
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
        btn_open_backups = create_pushbutton("查看配置备份", "LawnGreen")

        btn_load_old_version.clicked.connect(self.load_old_version)
        btn_load.clicked.connect(self.restart_to_load)
        btn_save.clicked.connect(self.save)
        btn_open_backups.clicked.connect(self.open_backups)

        layout = QHBoxLayout()
        layout.addWidget(btn_load_old_version)
        layout.addWidget(btn_load)
        layout.addWidget(btn_save)
        layout.addWidget(btn_open_backups)
        top_layout.addLayout(layout)
        top_layout.addWidget(QHLine())

        btn_add_account = create_pushbutton("添加账号", "Chartreuse")
        btn_del_account = create_pushbutton("删除账号", "lightgreen")
        btn_clear_login_status = create_pushbutton(
            "清除登录状态", "DarkCyan", "登录错账户，或者想要登录其他账户时，点击这个即可清除登录状态"
        )
        btn_join_group = create_pushbutton("加群反馈问题/交流", "Orange")
        btn_add_telegram = create_pushbutton("加入Telegram群", "LightBlue")

        btn_add_account.clicked.connect(self.add_account)
        btn_del_account.clicked.connect(self.del_account)
        btn_clear_login_status.clicked.connect(self.clear_login_status)
        btn_join_group.clicked.connect(self.join_group)
        btn_add_telegram.clicked.connect(self.join_telegram)

        layout = QHBoxLayout()
        layout.addWidget(btn_add_account)
        layout.addWidget(btn_del_account)
        layout.addWidget(btn_clear_login_status)
        layout.addWidget(btn_join_group)
        layout.addWidget(btn_add_telegram)
        top_layout.addLayout(layout)
        top_layout.addWidget(QHLine())

        btn_open_pay_guide = create_pushbutton("查看付费指引", "SpringGreen")
        btn_open_usage_guide = create_pushbutton("查看使用教程（文字版）", "SpringGreen")
        btn_open_usage_video = create_pushbutton("查看使用教程（视频版）", "SpringGreen")
        btn_show_notice = create_pushbutton("查看公告", "Lime")
        btn_check_update = create_pushbutton("检查更新", "PaleGreen")

        btn_open_pay_guide.clicked.connect(self.open_pay_guide)
        btn_open_usage_guide.clicked.connect(self.open_usage_guide)
        btn_open_usage_video.clicked.connect(self.open_usage_video)
        btn_show_notice.clicked.connect(self.show_notice)
        btn_check_update.clicked.connect(self.check_update)

        layout = QHBoxLayout()
        layout.addWidget(btn_open_pay_guide)
        layout.addWidget(btn_open_usage_guide)
        layout.addWidget(btn_open_usage_video)
        layout.addWidget(btn_show_notice)
        layout.addWidget(btn_check_update)
        top_layout.addLayout(layout)
        top_layout.addWidget(QHLine())

        self.btn_run_djc_helper = create_pushbutton("保存配置，然后运行小助手并退出配置工具", "cyan")
        self.btn_run_djc_helper.clicked.connect(self.run_djc_helper)
        top_layout.addWidget(self.btn_run_djc_helper)
        top_layout.addWidget(QHLine())

    def open_pay_guide(self):
        open_with_default_app("付费指引/付费指引.url")
        report_click_event("open_pay_guide")

    def open_usage_guide(self):
        open_with_default_app("使用教程/使用文档.url")
        report_click_event("open_usage_guide")

    def open_usage_video(self):
        open_with_default_app("使用教程/视频教程_合集.url")
        report_click_event("open_usage_video")

    def open_autojs(self):
        webbrowser.open("https://github.com/fzls/autojs")
        report_click_event("open_autojs")

    def support(self, checked=False):
        show_message(get_random_face(), "纳尼，真的要打钱吗？还有这种好事，搓手手0-0")
        self.popen(os.path.realpath("付费指引/支持一下.png"))

        report_click_event("support")

    def show_notice(self):
        if hasattr(self, "notice"):
            self.notice.close()  # type: ignore

        self.notice = NoticeUi(self)
        self.notice.show()

    def check_update(self, checked=False):
        cfg = self.to_config().common

        try:
            ui = get_update_info(cfg)
            if not try_manaual_update(ui):
                show_message("无需更新", "当前已经是最新版本~")
        except Exception:
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

        subprocess.Popen(
            args,
            cwd=cwd,
            shell=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def clear_login_status(self, checked=False):
        clear_login_status()

        show_message(
            "清除完毕",
            (
                "登录状态已经清除完毕，可使用新账号重新运行~\n"
                "\n"
                "友情提示：清除登录状态是否是为了登录另外一个qq来领取奖励？\n"
                "如果是这样，推荐使用小助手已有的多账号配置功能，可实现领取多个账号的需求~\n"
                "具体配置方法请点击【查看使用教程 文字版】，查看其中的【添加多个账号】章节，按步骤操作即可\n"
            ),
        )
        report_click_event("clear_login_status")

    def join_group(self, checked=False):
        # note: 如果群 791343073 满了，到 https://qun.qq.com/join.html 获取新群的加群链接 @2021-02-13 01:41:03
        webbrowser.open("https://qm.qq.com/cgi-bin/qm/qr?k=w-U4SsRhWKGHtiMprzqa6plhbvCSALA2&jump_from=webapi")
        for suffix in [
            "png",
            "jpg",
        ]:
            img_name = f"DNF蚊子腿小助手交流群群二维码.{suffix}"
            if not os.path.isfile(img_name):
                continue

            self.popen(img_name)

        report_click_event("join_group")

    def join_telegram(self, checked=False):
        webbrowser.open("https://t.me/djc_helper")
        report_click_event("join_telegram")

    def add_account(self, checked=False):
        account_name, ok = QInputDialog.getText(
            self, "添加账号", "要添加的账号名称", QLineEdit.Normal, f"默认账号名-{len(self.accounts) + 1}"
        )
        if ok:
            logger.info(f"尝试添加账号 {account_name} ...")

            if account_name == "":
                show_message("添加失败", "未填写账号名称，请重新操作~")
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
        user_names = []
        for account in self.accounts:
            user_names.append(account.lineedit_name.text())

        account_name, ok = QInputDialog().getItem(self, "删除账号", "要删除的账号名称", user_names, 0, False)
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
        self.create_majieluo_tab(cfg)
        self.create_mo_jie_ren_tab(cfg)
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

        remote_config = config_cloud()

        # 一些共用的字段描述和提示，避免卡密和直接购买的地方各写一遍，导致难以维护
        label_name_qq = "主QQ"
        placeholder_text_qq = "形如 1234567"

        label_name_game_qqs = "其他要使用的QQ（新增）"
        placeholder_text_game_qqs = "最多5个，使用英文逗号分隔，形如 123,456,789,12,13"

        label_name_recommender_qq = "推荐人QQ（若有可填写）"
        placeholder_text_recommender_qq = "完成首次购买按月付费时，推荐人将会获得一个月的小助手使用时长作为奖励"

        # -------------- 区域：购买卡密 --------------
        self.collapsible_box_buy_card_secret = create_collapsible_box_add_to_parent_layout(
            "购买卡密(点击展开)(不会操作或无法支付可点击左上方的【查看付费指引】按钮)",
            top_layout,
            title_backgroup_color="Chartreuse",
        )
        hbox_layout = QHBoxLayout()
        self.collapsible_box_buy_card_secret.setContentLayout(hbox_layout)

        btn_buy_auto_updater_dlc = create_pushbutton(
            "购买自动更新DLC的卡密",
            "DeepSkyBlue",
            "10.24元，一次性付费，永久激活自动更新功能，需去网盘或群文件下载auto_updater.exe放到utils目录，详情可见付费指引/付费指引.docx",
        )
        btn_pay_by_month = create_pushbutton(
            "购买按月付费的卡密",
            "DeepSkyBlue",
            "5元/月(31天)，付费生效期间可以激活2020.2.6及之后加入的短期活动，可从账号概览区域看到付费情况，详情可见付费指引/付费指引.docx",
        )

        btn_buy_auto_updater_dlc.clicked.connect(self.buy_auto_updater_dlc)
        btn_pay_by_month.clicked.connect(self.pay_by_month)

        hbox_layout.addWidget(btn_buy_auto_updater_dlc)
        hbox_layout.addWidget(btn_pay_by_month)

        # -------------- 区域：使用卡密 --------------
        self.collapsible_box_use_card_secret = create_collapsible_box_add_to_parent_layout(
            "使用卡密(点击展开)", top_layout, title_backgroup_color="MediumSpringGreen"
        )
        vbox_layout = QVBoxLayout()
        self.collapsible_box_use_card_secret.setContentLayout(vbox_layout)

        form_layout = QFormLayout()
        vbox_layout.addLayout(form_layout)

        self.lineedit_card = create_lineedit(
            "", placeholder_text="填入在卡密网站付款后得到的卡号，形如 auto_update-20210313133230-00001"
        )
        form_layout.addRow("卡号", self.lineedit_card)

        self.lineedit_secret = create_lineedit(
            "", placeholder_text="填入在卡密网站付款后得到的密码，形如 BF8h0y1Zcb8ukY6rsn5YFhkh0Nbe9hit"
        )
        form_layout.addRow("卡密", self.lineedit_secret)

        self.lineedit_qq = create_lineedit("", placeholder_text=placeholder_text_qq)
        self.lineedit_qq.setValidator(QQValidator())
        form_layout.addRow(label_name_qq, self.lineedit_qq)
        # 如果首个账号设置了qq，则直接填入作为主QQ默认值，简化操作
        if len(cfg.account_configs) != 0:
            account_cfg = cfg.account_configs[0]
            if account_cfg.account_info.has_set_account():
                self.lineedit_qq.setText(cfg.account_configs[0].account_info.account)

        self.lineedit_game_qqs = create_lineedit("", placeholder_text=placeholder_text_game_qqs)
        self.lineedit_game_qqs.setValidator(QQListValidator())
        form_layout.addRow(label_name_game_qqs, self.lineedit_game_qqs)

        if remote_config.enable_recommend_reward:
            self.lineedit_recommender_qq = create_lineedit("", placeholder_text=placeholder_text_recommender_qq)
            self.lineedit_recommender_qq.setValidator(QQValidator())
            form_layout.addRow(label_name_recommender_qq, self.lineedit_recommender_qq)

        btn_pay_by_card_and_secret = create_pushbutton("使用卡密购买对应服务（二十分钟内生效）", "MediumSpringGreen")
        vbox_layout.addWidget(btn_pay_by_card_and_secret)

        btn_pay_by_card_and_secret.clicked.connect(self.pay_by_card_and_secret)

        # -------------- 区域：直接购买 --------------
        # 显示新版的付费界面
        self.collapsible_box_pay_directly = create_collapsible_box_add_to_parent_layout(
            "购买付费内容(点击展开)(不会操作或无法支付可点击左上方的【查看付费指引】按钮)",
            top_layout,
            title_backgroup_color="LightCyan",
        )
        vbox_layout = QVBoxLayout()
        self.collapsible_box_pay_directly.setContentLayout(vbox_layout)

        form_layout = QFormLayout()
        vbox_layout.addLayout(form_layout)

        self.lineedit_pay_directly_qq = create_lineedit("", placeholder_text=placeholder_text_qq)
        self.lineedit_pay_directly_qq.setValidator(QQValidator())
        form_layout.addRow(label_name_qq, self.lineedit_pay_directly_qq)
        # 如果首个账号设置了qq，则直接填入作为主QQ默认值，简化操作
        if len(cfg.account_configs) != 0:
            account_cfg = cfg.account_configs[0]
            if account_cfg.account_info.has_set_account():
                self.lineedit_pay_directly_qq.setText(cfg.account_configs[0].account_info.account)

        self.lineedit_pay_directly_game_qqs = create_lineedit("", placeholder_text=placeholder_text_game_qqs)
        self.lineedit_pay_directly_game_qqs.setValidator(QQListValidator())
        form_layout.addRow(label_name_game_qqs, self.lineedit_pay_directly_game_qqs)

        if remote_config.enable_recommend_reward:
            self.lineedit_pay_directly_recommender_qq = create_lineedit(
                "", placeholder_text=placeholder_text_recommender_qq
            )
            self.lineedit_pay_directly_recommender_qq.setValidator(QQValidator())
            form_layout.addRow(label_name_recommender_qq, self.lineedit_pay_directly_recommender_qq)

        form_layout.addWidget(QHLine())

        self.push_button_grid_layout_item_name = create_push_button_grid_layout(all_pay_item_names, "Cyan")
        form_layout.addRow("付费内容", self.push_button_grid_layout_item_name)

        form_layout.addWidget(QHLine())

        self.push_button_grid_layout_pay_type_name = create_push_button_grid_layout(all_pay_type_names, "Cyan")

        form_layout.addRow("付款方式", self.push_button_grid_layout_pay_type_name)

        form_layout.addWidget(QHLine())

        btn_pay_directly = create_pushbutton(
            "购买对应服务（点击后会跳转到付费页面，扫码支付即可，二十分钟内生效）", "SpringGreen"
        )
        vbox_layout.addWidget(btn_pay_directly)

        btn_pay_directly.clicked.connect(self.pay_directly)

        # -------------- 区域：切换卡密/直接购买界面 --------------
        self.btn_toggle_card_secret = create_pushbutton("显示原来的卡密支付界面")
        self.btn_toggle_card_secret.clicked.connect(self.toggle_card_secret)
        top_layout.addWidget(self.btn_toggle_card_secret)

        self.btn_alipay_redpacket = create_pushbutton("领取支付宝小红包（若使用支付宝支付可以先扫码领一下）", "Lime")
        self.btn_alipay_redpacket.clicked.connect(self.alipay_redpacket)
        top_layout.addWidget(self.btn_alipay_redpacket)

        top_layout.addWidget(QHLine())

        # -------------- 区域：查询信息 --------------
        add_vbox_seperator(top_layout, "查询信息")
        vbox_layout = QVBoxLayout()
        top_layout.addLayout(vbox_layout)

        # 显示付费相关内容
        self.btn_show_buy_info = create_pushbutton(
            "显示付费相关信息(点击后将登录所有账户，可能需要较长时间，请耐心等候)"
        )
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

    def is_card_secret_hidden(self) -> bool:
        return self.collapsible_box_buy_card_secret.isHidden()

    def hide_card_secret(self):
        self.collapsible_box_buy_card_secret.setVisible(False)
        self.collapsible_box_use_card_secret.setVisible(False)

        self.collapsible_box_pay_directly.setVisible(True)

    def show_card_secret(self):
        self.collapsible_box_buy_card_secret.setVisible(True)
        self.collapsible_box_use_card_secret.setVisible(True)

        self.collapsible_box_pay_directly.setVisible(False)

    def buy_auto_updater_dlc(self, checked=False):
        if not self.confirm_buy_auto_updater():
            return

        if not self.check_pay_server():
            return

        cfg = config_cloud()
        webbrowser.open(cfg.auto_updater_dlc_purchase_url)
        increase_counter(ga_category="open_pay_webpage", name="auto_updater_dlc")

    def confirm_buy_auto_updater(self) -> bool:
        total_confirm_time = 3
        for show_index in range_from_one(total_confirm_time):
            ret = show_confirm_message_box(
                "友情提示",
                (
                    f"[{show_index}/{total_confirm_time}] 重要的事情说{total_confirm_time}遍\n"
                    "\n"
                    f"自动更新DLC的唯一作用仅仅是【自动更新】，不会给你带来付费活动的使用资格的哦，请确认你想要购买的是这个功能后再点击【确认】按钮进行购买-。-"
                ),
            )
            if ret == QMessageBox.Cancel:
                logger.info("取消购买")
                return False

        message_box = QMessageBox()
        message_box.setWindowTitle("友情提示")
        message_box.setText("自动更新DLC只需购买一次，请确认从未购买过后再点击【确认】按钮进行购买")
        message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        ret = message_box.exec_()
        if ret == QMessageBox.Cancel:
            logger.info("取消购买")
            return False

        return True

    def pay_by_month(self, checked=False):
        if not self.check_pay_server():
            return

        cfg = config_cloud()
        webbrowser.open(cfg.pay_by_month_purchase_url)
        increase_counter(ga_category="open_pay_webpage", name="pay_buy_month")

    def pay_by_card_and_secret(self, checked=False):
        card = self.lineedit_card.text().strip()
        secret = self.lineedit_secret.text().strip()
        qq = self.lineedit_qq.text().strip()
        game_qqs = str_to_list(self.lineedit_game_qqs.text().strip())
        recommender_qq = ""
        if hasattr(self, "lineedit_recommender_qq"):
            recommender_qq = self.lineedit_recommender_qq.text().strip()

        msg = self.check_pay_params(card, secret, qq, game_qqs, recommender_qq)
        if msg != CHECK_RESULT_OK:
            show_message("出错了", msg)
            return

        ret = show_confirm_message_box(
            "请确认账号信息",
            (
                "请确认输入的账号信息是否无误，避免充错账号~\n"
                "\n"
                f"主QQ：       {format_qq_for_message_box(qq)}\n"
                f"其他QQ列表： {format_qq_list_for_message_box(game_qqs)}\n"
                f"推荐人QQ：    {format_qq_for_message_box(recommender_qq)}\n"
            ),
        )
        if ret == QMessageBox.Cancel:
            logger.info("取消使用卡密")
            return

        if not self.check_main_qq_in_local(qq):
            return

        if not self.check_pay_server():
            return

        try:
            self.do_pay_request(card, secret, qq, game_qqs, recommender_qq)
        except Exception as e:
            show_message(
                "出错了", (f"请求出现异常，报错如下:\n" "\n" f"{e}\n" "\n" "可以试试使用付款方式二进行付款~\n")
            )

        # 点击付费按钮后重置cache
        reset_cache(cache_name_download)
        reset_cache(cache_name_user_buy_info)

    def check_pay_params(self, card: str, secret: str, qq: str, game_qqs: list[str], recommender_qq) -> str:
        if len(card.split("-")) != 3:
            return "无效的卡号"

        if len(secret) != 32:
            return "无效的卡密"

        msg = self.check_qqs(qq, game_qqs, recommender_qq)
        if msg != CHECK_RESULT_OK:
            return msg

        return CHECK_RESULT_OK

    def check_qqs(self, qq: str, game_qqs: list[str], recommender_qq: str) -> str:
        for qq_to_check in [qq, *game_qqs]:
            if not is_valid_qq(qq_to_check):
                return f"无效的QQ：{qq_to_check}"

        if len(game_qqs) > 5:
            return (
                "最多五个QQ哦，如果有更多QQ，建议用配置工具添加多个账号一起使用（任意一个有权限就可以），无需全部填写~"
            )

        if recommender_qq != "":
            if not is_valid_qq(recommender_qq):
                return f"推荐人QQ不是有效的QQ：{recommender_qq}"

            if recommender_qq == qq:
                return f"推荐人QQ不能与当前主QQ一样：{recommender_qq}"

        return CHECK_RESULT_OK

    def do_pay_request(self, card: str, secret: str, qq: str, game_qqs: list[str], recommender_qq: str):
        req = PayRequest()
        req.card_secret.card = card
        req.card_secret.secret = secret
        req.qq = qq
        req.game_qqs = game_qqs
        req.recommender_qq = recommender_qq

        server_addr = self.get_pay_server_addr()
        raw_res = requests.post(f"{server_addr}/pay", json=to_raw_type(req), timeout=20)
        logger.debug(f"req={req}")
        process_result("使用卡密", raw_res)
        if raw_res.status_code != 200:
            show_message("出错了", f"服务器似乎暂时挂掉了, 请稍后再试试, result={raw_res.text}")
            return

        res = PayResponse().auto_update_config(raw_res.json())

        if res.msg == RESULT_OK:
            # 使用成功
            show_message(
                "处理成功",
                "卡密使用成功，目前有缓存机制，因此可能不会立即生效。一般会在15分钟生效，请耐心等候。如果30分钟后仍未生效，可以去QQ群联系我进行反馈~",
            )
            self.lineedit_card.clear()
            self.lineedit_secret.clear()

            # 自动更新购买完成后提示去网盘下载
            if card.startswith("auto_update"):
                show_message(
                    "提示", "自动更新已激活，下次启动小助手时将自动生效，具体操作流程请看【付费指引/付费指引.docx】"
                )

            self.report_use_card_secret(card, recommender_qq)
        else:
            # 使用失败
            show_message("使用失败", res.msg)

    @try_except(return_val_on_except=False)
    def report_use_card_secret(self, card: str, recommender_qq: str):
        increase_counter(ga_category="use_card_secret", name=card.split("-")[0])
        self.report_fill_recommender_qq(recommender_qq)

    def pay_directly(self, checked=False):
        qq = self.lineedit_pay_directly_qq.text().strip()
        game_qqs = str_to_list(self.lineedit_pay_directly_game_qqs.text().strip())
        recommender_qq = ""
        if hasattr(self, "lineedit_pay_directly_recommender_qq"):
            recommender_qq = self.lineedit_pay_directly_recommender_qq.text().strip()
        item_name = self.push_button_grid_layout_item_name.get_active_radio_text()
        pay_type_name = self.push_button_grid_layout_pay_type_name.get_active_radio_text()

        pay_type = pay_type_name_to_type[pay_type_name]

        # 检查对应渠道是否在维护中
        if not self.check_pay_type_name(pay_type_name):
            return

        msg = self.check_qqs(qq, game_qqs, recommender_qq)
        if msg != CHECK_RESULT_OK:
            show_message("出错了", msg)
            return

        ret = show_confirm_message_box(
            "请确认购买信息",
            (
                "请确认输入的购买信息是否无误，避免充错账号~\n"
                "\n"
                f"主QQ：       {format_qq_for_message_box(qq)}\n"
                f"其他QQ列表： {format_qq_list_for_message_box(game_qqs)}\n"
                f"推荐人QQ：   {format_qq_for_message_box(recommender_qq)}\n"
                "\n"
                f"付费内容：   {item_name}\n"
                f"付款方式：   {pay_type_name}\n"
                f"总计金额：   {item_name_to_money_map[item_name]} 元\n"
            ),
        )
        if ret == QMessageBox.Cancel:
            logger.info("取消购买")
            return

        if not self.check_main_qq_in_local(qq):
            return

        if item_name == pay_item_item_auto_updater and not self.confirm_buy_auto_updater():
            return

        if not self.check_pay_server():
            return

        try:
            self.do_pay_directly_request(item_name, pay_type, qq, game_qqs, recommender_qq)
        except Exception as e:
            self.show_card_secret()
            self.collapsible_box_pay_directly.setVisible(False)

            show_message(
                "出错了",
                (
                    f"直接购买出现异常，报错如下:\n"
                    "\n"
                    f"{e}\n"
                    "\n"
                    "已切换回卡密界面，可尝试卡密方案付款或者使用付款方式二直接付款\n"
                ),
            )

        # 点击付费按钮后重置cache
        reset_cache(cache_name_download)
        reset_cache(cache_name_user_buy_info)

    def check_main_qq_in_local(self, main_qq: str) -> bool:
        local_qqs = [
            account.account_info.account
            for account in self.to_config().account_configs
            if account.account_info.has_set_account()
        ]
        if len(local_qqs) == 0:
            # 本地账号未配置QQ，则视为通过
            return True

        if main_qq in local_qqs:
            # 当前主QQ在本地QQ列表中
            return True

        logger.info(f"当前充值的主QQ {main_qq} 不在本地QQ列表中，将额外弹窗确认是否是预期行为 {local_qqs}")

        total_confirm_time = 3
        for show_index in range_from_one(total_confirm_time):
            ret = show_confirm_message_box(
                "友情提示",
                (
                    f"[{show_index}/{total_confirm_time}] 你当前填写的主QQ并不在本地配置的QQ列表中，请确认这是你预期的行为，而不是手误填错了~\n"
                    "\n"
                    f"当前填写主QQ：{format_qq_for_message_box(main_qq)}\n"
                    f"本地QQ列表: {format_qq_list_for_message_box(local_qqs)}\n"
                ),
            )
            if ret == QMessageBox.Cancel:
                logger.info("取消购买")
                return False

        return True

    def check_pay_type_name(self, pay_type_name: str) -> bool:
        cfg = config_cloud()
        if pay_type_name in cfg.maintaining_payment_name_list:
            other_pay_type_list = list(
                pay_type for pay_type in all_pay_type_names if pay_type not in cfg.maintaining_payment_name_list
            )
            other_pay_type_tip = "或者".join(other_pay_type_list)

            self.show_pay_type_in_maintain(pay_type_name, other_pay_type_tip)
            return False

        return True

    def show_pay_type_in_maintain(self, pay_type_name: str, others: str):
        show_message(
            "提示",
            (
                f"支付网站的 {pay_type_name} 渠道暂时在维护中，请选择 {others} 进行支付\n"
                "\n"
                "如果你其他两个里没放钱，可以点击【其他功能】tab中第一行最右侧的【显示原来的卡密支付界面】，然后回到当前页面，即可看到卡密的界面。\n"
                f"若卡密网站的 {pay_type_name} 渠道可用，可以在那边下单后再使用卡密~\n"
            ),
            disabled_seconds=5,
        )

    def do_pay_directly_request(self, item_name: str, pay_type: str, qq: str, game_qqs: list[str], recommender_qq: str):
        req = SubmitOrderRequest()
        req.qq = qq
        req.game_qqs = game_qqs
        req.recommender_qq = recommender_qq

        req.pay_type = pay_type
        req.item_name = item_name

        server_addr = self.get_pay_server_addr()
        raw_res = requests.post(f"{server_addr}/submit_order", json=to_raw_type(req), timeout=20)
        logger.debug(f"req={req}")
        process_result("直接购买", raw_res)
        if raw_res.status_code != 200:
            show_message("出错了", f"服务器似乎暂时挂掉了, 请稍后再试试, result={raw_res.text}")
            return

        res = SubmitOrderResponse().auto_update_config(raw_res.json())

        if res.msg == RESULT_OK:
            # 使用成功
            self.lineedit_pay_directly_qq.clear()
            self.lineedit_pay_directly_game_qqs.clear()
            if hasattr(self, "lineedit_pay_directly_recommender_qq"):
                self.lineedit_pay_directly_recommender_qq.clear()

            logging.info(f"订单链接为 {res.order_url}")
            webbrowser.open(res.order_url)

            self.report_pay_directly(item_name, recommender_qq)
        else:
            # 使用失败
            show_message("使用失败", res.msg)

    @try_except(return_val_on_except=False)
    def report_pay_directly(self, item_name: str, recommender_qq: str):
        increase_counter(ga_category="pay_directly", name=item_name)
        self.report_fill_recommender_qq(recommender_qq)

    @try_except(return_val_on_except=False)
    def report_fill_recommender_qq(self, recommender_qq: str):
        remote_config = config_cloud()
        if not remote_config.enable_recommend_reward:
            # 未开启推荐奖励的情况下，不尝试上报数据，避免扰乱结果
            return

        increase_counter(ga_category="fill_recommender_qq", name=recommender_qq != "")

    @try_except(return_val_on_except=False)
    def check_pay_server(self) -> bool:
        server_not_online_message = f"无法访问服务器，若非最新版本，请尝试更新小助手版本~ 保底可使用扫码付费后私聊的方式购买，具体流程请参考【付费指引/付费指引.docx】\n\n当前使用版本为： v{now_version} {ver_time}"
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
        except Exception:
            show_message("出错了", server_not_online_message)
            return False

    def get_pay_server_addr(self) -> str:
        return get_pay_server_addr()

    def create_others_tab(self, cfg: Config):
        top_layout = QVBoxLayout()

        btn_support = create_pushbutton("作者很胖胖，我要给他买罐肥宅快乐水！", "DodgerBlue", "有钱就是任性.jpeg")
        btn_open_autojs = create_pushbutton("查看autojs版", "SpringGreen")

        btn_support.clicked.connect(self.support)
        btn_open_autojs.clicked.connect(self.open_autojs)

        layout = QHBoxLayout()
        layout.addWidget(btn_support)
        layout.addWidget(btn_open_autojs)
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

    def toggle_card_secret(self, checked=False):
        toggle_to_enable = self.is_card_secret_hidden()

        self.set_card_secret_button_status(toggle_to_enable)

        report_click_event("toggle_card_secret")

    def set_card_secret_button_status(self, enable=False):
        if enable:
            self.show_card_secret()
            self.btn_toggle_card_secret.setText("隐藏原来的卡密支付界面")
        else:
            self.hide_card_secret()
            self.btn_toggle_card_secret.setText("显示原来的卡密支付界面")

    def alipay_redpacket(self, checked=False):
        image_path = random.choice(["付费指引/支付宝红包活动.jpg", "付费指引/支付宝红包活动_实体版.jpg"])
        os.popen(os.path.realpath(image_path))

        report_click_event("alipay_redpacket")

    def adjust_pay_window(self):
        logger.info("根据配置情况，调整付费界面")
        if not use_new_pay_method():
            # 没有使用新支付方式的情况下，隐藏切换按钮，并显示卡密界面
            self.set_card_secret_button_status(True)
            self.btn_toggle_card_secret.setVisible(False)
            return

        # 按照远程配置，调整付费界面
        remote_config = config_cloud()

        # 先将全部界面都显示
        self.collapsible_box_buy_card_secret.setVisible(True)
        self.collapsible_box_use_card_secret.setVisible(True)
        self.collapsible_box_pay_directly.setVisible(True)

        if remote_config.enable_card_secret and remote_config.enable_pay_directly:
            logger.info(f"远程配置优先显示卡密: {remote_config.show_card_secret_first}")
            self.set_card_secret_button_status(remote_config.show_card_secret_first)
        else:
            if not remote_config.enable_card_secret:
                logger.info("远程配置禁用卡密界面")
                self.collapsible_box_buy_card_secret.setVisible(False)
                self.collapsible_box_use_card_secret.setVisible(False)

            if not remote_config.enable_pay_directly:
                logger.info("远程配置禁用直接购买界面")
                self.collapsible_box_pay_directly.setVisible(False)

            logger.info("远程配置禁用了卡密或直接购买界面，将隐藏切换按钮")
            self.btn_toggle_card_secret.setVisible(False)

    def auto_run_on_login(self):
        self.popen(
            [
                "reg",
                "add",
                "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                "/v",
                "DNF蚊子腿小助手",
                "/t",
                "reg_sz",
                "/d",
                self.get_djc_helper_path(),
                "/f",
            ]
        )
        show_message(
            "设置完毕",
            "已设置为开机自动启动~\n若想定时运行，请打开【使用教程/使用文档.docx】，参照【定时自动运行】章节（目前在第21页）设置",
        )

        report_click_event("auto_run_on_login")

    def stop_auto_run_on_login(self):
        self.popen(
            [
                "reg",
                "delete",
                "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                "/v",
                "DNF蚊子腿小助手",
                "/f",
            ]
        )
        show_message("设置完毕", "已取消开机自动启动~")

        report_click_event("stop_auto_run_on_login")

    def create_common_tab(self, cfg: Config):
        self.common = CommonConfigUi(cfg.common)
        self.tabs.addTab(self.common, "公共配置")

    def create_majieluo_tab(self, cfg: Config):
        self.majieluo = MajieluoConfigUi(cfg.common.majieluo, self)
        # self.tabs.addTab(self.majieluo, "马杰洛小工具")

    def create_mo_jie_ren_tab(self, cfg: Config):
        self.mo_jie_ren = MoJieRenTab()
        self.tabs.addTab(self.mo_jie_ren, "跳一跳小工具")

    def create_account_tabs(self, cfg: Config):
        self.accounts: list[AccountConfigUi] = []

        common_cfg = self.to_config().common
        for account in cfg.account_configs:
            account_ui = AccountConfigUi(account, common_cfg)
            self.add_account_tab(account_ui)

    def add_account_tab(self, account_ui: AccountConfigUi):
        self.accounts.append(account_ui)
        self.tabs.addTab(
            account_ui,
            self.account_name_to_tab_name(account_ui.lineedit_name.text(), account_ui.checkbox_enable.isChecked()),
        )

        # 记录当前账号名，用于同步修改tab名称
        account_ui.old_name = account_ui.lineedit_name.text()

        # 当修改账号名时，根据之前的账号名，定位并同步修改tab名称
        def update_tab_name(_):
            new_account_name = account_ui.lineedit_name.text()
            new_tab_name = self.account_name_to_tab_name(new_account_name, account_ui.checkbox_enable.isChecked())

            for tab_index in range(self.tabs.count()):
                tab_name = self.tabs.tabText(tab_index)
                account_name = self.tab_name_to_account_name(tab_name)

                if account_name == account_ui.old_name:
                    self.tabs.setTabText(tab_index, new_tab_name)
                    account_ui.old_name = new_account_name
                    break

        account_ui.lineedit_name.textChanged.connect(update_tab_name)
        account_ui.checkbox_enable.stateChanged.connect(update_tab_name)

    def account_name_to_tab_name(self, name: str, enabled: bool) -> str:
        if enabled:
            return name
        else:
            return name + self.disabled_account_name_suffix()

    def tab_name_to_account_name(self, tab_name) -> str:
        return remove_suffix(tab_name, self.disabled_account_name_suffix())

    def disabled_account_name_suffix(self) -> str:
        return "（未启用）"

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
            self.majieluo.update_config(cfg.common.majieluo)

            account_configs = []
            for idx, account in enumerate(self.accounts):
                # 以在账号中的次序作为唯一定位key，从而获取当前配置中该账号的配置，以便能保留一些配置工具中未涉及的配置，可以与文本编辑器改动兼容
                if idx < len(cfg.account_configs):
                    account_config = cfg.account_configs[idx]
                else:
                    account_config = AccountConfig()

                account.update_config(account_config)
                # 调用下这个函数，确保读取配置时的回调的一些参数能够生成，避免刚创建账号时执行一些操作会报错
                account_config.auto_update_config({})

                account_configs.append(account_config)

            cfg.account_configs = account_configs

        return cfg

    def remove_dynamic_attrs(self, cfg: Config):
        # 这些是动态生成的，不需要保存到配置表中
        for account_cfg in cfg.account_configs:
            for attr in ["sDjcSign"]:
                if not hasattr(account_cfg, attr):
                    continue
                delattr(account_cfg, attr)


class CommonConfigUi(QFrame):
    def __init__(self, cfg: CommonConfig, parent=None):
        super().__init__(parent)

        self.from_config(cfg)

    def from_config(self, cfg: CommonConfig):
        top_layout = QVBoxLayout()

        form_layout = QFormLayout()
        top_layout.addLayout(form_layout)

        # -------------- 区域：角色绑定与同步 --------------
        (
            self.collapsible_box_role_binding_sync,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("角色绑定与同步", top_layout)

        self.checkbox_try_auto_bind_new_activity = create_checkbox(cfg.try_auto_bind_new_activity)
        add_row(form_layout, "尝试自动绑定新活动", self.checkbox_try_auto_bind_new_activity)

        self.checkbox_force_sync_bind_with_djc = create_checkbox(cfg.force_sync_bind_with_djc)
        add_row(form_layout, "是否强制与道聚城的绑定角色同步", self.checkbox_force_sync_bind_with_djc)

        # -------------- 区域：集卡 --------------
        (
            self.collapsible_box_ark_lottery,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("集卡", top_layout)

        self.lineedit_auto_send_card_target_qqs = create_lineedit(
            list_to_str(cfg.auto_send_card_target_qqs),
            "填写要接收卡片的qq号列表，使用英文逗号分开，示例：123, 456, 789",
        )
        self.lineedit_auto_send_card_target_qqs.setValidator(QQListValidator())
        add_row(
            form_layout,
            "自动赠送卡片的目标QQ数组(这些QQ将接收来自其他QQ赠送的卡片)",
            self.lineedit_auto_send_card_target_qqs,
        )

        self.checkbox_enable_send_card_by_request = create_checkbox(cfg.enable_send_card_by_request)
        add_row(
            form_layout,
            "集卡赠送次数耗尽后，是否尝试通过索取的方式来赠送卡片",
            self.checkbox_enable_send_card_by_request,
        )

        self.checkbox_cost_all_cards_and_do_lottery_on_last_day = create_checkbox(
            cfg.cost_all_cards_and_do_lottery_on_last_day
        )
        add_row(
            form_layout,
            "是否在活动最后一天消耗所有卡牌来抽奖（若还有卡）",
            self.checkbox_cost_all_cards_and_do_lottery_on_last_day,
        )

        # -------------- 区域：心悦 --------------
        self.collapsible_box_xinyue, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "心悦相关", top_layout
        )

        self.lineedit_xinyue_send_card_target_qq = create_lineedit(cfg.xinyue_send_card_target_qq)
        self.lineedit_xinyue_send_card_target_qq.setValidator(QQValidator())
        add_row(
            form_layout,
            "心悦集卡赠送卡片目标QQ(这个QQ将接收来自其他QQ赠送的卡片)",
            self.lineedit_xinyue_send_card_target_qq,
        )

        self.fixed_teams = []
        for team in cfg.fixed_teams:
            self.fixed_teams.append(FixedTeamConfigUi(form_layout, team))

        # -------------- 区域：更新 --------------
        self.collapsible_box_update, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "更新", top_layout
        )

        self.checkbox_check_update_on_start = create_checkbox(cfg.check_update_on_start)
        add_row(form_layout, "启动时检查更新", self.checkbox_check_update_on_start)

        self.checkbox_check_update_on_end = create_checkbox(cfg.check_update_on_end)
        add_row(form_layout, "结束前检查更新", self.checkbox_check_update_on_end)

        self.checkbox_auto_update_on_start = create_checkbox(cfg.auto_update_on_start)
        add_row(form_layout, "自动更新（需要购买DLC才可生效）", self.checkbox_auto_update_on_start)

        # -------------- 区域：多进程 --------------
        (
            self.collapsible_box_multiprocessing,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("多进程", top_layout)

        self.checkbox_enable_multiprocessing = create_checkbox(cfg.enable_multiprocessing)
        add_row(form_layout, "是否启用多进程功能", self.checkbox_enable_multiprocessing)

        self.checkbox_enable_super_fast_mode = create_checkbox(cfg.enable_super_fast_mode)
        add_row(form_layout, "是否启用超快速模式（并行活动）", self.checkbox_enable_super_fast_mode)

        self.spinbox_multiprocessing_pool_size = create_spin_box(cfg.multiprocessing_pool_size, minimum=-1)
        add_row(
            form_layout,
            "进程池大小(0=cpu核心数,-1=当前账号数(普通)/4*cpu(超快速),其他=进程数)",
            self.spinbox_multiprocessing_pool_size,
        )

        self.checkbox_enable_multiprocessing_login = create_checkbox(cfg.enable_multiprocessing_login)
        add_row(
            form_layout,
            "是否启用多进程登录功能（如果分不清哪个号在登录，请关闭该选项）",
            self.checkbox_enable_multiprocessing_login,
        )

        # -------------- 区域：登录 --------------
        self.collapsible_box_login, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "登录", top_layout
        )

        self.checkbox_force_use_portable_chrome = create_checkbox(cfg.force_use_portable_chrome)
        add_row(form_layout, "强制使用便携版chrome", self.checkbox_force_use_portable_chrome)

        self.spinbox_force_use_chrome_major_version = create_spin_box(cfg.force_use_chrome_major_version)
        add_row(form_layout, "强制使用特定大版本的chrome（0表示默认版本）", self.spinbox_force_use_chrome_major_version)

        self.checkbox_run_in_headless_mode = create_checkbox(cfg.run_in_headless_mode)
        add_row(form_layout, "自动登录模式不显示浏览器界面", self.checkbox_run_in_headless_mode)

        self.login = LoginConfigUi(form_layout, cfg.login)

        # -------------- 区域：窗口大小调整 --------------
        (
            self.collapsible_box_window_size,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("窗口大小调整", top_layout)

        self.checkbox_enable_change_cmd_buffer = create_checkbox(cfg.enable_change_cmd_buffer)
        add_row(form_layout, "是否修改命令行缓存大小，以避免运行日志被截断", self.checkbox_enable_change_cmd_buffer)

        self.checkbox_enable_max_console = create_checkbox(cfg.enable_max_console)
        add_row(form_layout, "是否最大化窗口", self.checkbox_enable_max_console)

        self.checkbox_enable_min_console = create_checkbox(cfg.enable_min_console)
        add_row(form_layout, "是否最小化窗口", self.checkbox_enable_min_console)

        # -------------- 区域：其他 --------------
        self.collapsible_box_others, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "其他", top_layout
        )

        self.checkbox_try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once = create_checkbox(
            cfg.try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once
        )
        add_row(
            form_layout,
            "是否在全部账号运行完毕后再次领取编年史任务奖励\n（从而当本地两个号设置为搭档时可以领取到对方的经验，而不需要再运行一次）",
            self.checkbox_try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once,
        )

        self.checkbox_enable_alipay_redpacket_v3 = create_checkbox(cfg.enable_alipay_redpacket_v3)
        add_row(form_layout, "是否弹出支付宝红包活动图片", self.checkbox_enable_alipay_redpacket_v3)

        self.checkbox_config_ui_enable_high_dpi = create_checkbox(cfg.config_ui_enable_high_dpi)
        add_row(form_layout, "是否启用高DPI模式（如4k屏，重启生效）", self.checkbox_config_ui_enable_high_dpi)

        self.checkbox_bypass_proxy = create_checkbox(cfg.bypass_proxy)
        add_row(form_layout, "是否无视系统代理（VPN）", self.checkbox_bypass_proxy)

        self.checkbox_disable_cmd_quick_edit = create_checkbox(cfg.disable_cmd_quick_edit)
        add_row(form_layout, "是否禁用cmd命令行的快速编辑模式", self.checkbox_disable_cmd_quick_edit)

        self.checkbox_disable_sync_configs = create_checkbox(os.path.exists(disable_flag_file))
        add_row(form_layout, "是否禁用在本机自动备份还原配置功能", self.checkbox_disable_sync_configs)

        self.spinbox_notify_pay_expired_in_days = create_spin_box(cfg.notify_pay_expired_in_days, minimum=0)
        add_row(form_layout, "提前多少天提示付费过期", self.spinbox_notify_pay_expired_in_days)

        self.checkbox_allow_only_one_instance = create_checkbox(cfg.allow_only_one_instance)
        add_row(form_layout, "是否仅允许单个运行实例", self.checkbox_allow_only_one_instance)

        self.combobox_log_level = create_combobox(
            cfg.log_level,
            [
                "debug",
                "info",
                "warning",
                "error",
                "critical",
            ],
        )
        add_row(form_layout, "日志级别", self.combobox_log_level)

        self.spinbox_max_logs_size = create_spin_box(cfg.max_logs_size)
        add_row(form_layout, "日志目录最大允许大小（单位为MiB）", self.spinbox_max_logs_size)

        self.spinbox_keep_logs_size = create_spin_box(cfg.keep_logs_size)
        add_row(form_layout, "日志目录保留大小（单位为MiB）", self.spinbox_keep_logs_size)

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
        cfg.bypass_proxy = self.checkbox_bypass_proxy.isChecked()
        cfg.disable_cmd_quick_edit = self.checkbox_disable_cmd_quick_edit.isChecked()
        cfg.enable_change_cmd_buffer = self.checkbox_enable_change_cmd_buffer.isChecked()
        cfg.enable_max_console = self.checkbox_enable_max_console.isChecked()
        cfg.enable_min_console = self.checkbox_enable_min_console.isChecked()
        cfg.enable_multiprocessing = self.checkbox_enable_multiprocessing.isChecked()
        cfg.enable_super_fast_mode = self.checkbox_enable_super_fast_mode.isChecked()
        cfg.enable_multiprocessing_login = self.checkbox_enable_multiprocessing_login.isChecked()
        cfg.multiprocessing_pool_size = self.spinbox_multiprocessing_pool_size.value()
        cfg.check_update_on_start = self.checkbox_check_update_on_start.isChecked()
        cfg.check_update_on_end = self.checkbox_check_update_on_end.isChecked()
        cfg.auto_update_on_start = self.checkbox_auto_update_on_start.isChecked()
        cfg.notify_pay_expired_in_days = self.spinbox_notify_pay_expired_in_days.value()
        cfg.allow_only_one_instance = self.checkbox_allow_only_one_instance.isChecked()
        cfg.try_auto_bind_new_activity = self.checkbox_try_auto_bind_new_activity.isChecked()
        cfg.force_sync_bind_with_djc = self.checkbox_force_sync_bind_with_djc.isChecked()
        cfg.enable_alipay_redpacket_v3 = self.checkbox_enable_alipay_redpacket_v3.isChecked()
        cfg.try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once = (
            self.checkbox_try_take_dnf_helper_chronicle_task_awards_again_after_all_accounts_run_once.isChecked()
        )

        cfg.max_logs_size = self.spinbox_max_logs_size.value()
        cfg.keep_logs_size = self.spinbox_keep_logs_size.value()
        cfg.http_timeout = self.spinbox_http_timeout.value()
        cfg.log_level = self.combobox_log_level.currentText()
        cfg.auto_send_card_target_qqs = str_to_list(self.lineedit_auto_send_card_target_qqs.text())
        cfg.enable_send_card_by_request = self.checkbox_enable_send_card_by_request.isChecked()
        cfg.cost_all_cards_and_do_lottery_on_last_day = (
            self.checkbox_cost_all_cards_and_do_lottery_on_last_day.isChecked()
        )

        self.login.update_config(cfg.login)
        self.retry.update_config(cfg.retry)
        for idx, team in enumerate(self.fixed_teams):
            team.update_config(cfg.fixed_teams[idx])

        cfg.xinyue_send_card_target_qq = self.lineedit_xinyue_send_card_target_qq.text()

        # 特殊处理基于标记文件的开关
        if self.checkbox_disable_sync_configs.isChecked():
            if not os.path.exists(disable_flag_file):
                with open(disable_flag_file, "w", encoding="utf-8") as f:
                    f.write("ok")
        else:
            if os.path.exists(disable_flag_file):
                if os.path.isfile(disable_flag_file):
                    os.remove(disable_flag_file)
                else:
                    shutil.rmtree(disable_flag_file, ignore_errors=True)


class MajieluoConfigUi(QFrame):
    def __init__(self, cfg: MajieluoConfig, config_ui: ConfigUi, parent=None):
        super().__init__(parent)

        self.config_ui = config_ui

        self.from_config(cfg)

    def from_config(self, cfg: MajieluoConfig):
        # 根据配置初始化ui
        top_layout = QVBoxLayout()

        # -------------- 区域：选填和必填分割线 --------------
        add_vbox_seperator(
            top_layout, "完整使用本工具需要准备三个小号和一个大号，并确保他们是好友，且均配置在小助手的账号列表中"
        )

        btn_show_majieluo_usage = create_pushbutton("查看使用教程帖子（其中的方法二）", "Lime")
        top_layout.addWidget(btn_show_majieluo_usage)

        btn_show_majieluo_usage.clicked.connect(self.show_majieluo_usage)
        top_layout.addWidget(QHLine())

        # -------------- 区域：基础配置 --------------
        form_layout = QFormLayout()
        top_layout.addLayout(form_layout)

        self.lineedit_dahao_index = create_lineedit(
            cfg.dahao_index, placeholder_text="大号在配置中的账号序号，从1开始计算，如 1 表示第一个账号作为大号"
        )
        form_layout.addRow("大号序号", self.lineedit_dahao_index)

        self.lineedit_xiaohao_indexes = create_lineedit(
            list_to_str(cfg.xiaohao_indexes),
            placeholder_text="最多3个，使用英文逗号分隔，如 1,2,3 表示使用本地配置的第 1/2/3 个账号作为小号",
        )
        self.lineedit_xiaohao_indexes.setValidator(QQListValidator())
        form_layout.addRow("小号序号列表", self.lineedit_xiaohao_indexes)

        self.lineedit_xiaohao_qq_list = create_lineedit(
            list_to_str(cfg.xiaohao_qq_list),
            placeholder_text="最多3个，使用英文逗号分隔，如 123,456,789 表示三个小号的QQ号分别为123/456/789",
        )
        # self.lineedit_xiaohao_qq_list.setValidator(QQListValidator())
        form_layout.addRow("小号在马杰洛页面的Uin列表", self.lineedit_xiaohao_qq_list)
        form_layout.addRow(
            "获取说明",
            QLabel(
                "1. 打开马杰洛活动，找到赠送列表，一页页翻，直到找到小号\n"
                "2. 如果找不到你的小号，那就可以放弃了，只能手动赠送给其他qq\n"
                "3. 否则，可以在小号右侧的按钮处，右键，选择 检查元素，然后复制其中uin的值，形如（0502696b3b1e8cfe0ec987ec32be08a89）\n"
                "\n"
                "此外，本期一天只能送两次，需要只需要两个小号\n"
            ),
        )

        # -------------- 区域：发送礼盒链接给小号 --------------
        top_layout.addWidget(QHLine())

        btn_send_box_url = create_pushbutton(
            "步骤1：发送礼盒链接给小号（需要今天先登录过游戏）（点击后将登录大号，可能界面会没反应，请耐心等待）",
            "MediumSpringGreen",
        )
        top_layout.addWidget(btn_send_box_url)

        btn_send_box_url.clicked.connect(self.send_box_url)

        # -------------- 区域：使用小号领取礼盒 --------------
        form_layout = QFormLayout()
        top_layout.addLayout(form_layout)

        self.lineedit_scode_1 = create_lineedit(
            cfg.scode_1,
            placeholder_text="第1个小号收到的礼盒链接，直接整个复制过来，或者单独复制scode的值，形如 https://dnf.qq.com/cp/a20210730care/index.html?sCode=MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0= 或 MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=",
        )
        form_layout.addRow("SCode 1", self.lineedit_scode_1)

        self.lineedit_scode_2 = create_lineedit(
            cfg.scode_2,
            placeholder_text="第2个小号收到的礼盒链接，直接整个复制过来，或者单独复制scode的值，形如 https://dnf.qq.com/cp/a20210730care/index.html?sCode=MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0= 或 MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=",
        )
        form_layout.addRow("SCode 2", self.lineedit_scode_2)

        self.lineedit_scode_3 = create_lineedit(
            cfg.scode_3,
            placeholder_text="第3个小号收到的礼盒链接，直接整个复制过来，或者单独复制scode的值，形如 https://dnf.qq.com/cp/a20210730care/index.html?sCode=MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0= 或 MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=",
        )
        form_layout.addRow("SCode 3", self.lineedit_scode_3)

        top_layout.addWidget(QHLine())

        btn_open_box = create_pushbutton(
            "步骤2：设定的小号依次领取礼盒（点击后将依次登录小号，可能界面会没反应，请耐心等待）", "cyan"
        )
        top_layout.addWidget(btn_open_box)

        btn_open_box.clicked.connect(self.open_box)

        self.setLayout(make_scroll_layout(top_layout))

    def update_config(self, cfg: MajieluoConfig):
        cfg.dahao_index = self.lineedit_dahao_index.text()
        cfg.xiaohao_indexes = str_to_list(self.lineedit_xiaohao_indexes.text())
        cfg.xiaohao_qq_list = str_to_list(self.lineedit_xiaohao_qq_list.text())
        cfg.scode_1 = self.lineedit_scode_1.text()
        cfg.scode_2 = self.lineedit_scode_2.text()
        cfg.scode_3 = self.lineedit_scode_3.text()

    def show_majieluo_usage(self):
        webbrowser.open("https://bbs.colg.cn/thread-8255531-1-1.html")
        report_click_event("majieluo_tool")

    def send_box_url(self):
        cfg = self.config_ui.to_config()

        account_index = int(self.lineedit_dahao_index.text())
        xiaohao_qq_list = str_to_list(self.lineedit_xiaohao_qq_list.text())

        if account_index <= 0 or account_index > len(cfg.account_configs):
            show_message("配置有误", f"配置的大号序号({account_index}) 不对，正确范围是[1, {len(cfg.account_configs)}]")
            return

        account_config = cfg.account_configs[account_index - 1]

        djcHelper = DjcHelper(account_config, cfg.common)

        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        logger.info(color("bold_green") + f"发送宝箱链接给小号QQ: {xiaohao_qq_list}")

        results = djcHelper.majieluo_send_to_xiaohao(xiaohao_qq_list)
        msg = "\n".join(f"    {res}" for res in results)

        show_message(
            "后续流程",
            (
                "赠送结果如下:\n"
                f"{msg}\n"
                "\n"
                "0. 如果上述赠送结果显示OK，则按下面步骤继续操作。"
                "1. 链接已发送完毕，请在电脑登录大号QQ，依次点击各个小号的对话框里刚刚发送的礼盒链接，在浏览器中复制整个链接到各个Scode的输入框内\n"
                "2. 输入完毕后请点击 接收宝箱 按钮\n"
            ),
        )
        report_click_event("majieluo_send_box_url")

    def open_box(self):
        cfg = self.config_ui.to_config()

        indexes = [int(index) for index in str_to_list(self.lineedit_xiaohao_indexes.text())]
        scode_list = [
            parse_scode(self.lineedit_scode_1.text()),
            parse_scode(self.lineedit_scode_2.text()),
            parse_scode(self.lineedit_scode_3.text()),
        ]
        scode_list = [v for v in scode_list if len(v) != 0]

        if len(indexes) != len(scode_list):
            show_message("配置有误", f"配置的小号数目({len(indexes)})与scode数目({len(scode_list)})不一致")
            return

        for account_index in indexes:
            if account_index <= 0 or account_index > len(cfg.account_configs):
                show_message(
                    "配置有误", f"配置的小号序号({account_index}) 不对，正确范围是[1, {len(cfg.account_configs)}]"
                )
                return

        messages: list[str] = []

        for order_index, account_index in enumerate(indexes):  # 从1开始，第i个
            account_config = cfg.account_configs[account_index - 1]

            djcHelper = DjcHelper(account_config, cfg.common)

            djcHelper.fetch_pskey()
            djcHelper.check_skey_expired()
            djcHelper.get_bind_role_list()

            scode = scode_list[order_index]
            logger.info(f"第{order_index + 1}个小号领取刚刚运行后填写的Scode列表中第{order_index + 1}个scode - {scode}")

            ret, message = djcHelper.majieluo_open_box(scode)
            if ret == 0:
                messages.append(f"第 {order_index + 1} 个小号 {djcHelper.qq()} 领取礼盒成功")
            else:
                messages.append(f"第 {order_index + 1} 个小号 {djcHelper.qq()}：{message}")

            time.sleep(1)

        invite_count = self.query_invite_count()
        messages.append("")
        messages.append(f"已领取完毕，当前累计赠送次数为 {invite_count}/30")

        show_message("操作结果如下", "\n".join(messages))

        report_click_event("majieluo_open_box")

    def query_invite_count(self) -> int:
        cfg = self.config_ui.to_config()

        account_index = int(self.lineedit_dahao_index.text())

        account_config = cfg.account_configs[account_index - 1]

        djcHelper = DjcHelper(account_config, cfg.common)

        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        return djcHelper.query_invite_count()


class MoJieRenTab(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 根据配置初始化ui
        top_layout = QVBoxLayout()

        btn_open_doc = create_pushbutton("查看跳一跳小工具文档", "Lime")
        top_layout.addWidget(btn_open_doc)

        btn_open_doc.clicked.connect(self.show_usage)

        self.setLayout(make_scroll_layout(top_layout))

    def show_usage(self):
        webbrowser.open("https://bbs.colg.cn/thread-8615377-1-1.html")
        report_click_event("mo_jie_ren_tool")


class LoginConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: LoginConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: LoginConfig):
        add_form_seperator(form_layout, "自动点击头像登录")

        self.checkbox_enable_auto_click_avatar_in_auto_login = create_checkbox(
            cfg.enable_auto_click_avatar_in_auto_login
        )
        add_row(form_layout, "账密自动登录 时是否启用", self.checkbox_enable_auto_click_avatar_in_auto_login)

        self.checkbox_enable_auto_click_avatar_in_qr_login = create_checkbox(cfg.enable_auto_click_avatar_in_qr_login)
        add_row(form_layout, "扫码登录 时是否启用", self.checkbox_enable_auto_click_avatar_in_qr_login)

        add_form_seperator(form_layout, "自动处理滑动验证码")

        self.checkbox_auto_resolve_captcha = create_checkbox(cfg.auto_resolve_captcha)
        add_row(form_layout, "启用", self.checkbox_auto_resolve_captcha)

        self.doublespinbox_move_captcha_delta_width_rate_v2 = create_double_spin_box(
            cfg.move_captcha_delta_width_rate_v2
        )
        self.doublespinbox_move_captcha_delta_width_rate_v2.setSingleStep(0.01)
        add_row(
            form_layout, "每次尝试滑动验证码多少倍滑块宽度的偏移值", self.doublespinbox_move_captcha_delta_width_rate_v2
        )

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

        self.spinbox_login_by_click_avatar_finished_timeout = create_spin_box(
            cfg.login_by_click_avatar_finished_timeout
        )
        add_row(form_layout, "等待点击头像登录完成的超时时间", self.spinbox_login_by_click_avatar_finished_timeout)

    def update_config(self, cfg: LoginConfig):
        cfg.enable_auto_click_avatar_in_auto_login = self.checkbox_enable_auto_click_avatar_in_auto_login.isChecked()
        cfg.enable_auto_click_avatar_in_qr_login = self.checkbox_enable_auto_click_avatar_in_qr_login.isChecked()

        cfg.auto_resolve_captcha = self.checkbox_auto_resolve_captcha.isChecked()
        cfg.move_captcha_delta_width_rate_v2 = self.doublespinbox_move_captcha_delta_width_rate_v2.value()

        cfg.max_retry_count = self.spinbox_max_retry_count.value()
        cfg.retry_wait_time = self.spinbox_retry_wait_time.value()
        cfg.open_url_wait_time = self.spinbox_open_url_wait_time.value()
        cfg.load_page_timeout = self.spinbox_load_page_timeout.value()
        cfg.load_login_iframe_timeout = self.spinbox_load_login_iframe_timeout.value()
        cfg.login_timeout = self.spinbox_login_timeout.value()
        cfg.login_finished_timeout = self.spinbox_login_finished_timeout.value()
        cfg.login_by_click_avatar_finished_timeout = self.spinbox_login_by_click_avatar_finished_timeout.value()


class RetryConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: RetryConfig, parent=None):
        super().__init__(parent)

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
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: FixedTeamConfig):
        add_form_seperator(form_layout, f"心悦战场固定队 - {cfg.id}")

        self.checkbox_enable = create_checkbox(cfg.enable)
        add_row(form_layout, "启用", self.checkbox_enable)

        self.lineedit_id = create_lineedit(cfg.id, "固定队伍id，仅用于本地区分用")
        add_row(form_layout, "队伍id", self.lineedit_id)

        self.lineedit_members = create_lineedit(
            list_to_str(cfg.members), "固定队成员，必须是两个，则必须都配置在本地的账号列表中了，否则将报错，不生效"
        )
        self.lineedit_members.setValidator(QQListValidator())
        add_row(form_layout, "成员", self.lineedit_members)

    def update_config(self, cfg: FixedTeamConfig):
        cfg.enable = self.checkbox_enable.isChecked()
        cfg.id = self.lineedit_id.text()
        cfg.members = str_to_list(self.lineedit_members.text())


class AccountConfigUi(QWidget):
    login_mode_bidict = BiDict(
        {
            # "手动登录": "by_hand",
            "扫码/点击头像登录": "qr_login",
            "账号密码自动登录": "auto_login",
        }
    )

    def __init__(self, cfg: AccountConfig, common_cfg: CommonConfig, parent=None):
        super().__init__(parent)

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

        self.combobox_login_mode = create_combobox(
            self.login_mode_bidict.val_to_key.get(cfg.login_mode, "扫码/点击头像登录"),
            list(self.login_mode_bidict.key_to_val.keys()),
        )
        add_row(form_layout, "登录模式（可下拉切换）", self.combobox_login_mode)

        self.lineedit_account = create_lineedit(
            cfg.account_info.account,
            "账号密码模式下用于配置QQ信息，扫码模式下填写将尝试触发自动点击头像登录（若对应QQ客户端已登录）",
        )
        self.lineedit_account.setValidator(QQValidator())
        add_row(form_layout, "QQ账号", self.lineedit_account)

        # -------------- 区域：QQ信息 --------------
        (
            self.collapsible_box_account_password,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("密码", top_layout)

        self.account_info = AccountInfoConfigUi(form_layout, cfg.account_info)

        self.combobox_login_mode.currentTextChanged.connect(self.on_login_mode_change)
        self.on_login_mode_change(self.combobox_login_mode.currentText(), in_init_step=True)

        # -------------- 区域：选填和必填分割线 --------------
        add_vbox_seperator(top_layout, "以下内容为选填内容，不填仍可正常运行，不过部分活动将无法领取")

        # -------------- 区域：角色绑定 --------------
        (
            self.collapsible_box_vip_mentor,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "角色绑定（若不配置，则使用道聚城中绑定的角色）", top_layout
        )
        self.bind_role = BindRoleConfigUi(form_layout, cfg.bind_role, cfg, self.common_cfg)

        # -------------- 区域：道聚城 --------------
        self.collapsible_box_djc, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "道聚城", top_layout
        )

        self.checkbox_cannot_bind_dnf_v2 = create_checkbox(cfg.cannot_bind_dnf_v2)
        add_row(
            form_layout,
            (
                "无法在道聚城绑定dnf\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "\n"
                "    开启后将不再检查是否已在道聚城app进行绑定dnf角色，用于跳过开始阶段的检查dnf绑定流程\n"
                "    若实际没有进行绑定，在后续尝试绑定各个活动的角色时，会提示手动进行绑定\n"
                "\n"
                "    主要配合后面的【禁用绝大部分活动】开关使用，用于小号，被风控不能注册dnf账号，但是不影响用来当抽卡等活动的工具人"
            ),
            self.checkbox_cannot_bind_dnf_v2,
        )
        self.checkbox_cannot_bind_dnf_v2.stateChanged.connect(self.confirm_set_cannot_bind_dnf)

        self.mobile_game_role_info = MobileGameRoleInfoConfigUi(form_layout, cfg.mobile_game_role_info)

        # -------------- 区域：道聚城兑换 --------------
        (
            self.collapsible_box_djc_exchange,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "道聚城兑换（填 0 就是不兑换）（已支持 命运方舟）", top_layout
        )

        self.try_set_default_exchange_items_for_cfg(cfg)
        self.exchange_items = {}
        for exchange_item in cfg.exchange_items:
            self.exchange_items[exchange_item.unique_key()] = ExchangeItemConfigUi(form_layout, exchange_item)

        # -------------- 区域：心悦组队 --------------
        (
            self.collapsible_box_xinyue_team,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("心悦组队", top_layout)

        self.checkbox_enable_auto_match_xinyue_team = create_checkbox(cfg.enable_auto_match_xinyue_team)
        add_row(
            form_layout,
            "是否心悦自动匹配组队\n  （在同时配置本地组队的情况下，若勾选本开关且满足下列条件，会优先在线匹配）",
            self.checkbox_enable_auto_match_xinyue_team,
        )

        add_row(
            form_layout,
            "需要满足这些条件",
            QLabel(
                "1. 在付费生效期间\n" "2. 当前QQ是特邀会员或者心悦会员\n" "3. 上周心悦战场荣耀镖局并成功完成运镖 3 次\n"
            ),
        )

        # -------------- 区域：心悦特权专区兑换 --------------
        (
            self.collapsible_box_xinyue_exchange,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "心悦特权专区兑换（填 0 就是不兑换）", top_layout
        )

        self.try_set_default_xinyue_exchange_items_for_cfg(cfg)
        self.xinyue_exchange_items = {}
        for xinyue_exchange_item in cfg.xinyue_operations_v2:
            self.xinyue_exchange_items[xinyue_exchange_item.unique_key()] = XinyueOperationConfigUi(
                form_layout, xinyue_exchange_item
            )

        # -------------- 区域：dnf助手 --------------
        (
            self.collapsible_box_dnf_helper_info,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("dnf助手（每月的编年史）", top_layout)
        self.dnf_helper_info = DnfHelperInfoConfigUi(form_layout, cfg.dnf_helper_info)

        # -------------- 区域：漫画 --------------
        (
            self.collapsible_box_comic,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("漫画", top_layout)
        self.comic = ComicConfigUi(form_layout, cfg.comic)

        # -------------- 区域：集卡 --------------
        (
            self.collapsible_box_ark_lottery,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("集卡", top_layout)
        self.ark_lottery = ArkLotteryConfigUi(form_layout, cfg.ark_lottery, cfg, self.common_cfg)

        # -------------- 区域：dnf论坛 --------------
        (
            self.collapsible_box_dnf_bbs,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("dnf论坛", top_layout)

        self.lineedit_dnf_bbs_cookie = create_lineedit(
            cfg.dnf_bbs_cookie, "请填写论坛请求的完整cookie串，获取方式请点击右侧按钮"
        )

        btn_show_dnf_bbs_cookies_doc = create_pushbutton("查看文档", "cyan")
        btn_show_dnf_bbs_cookies_doc.clicked.connect(self.show_dnf_bbs_cookies_doc)

        layout = QHBoxLayout()
        layout.addWidget(self.lineedit_dnf_bbs_cookie)
        layout.addWidget(btn_show_dnf_bbs_cookies_doc)
        add_row(form_layout, "dnf论坛cookie", layout)

        self.lineedit_colg_cookie = create_lineedit(
            cfg.colg_cookie, "请填写论坛请求的完整cookie串，获取方式请点击右侧按钮"
        )

        btn_show_colg_cookies_doc = create_pushbutton("查看文档", "cyan")
        btn_show_colg_cookies_doc.clicked.connect(self.show_colg_cookies_doc)

        layout = QHBoxLayout()
        layout.addWidget(self.lineedit_colg_cookie)
        layout.addWidget(btn_show_colg_cookies_doc)
        add_row(form_layout, "colg cookie", layout)

        # -------------- 区域：心悦app --------------
        (
            self.collapsible_box_xinyue_app,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("心悦app", top_layout)

        self.btn_show_xinyue_app_guide = create_pushbutton(
            "点击查看心悦app的加密http请求体获取方式（相当复杂，建议手动打开app领取，不信邪可以点开试试-。-）", "cyan"
        )
        self.btn_show_xinyue_app_guide.clicked.connect(self.show_xinyue_app_guide)
        add_row(form_layout, "", self.btn_show_xinyue_app_guide)

        self.try_set_default_xinyue_app_operations_for_cfg(cfg)
        self.xinyue_app_operations = {}
        for operation in cfg.xinyue_app_operations:
            self.xinyue_app_operations[operation.name] = XinYueAppOperationConfigUi(form_layout, operation)

        # -------------- 区域：会员关怀 --------------
        (
            self.collapsible_box_vip_mentor,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("会员关怀", top_layout)
        self.vip_mentor = VipMentorConfigUi(form_layout, cfg.vip_mentor, cfg, self.common_cfg)

        # # -------------- 区域：hello语音（皮皮蟹） --------------
        # (
        #     self.collapsible_box_hello_voice,
        #     form_layout,
        # ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("hello语音（皮皮蟹）", top_layout)
        # self.hello_voice = HelloVoiceInfoConfigUi(form_layout, cfg.hello_voice)

        # -------------- 区域：其他 --------------
        self.collapsible_box_others, form_layout = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
            "其他", top_layout
        )

        self.lineedit_myhome_steal_xiaohao_qq_list = create_lineedit(
            list_to_str(cfg.myhome_steal_xiaohao_qq_list), "填写qq号列表，使用英文逗号分开，示例：123, 456, 789"
        )
        # add_row(form_layout, "我的小屋偷水稻的小号qq列表", self.lineedit_myhome_steal_xiaohao_qq_list)

        self.lineedit_myhome_extra_wanted_gift_name_list = create_lineedit(
            list_to_str(cfg.myhome_extra_wanted_gift_name_list),
            "填写奖励列表，使用英文逗号分开，示例：一次性材质转换器, 黑钻3天, 一次性继承装置",
        )
        # add_row(form_layout, "我的小屋想要额外提示兑换的奖励名称列表", self.lineedit_myhome_extra_wanted_gift_name_list)

        self.lineedit_ozma_ignored_rolename_list = create_lineedit(
            list_to_str(cfg.ozma_ignored_rolename_list),
            "填写角色名列表，使用英文逗号分开，示例：卢克奶妈一号, 卢克奶妈二号, 卢克奶妈三号",
        )
        # add_row(form_layout, "不参与奥兹玛竞速活动切换角色的角色名列表", self.lineedit_ozma_ignored_rolename_list)

        self.lineedit_gonghui_rolename_huizhang = create_lineedit(
            cfg.gonghui_rolename_huizhang, "公会活动-会长角色名称，如果不设置，则尝试符合条件的角色（优先当前角色）"
        )
        # add_row(form_layout, "公会活动-会长角色名称", self.lineedit_gonghui_rolename_huizhang)

        self.lineedit_gonghui_rolename_huiyuan = create_lineedit(
            cfg.gonghui_rolename_huiyuan, "公会活动-会员角色名称，如果不设置，则尝试符合条件的角色（优先当前角色）"
        )
        # add_row(form_layout, "公会活动-会员角色名称", self.lineedit_gonghui_rolename_huiyuan)

        self.checkbox_enable_majieluo_lucky = create_checkbox(cfg.enable_majieluo_lucky)
        # add_row(form_layout, "马杰洛活动是否尝试用配置的集卡回归角色领取见面礼", self.checkbox_enable_majieluo_lucky)

        self.checkbox_dnf_gonghui_enable_lottery = create_checkbox(cfg.function_switches.dnf_gonghui_enable_lottery)
        # add_row(form_layout, "公会活动是否进行积分抽奖", self.checkbox_dnf_gonghui_enable_lottery)

        self.combobox_take_award_34c_server_name = create_combobox(
            dnf_server_id_to_name(cfg.take_award_34c_server_id), dnf_server_name_list()
        )
        # add_row(form_layout, "wegame活动的34C角色 区服名称", self.combobox_take_award_34c_server_name)

        self.lineedit_take_award_34c_role_id = create_lineedit(
            cfg.take_award_34c_role_id,
            "角色ID（不是角色名称！！！），形如 1282822，可以点击下面的选项框来选择角色（需登录）",
        )
        self.lineedit_take_award_34c_role_id.setValidator(DNFRoleIdValidator())
        # add_row(form_layout, "wegame活动的34C角色 角色ID", self.lineedit_take_award_34c_role_id)

        self.role_selector = RoleSelector(
            "幸运勇士",
            self.combobox_take_award_34c_server_name,
            self.lineedit_take_award_34c_role_id,
            cfg,
            self.common_cfg,
        )
        # add_row(form_layout, "查询角色（需要登录）", self.role_selector.combobox_role_name)

        # -------------- 区域：活动开关 --------------
        (
            self.collapsible_box_function_switches,
            form_layout,
        ) = create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout("活动开关", top_layout)
        self.function_switches = FunctionSwitchesConfigUi(form_layout, cfg.function_switches)

        # -------------- 区域代码结束 --------------
        self.setLayout(make_scroll_layout(top_layout))

        init_collapsible_box_size(self)

    def update_config(self, cfg: AccountConfig):
        cfg.enable = self.checkbox_enable.isChecked()
        cfg.name = self.lineedit_name.text()
        cfg.login_mode = self.login_mode_bidict.key_to_val[self.combobox_login_mode.currentText()]
        cfg.account_info.account = self.lineedit_account.text()
        cfg.cannot_bind_dnf_v2 = self.checkbox_cannot_bind_dnf_v2.isChecked()

        cfg.myhome_steal_xiaohao_qq_list = str_to_list(self.lineedit_myhome_steal_xiaohao_qq_list.text())
        cfg.myhome_extra_wanted_gift_name_list = str_to_list(self.lineedit_myhome_extra_wanted_gift_name_list.text())
        cfg.ozma_ignored_rolename_list = str_to_list(self.lineedit_ozma_ignored_rolename_list.text())
        cfg.gonghui_rolename_huizhang = self.lineedit_gonghui_rolename_huizhang.text()
        cfg.gonghui_rolename_huiyuan = self.lineedit_gonghui_rolename_huiyuan.text()
        cfg.enable_majieluo_lucky = self.checkbox_enable_majieluo_lucky.isChecked()
        cfg.function_switches.dnf_gonghui_enable_lottery = self.checkbox_dnf_gonghui_enable_lottery.isChecked()
        cfg.enable_auto_match_xinyue_team = self.checkbox_enable_auto_match_xinyue_team.isChecked()

        cfg.dnf_bbs_cookie = self.lineedit_dnf_bbs_cookie.text()
        cfg.colg_cookie = self.lineedit_colg_cookie.text()

        cfg.take_award_34c_server_id = dnf_server_name_to_id(self.combobox_take_award_34c_server_name.currentText())
        cfg.take_award_34c_role_id = self.lineedit_take_award_34c_role_id.text()

        self.account_info.update_config(cfg.account_info)
        self.function_switches.update_config(cfg.function_switches)
        self.mobile_game_role_info.update_config(cfg.mobile_game_role_info)

        self.try_set_default_exchange_items_for_cfg(cfg)
        for unique_key, exchange_item in self.exchange_items.items():
            item_cfg = cfg.get_exchange_item_by_unique_key(unique_key)
            if item_cfg is None:
                continue

            exchange_item.update_config(item_cfg)

        self.try_set_default_xinyue_exchange_items_for_cfg(cfg, remove_fake_id_items=True)
        for unique_key, xinyue_exchange_item in self.xinyue_exchange_items.items():
            xinyue_item_cfg = cfg.get_xinyue_exchange_item_by_unique_key(unique_key)
            if xinyue_item_cfg is None:
                continue

            xinyue_exchange_item.update_config(xinyue_item_cfg)

        self.try_set_default_xinyue_app_operations_for_cfg(cfg)
        for name, operation in self.xinyue_app_operations.items():
            operation_cfg = cfg.get_xinyue_app_operation_by_name(name)
            if operation_cfg is None:
                continue

            operation.update_config(operation_cfg)

        self.ark_lottery.update_config(cfg.ark_lottery)
        self.vip_mentor.update_config(cfg.vip_mentor)
        self.bind_role.update_config(cfg.bind_role)
        self.dnf_helper_info.update_config(cfg.dnf_helper_info)
        # self.hello_voice.update_config(cfg.hello_voice)
        self.comic.update_config(cfg.comic)

    def confirm_set_cannot_bind_dnf(self, state: int):
        if state != Qt.Checked:
            return

        ret = show_confirm_message_box(
            "请确认",
            (
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "\n"
                "勾选这个开关后，将导致以下结果\n"
                "1. 将跳过检查dnf角色绑定流程，在未绑定道聚城的情况下可以继续使用\n"
                "2. 如果真的没用在道聚城中绑定dnf的角色，将导致后续流程中无法获取角色绑定信息，因此将无法完成自动绑定活动角色以及领取奖励\n"
                "\n"
                "这个开关主要用于小号，被风控不能注册dnf账号，但是不影响用来当抽卡等活动的工具人\n"
                "请确定你打开这个开关的目的是这样，如果仅仅是不想领取道聚城的奖励，其他奖励想正常使用，请勿打开本开关，请单独修改【道聚城兑换】相关的配置\n"
                "\n"
                "如果你单纯是因为小号注册后进游戏就提示被封禁而无法绑定角色，所以想开启这个开关，建议按照【使用教程/小号无法创建角色的解决方案.txt】中的流程去申请解封，一般一天左右就能解决\n"
            ),
        )
        if ret == QMessageBox.Cancel:
            self.checkbox_cannot_bind_dnf_v2.setCheckState(Qt.Unchecked)

    def show_xinyue_app_guide(self):
        report_click_event("show_xinyue_app_guide")
        show_message(
            "获取方式",
            (
                "以下流程相当复杂，需要了解【https抓包、手机抓包、调试】等背景知识，建议手动打开心悦app领取，不信邪可以按下面流程操作试试-。-\n"
                "\n"
                "抓包获取http body，以下流程以fiddler为例，具体流程或其他抓包软件的操作流程请自行根据各个环节关键词去百度学习\n"
                "\n"
                "1. 使用fiddler抓取手机心悦app中G分兑换的所有请求\n"
                "2. 从请求中找到请求body大小为150左右的那个请求（一般就是点击兑换后抓取到的第一个请求）\n"
                "3. 右侧点Inspector/HexView，选中Http Body部分的字节码（未标蓝部分），右击Copy/Copy as 0x##，然后粘贴出来，将其中的bytes复制到下列对应数组位置\n"
                "4. 对每个需要的兑换（如复活币、霸王契约）进行1/2/3步骤的操作（ps：每个兑换当天只能完成一次，如果当天抓失败了，就要第二天重试）\n"
                "\n"
                "5. 举例：\n"
                "5.1 假设复制出的结果为 byte[] arrOutput = { 0x58, 0x59, 0x01, 0x00, 0x00 };\n"
                "5.2 复制出bytes部分： 0x58, 0x59, 0x01, 0x00, 0x00\n"
                "5.3 粘贴以上内容到配置工具对应兑换的加密请求体输入框中\n"
            ),
        )

    def try_set_default_exchange_items_for_cfg(self, cfg: AccountConfig):
        # 特殊处理下道聚城兑换，若相应配置不存在，则加上默认不领取的配置，确保界面显示出来
        biz_to_default_item_info: dict[str, dict[str, str | list[tuple[str, str]]]] = {
            "dnf": {
                "iActionId": "",
                "iType": "",
                "items": [
                    ("3089", "高级装扮兑换券（7天）（每周限量1次）"),
                    ("3120", "魔界抗疲劳秘药（10点）（每周限量1次）"),
                    ("3088", "装备品级调整箱（2个）（每月限兑1次）"),
                    ("110", "成长之契约（3天）（每年限兑5次）"),
                    ("107", "达人之契约（3天）（每天限兑2次）"),
                    ("382", "晶之契约（3天）（每天限兑2次）"),
                    ("381", "复活币（每天限兑2次）"),
                    ("754", "装扮属性调整箱（高级）（1个）（每天限兑1次）"),
                    ("383", "闪亮的雷米援助(15个)"),
                ],
            },
            "fz": {
                "iActionId": "29657",
                "iType": "26",
                "items": [
                    ("4376", "[每周]艾芙娜委托 1（1个）（每月限兑1次）"),
                    ("4377", "[每日]艾芙娜委托完成券（3个）（每周限兑1次）"),
                    ("4375", "交易牌x5（每日限兑1次）"),
                    ("4374", "复活羽毛x5（每日限兑1次）"),
                    ("4373", "跳跃精华x5（每日限兑1次）"),
                    ("4389", "命运方舟惊喜抽奖宝箱（每日限兑5次）"),
                ],
            },
        }
        # 已经废弃的道具信息
        biz_to_deprecated_item_info: dict[str, dict[str, str | list[tuple[str, str]]]] = {
            "dnf": {
                "iActionId": "",
                "iType": "",
                "items": [
                    ("111", "高级装扮兑换券（无期限）（活动期间5次）"),
                    ("753", "装备品级调整箱（5个）（每天限兑2次）"),
                    ("755", "魔界抗疲劳秘药（10点）（每天限兑1次）"),
                ],
            },
        }

        exchange_items: list[ExchangeItemConfig] = []

        # 初始化列表，剔除已废弃的道具
        for item in cfg.exchange_items:
            deprecated = False
            for sBizCode, default_item_info in biz_to_deprecated_item_info.items():
                if item.sBizCode != sBizCode:
                    continue

                for iGoodsId, sGoodsName in default_item_info["items"]:
                    if item.iGoodsId == iGoodsId:
                        deprecated = True
                        logger.warning(
                            color("bold_yellow") + f"道聚城道具 {sGoodsName} {iGoodsId} 已废弃，将从配置中移除"
                        )
                        break

            if not deprecated:
                exchange_items.append(item)

        # 记录下已有的配置的信息，方便去重
        all_item_biz_ids = set()
        for item in exchange_items:
            all_item_biz_ids.add((item.sBizCode, item.iGoodsId))

        for sBizCode, default_item_info in biz_to_default_item_info.items():
            iActionId = default_item_info["iActionId"]
            iType = default_item_info["iType"]

            for iGoodsId, sGoodsName in default_item_info["items"]:
                if (sBizCode, iGoodsId) in all_item_biz_ids:
                    continue
                all_item_biz_ids.add((sBizCode, iGoodsId))

                item = ExchangeItemConfig()
                item.iGoodsId = iGoodsId
                item.sGoodsName = sGoodsName
                item.count = 0
                item.iActionId = iActionId  # type: ignore
                item.iType = iType  # type: ignore
                item.sBizCode = sBizCode
                exchange_items.append(item)

        cfg.exchange_items = exchange_items

    def try_set_default_xinyue_exchange_items_for_cfg(self, cfg: AccountConfig, remove_fake_id_items: bool = False):
        _minus_id = 0

        def gen_fake_default_item_with_decrease_minus_id(item_name: str) -> tuple[int, str]:
            nonlocal _minus_id
            _minus_id = _minus_id - 1

            marker = "-" * 5

            return (_minus_id, f"{marker} {item_name} {marker}")

        def is_fake_id_for_display(xyop_cfg: XinYueOperationConfig) -> bool:
            """
            为了配置工具更加美观，在配置工具展示时，会添加一些id为负数，名称为接下来条目的类别的条目
            在启动初始化时，会添加这些虚假配置，并参数排序，从而看起来比较直观
            在保存前，会从配置中移除，而界面部分会继续显示，从而不影响实际操作
            """
            return xyop_cfg.iFlowId < 0

        # 特殊处理下心悦兑换，若相应配置不存在，则加上默认不领取的配置，确保界面显示出来，方便用户进行配置
        default_items = [
            gen_fake_default_item_with_decrease_minus_id("以上为已配置兑换的道具，优先展示"),
            (131708, "抗疲劳秘药30*1-（日限3）-成就点：30"),
            (130822, "抗疲劳秘药5-（每日3次）-10勇士币"),
            (130823, "抗疲劳秘药10-（每日3次）-20勇士币"),
            (130824, "抗疲劳秘药20*1-（每日3次）-40勇士币"),
            (130825, "抗疲劳秘药30*1-（每日3次）-60勇士币"),
            (131698, "装备提升礼盒-（日限20）-成就点：10"),
            # (912508, "新版装备提升礼盒(需30点勇士币)(每日20次)（可批量兑换）"),
            (130821, "装备提升礼盒-（每日20次）-30勇士币"),
            (131671, "复活币礼盒*3-（日限10）-成就点：8"),
            # (821281, "新版复活币*1(日限100)(需1点勇士币)（可批量兑换）"),
            (130788, "复活币礼盒（1个）-（每日100次）-1勇士币"),
            (130827, "高级装扮兑换券-（每月1次）-400勇士币"),
            #
            # 其他的可兑换条目，则按照对应页面的处理流程来操作
            # hack: 下面不需要过滤掉上面优先展示的条目，因为后续添加配置的代码中，会确保按顺序处理，且不重复添加
            gen_fake_default_item_with_decrease_minus_id("普通兑换"),
            (130788, "复活币礼盒（1个）-（每日100次）-1勇士币"),
            (130819, "一次性材质转化器-（每日1次）-28勇士币"),
            (130820, "神秘契约礼包-（每日20次）-10勇士币"),
            (130821, "装备提升礼盒-（每日20次）-30勇士币"),
            (130822, "抗疲劳秘药5-（每日3次）-10勇士币"),
            (130823, "抗疲劳秘药10-（每日3次）-20勇士币"),
            (130824, "抗疲劳秘药20*1-（每日3次）-40勇士币"),
            (130825, "抗疲劳秘药30*1-（每日3次）-60勇士币"),
            (130826, "物品栏扩展券-（限制200次）-150勇士币"),
            (130827, "高级装扮兑换券-（每月1次）-400勇士币"),
            (130829, "华丽的徽章自选礼盒-（每周3次）-150勇士币"),
            (130831, "升级券（50-109）-（每月1次）-100勇士币"),
            (130832, "金库升级工具-（限200次）-400勇士币"),
            #
            gen_fake_default_item_with_decrease_minus_id("心悦兑换"),
            (130833, "骑士贞德*1-600勇士币"),
            (130956, "巫女桔梗*1-600勇士币"),
            (130957, "女仆十六夜*1-600勇士币"),
            (130958, "忍者千代火舞*1-600勇士币"),
            (130959, "帅帅小木偶*1-600勇士币"),
            (130960, "美美小木偶*1-600勇士币"),
            (130961, "咕咕鸡*1-600勇士币"),
            (131042, "铜色皮特兰猪*1-600勇士币"),
            (131043, "霓裳仙子*1-600勇士币"),
            (131044, "枯灵*1-600勇士币"),
            (131045, "沙滩排球*1-600勇士币"),
            (131046, "小柳树*1-600勇士币"),
            #
            gen_fake_default_item_with_decrease_minus_id("成就点兑换"),
            gen_fake_default_item_with_decrease_minus_id(" 镖局宝库"),
            (131671, "复活币礼盒*3-（日限10）-成就点：8"),
            (131695, "神器符文自选礼盒-（日限20）-成就点：8"),
            (131696, "一次性材质转化器-（日限1）-成就点：10"),
            (131697, "神秘契约礼包（1天）-（日限20）-成就点：20"),
            (131698, "装备提升礼盒-（日限20）-成就点：10"),
            (131699, "华丽的徽章神秘礼盒-（日限20）-成就点：20"),
            (131708, "抗疲劳秘药30*1-（日限3）-成就点：30"),
            (131709, "升级券（50-109）-（月限1）-成就点：50"),
            gen_fake_default_item_with_decrease_minus_id(" 专属光环"),
            (132380, "腾龙光环（心悦1）-330成就点"),
            (133120, "腾龙光环（心悦2-3）-330成就点"),
            (133123, "腾龙光环（心悦4-5）-330成就点"),
            (133124, "星空射手光环（心悦1）-330成就点"),
            (133125, "星空射手光环（心悦2-3）-330成就点"),
            (133127, "星空射手光环（心悦4-5）-330成就点"),
            (133128, "星恋双鱼（心悦1）-330成就点"),
            (133131, "星恋双鱼（心悦2-3）-330成就点"),
            (133133, "星恋双鱼（心悦4-5）-330成就点"),
            (133135, "星愿天蝎（心悦1）-330成就点"),
            (133137, "星愿天蝎（心悦2-3）-330成就点"),
            (133138, "星愿天蝎（心悦4-5）-330成就点"),
            gen_fake_default_item_with_decrease_minus_id(" 专属宠物"),
            (133139, "天小蝎（心悦1）-260成就点"),
            (133141, "天小蝎（心悦2-3）-260成就点"),
            (133142, "天小蝎（心悦4-5）-260成就点"),
            (133143, "羊小咩（心悦1）-260成就点"),
            (133144, "羊小咩（心悦2-3）-260成就点"),
            (133147, "羊小咩（心悦4-5）-260成就点"),
            (133148, "牛小哞（心悦1）-260成就点"),
            (133149, "牛小哞（心悦2-3）-260成就点"),
            (133150, "牛小哞（心悦4-5）-260成就点"),
            (133151, "弓小弦（心悦1）-260成就点"),
            (133152, "弓小弦（心悦2-3）-260成就点"),
            (133153, "弓小弦（心悦4-5）-260成就点"),
            (133154, "甜小鱼（心悦1）-360成就点"),
            (133155, "甜小鱼（心悦2-3）-360成就点"),
            (133156, "甜小鱼（心悦4-5）-360成就点"),
            (133157, "星小双（心悦1）-260成就点"),
            (133158, "星小双（心悦2-3）-260成就点"),
            (133159, "星小双（心悦4-5）-260成就点"),
            (133160, "水小瓶（心悦1）-260成就点"),
            (133161, "水小瓶（心悦2-3）-260成就点"),
            (133162, "水小瓶（心悦4-5）-260成就点"),
            gen_fake_default_item_with_decrease_minus_id(" 专属称号"),
            (133163, "最强战王（心悦1）-260成就点"),
            (133164, "最强战皇（心悦2-3）-260成就点"),
            (133165, "最强战神（心悦4-5）-260成就点"),
        ]

        # 记录下已有的配置的信息，方便去重
        all_item_keys = set()
        for item in cfg.xinyue_operations_v2:
            all_item_keys.add(item.unique_key())

        # 将不存在的部分添加到配置后面
        for iFlowId, sFlowName in default_items:
            item = XinYueOperationConfig()
            item.iFlowId = iFlowId
            item.sFlowName = sFlowName
            item.count = 0

            key = item.unique_key()
            if key in all_item_keys:
                # 如果配置文件中的对应条目的名字与这里不一样，则改为这里的，这样偶尔填错了名字，也可以在后续通过代码内修正为正确的名字
                item_cfg_from_config_file = cfg.get_xinyue_exchange_item_by_unique_key(key)
                if item_cfg_from_config_file is not None and item_cfg_from_config_file.sFlowName != item.sFlowName:
                    item_cfg_from_config_file.sFlowName = item.sFlowName

                continue
            all_item_keys.add(key)

            cfg.xinyue_operations_v2.append(item)

        if remove_fake_id_items:
            # 移除仅用于展示的虚假条目（如实际保存的时候）
            cfg.xinyue_operations_v2 = [item for item in cfg.xinyue_operations_v2 if not is_fake_id_for_display(item)]

        self.sort_xinyue_exchange_items(cfg, default_items)

    def sort_xinyue_exchange_items(self, cfg: AccountConfig, default_items: list[tuple[int, str]]):
        # 调整下配置的顺序，使其更加直观
        config_file_flow_id_to_index: dict[int, int] = {}
        for idx, item in enumerate(cfg.xinyue_operations_v2):
            config_file_flow_id_to_index[item.iFlowId] = idx

        default_flow_id_to_index: dict[int, int] = {}
        for idx, info in enumerate(default_items):
            iFlowId, sFlowName = info

            default_flow_id_to_index[iFlowId] = idx

        # 默认是升序，从小到大。cmp函数负数表示左边的较小，正数则表示右边的较小，而较小的会排在前面
        def cmp_func(left: XinYueOperationConfig, right: XinYueOperationConfig) -> int:
            # 排序顺序优先级如下
            if left.count > 0 and right.count > 0:
                # 两者配置了兑换次数的，则按照当前配置文件中的顺序（这里不需要9999，但为了安全起见，也放着）
                return config_file_flow_id_to_index.get(left.iFlowId, 9999) - config_file_flow_id_to_index.get(
                    right.iFlowId, 9999
                )
            elif left.count > 0:
                # 只有左边配置了兑换次数的，优先左边
                return -1
            elif right.count > 0:
                # 只有右边配置了兑换次数的，优先右边
                return 1
            else:
                # 两者都未配置兑换次数，则按照默认配置的顺序（若其中一个不在其中，如设置了周常月常那几个，则对应条目排在后面（也就是给一个很大的值9999））
                return default_flow_id_to_index.get(left.iFlowId, 9999) - default_flow_id_to_index.get(
                    right.iFlowId, 9999
                )

        cfg.xinyue_operations_v2.sort(key=functools.cmp_to_key(cmp_func))

    def try_set_default_xinyue_app_operations_for_cfg(self, cfg: AccountConfig):
        all_operations = set()
        for operation in cfg.xinyue_app_operations:
            all_operations.add(operation.name)

        # 特殊处理下心悦app兑换，若相应配置不存在，咋加上默认不领取的配置，确保界面显示出来
        default_operations = [
            ("兑换复活币", ""),
            ("兑换雷米", ""),
            ("兑换霸王契约", ""),
        ]
        for name, encrypted_raw_http_body in default_operations:
            operation = XinYueAppOperationConfig()
            operation.name = name
            operation.encrypted_raw_http_body = encrypted_raw_http_body

            if operation.name in all_operations:
                continue

            cfg.xinyue_app_operations.append(operation)

    def on_login_mode_change(self, text, in_init_step=False):
        disable = text != self.login_mode_bidict.val_to_key["auto_login"]

        # 需要排除一个特例：
        # 启动时界面还未显示时，所有组件都是hidden状态
        # 此时如果是自动登录模式，不需要特别调用setHidden(False)，因为组件在gui初始化完毕后都默认是启用的
        # 此时如果调用了，会出现在主窗口弹出来之前，快速显示并消失各个账号的账号密码登录窗口，看上去很奇怪
        need_set_hidden = not (in_init_step and not disable)
        if need_set_hidden:
            self.collapsible_box_account_password.setHidden(disable)
        self.collapsible_box_account_password.set_fold(disable)
        self.account_info.setDisabled(disable)

    def show_dnf_bbs_cookies_doc(self):
        webbrowser.open("https://docs.qq.com/doc/DYlVnT1ZVVUlKYWpJ")
        report_click_event("dnf_bbs_cookies_doc")

    def show_colg_cookies_doc(self):
        webbrowser.open("https://docs.qq.com/doc/DYnZXenZRbkxWbE1O")
        report_click_event("colg_cookies_doc")


class AccountInfoConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: AccountInfoConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: AccountInfoConfig):
        self.lineedit_password = create_lineedit(
            cfg.password, "使用账号密码自动登录有风险_请理解这个功能到底如何使用你的账号密码后再决定是否使用"
        )
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
        cfg.password = self.lineedit_password.text()

    def setDisabled(self, disabled: bool) -> None:
        super().setDisabled(disabled)

        self.lineedit_password.setDisabled(disabled)


class FunctionSwitchesConfigUi(QWidget):
    act_category_to_act_desc_switch_list = {
        "普通skey": [
            # 免费活动
            ("道聚城", "get_djc"),
            ("道聚城许愿", "make_wish"),
            ("DNF地下城与勇士心悦特权专区", "get_xinyue"),
            ("心悦app", "get_xinyue_app"),
            ("dnf论坛签到", "get_dnf_bbs_signin"),
            ("小酱油周礼包和生日礼包", "get_xiaojiangyou"),
            ("DNF福利中心兑换", "get_dnf_welfare"),
            # 收费活动
            ("dnf助手编年史（需配置助手userId和token和uniqueRoleId）", "get_dnf_helper_chronicle"),
            ("绑定手机活动", "get_dnf_bind_phone"),
            ("DNF漫画预约活动", "get_dnf_comic"),
            ("DNF神界成长之路", "get_dnf_shenjie_grow_up"),
            ("DNF落地页活动", "get_dnf_luodiye"),
            ("colg每日签到", "get_colg_signin"),
            ("DNFxSNK", "get_dnf_snk"),
        ],
        "QQ空间pskey": [
            ("集卡", "get_ark_lottery"),
            ("会员关怀", "get_vip_mentor"),
            ("超级会员", "get_dnf_super_vip"),
            ("黄钻", "get_dnf_yellow_diamond"),
            ("qq会员杯", "get_dnf_club_vip"),
        ],
        "安全管家pskey": [
            ("管家蚊子腿", "get_guanjia"),
        ],
    }

    # 已过期的活动，方便快速加回去
    expired_act_category_to_act_desc_switch_list = {
        "普通skey": [
            ("9163补偿", "get_dnf_9163_apologize"),
            ("超核勇士wpe", "get_dnf_chaohe_wpe"),
            ("DNF年货铺", "get_dnf_nianhuopu"),
            ("DNF心悦wpe", "get_dnf_xinyue"),
            ("dnf助手活动wpe", "get_dnf_helper_wpe"),
            ("colg其他活动", "get_colg_other_act"),
            ("拯救赛利亚", "get_dnf_save_sailiyam"),
            ("WeGame活动", "get_dnf_wegame"),
            ("DNF马杰洛的规划", "get_majieluo"),
            ("神界预热", "get_dnf_shenjie_yure"),
            ("qq视频蚊子腿-爱玩", "get_qq_video"),
            ("DNF预约", "get_dnf_reservation"),
            ("DNF娱乐赛", "get_dnf_game"),
            ("dnf助手活动", "get_dnf_helper"),
            ("勇士的冒险补给", "get_maoxian"),
            ("腾讯游戏信用礼包", "get_credit_xinyue_gift"),
            ("黑钻礼包", "get_heizuan_gift"),
            ("DNF心悦", "get_dnf_xinyue"),
            ("DNF心悦Dup", "get_dnf_xinyue"),
            ("dnf周年拉好友", "get_dnf_anniversary_friend"),
            ("DNF周年庆登录活动", "get_dnf_anniversary"),
            ("心悦app理财礼卡", "get_xinyue_financing"),
            ("冒险的起点", "get_maoxian_start"),
            ("DNF巴卡尔竞速", "get_dnf_bakaer"),
            ("和谐补偿活动", "get_dnf_compensate"),
            ("colg其他活动", "get_colg_other_act"),
            ("巴卡尔对战地图", "get_dnf_bakaer_map"),
            ("巴卡尔大作战", "get_dnf_bakaer_fight"),
            ("魔界人探险记", "get_mojieren"),
            ("DNF集合站", "get_dnf_collection"),
            ("超级会员", "get_dnf_super_vip"),
            ("集卡", "get_ark_lottery"),
        ]
    }

    def __init__(self, form_layout: QFormLayout, cfg: FunctionSwitchesConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: FunctionSwitchesConfig):
        add_form_seperator(form_layout, "各功能开关")

        self.checkbox_disable_most_activities_v2 = create_checkbox(cfg.disable_most_activities_v2)
        add_row(
            form_layout,
            (
                "禁用绝大部分活动\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "\n"
                "    勾选后将几乎不能领取任何活动，主要是给【QQ空间集卡】工具人小号使用的\n"
                "    以下活动需要单独关闭\n"
                "       1. 领取道聚城\n"
                "       2. 道聚城许愿\n"
                "       3. 心悦特权专区\n"
                "       4. 集卡"
            ),
            self.checkbox_disable_most_activities_v2,
        )
        self.checkbox_disable_most_activities_v2.stateChanged.connect(self.confirm_set_disable_most_activities)

        from util import padLeftRight

        def _pad(name: str) -> str:
            return padLeftRight(name, 8, pad_char="  ")

        def make_title(name: str, influence: str, suffix: str = "登录") -> str:
            title = f"【禁用 {_pad(name)} {suffix}】"
            if influence != "":
                title = f"{title}    {influence}"

            return title

        self.checkbox_disable_share = create_checkbox(cfg.disable_share)
        add_row(
            form_layout,
            make_title("分享", "影响各种活动中需要实际分享才能领奖的部分", "功能"),
            self.checkbox_disable_share,
        )

        # ----------------------------------------------------------
        add_form_seperator(form_layout, "登录类型开关")

        self.checkbox_disable_login_mode_normal = create_checkbox(cfg.disable_login_mode_normal)
        add_row(form_layout, make_title("普通", "绝大部分活动"), self.checkbox_disable_login_mode_normal)

        self.checkbox_disable_login_mode_qzone = create_checkbox(cfg.disable_login_mode_qzone)
        add_row(
            form_layout, make_title("QQ空间", "集卡、QQ会员、黄钻、会员关怀等"), self.checkbox_disable_login_mode_qzone
        )

        self.checkbox_disable_login_mode_iwan = create_checkbox(cfg.disable_login_mode_iwan)
        add_row(form_layout, make_title("爱玩", "qq视频蚊子腿-爱玩"), self.checkbox_disable_login_mode_iwan)

        self.checkbox_disable_login_mode_guanjia = create_checkbox(cfg.disable_login_mode_guanjia)
        add_row(form_layout, make_title(" 安全管家 ", "安全管家"), self.checkbox_disable_login_mode_guanjia)

        self.checkbox_disable_login_mode_xinyue = create_checkbox(cfg.disable_login_mode_xinyue)
        add_row(
            form_layout,
            make_title("心悦", "dnf助手专属、编年史、心悦战场等各类wpe活动"),
            self.checkbox_disable_login_mode_xinyue,
        )

        self.checkbox_disable_login_mode_supercore = create_checkbox(cfg.disable_login_mode_supercore)
        add_row(form_layout, make_title("超享玩", "超享玩"), self.checkbox_disable_login_mode_supercore)

        self.checkbox_disable_login_mode_djc = create_checkbox(cfg.disable_login_mode_djc)
        add_row(
            form_layout,
            make_title("道聚城", "道聚城任务、兑换、查询道聚城绑定角色信息"),
            self.checkbox_disable_login_mode_djc,
        )

        # ----------------------------------------------------------
        # 不同登录类型的活动开关
        for act_actegory, act_desc_swtich_list in self.act_category_to_act_desc_switch_list.items():
            add_form_seperator(form_layout, act_actegory)

            for act_name, switch_name in act_desc_swtich_list:
                checkbox_name = f"checkbox_{switch_name}"
                checkbox = create_checkbox(getattr(cfg, switch_name))

                setattr(self, checkbox_name, checkbox)
                add_row(form_layout, act_name, checkbox)

    def update_config(self, cfg: FunctionSwitchesConfig):
        # 总控制
        cfg.disable_most_activities_v2 = self.checkbox_disable_most_activities_v2.isChecked()
        cfg.disable_share = self.checkbox_disable_share.isChecked()

        # 登陆方式的开关
        cfg.disable_login_mode_normal = self.checkbox_disable_login_mode_normal.isChecked()
        cfg.disable_login_mode_qzone = self.checkbox_disable_login_mode_qzone.isChecked()
        cfg.disable_login_mode_iwan = self.checkbox_disable_login_mode_iwan.isChecked()
        cfg.disable_login_mode_guanjia = self.checkbox_disable_login_mode_guanjia.isChecked()
        cfg.disable_login_mode_xinyue = self.checkbox_disable_login_mode_xinyue.isChecked()
        cfg.disable_login_mode_supercore = self.checkbox_disable_login_mode_supercore.isChecked()
        cfg.disable_login_mode_djc = self.checkbox_disable_login_mode_djc.isChecked()

        # 不同登录类型的活动开关
        for _, act_desc_swtich_list in self.act_category_to_act_desc_switch_list.items():
            for _, switch_name in act_desc_swtich_list:
                checkbox_name = f"checkbox_{switch_name}"
                checkbox = getattr(self, checkbox_name)

                setattr(cfg, switch_name, checkbox.isChecked())

    def confirm_set_disable_most_activities(self, state: int):
        if state != Qt.Checked:
            return

        ret = show_confirm_message_box(
            "请确认",
            (
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "    !!! 如果你不能理解下面这几句话是什么意思，就千万不要勾选这个开关 !!!\n"
                "\n"
                "勾选这个开关后，将导致无法领取绝大部分活动，请确认这是你想要做的。\n"
                "\n"
                "这个开关主要用于小号，被风控不能注册dnf账号，但是不影响用来当抽卡等活动的工具人\n"
                "\n"
            ),
        )
        if ret == QMessageBox.Cancel:
            self.checkbox_disable_most_activities_v2.setCheckState(Qt.Unchecked)


class MobileGameRoleInfoConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: MobileGameRoleInfoConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: MobileGameRoleInfoConfig):
        self.combobox_game_name = create_combobox(
            cfg.game_name, ["无", "任意手游", *sorted(get_name_2_mobile_game_info_map().keys())]
        )
        add_row(
            form_layout,
            "完成礼包达人任务的手游名称（不玩手游可直接选 无）（PS：目前这个任务暂时无法自动完成）",
            self.combobox_game_name,
        )

    def update_config(self, cfg: MobileGameRoleInfoConfig):
        cfg.game_name = self.combobox_game_name.currentText()


class ExchangeItemConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: ExchangeItemConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: ExchangeItemConfig):
        self.spinbox_count = create_spin_box(cfg.count, 10)
        add_row(form_layout, f"{cfg.sGoodsName}", self.spinbox_count)

    def update_config(self, cfg: ExchangeItemConfig):
        cfg.count = self.spinbox_count.value()


class XinyueOperationConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: XinYueOperationConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: XinYueOperationConfig):
        self.spinbox_count = create_spin_box(cfg.count, 999)
        add_row(form_layout, f"{cfg.sFlowName}", self.spinbox_count)

    def update_config(self, cfg: XinYueOperationConfig):
        cfg.count = self.spinbox_count.value()


class XinYueAppOperationConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: XinYueAppOperationConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: XinYueAppOperationConfig):
        self.lineedit_encrypted_raw_http_body = create_lineedit(
            bytes_arr_to_hex_str(cfg.encrypted_raw_http_body), "抓包获取的加密http请求体，形如 0x58, 0x59, 0x01, 0x00, 0x00"  # type: ignore
        )
        add_row(form_layout, f"{cfg.name}", self.lineedit_encrypted_raw_http_body)

    def update_config(self, cfg: XinYueAppOperationConfig):
        cfg.encrypted_raw_http_body = hex_str_to_bytes_arr(self.lineedit_encrypted_raw_http_body.text())


class ArkLotteryConfigUi(QWidget):
    def __init__(
        self,
        form_layout: QFormLayout,
        cfg: ArkLotteryConfig,
        account_cfg: AccountConfig,
        common_cfg: CommonConfig,
        parent=None,
    ):
        super().__init__(parent)

        self.account_cfg = account_cfg
        self.common_cfg = common_cfg

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: ArkLotteryConfig):
        self.combobox_lucky_dnf_server_name = create_combobox(
            dnf_server_id_to_name(cfg.lucky_dnf_server_id), dnf_server_name_list()
        )
        add_row(form_layout, "幸运勇士区服名称", self.combobox_lucky_dnf_server_name)

        self.lineedit_lucky_dnf_role_id = create_lineedit(
            cfg.lucky_dnf_role_id,
            "角色ID（不是角色名称！！！），形如 1282822，可以点击下面的选项框来选择角色（需登录）",
        )
        self.lineedit_lucky_dnf_role_id.setValidator(DNFRoleIdValidator())
        add_row(form_layout, "幸运勇士角色ID", self.lineedit_lucky_dnf_role_id)

        self.role_selector = RoleSelector(
            "幸运勇士",
            self.combobox_lucky_dnf_server_name,
            self.lineedit_lucky_dnf_role_id,
            self.account_cfg,
            self.common_cfg,
        )
        add_row(form_layout, "查询角色（需要登录）", self.role_selector.combobox_role_name)

        self.checkbox_need_take_awards = create_checkbox(cfg.need_take_awards)
        add_row(form_layout, "领取礼包", self.checkbox_need_take_awards)

        cost_all_cards_and_do_lottery = cfg.act_id_to_cost_all_cards_and_do_lottery.get(
            self.get_ark_lottery_act_id(), False
        )
        self.checkbox_cost_all_cards_and_do_lottery = create_checkbox(cost_all_cards_and_do_lottery)
        add_row(form_layout, "是否消耗所有卡牌来抽奖", self.checkbox_cost_all_cards_and_do_lottery)

    def update_config(self, cfg: ArkLotteryConfig):
        cfg.lucky_dnf_server_id = dnf_server_name_to_id(self.combobox_lucky_dnf_server_name.currentText())
        cfg.lucky_dnf_role_id = self.lineedit_lucky_dnf_role_id.text()

        cfg.need_take_awards = self.checkbox_need_take_awards.isChecked()

        cfg.act_id_to_cost_all_cards_and_do_lottery[self.get_ark_lottery_act_id()] = (
            self.checkbox_cost_all_cards_and_do_lottery.isChecked()
        )

    def get_ark_lottery_act_id(self) -> int:
        if is_new_version_ark_lottery():
            return Urls().pesudo_ark_lottery_act_id
        else:
            return zzconfig().actid


class VipMentorConfigUi(QWidget):
    def __init__(
        self,
        form_layout: QFormLayout,
        cfg: VipMentorConfig,
        account_cfg: AccountConfig,
        common_cfg: CommonConfig,
        parent=None,
    ):
        super().__init__(parent)

        self.account_cfg = account_cfg
        self.common_cfg = common_cfg

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: VipMentorConfig):
        self.spinbox_take_index = create_spin_box(cfg.take_index, 3, 1)
        add_row(form_layout, "兑换数目", self.spinbox_take_index)

        self.combobox_guanhuai_dnf_server_name = create_combobox(
            dnf_server_id_to_name(cfg.guanhuai_dnf_server_id), dnf_server_name_list()
        )
        add_row(form_layout, "关怀礼包角色区服名称", self.combobox_guanhuai_dnf_server_name)

        self.lineedit_guanhuai_dnf_role_id = create_lineedit(
            cfg.guanhuai_dnf_role_id,
            "角色ID（不是角色名称！！！），形如 1282822，可以点击下面的选项框来选择角色（需登录）",
        )
        self.lineedit_guanhuai_dnf_role_id.setValidator(DNFRoleIdValidator())
        add_row(form_layout, "关怀礼包角色角色ID", self.lineedit_guanhuai_dnf_role_id)

        self.role_selector = RoleSelector(
            "会员关怀",
            self.combobox_guanhuai_dnf_server_name,
            self.lineedit_guanhuai_dnf_role_id,
            self.account_cfg,
            self.common_cfg,
        )
        add_row(form_layout, "查询角色（需要登录）", self.role_selector.combobox_role_name)

    def update_config(self, cfg: VipMentorConfig):
        cfg.take_index = self.spinbox_take_index.value()

        cfg.guanhuai_dnf_server_id = dnf_server_name_to_id(self.combobox_guanhuai_dnf_server_name.currentText())
        cfg.guanhuai_dnf_role_id = self.lineedit_guanhuai_dnf_role_id.text()


class BindRoleConfigUi(QWidget):
    def __init__(
        self,
        form_layout: QFormLayout,
        cfg: BindRoleConfig,
        account_cfg: AccountConfig,
        common_cfg: CommonConfig,
        parent=None,
    ):
        super().__init__(parent)

        self.account_cfg = account_cfg
        self.common_cfg = common_cfg

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: BindRoleConfig):
        self.combobox_dnf_server_name = create_combobox(
            dnf_server_id_to_name(cfg.dnf_server_id), dnf_server_name_list()
        )
        add_row(form_layout, "领奖角色区服名称", self.combobox_dnf_server_name)

        self.lineedit_dnf_role_id = create_lineedit(
            cfg.dnf_role_id,
            "角色ID（不是角色名称！！！），形如 1282822，可以点击下面的选项框来选择角色（需登录，若卡住请先运行一遍本体来完成登录流程再操作）",
        )
        self.lineedit_dnf_role_id.setValidator(DNFRoleIdValidator())
        add_row(form_layout, "领奖角色角色ID", self.lineedit_dnf_role_id)

        self.role_selector = RoleSelector(
            "领奖角色",
            self.combobox_dnf_server_name,
            self.lineedit_dnf_role_id,
            self.account_cfg,
            self.common_cfg,
        )
        add_row(form_layout, "查询角色（需要登录）", self.role_selector.combobox_role_name)

    def update_config(self, cfg: BindRoleConfig):
        cfg.dnf_server_id = dnf_server_name_to_id(self.combobox_dnf_server_name.currentText())
        cfg.dnf_role_id = self.lineedit_dnf_role_id.text()


class RoleSelector(QWidget):
    combobox_role_name_placeholder = (
        "点我查询当前服务器的角色列表，可能会卡一会（一直卡的话，建议先运行一遍本体，完成登录后再进行这个操作）"
    )

    def __init__(
        self,
        ctx,
        combobox_server_name: MyComboBox,
        lineedit_role_id: QLineEdit,
        account_cfg: AccountConfig,
        common_cfg: CommonConfig,
        parent=None,
    ):
        super().__init__(parent)

        self.ctx = ctx
        self.combobox_server_name = combobox_server_name
        self.lineedit_role_id = lineedit_role_id
        self.account_cfg = account_cfg
        self.common_cfg = common_cfg

        self.server_id_to_roles: dict[str, list[DnfRoleInfo]] = {}

        self.combobox_role_name = create_combobox(
            self.combobox_role_name_placeholder, [self.combobox_role_name_placeholder]
        )
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
            djcHelper.check_skey_expired()

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

    def get_roles(self) -> list[DnfRoleInfo]:
        server_id = self.get_server_id()
        if server_id not in self.server_id_to_roles:
            return []

        return self.server_id_to_roles[server_id]


class DnfHelperInfoConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: DnfHelperInfoConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: DnfHelperInfoConfig):
        self.checkbox_chronicle_lottery = create_checkbox(cfg.chronicle_lottery)
        add_row(form_layout, "编年史开启抽奖", self.checkbox_chronicle_lottery)

        self.checkbox_disable_fetch_access_token = create_checkbox(cfg.disable_fetch_access_token)
        add_row(
            form_layout,
            (
                "不尝试获取编年史新鉴权参数\n"
                "（勾选后以下等功能将无法完成）\n"
                "   1. 签到奖励\n"
                "   2. 领取等级奖励\n"
                "   3. 兑换奖励"
            ),
            self.checkbox_disable_fetch_access_token,
        )

        self.lineedit_url = create_lineedit(
            "", "填入助手生日活动链接，即可自动解析下面四个参数。获取方式请点击右侧按钮"
        )
        self.lineedit_url.textEdited.connect(self.on_url_changed)

        btn_show_token_doc = create_pushbutton("查看文档", "cyan")
        btn_show_token_doc.clicked.connect(self.show_token_doc)

        layout = QHBoxLayout()
        layout.addWidget(self.lineedit_url)
        layout.addWidget(btn_show_token_doc)
        add_row(form_layout, "助手生日活动链接", layout)

        self.lineedit_userId = create_lineedit(cfg.userId, "dnf助手->我的->编辑->社区ID")
        add_row(form_layout, "社区ID(userId)", self.lineedit_userId)

        self.lineedit_nickName = create_lineedit(cfg.nickName, "dnf助手->我的->编辑->昵称")
        add_row(form_layout, "昵称(nickname)", self.lineedit_nickName)

        self.lineedit_token = create_lineedit(
            cfg.token,
            "形如 sSfsEtDH，抓包或分享链接可得（ps：不知道咋操作，可查看【使用教程/使用文档.docx/获取助手token】",
        )
        add_row(form_layout, "登陆票据(token)", self.lineedit_token)

        self.lineedit_uniqueRoleId = create_lineedit(
            cfg.uniqueRoleId,
            "形如 3482436497，抓包或分享链接可得（ps：不知道咋操作，可查看【使用教程/使用文档.docx/获取助手token】",
        )
        add_row(form_layout, "唯一角色ID(uniqueRoleId)", self.lineedit_uniqueRoleId)

        add_row(form_layout, "", QHLine())

        self.lineedit_pNickName = create_lineedit(
            cfg.pNickName, "你的固定搭档的备注，无实际作用，方便记住固定搭档到底是谁<_<"
        )
        add_row(form_layout, "固定搭档的名称(仅本地区分用)", self.lineedit_pNickName)

        self.lineedit_pUserId = create_lineedit(
            cfg.pUserId, "如果你有固定搭档，可以把他的社区ID填到这里，这样每期编年史将会自动绑定"
        )
        add_row(form_layout, "固定搭档的社区ID", self.lineedit_pUserId)

        add_row(form_layout, "", QHLine())

        self.checkbox_enable_auto_match_dnf_chronicle = create_checkbox(cfg.enable_auto_match_dnf_chronicle)
        add_row(
            form_layout, "是否自动匹配编年史搭档（优先级高于固定搭档）", self.checkbox_enable_auto_match_dnf_chronicle
        )

        add_row(form_layout, "需要满足这些条件", QLabel("1. 在付费生效期间\n" "2. 上个月达到了30级\n"))

        add_row(form_layout, "", QHLine())

        add_row(form_layout, "++++ token和唯一角色id是用于自动领取编年史等级奖励 ++++", QHLine())
        add_row(form_layout, "++++ 以及部分助手自己专属的活动的 ++++", QHLine())
        add_row(form_layout, "++++ 如果真抓不来，可以手动做这部分 ++++", QHLine())

        self.try_set_default_exchange_items_for_cfg(cfg)
        if len(cfg.chronicle_exchange_items) != 0:
            add_row(form_layout, "---- 要兑换的道具 (等级/碎片/次数/名称) ----", QHLine())
            add_row(form_layout, "优先换前面的已配置兑换次数的奖励", QHLine())
            add_row(form_layout, "如果前面的等级未到或者碎片不够，不会尝试兑换排在后面的", QHLine())
        self.exchange_items = {}
        for exchange_item in cfg.chronicle_exchange_items:
            self.exchange_items[exchange_item.sLbcode] = DnfHelperChronicleExchangeItemConfigUi(
                form_layout, exchange_item
            )

    def update_config(self, cfg: DnfHelperInfoConfig):
        cfg.userId = self.lineedit_userId.text()
        cfg.nickName = self.lineedit_nickName.text()
        cfg.token = self.lineedit_token.text()
        cfg.uniqueRoleId = self.lineedit_uniqueRoleId.text()
        cfg.pNickName = self.lineedit_pNickName.text()
        cfg.pUserId = self.lineedit_pUserId.text()
        cfg.enable_auto_match_dnf_chronicle = self.checkbox_enable_auto_match_dnf_chronicle.isChecked()

        cfg.chronicle_lottery = self.checkbox_chronicle_lottery.isChecked()
        cfg.disable_fetch_access_token = self.checkbox_disable_fetch_access_token.isChecked()

        self.try_set_default_exchange_items_for_cfg(cfg)
        for sLbcode, exchange_item in self.exchange_items.items():
            item_cfg = cfg.get_exchange_item_by_sLbcode(sLbcode)
            if item_cfg is None:
                continue

            exchange_item.update_config(item_cfg)

        # 排下序，已设置了兑换次数的放到前面
        cfg.move_exchange_item_to_front()

    def try_set_default_exchange_items_for_cfg(self, cfg: DnfHelperInfoConfig):
        sLBcode_to_item: dict[str, DnfHelperChronicleExchangeItemConfig] = {}
        for item in cfg.chronicle_exchange_items:
            sLBcode_to_item[item.sLbcode] = item

        # 特殊处理下编年史兑换，若相应配置不存在，则加上默认不领取的配置，确保界面显示出来
        db = DnfHelperChronicleExchangeListDB().load()
        for gift in db.exchange_list.gifts:
            if gift.sLbcode in sLBcode_to_item:
                # 同步下除count外的其他信息
                sLBcode_to_item[gift.sLbcode].sync_everything_except_code_and_count(gift)
                continue

            # 未配置该道具，添加默认的空值，确保显示出来
            item = DnfHelperChronicleExchangeItemConfig()
            item.sLbcode = gift.sLbcode
            item.count = 0
            item.sync_everything_except_code_and_count(gift)
            cfg.chronicle_exchange_items.append(item)

        # 排下序，已设置了兑换次数的放到前面
        cfg.move_exchange_item_to_front()

    def on_url_changed(self, new_url: str):
        userId = parse_url_param(new_url, "userId").strip()
        nickname = parse_url_param(new_url, "nickname").strip()
        token = parse_url_param(new_url, "token").strip()
        uniqueRoleId = parse_url_param(new_url, "uniqueRoleId").strip()

        self.lineedit_userId.setText(userId)
        self.lineedit_nickName.setText(nickname)
        self.lineedit_token.setText(token)
        self.lineedit_uniqueRoleId.setText(uniqueRoleId)

    def show_token_doc(self):
        webbrowser.open("https://docs.qq.com/doc/DYmN0UldUbmxITkFj")
        report_click_event("token_doc")


class DnfHelperChronicleExchangeItemConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: DnfHelperChronicleExchangeItemConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: DnfHelperChronicleExchangeItemConfig):
        self.spinbox_count = create_spin_box(cfg.count, 99)
        add_row(form_layout, f"{cfg.iLevel:2} {cfg.iCard:3} {cfg.iNum:2} {cfg.sName}", self.spinbox_count)

    def update_config(self, cfg: DnfHelperChronicleExchangeItemConfig):
        cfg.count = self.spinbox_count.value()


class ComicConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: ComicConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: ComicConfig):
        self.checkbox_enable_lottery = create_checkbox(cfg.enable_lottery)
        add_row(form_layout, "是否自动抽奖（建议领完需要的奖励后开启该开关）", self.checkbox_enable_lottery)

        self.try_set_default_exchange_items_for_cfg(cfg)
        if len(cfg.exchange_items) != 0:
            add_row(form_layout, "---- 要兑换的道具 ----", QHLine())
            add_row(form_layout, "优先换前面的已配置兑换次数的奖励", QHLine())
            add_row(form_layout, "如果前面的星星不够，不会尝试兑换排在后面的", QHLine())
        self.exchange_items = {}
        for exchange_item in cfg.exchange_items:
            self.exchange_items[exchange_item.index] = ComicExchangeItemConfigUi(form_layout, exchange_item)

    def update_config(self, cfg: ComicConfig):
        cfg.enable_lottery = self.checkbox_enable_lottery.isChecked()

        self.try_set_default_exchange_items_for_cfg(cfg)
        for index, exchange_item in self.exchange_items.items():
            item_cfg = cfg.get_exchange_item_by_index(index)
            if item_cfg is None:
                continue

            exchange_item.update_config(item_cfg)

        # 排下序，已设置了兑换次数的放到前面
        cfg.move_exchange_item_to_front()

    def try_set_default_exchange_items_for_cfg(self, cfg: ComicConfig):
        # 特殊处理下，若相应配置不存在，则加上默认不领取的配置，确保界面显示出来，方便用户进行配置
        default_items: list[tuple[int, str, int]] = [
            (1, "黑钻15天", 20),
            (2, "黑钻7天", 10),
            (3, "黑钻3天", 6),
            (4, "灿烂的徽章神秘礼盒", 6),
            (5, "升级券(Lv50~109)", 5),
            (6, "抗疲劳药（10点）", 4),
            (7, "华丽的徽章神秘礼盒", 4),
            (8, "凯丽的强化器", 2),
            (9, "顶级灵药组合包", 2),
            (10, "宠物饲料礼袋(20个)", 2),
            (11, "抗疲劳秘药(5点)", 2),
            (12, "镶嵌栏开启装置", 1),
            (13, "神秘契约礼包(1天)", 1),
        ]

        # 记录下已有的配置的信息，方便去重
        all_item_keys = set()
        for item in cfg.exchange_items:
            all_item_keys.add(item.index)

        # 将不存在的部分添加到配置后面
        for index, name, need_star in default_items:
            item = ComicExchangeItemConfig()
            item.index = index
            item.name = name
            item.need_star = need_star
            item.count = 0

            if index in all_item_keys:
                # 如果配置文件中的对应条目的名字与这里不一样，则改为这里的，这样偶尔填错了名字，也可以在后续通过代码内修正为正确的名字
                item_cfg_from_config_file = cfg.get_exchange_item_by_index(index)
                if item_cfg_from_config_file is not None and item_cfg_from_config_file.name != item.name:
                    item_cfg_from_config_file.name = item.name

                continue
            all_item_keys.add(index)

            cfg.exchange_items.append(item)

        # 排下序，已设置了兑换次数的放到前面
        cfg.move_exchange_item_to_front()


class ComicExchangeItemConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: ComicExchangeItemConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: ComicExchangeItemConfig):
        self.spinbox_count = create_spin_box(cfg.count, 99)
        add_row(form_layout, f"{cfg.name} - 星星*{cfg.need_star}", self.spinbox_count)

    def update_config(self, cfg: ComicExchangeItemConfig):
        cfg.count = self.spinbox_count.value()


class HelloVoiceInfoConfigUi(QWidget):
    def __init__(self, form_layout: QFormLayout, cfg: HelloVoiceInfoConfig, parent=None):
        super().__init__(parent)

        self.from_config(form_layout, cfg)

    def from_config(self, form_layout: QFormLayout, cfg: HelloVoiceInfoConfig):
        self.lineedit_hello_id = create_lineedit(
            cfg.hello_id, "hello语音（皮皮蟹）->我的->头像右侧，昵称下方的【ID：XXXXXX】中的XXX那部分"
        )
        add_row(form_layout, "hello语音（皮皮蟹）的用户ID", self.lineedit_hello_id)

    def update_config(self, cfg: HelloVoiceInfoConfig):
        cfg.hello_id = self.lineedit_hello_id.text()


def format_qq_list_for_message_box(qq_list: list[str]) -> str:
    return "\n" + "\n".join(f"\t{qq}" for qq in qq_list)


def format_qq_for_message_box(qq: str) -> str:
    return "\n" + f"\t{qq}"


def report_click_event(event: str):
    increase_counter(ga_category="click_in_config_ui", name=event)


def show_notices():
    if is_first_run("新增微信支付"):
        show_message(
            "新增微信支付",
            (
                "这几天新接入了银联微信通道，配置工具的购买界面可以使用微信支付了，各位习惯使用微信支付的朋友下次购买的时候可以试试看~"
            ),
            disabled_seconds=5,
        )

    pass


def main():
    import config as config_module

    config_module.g_exit_on_check_error = False

    increase_counter(name="config_ui", ga_type=GA_REPORT_TYPE_PAGE_VIEW)

    def catch_exceptions(t, val, tb):
        result = StringIO()
        print_tb(tb, file=result)
        msg = f"{t} {val}:\n{result.getvalue()}"
        logger.error(msg)
        QMessageBox.critical(None, f"出错了 - v{now_version} {ver_time}", msg)
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

    # 视情况调整付费界面
    ui.adjust_pay_window()

    show_notices()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
