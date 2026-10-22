---
name: tencent-upload
description: 使用 social-auto-upload 的 `sau tencent` 登录视频号并发布或定时发布视频、保存草稿。Use when 用户要向微信视频号发布视频或检查视频号账号状态。
license: MIT-0
slug: social-auto-upload-tencent-upload
displayName: 微信视频号发布
version: 1.0.0
summary: 登录视频号并发布、定时发布或保存视频草稿。
---

# 视频号发布

调用现有 `sau tencent` CLI，不另写网页上传流程。先确认 `sau tencent --help`；账号名是本地会话别名。

```powershell
sau tencent login --account creator
sau tencent check --account creator
sau tencent upload-video --account creator --file videos/demo.mp4 --title "标题" --desc "简介" --tags 视频号,测试
```

视频号仅支持视频发布。可选参数包括 `--schedule "YYYY-MM-DD HH:MM"`、`--draft`、`--collection`、`--short-title`、`--category`、`--thumbnail-landscape` 和 `--thumbnail-portrait`。`--thumbnail` 是竖版封面的兼容参数。合集必须已存在。

登录和上传依赖浏览器会话。登录若生成二维码，直接展示二维码图片供用户扫码；需要人工操作页面时使用 `--headed`。定时仅在用户给出明确时间时使用。`--draft` 只保存草稿，不代表发布。

发布前确认目标账号、视频、标题、简介、标签及立即发布/定时/草稿意图。只依据 CLI 输出和平台页面确认结果，不把命令启动成功当成发布成功。完整参数以 `sau tencent upload-video --help` 为准。
