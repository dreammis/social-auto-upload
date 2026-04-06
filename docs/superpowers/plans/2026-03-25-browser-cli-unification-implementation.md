# Browser CLI Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为抖音、快手、小红书三家浏览器平台统一 `sau` CLI 契约，补齐小红书 CLI/skill，并把视频正文统一为 `desc`、图文正文统一为 `note`。

**Architecture:** 保持现有 `sau_cli.py` 单文件主入口，不引入新的 CLI 框架。`sau_cli.py` 负责 parser、request dataclass、dispatch 和账号文件解析；各平台 uploader 只做最小字段接线；skill、README、CLI/install/update 文档、examples 同步切到统一契约，避免对外同时暴露多套命名。

**Tech Stack:** Python 3.10+, `argparse`, `asyncio`, `dataclasses`, `pathlib`, `unittest`, existing Patchright-based uploaders, repository markdown docs

---

## File Structure

### New files

- `tests/test_sau_browser_cli.py`
  - 覆盖三家浏览器平台统一 CLI parser / dispatch / request 映射
- `skills/xiaohongshu-upload/SKILL.md`
  - 小红书 CLI skill 主说明
- `skills/xiaohongshu-upload/references/runtime-requirements.md`
  - 小红书运行前提
- `skills/xiaohongshu-upload/references/cli-contract.md`
  - 小红书 CLI 契约
- `skills/xiaohongshu-upload/references/troubleshooting.md`
  - 小红书排障文档
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.ps1`
  - PowerShell 示例命令
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.sh`
  - shell 示例命令
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_cli_template.py`
  - Python 命令模板

### Modified files

- `sau_cli.py`
  - 新增 `xiaohongshu` parser / dispatch
  - 改造抖音、快手 request dataclass 和参数模型
- `uploader/douyin_uploader/main.py`
  - 给视频接入 `desc`
  - 给图文接入 `title + note`
- `uploader/ks_uploader/main.py`
  - 给视频接入 `desc`
  - 给图文接入 `title + note`
- `uploader/xiaohongshu_uploader/main.py`
  - 只补 CLI 接线所需的最小字段适配
- `README.md`
  - 补小红书 CLI / skill，并统一三家参数说明
- `docs/CLI.md`
  - 统一三家浏览器平台命令契约
- `docs/install.md`
  - 补小红书 CLI 示例和统一参数说明
- `docs/update.md`
  - 补小红书检查项与 skill 路径
- `skills/douyin-upload/SKILL.md`
- `skills/douyin-upload/references/cli-contract.md`
- `skills/douyin-upload/scripts/examples/douyin_commands.ps1`
- `skills/douyin-upload/scripts/examples/douyin_commands.sh`
- `skills/douyin-upload/scripts/examples/douyin_cli_template.py`
- `skills/kuaishou-upload/SKILL.md`
- `skills/kuaishou-upload/references/cli-contract.md`
- `skills/kuaishou-upload/scripts/examples/kuaishou_commands.ps1`
- `skills/kuaishou-upload/scripts/examples/kuaishou_commands.sh`
- `skills/kuaishou-upload/scripts/examples/kuaishou_cli_template.py`
- `examples/get_xiaohongshu_cookie.py`
- `examples/upload_video_to_xiaohongshu.py`

## Task 1: 用测试锁定统一 CLI 契约

**Files:**
- Create: `tests/test_sau_browser_cli.py`
- Reference: `sau_cli.py`

- [ ] **Step 1: 写统一 CLI parser 测试**

在 `tests/test_sau_browser_cli.py` 里覆盖最小命令契约：

```python
import asyncio
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import sau_cli


