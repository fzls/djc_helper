from abc import ABCMeta

from Crypto.Cipher import AES

from log import logger


class Object:
    def __init__(self, fromDict=None):
        if fromDict is None:
            fromDict = {}
        self.__dict__ = fromDict

    def __str__(self):
        return str(self.__dict__)


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


# 如果配置的值是dict，可以用ConfigInterface自行实现对应结构，将会自动解析
# 如果配置的值是list/set/tuple，则需要实现ConfigInterface，同时重写auto_update_config，在调用过基类的该函数后，再自行处理这三类结果
class ConfigInterface(metaclass=ABCMeta):
    def auto_update_config(self, raw_config: dict):
        if type(raw_config) is not dict:
            logger.warning("raw_config={} is not dict".format(raw_config))
            return
        
        for key, val in raw_config.items():
            if hasattr(self, key):
                attr = getattr(self, key)
                if isinstance(attr, ConfigInterface):
                    config_field = attr  # type: ConfigInterface
                    config_field.auto_update_config(val)
                else:
                    setattr(self, key, val)

    def get_str_for(self, v):
        res = v
        if isinstance(v, ConfigInterface):
            res = v.__str__()
        elif isinstance(v, list):
            res = list(self.get_str_for(sv) for sk, sv in enumerate(v))
        elif isinstance(v, tuple):
            res = tuple(self.get_str_for(sv) for sk, sv in enumerate(v))
        elif isinstance(v, set):
            res = set(self.get_str_for(sv) for sk, sv in enumerate(v))
        elif isinstance(v, dict):
            res = {sk: self.get_str_for(sv) for sk, sv in v.items()}

        return res

    def __str__(self):
        res = {}
        for k, v in self.__dict__.items():
            res[k] = self.get_str_for(v)
        return str(res)
