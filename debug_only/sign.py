import time

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

from data_struct import AESCipher

init_token_value = 5381


def getACSRFTokenForAMS(skey):
    skeyBytes = skey.encode()
    token = init_token_value
    for byte in skeyBytes:
        token += byte + (token << 5 & 0x7fffffff)

    return token & 0x7fffffff


# AES/ECB/PKCS5Padding
def getDjcSignParams(aes_key, rsa_public_key_file, qq_number, sDeviceID, appVersion):
    nowMillSecond = getMillSecondsUnix()
    dataToSign = f"{qq_number}+{sDeviceID}+{nowMillSecond}+{appVersion}"

    # aes
    encrypted = AESCipher(aes_key).encrypt(dataToSign)

    # rsa
    rasPublicKey = RSA.import_key(open(rsa_public_key_file, "rb").read())
    encrypted = PKCS1_v1_5.new(rasPublicKey).encrypt(encrypted)

    return encrypted.hex()


def getMillSecondsUnix():
    return int(time.time() * 1000.0)
