<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# nonebot-plugin-bilibilibot

👾 _NoneBot bilibili通知插件_ 👾
    
</div>

# 简介
基于[Nonebot2](https://github.com/nonebot/nonebot2)的bilibili通知插件，可将up主，主播以及番剧的更新/直播动态推送到QQ

# 特色功能
- 可通过在B站客户端分享用户主页进行关注up主

- 可通过在B站客户端分享直播间进行关注主播

- 可通过分享番剧播放页面进行关注番剧

- 超级用户可对普通用户进行广播

# 配置项
配置方式: 请在nonebot的全局配置文件中添加如下配置项。
## SUPERUSERS
- 类型: List[str]
- 说明: 超级用户的列表
> SUPERSUSERS = ["your qq id"]

# 示例
## 获取帮助
![help](docs/help.jpg)
## 视频更新推送
![videupdate](/docs/updatepush.jpg)
![videopush](/docs/videopush.jpg)
## 直播开播推送
![streampuah](docs/streampush.jpg)
## 通过B站客户端分享进行关注
![follow](docs/follow.jpg)
## 查询关注列表
![list](docs/list.jpg)





# 特别鸣谢
- 感谢0w0w0帮助测试
