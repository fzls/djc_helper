from __future__ import annotations

import json
import random
import time
import traceback
from typing import Callable
from urllib.parse import unquote_plus

import requests

from config import CommonConfig, RetryConfig
from const import appVersion, sVersionName
from dao import ResponseInfo
from log import color, logger
from util import check_some_exception, get_meaningful_call_point_for_log

jsonp_callback_flag = "jsonp_callback"


def check_tencent_game_common_status_code(response: requests.Response) -> Exception | None:
    """
    检查是否属于腾讯游戏接口返回请求过快的情况
    """
    if response.status_code == 401 and "您的速度过快或参数非法，请重试哦" in response.text:
        # res.status=401, Unauthorized <Response [401]>
        #
        # <html>
        # <head><title>Tencent Game 401</title></head>
        # <meta charset="utf-8" />
        # <body bgcolor="white">
        # <center><h1>Welcome Tencent Game 401</h1></center>
        # <center><h1>您的速度过快或参数非法，请重试哦</h1></center>
        # <hr><center>Welcome Tencent Game</center>
        # </body>
        # </html>
        #
        wait_seconds = 0.1 + random.random()
        logger.warning(get_meaningful_call_point_for_log() + f"请求过快，等待{wait_seconds:.2f}秒后重试")
        time.sleep(wait_seconds)
        return Exception("请求过快")
    elif response.status_code == 504 and "504 Gateway Time-out" in response.text:
        # status_code=504 reason=Gateway Time-out
        #
        # <html>
        # <head><title>504 Gateway Time-out</title></head>
        # <body>
        # <center><h1>504 Gateway Time-out</h1></center>
        # <hr><center>stgw</center>
        # </body>
        # </html>
        wait_seconds = 0.1 + random.random()
        logger.warning(get_meaningful_call_point_for_log() + f"网关超时，等待{wait_seconds:.2f}秒后重试")
        time.sleep(wait_seconds)
        return Exception("网关超时")

    return None


class Network:
    def __init__(self, sDeviceID, uin, skey, common_cfg):
        self.common_cfg: CommonConfig = common_cfg

        self.base_cookies = (
            "djc_appSource=android; djc_appVersion={djc_appVersion}; acctype=; uin={uin}; skey={skey};".format(
                djc_appVersion=appVersion,
                uin=uin,
                skey=skey,
            )
        )

        self.base_headers = {
            "User-Agent": "TencentDaojucheng={sVersionName}&appSource=android&appVersion={appVersion}&ch=10000&sDeviceID={sDeviceID}&firmwareVersion=9&phoneBrand=Xiaomi&phoneVersion=MIX+2&displayMetrics=1080 * 2030&cpu=AArch64 Processor rev 1 (aarch64)&net=wifi&sVersionName={sVersionName} Mobile GameHelper_1006/2103050005".format(
                appVersion=appVersion,
                sVersionName=sVersionName,
                sDeviceID=sDeviceID,
            ),
            "Charset": "UTF-8",
            "Referer": "https://daoju.qq.com/index.shtml",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Cookie": self.base_cookies,
        }

    def get(
        self,
        ctx,
        url,
        pretty=False,
        print_res=True,
        is_jsonp=False,
        is_normal_jsonp=False,
        need_unquote=True,
        extra_cookies="",
        check_fn: Callable[[requests.Response], Exception | None] | None = check_tencent_game_common_status_code,
        extra_headers: dict[str, str] | None = None,
        use_this_cookies="",
    ) -> dict:
        cookies = self.base_cookies + extra_cookies
        if use_this_cookies != "":
            cookies = use_this_cookies
        get_headers = {
            **self.base_headers,
            **{
                "Cookie": cookies,
            },
        }
        if extra_headers is not None:
            get_headers = {**get_headers, **extra_headers}

        def request_fn() -> requests.Response:
            return requests.get(url, headers=get_headers, timeout=self.common_cfg.http_timeout)

        res = try_request(request_fn, self.common_cfg.retry, check_fn)

        logger.debug(f"{ctx} cookies = {cookies}")

        return process_result(ctx, res, pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote)

    def post(
        self,
        ctx,
        url,
        data=None,
        json=None,
        pretty=False,
        print_res=True,
        is_jsonp=False,
        is_normal_jsonp=False,
        need_unquote=True,
        extra_cookies="",
        check_fn: Callable[[requests.Response], Exception | None] | None = check_tencent_game_common_status_code,
        extra_headers: dict[str, str] | None = None,
        disable_retry=False,
        use_this_cookies="",
    ) -> dict:
        cookies = self.base_cookies + extra_cookies
        if use_this_cookies != "":
            cookies = use_this_cookies
        content_type = "application/x-www-form-urlencoded"
        if data is None and json is not None:
            content_type = "application/json"

        post_headers = {
            **self.base_headers,
            **{
                "Content-Type": content_type,
                "Cookie": cookies,
            },
        }
        if extra_headers is not None:
            post_headers = {**post_headers, **extra_headers}

        def request_fn() -> requests.Response:
            return requests.post(url, data=data, json=json, headers=post_headers, timeout=self.common_cfg.http_timeout)

        if not disable_retry:
            res = try_request(request_fn, self.common_cfg.retry, check_fn)
        else:
            res = request_fn()

        logger.debug(f"{ctx} data = {data}")
        logger.debug(f"{ctx} json = {json}")
        logger.debug(f"{ctx} cookies = {cookies}")

        return process_result(ctx, res, pretty, print_res, is_jsonp, is_normal_jsonp, need_unquote)


