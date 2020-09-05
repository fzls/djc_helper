import datetime
import logging
import multiprocessing
import pathlib
import sys

import colorlog

###########################################################
#                         logging                         #
###########################################################
fileFmtStr = "%(asctime)s [%(name)s] %(funcName)s:%(lineno)d %(levelname)-5.5s: %(message)s"
consoleFmtStr = "{}%(asctime)s {}[%(name)s] {}%(funcName)s:%(lineno)d {}%(levelname)-5.5s: %(message)s".format(
    "%(purple)s",
    "%(purple)s",
    "%(purple)s",
    "%(log_color)s",
)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.name = "djc_helper"

log_directory = "logs"
try:
    pathlib.Path(log_directory).mkdir(parents=True, exist_ok=True)
except PermissionError as err:
    print("创建日志目录logs失败，请确认是否限制了基础的运行权限")
    sys.exit(-1)

process_name = multiprocessing.current_process().name
if "MainProcess" in process_name:
    time_str = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    fileHandler = logging.FileHandler("{0}/{1}_{2}_{3}.log".format(log_directory, logger.name, process_name, time_str), encoding="utf-8")
    fileLogFormatter = logging.Formatter(fileFmtStr)
    fileHandler.setFormatter(fileLogFormatter)
    fileHandler.setLevel(logging.DEBUG)
    logger.addHandler(fileHandler)

consoleLogFormatter = colorlog.ColoredFormatter(
    consoleFmtStr,
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red',
    },
    secondary_log_colors={},
    style='%'
)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(consoleLogFormatter)
consoleHandler.setLevel(logging.INFO)
logger.addHandler(consoleHandler)

if __name__ == '__main__':
    consoleHandler.setLevel(logging.DEBUG)
    logger.debug("debug")
    logger.info("info")
    logger.warning("warn")
    logger.error("error")
    logger.critical("critical")
    logger.exception("exception", exc_info=Exception("测试Exception"))
