---
name: zhihu-upload
description: 使用 social-auto-upload 的 sau CLI 登录知乎、发布文章或视频，并按作品链接核对结果；支持原稿位置配图与视频领域、声明选项。
---

# 知乎文章与视频

使用仓库的 `sau zhihu` 命令，不另写网页上传逻辑。

## 功能概览

| 功能 | 命令入口 | 说明 |
| --- | --- | --- |
| 登录 | `sau zhihu login --account <name>` | 保存指定账号的本地会话 |
| 账号检查 | `sau zhihu check --account <name>` | 检查会话与当前账号是否一致 |
| 文章发布 | `sau zhihu upload-article ...` | HTML/Markdown/TXT 原稿，图片保留原稿位置 |
| 视频发布 | `sau zhihu upload-video ...` | 单视频、标题、简介、领域与内容声明 |
| 作品核对 | `sau zhihu verify --account <name> --result <json>` | 打开结果文件中的原作品链接核对标题 |

元数据约定：文章使用 `title + content-file`，视频使用 `title + desc + originality + category + video-mark`。`--account` 是本地会话别名，无须与知乎昵称相同。

## 登录

```powershell
sau zhihu login --account creator
sau zhihu check --account creator
```

账号密码、验证码在登录窗口输入；会话文件保存在本地，不提交到仓库。

## 文章

标题最多 100 字。正文使用 UTF-8 HTML、Markdown 或 TXT；Markdown 首次使用先执行 `sau article setup`。

图片写在原稿对应段落中，相对路径从原稿目录解析：

```markdown
第一段正文。

![配图](images/1.png)

第二段正文。
```

```powershell
sau zhihu upload-article --account creator --title "文章标题" --content-file "文章.md"
```

提交前核对文字、图片顺序、基本格式和链接。编辑器恢复出非空草稿时会停止，避免覆盖已有内容。暂不支持自定义主题 CSS、手动封面、专栏收录、芝士任务和文档导入。

## 视频

文件必须大于 100KB（102400 字节）、最大 20GB、最长 4 小时。标题 5–50 字，简介最多 300 字；默认使用平台生成的封面。

```powershell
sau zhihu upload-video --account creator --file "视频.mp4" --title "视频标题示例" --desc "视频简介" --originality original --category "教育" --video-mark "含 AI 生成内容"
```

- `--originality`：`original`（原创）或 `reprint`（转载）。
- `--category`：领域选项见 `sau zhihu upload-video --help`；省略时显示实时菜单，按编号选择。
- `--video-mark`：`内容无需标注`、`含 AI 生成内容`、`含虚构演绎内容`、`内容含营销信息`、`内容为转载`、`个人观点仅供参考`；声明须与内容一致。

非交互调用应指定领域和声明。程序提交前仍会核对实时菜单。仅获取当前页面的候选时使用：

```powershell
sau zhihu upload-video --account creator --file "视频.mp4" --title "视频标题示例" --originality original --show-options
```

候选写入结果 JSON 的 `options.category`、`options.video_mark`。暂不支持自动选择话题、自定义封面、专栏和内容来源。

## 提交与结果

文章和视频均可加 `--prepare-only`，填写并检查后结束；`--prepare-only`、`--show-options` 都可能留下远端草稿。

`published` 表示平台确认发表，详情链接写入结果文件的 `url`；视频地址可为 `/pin/<作品ID>`。若详情读取失败，保留 `published` 和 `error`，到创作中心查原作品，勿重发。`prepared` 不表示发表成功。若为 `submission_unknown`，也先按标题和提交时间检查原作品。已有 URL 时可执行：

```powershell
sau zhihu verify --account creator --result "本次结果.json"
```

`--schedule "YYYY-MM-DD HH:MM"` 为实验性选项，按北京时间限制在 30 分钟后至 48 小时内；尚不保证完整排期流程可用。

## 示例脚本

以下文件提供登录、检查、表单预填及候选查询模板；移除 `--prepare-only` 会真实发布文章。

- [PowerShell](scripts/examples/zhihu_commands.ps1)
- [Bash](scripts/examples/zhihu_commands.sh)
- [Python subprocess](scripts/examples/zhihu_cli_template.py)
