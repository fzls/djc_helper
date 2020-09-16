import threading

import win32con
import win32gui


def uin2qq(uin):
    return str(uin)[1:].lstrip('0')


def maximize_console():
    threading.Thread(target=maximize_console_sync, daemon=True).start()

def maximize_console_sync():
    hwnd = win32gui.GetForegroundWindow()
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)


if __name__ == '__main__':
    print(uin2qq("o0563251763"))
