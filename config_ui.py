from log import logger, fileHandler, new_file_handler
from version import now_version

logger.name = "config_ui"
logger.removeHandler(fileHandler)
logger.addHandler(new_file_handler())

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QFormLayout, QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox,
                             QWidget, QTabWidget, QComboBox, QStyleFactory, QSpinBox, QFrame, QMessageBox, QPushButton, QInputDialog)

from config import *


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class QVLine(QFrame):
    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)


def list_to_str(vlist: List[str]):
    return ','.join(str(v) for v in vlist)


def str_to_list(str_list: str):
    if str_list.strip() == "":
        return []

    return [s.strip() for s in str_list.split(',')]


def show_message(title, text):
    logger.info(f"{title} {text}")

    message_box = QMessageBox()
    message_box.setWindowTitle(title)
    message_box.setText(text)
    message_box.exec_()


class ConfigUi(QFrame):
    def __init__(self, parent=None):
        super(ConfigUi, self).__init__(parent)

        self.resize(1080, 720)
        self.setWindowTitle("简易配置工具（如需要更细化配置，请使用文本编辑器编辑config.toml）（保存后config.toml将丢失注释信息，可去config.toml.example查看注释）")

        self.setWhatsThis("简易配置工具")

        self.load()

        logger.info(f"配置工具启动成功，版本号为v{now_version}")

    def load(self):
        self.from_config(self.load_config())

        logger.info("已读取成功，请按需调整配置，调整完记得点下保存~")

    def notify_reopen(self):
        show_message("请重新打开", "目前因为不知道如何清除pyqt的已有组件然后再添加新的组件，暂时没有实现重新读取配置的功能，请直接右上角关掉重新打开-。-")

    def save(self):
        self.save_config(self.to_config())
        show_message("保存成功", "已保存成功，请自行运行小助手本体")

    def load_config(self) -> Config:
        load_config(local_config_path="")
        return config()

    def save_config(self, cfg: Config):
        save_config(cfg)

    def from_config(self, cfg: Config):
        # 根据配置初始化ui
        top_layout = QVBoxLayout()

        self.create_buttons(top_layout)
        self.create_tabs(cfg, top_layout)

        self.setLayout(top_layout)

    def create_buttons(self, top_layout: QVBoxLayout):
        btn_load = QPushButton("读取配置")
        btn_save = QPushButton("保存配置")

        btn_load.clicked.connect(self.notify_reopen)
        btn_save.clicked.connect(self.save)

        layout = QHBoxLayout()
        layout.addWidget(btn_load)
        layout.addWidget(btn_save)
        top_layout.addLayout(layout)
        top_layout.addWidget(QHLine())

        btn_add_account = QPushButton("添加账号")
        btn_del_account = QPushButton("删除账号")

        btn_add_account.clicked.connect(self.add_account)
        btn_del_account.clicked.connect(self.del_account)

        layout = QHBoxLayout()
        layout.addWidget(btn_add_account)
        layout.addWidget(btn_del_account)
        top_layout.addLayout(layout)
        top_layout.addWidget(QHLine())

    def add_account(self):
        account_name, ok = QInputDialog.getText(self, "添加账号", "要添加的账号名称", QLineEdit.Normal, "")
        if ok:
            logger.info(f"尝试添加账号 {account_name} ...")

            for account in self.accounts:
                if account.lineedit_name.text() == account_name:
                    show_message("添加失败", f"已存在名称为 {account_name} 的账号，请重新操作~")
                    return

            account_config = AccountConfig()
            account_config.name = account_name
            account_ui = AccountConfigUi(account_config)
            self.accounts.append(account_ui)
            self.tabs.addTab(account_ui, account_name)

            show_message("添加成功", "请继续进行其他操作~ 全部操作完成后记得保存~")

    def del_account(self):
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

    def create_tabs(self, cfg: Config, top_layout: QVBoxLayout):
        self.tabs = QTabWidget()
        self.create_common_tab(cfg)
        self.create_account_tabs(cfg)
        top_layout.addWidget(self.tabs)

    def create_common_tab(self, cfg: Config):
        self.common = CommonConfigUi(cfg.common)
        self.tabs.addTab(self.common, "公共配置")

    def create_account_tabs(self, cfg: Config):
        self.accounts = []  # type: List[AccountConfigUi]
        for account in cfg.account_configs:
            account_ui = AccountConfigUi(account)
            self.accounts.append(account_ui)
            self.tabs.addTab(account_ui, account.name)

    def to_config(self) -> Config:
        cfg = self.load_config()

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


