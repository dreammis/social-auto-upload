# Bilibili CLI 契约

这个 skill 默认假设当前环境已经安装并可调用 `sau` 命令。

## 命令列表

### 登录

```bash
sau bilibili login --account <account>
```

- 必填参数：
  - `--account`
- 作用：
  - 自动准备 `biliup`
  - 触发 Bilibili 登录流程

### 校验账号

```bash
sau bilibili check --account <account>
```

- 必填参数：
  - `--account`
- 预期输出：
  - `valid`
  - `invalid`

### 上传视频

```bash
sau bilibili upload-video \
  --account <account> \
  --file <video-path> \
  --title "<title>" \
  --desc "<desc>" \
  --tid <category-id> \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"]
```

- 必填参数：
  - `--account`
  - `--file`
  - `--title`
  - `--desc`
  - `--tid`
- 可选参数：
  - `--tags`
  - `--schedule`

## 额外说明

- `--tid` 第一版必须传
- `--tags` 使用逗号分隔
- `--schedule` 走 `sau` 统一时间格式
- 程序会自动准备和更新 `biliup`
