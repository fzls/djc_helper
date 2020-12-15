from config import ArkLotteryAwardConfig
from setting_def import *
from settings import ark_lottery


def zzconfig():
    return ArkLotteryZzConfig().auto_update_config(ark_lottery.setting["zzconfig"])


def parse_card_group_info_map(cfg: ArkLotteryZzConfig):
    card_group_info_map = {}

    groups = [
        cfg.cardGroups.group1,
        cfg.cardGroups.group2,
        cfg.cardGroups.group3,
    ]
    for groupIndex, group in enumerate(groups):
        for cardIndex, card in enumerate(group.cardList):
            card.index = "{}-{}".format(groupIndex + 1, cardIndex + 1)
            card_group_info_map[card.name] = card

    return card_group_info_map


def parse_prize_list(cfg: ArkLotteryZzConfig):
    prize_list = []

    # 首先加入前三个礼包，eg：全民竞速礼包=28592，即刷即得礼包=28593，直播福利礼包=28594
    groups = [
        cfg.prizeGroups.group1,
        cfg.prizeGroups.group2,
        cfg.prizeGroups.group3,
    ]
    for group in groups:
        prize_list.append(ArkLotteryAwardConfig().update(group.title, group.rule))

    # 然后加入幸运礼包，eg：幸运礼包=[依次执行 28610、28609、28583、28611、28612]
    prize_list.append(ArkLotteryAwardConfig().update("幸运礼包-至尊礼包中间资格1", cfg.rules.midRule1))
    prize_list.append(ArkLotteryAwardConfig().update("幸运礼包-至尊礼包中间资格2", cfg.rules.midRule2))
    prize_list.append(ArkLotteryAwardConfig().update("幸运礼包-至尊礼包限制", cfg.prizeGroups.group4.rule))
    prize_list.append(ArkLotteryAwardConfig().update("幸运礼包-兑换至尊失败回滚后6张卡", cfg.rules.midBack2))
    prize_list.append(ArkLotteryAwardConfig().update("幸运礼包-兑换至尊失败回滚前6张卡", cfg.rules.midBack1))

    return prize_list


if __name__ == '__main__':
    cfg = zzconfig()
    print("卡片信息如下")
    for name, card in parse_card_group_info_map(cfg).items():
        print(name, card)

    print()
    print("奖励信息如下")
    for prize in parse_prize_list(cfg):
        print(prize)
