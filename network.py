import json
from urllib.parse import unquote

import requests

from config import *
from log import logger

jsonp_callback_flag = "jsonp_callback"


class Network:
    def __init__(self, sDeviceID, uin, skey):
        self.PRETTY_JSON = False

        self.base_headers = {
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

        self.get_headers = {**self.base_headers}

        self.post_headers = {**self.base_headers, **{
            "Content-Type": "application/x-www-form-urlencoded",
        }}

    def get(self, ctx, url, pretty=False, print_res=True, is_jsonp=False):
        res = requests.get(url, headers=self.get_headers)
        return self._common(ctx, res, pretty, print_res, is_jsonp)

    def post(self, ctx, url, data, pretty=False, print_res=True, is_jsonp=False):
        res = requests.post(url, data=data, headers=self.post_headers)
        return self._common(ctx, res, pretty, print_res, is_jsonp)

    def _common(self, ctx, res, pretty=False, print_res=True, is_jsonp=False):
        res.encoding = 'utf-8'

        if is_jsonp:
            data = self.jsonp2json(res.text)
        else:
            data = res.json()
        if print_res:
            success = True
            if "ret" in data:
                success = int(data["ret"]) == 0

            logFunc = logger.info
            if not success:
                logFunc = logger.error
            logFunc("{}\t{}".format(ctx, self.pretty_json(data, pretty)))
        return data

    def jsonp2json(self, jsonpStr):
        left_idx = jsonpStr.index("{")
        right_idx = jsonpStr.index("}")
        jsonpStr = jsonpStr[left_idx + 1:right_idx]

        jsonRes = {}
        for kv in jsonpStr.split(","):
            try:
                k, v = kv.strip().split(":")
                if v[0] == "'":
                    v = v[1:-1]  # 去除前后的''
                jsonRes[k] = unquote(v)
            except:
                pass

        return jsonRes

    def pretty_json(self, data, pretty=False):
        if self.PRETTY_JSON or pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return json.dumps(data, ensure_ascii=False)
