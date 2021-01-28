from config import load_config, config
from djc_helper import DjcHelper
from log import color
from util import show_head_line

if __name__ == '__main__':
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    # 12.30 送卡片次数（re:好像送给别人没有上限？）
    indexes = [6]

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]
        show_head_line(f"开始处理第{idx}个账户[{account_config.name}]", color("fg_bold_yellow"))

        djcHelper = DjcHelper(account_config, cfg.common)
        lr = djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        # re: 先填QQ undone: 然后填写卡片
        targetQQ = "XXXXXXXXXXX"
        cards_to_send = [
            ("XXXXXXXXXXX", 1),
            ("XXXXXXXXXXX", 1),
            ("XXXXXXXXXXX", 1),
            ("XXXXXXXXXXX", 1),
        ]
        for name, count in cards_to_send:
            if name == "XXXXXXXXXXX":
                continue
            for i in range(count):
                djcHelper.send_card_by_name(name, targetQQ)

# -----------具体卡片相关信息---------------
# 1-1 深渊七彩闪不停 {'name': '深渊七彩闪不停', 'id': 119186, 'prizeId': 45800, 'lotterySwitchId': 29598, 'index': '1-1'}
# 1-2 增幅强化次次成 {'name': '增幅强化次次成', 'id': 119185, 'prizeId': 45799, 'lotterySwitchId': 29597, 'index': '1-2'}
# 1-3 缺啥爆啥秒毕业 {'name': '缺啥爆啥秒毕业', 'id': 119184, 'prizeId': 45798, 'lotterySwitchId': 29596, 'index': '1-3'}
# 1-4 变身主C战使徒 {'name': '变身主C战使徒', 'id': 119183, 'prizeId': 45797, 'lotterySwitchId': 29595, 'index': '1-4'}

# 2-1 组队征战希洛克 {'name': '组队征战希洛克', 'id': 119182, 'prizeId': 45796, 'lotterySwitchId': 29594, 'index': '2-1'}
# 2-2 频频金牌闪亮眼 {'name': '频频金牌闪亮眼', 'id': 119181, 'prizeId': 45795, 'lotterySwitchId': 29593, 'index': '2-2'}
# 2-3 提升摸金两不误 {'name': '提升摸金两不误', 'id': 119180, 'prizeId': 45794, 'lotterySwitchId': 29592, 'index': '2-3'}
# 2-4 日进斗金成土豪 {'name': '日进斗金成土豪', 'id': 119179, 'prizeId': 45793, 'lotterySwitchId': 29591, 'index': '2-4'}

# 3-1 集卡抽奖送豪礼 {'name': '集卡抽奖送豪礼', 'id': 119178, 'prizeId': 45792, 'lotterySwitchId': 29590, 'index': '3-1'}
# 3-2 灿烂黑钻拿不停 {'name': '灿烂黑钻拿不停', 'id': 119177, 'prizeId': 45791, 'lotterySwitchId': 29589, 'index': '3-2'}
# 3-3 追忆白金黄金书 {'name': '追忆白金黄金书', 'id': 119176, 'prizeId': 45790, 'lotterySwitchId': 29588, 'index': '3-3'}
# 3-4 超强奖励等你拿 {'name': '超强奖励等你拿', 'id': 119175, 'prizeId': 45789, 'lotterySwitchId': 29587, 'index': '3-4'}
