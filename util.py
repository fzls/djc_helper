import threading

import win32con
import win32gui
from log import logger


def uin2qq(uin):
    return str(uin)[1:].lstrip('0')


def maximize_console():
    threading.Thread(target=maximize_console_sync, daemon=True).start()


def maximize_console_sync():
    hwnd = win32gui.GetForegroundWindow()
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)


def show_head_line(msg):
    char = "+"
    line_length = 80
    msg_len = sum([1 if ord(c) < 128 else 2 for c in msg])
    mid_side_length = (line_length - msg_len) // 2

    # 按照下列格式打印
    # +++++++++++
    # +  test   +
    # +++++++++++
    logger.warning(char * line_length)
    logger.warning(char + " " * (mid_side_length - 1) + msg + " " * (mid_side_length - 1) + char)
    logger.warning(char * line_length)


if __name__ == '__main__':
    print(uin2qq("o0563251763"))