class BrowserCliParserTests(unittest.TestCase):
    def test_build_parser_accepts_xiaohongshu_login(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["xiaohongshu", "login", "--account", "creator"])
        self.assertEqual(args.platform, "xiaohongshu")
        self.assertEqual(args.action, "login")

    def test_douyin_upload_video_accepts_desc(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args([
            "douyin", "upload-video",
            "--account", "creator",
            "--file", "demo.mp4",
            "--title", "标题",
            "--desc", "视频简介",
        ])
        self.assertEqual(args.desc, "视频简介")

    def test_kuaishou_upload_note_accepts_title_and_note(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args([
            "kuaishou", "upload-note",
            "--account", "creator",
            "--images", "1.png",
            "--title", "图文标题",
            "--note", "图文正文",
        ])
        self.assertEqual(args.title, "图文标题")
        self.assertEqual(args.note, "图文正文")
```

- [ ] **Step 2: 写 dispatch 路由测试**

继续在 `tests/test_sau_browser_cli.py` 中补最小 dispatch 验证：

```python
class BrowserCliDispatchTests(unittest.TestCase):
    def test_dispatch_xiaohongshu_check_prints_valid(self):
        args = Namespace(platform="xiaohongshu", action="check", account="creator")
        with patch("sau_cli.check_xiaohongshu_account", new=AsyncMock(return_value=True)):
            code = asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(code, 0)

    def test_dispatch_douyin_upload_note_uses_new_request_fields(self):
        args = Namespace(
            platform="douyin",
            action="upload-note",
            account="creator",
            images=[Path("1.png")],
            title="图文标题",
            note="图文正文",
            tags="测试,图文",
            schedule=0,
            debug=False,
            headless=True,
        )
        with patch("sau_cli.upload_note", new=AsyncMock()) as mock_upload:
            asyncio.run(sau_cli.dispatch(args))
        request = mock_upload.await_args.args[0]
        self.assertEqual(request.title, "图文标题")
        self.assertEqual(request.note, "图文正文")
```

- [ ] **Step 3: 先跑测试确认失败**

Run:

```powershell
py -3 -m unittest tests.test_sau_browser_cli -v
```

Expected:

- 因为 `sau_cli.py` 还没有 `xiaohongshu` 分支和统一字段而失败

- [ ] **Step 4: 提交测试脚手架**

```powershell
git add tests/test_sau_browser_cli.py
git commit -m "test: define browser cli unification contract"
```

## Task 2: 改 `sau_cli.py`，补齐统一参数与小红书路由

**Files:**
- Modify: `sau_cli.py`
- Reference: `uploader/xiaohongshu_uploader/main.py`
- Reference: `uploader/douyin_uploader/main.py`
- Reference: `uploader/ks_uploader/main.py`

- [ ] **Step 1: 增加小红书 request dataclass**

在 `sau_cli.py` 中新增：

```python
@dataclass(slots=True)
class XiaohongshuVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class XiaohongshuNoteUploadRequest:
    account_name: str
    image_files: list[Path]
    title: str
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
```

- [ ] **Step 2: 改造抖音、快手 request dataclass**

把字段统一到以下模型：

```python
class DouyinVideoUploadRequest:
    title: str
    description: str

class DouyinNoteUploadRequest:
    title: str
    note: str

class KuaishouVideoUploadRequest:
    title: str
    description: str

class KuaishouNoteUploadRequest:
    title: str
    note: str
```

要求：

- 视频用 `description`
- 图文用 `note`
- 不再把图文 request 设计成只有历史 `note` 语义但没有 `title`

- [ ] **Step 3: 改 parser**

在 `build_parser()` 里完成：

- `douyin upload-video` 增加 `--desc`
- `kuaishou upload-video` 增加 `--desc`
- `douyin upload-note` 改成 `--title --note`
- `kuaishou upload-note` 改成 `--title --note`
- 新增整套 `xiaohongshu`：
  - `login`
  - `check`
  - `upload-video --title --desc --tags --thumbnail`
  - `upload-note --images --title --note --tags`

- [ ] **Step 4: 补小红书账号操作函数**

在 `sau_cli.py` 中新增：

```python
async def login_xiaohongshu_account(account_name: str, headless: bool = True) -> dict: ...
async def check_xiaohongshu_account(account_name: str) -> bool: ...
async def upload_xiaohongshu_video(request: XiaohongshuVideoUploadRequest) -> Path: ...
async def upload_xiaohongshu_note(request: XiaohongshuNoteUploadRequest) -> Path: ...
```

要求：

- 账号路径继续走 `resolve_account_file("xiaohongshu", account_name)`
- 登录 / 检查分别复用 `xiaohongshu_setup` 与 `cookie_auth`
- 上传前先做 `setup(handle=False)` 校验

- [ ] **Step 5: 改 dispatch**

要求：

- 三家浏览器平台都统一输出：
  - `login` 成功时打印账号文件路径
  - `check` 输出 `valid` / `invalid`
  - `upload-video` 打印简洁摘要
  - `upload-note` 打印图片数量摘要
- request 构造统一映射：
  - 视频：`title + description`
  - 图文：`title + note`

- [ ] **Step 6: 跑 CLI 测试确认通过**

Run:

```powershell
py -3 -m unittest tests.test_sau_browser_cli -v
```

Expected:

- `BrowserCliParserTests`
- `BrowserCliDispatchTests`

全部通过

- [ ] **Step 7: 跑最小 help 自检**

Run:

```powershell
py -3 sau_cli.py douyin --help
py -3 sau_cli.py kuaishou --help
py -3 sau_cli.py xiaohongshu --help
py -3 sau_cli.py xiaohongshu upload-note --help
```

Expected:

- 小红书子命令存在
- 图文命令展示 `--title`、`--note`
- 视频命令展示 `--desc`

- [ ] **Step 8: 提交 CLI 主线**

```powershell
git add sau_cli.py tests/test_sau_browser_cli.py
git commit -m "feat: unify browser cli contracts"
```

## Task 3: 给 uploader 做最小字段接线

**Files:**
- Modify: `uploader/douyin_uploader/main.py`
- Modify: `uploader/ks_uploader/main.py`
- Modify: `uploader/xiaohongshu_uploader/main.py`
- Modify: `tests/test_xiaohongshu_uploader.py`

- [ ] **Step 1: 给抖音视频接入 `desc`**

在 `DouYinVideo.__init__()` 中补 `desc` 参数和 `self.desc`，并把发布页填写逻辑改成：

```python
await self.fill_title_and_description(page, self.title, self.desc or self.title, self.tags)
```

- [ ] **Step 2: 给抖音图文接入 `title + note`**

在 `DouYinNote.__init__()` 中补 `title` 参数，保留 `note` 作为图文正文，发布页填写改成：

```python
await self.fill_title_and_description(page, self.title, self.note, self.tags)
```

要求：

- `title` 必填
- `note` 可选但建议非空；如果现有逻辑要求非空，就继续保留校验

- [ ] **Step 3: 给快手视频接入 `desc`**

在 `KSVideo.__init__()` 中补 `desc` 参数和 `self.desc`，填写“描述”区域时改成：

```python
await page.keyboard.type(self.desc or self.title)
```

- [ ] **Step 4: 给快手图文接入 `title + note`**

在 `KSNote.__init__()` 中补 `title` 参数与 `self.title`，保留 `self.note` 作为正文。

要求：

- 图文上传校验里增加 `title` 必填
- 如果页面当前只有正文输入区，没有独立标题区，仍然要在 CLI / request / 构造函数层保持 `title` 字段，以便后续平台对齐

- [ ] **Step 5: 检查小红书 CLI 接线是否需要补充适配**

确认 `XiaoHongShuVideo` / `XiaoHongShuNote` 只需要以下映射即可：

```python
title=request.title
desc=request.description  # 视频
desc=request.note         # 图文
```

如果 `XiaoHongShuNote` 里还保留历史 `note` 兼容，不要删，只保持 CLI 层优先走 `title + note + tags`。

- [ ] **Step 6: 补一条小红书映射测试**

在 `tests/test_xiaohongshu_uploader.py` 中增加最小断言：

```python
def test_note_title_defaults_do_not_override_explicit_title(self):
    app = xhs_main.XiaoHongShuNote(
        image_paths=["a.png"],
        note="正文",
        tags=[],
        publish_date=0,
        account_file="account.json",
        title="显式标题",
        desc="图文正文",
    )
    self.assertEqual(app.title, "显式标题")
    self.assertEqual(app.desc, "图文正文")
```

- [ ] **Step 7: 跑 uploader 相关测试**

Run:

```powershell
py -3 -m unittest tests.test_xiaohongshu_uploader -v
```

Expected:

- 小红书 uploader 相关单测通过

- [ ] **Step 8: 提交 uploader 接线**

```powershell
git add uploader/douyin_uploader/main.py uploader/ks_uploader/main.py uploader/xiaohongshu_uploader/main.py tests/test_xiaohongshu_uploader.py
git commit -m "feat: align browser uploader metadata fields"
```

## Task 4: 新增小红书 skill，并同步更新抖音、快手 skill

**Files:**
- Create: `skills/xiaohongshu-upload/SKILL.md`
- Create: `skills/xiaohongshu-upload/references/runtime-requirements.md`
- Create: `skills/xiaohongshu-upload/references/cli-contract.md`
- Create: `skills/xiaohongshu-upload/references/troubleshooting.md`
- Create: `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.ps1`
- Create: `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.sh`
- Create: `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_cli_template.py`
- Modify: `skills/douyin-upload/SKILL.md`
- Modify: `skills/douyin-upload/references/cli-contract.md`
- Modify: `skills/douyin-upload/scripts/examples/douyin_commands.ps1`
- Modify: `skills/douyin-upload/scripts/examples/douyin_commands.sh`
- Modify: `skills/douyin-upload/scripts/examples/douyin_cli_template.py`
- Modify: `skills/kuaishou-upload/SKILL.md`
- Modify: `skills/kuaishou-upload/references/cli-contract.md`
- Modify: `skills/kuaishou-upload/scripts/examples/kuaishou_commands.ps1`
- Modify: `skills/kuaishou-upload/scripts/examples/kuaishou_commands.sh`
- Modify: `skills/kuaishou-upload/scripts/examples/kuaishou_cli_template.py`

- [ ] **Step 1: 复制现有 skill 目录结构作为小红书骨架**

要求：

- 风格对齐 `skills/douyin-upload/`
- 默认优先走 `sau xiaohongshu ...`
- 明确小红书支持：
  - `login`
  - `check`
  - `upload-video`
  - `upload-note`

- [ ] **Step 2: 写小红书 CLI 契约**

至少写清：

```bash
sau xiaohongshu login --account <account>
sau xiaohongshu check --account <account>
sau xiaohongshu upload-video --account <account> --file <video> --title "<title>" [--desc "..."] [--tags ...]
sau xiaohongshu upload-note --account <account> --images <img...> --title "<title>" [--note "..."] [--tags ...]
```

- [ ] **Step 3: 更新抖音、快手 skill 契约**

要求：

- 视频示例命令补 `--desc`
- 图文示例命令改成 `--title --note`
- 所有模板文件同步更新，不要只改文档不改脚本

- [ ] **Step 4: 做 skill 文件级自检**

Run:

```powershell
Get-ChildItem skills\xiaohongshu-upload -Recurse
Get-Content skills\douyin-upload\references\cli-contract.md
Get-Content skills\kuaishou-upload\references\cli-contract.md
```

Expected:

- 小红书 skill 目录完整
- 抖音、快手 skill 契约都已经切到新参数模型

- [ ] **Step 5: 提交 skill 变更**

```powershell
git add skills/xiaohongshu-upload skills/douyin-upload skills/kuaishou-upload
git commit -m "feat: add xiaohongshu skill and align browser skill contracts"
```

## Task 5: 更新 examples 和 README / docs

**Files:**
- Modify: `examples/get_xiaohongshu_cookie.py`
- Modify: `examples/upload_video_to_xiaohongshu.py`
- Modify: `README.md`
- Modify: `docs/CLI.md`
- Modify: `docs/install.md`
- Modify: `docs/update.md`

- [ ] **Step 1: 改小红书 examples**

要求：

- `examples/get_xiaohongshu_cookie.py` 明确指向 `sau xiaohongshu login --account <account_name>` 这一主线
- `examples/upload_video_to_xiaohongshu.py` 说明当前主线优先走 CLI
- 如果继续保留 uploader 直连示例，注释里标明“调试入口 / 历史直连路径”

- [ ] **Step 2: 更新 README 平台表和快速开始**

README 至少要改这些位置：

- 平台能力表里把小红书改成：
  - `CLI ✅`
  - `Skill ✅`
- 快速开始里的浏览器平台命令改成统一契约
- 抖音、快手图文示例改成：

```bash
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文正文"
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文正文"
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文正文"
```

- [ ] **Step 3: 更新 `docs/CLI.md`**

要求：

- 补 `xiaohongshu` 小节
- 把三家浏览器平台整理成一致说明：
  - 视频：`title + desc + tags`
  - 图文：`title + note + tags`
- 登录二维码说明补小红书

- [ ] **Step 4: 更新 `docs/install.md` 和 `docs/update.md`**

要求：

- 安装文档里补 `sau xiaohongshu --help`
- 更新文档里补小红书自检命令和 skill 路径
- 文档统一写 `account_name`

- [ ] **Step 5: 做文档与示例核对**

Run:

```powershell
Get-Content README.md | Select-String -Pattern "xiaohongshu|upload-note|--note|--desc" -Context 1,2
Get-Content docs\CLI.md | Select-String -Pattern "xiaohongshu|--note|--desc" -Context 1,2
Get-Content docs\install.md | Select-String -Pattern "xiaohongshu" -Context 1,2
Get-Content docs\update.md | Select-String -Pattern "xiaohongshu" -Context 1,2
```

Expected:

- README、CLI、install、update 都出现小红书 CLI
- 图文正文写成 `--note`
- 视频描述写成 `--desc`

- [ ] **Step 6: 跑最终最小验证**

Run:

```powershell
py -3 -m unittest tests.test_sau_browser_cli tests.test_xiaohongshu_uploader -v
py -3 sau_cli.py xiaohongshu --help
py -3 sau_cli.py xiaohongshu upload-video --help
py -3 sau_cli.py xiaohongshu upload-note --help
```

Expected:

- 单测通过
- 小红书 CLI 帮助存在
- 视频命令显示 `--desc`
- 图文命令显示 `--note`

- [ ] **Step 7: 提交收尾**

```powershell
git add examples/get_xiaohongshu_cookie.py examples/upload_video_to_xiaohongshu.py README.md docs/CLI.md docs/install.md docs/update.md
git commit -m "docs: align browser cli docs and examples"
```
