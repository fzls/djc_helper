# 道聚城自动签到领奖助手
本脚本可用于自动化道聚城的查询、签到、领奖与兑换流程，从而不必再每日手动点开app去进行（签到-领取签到奖励-完成每日任务-领取任务奖励-领取金银箱子-兑换调整箱和疲劳药）的琐碎流程，解放双手和心智。

# 唯一发布地址
源代码将持续更新于[本仓库](https://github.com/fzls/djc_helper) ，每个版本将通过下面的蓝奏云链接进行发布，请勿于其他地方下载使用，如各种群文件、软件站等，避免使用到被篡改后的版本，以免出问题-。-

# 网盘链接（更新于2020/8/30)
链接: https://www.lanzoux.com/b01bor45i 提取码: fzls
链接: https://www.lanzoux.com/s/djc-helper 提取码: fzls

# 使用方法
首次使用时，需要设置一些东西，如qq号、登陆后msdk返回的skey（登录票据token）、dnf绑定的角色信息（兑换道具）、指尖江湖绑定的角色信息（完成手游领奖任务）
具体配置流程如下：

1. 安装python3环境，并安装依赖
    > 在当前目录输入下列内容<p>
    > pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
2. 获取uin和登录票据skey并填写到config.toml中
    1. 第一种方式（推荐）：直接运行工具，根据提示进行相关操作来获取skey并配置
    3. 第二种方式（操作比较复杂）：基于fiddler监听打开登陆后打开道聚城app各个页面的请求来获取uin和skey
        1. 电脑安装fiddler经典版，并开启https的监听功能，开放端口。手机链接同一个网络，并设置电脑的对应端口为代理服务器
            1. 具体操作参考链接（https://juejin.im/post/6844903602209685517）
        2. 手机下载道聚城app，登录上面配置的账号
        3. 在fiddler中随意找一个向djcapp.game.qq.com发起的请求记录
            1. 选中后，在右侧两个tab分别点选Inspector、Raw按钮
            2. 在文本框末尾应可看到形如下列的内容uin=o123456789; skey=@a1b2c3d4e
            3. 将uin/skey的值分别填写到config.toml中对应变量的值中即可
3. 获取dnf和指尖江湖的绑定角色信息
    1. 确保已在道聚城中绑定dnf和指尖江湖的角色信息，若对应游戏未创建账号，建议先去下载游戏客户端创建一个角色
    2. 运行djc_helper.py，使其调用末尾的那段代码
    
   ```python
   if __name__ == '__main__':
        djcHelper = DjcHelper()
        # djcHelper.run()
        djcHelper.query_all_extra_info()  # 当切换新的账号的时候，调用下面这个单独查询相关信息
   
    # 示例结果如下：   
    # 3.2.0 获取指尖江湖角色列表 [{'roleid': '指尖江湖角色ID', 'rolename': '指尖江湖玩家名'}]
    # 4.2.x 获取dnf角色列表 [{'roleid': DNF角色ID, 'rolename': 'DNF角色名', 'forceid': 0, 'level': 100}]
    ```
    3. 从结果中可获知相应角色信息，将角色id和角色名其填入到config.toml对应变量即可
    4. 目前默认dnf是浙江一区=11，指尖江湖是安卓手Q一区=20001，如果不是上述区服，可以从reference_data下的dnf_server_list.js和jx3_server_list.js中查询服务器的id
    5. 目前手游任务暂时只支持指尖江湖，后续版本将加入王者荣耀、天天酷跑等热门游戏
5. 万事ok，运行main.py或者直接双击运行道聚城助手.exe，芜湖起飞
    > python main.py

# 开机自动运行
1. 使用windows的任务计划程序来实现启动时或者每天凌晨定期运行改脚本，具体流程自行百度
2. 添加快捷方式放到windows的启动目录，具体方式参看后文
3. 其他自动运行的方式可以自行百度：如何特定时机/时间运行一个python脚本/exe

## 参考方案
现提供本人在用的windows下的一个方案
1. 在目录下新建一个start.bat批处理文件，内容如下
```bat
@ECHO OFF

:: 修改console默认encoding为utf8，避免中文乱码
CHCP 65001

echo 启动自动化助手
# python main.py
道聚城助手.exe

PAUSE

```
2. 在目录下右键创建一个快捷方式，右键选择属性，调整下列数值（具体路径记得改为自己的路径）
    1. 目标填：C:\Windows\System32\cmd.exe /c "D:\_codes\Python\djc_helper\start.bat"
    2. 起始位置：D:\_codes\Python\djc_helper
    3. 上述路径记得改为你实际放的位置
3. 打开启动目录，将这个快捷方式复制一份放进去
    > 我的电脑上的启动目录是下面这个，不同系统可能有所不同，可以百度一下
    > C:\Users\Administrator\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
4. 到此，每次启动电脑的时候就会自动运行这个脚本了

# 功能完成情况
- [ ] 自动化登录qq获取skey
- [x] 签到
- [x] 领取每日签到奖励
- [x] 领取累积签到奖励
- [x] 自动完成《礼包达人》任务
- [x] 自动完成《绝不错亿》任务
- [x] 领取任务奖励和金银宝箱
- [x] 兑换调整箱和疲劳药
- [x] 查询聚豆余额
- [x] 查询聚豆流水
- [x] 获取dnf角色信息
- [x] 获取指尖江湖（手游）礼包、角色信息
- [ ] 增加支持设置更多手游来用于完成《礼包达人》任务
- [ ] 增加自动完成更多其他蚊子腿活动，如心悦签到、最近出的助手的新活动等

# 已知缺陷
## 自动登录未实现
目前已实现除自动登录外的所有步骤，由于实现登录流程需要额外进行一些签名流程，比较难搞，不一定能搞定。而且即使实现，由于自动登录需要配置账号密码信息，尽管我不会进行网络上传，但还是有各种潜在的风险。所以即使实现了也不推荐使用该方式。

## 需要定期手动更新skey
因为还木有实现自动登录，且skey有有效期（暂时不确定具体时长），故而在skey过期时需要用户自行更新skey-。-

## 手游任务
目前手游任务暂时只支持指尖江湖，后续版本将加入王者荣耀、天天酷跑等热门游戏
