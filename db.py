import datetime
import json
import os

from log import logger, color

db_dir = ".db"
if not os.path.isdir(db_dir):
    os.mkdir(db_dir)


def load_db() -> dict:
    with open(localdb_file, 'r', encoding='utf-8') as fp:
        return json.load(fp)


def save_db(db):
    with open(localdb_file, 'w', encoding='utf-8') as fp:
        json.dump(db, fp, ensure_ascii=False, indent=4)


def update_db(callback):
    db = load_db()

    callback(db)

    save_db(db)

    return db


def load_db_for(accountName):
    db = load_db()

    accountDb = get_account_from_db(accountName, db)

    return accountDb


def save_db_for(accountName, accountDb):
    db = load_db()

    set_account_to_db(accountName, db, accountDb)

    save_db(db)


def update_db_for(accountName, callback):
    db = load_db()

    accountDb = get_account_from_db(accountName, db)
    callback(accountDb)

    save_db(db)

    return db


def get_account_from_db(accountName, db):
    if "accounts" not in db:
        db["accounts"] = {}
    accounts = db["accounts"]
    if accountName not in accounts:
        accounts[accountName] = {}
    account = accounts[accountName]
    return account


def set_account_to_db(accountName, db, accountDb):
    if "accounts" not in db:
        db["accounts"] = {}
    accounts = db["accounts"]

    accounts[accountName] = accountDb


def init_db():
    save_db({
        "created_at": datetime.datetime.now().timestamp(),
        "created_at_str": datetime.datetime.now(),
    })
    logger.info(color("bold_green") + "数据库已初始化完毕")


localdb_file = os.path.join(db_dir, 'db.json')
# 如果未创建，则初始化
if not os.path.isfile(localdb_file):
    init_db()
# 检测数据库是否损坏，若损坏则重新初始化
try:
    load_db()
except json.decoder.JSONDecodeError as e:
    logger.error("数据库似乎损坏了，具体出错情况如下，将重新初始化数据库文件", exc_info=e)
    init_db()
