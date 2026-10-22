---
name: baijiahao-upload
description: 使用 social-auto-upload 的 `sau baijiahao` 登录百家号、检查账号并发布视频。Use when 用户要向百家号发布视频或核验百家号登录状态。
license: MIT-0
slug: social-auto-upload-baijiahao-upload
displayName: 百家号视频发布
version: 1.0.0
summary: 登录百家号并发布视频，支持封面和合集。
---

# 百家号视频发布

调用现有 CLI，不另写上传流程。账号名是本地会话别名；发布前先查看 `sau baijiahao upload-video --help`。

```powershell
sau baijiahao login --account creator
sau baijiahao check --account creator
sau baijiahao upload-video --account creator --file videos/demo.mp4 --title "标题" --desc "简介" --tags 百家号,测试
```

当前仅支持视频，不支持图文和定时发布。可选 `--thumbnail` 指定封面，`--collection` 指定已有合集。先完成百度账号登录并保存会话；登录出现二维码时把二维码图片展示给用户。

发布前核对账号、素材、标题、文案和标签。只有命令及平台提供的本次提交证据才表示成功；超时或状态不明时先去后台核查，不能直接重发。
