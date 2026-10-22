---
name: weibo-upload
description: 使用 social-auto-upload 的 `sau weibo` 登录微博并发布视频，可指定封面。Use when 用户要向微博发布视频或检查微博账号状态。
license: MIT-0
slug: social-auto-upload-weibo-upload
displayName: 微博视频发布
version: 1.0.0
summary: 使用 sau 登录微博并发布视频，可指定封面。
---

# 微博视频发布

调用现有 CLI，不另写网页上传流程。账号名是本地会话别名。

```powershell
sau weibo login --account creator
sau weibo check --account creator
sau weibo upload-video --account creator --file videos/demo.mp4 --title "标题" --desc "简介" --tags 微博,测试 --thumbnail covers/demo.png
```

当前仅支持视频，不支持图文和定时发布。标题最多 30 个字；封面建议小于 5 MB。登录时若出现二维码，展示二维码图片供用户扫码。完整参数以 `sau weibo upload-video --help` 为准。

发布前核对账号、视频、标题长度、简介、标签和封面。提交后只根据实际平台反馈报告结果；超时或状态不明时先在微博后台确认原作品，不重复上传。
