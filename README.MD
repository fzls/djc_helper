<div align="center">
  <h1>DNF蚊子腿小助手</h1>
</div>

<div align="center">
  <strong>本脚本可用于自动化DNF相关的一些蚊子腿活动，从而不必再每天在各种网页和app里点来点去，解放双手和心智。</strong>
</div>

<div align="center">
  现已支持最近新出的几乎所有蚊子腿活动，欢迎大家体验并使用~
</div>

<br>

<div align="center">
  相关页面: <br>
  <a href="https://fzls.github.io/djc_helper/#/">网页</a>
  <span> | </span>
  <a href="https://fzls.lanzoui.com/s/djc-helper">网盘</a>
  <span> | </span>
  <a href="https://space.bilibili.com/1851177">B站视频教程</a>
  <span> | </span>
  <a href="https://fzls.lanzoui.com/s/djc-tools">小工具</a>
</div>

<br>

<div align="center">
<!---
  <a href="https://codecov.io/gh/fzls/djc_helper">
    <img src="https://codecov.io/gh/fzls/djc_helper/branch/master/graph/badge.svg?token=2QY73AMZAK" alt="Codecov" />
  </a>
-->
  <a href="https://coveralls.io/github/fzls/djc_helper?branch=master">
    <img src="https://coveralls.io/repos/github/fzls/djc_helper/badge.svg?branch=master" alt="Coveralls" />
  </a>
  <a href="https://www.codacy.com/gh/fzls/djc_helper/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fzls/djc_helper&amp;utm_campaign=Badge_Grade">
    <img src="https://app.codacy.com/project/badge/Grade/d846d4bc8f1b46d6af4a873acabad5f0" alt="Codacy" />
  </a>
<!---
  <a href="https://www.codefactor.io/repository/github/fzls/djc_helper">
    <img src="https://www.codefactor.io/repository/github/fzls/djc_helper/badge" alt="CodeFactor" />
  </a>
-->
  <a href="https://github.com/fzls/djc_helper/actions/workflows/pytest.yml">
    <img src="https://github.com/fzls/djc_helper/actions/workflows/pytest.yml/badge.svg" alt="Test" />
  </a>
  <a href="https://github.com/fzls/djc_helper/actions/workflows/package.yml">
    <img src="https://github.com/fzls/djc_helper/actions/workflows/package.yml/badge.svg" alt="Build" />
  </a>
  <a href="https://GitHub.com/fzls/djc_helper/releases/">
    <img src="https://img.shields.io/github/release/fzls/djc_helper.svg" alt="Release" />
  </a>
</div>

## 目录

