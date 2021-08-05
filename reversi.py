# 更新器不启用文件日志

import logging

from log import fileHandler, logger, new_file_handler

logger.name = "reversi"
logger.removeHandler(fileHandler)
logger.addHandler(new_file_handler())
logger.setLevel(logging.INFO)

import copy
import random
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Tuple

from PyQt5.Qt import (QApplication, QBrush, QDialog, QDialogButtonBox, QIcon,
                      QImage, QLabel, QMessageBox, QPalette, QSize)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

from log import asciiReset, color
from qt_wrapper import *
from util import range_from_one

board_size = 8

cell_blue = -1
cell_empty = 0
cell_red = 1
cell_invalid = 2

invalid_cell_count = 5

winner_counter = Counter()

weight_map = [
    [500, -25, 10, 5, 5, 10, -25, 500],
    [-25, -45, 1, 1, 1, 1, -45, -25],
    [10, 1, 3, 2, 2, 3, 1, 10],
    [5, 1, 2, 1, 1, 2, 1, 5],
    [5, 1, 2, 1, 1, 2, 1, 5],
    [10, 1, 3, 2, 2, 3, 1, 10],
    [-25, -45, 1, 1, 1, 1, -45, -25],
    [500, -25, 10, 5, 5, 10, -25, 500],
]


class AvgStat:
    def __init__(self):
        self.count = 0
        self.total = 0.0

    def add(self, val):
        self.count += 1
        self.total += val

    def avg(self):
        if self.count == 0:
            return 0.0

        return self.total / self.count


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("ai参数设置")

        # 组件
        self.blue_set_ai = create_checkbox(True)
        self.red_set_ai = create_checkbox(False)
        self.ai_dfs_max_depth = create_spin_box(7)
        self.ai_min_decision_seconds = create_double_spin_box(0.5, maximum=99999)
        self.ai_max_decision_time = create_double_spin_box(26, maximum=99999)
        self.enable_presearch = create_checkbox(True)
        self.ai_dfs_presearch_depth = create_spin_box(2)
        self.ai_dfs_max_choice_per_depth = create_spin_box(5)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok, self)

        # 拼接
        layout = QFormLayout(self)
        layout.addRow("蓝方是否启用AI？", self.blue_set_ai)
        layout.addRow("红方是否启用AI？", self.red_set_ai)
        add_form_seperator(layout, "算力强度配置（以下配置基本可以使用默认值）")
        layout.addRow("ai最大搜索层数（越大越强，速度越慢）", self.ai_dfs_max_depth)
        layout.addRow("ai每步最小等待时间（秒）（太小可能会看不清手动方的落子位置-。-）", self.ai_min_decision_seconds)
        layout.addRow("ai每步最大等待时间（秒）（避免超出30秒）", self.ai_max_decision_time)
        layout.addRow("是否启用预搜索（加快搜索速度）", self.enable_presearch)
        layout.addRow("预搜索层数（越大速度越慢，精度越高）", self.ai_dfs_presearch_depth)
        layout.addRow("预搜索后实际最多搜索子节点数（越小速度越快，精度越小）", self.ai_dfs_max_choice_per_depth)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def getInputs(self):
        return (self.first.text(), self.second.value())


