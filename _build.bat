:: 修改console默认encoding为utf8，避免中文乱码
CHCP 65001

pyinstaller --icon 道聚城.ico --name 道聚城助手.exe -F --exclude-module PySide2 --exclude-module tkinter --exclude-module numpy --exclude-module PyQt5 --exclude-module PyQt5.QtCore --exclude-module PyQt5.QtGui --exclude-module PyQt5.QtWidgets --exclude-module distutils --exclude-module lib2to3 main.py


:: 复制生成的结果后删除临时文件
COPY /Y "dist\道聚城助手.exe" "道聚城助手.exe"
RMDIR /S /Q "build" "dist"
DEL /Q "道聚城助手.exe.spec"

PAUSE