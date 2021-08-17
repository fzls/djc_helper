from djc_helper import *


def cui():
    # 读取配置信息
    load_config("config.toml", "config.toml.local")
    cfg = config()

    from main_def import check_proxy

    check_proxy(cfg)

    # note: 以下内容修改为自己的配置
    # 大号的账号序号（从1开始）
    dahao_indexes = [1]
    # 三个小号的序号
    xiaohao_indexes = [6, 7, 8]
    # 三个小号的QQ号
    xiaohao_qq_list = ["3036079506", "1470237902", "1276170371"]

    # re: 流程：
    #   1. send_to_xiaohao设为True，大号发送宝箱链接给三个小号
    #   2. 电脑上，大号QQ里点开三个小号对话的宝箱链接，替换Scode到scode_list里面
    #   3. send_to_xiaohao设为False，让小号开启各个宝箱

    # --------------- 每次只需要按流程修改下面几行 ---------------------

    send_to_xiaohao = True
    # send_to_xiaohao = False

    scode_list = [
        "MDJKQ0t5dDJYazlMVmMrc2ZXV0tVT0xsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=",
        "UFgxa1lQZ3RBZERCMTU0N3dSWmcwZUxsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=",
        "cXNpZTIrY2dRYk1GL2E4UjlGQzBkdUxsZitZMi9YOXZUUFgxMW1PcnQ2Yz0=",
    ]

    if len(xiaohao_qq_list) != scode_list:
        message_box("配置的小号数目与scode数目不一致，请确保两者一致", "出错了")
        sys.exit()

    # --------------- 每次只需要按流程修改上面几行 ---------------------

    # 登录相应账号
    if send_to_xiaohao:
        indexes = dahao_indexes
    else:
        indexes = xiaohao_indexes

    for idx in indexes:  # 从1开始，第i个
        account_config = cfg.account_configs[idx - 1]

        show_head_line(f"预先获取第{idx}个账户[{account_config.name}]的skey", color("fg_bold_yellow"))

        if not account_config.is_enabled():
            logger.warning("账号被禁用，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)
        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()

    # 执行对应逻辑
    for order_index, account_index in enumerate(indexes):  # 从1开始，第i个
        account_config = cfg.account_configs[account_index - 1]

        show_head_line(f"开始处理第{account_index}个账户[{account_config.name}]", color("fg_bold_yellow"))

        if not account_config.is_enabled():
            logger.warning("账号被禁用，将跳过")
            continue

        djcHelper = DjcHelper(account_config, cfg.common)

        djcHelper.fetch_pskey()
        djcHelper.check_skey_expired()
        djcHelper.get_bind_role_list()

        if send_to_xiaohao:
            logger.info(color("bold_green") + f"发送宝箱链接给小号QQ: {xiaohao_qq_list}")

            djcHelper.majieluo_send_to_xiaohao(xiaohao_qq_list)

            msg = (
                "1. 请在电脑登录大号QQ，依次点击各个小号的对话框里刚刚发送的宝箱链接，在浏览器中复制其链接中sCode的值到scode_list对应位置\n"
                "2. 请修改send_to_xiaohao为False后再次运行"
            )
            message_box(msg, "后续流程")
        else:
            scode = scode_list[order_index]
            logger.info(f"第{order_index + 1}个小号领取刚刚运行后填写的Scode列表中第{order_index + 1}个scode - {scode}")

            res = djcHelper.majieluo_open_box(scode)
            if res.sOutValue1 == 0:
                logger.info(color("bold_green") + "领取成功")
            else:
                code_to_message = {
                    "1": "无效的赠送链接",
                    "2": "不能打开自己的礼盒~",
                    "3": "该礼盒已经被开启",
                    "4": "好友今天的礼盒已经被全部打开了哦~",
                    "5": "一天只可以打开3次礼盒哦~",
                    "6": "该礼盒已经被开启",
                    "7": "该礼盒已经被开启",
                }
                message = "系统繁忙，请稍后再试~"
                if res.sOutValue1 in code_to_message:
                    message = code_to_message[res.sOutValue1]

                logger.error(message)

            time.sleep(1)

    # 第二次执行完毕提示修改send_to_xiaohao
    if not send_to_xiaohao:
        message_box("已领取完毕，请修改send_to_xiaohao为True，方便明天继续从头用", "提示")


if __name__ == '__main__':
    cui()
