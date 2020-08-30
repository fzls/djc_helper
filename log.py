import datetime
import logging
import multiprocessing
import pathlib
import sys

###########################################################
#                         logging                         #
###########################################################
logFormatter = logging.Formatter("%(asctime)s %(levelname)-5.5s [%(name)s] %(funcName)s:%(lineno)d: %(message)s")
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
    fileHandler.setFormatter(logFormatter)
    fileHandler.setLevel(logging.DEBUG)
    logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
consoleHandler.setLevel(logging.INFO)
logger.addHandler(consoleHandler)
