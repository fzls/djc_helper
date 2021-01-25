@ECHO OFF

:: 修改console默认encoding为utf8，避免中文乱码
CHCP 65001

rmdir /S /Q .cached

echo 已清除登录信息，请点击任意键退出。之后重新运行小助手即可

PAUSE