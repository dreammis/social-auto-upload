# CLI 使用说明

项目现在提供一个更直接的抖音 CLI 入口，默认推荐使用 `sau`。

实现说明：

- `sau_cli.py` 是当前 CLI 的主入口和唯一主要实现文件
- `sau.exe` 是安装后在 Windows 虚拟环境里自动生成的命令入口，本质上还是调用 `sau_cli.py`
- 如果需要给 OpenClaw、Codex 等 agent 使用，可参考仓库内 skill：`skills/douyin-upload/`

## 安装 CLI 入口

如果你希望直接使用 `sau` 命令，而不是手动执行 `python sau_cli.py`，先在项目根目录安装一次：

```bash
uv pip install -e .
```

安装后就可以直接使用：

```bash
sau douyin --help
```

## 安装 patchright 浏览器

Windows 下推荐先指定镜像，再安装 Chromium：

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

## 抖音 CLI 子命令

```bash
sau douyin login --account creator
sau douyin login --account creator --headless
sau douyin check --account creator
sau douyin upload-video --account creator --file videos/demo.mp4 --title "示例标题" --tags 运动,训练
sau douyin upload-note --account creator --images videos/1.png videos/2.png --note "图文示例" --tags 图文,测试
```

## 定时发布

视频和图文都支持 `--schedule`。只要传了 `--schedule`，CLI 就会自动切换到 `scheduled` 发布策略；不传则默认立即发布。

```bash
sau douyin upload-video --account creator --file videos/demo.mp4 --title "示例标题" --schedule "2026-03-24 21:30"
sau douyin upload-note --account creator --images videos/1.png videos/2.png --note "图文示例" --schedule "2026-03-24 21:30"
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

## 视频上传参数

```bash
--file videos/demo.mp4
--title "示例标题"
--tags 运动,训练
--thumbnail videos/demo.png
--product-link https://example.com/item
--product-title 示例商品
```

## 图文上传参数

```bash
--images videos/1.png videos/2.png videos/3.png
--note "图文内容"
--tags 图文,测试
```

图文上传当前限制：

- 最多 35 张图片
- 不支持 GIF

后续维护 CLI 时，优先看 `sau_cli.py` 和 `uploader/`。
