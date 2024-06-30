from __future__ import annotations

from config import ArkLotteryAwardConfig
from setting_def import ArkLotteryZzConfig, DnfAreaServerListConfig, DnfServerConfig
from settings import ark_lottery, dnf_server_list


def zzconfig():
    return ArkLotteryZzConfig().auto_update_config(ark_lottery.setting["zzconfig"])  # type: ignore


def parse_card_group_info_map(cfg: ArkLotteryZzConfig):
    card_group_info_map = {}

    groups = [
        cfg.cardGroups.group1,
        cfg.cardGroups.group2,
        cfg.cardGroups.group3,
    ]
    for groupIndex, group in enumerate(groups):
        for cardIndex, card in enumerate(group.cardList):
            card.index = f"{groupIndex + 1}-{cardIndex + 1}"
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


def dnf_area_server_list_config() -> list[DnfAreaServerListConfig]:
    area_servers: list[DnfAreaServerListConfig] = []
    for area_server_setting in dnf_server_list.setting:
        area_servers.append(DnfAreaServerListConfig().auto_update_config(area_server_setting))

    return area_servers


def dnf_server_list_config():
    area_servers = dnf_area_server_list_config()

    servers: list[DnfServerConfig] = []
    for area_server in area_servers:
        servers.extend(area_server.opt_data_array)

    return servers


def dnf_server_name_list():
    return ["", *[server.t for server in dnf_server_list_config()]]


def dnf_server_name_to_id(name):
    for server in dnf_server_list_config():
        if server.t == name:
            return server.v

    return ""


def dnf_server_id_to_name(id):
    for server in dnf_server_list_config():
        if server.v == str(id):
            return server.t

    return ""


def dnf_server_id_to_area_info(id: str) -> DnfAreaServerListConfig:
    for area in dnf_area_server_list_config():
        for server in area.opt_data_array:
            if server.v == id:
                return area

    return DnfAreaServerListConfig()


if __name__ == "__main__":
    cfg = zzconfig()
    print("卡片信息如下")
    for name, card in parse_card_group_info_map(cfg).items():
        print(card.index, name, card)

    print()
    print("奖励信息如下")
    for prize in parse_prize_list(cfg):
        print(prize)

    print(dnf_server_name_list())
    print(dnf_server_id_to_name(11))
    print(dnf_server_name_to_id("浙江一区"))
