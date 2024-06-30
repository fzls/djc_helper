from __future__ import annotations

from multiprocessing import Pool
from multiprocessing.pool import Pool as TPool

from log import color, logger

pool: TPool | None = None


def init_pool(pool_size):
    if pool_size <= 0:
        return

    global pool
    logger.info(f"开始创建进程池，大小为 {pool_size}")
    pool = Pool(pool_size)
    logger.info(color("bold_cyan") + f"进程池已初始化完毕，大小为 {pool_size}")


def close_pool():
    global pool
    if pool is None:
        return

    pool_size = get_pool_size()
    logger.info(color("bold_cyan") + f"程序运行完毕，将清理线程池({pool_size})，释放相应资源")

    pool.close()
    pool = None
    logger.info(color("bold_cyan") + "清理完毕")


def get_pool_size() -> int:
    if pool is None:
        return 0

    return pool._processes


def get_pool() -> TPool | None:
    return pool


if __name__ == "__main__":
    print(get_pool())

    init_pool(8)

    print(get_pool())
    print(get_pool())
    print(get_pool().__hash__())
    print(get_pool().__hash__())
