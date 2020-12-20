import datetime
import json
import os

db_dir = ".db"
if not os.path.isdir(db_dir):
    os.mkdir(db_dir)


def load_db() -> dict:
    with open(localdb_file, 'r', encoding='utf-8') as fp:
        return json.load(fp)


def save_db(db):
    with open(localdb_file, 'w', encoding='utf-8') as fp:
        json.dump(db, fp, ensure_ascii=False, indent=4)


def load_db_for(accountName):
    db = load_db()

    account = get_account_from_db(accountName, db)

    return account


def update_db_for(accountName, callback):
    db = load_db()

    account = get_account_from_db(accountName, db)
    callback(account)

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


localdb_file = os.path.join(db_dir, 'db.json')
if not os.path.isfile(localdb_file):
    save_db({"created_at": datetime.datetime.now().timestamp()})