def try_request(
    request_fn: Callable[[], requests.Response],
    retryCfg: RetryConfig,
    check_fn: Callable[[requests.Response], Exception | None] | None = check_tencent_game_common_status_code,
) -> requests.Response | None:
    """
    :param check_fn: func(requests.Response) -> bool
    :type retryCfg: RetryConfig
    """
    for i in range(retryCfg.max_retry_count):
        try:
            response: requests.Response = request_fn()
            fix_encoding(response)

            if check_fn is not None:
                check_exception = check_fn(response)
                if check_exception is not None:
                    raise check_exception

            return response
        except Exception as exc:

            def get_log_func(exc, log_func):
                if str(exc) == "请求过快":
                    return logger.debug
                else:
                    return log_func

            extra_info = check_some_exception(exc)
            get_log_func(exc, logger.exception)("request failed, detail as below:" + extra_info, exc_info=exc)
            stack_info = color("bold_black") + "".join(traceback.format_stack())
            get_log_func(exc, logger.error)(f"full call stack=\n{stack_info}")
            get_log_func(exc, logger.warning)(
                color("thin_yellow")
                + f"{i + 1}/{retryCfg.max_retry_count}: request failed, wait {retryCfg.retry_wait_time}s。异常补充说明如下：{extra_info}"
            )
            if i + 1 != retryCfg.max_retry_count:
                time.sleep(retryCfg.retry_wait_time)

    logger.error(f"重试{retryCfg.max_retry_count}次后仍失败")
    return None


# 每次处理完备份一次最后的报错，方便出错时打印出来~
last_response_info: ResponseInfo | None = None


def set_last_response_info(status_code: int, reason: str, text: str):
    global last_response_info
    last_response_info = ResponseInfo()
    last_response_info.status_code = status_code
    last_response_info.reason = reason
    last_response_info.text = text


last_process_result: dict | None = None


