import json
import time
from urllib.parse import unquote_plus

import requests

from config import *
from log import logger

jsonp_callback_flag = "jsonp_callback"


class Network:
    def __init__(self, sDeviceID, uin, skey, common_cfg):
        self.common_cfg = common_cfg  # type: CommonConfig

        self.base_cookies = "djc_appSource=android; djc_appVersion={djc_appVersion}; acctype=; uin={uin}; skey={skey};".format(
            djc_appVersion=appVersion,
            uin=uin,
            skey=skey,
        )

        self.base_headers = {
            "User-Agent": "TencentDaojucheng=v4.1.6.0&appSource=android&appVersion={appVersion}&ch=10003&sDeviceID={sDeviceID}&firmwareVersion=9&phoneBrand=Xiaomi&phoneVersion=MIX+2&displayMetrics=1080 * 2030&cpu=AArch64 Processor rev 1 (aarch64)&net=wifi&sVersionName=v4.1.6.0".format(
                appVersion=appVersion,
                sDeviceID=sDeviceID,
            ),
            "Charset": "UTF-8",
            "Referer": "https://daoju.qq.com/index.shtml",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Cookie": self.base_cookies,
        }

    def get(self, ctx, url, pretty=False, print_res=True, is_jsonp=False, extra_cookies=""):
        def request_fn():
            cookies = self.base_cookies + extra_cookies
            get_headers = {**self.base_headers, **{
                "Cookie": cookies,
            }}
            return requests.get(url, headers=get_headers, timeout=self.common_cfg.http_timeout)

        res = self.try_request(request_fn)
        return process_result(ctx, res, pretty, print_res, is_jsonp)

    def post(self, ctx, url, data, pretty=False, print_res=True, is_jsonp=False, extra_cookies=""):
        def request_fn():
            cookies = self.base_cookies + extra_cookies
            post_headers = {**self.base_headers, **{
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookies,
            }}
            return requests.post(url, data=data, headers=post_headers, timeout=self.common_cfg.http_timeout)

        res = self.try_request(request_fn)
        return process_result(ctx, res, pretty, print_res, is_jsonp)

    def try_request(self, request_fn):
        retryCfg = self.common_cfg.retry
        for i in range(retryCfg.max_retry_count):
            try:
                return request_fn()
            except requests.exceptions.Timeout as exc:
                logger.exception("{}/{}: request timeout, wait {}s".format(i + 1, retryCfg.max_retry_count, retryCfg.retry_wait_time), exc_info=exc)
                if i + 1 != retryCfg.max_retry_count:
                    time.sleep(retryCfg.retry_wait_time)

        logger.error("重试{}次后仍失败".format(retryCfg.max_retry_count))


def process_result(ctx, res, pretty=False, print_res=True, is_jsonp=False):
    res.encoding = 'utf-8'

    if is_jsonp:
        data = jsonp2json(res.text)
    else:
        data = res.json()
    if print_res:
        success = True
        if "ret" in data:
            success = int(data["ret"]) == 0
        elif "code" in data:
            success = int(data["code"]) == 0

        logFunc = logger.info
        if not success:
            logFunc = logger.error
        logFunc("{}\t{}".format(ctx, pretty_json(data, pretty)))
    return data


def jsonp2json(jsonpStr):
    left_idx = jsonpStr.index("{")
    right_idx = jsonpStr.index("}")
    jsonpStr = jsonpStr[left_idx + 1:right_idx]

    jsonRes = {}
    for kv in jsonpStr.split(","):
        try:
            k, v = kv.strip().split(":")
            if v[0] == "'":
                v = v[1:-1]  # 去除前后的''
            jsonRes[k] = unquote_plus(v)
        except:
            pass

    return jsonRes


def pretty_json(data, pretty=False, need_unquote=True):
    if pretty:
        jsonStr = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        jsonStr = json.dumps(data, ensure_ascii=False)

    if need_unquote:
        jsonStr = unquote_plus(jsonStr)

    return jsonStr
