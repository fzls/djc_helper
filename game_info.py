from __future__ import annotations

import json
import os

from const import vscode_online_url
from dao import GameInfo
from log import logger
from util import async_message_box, message_box, pause_and_exit

_loaded = False
name_2_game_info_map: dict[str, GameInfo] = {}
code_2_game_info_map: dict[str, GameInfo] = {}
name_2_mobile_game_info_map: dict[str, GameInfo] = {}


def lazy_load():
    global _loaded
    if _loaded:
        return

    global name_2_game_info_map, code_2_game_info_map, name_2_mobile_game_info_map
    try:
        with open("utils/reference_data/djc_biz_list.json", encoding="utf-8") as f:
            raw_data = json.load(f)
            for game_data in raw_data["data"]:
                gameInfo = GameInfo(game_data)
                name_2_game_info_map[game_data["bizName"]] = gameInfo
                code_2_game_info_map[game_data["bizCode"]] = gameInfo

                if gameInfo.is_mobile_game():
                    name_2_mobile_game_info_map[game_data["bizName"]] = gameInfo

            _loaded = True
    except FileNotFoundError as e:
        logger.error(
            (
                f"当前工作目录为 {os.getcwd()}\n"
                "未找到djc配置文件，是否是下述两种情况之一\n"
                "   1. 直接在压缩包中运行exe\n"
                "   2. 未在解压缩出的目录中运行exe\n"
                "   3. 使用任务计划程序自动运行时未配置工作目录（也就是配置任务时的【起始于(可选)】配置项。需要确保设置为exe所在目录\n"
                "\n"
                "请按照上述提示调整后重试\n"
            ),
            exc_info=e,
        )
        pause_and_exit(-1)


def get_game_info(name):
    lazy_load()
    if name not in name_2_game_info_map:
        message_box(
            f"未找到游戏【{name}】相关的配置，可能是空格等不完全匹配，请在稍后打开的文件中查找对应游戏的实际名字",
            "游戏名不正确",
        )
        async_message_box(
            "请使用网页版vscode或者下载个本地版的vscode打开【utils/reference_data/djc_biz_list.json】文件来自行修改~",
            "提示",
            open_url=vscode_online_url,
        )
        pause_and_exit(-1)

    return name_2_game_info_map[name]


def get_game_info_by_bizcode(bizcode):
    lazy_load()
    return code_2_game_info_map[bizcode]


def get_name_2_mobile_game_info_map():
    lazy_load()
    return name_2_mobile_game_info_map


if __name__ == "__main__":
    print(get_game_info("剑网3:指尖江湖"))
