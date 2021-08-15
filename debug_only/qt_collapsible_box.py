from PyQt5 import QtCore, QtGui, QtWidgets


# copy from https://stackoverflow.com/a/52617714/5251903
class CollapsibleBox(QtWidgets.QWidget):
    def __init__(self, title="", title_backgroup_color="", tool_tip="点击展开/折叠", animation_duration_millseconds=250, parent=None):
        super(CollapsibleBox, self).__init__(parent)

        self.title = title

        self.setToolTip(tool_tip)

        self.animation_duration_millseconds = animation_duration_millseconds

        self.collapsed_height = 19

        self.toggle_button = QtWidgets.QToolButton(self)
        self.toggle_button.setText(title)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.toggle_button.setSizePolicy(sizePolicy)
        
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setStyleSheet(f"QToolButton {{ border: none; font-weight: bold; background-color: {title_backgroup_color}; }}")
        self.toggle_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.toggle_animation = QtCore.QParallelAnimationGroup(self)

        self.content_area = QtWidgets.QScrollArea(self)
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        self.content_area.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        self.content_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self, b"minimumHeight")
        )
        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self, b"maximumHeight")
        )
        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self.content_area, b"maximumHeight")
        )

    def set_fold(self, fold: bool):
        if self.toggle_button.isChecked() != fold:
            # 已经达到预期状态，无需额外操作
            return

        # 折叠状态(fold=True)：checked为False
        # 展开状态(fold=False)：checked为True

        # 状态变化：先处理on_pressed，之后再变更checked为 not fold，因此on_pressed中读取的是之前状态的checked状态
        self.on_pressed()
        self.toggle_button.setChecked(not fold)

    @QtCore.pyqtSlot()
    def on_pressed(self):
        self.try_adjust_size()

        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(
            QtCore.Qt.DownArrow if not checked else QtCore.Qt.RightArrow
        )
        self.toggle_animation.setDirection(
            QtCore.QAbstractAnimation.Forward
            if not checked
            else QtCore.QAbstractAnimation.Backward
        )
        self.toggle_animation.start()

    def setContentLayout(self, layout):
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)

        self.try_adjust_size()

    def try_adjust_size(self):
        collapsed_height = self.get_collapsed_height()
        content_height = self.content_area.layout().sizeHint().height()
        # print("本地调试", self.title, self.sizeHint().height(), self.content_area.maximumHeight(), collapsed_height, content_height)
        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(self.animation_duration_millseconds)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(
            self.toggle_animation.animationCount() - 1
        )
        content_animation.setDuration(self.animation_duration_millseconds)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)

    def get_collapsed_height(self):
        collapsed_height = (
                self.sizeHint().height() - self.content_area.maximumHeight()
        )
        if collapsed_height >= self.collapsed_height:
            # 只允许变大
            self.collapsed_height = collapsed_height

        return self.collapsed_height


def test_CollapsibleBox():
    import random
    import sys

    app = QtWidgets.QApplication(sys.argv)

    w = QtWidgets.QMainWindow()
    w.setCentralWidget(QtWidgets.QWidget())
    dock = QtWidgets.QDockWidget("Collapsible Demo")
    w.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
    scroll = QtWidgets.QScrollArea()
    dock.setWidget(scroll)
    content = QtWidgets.QWidget()
    scroll.setWidget(content)
    scroll.setWidgetResizable(True)
    vlay = QtWidgets.QVBoxLayout(content)
    for i in range(10):
        box = CollapsibleBox("Collapsible Box Header-{}".format(i))
        vlay.addWidget(box)
        lay = QtWidgets.QVBoxLayout()
        for j in range(8):
            label = QtWidgets.QLabel("{}".format(j))
            color = QtGui.QColor(*[random.randint(0, 255) for _ in range(3)])
            label.setStyleSheet(
                "background-color: {}; color : white;".format(color.name())
            )
            label.setAlignment(QtCore.Qt.AlignCenter)
            lay.addWidget(label)

        box.setContentLayout(lay)
    vlay.addStretch()
    w.resize(640, 480)
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test_CollapsibleBox()
