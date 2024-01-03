from __future__ import annotations

import datetime
import math

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QValidator, QWheelEvent
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from log import logger
from qt_collapsible_box import CollapsibleBox
from util import get_now, padLeftRight


class QHLine(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class QVLine(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)


class MySpinbox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class MyDoubleSpinbox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class MyComboBox(QComboBox):
    clicked = pyqtSignal()

    def showPopup(self):
        self.clicked.emit()
        super().showPopup()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


def create_pushbutton(text, color="", tooltip="") -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(f"background-color: {color}; font-weight: bold; font-family: Microsoft YaHei")
    btn.setToolTip(tooltip)

    return btn


def create_checkbox(val=False, name="") -> QCheckBox:
    checkbox = QCheckBox(name)

    checkbox.setChecked(val)

    return checkbox


def create_spin_box(value: int, maximum: int = 99999, minimum: int = 0) -> MySpinbox:
    spinbox = MySpinbox()
    spinbox.setMaximum(maximum)
    spinbox.setMinimum(minimum)

    spinbox.setValue(value)

    return spinbox


def create_double_spin_box(value: float, maximum: float = 1.0, minimum: float = 0.0) -> MyDoubleSpinbox:
    spinbox = MyDoubleSpinbox()
    spinbox.setMaximum(maximum)
    spinbox.setMinimum(minimum)

    spinbox.setValue(value)

    return spinbox


def create_combobox(current_val: str, values: list[str] | None = None) -> MyComboBox:
    combobox = MyComboBox()

    combobox.setFocusPolicy(Qt.StrongFocus)

    if values is not None:
        combobox.addItems(values)
    combobox.setCurrentText(current_val)

    return combobox


def create_lineedit(current_text: str, placeholder_text="") -> QLineEdit:
    lineedit = QLineEdit(current_text)

    lineedit.setPlaceholderText(placeholder_text)

    return lineedit


def add_form_seperator(form_layout: QFormLayout, title: str):
    add_row(form_layout, f"=== {title} ===", QHLine())


def add_vbox_seperator(vbox_layout: QVBoxLayout, title: str):
    hbox = QHBoxLayout()

    hbox.addStretch(1)
    hbox.addWidget(QLabel(title))
    hbox.addStretch(1)

    vbox_layout.addWidget(QHLine())
    vbox_layout.addLayout(hbox)
    vbox_layout.addWidget(QHLine())


def add_row(form_layout: QFormLayout, row_name: str, row_widget: QWidget, minium_row_name_size=0):
    if minium_row_name_size > 0:
        row_name = padLeftRight(row_name, minium_row_name_size, mode="left")
    form_layout.addRow(row_name, row_widget)


def make_scroll_layout(inner_layout: QLayout):
    widget = QWidget()
    widget.setLayout(inner_layout)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)

    scroll_layout = QVBoxLayout()
    scroll_layout.addWidget(scroll)

    return scroll_layout


def create_collapsible_box_with_sub_form_layout_and_add_to_parent_layout(
    title: str, parent_layout: QLayout, fold: bool = True, title_backgroup_color=""
) -> tuple[CollapsibleBox, QFormLayout]:
    collapsible_box = CollapsibleBox(title, title_backgroup_color=title_backgroup_color)
    parent_layout.addWidget(collapsible_box)

    form_layout = QFormLayout()
    collapsible_box.setContentLayout(form_layout)

    collapsible_box.set_fold(fold)

    return collapsible_box, form_layout


def create_collapsible_box_add_to_parent_layout(
    title: str, parent_layout: QLayout, title_backgroup_color=""
) -> CollapsibleBox:
    collapsible_box = CollapsibleBox(title, title_backgroup_color=title_backgroup_color)
    parent_layout.addWidget(collapsible_box)

    return collapsible_box


def init_collapsible_box_size(parent_widget: QWidget):
    # 尝试更新各个折叠区域的大小
    for attr_name in dir(parent_widget):
        if not attr_name.startswith("collapsible_box_"):
            continue

        collapsible_box: CollapsibleBox = getattr(parent_widget, attr_name)
        collapsible_box.try_adjust_size()


def list_to_str(vlist: list[str]):
    return ",".join(str(v) for v in vlist)


def str_to_list(str_list: str):
    str_list = str_list.strip(" ,")
    if str_list == "":
        return []

    return [s.strip() for s in str_list.split(",")]


