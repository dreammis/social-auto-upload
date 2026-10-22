---
name: hupu-upload
description: 使用 social-auto-upload 的 `sau hupu` 登录虎扑并发布视频，可指定封面。Use when 用户要向虎扑发布视频或检查虎扑账号状态。
license: MIT-0
slug: social-auto-upload-hupu-upload
displayName: 虎扑视频发布
version: 1.0.0
summary: 登录虎扑并发布视频，可指定封面。
---

# 虎扑视频发布

调用现有 CLI，不另写网页上传流程。账号名是本地会话别名。

```powershell
sau hupu login --account creator --headed
sau hupu check --account creator
sau hupu upload-video --account creator --file videos/demo.mp4 --title "标题" --desc "简介" --tags 虎扑,测试 --thumbnail covers/demo.png
```

当前仅支持视频，不支持图文和定时发布。标题长度为 4–40 个字。登录可能需要用户在浏览器中完成 QQ 或手机号验证；需要看见页面时保留 `--headed`。封面参数 `--thumbnail` 可省略。

发布前核对账号、视频、标题长度、简介、标签和封面。结果不明确时先查虎扑后台，不直接重发。