- [概览](#概览)
  - [支持的系统](#支持的系统)
  - [拉取代码](#拉取代码)
  - [长期支持的活动](#长期支持的活动)
  - [支持的短期活动](#支持的短期活动)
  - [基于auto.js支持的蚊子腿](#基于autojs支持的蚊子腿)
- [声明](#声明)
- [唯一发布地址](#唯一发布地址)
- [网盘链接（更新于2020/10/21)](#网盘链接更新于20201021)
- [视频教程](#视频教程)
- [交流群](#交流群)
- [『重要』与个人隐私有关的skey相关说明](#重要与个人隐私有关的skey相关说明)
- [自动登录须知](#自动登录须知)
  - [弊](#弊)
  - [利](#利)
- [提示：](#提示)
- [使用方法](#使用方法)
- [开机自动运行](#开机自动运行)
- [支持一下](#支持一下)
- [历史 Star 数](#历史-star-数)

# 概览
## 支持的系统
目前已测试在以下系统可以运行
1. Windows 7/10/11
2. Ubuntu 21.04 桌面版和服务器版 以及windows自带的wsl

## 拉取代码
如果github clone过慢，可以使用gitee的镜像仓库，目前设定了github action，会自动同步代码到gitee该仓库
> git clone --depth=1 https://gitee.com/fzls/djc_helper.git

或者可以使用github的镜像加速访问，如
> git clone --depth=1 https://github.com.cnpmjs.org/fzls/djc_helper.git
> git clone --depth=1 https://hub.fastgit.org/fzls/djc_helper.git

## 长期支持的活动
- [x] 道聚城签到与领奖、任务与领奖、兑换奖励、查询信息等功能
- [X] 心悦战场组队与领奖、任务、兑换奖励
- [X] 黑钻每月礼包
- [X] 信用积分礼包和游戏信用礼包

## 支持的短期活动
- [X] 2020.09.22 心悦国庆活动【金秋送福 心悦有礼】
- [X] 2020.09.22 集卡活动【征战希洛克集卡抽战灵天舞套！】
- [X] 2020.09.22 wegame国庆活动
- [X] 2020.09.22 阿拉德集合站活动
- [X] 2020.09.22 2020DNF闪光杯返场赛
- [X] 2020.09.22 腾讯视频蚊子腿
- [X] 2020.09.22 dnf助手希洛克攻击战活动
- [X] 2020.09.22 电脑管家蚊子腿
- [X] 2020.10.30 DNF助手10月女法师三觉活动
- [X] 2020.11.18 DNF进击吧赛利亚活动
- [X] 2020.11.29 dnf助手排行榜活动
- [X] 2020.12.02 阿拉德勇士征集令活动
- [X] 2020.12.02 dnf助手编年史活动
- [X] 2020.12.04 hello语音网页礼包兑换
- [X] 2020.12.07 dnf排行榜活动领黑钻流程
- [X] 2020.12.12 2020DNF嘉年华页面主页面签到活动
- [X] 2020.12.14 集卡活动-阿拉德勇士征集令
- [X] 2020.12.22 心悦app理财礼卡活动
- [X] 2020.12.22 2020DNF嘉年华直播活动
- [X] 2020.12.22 dnf福利中心兑换和三次签到功能
- [X] 2020.12.22 dnf共创投票逻辑
- [X] 2020.12.25 史诗之路活动
- [X] 2020.12.25 dnf漂流瓶活动
- [X] 2020.12.25 马杰洛的规划活动
- [X] 2020.12.25 dnf双旦活动
- [X] 2020.12.25 闪光杯第三期
- [X] 2020.12.26 暖冬有礼活动

## [基于auto.js支持的蚊子腿](https://github.com/fzls/autojs)
- [X] dnf微信签到和2020DNF嘉年华派送好礼活动
- [X] dnf助手编年史相关任务完成
- [X] hello语音阿拉德勇士征集令活动
- [X] 掌上wegame积分兑换Q币和明日宝藏
- [X] 心悦app G分 签到、每周免费抽奖、兑换复活币、心悦猫咪历练与战斗

# 声明
再强调一遍，这个工具首先是我自己用，然后才是分享出来给大家一起用的~<br>
核心需求是我自己会用能用，文档、教程都是为了方便各位使用而特地添加的，能起到一丝参考作用已经是很不错了。<br>
维护这个工具的时间有限，各位请将程序稳定性/功能可用性/异常崩溃等【偏程序】类的问题来作为反馈问题的主要类目，而不是配置方便性、文档准确性、视频精练度、界面美观度等【非程序类】问题。我是一个程序员，不是策划，也不是文案，更不是ui，能把程序功能做好已经很不错了。而且单就指引性信息而言，目前的文字文档、视频教程、配置文件注释、代码注释、运行时日志等已经提供了使用本工具所需要的几乎所有须知信息了。<br>
今天在论坛跟一个揪着文档不能完美描述程序运行逻辑这一点不放的人大吵了一顿，而且最后看他给出的截图，所谓的因为我没有给出多账号时账号名称不能重复这一点而浪费了半小时也完全不能成立，根据截图，明确提示了【第2个账号 默认账号 的名称与第1个账号的名称重复了，请调整为其他名称】，因为使用了默认的log.error方法，最终的色彩为暗红色，可能不太显眼，但是这并不能抵消实际已经给出了解决问题所需的完整信息这一点。<br>
今后如果再有这种事的话，我觉得可能还是我自己一个人用比较好，免得生是非=……=<br>
最后再提一小点，这真的只是单纯的分享出来给大家用，没有高人一等，也不比你低劣几分。我选择分享出来，也自然可以选择只接受特定内容的建议，你如果觉得好用，尽管去用。<br>
如果觉得哪里不好，如果是程序性逻辑问题，可以向我提issue或反馈，自然会尽力解决。如果是非程序类的问题，如配置方便性等，请自行fork一份代码去做调整，然后使用自己修改后的版本。当然如果愿意与其他人分享，也可以提一个pull request，如果真的有所改善，将会选择性合并进主干。当然，也可以选择不用哈。但是不接受就非程序类的问题来向我提意见/需求等，真的真的没有时间（别跟我说【我管你有没有时间】这种话，如果这样彼此没用沟通的必要了）。

# 唯一发布地址
源代码将持续更新于[本仓库](https://github.com/fzls/djc_helper) ，每个版本将通过下面的蓝奏云链接进行发布，请勿于其他地方下载使用，如各种群文件、软件站等，避免使用到被篡改后的版本，以免出问题-。-

# 网盘链接（更新于2020/10/21)
链接: https://fzls.lanzoui.com/b01bor45i 提取码: fzls
链接: https://fzls.lanzoui.com/s/djc-helper 提取码: fzls

# 视频教程
https://space.bilibili.com/1851177

# 交流群
DNF蚊子腿小助手     553925117 <br>
DNF蚊子腿小助手二群 966403777 <br>
DNF蚊子腿小助手三群 1041823293 <br>
DNF蚊子腿小助手四群 743671885 <br>
DNF蚊子腿小助手五群 545316504 <br>
DNF蚊子腿小助手六群 444193814 <br>

# 『重要』与个人隐私有关的skey相关说明
1. skey是腾讯系应用的通用鉴权票据，个中风险，请Google搜索《腾讯skey》后自行评估
2. skey有过期时间，目前根据测试来看应该是一天。目前已实现手动登录、扫码登录（默认）、自动登录。
    1. 手动登录需要自行在网页中登录并获取skey填写到配置表。
    2. 扫码登录则会在每次过期时打开网页让你签到，无需手动填写。
    3. 自动登录则设置过一次账号密码后续无需再操作。
3. 本脚本仅使用skey进行必要操作，用以实现自动化查询、签到、领奖和兑换等逻辑，不会上传到与此无关的网站，请自行阅读源码进行审阅
4. 如果感觉有风险，请及时停止使用本软件，避免后续问题

# 自动登录须知
自动登录需要在本地配置文件明文保存账号和密码，利弊如下，请仔细权衡后再决定是否适用
若觉得有任何不妥，强烈建议改回其他需要手动操作的登录模式

## 弊
1. 需要填写账号和密码，有潜在泄漏风险
2. 需要明文保存到本地，可能被他人窥伺
3. 涉及账号密码，总之很危险<_<

## 利
1. 无需手动操作，一劳永逸

# 提示：
目前仅保证CHANGELOG.MD和使用教程文档中是最新内容介绍，后续新功能可能会忘记添加到这里，大家可以自行查看对应文档。
更有甚者，因为精力有限，上述位置的描述可能也无法及时更新，如有冲突，以代码、注释以及命令行提示为准。

# 使用方法
请查看【使用教程/使用文档.docx】

# 开机自动运行
请查看【使用教程/使用文档.docx】

# 支持一下
[![支持一下](https://s3.ax1x.com/2020/12/16/r1yWZT.png)](https://imgchr.com/i/r1yWZT)

# 历史 Star 数
<p align="center">
    <a href="https://starchart.cc/fzls/djc_helper"><img src="https://starchart.cc/fzls/djc_helper.svg" alt="starchart"></a>
</p>
