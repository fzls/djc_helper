import argparse
import json
from typing import Dict, List

from config import config, load_config
from djc_helper import DjcHelper
from log import color, logger
from main_def import make_ark_lottery_card_and_award_info, new_ark_lottery_parse_card_id_from_index
from util import show_head_line

CARD_PLACEHOLDER = "XXXXXXXXXXX"


def sell_card(targetQQ: str, cards_to_send: List[str]) -> str:
    cards_to_send = [name for name in cards_to_send if name != CARD_PLACEHOLDER]

    # 读取配置信息
    cfg = config()

    # 12.30 送卡片次数（re:好像送给别人没有上限？）
    indexes = list(range(len(cfg.account_configs), 0, -1))

    success_send_list = []

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]
        show_head_line(f"开始处理第{idx}个账户[{account_config.name}]", color("fg_bold_yellow"))
        if not account_config.function_switches.get_ark_lottery or not account_config.is_enabled():
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        remaining_cards = []
        for name in cards_to_send:
            send_ok = False

            send_ok = djcHelper.dnf_ark_lottery_send_card(name, targetQQ)

            if send_ok:
                success_send_list.append(name)
            else:
                remaining_cards.append(name)

        cards_to_send = remaining_cards
        if len(cards_to_send) == 0:
            break

    msg = ""
    if len(success_send_list) != 0:
        msg += f"\n成功发送以下卡片：{success_send_list}"
    if len(cards_to_send) != 0:
        msg += f"\n无法发送以下卡片：{cards_to_send}，是否已达到赠送上限或者这个卡卖完了？"
    if len(success_send_list) != 0:
        msg += "\n请使用手机打开集卡页面确认是否到账~ 若到账请按1元每张的价格主动扫码转账哦~（不定期我会核查的，如果买了不付款的话就加入本工具黑名单~）"
    msg += "\n"

    return msg


def query_card_info():
    # 读取配置信息
    cfg = config()

    # init_pool(cfg.get_pool_size())
    # check_all_skey_and_pskey(cfg, check_skey_only=True)

    # 12.30 送卡片次数（re:好像送给别人没有上限？）
    indexes = list(range(len(cfg.account_configs), 0, -1))

    order_map, _ = make_ark_lottery_card_and_award_info()

    heads = []
    colSizes = []

    card_indexes = ["1-1", "1-2", "1-3", "1-4", "2-1", "2-2", "2-3", "2-4", "3-1", "3-2", "3-3", "3-4"]
    card_width = 3
    heads.extend(card_indexes)
    colSizes.extend([card_width for i in card_indexes])

    summaryCols = [*[0 for card in card_indexes]]

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]
        if not account_config.function_switches.get_ark_lottery or not account_config.is_enabled():
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        # 获取卡片和奖励数目，其中新版本卡片为 id=>count ，旧版本卡片为 name=>count
        card_counts: Dict[str, int]

        card_counts = djcHelper.dnf_ark_lottery_get_card_counts()

        # 处理各个卡片数目
        for card_position, card_index in enumerate(card_indexes):
            card_count = card_counts[order_map[card_index]]

            # 更新统计信息
            summaryCols[card_position] += card_count

    msg = "\n卡片详情如下"
    msg += "\n "
    for col in range(4):
        msg += f" {col + 1:3d}"
    for row in range(3):
        msg += f"\n{row + 1}"
        for col in range(4):
            msg += f" {summaryCols[row * 4 + col]:3d}"
    msg += "\n"

    return msg


def run_local():
    # re: 先填QQ undone: 然后填写卡片
    targetQQ = "1054073896"
    cards_to_send: List[str]

    # 新版集卡中名称为 1/2/3/4/.../10/11/12
    cards_to_send = [
        "8",
        CARD_PLACEHOLDER,
        CARD_PLACEHOLDER,
        CARD_PLACEHOLDER,
    ]

    msg = sell_card(targetQQ, cards_to_send)
    logger.info(msg)


def run_remote(args):
    if args.query:
        msg = query_card_info()
    else:
        # 新版集卡中名称为 1/2/3/4/.../10/11/12
        card_name_list = [new_ark_lottery_parse_card_id_from_index(args.card_index)]

        msg = sell_card(args.target_qq, card_name_list)
    print(json.dumps(msg))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_remote", action="store_true")
    parser.add_argument("--query", action="store_true")
    parser.add_argument("--target_qq", default="", type=str, help="qq to send card, eg. 1054073896")
    parser.add_argument("--card_index", default="", type=str, help="card index to send, eg. 2-3")
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    load_config("config.toml", "config.toml.local")

    args = parse_args()
    if args.run_remote:
        run_remote(args)
    else:
        run_local()

# note: 运行 setting.py 可获取最新集卡信息
# -----------具体卡片相关信息---------------
# 1-1 神话闪光新途径 {"name": "神话闪光新途径", "id": 120698, "prizeId": 48173, "lotterySwitchId": 31255, "index": "1-1"}
# 1-2 角色成长新环境 {"name": "角色成长新环境", "id": 120697, "prizeId": 48172, "lotterySwitchId": 31254, "index": "1-2"}
# 1-3 战力挑战新副本 {"name": "战力挑战新副本", "id": 120696, "prizeId": 48171, "lotterySwitchId": 31253, "index": "1-3"}
# 1-4 收益摸金新圣地 {"name": "收益摸金新圣地", "id": 120695, "prizeId": 48170, "lotterySwitchId": 31252, "index": "1-4"}

# 2-1 黑鸦之境大提升 {"name": "黑鸦之境大提升", "id": 120694, "prizeId": 48169, "lotterySwitchId": 31251, "index": "2-1"}
# 2-2 史诗装备可补齐 {"name": "史诗装备可补齐", "id": 120693, "prizeId": 48168, "lotterySwitchId": 31250, "index": "2-2"}
# 2-3 装备词条由你搭 {"name": "装备词条由你搭", "id": 120692, "prizeId": 48167, "lotterySwitchId": 31249, "index": "2-3"}
# 2-4 智慧产物能升级 {"name": "智慧产物能升级", "id": 120691, "prizeId": 48166, "lotterySwitchId": 31248, "index": "2-4"}

# 3-1 守护者三觉·启 {"name": "守护者三觉·启", "id": 120690, "prizeId": 48165, "lotterySwitchId": 31247, "index": "3-1"}
# 3-2 狂拽酷炫美炸天 {"name": "狂拽酷炫美炸天", "id": 120689, "prizeId": 48164, "lotterySwitchId": 31246, "index": "3-2"}
# 3-3 三觉挑战等你接 {"name": "三觉挑战等你接", "id": 120688, "prizeId": 48163, "lotterySwitchId": 31245, "index": "3-3"}
# 3-4 签到好礼不停歇 {"name": "签到好礼不停歇", "id": 120687, "prizeId": 48162, "lotterySwitchId": 31244, "index": "3-4"}
