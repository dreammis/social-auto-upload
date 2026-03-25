# 抖音 CLI 契约

这个 skill 默认假设当前环境已经安装并可调用 `sau` 命令。

## 命令列表

### 登录

```bash
sau douyin login --account <account>
```

- 必填参数:
  - `--account`
- 作用:
  - 启动抖音登录流程，为指定账号生成或刷新 cookie 文件
  - 如果登录过程中生成本地二维码图片，agent 应优先直接把图片展示/发送给用户扫码，而不是只回传路径
- 账号说明:
  - `--account` 传的是用户自定义的 `account_name`，不是固定只能叫 `creator`
  - 一个 `account_name` 对应一个账号文件，可用于多账号隔离和并发任务

### 校验 cookie

```bash
sau douyin check --account <account>
```

- 必填参数:
  - `--account`
- 预期输出:
  - `valid`：cookie 可用
  - `invalid`：cookie 缺失或已失效

### 上传视频

```bash
sau douyin upload-video \
  --account <account> \
  --file <video-path> \
  --title "<title>" \
  [--desc "<description>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"] \
  [--thumbnail <image-path>] \
  [--product-link <url>] \
  [--product-title "<title>"] \
  [--debug] \
  [--headless | --headed]
```

- 必填参数:
  - `--account`
  - `--file`
  - `--title`
- 可选参数:
  - `--desc`
  - `--tags`
  - `--schedule`
  - `--thumbnail`
  - `--product-link`
  - `--product-title`
  - `--debug`
  - `--headless`
  - `--headed`

### 上传图文

```bash
sau douyin upload-note \
  --account <account> \
  --images <image-1> [image-2 ...] \
  --title "<title>" \
  [--note "<content>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"] \
  [--debug] \
  [--headless | --headed]
```

- 必填参数:
  - `--account`
  - `--images`
  - `--title`
- 可选参数:
  - `--note`
  - `--tags`
  - `--schedule`
  - `--debug`
  - `--headless`
  - `--headed`

## 发布策略

- 如果不传 `--schedule`，CLI 使用立即发布
- 如果传了 `--schedule`，CLI 自动切换为定时发布
- 时间格式为:

```text
YYYY-MM-DD HH:MM
```

## 额外说明

- `upload-video` 每次命令只支持一个视频文件
- `upload-note` 每次命令支持多张图片
- 视频描述字段统一使用 `--desc`
- 图文正文统一使用 `--note`
- `upload-note` 当前不支持 GIF
- `upload-note` 当前最多支持 35 张图片
