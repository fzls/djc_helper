from __future__ import annotations

from typing import Any

from dao import BuyInfo, DnfHelperChronicleExchangeList, DnfHelperChronicleUserActivityTopInfo
from db_def import ConfigInterface, DBInterface

# ----------------- 数据定义 -----------------


class DemoDB(DBInterface):
    def __init__(self):
        super().__init__()
        self.int_val = 1
        self.bool_val = True


class FirstRunDB(DBInterface):
    def __init__(self):
        super().__init__()

    def get_version(self) -> str:
        # 2.0.0     修改字段update为_update，废弃原有数据
        return "2.0.0"


class WelfareDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.share_code_list: list[str] = []
        self.exchanged_dict: dict[str, bool] = {}


class DianzanDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.day_to_dianzan_count: dict[str, int] = {}
        self.used_content_ids: list[str] = []
        self.content_ids: list[str] = []


class CaptchaDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.offset_to_history_succes_count: dict[str, int] = {}

    def increse_success_count(self, offset: int):
        success_key = str(offset)  # 因为json只支持str作为key，所以需要强转一下，使用时再转回int
        if success_key not in self.offset_to_history_succes_count:
            self.offset_to_history_succes_count[success_key] = 0

        self.offset_to_history_succes_count[success_key] += 1


class LoginRetryDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.recommended_first_retry_timeout: float = 0.0
        self.history_success_timeouts: list[float] = []


class CacheDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.cache: dict[str, CacheInfo] = {}

    def dict_fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [("cache", CacheInfo)]


class CacheInfo(DBInterface):
    def __init__(self):
        super().__init__()

        self.value: Any = None


class FireCrackersDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.friend_qqs: list[str] = []


class UserBuyInfoDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.buy_info = BuyInfo()


class DnfHelperChronicleUserActivityTopInfoDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.account_name = ""
        self.year_month_to_user_info: dict[str, DnfHelperChronicleUserActivityTopInfo] = {}

    def dict_fields_to_fill(self) -> list[tuple[str, type[ConfigInterface]]]:
        return [("year_month_to_user_info", DnfHelperChronicleUserActivityTopInfo)]

    def get_last_month_user_info(self) -> DnfHelperChronicleUserActivityTopInfo:
        from util import get_last_month

        last_month = get_last_month()
        if last_month not in self.year_month_to_user_info:
            return DnfHelperChronicleUserActivityTopInfo()

        return self.year_month_to_user_info[last_month]


class DnfHelperChronicleExchangeListDB(DBInterface):
    def __init__(self):
        super().__init__()

        self.exchange_list = DnfHelperChronicleExchangeList()


if __name__ == "__main__":
    print(DBInterface())
    print(DemoDB())
