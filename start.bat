@ECHO OFF

:: 修改console默认encoding为utf8，避免中文乱码
CHCP 65001

set venv_path=".venv"
set pyscript_path="%venv_path%\Scripts"
set py_path="%pyscript_path%\python"
set pip_path="%pyscript_path%\pip"
set pyinstaller_path="%pyscript_path%\pyinstaller"

:: 更新代码
ECHO.
ECHO 更新源代码
git pull origin master

ECHO.
ECHO 尝试初始化venv
python _init_venv_and_requirements.py

ECHO.
ECHO 从venv启动小助手
.venv\Scripts\python main.py
