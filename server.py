import requests

from log import color, logger
from usage_count import increase_counter

# 可能的服务器列表，优先使用前面的
server_ip_list = [
    # "127.0.0.1",  # 本地测试机
    "139.198.179.81",  # 青云
    "101.43.54.94",  # 腾讯云轻量服务器
]

# 检查服务器可用性时的超时时间
check_timeout = 3

# 当前选中的可用服务器ip
current_chosen_server_ip = ""

# 相关服务的端口
pay_server_port = "8438"
match_server_port = "8439"


def get_pay_server_addr(server_ip="") -> str:
    return f"http://{get_server_ip()}:{pay_server_port}"


def get_match_server_api(api_name="/") -> str:
    return f"http://{get_server_ip()}:{match_server_port}{api_name}"


def get_server_ip() -> str:
    global current_chosen_server_ip

    debugFunc = logger.debug
    # 可取消下面这行来本地测试，显示调试日志
    # debugFunc = logger.warning

    if current_chosen_server_ip == "":
        debugFunc(f"开始尝试选择可用的服务器: {server_ip_list}，超时时间为{check_timeout}秒")
        # 按优先级选择第一个可用的服务器
        for ip in server_ip_list:
            debugFunc("尝试连接服务器: " + ip)
            if is_server_alive(ip):
                current_chosen_server_ip = ip
                break

            debugFunc("连接失败")

        # 没有任何可用服务器时，取第一个
        if current_chosen_server_ip == "":
            current_chosen_server_ip = server_ip_list[0]
            logger.warning(f"未发现任何可用服务器，将使用首个服务器 {current_chosen_server_ip}")

        debugFunc(color("bold_cyan") + f"已初始化服务器为 {current_chosen_server_ip}")

        # 上报选用的服务器ip
        increase_counter(ga_category="chosen_server_ip", name=current_chosen_server_ip)

    return current_chosen_server_ip


def is_server_alive(ip: str) -> bool:
    check_alive_url = f"http://{ip}:{pay_server_port}"
    try:
        res = requests.get(check_alive_url, timeout=check_timeout)
        return res.status_code == 200

    except Exception:
        return False


if __name__ == "__main__":
    print(get_pay_server_addr())
    print(get_match_server_api())