class Reversi(QWidget):
    def __init__(self):
        super().__init__()

        self.init_logic()
        self.init_ui()
        self.init_invalid_cells()

    def init_logic(self):
        logger.info(f"初始化逻辑数据")

        self.loop_index = 1
        self.invalid_cell_count = 0

        # 先手为蓝
        self.step_cell = cell_blue

        # ai托管，默认不托管
        self.ai_cells = {}
        self.ai_to_avg_stat = {}  # type: Dict[int, AvgStat]

        self.ai_moving = False

        self.game_start_time = datetime.now()
        self.game_restarted = False

        cd = ConfigDialog()
        cd.exec()

        self.ai_dfs_max_depth = cd.ai_dfs_max_depth.value()
        self.ai_min_decision_seconds = timedelta(seconds=cd.ai_min_decision_seconds.value())
        self.ai_max_decision_time = timedelta(seconds=cd.ai_max_decision_time.value())
        blue_set_ai = cd.blue_set_ai.isChecked()
        red_set_ai = cd.red_set_ai.isChecked()
        self.enable_presearch = cd.enable_presearch.isChecked()
        self.ai_dfs_max_choice_per_depth = cd.ai_dfs_max_choice_per_depth.value()
        self.ai_dfs_presearch_depth = cd.ai_dfs_presearch_depth.value()

        if blue_set_ai:
            self.set_ai(cell_blue, self.ai_min_max)
        if red_set_ai:
            self.set_ai(cell_red, self.ai_min_max)

        logger.info(f"ai最大迭代次数为{self.ai_dfs_max_depth}，每次操作至少{self.ai_min_decision_seconds}，最大等待时间为{self.ai_max_decision_time}")

        self.last_step = (1, 1)

        self.init_board_without_invalid_cells()

    def init_invalid_cells(self):
        # 设置玩家名称
        if cell_blue in self.ai_cells:
            self.label_blue_name.setText("蓝方-AI托管")
        else:
            self.label_blue_name.setText("蓝方")
        if cell_red in self.ai_cells:
            self.label_red_name.setText("大师南瓜球-AI托管")
        else:
            self.label_red_name.setText("大师南瓜球")

        if len(self.ai_cells) < 2:
            # self.init_invalid_cells_randomly()
            self.init_invalid_cells_by_click()
            # self.init_invalid_cells_by_input()
        else:
            self.init_invalid_cells_randomly()

        self.ai_try_put_cell()

    def init_ui(self):
        width = 800
        height = 580

        self.setFixedSize(width, height)

        # 设置棋盘背景
        oBackGroundImage = QImage("reversi_images/board.png")
        sBackGroundImage = oBackGroundImage.scaled(QSize(width, height))  # resize Image to widgets size
        palette = QPalette()
        palette.setBrush(QPalette.Window, QBrush(sBackGroundImage))
        self.setPalette(palette)

        # 初始化棋盘元素
        self.label_count_down = QLabel('', self)
        self.label_count_down.setStyleSheet(f"color: orange; font-size: 30px; font-weight: bold; font-family: Microsoft YaHei")
        self.label_count_down.setGeometry(350, 0, 500, 60)

        self.label_turn = QLabel('蓝方回合', self)
        self.label_turn.setStyleSheet(f"color: blue; font-size: 24px; font-weight: bold; font-family: Microsoft YaHei")
        self.label_turn.setGeometry(320, 60, 500, 40)

        self.label_blue_name = QLabel('蓝方-AI托管', self)
        self.label_blue_name.setStyleSheet(f"color: gray; font-size: 18px; font-weight: bold; font-family: Microsoft YaHei")
        self.label_blue_name.setGeometry(150, 40, 180, 20)

        self.label_blue_score = QLabel('2', self)
        self.label_blue_score.setStyleSheet(f"color: yellow; font-size: 24px; font-weight: bold; font-family: Microsoft YaHei")
        self.label_blue_score.setGeometry(180, 60, 120, 30)

        self.label_red_name = QLabel('大师南瓜球', self)
        self.label_red_name.setStyleSheet(f"color: gray; font-size: 18px; font-weight: bold; font-family: Microsoft YaHei")
        self.label_red_name.setGeometry(520, 40, 180, 20)

        self.label_red_score = QLabel('2', self)
        self.label_red_score.setStyleSheet(f"color: yellow; font-size: 24px; font-weight: bold; font-family: Microsoft YaHei")
        self.label_red_score.setGeometry(570, 60, 120, 30)

        self.btn_manunal_bye = QPushButton('手动轮空', self)
        self.btn_manunal_bye.setStyleSheet(f"color: #cf8160; font-size: 18px; font-weight: bold; font-family: Microsoft YaHei; background-color: #89090a")
        self.btn_manunal_bye.setGeometry(685, 460, 80, 30)
        self.btn_manunal_bye.clicked.connect(self.manunal_bye)

        self.btn_restart = QPushButton('重新开始', self)
        self.btn_restart.setStyleSheet(f"color: #cf8160; font-size: 18px; font-weight: bold; font-family: Microsoft YaHei; background-color: #89090a")
        self.btn_restart.setGeometry(685, 505, 80, 30)
        self.btn_restart.clicked.connect(self.restart)

        # 180 120
        # 445 -> 480 (row 1 -> 8 top )
        mid_top_x, mid_top_y = 400, 120
        self.btn_list_board = []

        self.qicon_blue = QIcon(QPixmap("reversi_images/blue.png"))
        self.qicon_red = QIcon(QPixmap("reversi_images/red.png"))
        self.qicon_empty = QIcon()
        self.qicon_next_step = QIcon(QPixmap("reversi_images/next_step.png"))
        self.qicon_invalid = QIcon(QPixmap("reversi_images/invalid.png"))
        self.qicon_current_blue = QIcon(QPixmap("reversi_images/current_blue.png"))
        self.qicon_current_red = QIcon(QPixmap("reversi_images/current_red.png"))

        for row_index in range_from_one(board_size):
            label_row = []

            row_width = 445 + int((480 - 445) / 7 * (row_index - 1))

            for col_index in range_from_one(board_size):
                cell = self.board[row_index][col_index]
                x, y = mid_top_x - row_width // 2 + row_width // 8 * (col_index - 1), mid_top_y + 47 * (row_index - 1)

                btn = QPushButton(self)
                btn.setIconSize(QSize(60, 50))
                btn.setGeometry(x, y, row_width // 8, 50)

                btn.setStyleSheet("QPushButton { background-color: transparent; border: 0px }")

                def cb(ri, ci):
                    def _cb():
                        logger.debug(f"clicked row={ri}, col={ci}")

                        # 初始化无效格子
                        if self.invalid_cell_count < invalid_cell_count:
                            if self.board[ri][ci] != cell_empty:
                                logger.info("该格子不为空，不能设置为无效格子")
                                return

                            self.board[ri][ci] = cell_invalid
                            self.invalid_cell_count = self.invalid_cell_count + 1
                            logger.info(f"设置第{self.invalid_cell_count}个无效位置")
                            self.paint()

                            if self.invalid_cell_count == invalid_cell_count:
                                # 记录点击次数，到达五个按钮时进入正式游戏模式（尝试ai点击）并隐藏提示按钮
                                self.ai_try_put_cell()
                            return

                        if self.current_step_cell() in self.ai_cells and not self.ai_moving:
                            logger.info("当前回合由机器人托管，将无视该点击")
                            return
                        self.ai_moving = False

                        # 判断是否可行
                        if self.is_game_over():
                            self.game_over()
                            return

                        if not self.has_any_valid_cell():
                            logger.info("本轮无任何可行落子，将轮空")
                            self.next_turn()
                            self.loop_index += 1
                            if not self.has_any_valid_cell():
                                logger.info("双方均不可再落子，游戏结束")
                                self.game_over()
                                return

                        # 记录下当前方
                        current_step_cell = self.current_step_cell()

                        # 落子
                        is_valid = self.put_cell(ri, ci) is not None
                        if is_valid:
                            self.loop_index += 1

                        # 计算落子后当前方局面分
                        current_score = self.evaluate(current_step_cell)
                        if current_score >= 0:
                            cr = "bold_red"
                        else:
                            cr = "bold_green"
                        logger.info(color(cr) + f"落子后当前{self.cell_name_without_color(current_step_cell)}局面分为{current_score}")

                        # 重绘界面
                        self.paint()

                        # 若轮到机器人
                        self.ai_try_put_cell()

                    return _cb

                btn.clicked.connect(cb(row_index, col_index))

                label_row.append(btn)

            self.btn_list_board.append(label_row)

        self.paint()

        self.show()

    def manunal_bye(self):
        logger.info("手动点击轮空，跳过本轮")
        self.label_count_down.setText(self.cell_name(self.step_cell, False) + "主动轮空")
        self.next_turn()
        self.paint()

        self.ai_try_put_cell()

    def restart(self, clicked=True, manual=True):
        logger.info("重新开始游戏")
        self.label_count_down.setText("重新开始")

        self.game_restarted = True
        if manual:
            logger.info("等待一秒，确保AI停止")
            time.sleep(1)

        self.init_logic()
        self.paint()
        self.init_invalid_cells()

    def ai_try_put_cell(self):
        if self.invalid_cell_count < invalid_cell_count:
            logger.info("棋盘无效位置未初始化，ai暂不操作")
            return

        if self.current_step_cell() in self.ai_cells:
            worker = AiThread(self, self)
            worker.signal_move.connect(self.on_ai_move)
            worker.start()

    def on_ai_move(self, row, col):
        logger.info(f"{self.cell_name(self.current_step_cell(), False)}ai执行操作为 {chr(ord('a') + row - 1)}行{col}列")

        # 机器人落子
        self.ai_moving = True
        btn = self.btn_list_board[row - 1][col - 1]
        btn.click()

    def init_board_without_invalid_cells(self):
        # 空棋盘
        self.board = list([list([cell_empty for col in range(board_size + 2)]) for row in range(board_size + 2)])

        # 设置边缘为invalid
        for row_index in range(board_size + 2):
            for col_index in range(board_size + 2):
                if row_index in [0, board_size + 1] or col_index in [0, board_size + 1]:
                    self.board[row_index][col_index] = cell_invalid

        # 设置红蓝初始位置
        self.board[4][4] = cell_blue
        self.board[5][5] = cell_blue
        self.board[4][5] = cell_red
        self.board[5][4] = cell_red

    def init_invalid_cells_randomly(self):
        # 随机选择五个位置不可下棋
        possiable_invalid_cells = list(filter(lambda v: not (
                (v[0] == 4 and v[1] == 4) or
                (v[0] == 5 and v[1] == 5) or
                (v[0] == 4 and v[1] == 5) or
                (v[0] == 5 and v[1] == 4)
        ), [(row, col) for col in range_from_one(board_size) for row in range_from_one(board_size)]))
        for row, col in random.sample(possiable_invalid_cells, k=invalid_cell_count):
            self.board[row][col] = cell_invalid
            self.invalid_cell_count = self.invalid_cell_count + 1

        self.paint()

    def init_invalid_cells_by_input(self):
        prompt = f"输入游戏内显示的五个无效格子位置，用单个空格分开。eg. a1 b1 c1 d1 e1: \n"
        raw_input = input(prompt)
        import re

        re_arguments = r'([a-h][1-8]) ([a-h][1-8]) ([a-h][1-8]) ([a-h][1-8]) ([a-h][1-8])'
        while re.match(re_arguments, raw_input) is None:
            logger.info("格式有误")
            raw_input = input(prompt)

        row_cols = re.match(re_arguments, raw_input).groups()

        for row_col in row_cols:
            row, col = int(ord(row_col[0]) - ord('a') + 1), int(row_col[1])
            self.board[row][col] = cell_invalid
            self.invalid_cell_count = self.invalid_cell_count + 1

        self.paint()

    def init_invalid_cells_by_click(self):
        # 界面提示点击五个按钮
        if invalid_cell_count > 0:
            self.notify(f"请点击{invalid_cell_count}个格子，设置为无效格子")

    def set_ai(self, cell_color, ai_algorithm_fn):
        self.ai_cells[cell_color] = ai_algorithm_fn
        self.ai_to_avg_stat[cell_color] = AvgStat()
        logger.info(self.cell_name(cell_color) + color("bold_green") + f"将被ai托管，算法为{ai_algorithm_fn}")

    def play_with_cgi(self):
        # self.set_ai(cell_red, self.ai_random)
        self.set_ai(cell_blue, self.ai_min_max)

        bye_count = 0

        while not self.is_game_over():
            self.paint()

            logger.info(f"当前回合为 {self.cell_name(self.current_step_cell())}")

            if not self.has_any_valid_cell():
                bye_count += 1
                if bye_count < 2:
                    logger.info("本轮无任何可行落子，将轮空")
                    self.next_turn()
                    continue
                else:
                    logger.info("双方均不可再落子，游戏结束")
                    break

            if self.current_step_cell() not in self.ai_cells:
                # 人类操作
                row_col = input("请输入你的落子（eg. c2表示第三行第二列）：")
                row, col = int(ord(row_col[0]) - ord('a') + 1), int(row_col[1])
            else:
                # ai操作
                row, col = self.next_move_by_ai()

                wait_time = 0.01
                logger.info(f"ai执行操作为 {chr(ord('a') + row - 1)}行{col}列，并等待{wait_time}秒")
                time.sleep(wait_time)
            self.put_cell(row, col)

            bye_count = 0

        self.show_game_result()

    def cell_name_without_color(self, cell_color):
        return self.cell_name(cell_color, False)

    def cell_name(self, cell_color, with_color=True):
        color_fn = self.with_color
        if not with_color:
            color_fn = self.without_color

        if cell_color == cell_blue:
            return color_fn("蓝方", "blue")
        else:
            return color_fn("红方", "red")

    def next_move_by_ai(self) -> Tuple[int, int]:
        algo_fn = self.ai_cells[self.current_step_cell()]

        return algo_fn(self.get_valid_cells(self.current_step_cell()))

    def get_valid_cells(self, current_step_cell) -> List[Tuple[int, int]]:
        valid_cells = []
        for row_index in range_from_one(board_size):
            for col_index in range_from_one(board_size):
                if self.is_valid_cell(row_index, col_index, current_step_cell):
                    valid_cells.append((row_index, col_index))

        return valid_cells

    def ai_random(self, valid_cells: List[Tuple[int, int]]) -> Tuple[int, int]:
        if len(valid_cells) == 0:
            return (0, 0)

        return random.choice(valid_cells)

    def ai_min_max(self, valid_cells: List[Tuple[int, int]]) -> Tuple[int, int]:
        # save
        backup_board = copy.deepcopy(self.board)
        backup_step_cell = self.step_cell

        alpha = -0x7fffffff
        beta = 0x7fffffff

        self.ai_start_time = datetime.now()
        self.last_update_time = datetime.now()

        # # re: 调试用代码
        # self.iter_count = 0
        # self.avg_choice = AvgStat()
        #
        # self.ai_min_decision_seconds = timedelta(seconds=0.01)
        # # 为方便测试，单独设置双方AI的参数
        # if self.step_cell == cell_blue:
        #     self.enable_presearch = True
        #     self.ai_dfs_max_depth = 7
        #     self.ai_dfs_presearch_depth = 2
        #     self.ai_dfs_max_choice_per_depth = 5
        #     # 红方算力：4层搜索，无预搜索
        #     # 层数 预搜索 最大子节点 平均耗时 蓝方局面分
        #     # 6     2       6       1.3     2067
        #     #
        #     # 7     2       5       3.4     2471/1523/1034/2037
        #     #
        #     # 8     2       5       9.5     2223
        # else:
        #     self.enable_presearch = False
        #     self.ai_dfs_max_depth = 4
        #
        # logger.info(
        #     self.cell_name(self.step_cell) + f"ai参数：max_depth={self.ai_dfs_max_depth}, enable_presearch={self.enable_presearch}, max_choice_per_depth={self.ai_dfs_max_choice_per_depth}, presearch_depth={self.ai_dfs_presearch_depth}")

        res = self.ai_min_max_dfs(0, valid_cells, self.step_cell, alpha, beta)

        used_time = datetime.now() - self.ai_start_time
        self.ai_to_avg_stat[self.step_cell].add(used_time.total_seconds())

        # if self.step_cell == cell_blue:
        #     logfunc = logger.warning
        # else:
        #     logfunc = logger.info
        #
        # logfunc(f"count={self.iter_count}, avg_choice={self.avg_choice.avg()}, expected_score={res[1]}")

        # resume
        self.board = backup_board
        self.step_cell = backup_step_cell

        return res[0]

    def ai_min_max_dfs(self, depth, valid_cells: List[Tuple[int, int]], ai_step_cell, alpha, beta, presearch=False) -> Tuple[Optional[Tuple[int, int]], int]:
        # self.iter_count += 1
        # if len(valid_cells) != 0:
        #     self.avg_choice.add(len(valid_cells))

        if datetime.now() - self.last_update_time >= timedelta(seconds=1 / 60):
            since_start = datetime.now() - self.ai_start_time
            remaining_time = (self.ai_max_decision_time - since_start)

            avg_used_time = self.ai_to_avg_stat[ai_step_cell].avg()

            self.label_count_down.setText(f"{remaining_time.total_seconds():.1f}(平均{avg_used_time:.1f})")
            self.last_update_time = datetime.now()

        if depth == self.ai_dfs_max_depth:
            return (None, self.evaluate(ai_step_cell))

        if self.step_cell == ai_step_cell:
            min_max = max
            alpha = -0x7fffffff
            need_reverse_weights = True
        else:
            min_max = min
            beta = 0x7fffffff
            need_reverse_weights = False

        best_next_move = None

        if len(valid_cells) != 0:
            # 子搜索流程（实际搜索和预搜索将共用该逻辑）
            def subsearch(valid_cells, alpha, beta, current_depth, presearch=False, subresult_cb=None):
                best_next_move = None

                for idx, next_move_index in enumerate(valid_cells):
                    next_move_row_index, next_move_col_index = next_move_index

                    revoke_op = self.put_cell(next_move_row_index, next_move_col_index, ai_probe=True)

                    next_depth_best_move = self.ai_min_max_dfs(current_depth + 1, self.get_valid_cells(self.current_step_cell()), ai_step_cell, alpha, beta, presearch)
                    if next_depth_best_move is None:
                        continue

                    next_depth_min_max_score = next_depth_best_move[1]

                    next_move = ((next_move_row_index, next_move_col_index), next_depth_min_max_score)
                    if best_next_move is None:
                        best_next_move = next_move
                    else:
                        best_next_move = min_max(best_next_move, next_move, key=lambda v: v[1])

                    revoke_op()

                    # 更新alpha、beta
                    if self.step_cell == ai_step_cell:
                        if next_depth_min_max_score > alpha:
                            alpha = next_depth_min_max_score
                    else:
                        if next_depth_min_max_score < beta:
                            beta = next_depth_min_max_score

                    # 子节点结果回调
                    if subresult_cb is not None:
                        subresult_cb(idx, next_depth_min_max_score)

                    # 剪枝
                    if alpha >= beta:
                        logger.debug(f"剪枝 alpha={alpha}, beta={beta}")
                        break

                    # 如果运行时间超限，停止处理
                    since_start = datetime.now() - self.ai_start_time
                    if since_start >= self.ai_max_decision_time:
                        logger.info(f"depth={depth}/{self.ai_dfs_max_depth} valid_cells={idx + 1}/{len(valid_cells)} 等待时间已达到{since_start}，将强制停止搜索")
                        break

                    # 如果重开了，停止处理
                    if self.game_restarted:
                        logger.info(f"游戏重开，将强制停止搜索")
                        break

                return best_next_move

            need_presearch = self.enable_presearch and \
                             not presearch and \
                             len(valid_cells) > self.ai_dfs_max_choice_per_depth and \
                             depth + self.ai_dfs_presearch_depth < self.ai_dfs_max_depth

            if need_presearch:
                # 预计算若干层得到各落子的评分，按照该评分排序
                # 预搜索时本层实际不需要剪枝，因为目的是为了计算出各个子节点的排序权重
                presearch_alpha, presearch_beta = -0x7fffffff, 0x7fffffff
                presearch_current_depth = self.ai_dfs_max_depth - self.ai_dfs_presearch_depth
                valid_cells_weights = [0 for cell in valid_cells]

                def subresult_cb(child_idx, next_depth_min_max_score):
                    valid_cells_weights[child_idx] = next_depth_min_max_score

                subsearch(valid_cells, presearch_alpha, presearch_beta, presearch_current_depth, presearch=True, subresult_cb=subresult_cb)

                # 根据计算出的权重进行排序
                valid_cells = [cell for weight, cell in sorted(zip(valid_cells_weights, valid_cells), reverse=need_reverse_weights)]
                # 取前几个
                valid_cells = valid_cells[:self.ai_dfs_max_choice_per_depth]
            else:
                # 以下情况则直接按照权重排序
                # 1. 如果可选落子数不多
                # 2. 已经接近叶节点
                # 3. 预搜索流程
                valid_cells = sorted(valid_cells, key=lambda v: weight_map[v[0] - 1][v[1] - 1], reverse=need_reverse_weights)

            # 正式开始搜索
            best_next_move = subsearch(valid_cells, alpha, beta, depth)
        else:
            # 本方无可行下子，跳过本轮
            old_step_cell = self.step_cell

            self.next_turn()
            next_depth_best_move = self.ai_min_max_dfs(depth + 1, self.get_valid_cells(self.current_step_cell()), ai_step_cell, alpha, beta)
            if next_depth_best_move is not None:
                next_depth_min_max_score = next_depth_best_move[1]

                next_move = ((0, 0), next_depth_min_max_score)
                best_next_move = next_move

            self.step_cell = old_step_cell

        return best_next_move

    def evaluate(self, current_step_cell, ignore_game_over=False) -> int:
        if self.is_game_over() and not ignore_game_over:
            # 如果已经能判定胜负，则取极大的权重分
            blue, red, winner = self.get_current_winner_info()
            return current_step_cell * winner * 0x7FFFFFFF

        # ai方与另一方的行动力之差（越大越好）
        moves_delta = self.move_delta(current_step_cell)

        # ai方与另一方的当前棋盘落子权重之差，越大越好
        weights = self.weight_sum(current_step_cell)

        # ai方与另一方的 稳定子（角、边、八方均无空格（均被占用）） 之差
        stable_score = self.stable_score(current_step_cell)

        # re: 看看其他的策略里有没有比较好实现的
        #  https://zhuanlan.zhihu.com/p/35121997

        return weights + 15 * moves_delta + 10 * stable_score

    def move_delta(self, current_step_cell) -> int:
        other_step_cell = self.other_step_cell(current_step_cell)
        return len(self.get_valid_cells(current_step_cell)) - len(self.get_valid_cells(other_step_cell))

    def weight_sum(self, current_step_cell) -> int:
        weights = 0

        for row_index in range_from_one(board_size):
            for col_index in range_from_one(board_size):
                if self.board[row_index][col_index] not in [cell_blue, cell_red]:
                    continue

                weights += weight_map[row_index - 1][col_index - 1] * self.board[row_index][col_index]

        return current_step_cell * weights

    def stable_score(self, current_step_cell) -> int:
        # 一些辅助函数
        def add(cell_position, direction):
            return tuple(v + delta for v, delta in zip(cell_position, direction))

        def reverse(direction):
            return tuple(-delta for delta in direction)

        def continuously_nonempty_cell_count(first_cell_position, direction, max_count) -> int:
            not_empty = 0
            current_position = first_cell_position
            for i in range(7):
                cell = get_cell(current_position)
                if cell == cell_empty:
                    break

                not_empty += 1

                current_position = add(current_position, direction)

            return not_empty

        def get_cell(cell_position) -> int:
            row, col = cell_position
            return self.board[row][col]

        # 返回各自所属的 左上到右下的对角线（1-15），左下到右上的对角线（1-15）
        def get_diagonal(row, col) -> Tuple[int, int]:
            upper_diagonal = col - row + 8
            lower_diagonal = col + row - 1

            return (upper_diagonal, lower_diagonal)

        # 角、边、其他（八个方向都无空位） 之差
        # note: 与参考文献不同，自己和对方取差值，而不是相加，因为对方越多稳定子，对自己不利
        corner, edge, other = 0, 0, 0

        # 计算角
        corner_cell_positions = [
            (1, 1), (1, 8),
            (8, 1), (8, 8),
        ]
        for row, col in corner_cell_positions:
            cell = self.board[row][col]
            if cell in [cell_blue, cell_red]:
                corner += current_step_cell * cell

        # 计算边
        edge_cell_positions = [
            ((0, 1), [(1, col) for col in range(2, 7 + 1)]),  # 上
            ((0, 1), [(8, col) for col in range(2, 7 + 1)]),  # 下
            ((1, 0), [(row, 1) for row in range(2, 7 + 1)]),  # 左
            ((1, 0), [(row, 8) for row in range(2, 7 + 1)]),  # 右
        ]

        for direction, cell_positions in edge_cell_positions:
            # 计算两个边界格子
            lower = add(cell_positions[0], reverse(direction))
            upper = add(cell_positions[-1], direction)

            # 计算lower->upper方向格子连续非空的数目
            lu = continuously_nonempty_cell_count(lower, direction, 7)

            # 计算upper->lower方向格子连续非空的数目
            ul = continuously_nonempty_cell_count(upper, reverse(direction), 7)

            # 计算本边上与边界间连续无空格的位置数目
            for idx, _position in enumerate(cell_positions):
                cell = self.board[_position[0]][_position[1]]
                if cell not in [cell_blue, cell_red]:
                    continue

                index = 2 + idx
                if (index <= lu and get_cell(lower) != cell_empty) or \
                        (index >= board_size - ul + 1 and get_cell(upper) != cell_empty):
                    edge += current_step_cell * cell

        # 计算其他位置（八个方向都无空位）

        # 预计算
        # 非空行
        not_empty_rows = set(row for row in range_from_one(8))
        # 非空列
        not_empty_cols = set(col for col in range_from_one(8))
        # 非空的左上到右下方向的对角线
        not_empty_upper_diagonal = set(dia for dia in range_from_one(15))
        # 非空的左下到右上方向的对角线
        not_empty_lower_diagonal = set(dia for dia in range_from_one(15))

        for row in range_from_one(board_size):
            for col in range_from_one(board_size):
                cell = self.board[row][col]
                if cell != cell_empty:
                    continue

                # 标记所在行列和两个对角线为非空
                upper_diagonal, lower_diagonal = get_diagonal(row, col)

                not_empty_rows.discard(row)
                not_empty_cols.discard(col)
                not_empty_upper_diagonal.discard(upper_diagonal)
                not_empty_lower_diagonal.discard(lower_diagonal)

        # 实际计算出非边角位置的八方向都无空格的格子
        for row in range(2, 7 + 1):
            for col in range(2, 7 + 1):
                cell = self.board[row][col]
                if cell not in [cell_blue, cell_red]:
                    continue

                upper_diagonal, lower_diagonal = get_diagonal(row, col)

                if row in not_empty_rows and \
                        col in not_empty_cols and \
                        upper_diagonal in not_empty_upper_diagonal and \
                        lower_diagonal in not_empty_lower_diagonal:
                    other += cell * current_step_cell

        return corner + edge + other

    def put_cell(self, row_index, col_index, ai_probe=False) -> Optional[Callable]:
        valid_directions = self.valid_directions(row_index, col_index, self.current_step_cell())

        old_step_cell = self.step_cell

        if len(valid_directions) == 0:
            if not ai_probe:
                logger.info(color("bold_yellow") + f"无效的下子(row={row_index}, col={col_index}, color={self.cell_name(self.step_cell)})，请重新操作" + asciiReset)
                return None

            # 换手
            self.next_turn()

            def revoke_op():
                self.step_cell = old_step_cell

            return revoke_op

        # 落子
        self.board[row_index][col_index] = self.current_step_cell()
        self.last_step = (row_index, col_index)

        if not ai_probe and self.current_step_cell() not in self.ai_cells:
            logger.info(f"第{self.loop_index}轮人类执行操作为 {chr(ord('a') + row_index - 1)}行{col_index}列")

        # 执行翻转
        undo_indexes = []
        undo_cell = self.next_step_cell()
        for delta_x, delta_y in valid_directions:
            next_row_index, next_col_index = row_index + delta_y, col_index + delta_x
            while self.board[next_row_index][next_col_index] == self.next_step_cell():
                self.board[next_row_index][next_col_index] = self.current_step_cell()
                undo_indexes.append((next_row_index, next_col_index))

                next_row_index, next_col_index = next_row_index + delta_y, next_col_index + delta_x

        # 换手
        self.next_turn()

        def revoke_op():
            self.step_cell = old_step_cell
            self.board[row_index][col_index] = cell_empty
            for ri, ci in undo_indexes:
                self.board[ri][ci] = undo_cell

        return revoke_op

    def next_turn(self):
        self.step_cell = self.next_step_cell()

    def is_valid_cell(self, row_index, col_index, current_step_cell) -> bool:
        return len(self.valid_directions(row_index, col_index, current_step_cell)) != 0

    def has_any_valid_cell(self) -> bool:
        return self.has_any_valid_cell_for(self.current_step_cell())

    def has_any_valid_cell_for(self, cell_color) -> bool:
        for row_index in range_from_one(board_size):
            for col_index in range_from_one(board_size):
                if self.is_valid_cell(row_index, col_index, cell_color):
                    return True

        return False

    def valid_directions(self, row_index, col_index, current_step_cell) -> List[Tuple[int, int]]:
        if self.board[row_index][col_index] != cell_empty:
            return []

        next_step_cell = self.other_step_cell(current_step_cell)

        directions = [
            (1, 0), (-1, 0),
            (0, 1), (0, -1),
            (1, 1), (1, -1),
            (-1, 1), (-1, -1),
        ]

        valid_directions = []
        for direction in directions:
            delta_x, delta_y = direction

            next_row_index, next_col_index = row_index + delta_y, col_index + delta_x
            # 沿该方向下一格必须要是另一方的棋子
            if self.board[next_row_index][next_col_index] != next_step_cell:
                continue

            # 继续往后滑动直到找到第一个不是另一方的格子
            while self.board[next_row_index][next_col_index] == next_step_cell:
                next_row_index, next_col_index = next_row_index + delta_y, next_col_index + delta_x

            # 若最终该格子是当前方棋子，则符合要求
            if self.board[next_row_index][next_col_index] == current_step_cell:
                valid_directions.append(direction)

        return valid_directions

    def is_game_over(self) -> bool:
        if not self.has_any_valid_cell_for(self.step_cell) and \
                not self.has_any_valid_cell_for(self.other_step_cell(self.step_cell)):
            # 游戏已经结束
            return True

        for row_index in range_from_one(board_size):
            for col_index in range_from_one(board_size):
                cell = self.board[row_index][col_index]
                if cell == cell_empty:
                    return False

        return True

    def game_over(self):
        self.paint(game_overd=True)
        self.show_game_result()
        self.notify('游戏结束')

        restart = QMessageBox.question(self, "游戏结束", "是否重新开始？") == QMessageBox.Yes
        if restart:
            self.restart(manual=False)

    def show_game_result(self):
        blue_evaluted_score = self.evaluate(cell_blue, ignore_game_over=True)
        red_evaluted_score = -blue_evaluted_score
        self.label_blue_score.setText(f"{self.score(cell_blue)}({blue_evaluted_score})")
        self.label_red_score.setText(f"{self.score(cell_red)}({red_evaluted_score})")

        blue, red, winner = self.get_current_winner_info()

        winner_name = self.cell_name(winner)
        winner_evaluated_score = self.evaluate(winner, ignore_game_over=True)
        winner_avg = self.ai_to_avg_stat.get(winner, AvgStat()).avg()

        winner_counter[winner] += 1

        avg_blue = self.ai_to_avg_stat.get(cell_blue, AvgStat()).avg()
        avg_red = self.ai_to_avg_stat.get(cell_red, AvgStat()).avg()

        logger.info(f"{self.cell_name(cell_blue)}={blue}, 胜利次数为{winner_counter[cell_blue]}，平均落子时间为{avg_blue:.1f}")
        logger.info(f"{self.cell_name(cell_red)}={red}, 胜利次数为{winner_counter[cell_red]}，平均落子时间为{avg_red:.1f}")
        logger.info(color("bold_yellow") + f"游戏已经结束，胜方为{winner_name}，局面分为{winner_evaluated_score}，胜方平均落子时间为{winner_avg:.1f}，共耗时：{datetime.now() - self.game_start_time}")

    def get_current_winner_info(self) -> Tuple[int, int, int]:
        # 数子
        counter = Counter()

        for row_index in range_from_one(board_size):
            for col_index in range_from_one(board_size):
                cell = self.board[row_index][col_index]

                counter[cell] += 1

        blue, red = counter[cell_blue], counter[cell_red]
        if blue > red:
            winner = cell_blue
        else:
            winner = cell_red

        return (blue, red, winner)

    def paint(self, show_cui_detail=False, game_overd=False):
        logger.info('-' * 20)
        blue_score = self.with_color(f"蓝方：{self.score(cell_blue)}", "blue")
        red_score = self.with_color(f"红方：{self.score(cell_red)}", "red")
        logger.info(f"{blue_score}\t{red_score}")

        if show_cui_detail:
            logger.info(' '.join(['  ', *[str(col_idx + 1) for col_idx in range(board_size)]]))
            for row_index in range_from_one(board_size):

                state = [f'{chr(ord("a") + row_index - 1)} ']

                for col_index in range_from_one(board_size):
                    cell = self.board[row_index][col_index]
                    if cell in [cell_blue, cell_red]:
                        if cell == cell_blue:
                            val, show_color = 'B', 'blue'
                        else:
                            val, show_color = 'R', 'red'

                        if row_index == self.last_step[0] and col_index == self.last_step[1]:
                            show_color = "bold_purple"

                        state.append(self.with_color(val, show_color))
                    elif cell == cell_empty:
                        if self.is_valid_cell(row_index, col_index, self.current_step_cell()):
                            current_color = 'blue'
                            if self.current_step_cell() == cell_red:
                                current_color = 'red'
                            state.append(self.with_color('*', current_color))
                        else:
                            state.append(' ')
                    elif cell == cell_invalid:
                        state.append(self.with_color('X', 'bold_white'))

                state.append('')
                logger.info('|'.join(state))

            if not self.has_any_valid_cell():
                logger.info("本轮无任何可行落子，将轮空")

        # gui
        # 绘制格子
        for row_index in range_from_one(board_size):
            for col_index in range_from_one(board_size):
                cell = self.board[row_index][col_index]
                btn = self.btn_list_board[row_index - 1][col_index - 1]

                ico = None
                if cell in [cell_blue, cell_red]:
                    if row_index == self.last_step[0] and col_index == self.last_step[1]:
                        if cell == cell_blue:
                            ico = self.qicon_current_blue
                        else:
                            ico = self.qicon_current_red
                    else:
                        if cell == cell_blue:
                            ico = self.qicon_blue
                        else:
                            ico = self.qicon_red
                elif cell == cell_empty:
                    if self.is_valid_cell(row_index, col_index, self.current_step_cell()):
                        ico = self.qicon_next_step
                    else:
                        ico = self.qicon_empty
                else:
                    # cell_invalid
                    ico = self.qicon_invalid

                btn.setIcon(ico)

        # 绘制其他界面元素
        if self.invalid_cell_count < invalid_cell_count:
            self.label_turn.setText(f"请继续点击{invalid_cell_count - self.invalid_cell_count}个格子，设置为无效格子")
            self.label_turn.setStyleSheet(f"color: cyan; font-size: 24px; font-weight: bold; font-family: Microsoft YaHei")
        else:
            turn_name = ""
            if self.current_step_cell() == cell_blue:
                turn_name = "蓝方回合"
                self.label_turn.setStyleSheet(f"color: blue; font-size: 24px; font-weight: bold; font-family: Microsoft YaHei")
            else:
                turn_name = "红方回合"
                self.label_turn.setStyleSheet(f"color: red; font-size: 24px; font-weight: bold; font-family: Microsoft YaHei")

            if self.current_step_cell() in self.ai_cells:
                turn_name += "-AI托管"

            self.label_turn.setText(f"{self.loop_index}-{turn_name}")

            if not self.has_any_valid_cell():
                logger.info("本轮无任何可行落子，将轮空")
                if len(self.ai_cells) < 2:
                    self.notify(self.cell_name(self.current_step_cell(), with_color=False) + '轮空，请点击任意位置结束本轮')

        blue_evaluted_score = self.evaluate(cell_blue, ignore_game_over=game_overd)
        red_evaluted_score = -blue_evaluted_score
        self.label_blue_score.setText(f"{self.score(cell_blue)}({blue_evaluted_score})")
        self.label_red_score.setText(f"{self.score(cell_red)}({red_evaluted_score})")

        self.update()

    def score(self, cell_color) -> int:
        score = 0

        for row_index in range_from_one(board_size):
            for col_index in range_from_one(board_size):
                cell = self.board[row_index][col_index]
                if cell == cell_color:
                    score += 1

        return score

    def with_color(self, value, color_name):
        return color(color_name) + str(value) + asciiReset

    def without_color(self, value, color_name):
        return str(value)

    def current_step_cell(self):
        return self.step_cell

    def next_step_cell(self):
        return self.other_step_cell(self.step_cell)

    def other_step_cell(self, step_cell):
        return -step_cell

    def notify(self, msg):
        self.label_turn.setText(msg)
        QMessageBox.information(self, "提示", msg)


class AiThread(QThread):
    signal_move = pyqtSignal(int, int)

    def __init__(self, parent, reversi: Reversi):
        super(AiThread, self).__init__(parent)

        self.reversi = reversi
        self.time_start = datetime.now()

    def __del__(self):
        self.exiting = True

    def run(self) -> None:
        row, col = self.reversi.next_move_by_ai()

        ut = datetime.now() - self.time_start
        cell_name = self.reversi.cell_name_without_color(self.reversi.step_cell)
        avg = self.reversi.ai_to_avg_stat[self.reversi.step_cell].avg()
        logger.info(f"第{self.reversi.loop_index}轮决策 {cell_name} 共耗时{ut.total_seconds():.1f}秒，平均耗时为{avg:.1f}秒")

        min_decision_seconds = self.reversi.ai_min_decision_seconds
        if ut < min_decision_seconds:
            wt = (min_decision_seconds - ut).total_seconds()
            logger.debug(f"耗时低于{min_decision_seconds}，等待至{min_decision_seconds}再落子")
            time.sleep(wt)

        self.signal_move.emit(row, col)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    re = Reversi()
    # re.play()
    sys.exit(app.exec_())
