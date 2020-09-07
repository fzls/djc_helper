def uin2qq(uin):
    return str(uin)[1:].lstrip('0')


if __name__ == '__main__':
    print(uin2qq("o0563251763"))
