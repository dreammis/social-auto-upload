# Bilibili CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Bilibili 补齐和抖音、快手同层级的 `sau` CLI、自动更新 `biliup` 的运行时机制、对应 skill，以及完整文档与上游致谢说明。

**Architecture:** 保持轻量，不新建大而全框架。新增一个 Bilibili 运行时模块负责检查 GitHub Release、下载/更新 `biliup`、执行命令；`sau_cli.py` 仅补 `bilibili` 子命令和参数映射；skill、example、README/CLI/install/update 文档按现有 Douyin/Kuaishou 结构对齐。

**Tech Stack:** Python 3.10+, `requests`, `argparse`, `asyncio`, `subprocess`, `pathlib`, `unittest`, GitHub Releases, existing `biliup` integration

---

## File Structure

### New files

- `uploader/bilibili_uploader/runtime.py`
  - Bilibili 运行时入口
  - 负责 `biliup` 自动检查、自动下载、自动更新、执行命令
- `tests/__init__.py`
  - 测试包初始化
- `tests/test_bilibili_runtime.py`
  - 测试自动更新、下载、缓存复用、执行器行为
- `tests/test_sau_bilibili_cli.py`
  - 测试 `sau bilibili` parser 和 dispatch 行为
- `skills/bilibili-upload/SKILL.md`
  - Bilibili CLI skill 主说明
- `skills/bilibili-upload/references/runtime-requirements.md`
  - 运行前提和自动下载说明
- `skills/bilibili-upload/references/cli-contract.md`
  - `sau bilibili ...` 命令契约
- `skills/bilibili-upload/references/troubleshooting.md`
  - 常见问题与排障
- `skills/bilibili-upload/scripts/examples/bilibili_commands.ps1`
  - PowerShell 示例命令
- `skills/bilibili-upload/scripts/examples/bilibili_commands.sh`
  - shell 示例命令
- `skills/bilibili-upload/scripts/examples/bilibili_cli_template.py`
  - Python 调用模板

### Modified files

- `sau_cli.py`
  - 补 `bilibili` 子命令
  - 复用现有 `resolve_account_file()`、`parse_tags()`、`parse_schedule()`
- `examples/get_bilibili_cookie.py`
  - 对齐新的 `sau bilibili login` 用法
- `examples/upload_video_to_bilibili.py`
  - 对齐新的 CLI/账号文件约定
- `README.md`
  - 补 Bilibili CLI 用法、自动下载说明、致谢说明
- `docs/CLI.md`
  - 补 `sau bilibili login/check/upload-video`
- `docs/install.md`
  - 补 Bilibili 自动下载/首次运行说明
- `docs/update.md`
  - 补 Bilibili 自动更新行为说明

## Task 1: Bilibili 自动更新运行时

**Files:**
- Create: `uploader/bilibili_uploader/runtime.py`
- Create: `tests/__init__.py`
- Create: `tests/test_bilibili_runtime.py`

- [ ] **Step 1: 写 Bilibili 运行时测试**

使用 `unittest`，覆盖这些最小路径：

```python
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from uploader.bilibili_uploader.runtime import (
    build_biliup_runtime_path,
    ensure_biliup_binary,
    run_biliup_command,
)


class BiliupRuntimeTests(unittest.TestCase):
    def test_build_biliup_runtime_path_returns_platform_path(self):
        path = build_biliup_runtime_path("Windows")
        self.assertTrue(str(path).endswith("biliup.exe"))

    @patch("uploader.bilibili_uploader.runtime.fetch_latest_release")
    def test_ensure_biliup_binary_downloads_when_missing(self, mock_release):
        mock_release.return_value = {
            "tag_name": "v1.0.0",
            "asset_url": "https://example.invalid/biliup.exe",
            "asset_name": "biliup.exe",
        }
        with patch("uploader.bilibili_uploader.runtime.download_biliup_asset") as mock_download:
            ensure_biliup_binary(force_check=True)
        mock_download.assert_called_once()

    @patch("uploader.bilibili_uploader.runtime.fetch_latest_release")
    def test_ensure_biliup_binary_reuses_local_when_up_to_date(self, mock_release):
        mock_release.return_value = {
            "tag_name": "v1.0.0",
            "asset_url": "https://example.invalid/biliup.exe",
            "asset_name": "biliup.exe",
        }
        with patch("uploader.bilibili_uploader.runtime.read_local_biliup_version", return_value="v1.0.0"):
            with patch("uploader.bilibili_uploader.runtime.download_biliup_asset") as mock_download:
                ensure_biliup_binary(force_check=True)
        mock_download.assert_not_called()

    @patch("uploader.bilibili_uploader.runtime.subprocess.run")
    def test_run_biliup_command_returns_completed_process(self, mock_run):
        mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")
        result = run_biliup_command(["login"])
        self.assertEqual(result.returncode, 0)
```

