@ECHO OFF

:: 修改console默认encoding为utf8，避免中文乱码
CHCP 65001

echo 请在稍后打开的notepad++中修改config.toml对应配置项，修改完成后请按ctrl+s进行保存。
echo.
echo 简单背景知识：
echo 1. bool类的配置项值为true表示启用，false表示不启用。eg. get_djc = false 表示不启用道聚城相关功能
echo 2. 示例配置中若含有双引号，实际填值请保留。如auto_send_card_target_qqs = ["123456"]，将123456替换为自己的QQ，双引号留下
echo 3. config.toml为实际配置文件，包含大部分用户需要用到的配置项。config.toml.example为示例配置文件，包含所有公开提供的配置项
echo 4. 多账号配置时，请确保每个账号配置的name不同，否则会报错
echo 5. 很多配置项（如心悦兑换奖励列表）默认为注释状态（此时取工具设定的默认值，比如列表类配置则默认为无配置）。如果想要启用，可以在notepad++中选择对应行然后按 ctrl+/ 快捷键进行取消注释。当需要注释特定配置项时，同理，选中按前述快捷键即可注释
echo 更多关于toml配置语法的背景知识，请百度 toml 简要教程 关键词进行搜索。
echo.
echo 如若不会操作，请查看使用教程目录下的文字教程或视频教程中关于配置相关的部分进行学习。
echo.
echo 请确保已阅读上述内容，然后点击任意键，即可打开配置文件

PAUSE

start utils/npp_portable/notepad++.exe config.toml