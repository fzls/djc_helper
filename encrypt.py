from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any
from urllib.parse import quote_plus


def make_dnf_helper_signature(
    http_method: str,
    api_path: str,
    post_data: str,
    secret: str,
) -> str:
    data = "&".join([http_method, quote_plus(api_path), quote_plus(post_data)])

    hash_bytes = hmac.new(secret.encode(), data.encode(), hashlib.sha1).digest()

    signature = base64.b64encode(hash_bytes).decode()

    # 对于get请求，由于签名字段要放到query string中，需要做下url编码
    if http_method == "GET":
        signature = quote_plus(signature)

    return signature


def make_dnf_helper_signature_data(data: dict[str, Any]) -> str:
    # 取出keys
    keys = list(data.keys())

    # 升序排序
    keys.sort()

    # 按顺序拼接成字符串
    results = []
    for key in keys:
        results.append(f"{key}={data[key]}")

    final_result = "&".join(results)

    return final_result


if __name__ == "__main__":
    from urllib.parse import parse_qsl

    query_string = "userId=504051073&gameId=1006&sPartition=11&sRoleId=71672841&game_code=dnf&token=wvtY7ern&uin=1054073896&uniqueRoleId=3482436497&openid=&appOpenid=4B92C052573D369D37CF9408B9112DA2&appidTask=1000042&cRand=1660746760049&tghappid=1000045"
    query_data = dict(parse_qsl(query_string, keep_blank_values=True))

    # query_data = {
    #     "userId": "504051073",
    #     "gameId": 1006,
    #     "sPartition": "11",
    #     "sRoleId": "71672841",
    #     "game_code": "dnf",
    #     "token": "wvtY7ern",
    #     "uin": "1054073896",
    #     "uniqueRoleId": "3482436497",
    #     "openid": "",
    #     "appOpenid": "4B92C052573D369D37CF9408B9112DA2",
    #     "appidTask": 1000042,
    #     "cRand": 1660746760049,
    #     "tghappid": 1000045
    # }

    data = make_dnf_helper_signature_data(query_data)

    print(
        make_dnf_helper_signature(
            "GET",
            "/peak/list/basic",
            data,
            "nKJH89hh@8yoHJ98y&IOhIUt9hbOh98ht",
        )
    )