- [ ] **Step 2: 运行测试，确认先失败**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_bilibili_runtime -v
```

Expected:

- 因为 `uploader.bilibili_uploader.runtime` 还不存在而失败

- [ ] **Step 3: 写最小运行时实现**

在 `uploader/bilibili_uploader/runtime.py` 里先补这些最小函数：

```python
def get_biliup_runtime_root() -> Path: ...
def build_biliup_runtime_path(system_name: str | None = None) -> Path: ...
def fetch_latest_release() -> dict: ...
def read_local_biliup_version() -> str | None: ...
def write_local_biliup_version(version: str) -> None: ...
def download_biliup_asset(release: dict, destination: Path) -> Path: ...
def ensure_biliup_binary(force_check: bool = True) -> Path: ...
def run_biliup_command(arguments: list[str]) -> subprocess.CompletedProcess[str]: ...
```

约束：

- 不引入复杂 manifest
- 直接面向 GitHub Release 最新版本
- 本地只保存当前版本字符串和二进制
- 保持简单的路径/网络/替换逻辑

- [ ] **Step 4: 再跑运行时测试，确认通过**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_bilibili_runtime -v
```

Expected:

- 所有 `BiliupRuntimeTests` 通过

- [ ] **Step 5: 提交这一小步**

```powershell
git add uploader/bilibili_uploader/runtime.py tests/__init__.py tests/test_bilibili_runtime.py
git commit -m "feat: add biliup runtime bootstrap"
```

## Task 2: 接入 `sau bilibili` CLI

**Files:**
- Modify: `sau_cli.py`
- Create: `tests/test_sau_bilibili_cli.py`
- Reference: `uploader/bilibili_uploader/main.py`
- Reference: `utils/constant.py`

- [ ] **Step 1: 写 CLI parser 和 dispatch 测试**

在 `tests/test_sau_bilibili_cli.py` 中覆盖：

```python
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import sau_cli


class BilibiliCliTests(unittest.TestCase):
    def test_build_parser_accepts_bilibili_login(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["bilibili", "login", "--account", "creator"])
        self.assertEqual(args.platform, "bilibili")
        self.assertEqual(args.action, "login")

    def test_build_parser_requires_tid_for_upload_video(self):
        parser = sau_cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "bilibili", "upload-video",
                "--account", "creator",
                "--file", "demo.mp4",
                "--title", "hello",
                "--desc", "hello",
            ])

    def test_dispatch_bilibili_check_prints_valid(self):
        args = Namespace(platform="bilibili", action="check", account="creator")
        with patch("sau_cli.check_bilibili_account", new=AsyncMock(return_value=True)):
            code = asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(code, 0)
```

- [ ] **Step 2: 运行测试，确认先失败**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sau_bilibili_cli -v
```

Expected:

- 因为 `sau_cli.py` 里还没有 `bilibili` parser/dispatch 分支而失败

- [ ] **Step 3: 在 `sau_cli.py` 中补 Bilibili 请求模型和命令**

只做最小接入，保持和 Douyin/Kuaishou 同风格：

```python
@dataclass(slots=True)
class BilibiliVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tid: int
    tags: list[str]
    publish_date: datetime | int
    debug: bool = True


async def login_bilibili_account(account_name: str) -> dict: ...
async def check_bilibili_account(account_name: str) -> bool: ...
async def upload_bilibili_video(request: BilibiliVideoUploadRequest) -> Path: ...
```

Parser 最小要求：

- `sau bilibili login --account <name>`
- `sau bilibili check --account <name>`
- `sau bilibili upload-video --account ... --file ... --title ... --desc ... --tid ... [--tags] [--schedule]`

Dispatch 最小要求：

- 和其他平台一样输出 `valid` / `invalid`
- 上传成功后打印简洁摘要

- [ ] **Step 4: 复用现有 B 站参数语义**

在 Bilibili wrapper 中直接沿用现有工程概念：

- `tid` 必填
- `tags` 用现有 `parse_tags()`
- `schedule` 沿用现有 `parse_schedule()`
- `account` 仍通过 `resolve_account_file("bilibili", account_name)` 得到项目内账号路径

- [ ] **Step 5: 再跑 CLI 测试，确认通过**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sau_bilibili_cli -v
```

Expected:

- `BilibiliCliTests` 通过

- [ ] **Step 6: 做一次联测**

Run:

```powershell
.\.venv\Scripts\python.exe sau_cli.py bilibili --help
.\.venv\Scripts\python.exe sau_cli.py bilibili upload-video --help
```

Expected:

- 能看到 `login` / `check` / `upload-video`
- `upload-video` 中 `--tid` 显示为必填

- [ ] **Step 7: 提交这一小步**

```powershell
git add sau_cli.py tests/test_sau_bilibili_cli.py
git commit -m "feat: add bilibili cli commands"
```

