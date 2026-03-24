# CLI 使用说明

项目现在提供一个更直接的抖音 CLI 入口，默认推荐使用 `sau`。

实现说明：

- `sau_cli.py` 是当前 CLI 的主入口和唯一主要实现文件

## 抖音 CLI 子命令

```bash
sau douyin login --account creator
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

仓库内的轻量 skill 源位于 `skills/douyin-cli/`，后续维护 CLI 时应优先以这里和 `social_auto_upload/` 下的新入口为准。