def process_result(
    ctx, res, pretty=False, print_res=True, is_jsonp=False, is_normal_jsonp=False, need_unquote=True
) -> dict:
    fix_encoding(res)

    if res is not None:
        set_last_response_info(res.status_code, res.reason, res.text)

    if is_jsonp:
        data = jsonp2json(res.text, is_normal_jsonp, need_unquote)
    else:
        json_text = res.text
        for _ in range(10):
            try:
                data = json.loads(json_text)
                break
            except json.JSONDecodeError as e:
                if e.msg == "Extra data":
                    # {"ret":0,"msg":"ok",...}{"ret":-5507,"msg":"很抱歉，系统繁忙，请等待10秒后再试！"...}
                    logger.debug(f"道聚城似乎又抽风了，末尾多加了一个json串，尝试移除最后一个左括号及之后的内容，修改前 json_text 为 {json_text}")
                    json_text = json_text[: json_text.rindex("{")]
                    logger.debug(f"修改后 json_text 为 {json_text}")
                else:
                    # 其他情况则继续抛出异常
                    raise e

    success = is_request_ok(data)

    if print_res:
        logFunc = logger.info
        if not success:
            logFunc = logger.error
    else:
        # 不打印的时候改为使用debug级别，而不是连文件也不输出，这样方便排查问题
        logFunc = logger.debug

    # log增加记录实际调用处
    ctx = get_meaningful_call_point_for_log() + ctx

    processed_data = pre_process_data(data)
    if processed_data is None:
        logFunc(f"{ctx}\t{pretty_json(data, pretty)}")
    else:
        # 如果数据需要调整，则打印调整后数据，并额外使用调试级别打印原始数据
        logFunc(f"{ctx}\t{pretty_json(processed_data, pretty)}")
        logger.debug(f"{ctx}(原始数据)\t{pretty_json(data, pretty)}")

    global last_process_result
    last_process_result = data

    return data


def fix_encoding(res: requests.Response):
    if res.encoding not in ["gbk"]:
        # 某些特殊编码不要转，否则会显示乱码
        res.encoding = "utf-8"


def pre_process_data(data) -> dict | None:
    # 特殊处理一些数据
    if type(data) is dict:
        if "frame_resp" in data and "data" in data:
            # QQ视频活动的回包太杂，重新取特定数据
            new_data = {}
            new_data["msg"] = extract_qq_video_message(data)
            new_data["code"] = data["data"].get("sys_code", data["ret"])
            new_data["prize_id"] = data["data"].get("prize_id", "0")
            return new_data

    return None


def extract_qq_video_message(res) -> str:
    data = res["data"]

    msg = ""
    if "lottery_txt" in data:
        msg = data["lottery_txt"]
    elif "wording_info" in data:
        msg = data["wording_info"]["custom_words"]

    if "msg" in res:
        msg += " | " + res["msg"]

    return msg


def is_request_ok(data) -> bool:
    success = True
    try:
        if type(data) is dict:
            returnCodeKeys = [
                "ret",
                "code",
                "iRet",
                "status",
                "ecode",
            ]
            for key in returnCodeKeys:
                if key in data:
                    # 特殊处理 status
                    val = data[key]
                    if key == "status":
                        if type(val) is str and not val.isnumeric():
                            success = False
                        else:
                            success = int(val) in [0, 1, 200]
                    else:
                        success = int(val) == 0
                    break

            # 特殊处理qq视频
            if "data" in data and type(data["data"]) is dict and "sys_code" in data["data"]:
                success = int(data["data"]["sys_code"]) == 0

            # 特殊处理赠送卡片
            if "13333" in data and type(data["13333"]) is dict and "ret" in data["13333"]:
                success = int(data["13333"]["ret"]) == 0
        elif type(data) is int:
            success = data == 0

    except Exception as e:
        logger.error(f"is_request_ok parse failed data={data}, exception=\n{e}")

    return success


def jsonp2json(jsonpStr, is_normal_jsonp=True, need_unquote=True) -> dict:
    if is_normal_jsonp:
        left_idx = jsonpStr.index("(")
        right_idx = jsonpStr.rindex(")")
        jsonpStr = jsonpStr[left_idx + 1 : right_idx]
        return json.loads(jsonpStr)

    # dnf返回的jsonp比较诡异，需要特殊处理
    left_idx = jsonpStr.index("{")
    right_idx = jsonpStr.rindex("}")
    jsonpStr = jsonpStr[left_idx + 1 : right_idx]

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
        except Exception:
            pass

    return jsonRes


def pretty_json(data, pretty=False, need_unquote=True) -> str:
    if pretty:
        jsonStr = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        jsonStr = json.dumps(data, ensure_ascii=False)

    if need_unquote:
        jsonStr = unquote_plus(jsonStr)

    return jsonStr
