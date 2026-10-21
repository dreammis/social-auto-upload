---
name: xueqiu-upload
description: 通过 social-auto-upload 的 sau CLI 登录和核验雪球账号，发布 HTML、Markdown 或 TXT 长文，保留原稿段间配图、原生文字结构与独立封面，并查询原作品确认结果。适用于雪球创作者平台，不支持定时或视频。
---

# 雪球长文

使用仓库现有 `sau xueqiu`，不另写网页上传实现。先检查 `sau xueqiu upload-article --help`。Windows 未加入 PATH 时在仓库根目录使用 `.\.venv\Scripts\sau.exe`。完整输入及结果说明见 [雪球使用说明](../../docs/xueqiu.md)。

## 账号及输入

- 已有账号执行 `sau xueqiu check --account <别名>`。首次使用执行 `sau xueqiu login --account <别名> --expected-name "用户指定昵称"`，在打开的 Chrome 中登录。程序保存会话并绑定真实用户 ID；不要把账号密码写进命令或源码。Codex 内置浏览器的登录不会自动生成 CLI 会话文件。
- 必须提供非空单行 `--title`、UTF-8 HTML/Markdown/TXT `--content-file` 和与实际创作方式相符的 `--declaration`。声明选择 `不添加创作声明` 或 `本文包含AI生成内容`，不要替用户猜测。
- `--visibility` 为 `公开` 或 `私人`，默认公开。正文图片通过 HTML 的 `img` 或 Markdown 图片写在原稿对应位置，相对路径基于原稿目录；没有 `--images` 文末追加参数。独立封面用 `--cover`，采用平台默认裁剪。图片接受本地 GIF/JPEG/PNG，不接受远端或 data URL。
- 雪球各级标题统一为平台小标题，保留段落、加粗、斜体、链接；列表转换为带编号或圆点的段落。自定义 CSS 不保证保留。表格、代码块等未验证结构在创建远端草稿前报错。Markdown 首次使用需运行 `sau article setup`，详见使用说明。

## 草稿和发表

```powershell
sau xueqiu upload-article --account <别名> --title "用户标题" --content-file "文章.md" --cover "封面.png" --visibility 私人 --declaration "本文包含AI生成内容"
```

命令默认实际发表。仅检查草稿和预览时显式增加 `--prepare-only`；雪球会自动保存远端草稿，重复运行可能创建多份草稿。编辑器若已有内容会拒绝覆盖。无需独立封面时省略 `--cover`。

优先使用 Markdown 原稿；带本地段间配图的完整示例见 [examples/xueqiu_article.md](../../examples/xueqiu_article.md)。首次使用先执行 `sau article setup`。

正式 CLI 已实测原生结构、两张不同的段间图片、独立封面、私人发表及后台原作品查询。沿用用户的操作范围；开发或登录授权本身不等于授权发表测试内容。

没有定时参数：本次账号的完整长文表单未观察到定时功能。Word、自定义裁剪、视频、股票/话题/@关联对象尚未支持，不用普通文字冒充关联对象。

## 判断结果与中断处理

保留命令输出的结果 JSON 路径和截图。`prepared` 仅表示准备完成；`published` 表示平台最终受理并通过主体、标题、分享范围及正文核对。`management_verified: true` 表示后台原 ID 查询也通过。私人作品显示“仅自己可见”。

若记录为 `submission_unknown`，执行 `sau xueqiu verify --account <别名> --result "本次结果文件.json"`，按已保存的原作品 ID 只读查询，并用原稿重查后台正文和图片。保留发表时的原稿、图片及路径，内容改变会报错；旧版缺少原稿路径的成功结果仅核查作品身份和分享范围。没有 ID 时进入“内容管理”按标题、账号及时间核查。未查明前不要重跑上传或再次点击发布，避免重复作品。

默认使用可见 Chrome，`--headless` 为显式选项；本机无头访问曾被平台拦截。网络超时、403 或主体不一致应保留具体错误，不据此断言 Cookie 失效。`--debug` 保存失败截图。

## 示例脚本

`scripts/examples/` 下的文件是复制用示例，不是运行时依赖。执行前先查看当前 CLI 的 `--help`，替换账号、素材和正文；这些命令可能创建真实作品。

- `xueqiu_commands.ps1`：PowerShell
- `xueqiu_commands.sh`：Bash
- `xueqiu_cli_template.py`：Python subprocess
