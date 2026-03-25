# CLI 使用说明

项目现在提供一个统一的 CLI 入口 `sau`，当前主线已经接入：

- `douyin`
- `kuaishou`
- `xiaohongshu`
- `bilibili`

实现说明：

- `sau_cli.py` 是当前 CLI 的主入口和唯一主要实现文件
- `sau.exe` 是安装后在 Windows 虚拟环境里自动生成的命令入口，本质上还是调用 `sau_cli.py`
- 如果需要给 OpenClaw、Codex 等 agent 使用，可参考仓库内 skill：
  - `skills/douyin-upload/`
  - `skills/kuaishou-upload/`
  - `skills/xiaohongshu-upload/`
  - `skills/bilibili-upload/`

## 安装 CLI 入口

如果你希望直接使用 `sau` 命令，而不是手动执行 `python sau_cli.py`，先在项目根目录安装一次：

```bash
uv pip install -e .
```

安装后就可以直接使用：

```bash
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
```

## 安装 patchright 浏览器

Windows 下推荐先指定镜像，再安装 Chromium：

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

## 抖音 CLI 子命令

```bash
sau douyin login --account <account_name>
sau douyin login --account <account_name> --headless
sau douyin check --account <account_name>
sau douyin upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 运动,训练
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文示例" --tags 图文,测试
```

## 快手 CLI 子命令

```bash
sau kuaishou login --account <account_name>
sau kuaishou check --account <account_name>
sau kuaishou upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 运动,训练
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文示例" --tags 图文,测试
```

## 小红书 CLI 子命令

```bash
sau xiaohongshu login --account <account_name>
sau xiaohongshu check --account <account_name>
sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 小红书,视频
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文示例" --tags 图文,测试
```

## Bilibili CLI 子命令

```bash
sau bilibili login --account <account_name>
sau bilibili check --account <account_name>
sau bilibili upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tid 249 --tags 足球,测试
```

补充说明：

- `creator` 之类的名字只是示例值，真正传的是用户自定义的 `account_name`
- 一个 `account_name` 对应一个账号文件，可以准备多个账号并发使用
- 浏览器平台统一元数据约定：
- 视频使用 `title + desc + tags`
- 图文使用 `title + note + tags`
- `sau bilibili ...` 会自动准备 `biliup`
- 如果本地没有 `biliup`，第一次运行会自动下载
- 如果上游 GitHub Release 有更新，运行时会先自动更新
- `sau bilibili login --account <name>` 建议由用户自己在本地真实终端里执行；如果终端里的二维码显示不完整，可直接打开当前目录下的 `qrcode.png` 扫码

## 登录二维码说明

- 抖音、快手、小红书登录过程中，CLI / uploader 可能会生成临时二维码图片
- 对普通用户来说，可以直接打开该图片扫码
- 对可操作本地文件的 agent 来说，不要只把图片路径告诉用户
- 这类二维码图片本身就是给用户扫码的，agent 应优先直接展示/发送本地图片给用户
- Bilibili 当前不走这套本地二维码图片托管链路，登录按上面的 Bilibili CLI 说明处理即可

## 定时发布

抖音、快手、小红书的图文和视频上传，以及 Bilibili 的视频上传都支持 `--schedule`。只要传了 `--schedule`，CLI 就会自动切换到对应平台的定时发布策略；不传则默认立即发布。

```bash
sau douyin upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --schedule "2026-03-24 21:30"
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文示例" --schedule "2026-03-24 21:30"
sau kuaishou upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --schedule "2026-03-24 21:30"
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文示例" --schedule "2026-03-24 21:30"
sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --schedule "2026-03-24 21:30"
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文示例" --schedule "2026-03-24 21:30"
sau bilibili upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tid 249 --schedule "2026-03-24 21:30"
```

## 运行时参数

CLI 将 `debug` 和 `headless` 拆成了两个独立维度：

```bash
--debug
--headless
--headed
```

- `--debug`: 打开调试行为，例如失败时保留更多调试信息
- `--headless`: 无头模式运行
- `--headed`: 有头模式运行

如果都不传，CLI 当前默认按 `headless=True` 运行。

补充：

- 抖音和快手的 CLI 默认都是无头模式
- 如果用户明确要求可见浏览器窗口，或确实需要人工看页面，再显式传 `--headed`

## 视频上传参数

```bash
--file videos/demo.mp4
--title "示例标题"
--desc "示例简介"
--tags 运动,训练
--thumbnail videos/demo.png
```

抖音额外支持：

```bash
--product-link https://example.com/item
--product-title 示例商品
```

Bilibili 额外要求：

```bash
--tid 249
```

- `--tid` 第一版是必填
- `--tags` 会映射到 `biliup upload --tag`
- `--schedule` 会映射到 Bilibili 所需的时间戳参数

## 图文上传参数

```bash
--images videos/1.png videos/2.png videos/3.png
--title "图文标题"
--note "图文内容"
--tags 图文,测试
```

图文上传当前限制：

- 抖音：最多 35 张图片，不支持 GIF
- 快手：支持多张图片，建议传真实不同文件，不要把同一路径重复多次
- 小红书：支持多张图片，正文 `--note` 可选，但 `--title` 建议始终显式传入

后续维护 CLI 时，优先看 `sau_cli.py`、`uploader/` 和 `skills/`。
