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
            "User-Agent": "TencentDaojucheng=v4.1.6.0&appSource=android&appVersion={appVersion}&ch=10003&sDeviceID={sDeviceID}&firmwareVersion=9&phoneBrand=Xiaomi&phoneVersion=MIX+2&displayMetrics=1080 * 2030&cpu=AArch64 Processor rev 1 (aarch64)&net=wifi&sVersionName=v4.1.6.0 Mobile GameHelper_1006/2103050005".format(
                appVersion=appVersion,
                sDeviceID=sDeviceID,
            ),
            "Charset": "UTF-8",
            "Referer": "https://daoju.qq.com/index.shtml",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Cookie": self.base_cookies,
        }

    def get(self, ctx, url, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True, extra_cookies=""):
        def request_fn():
            cookies = self.base_cookies + extra_cookies
            get_headers = {**self.base_headers, **{
                "Cookie": cookies,
            }}
            return requests.get(url, headers=get_headers, timeout=self.common_cfg.http_timeout)

        res = try_request(request_fn, self.common_cfg.retry)
        return process_result(ctx, res, pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote)

    def post(self, ctx, url, data, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True, extra_cookies=""):
        def request_fn():
            cookies = self.base_cookies + extra_cookies
            post_headers = {**self.base_headers, **{
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookies,
            }}
            return requests.post(url, data=data, headers=post_headers, timeout=self.common_cfg.http_timeout)

        res = try_request(request_fn, self.common_cfg.retry)
        logger.debug("{}".format(data))
        return process_result(ctx, res, pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote)


def try_request(request_fn, retryCfg, check_fn=None):
    """
    :param check_fn: func(requests.Response) -> bool
    :type retryCfg: RetryConfig
    """
    for i in range(retryCfg.max_retry_count):
        try:
            response = request_fn()  # type: requests.Response

            if check_fn is not None:
                if not check_fn(response):
                    raise Exception("check failed")

            return response
        except Exception as exc:
            logger.exception("request failed, detail as below:", exc_info=exc)
            logger.error("full call stack=\n{}".format(color("bold_black") + ''.join(traceback.format_stack())))
            logger.warning(color("thin_yellow") + "{}/{}: request failed, wait {}s".format(i + 1, retryCfg.max_retry_count, retryCfg.retry_wait_time))
            if i + 1 != retryCfg.max_retry_count:
                time.sleep(retryCfg.retry_wait_time)

    logger.error("重试{}次后仍失败".format(retryCfg.max_retry_count))


def process_result(ctx, res, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True):
    res.encoding = 'utf-8'

    if is_jsonp:
        data = jsonp2json(res.text, is_normal_jsonp, need_unquote)
    else:
        data = res.json()

    success = is_request_ok(data)

    if print_res:
        logFunc = logger.info
        if not success:
            logFunc = logger.error
    else:
        # 不打印的时候改为使用debug级别，而不是连文件也不输出，这样方便排查问题
        logFunc = logger.debug

    logFunc("{}\t{}".format(ctx, pretty_json(data, pretty)))

    return data


def is_request_ok(data):
    success = True
    try:
        returnCodeKeys = [
            "ret",
            "code",
            "iRet",
            "status",
            "ecode",
        ]
        for key in returnCodeKeys:
            if key in data:
                success = int(data[key]) == 0
                break

        # 特殊处理qq视频
        if "data" in data and type(data["data"]) is dict and "sys_code" in data["data"]:
            success = int(data["data"]["sys_code"]) == 0

        # 特殊处理赠送卡片
        if "13333" in data and type(data["13333"]) is dict and "ret" in data["13333"]:
            success = int(data["13333"]["ret"]) == 0

    except Exception as e:
        logger.error("is_request_ok parse failed data={}, exception=\n{}".format(data, e))

    return success


def jsonp2json(jsonpStr, is_normal_jsonp=True, need_unquote=True):
    if is_normal_jsonp:
        left_idx = jsonpStr.index("(")
        right_idx = jsonpStr.rindex(")")
        jsonpStr = jsonpStr[left_idx + 1:right_idx]
        return json.loads(jsonpStr)

    # dnf返回的jsonp比较诡异，需要特殊处理
    left_idx = jsonpStr.index("{")
    right_idx = jsonpStr.rindex("}")
    jsonpStr = jsonpStr[left_idx + 1:right_idx]

    jsonRes = {}
    for kv in jsonpStr.split(","):
        try:
            k, v = kv.strip().split(":")
            if v[0] == "'":
                v = v[1:-1]  # 去除前后的''
            if need_unquote:
                jsonRes[k] = unquote_plus(v)
            else:
                jsonRes[k] = v
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
