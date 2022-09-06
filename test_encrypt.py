from urllib.parse import parse_qsl

from encrypt import make_dnf_helper_signature, make_dnf_helper_signature_data


def test_make_dnf_helper_signature_post():
    method = "POST"
    api = "/yoyo/dnf/getuseractivitytopinfo"
    post_data = "appOpenid=4B92C052573D369D37CF9408B9112DA2&gameId=1006&game_code=dnf&openid=&sPartition=11&sRoleId=71672841&token=wvtY7ern&uin=1054073896&uniqueRoleId=3482436497&userId=504051073&cGameId=1006&cCurrentGameId=undefined&cRand=1662446109464&tghappid=1000045"
    data = make_dnf_helper_signature_data(dict(parse_qsl(post_data, keep_blank_values=True)))

    secret = "nKJH89hh@8yoHJ98y&IOhIUt9hbOh98ht"

    # post的签名中可有特殊字符，无需额外编码
    expect = "ylMdul+THpg4WrnM4gQOmWtttSk="

    assert make_dnf_helper_signature(method, api, data, secret) == expect


def test_make_dnf_helper_signature_get():
    method = "GET"
    api = "/peak/list/basic"

    query_string = "userId=504051073&gameId=1006&sPartition=11&sRoleId=71672841&game_code=dnf&token=wvtY7ern&uin=1054073896&uniqueRoleId=3482436497&openid=&appOpenid=4B92C052573D369D37CF9408B9112DA2&appidTask=1000042&cRand=1662446109111&tghappid=1000045"
    query_data = dict(parse_qsl(query_string, keep_blank_values=True))
    data = make_dnf_helper_signature_data(query_data)

    secret = "nKJH89hh@8yoHJ98y&IOhIUt9hbOh98ht"

    # get中的签名中的特殊字符，需要经过url编码
    expect = "CP2rBrBP%2Biimc%2BjA9jTbQZ8L5SQ%3D"

    assert make_dnf_helper_signature(method, api, data, secret) == expect


def test_make_dnf_helper_signature_data():
    data = {
        "appOpenid": "4B92C052573D369D37CF9408B9112DA2",
        "cCurrentGameId": "undefined",
        "cGameId": "1006",
        "cRand": "1660738585419",
        "gameId": "1006",
        "game_code": "dnf",
        "openid": "",
        "sPartition": "11",
        "sRoleId": "71672841",
        "tghappid": "1000045",
        "token": "wvtY7ern",
        "uin": "1054073896",
        "uniqueRoleId": "3482436497",
        "userId": "504051073",
    }

    expect = "appOpenid=4B92C052573D369D37CF9408B9112DA2&cCurrentGameId=undefined&cGameId=1006&cRand=1660738585419&gameId=1006&game_code=dnf&openid=&sPartition=11&sRoleId=71672841&tghappid=1000045&token=wvtY7ern&uin=1054073896&uniqueRoleId=3482436497&userId=504051073"

    assert make_dnf_helper_signature_data(data) == expect
