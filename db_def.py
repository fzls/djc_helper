from db_new import DbInterface


# ----------------- 数据定义 -----------------

class TestDb(DbInterface):
    def __init__(self):
        super().__init__()
        self.int_val = 1
        self.bool_val = True


if __name__ == '__main__':
    print(DbInterface())
    print(TestDb())
