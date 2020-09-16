import json
import subprocess

import win32api
import win32con

from dao import GameInfo

name_2_game_info_map = {}
code_2_game_info_map = {}

with open("reference_data/djc_biz_list.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)
    for game_data in raw_data["data"]:
        gameInfo = GameInfo(game_data)
        name_2_game_info_map[game_data["bizName"]] = GameInfo(game_data)
        code_2_game_info_map[game_data["bizCode"]] = GameInfo(game_data)


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
