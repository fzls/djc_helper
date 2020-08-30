from Crypto.Cipher import AES


class AESCipher:
    BLOCK_SIZE = 16  # Bytes

    def __init__(self, key):
        # 加密需要的key值
        self.key = key.encode()

    def encrypt(self, raw):
        raw = self.pad(raw)
        # 通过key值，使用ECB模式进行加密
        cipher = AES.new(self.key, AES.MODE_ECB)
        # 返回得到加密后的字符串
        return cipher.encrypt(raw.encode())

    def decrypt(self, enc):
        # 通过key值，使用ECB模式进行解密
        cipher = AES.new(self.key, AES.MODE_ECB)
        return self.unpad(cipher.decrypt(enc)).decode('utf8')

    # Padding for the input string --not related to encryption itself.
    def pad(self, s):
        return s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * chr(self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE)

    def unpad(self, s):
        return s[:-ord(s[len(s) - 1:])]
