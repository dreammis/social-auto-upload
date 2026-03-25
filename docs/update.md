# 更新说明

这个文档分成两部分：

- `For Humans`：给正常使用仓库的人看
- `For AI Agents`：给能执行命令和自动排查的 agent 看

## For Humans

### 1. 拉取最新代码

```bash
git pull
```

如果你平时是切分支开发，请先确认当前所在分支。

### 2. 更新本地可编辑安装

如果仓库最近改了 CLI、入口脚本、依赖配置，建议重新执行：

```bash
uv pip install -e .
```

### 3. 如有需要，更新浏览器依赖

当前主线使用 `patchright`。

Windows PowerShell：

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

Linux / macOS：

```bash
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium
```

### 4. 更新后自检

建议至少检查：

```bash
sau --help
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
sau douyin check --account your_account
sau kuaishou check --account your_account
sau xiaohongshu check --account your_account
sau bilibili check --account your_account
```

如果你在使用 skill，也建议同步看一下：

- `skills/douyin-upload/SKILL.md`
- `skills/kuaishou-upload/SKILL.md`
- `skills/xiaohongshu-upload/SKILL.md`
- `skills/bilibili-upload/SKILL.md`
- `docs/CLI.md`

## For AI Agents

如果你是 agent，更新仓库后建议按下面顺序做最小验证：

1. 拉取最新代码：

```bash
git pull
```

2. 重新同步本地安装：

```bash
uv pip install -e .
```

3. 如需浏览器驱动，更新 `patchright` Chromium

4. 重新验证 CLI：

```bash
sau --help
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
```

5. 如果任务是浏览器平台链路，再继续验证：

```bash
sau douyin check --account test
sau kuaishou check --account test
sau xiaohongshu check --account test
sau bilibili check --account test
```

6. 如果用户依赖 skill，再检查这些路径是否仍存在且契约没变：

- `skills/douyin-upload/SKILL.md`
- `skills/douyin-upload/references/cli-contract.md`
- `skills/douyin-upload/references/runtime-requirements.md`
- `skills/kuaishou-upload/SKILL.md`
- `skills/kuaishou-upload/references/cli-contract.md`
- `skills/kuaishou-upload/references/runtime-requirements.md`
- `skills/xiaohongshu-upload/SKILL.md`
- `skills/xiaohongshu-upload/references/cli-contract.md`
- `skills/xiaohongshu-upload/references/runtime-requirements.md`
- `skills/bilibili-upload/SKILL.md`
- `skills/bilibili-upload/references/cli-contract.md`
- `skills/bilibili-upload/references/runtime-requirements.md`

### 对 agent 的额外说明

- 优先相信 `pyproject.toml`，不要把 `requirements.txt` 视为当前主线真相
- 当前 README 只做总览，安装和更新以 `docs/install.md`、`docs/update.md` 为准
- Web 相关内容属于历史路径，见 `docs/legacy-web.md`
- 如果更新后的登录流程输出了本地二维码图片，agent 应直接把图片展示/发送给用户扫码，不要只回传图片路径
- Bilibili 命令运行时会自动检查并更新 `biliup`
- Bilibili 登录当前仍建议让用户自己在本地真实终端里执行；如果二维码显示不完整，可让用户直接打开 `qrcode.png` 扫码
