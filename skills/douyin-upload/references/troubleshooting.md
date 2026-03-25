# 故障排查

## 找不到 `sau` 命令

可以尝试以下方式：

```powershell
.\.venv\Scripts\Activate.ps1
sau douyin --help
```

```powershell
.\.venv\Scripts\sau.exe douyin --help
```

```bash
uv run sau douyin --help
```

如果当前环境还没有安装项目：

```bash
uv pip install -e .
```

## cookie 无效或已过期

先检查 cookie 状态：

```bash
sau douyin check --account <account>
```

如果无效，就重新登录：

```bash
sau douyin login --account <account>
```

## 无头登录二维码处理

如果用户无法使用终端二维码输出：

- 查找 CLI 打印出来的临时二维码图片
- agent 不要只把图片路径回给用户
- agent 应优先直接把本地二维码图片展示/发送给用户扫码

如果终端二维码显示不正常，优先使用保存下来的图片路径，而不是反复尝试随机的终端设置。

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

## 图片限制

对 `upload-note` 来说：

- 不支持 GIF
- 最多 35 张图片

如果超出这些限制，先减少图片数量或替换文件格式，再重试。

## 定时发布

时间格式使用：

```text
YYYY-MM-DD HH:MM
```

如果不需要定时发布，去掉 `--schedule` 即可改为立即发布。
