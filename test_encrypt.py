from encrypt import make_dnf_helper_signature, make_dnf_helper_signature_data


def test_make_dnf_helper_signature():
    method = "POST"
    api = "/yoyo/dnf/getuseractivitytopinfo"
    post_data = "appOpenid=4B92C052573D369D37CF9408B9112DA2&cCurrentGameId=undefined&cGameId=1006&cRand=1660738585419&gameId=1006&game_code=dnf&openid=&sPartition=11&sRoleId=71672841&tghappid=1000045&token=wvtY7ern&uin=1054073896&uniqueRoleId=3482436497&userId=504051073"

    secret = "nKJH89hh@8yoHJ98y&IOhIUt9hbOh98ht"

    expect = "UM7eesly6VMgafca2rEVq657VdE="

    assert make_dnf_helper_signature(method, api, post_data, secret) == expect


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
