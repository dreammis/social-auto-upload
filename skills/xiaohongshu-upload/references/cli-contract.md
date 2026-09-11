# 小红书 CLI 契约

这个 skill 默认假设当前环境已经安装并可调用 `sau` 命令。

## 命令列表

### 登录

```bash
sau xiaohongshu login --account <account>
```

- 必填参数:
  - `--account`
- 作用:
  - 启动小红书登录流程，为指定账号生成或刷新 cookie 文件
  - 如果登录过程中生成本地二维码图片，agent 应优先直接把图片展示/发送给用户扫码，而不是只回传路径
- 账号说明:
  - `--account` 传的是用户自定义的 `account_name`，不是固定只能叫 `creator`
  - 一个 `account_name` 对应一个账号文件，可用于多账号隔离和并发任务

### 校验 cookie

```bash
sau xiaohongshu check --account <account>
```

- 必填参数:
  - `--account`
- 预期输出:
  - `valid`：cookie 可用
  - `invalid`：cookie 缺失或已失效

### 上传视频

```bash
sau xiaohongshu upload-video \
  --account <account> \
  --file <video-path> \
  --title "<title>" \
  [--desc "<description>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"] \
  [--thumbnail <image-path>] \
  [--visibility private|public] \
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
  - `--debug`
  - `--headless`
  - `--headed`

### 改已有视频

```bash
sau xiaohongshu update-video \
  --account <account> \
  --visibility public|private \
  [--title "<existing-title>"] \
  [--id <note-id>] \
  [--debug] \
  [--headless | --headed]
```

- 必填参数:
  - `--account`
  - `--visibility`
  - `--title` 或 `--id` 至少一个
- 作用:
  - 打开创作者后台编辑页，改已有视频笔记的可见性
  - 不重新上传视频文件，也不会再发一条
- `--id` 来自编辑页 URL：`/publish/update?id=<note-id>&noteType=video`
- `--title` 按笔记管理页卡片标题精确匹配；匹配到多条则失败

### 上传图文

```bash
sau xiaohongshu upload-note \
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

- Video uploads default to `--visibility private` (only-self). Use public only after the user has reviewed and explicitly approved release. Private selection is checked before the final submission; failure aborts without clicking Publish.
- Changing an already submitted note uses `update-video`, not a second `upload-video`.
- A video submission is attempted once. An uncertain success response must be checked in note management before retrying, to avoid duplicate posts.
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
