# 运行前提

这个 skill 默认假设当前环境已经具备：

- 已安装 `social-auto-upload`
- 可以调用 `sau` 命令，或至少有等效调用方式
- 已为 `patchright` 安装 Chromium

## 推荐安装方式

在项目根目录执行：

```bash
uv pip install -e .
```

## 安装 patchright 浏览器

Windows PowerShell：

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

Linux / macOS（bash / zsh）：

```bash
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium
```

## 常见调用方式

### 如果 `sau` 已经在 PATH 中

```bash
sau douyin --help
```

### 如果虚拟环境存在，但还没有激活

PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
sau douyin --help
```

### 如果你想直接调用可执行文件

PowerShell：

```powershell
.\.venv\Scripts\sau.exe douyin --help
```

### 如果你更倾向于使用 uv

```bash
uv run sau douyin --help
```

## 无头和有头模式

- 使用 `--headless` 表示无头模式
- 使用 `--headed` 表示有头模式
- 如果用户明确要求无头登录，也要预期 CLI 会通过控制台输出或临时图片路径提供二维码相关提示
- 如果登录过程中已经生成了本地二维码图片，agent 应优先直接把图片展示/发送给用户扫码，不要只告诉用户图片路径
