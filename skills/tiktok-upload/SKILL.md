---
name: tiktok-upload
description: 使用仓库现有 Patchright/Playwright Chrome 上传器登录并发布 TikTok 视频。Use when 用户要发布 TikTok 视频，且当前环境可访问本仓库及其本地 Chrome 配置。
license: MIT-0
slug: social-auto-upload-tiktok-upload
displayName: TikTok 视频发布
version: 1.0.0
summary: 使用仓库 Chrome 上传器登录并发布 TikTok 视频。
---

# TikTok 视频发布

TikTok 当前没有 `sau tiktok` 命令。使用仓库的 `uploader/tk_uploader/main_chrome.py`，不能虚构 CLI 参数。运行前确认仓库依赖、`conf.py` 中的 Chrome 配置及用户提供的视频路径。

账号会话存放在 `cookies/tk_uploader/account.json`。首次登录可参考 `examples/get_tk_cookie.py`，在 TikTok 页面由用户本人完成登录。不要读取、复制或提交 cookie 文件。

单条视频优先按下面的仓库 API 流程执行，先用 `publish_date=0` 表示立即发布：

```python
import asyncio
from pathlib import Path
from conf import BASE_DIR
from uploader.tk_uploader.main_chrome import TiktokVideo, tiktok_setup

account_file = Path(BASE_DIR) / "cookies" / "tk_uploader" / "account.json"
video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
asyncio.run(tiktok_setup(str(account_file), handle=True))
app = TiktokVideo("标题", str(video_file), ["标签"], 0, str(account_file))
asyncio.run(app.main())
```

`TiktokVideo` 没有独立简介参数。定时发布需传入明确的 `datetime`，不要自行推算时间。仓库中的 `examples/upload_video_to_tiktok.py` 会批量处理目录下的 MP4、自动从文件提取标题/标签，并安排次日 16:00 发布；除非用户明确要求这些行为，不要直接运行该脚本。

每次发布前让用户确认账号、单条视频、标题、标签及立即/定时方式。页面布局或登录状态不符合预期时停止并报告；只有平台页面确认提交后才报告成功，未知结果先核查 TikTok Studio，不能直接重发。
