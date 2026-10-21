---
name: kuaishou-upload
description: 使用已安装的 sau CLI 登录、核验并发布快手视频或图文。适用于已有 social-auto-upload 环境。
---

# 快手发布

调用现有 CLI，不另写网页上传逻辑；命令失败后再查参考文档。

```powershell
sau kuaishou login --account <name>
sau kuaishou check --account <name>
sau kuaishou upload-video --account <name> --file videos/demo.mp4 --title "标题" --desc "正文" --tags 生活,分享
sau kuaishou upload-note --account <name> --images images/1.png images/2.png --title "标题" --note "正文" --tags 生活,分享
```

视频字段为 `title + desc + tags`；图文字段为 `title + note + tags`。只有用户明确要求定时才传 `--schedule`。登录二维码需要用户在本地浏览器完成。

详细参数和失败处理见 [CLI 契约](references/cli-contract.md)、[运行前提](references/runtime-requirements.md) 和 [故障排查](references/troubleshooting.md)。
