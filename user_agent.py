from enum import Enum


class UserAgent(Enum):
    # 手机qq
    MOBILE_QQ = "Mozilla/5.0 (Linux; U; Android 5.0.2; zh-cn; X900 Build/CBXCNOP5500912251S) AppleWebKit/533.1 (KHTML, like Gecko)Version/4.0 MQQBrowser/5.4 TBS/025489 Mobile Safari/533.1 V1_AND_SQ_6.0.0_300_YYB_D QQ/6.0.0.2605 NetType/WIFI WebP/0.3.0 Pixel/1440"
    # dnf助手
    DNF_HELPER = "Mozilla/5.0 (Linux; Android 9; MIX 2 Build/PKQ1.190118.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045714 Mobile Safari/537.36 GameHelper_1006/2103060508"
    # 道聚城
    DJC = "TencentDaojucheng=v4.1.6.0&appSource=android&appVersion=106&ch=10003&firmwareVersion=9&phoneBrand=Xiaomi&phoneVersion=MIX+2&displayMetrics=1080 * 2030&cpu=AArch64 Processor rev 1 (aarch64)&net=wifi&sVersionName=v4.1.6.0 Mobile GameHelper_1006/2103050005"
    # 心悦app
    XINYUE = "tgclub/5.7.6.81(Xiaomi MIX 2;android 9;Scale/440;android;865737030437124)"


if __name__ == "__main__":
    print(UserAgent.MOBILE_QQ.name)
    print(UserAgent.MOBILE_QQ.value)
    print(repr(UserAgent.MOBILE_QQ))
