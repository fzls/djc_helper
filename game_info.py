import json
import os
import subprocess
from sys import exit

import win32api
import win32con

from dao import GameInfo
from log import logger

name_2_game_info_map = {}
code_2_game_info_map = {}

try:
    with open("reference_data/djc_biz_list.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        for game_data in raw_data["data"]:
            gameInfo = GameInfo(game_data)
            name_2_game_info_map[game_data["bizName"]] = GameInfo(game_data)
            code_2_game_info_map[game_data["bizCode"]] = GameInfo(game_data)
except FileNotFoundError as e:
    logger.error((
        "未找到djc配置文件，是否是下述两种情况之一\n"
        "   1. 直接在压缩包中运行exe\n"
        "   2. 未在解压缩出的目录中运行exe\n"
        "   3. 使用任务计划程序自动运行时未配置工作目录（也就是配置任务时的【起始于(可选)】配置项。需要确保设置为exe所在目录\n"
        "\n"
        "请按照上述提示调整后重试\n"
    ), exc_info=e)
    os.system("PAUSE")
    exit(-1)


def get_game_info(name):
    if name not in name_2_game_info_map:
        win32api.MessageBox(0, "未找到游戏【{}】相关的配置，可能是空格等不完全匹配，请在稍后打开的文件中查找对应游戏的实际名字".format(name), "游戏名不正确", win32con.MB_ICONWARNING)
        subprocess.call(["npp_portable/notepad++.exe", "reference_data/djc_biz_list.json"])
        exit(-1)

    return name_2_game_info_map[name]


def get_game_info_by_bizcode(bizcode):
    return code_2_game_info_map[bizcode]


if __name__ == '__main__':
    print(get_game_info("剑网3:指尖江湖"))
