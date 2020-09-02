# 编译脚本
import os
import shutil
import subprocess

exe_name = '道聚城助手.exe'
icon = '道聚城.ico'

print("开始编译 {}".format(exe_name))

cmd = [
    'pyinstaller',
    '--icon', icon,
    '--name', exe_name,
    '-F',
    '--exclude-module', 'PySide2',
    '--exclude-module', 'tkinter',
    '--exclude-module', 'numpy',
    '--exclude-module', 'PyQt5',
    '--exclude-module', 'PyQt5.QtCore',
    '--exclude-module', 'PyQt5.QtGui',
    '--exclude-module', 'PyQt5.QtWidgets',
    '--exclude-module', 'distutils',
    '--exclude-module', 'lib2to3',
    'main.py',
]

subprocess.call(cmd)

print("编译结束，进行善后操作")
# 复制二进制
shutil.copyfile(os.path.join("dist", exe_name), exe_name)
# 删除临时文件
for directory in ["build", "dist", "__pycache__"]:
    shutil.rmtree(directory, ignore_errors=True)
for file in ["道聚城助手.exe.spec"]:
    os.remove(file)

print("done")