class QQListValidator(QValidator):
    def validate(self, text: str, pos: int) -> tuple[QValidator.State, str, int]:
        sl = str_to_list(text)

        for qq in sl:
            if not qq.isnumeric():
                return (QValidator.Invalid, text, pos)

        return (QValidator.Acceptable, text, pos)


class QQValidator(QValidator):
    def validate(self, text: str, pos: int) -> tuple[QValidator.State, str, int]:
        qq = text
        if qq != "" and not qq.isnumeric():
            return (QValidator.Invalid, text, pos)

        return (QValidator.Acceptable, text, pos)


class DNFRoleIdValidator(QValidator):
    def validate(self, text: str, pos: int) -> tuple[QValidator.State, str, int]:
        role_id = text
        if role_id != "" and not role_id.isnumeric():
            return (QValidator.Invalid, text, pos)

        return (QValidator.Acceptable, text, pos)


def show_message(title: str, text: str, disabled_seconds=0, is_text_selectable=False, show_log=True):
    if show_log:
        logger.info(f"{title} {text}")

    message_box = ConfirmMessageBox()
    message_box.setWindowTitle(title)
    message_box.setText(text)

    if is_text_selectable:
        message_box.setTextInteractionFlags(Qt.TextSelectableByMouse)

    message_box.setStandardButtons(QMessageBox.Ok)
    if disabled_seconds > 0:
        message_box.set_disabled_duration(disabled_seconds, [0])

    message_box.exec_()


# based on https://gitee.com/i_melon/DNFCalculating/blob/master/PublicReference/view/NotificationButton.py
class ConfirmMessageBox(QMessageBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_disabled_duration(self, seconds: float, btn_indexes: list[int]):
        self.end_time = get_now() + datetime.timedelta(seconds=seconds)
        self.btn_indexes = btn_indexes

        self.old_names = {}
        for btn_idx in self.btn_indexes:
            btn = self.buttons()[btn_idx]

            self.old_names[btn_idx] = btn.text()
            btn.setEnabled(False)

        self.time = QTimer(self)
        self.time.setInterval(100)
        self.time.timeout.connect(self.Refresh)
        self.time.start()

        self.Refresh()

    def Refresh(self):
        if get_now() < self.end_time:
            remaining_time = self.end_time - get_now()
            for btn_idx in self.btn_indexes:
                self.buttons()[btn_idx].setText(
                    self.old_names[btn_idx] + f"（{math.ceil(remaining_time.total_seconds())} 秒后可以点击）"
                )
        else:
            self.time.stop()

            for btn_idx in self.btn_indexes:
                btn = self.buttons()[btn_idx]

                btn.setText(self.old_names[btn_idx])
                btn.setEnabled(True)


def show_confirm_message_box(
    title: str,
    message: str,
    confirm_duration: int = 3,
) -> int:
    message_box = ConfirmMessageBox()
    message_box.setWindowTitle(title)
    message_box.setText(message)
    message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    message_box.set_disabled_duration(confirm_duration, [0])

    return message_box.exec_()


class MyPushButtonGridLayout(QGridLayout):
    def __init__(self, color="Cyan"):
        super().__init__()

        self.color = color
        self.buttons: list[QPushButton] = []

    def add_button(self, btn: QPushButton, row: int, col: int):
        btn.setStyleSheet(f"QPushButton::checked {{ background-color: {self.color}; }}")

        btn.setCheckable(True)
        if len(self.buttons) == 0:
            # 默认选中第一个选项
            btn.setChecked(True)

        self.addWidget(btn, row, col)

        def clicked():
            self.on_click(btn)

        btn.clicked.connect(clicked)

        self.buttons.append(btn)

    def on_click(self, clicked_btn: QPushButton):
        for btn in self.buttons:
            btn.setChecked(False)

        clicked_btn.setChecked(True)

    def get_active_radio_text(self) -> str:
        for btn in self.buttons:
            if btn.isChecked():
                return btn.text()

        return ""


def create_push_button_grid_layout(items: list[str], color="Cyan", width=3) -> MyPushButtonGridLayout:
    grid_layout = MyPushButtonGridLayout(color)

    for idx, item in enumerate(items):
        row = math.floor(idx / width)
        col = idx % width

        btn = create_pushbutton(item)
        grid_layout.add_button(btn, row, col)

    return grid_layout
