---
name: douyin-upload
description: 使用已安装的 sau CLI 登录、核验并发布抖音视频或图文。适用于已有 social-auto-upload 环境。
---

# 抖音发布

调用现有 CLI；只有命令失败时才查故障排查参考。

```powershell
sau douyin login --account <name>
sau douyin check --account <name>
sau douyin upload-video --account <name> --file videos/demo.mp4 --title "标题" --desc "正文" --tags 生活,分享
sau douyin upload-note --account <name> --images images/1.png images/2.png --title "标题" --note "正文" --tags 生活,分享
```

视频字段为 `title + desc + tags`；图文字段为 `title + note + tags`。只有用户明确要求定时才传 `--schedule`。登录二维码需要用户在本地浏览器完成。

详细参数见 [CLI 契约](references/cli-contract.md)，环境见 [运行前提](references/runtime-requirements.md)，失败后查 [故障排查](references/troubleshooting.md)。
