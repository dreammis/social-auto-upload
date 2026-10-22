---
name: youtube-upload
description: 使用 social-auto-upload 的 `sau youtube` 登录 YouTube 并上传、安排定时或设置视频可见范围。Use when 用户要向 YouTube 发布或定时发布视频，或检查 Google/YouTube 登录状态。
license: MIT-0
slug: social-auto-upload-youtube-upload
displayName: YouTube 视频发布
version: 1.0.0
summary: 使用 sau 登录 YouTube 并上传或定时发布视频。
---

# YouTube 视频发布

调用现有 `sau youtube` CLI。登录在浏览器中完成 Google 账号登录，不使用二维码；账号名是本地会话别名。

```powershell
sau youtube login --account creator
sau youtube check --account creator
sau youtube upload-video --account creator --file videos/demo.mp4 --title "标题" --desc "简介" --tags tag1,tag2 --visibility public
```

标题最多 100 个字符。`--visibility` 可选 `public`、`unlisted`、`private`，默认 `public`；`--thumbnail` 指定封面，`--playlist` 指定已有播放列表。只有用户明确给出定时时间才传 `--schedule "YYYY-MM-DD HH:MM"`；该选项会使用 YouTube Studio 的 Schedule 状态，需核对页面显示的日期与时间。

发布前再次核对账号、视频、标题、说明、标签、可见范围及立即/定时意图。上传或发布遇到超时时先查 YouTube Studio 中的原视频，不盲目重传。上传成功不等于审核完成或公开视频已可播放。