class CommonConfigUi(QWidget):
    def __init__(self, cfg: CommonConfig, parent=None):
        super(CommonConfigUi, self).__init__(parent)

        self.from_config(cfg)

    def from_config(self, cfg: CommonConfig):
        top_layout = QVBoxLayout()

        # 开关区域
        switches_h_layout = QHBoxLayout()

        self.checkbox_test_mode = QCheckBox("测试模式")
        self.checkbox_test_mode.setChecked(cfg.test_mode)
        switches_h_layout.addWidget(self.checkbox_test_mode)

        self.checkbox_enable_safe_mode_accounts = QCheckBox("启用安全模式账号")
        self.checkbox_enable_safe_mode_accounts.setChecked(cfg.enable_in_safe_mode_accounts)
        switches_h_layout.addWidget(self.checkbox_enable_safe_mode_accounts)

        top_layout.addLayout(switches_h_layout)

        # key val 表格区域
        form_layout = QFormLayout()

        self.spinbox_http_timeout = QSpinBox()
        self.spinbox_http_timeout.setValue(cfg.http_timeout)
        form_layout.addRow("HTTP超时（秒）", self.spinbox_http_timeout)

        self.combobox_log_level = QComboBox()
        self.combobox_log_level.addItems(["debug", "info", "warning", "error", "critical"])
        self.combobox_log_level.setCurrentText(cfg.log_level)
        form_layout.addRow("日志级别", self.combobox_log_level)

        self.lineedit_majieluo_send_card_target_qq = QLineEdit(cfg.majieluo_send_card_target_qq)
        self.lineedit_majieluo_send_card_target_qq.setPlaceholderText("填写qq号")
        form_layout.addRow("马杰洛新春版本赠送卡片目标QQ", self.lineedit_majieluo_send_card_target_qq)

        self.lineedit_auto_send_card_target_qqs = QLineEdit(list_to_str(cfg.auto_send_card_target_qqs))
        self.lineedit_auto_send_card_target_qqs.setPlaceholderText("填写qq号列表，使用英文逗号分开，示例：123, 456, 789")
        form_layout.addRow("自动赠送卡片的目标QQ数组", self.lineedit_auto_send_card_target_qqs)

        top_layout.addLayout(form_layout)

        self.setLayout(top_layout)

    def update_config(self, cfg: CommonConfig):
        cfg.test_mode = self.checkbox_test_mode.isChecked()
        cfg.enable_in_safe_mode_accounts = self.checkbox_enable_safe_mode_accounts.isChecked()

        cfg.http_timeout = self.spinbox_http_timeout.value()
        cfg.log_level = self.combobox_log_level.currentText()
        cfg.majieluo_send_card_target_qq = self.lineedit_majieluo_send_card_target_qq.text()
        cfg.auto_send_card_target_qqs = str_to_list(self.lineedit_auto_send_card_target_qqs.text())


class AccountConfigUi(QWidget):
    def __init__(self, cfg: AccountConfig, parent=None):
        super(AccountConfigUi, self).__init__(parent)

        self.from_config(cfg)

    def from_config(self, cfg: AccountConfig):
        top_layout = QVBoxLayout()

        # 开关区域
        switches_h_layout = QHBoxLayout()

        self.checkbox_enable = QCheckBox("启用该账号")
        self.checkbox_enable.setChecked(cfg.enable)
        switches_h_layout.addWidget(self.checkbox_enable)

        top_layout.addLayout(switches_h_layout)

        # key val 表格区域
        form_layout = QFormLayout()

        self.lineedit_name = QLineEdit(cfg.name)
        form_layout.addRow("账号名称", self.lineedit_name)

        self.combobox_login_mode = QComboBox()
        self.combobox_login_mode.addItems([
            "by_hand",
            "qr_login",
            "auto_login",
        ])
        self.combobox_login_mode.setCurrentText(cfg.login_mode)
        form_layout.addRow("登录模式", self.combobox_login_mode)

        top_layout.addLayout(form_layout)

        self.setLayout(top_layout)

    def update_config(self, cfg: AccountConfig):
        cfg.enable = self.checkbox_enable.isChecked()
        cfg.name = self.lineedit_name.text()

        cfg.login_mode = self.combobox_login_mode.currentText()


def main():
    app = QApplication([])

    QApplication.setStyle(QStyleFactory.create("fusion"))

    ui = ConfigUi()
    ui.show()

    app.exec()


if __name__ == '__main__':
    main()
