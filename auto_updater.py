import argparse
import os
import subprocess
import shutil

# 自动更新的基本原型，日后想要加这个逻辑的时候再细化接入

parser = argparse.ArgumentParser()
parser.add_argument("--pid", default=0, type=int)
parser.add_argument("--version", default=0, type=int)
args = parser.parse_args()

print("更新器的进程为{}，主进程为{}".format(os.getpid(), args.pid))

# 进行实际的检查是否需要更新操作
need_update = args.version < 2

if need_update:
    print("需要更新，尝试干掉原进程={}".format(args.pid))
    os.kill(args.pid, 9)

    print("进行更新操作...")
    shutil.copyfile("test2.py", "test.py")

    print("更新完毕，重新启动程序")
    subprocess.call([
        "python",
        "test.py",
    ])
    input("输入任意键退出更新器")
else:
    print("已经是最新版本，不需要更新")

# 示例用法
# import subprocess
# import os
# import argparse
#
# version = 1
#
# print("这是更新前的主进程，version={}".format(version))
#
# print("主进程pid={}".format(os.getpid()))
#
# print("尝试启动更新器，并传入当前进程pid和版本号，等待其执行完毕。若版本有更新，则会干掉这个进程并下载更新文件，之后重新启动进程")
# p = subprocess.Popen([
#     "python",
#     "auto_updater.py",
#     "--pid", str(os.getpid()),
#     "--version", str(version),
# ], shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,)
# p.wait()
#
# print("实际进行相关逻辑")
#
# print("主进程退出")
