from main_def import *


def test_try_notify_new_pay_info():
    qq_accounts = ["123", "456", "789"]

    # 准备初始付费信息
    user_buy_info = BuyInfo()
    user_buy_info.qq = qq_accounts[0]
    user_buy_info.game_qqs = qq_accounts[1:]
    user_buy_info.append_records_and_recompute([
        BuyRecord().auto_update_config({"buy_month": 1, "buy_at": "2021-10-01 12:30:15", "reason": "购买"}),
        BuyRecord().auto_update_config({"buy_month": 2, "buy_at": "2021-10-02 12:30:15", "reason": "购买"}),
        BuyRecord().auto_update_config({"buy_month": 3, "buy_at": "2021-10-03 12:30:15", "reason": "购买"}),
    ])

    # 清空数据
    UserBuyInfoDB().with_context(str(qq_accounts)).reset()

    # 执行第一次查询
    new_buy_dlc, new_buy_monthly_pay_records = try_notify_new_pay_info(qq_accounts, user_buy_info)
    # 在没有数据的情况下不应产生通知
    assert new_buy_dlc is False
    assert len(new_buy_monthly_pay_records) == 0

    # 增加1个月付费和购买dlc，再次执行查询
    delta_normal_months = [
        BuyRecord().auto_update_config({"buy_month": 1, "buy_at": "2021-10-04 12:30:15", "reason": "购买"}),
        BuyRecord().auto_update_config({"buy_month": 2, "buy_at": "2021-10-05 12:30:15", "reason": "购买"}),
    ]
    user_buy_info.append_records_and_recompute([
        *delta_normal_months,
        BuyRecord().auto_update_config({"buy_month": 2, "buy_at": "2021-02-08 00:00:00", "reason": "自动更新DLC赠送(自2.8至今最多累积未付费时长两个月***注意不是从购买日开始计算***)"}),
    ])
    new_buy_dlc, new_buy_monthly_pay_records = try_notify_new_pay_info(qq_accounts, user_buy_info)
    # 确保通知有dlc和新的普通按月付费
    assert new_buy_dlc is True
    assert new_buy_monthly_pay_records == delta_normal_months

    # 不做任何操作，再次执行操作
    new_buy_dlc, new_buy_monthly_pay_records = try_notify_new_pay_info(qq_accounts, user_buy_info)
    # 确保未发生变化
    assert new_buy_dlc is False
    assert len(new_buy_monthly_pay_records) == 0


def test_new_ark_lottery_parse_index_from_card_id():
    assert new_ark_lottery_parse_index_from_card_id("1") == "1-1"
    assert new_ark_lottery_parse_index_from_card_id("4") == "1-4"
    assert new_ark_lottery_parse_index_from_card_id("7") == "2-3"
    assert new_ark_lottery_parse_index_from_card_id("12") == "3-4"
