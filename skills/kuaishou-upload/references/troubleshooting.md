# 故障排查

## 找不到 `sau` 命令

可以尝试以下方式：

```powershell
.\.venv\Scripts\Activate.ps1
sau kuaishou --help
```

```powershell
.\.venv\Scripts\sau.exe kuaishou --help
```

```bash
uv run sau kuaishou --help
```

如果当前环境还没有安装项目：

```bash
uv pip install -e .
```

## cookie 无效或已过期

先检查 cookie 状态：

```bash
sau kuaishou check --account <account>
```

如果无效，就重新登录：

```bash
sau kuaishou login --account <account>
```

## 登录二维码问题

如果用户反馈二维码在终端里不好扫：

- 先优先使用 CLI / uploader 生成的本地二维码图片
- 只有用户明确需要可见浏览器窗口，或图片方案仍然不方便时，再切到 `--headed`
- 如果 CLI / uploader 已经生成临时二维码图片，agent 不要只回图片路径
- agent 应优先直接把本地二维码图片展示/发送给用户扫码
- 图片路径只作为补充信息

## 上传参数缺失

### 视频上传

最少需要：

- `--account`
- `--file`
- `--title`

### 图文上传

最少需要：

- `--account`
- `--images`
- `--title`

`--note` 当前是可选图文正文。

## 图文上传只有一张生效

如果用户一次传了多张图片，但页面只识别到一张，先确认：

- `--images` 里传的是不是真正不同的文件
- 不是同一路径重复多次

## 定时发布

时间格式使用：

```text
YYYY-MM-DD HH:MM
```

如果不需要定时发布，去掉 `--schedule` 即可改为立即发布。
