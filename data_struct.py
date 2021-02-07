import json
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
            logger.warning(f"raw_config={raw_config} is not dict")
        else:
            for key, val in raw_config.items():
                if hasattr(self, key):
                    attr = getattr(self, key)
                    if isinstance(attr, ConfigInterface):
                        config_field = attr  # type: ConfigInterface
                        config_field.auto_update_config(val)
                    else:
                        setattr(self, key, val)

        # 尝试填充一些数组元素
        self.fill_array_fields(raw_config, self.fields_to_fill())

        # re: 以后有需求的时候再增加处理dict、set、tuple等

        # 调用可能存在的回调
        self.on_config_update(raw_config)

        # 最终返回自己，方便链式调用
        return self

    def fill_array_fields(self, raw_config: dict, fields_to_fill):
        for field_name, field_type in fields_to_fill:
            if field_name in raw_config:
                if raw_config[field_name] is None:
                    setattr(self, field_name, [])
                    continue
                setattr(self, field_name, [field_type().auto_update_config(item) for item in raw_config[field_name]])

    def fields_to_fill(self):
        return []

    def on_config_update(self, raw_config: dict):
        return

    def to_json(self):
        return to_json(self)

    def __str__(self):
        return json.dumps(self.to_json(), ensure_ascii=False)


def to_json(v):
    if isinstance(v, ConfigInterface):
        return {sk: to_json(sv) for sk, sv in v.__dict__.items()}
    elif isinstance(v, list):
        return list(to_json(sv) for sk, sv in enumerate(v))
    elif isinstance(v, tuple):
        return tuple(to_json(sv) for sk, sv in enumerate(v))
    elif isinstance(v, set):
        return set(to_json(sv) for sk, sv in enumerate(v))
    elif isinstance(v, dict):
        return {sk: to_json(sv) for sk, sv in v.items()}
    else:
        return v
