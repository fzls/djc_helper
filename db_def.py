from __future__ import annotations

import os
from typing import Callable, Any

from const import db_top_dir
from data_struct import ConfigInterface
from log import logger


class DBInterface(ConfigInterface):
    # ----------------- 通用字段定义 -----------------
    def __init__(self):
        from util import format_now

        self.context = "global"
        self.db_type_name = self.__class__.__name__
        self.create_at = format_now()
        self.update_at = format_now()
        self.file_created = False

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
                self.file_created = True
            self.update_at = format_now()

            self.save_to_json_file(db_file)
        except Exception as e:
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

    def prepare_env_and_get_db_filepath(self) -> str:
        """
        逻辑说明
        假设key的md5为md5
        本地缓存文件路径为.db/md5{0:3}/md5.json
        文件内容为val_type的实例的json序列化结果
        :return: 是否是首次运行
        """
        from util import make_sure_dir_exists

        key_md5 = self.get_db_filename()

        db_dir = os.path.join(db_top_dir, key_md5[0:3])
        db_file = os.path.join(db_dir, key_md5)

        make_sure_dir_exists(db_dir)

        return db_file

    def get_db_filename(self) -> str:
        from util import md5

        key = f"{self.context}/{self.db_type_name}"
        return md5(key)


def test():
    from db import TestDB

    def _test(db: TestDB, save_inc: int, update_inc: int):
        # init
        db.int_val = 1

        # save
        db.int_val += save_inc
        db.save()

        assert_load_same(db, 1 + save_inc)

        def _cb(val: TestDB) -> Any:
            val.int_val += update_inc
            return val.int_val

        db.update(_cb)

        assert_load_same(db, 1 + save_inc + update_inc)

    def assert_load_same(db: TestDB, expect: int):
        load_db = TestDB().with_context(db.context).load()
        assert load_db.int_val == expect

    # 测试全局
    _test(TestDB(), 1, 10)

    # 测试设置context
    _test(TestDB().with_context("test"), 2, 20)


if __name__ == '__main__':
    test()
