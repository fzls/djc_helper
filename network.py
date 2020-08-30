import json
from urllib.parse import unquote

import requests

from config import *
from log import logger

base_headers = {
    "User-Agent": "TencentDaojucheng=v4.1.6.0&appSource=android&appVersion={appVersion}&ch=10003&sDeviceID={sDeviceID}&firmwareVersion=9&phoneBrand=Xiaomi&phoneVersion=MIX+2&displayMetrics=1080 * 2030&cpu=AArch64 Processor rev 1 (aarch64)&net=wifi&sVersionName=v4.1.6.0".format(
        appVersion=appVersion,
        sDeviceID=sDeviceID,
    ),
    "Charset": "UTF-8",
    "Referer": "https://daoju.qq.com/index.shtml",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "Cookie": "djc_appSource=android; djc_appVersion={djc_appVersion}; acctype=; uin={uin}; skey={skey}".format(
        djc_appVersion=appVersion,
        uin=uin,
        skey=skey,
    ),
}

get_headers = {**base_headers}

post_headers = {**base_headers, **{
    "Content-Type": "application/x-www-form-urlencoded",
}}

jsonp_callback_flag = "jsonp_callback"


def get(ctx, url, pretty=False, print_res=True, is_jsonp=False):
    res = requests.get(url, headers=get_headers)
    return _common(ctx, res, pretty, print_res, is_jsonp)


def post(ctx, url, data, pretty=False, print_res=True, is_jsonp=False):
    res = requests.post(url, data=data, headers=post_headers)
    return _common(ctx, res, pretty, print_res, is_jsonp)


def _common(ctx, res, pretty=False, print_res=True, is_jsonp=False):
    res.encoding = 'utf-8'

    if is_jsonp:
        data = jsonp2json(res.text)
    else:
        data = res.json()
    if print_res:
        logger.info("{}\t{}".format(ctx, pretty_json(data, pretty)))
    return data


def jsonp2json(jsonpStr):
    left_idx = jsonpStr.index("{")
    right_idx = jsonpStr.index("}")
    jsonpStr = jsonpStr[left_idx + 1:right_idx]

    jsonRes = {}
    for kv in jsonpStr.split(","):
        k, v = kv.strip().split(":")
        if v[0] == "'":
            v = v[1:-1]  # 去除前后的''
        jsonRes[k] = unquote(v)

    return jsonRes


PRETTY_JSON = False


def pretty_json(data, pretty=False):
    if PRETTY_JSON or pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    else:
        return json.dumps(data, ensure_ascii=False)