## Task 3: 补 skill 和 example

**Files:**
- Create: `skills/bilibili-upload/SKILL.md`
- Create: `skills/bilibili-upload/references/runtime-requirements.md`
- Create: `skills/bilibili-upload/references/cli-contract.md`
- Create: `skills/bilibili-upload/references/troubleshooting.md`
- Create: `skills/bilibili-upload/scripts/examples/bilibili_commands.ps1`
- Create: `skills/bilibili-upload/scripts/examples/bilibili_commands.sh`
- Create: `skills/bilibili-upload/scripts/examples/bilibili_cli_template.py`
- Modify: `examples/get_bilibili_cookie.py`
- Modify: `examples/upload_video_to_bilibili.py`

- [ ] **Step 1: 参考 Douyin/Kuaishou skill 结构搭出 Bilibili skill**

要求：

- `SKILL.md` 风格和现有两个 skill 对齐
- 默认优先用 `sau bilibili ...`
- 明确写“程序会自动准备 `biliup`”

- [ ] **Step 2: 写示例命令文件**

示例命令至少包括：

```powershell
sau bilibili login --account creator
sau bilibili check --account creator
sau bilibili upload-video --account creator --file .\videos\demo.mp4 --title "demo" --desc "demo" --tid 249 --tags 足球,测试
```

- [ ] **Step 3: 修改本地 example**

让以下 example 明确转向新入口或新约定：

- `examples/get_bilibili_cookie.py`
- `examples/upload_video_to_bilibili.py`

要求：

- 不再让用户手动猜 `biliup.exe` 路径
- 明确说明现在推荐走 `sau bilibili ...`
- 继续保留 `VideoZoneTypes` 的使用示例

- [ ] **Step 4: 做一次文件级自检**

Run:

```powershell
Get-ChildItem skills\bilibili-upload -Recurse
Get-Content examples\get_bilibili_cookie.py
Get-Content examples\upload_video_to_bilibili.py
```

Expected:

- Bilibili skill 目录完整
- example 内容已切到新的 CLI/说明

- [ ] **Step 5: 提交这一小步**

```powershell
git add skills/bilibili-upload examples/get_bilibili_cookie.py examples/upload_video_to_bilibili.py
git commit -m "feat: add bilibili upload skill"
```

## Task 4: 补文档与上游致谢

**Files:**
- Modify: `README.md`
- Modify: `docs/CLI.md`
- Modify: `docs/install.md`
- Modify: `docs/update.md`

- [ ] **Step 1: 在 README 中补 Bilibili CLI 用法**

至少写清：

- `sau bilibili login`
- `sau bilibili check`
- `sau bilibili upload-video`
- 自动下载/自动更新 `biliup`

- [ ] **Step 2: 在 CLI 文档中补命令契约**

把 Bilibili 一节写成和 Douyin/Kuaishou 同风格：

- 参数表
- `tid` 必填
- `schedule` 的行为

- [ ] **Step 3: 在安装/更新文档中写清自动下载机制**

至少补这些说明：

- 用户不需要自己安装 `biliup`
- 第一次运行会自动下载
- 后续运行会自动检查更新

- [ ] **Step 4: 在文档中加入对上游项目的感谢与借用说明**

至少在 README 中补一段明确说明：

- Bilibili 能力基于 `biliup`
- 感谢/借用上游项目
- 给出项目地址

建议文案：

```markdown
## 致谢

本项目的 Bilibili 上传能力基于开源项目 `biliup` 的能力进行接入与封装。
感谢 `biliup` 项目及其贡献者提供的基础能力：

- https://github.com/biliup/biliup
```

- [ ] **Step 5: 做一次文档核对**

Run:

```powershell
Get-Content README.md | Select-String -Pattern "bilibili|biliup|致谢" -Context 1,2
Get-Content docs\CLI.md | Select-String -Pattern "bilibili" -Context 1,3
Get-Content docs\install.md | Select-String -Pattern "bilibili|biliup" -Context 1,2
Get-Content docs\update.md | Select-String -Pattern "bilibili|biliup" -Context 1,2
```

Expected:

- README、CLI、install、update 都出现 Bilibili 新内容
- README 里有明确的上游致谢

- [ ] **Step 6: 跑最终验证**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_bilibili_runtime tests.test_sau_bilibili_cli -v
.\.venv\Scripts\python.exe sau_cli.py bilibili --help
.\.venv\Scripts\python.exe sau_cli.py bilibili upload-video --help
```

Expected:

- 单元测试通过
- Bilibili CLI 帮助可用
- `upload-video` 显示必填 `--tid`

- [ ] **Step 7: 提交收尾**

```powershell
git add README.md docs/CLI.md docs/install.md docs/update.md
git commit -m "docs: add bilibili cli guidance and attribution"
```
