from __future__ import annotations

import datetime
import os
from typing import Any, Callable

from const import db_top_dir
from data_struct import ConfigInterface
from log import logger


class DBInterface(ConfigInterface):
    time_cmt_millseconds = "%Y-%m-%d %H:%M:%S.%f"

    # ----------------- 通用字段定义 -----------------
    def __init__(self):
        from util import format_now

        self.context = "global"
        self.db_type_name = self.__class__.__name__
        self.version = ""

        self.create_at = format_now()
        self.save_at = format_now()
        self._update_at = format_now(self.time_cmt_millseconds)
        self.file_created = False

        # 如果设置了，则使用该路径，否则根据db类型和context的md5来生成路径
        self.db_filepath = ""

    def get_update_at(self) -> datetime.datetime:
        from util import parse_time
        return parse_time(self._update_at, self.time_cmt_millseconds)

    def set_update_at(self):
        from util import format_now
        self._update_at = format_now(self.time_cmt_millseconds)

    def get_version(self) -> str:
        return ""

    # ----------------- 数据库读写操作 -----------------
    def with_context(self, context: str) -> DBInterface:
        """
        设置context，默认为global，修改后保存的key将变更
        """
        self.context = context

        return self

    def load(self) -> DBInterface:
        db_file = self.prepare_env_and_get_db_filepath()

        # 若文件存在则加载到内存中
        if os.path.isfile(db_file):
            try:
                self.load_from_json_file(db_file)
            except Exception as e:
                logger.error(f"读取数据库失败，将重置该数据库 context={self.context} db_type_name={self.db_type_name} db_file={db_file}", exc_info=e)
                self.save()

                with open(db_file, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                logger.debug(f"old_content={old_content}")

        logger.debug(f"读取数据库完毕 context={self.context} db_type_name={self.db_type_name} db_file={db_file}")

        return self

    def save(self):
        from util import format_now

        db_file = self.prepare_env_and_get_db_filepath()
        try:
            if not os.path.isfile(db_file):
                self.create_at = format_now()

            self.save_at = format_now()
            self.file_created = True

            self.version = self.get_version()

            self.save_to_json_file(db_file)
        except Exception:
            logger.error(f"保存数据库失败，db_to_save={self}")

        logger.debug(f"保存数据库完毕 context={self.context} db_type_name={self.db_type_name} db_file={db_file}")

    def update(self, op: Callable[[Any], Any]) -> Any:
        # 加载配置
        self.load()
        # 回调
        res = op(self)
        # 保存修改后的配置
        self.save()

        # 返回回调结果
        return res

    def reset(self):
        db_file = self.prepare_env_and_get_db_filepath()
        if os.path.isfile(db_file):
            os.remove(db_file)

        logger.debug(f"重置数据库完毕 context={self.context} db_type_name={self.db_type_name} db_file={db_file}")

    # ----------------- 辅助函数 -----------------

    def with_db_filepath(self, filepath: str) -> DBInterface:
        self.db_filepath = os.path.realpath(filepath)

        return self

    def prepare_env_and_get_db_filepath(self) -> str:
        """
        逻辑说明
        假设key的md5为md5
        本地缓存文件路径为.db/md5{0:3}/md5.json
        文件内容为val_type的实例的json序列化结果
        :return: 是否是首次运行
        """
        from util import make_sure_dir_exists

        db_dir = ""
        db_file = ""

        if self.db_filepath != "":
            db_dir = os.path.dirname(self.db_filepath)
            db_file = self.db_filepath
        else:
            key_md5 = self.get_db_filename()

            db_dir = os.path.join(db_top_dir, key_md5[0:3])
            db_file = os.path.join(db_dir, key_md5)

        make_sure_dir_exists(db_dir)

        return db_file

    def get_db_filename(self) -> str:
        from util import md5

        key = f"{self.context}/{self.db_type_name}{self.get_version()}"
        return md5(key)


def test():
    from db import DemoDB

    def _test(db: DemoDB, save_inc: int, update_inc: int):
        # init
        db.int_val = 1

        # save
        db.int_val += save_inc
        db.save()

        assert_load_same(db, 1 + save_inc)

        def _cb(val: DemoDB) -> Any:
            val.int_val += update_inc
            return val.int_val

        db.update(_cb)

        assert_load_same(db, 1 + save_inc + update_inc)

    def assert_load_same(db: DemoDB, expect: int):
        load_db = DemoDB().with_context(db.context).load()
        assert load_db.int_val == expect

    # 测试全局
    _test(DemoDB(), 1, 10)

    # 测试设置context
    _test(DemoDB().with_context("test"), 2, 20)


def test_filepath_db():
    from db import DemoDB

    # 测试指定路径
    filepath_db = DemoDB().with_context("test_filepath").with_db_filepath("card_secrets/_local_test.txt")
    filepath_db.load()
    print(filepath_db.int_val)
    filepath_db.int_val = 666
    filepath_db.save()
    print(filepath_db.prepare_env_and_get_db_filepath())


if __name__ == '__main__':
    # test()
    test_filepath_db()
