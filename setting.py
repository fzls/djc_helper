from setting_def import *
from settings import ark_lottery


def zzconfig():
    return ArkLotteryZzConfig().auto_update_config(ark_lottery.setting["zzconfig"])


if __name__ == '__main__':
    print(zzconfig())
