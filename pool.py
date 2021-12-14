from multiprocessing import Pool
from multiprocessing.pool import Pool as TPool
from typing import Optional

from log import color, logger

pool: Optional[TPool] = None


def init_pool(pool_size):
    if pool_size <= 0:
        return

    global pool
    pool = Pool(pool_size)
    logger.info(color("bold_cyan") + f"进程池已初始化完毕，大小为 {pool_size}")


def close_pool():
    if pool is None:
        return

    pool.close()
    logger.info(color("bold_cyan") + "程序运行完毕，将清理线程池，释放相应资源")


def get_pool() -> Optional[TPool]:
    return pool


if __name__ == "__main__":
    print(get_pool())

    init_pool(8)

    print(get_pool())
    print(get_pool())
    print(get_pool().__hash__())
    print(get_pool().__hash__())
