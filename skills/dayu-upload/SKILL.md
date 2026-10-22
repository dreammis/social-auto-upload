---
name: dayu-upload
description: 通过 social-auto-upload 的 sau CLI 完成大鱼号登录、账号核验、视频和文章的立即或定时发布，以及原作品结果查询。文章接收 HTML、Markdown 或 TXT 文件，Markdown 可选择主题。适用于已安装 sau 的环境，无需先阅读上传器源码。
license: MIT-0
slug: social-auto-upload-dayu-upload
displayName: 大鱼号视频与文章发布
version: 1.0.0
summary: 发布大鱼号视频和文章，支持定时与结果核验。
---

# 大鱼号发布

使用 `sau dayu`，不另写一套网页发布逻辑。先执行 `sau dayu --help`，具体参数以 `upload-video --help`、`upload-article --help` 和 `verify --help` 为准。仓库环境在项目根目录运行；Windows 未将命令加入 PATH 时用 `.\.venv\Scripts\sau.exe`。不要依赖固定测试账号或本机路径。

## 账号与输入

1. 使用已有账号时执行 `sau dayu check --account <本地账号名>`。首次使用或登录失效时执行 `sau dayu login --account <本地账号名> --expected-name "用户指定的大鱼号名称"`，让用户在打开的 Chrome 中登录。CLI 会绑定发布主体，拒绝错号。
2. 视频必须提供 `--file`、`--title`、`--thumbnail`、`--category`、`--source`。视频至少 5 秒；标题 5–60 字（英文按半字）；封面最大 5 MB。分类从 CLI 的 choices 中选择，不能猜测页面外的分类。
3. 文章必须提供 `--title`、`--content-file`、`--source`。标题 5–50 字（英文按半字并向上取整），正文为 UTF-8 HTML/Markdown/TXT 文件，最多 2 万字。长文放在文件里，不拼进命令行。图片使用本地路径，相对路径以正文文件所在目录为起点，每张最大 5 MB。
4. 信息来源必须按实际内容选择：`无需标注`、`AI生成`、`虚构演绎`、`营销信息`、`转载`、`个人观点`、`不适宜未成年人`。转载必须同时提供 `--source-url "https://原文地址"`，其他来源不传原文链接。

## 命令

```powershell
sau dayu upload-video --account <本地账号名> --file "视频.mp4" --title "用户的视频标题" --category "科技" --source "无需标注" --thumbnail "封面.jpg"
sau dayu upload-article --account <本地账号名> --title "用户的文章标题" --content-file "文章.html" --source "无需标注" --cover-indices 1
```

以上会实际发表；素材、主体及发表意图沿用用户已给出的授权。仅要求检查准备时增加 `--prepare-only`：它会上传素材、填写表单并保存本地截图，不发表，也不保存可恢复草稿。

Markdown 首次使用需要 Node.js 22+ 并执行 `sau article setup`。在文章命令中传 `--content-file "文章.md" --theme modern`，主题可选 `default/grace/simple/modern/plain`，默认 `default`。HTML/TXT 不传 `--theme`。可先使用 `sau article render --content-file "文章.md" --theme modern --output "预览.html"` 本地渲染。大鱼号采用兼容排版，保留文字颜色、背景和近似字号；圆角、精确字体与间距不保证原样。最终发表前会核对服务端主题预览。

视频选填 `--desc`、逗号分隔的 `--tags`；文章选填 `--author`、`--cover-indices 1` 或 `--cover-indices 1 3 2`，封面序号从正文图片顺序的 1 开始，三封面须各不相同。文章没有分类和标签字段。竖版封面、素材库、文档导入、正文视频和独立保存草稿尚未接入；不要声称命令已支持。

## 定时

只有用户要求定时才增加 `--schedule "YYYY-MM-DD HH:MM"`；不传默认立即发表。时间固定按**北京时间 Asia/Shanghai（UTC+8）**解释，须在当前时间 **2 小时后至 7 天内**，分钟为 **5 的倍数**。视频和文章用同一参数。向用户说明时区；缺少具体时间或存在歧义时先明确时间，不擅自取整或改成立即发表。预留上传和处理时间，填表时仍会校验范围。

平台确认本次作品及保存的预定时间后即为定时安排成功，不等待到点、审核或公开访问，不把“定时安排成功”说成“已公开”。平台审核可能使实际公开时间延后。

## 结果与中断

保留命令输出的结果文件和作品 ID。立即发表以最终业务确认成功为完成，审核中也已提交成功；定时必须确认原作品及预定时间。

提交超时或结果未知时，**只查询原作品，不重新执行上传或确认发表**：

```powershell
sau dayu verify --account <本地账号名> --result "本次结果文件.json" --timeout 60
```

结果文件会帮助核对标题、主体、作品及定时时间。也可按 ID 查询：`sau dayu verify --account <本地账号名> --type article --content-id "作品ID"`（视频用 `--type video`）。无可查询 ID 时告知具体错误，请用户核查后台；不要猜测失败并重发。

只有用户明确要求核对公开内容/播放时才在查询命令添加 `--public`；主题或完整正文核对应使用原结果文件。公开检查可能等待审核或定时到点，不属于默认发表完成条件。

## 示例脚本

`scripts/examples/` 下的文件是复制用示例，不是运行时依赖。执行前先查看当前 CLI 的 `--help`，替换账号、素材和正文；这些命令可能创建真实作品。

- `dayu_commands.ps1`：PowerShell
- `dayu_commands.sh`：Bash
- `dayu_cli_template.py`：Python subprocess
