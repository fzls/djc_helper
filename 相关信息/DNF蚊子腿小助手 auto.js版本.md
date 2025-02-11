# 前言
由于部分蚊子腿实在难以在小助手里实现，于是乎这部分内容目前将基于auto.js进行开发并分享~

# TLRD
基于auto.js实现的dnf蚊子腿相关自动化脚本，用于补充DNF蚊子腿小助手，实现其难以完成的一些逻辑~
Github：https://github.com/fzls/autojs
主页：https://fzls.github.io/autojs/#/
交流群：
    telegram群组       https://t.me/djc_helper
    telegram频道       https://t.me/djc_helper_notice
    DNF蚊子腿小助手     https://docs.qq.com/doc/DYlFkaHdjTEp0dUZv
# auto.js下载地址
由于auto.js被各种黑产使用，原作者停止发布auto.js，而是开发与发布加了一些限制的auto.js pro（限制指无法对国内一些app操作，如支付宝、微信、淘宝啥的）。<br>
为了方便使用，推荐使用之前版本的auto.js。<br>
以下链接为酷安评论区【点石斋废喵】网友使用之前免费版本源码编译出的apk包，目前我用的也是这个（不提供任何担保，仅方便各位快速找到可用版本）<br>
1. [点石斋废喵 网友发布的github下载链接](https://github.com/Ericwyn/Auto.js/releases)
2. [我从他这下载后上传到蓝奏云的链接](https://fzls.lanzouo.com/s/djc-helper)

# 视频演示
心悦app脚本演示         https://www.bilibili.com/video/BV1zy4y1S7YL
Hello语音脚本演示       https://www.bilibili.com/video/BV1Y54y167ZH
掌上WeGame脚本演示      https://www.bilibili.com/video/BV1FT4y1M7gb
DNF助手脚本演示         https://www.bilibili.com/video/BV1G5411G7xA

# 使用须知
目前为了方便编写，大部分操作都是通过点击特定坐标的方式来实现的，目前版本是基于小米 MIX 2（2160 X 1080）的屏幕适配的。
如果使用该系列脚本，请自行调整各个坐标。

## 获取坐标的参考流程
1. 在手机上打开开发者模式（具体手机操作方法请百度）
2. 找到【指标位置】的开关，打开以使屏幕叠加层显示当前触摸点坐标。
    > MIUI系统应该是这个名称，其他手机请自行百度对应名称。

# 设置自动运行
可使用autojs自带的定时操作或者使用tasker来定期运行各个脚本~

## auto.js文档中关于定时运行的描述
* 如何定时运行脚本
> 点击脚本右边的菜单按钮->更多->定时任务即可定时运行脚本，但是必须保持Auto.js后台运行(自启动白名单、电源管理白名单等)。同时，可以在脚本的开头使用device.wakeUp()来唤醒屏幕；但是，Auto.js没有解锁屏幕的功能，因此难以在有锁屏密码的设备上达到效果。


# 各脚本功能简介
## _common.js
对auto.js进行的一些封装操作，简化脚本使用流程

## dnf_helper.js
dnf助手排行榜活动自动化完成获取鲜花任务以及编年史相关任务脚本
1. 阅读文字咨询
2. 阅读视频咨询
3. 阅读动态
4. 访问他人主页并关注社区好友
5. 分享周报

## hello_voice.js
hello语音dnf活动自动化脚本
1. 登录DNF助手以获取Hello贝
2. 阿拉德勇士征集令活动的投票助力及累积奖励领取
3. 阿拉德勇士征集令活动的签到、分享、抽奖

## wegame.js
掌上WeGame 每日签到与明日宝藏脚本
1. 进入福利中心进行自动签到
2. 限时兑换1-5Q币
3. 明日宝藏参与明日活动以及领取昨日奖励

## wx_dnf_checkin.js
微信dnf签到活动自动化脚本
1. 打开文件助手
2. 打开签到页面（默认文件助手最新一条为签到网页消息）
3. 签到

## xinyue.js
心悦app G分脚本
1. G分签到
2. 自动领取周礼包并抽完全部免费抽奖次数
3. 兑换复活币到首个角色
4. 心悦猫咪战斗、历练以及领取历练奖励
