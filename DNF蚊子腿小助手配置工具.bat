@ECHO OFF

:: 修改console默认encoding为utf8，避免中文乱码
CHCP 65001

echo 请在稍后打开的notepad++中修改config.toml对应配置项，修改完成后请按ctrl+s进行保存。
echo.
echo 如若不会操作，请查看使用教程目录下的文字教程或视频教程中关于配置相关的部分进行学习。
echo.
echo 请确保已阅读上述内容，然后点击任意键，即可打开配置文件

PAUSE

start npp_portable/notepad++.exe config.toml