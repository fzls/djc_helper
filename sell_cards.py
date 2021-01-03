from config import load_config, config
from djc_helper import DjcHelper
from log import color
from util import show_head_line

if __name__ == '__main__':
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    # 12.30 送卡片次数（re:好像送给别人没有上限？）
    indexes = [4]

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]
        show_head_line("开始处理第{}个账户[{}]".format(idx, account_config.name), color("fg_bold_yellow"))

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        lr = djcHelper.fetch_pskey()

        # re: 先填QQ
        # undone: 然后填写卡片
        targetQQ = "XXXXXXXXXXX"
        cards_to_send = [
            ("XXXXXXXXXXX", 1),
            ("XXXXXXXXXXX", 1),
            ("XXXXXXXXXXX", 1),
            ("XXXXXXXXXXX", 1),
        ]
        for name, count in cards_to_send:
            for i in range(count):
                djcHelper.send_card_by_name(name, targetQQ)

# -----------具体卡片相关信息---------------
# '1-1' 巅峰大佬刷竞速 {'name': '巅峰大佬刷竞速', 'id': 118409, 'prizeId': 44460, 'lotterySwitchId': 28608, 'index': '1-1'}
# '1-2' 主播趣味来打团 {'name': '主播趣味来打团', 'id': 118408, 'prizeId': 44459, 'lotterySwitchId': 28607, 'index': '1-2'}
# '1-3' BOSS机制全摸透 {'name': 'BOSS机制全摸透', 'id': 118407, 'prizeId': 44458, 'lotterySwitchId': 28606, 'index': '1-3'}
# '1-4' 萌新翻身把歌唱 {'name': '萌新翻身把歌唱', 'id': 118406, 'prizeId': 44457, 'lotterySwitchId': 28605, 'index': '1-4'}

# '2-1' 四人竞速希洛克 {'name': '四人竞速希洛克', 'id': 118405, 'prizeId': 44456, 'lotterySwitchId': 28604, 'index': '2-1'}
# '2-2' 普通困难任你选 {'name': '普通困难任你选', 'id': 118404, 'prizeId': 44455, 'lotterySwitchId': 28603, 'index': '2-2'}
# '2-3' 哪种都能领奖励 {'name': '哪种都能领奖励', 'id': 118403, 'prizeId': 44454, 'lotterySwitchId': 28602, 'index': '2-3'}
# '2-4' 点击报名薅大礼 {'name': '点击报名薅大礼', 'id': 118402, 'prizeId': 44453, 'lotterySwitchId': 28601, 'index': '2-4'}

# '3-1' 打团就可赢好礼 {'name': '打团就可赢好礼', 'id': 118401, 'prizeId': 44452, 'lotterySwitchId': 28600, 'index': '3-1'}
# '3-2' 报名即可领豪礼 {'name': '报名即可领豪礼', 'id': 118400, 'prizeId': 44451, 'lotterySwitchId': 28599, 'index': '3-2'}
# '3-3' 直播Q币抽不停  {'name': '直播Q币抽不停', 'id': 118399, 'prizeId': 44450, 'lotterySwitchId': 28598, 'index': '3-3'}
# '3-4' 决赛红包等着你 {'name': '决赛红包等着你', 'id': 118398, 'prizeId': 44449, 'lotterySwitchId': 28597, 'index': '3-4'}
