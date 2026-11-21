---
name: wechat-upload
description: 使用 social-auto-upload 的 sau CLI 登录微信公众平台、发布图文文章，支持摘要、作者、独立封面、创作来源声明与群发通知；发表最后一步的管理员扫码验证由账号管理员本人完成。
license: MIT-0
slug: social-auto-upload-wechat-upload
displayName: 微信公众号图文发布
version: 1.0.0
summary: 使用 sau 登录微信公众号并发布图文文章。
---

# 微信公众号图文

使用仓库的 `sau wechat` 命令，不另写网页上传逻辑。

## 功能概览

| 功能 | 命令入口 | 说明 |
| --- | --- | --- |
| 登录 | `sau wechat login --account <name>` | 可见 Chrome 中管理员微信扫码登录，保存本地会话 |
| 账号检查 | `sau wechat check --account <name>` | 检查登录态与公众号昵称绑定 |
| 图文发布 | `sau wechat upload-article ...` | HTML/Markdown/TXT 原稿，正文图片保留原稿位置 |

微信公众号后台 token 是会话级参数、每次登录都变化；发布时程序会从当前会话重新读取 token，不复用旧值。`--account` 是本地会话别名，无须与公众号昵称相同。

## 登录

```powershell
sau wechat login --account creator
sau wechat check --account creator
```

在打开的 Chrome 窗口中用**管理员微信扫码**登录；扫码和确认都在网页完成，账号密码不要告诉 Agent。会话保存在本地，不提交到仓库。登录态失效时重新执行 `login`。

## 图文发布

标题最多 64 字，摘要最多 120 字，作者最多 8 字。正文使用 UTF-8 HTML、Markdown 或 TXT；Markdown 首次使用先执行 `sau article setup`。图片写在原稿对应段落中，相对路径从原稿目录解析：

```markdown
第一段正文。

![配图](images/1.png)

第二段正文。
```

```powershell
sau wechat upload-article --account creator --title "文章标题" --content-file "文章.md" --digest "一句话摘要" --cover "封面.png"
```

- `--digest`：摘要，省略则由公众号用正文开头生成。
- `--author`：署名，最多 8 字。
- `--cover`：独立封面图片；省略则用公众号默认封面策略，封面不是发布必填项。
- `--originality`：`none`（默认，不声明）或 `original`（声明原创）。按实际创作方式选择，不要为流量虚报原创。
- `--no-broadcast`：发表但不群发通知；默认开启群发。群发会向全部粉丝推送，请确认后再发。
- `--prepare-only`：填写并核对后结束，不点击发表；会在编辑器留下远端草稿。

提交前核对标题、正文首段、摘要和账号绑定。编辑器恢复出非空草稿时不会自动清理，请先到后台处理。

## 发表与管理验证

发表后会依次遇到创作来源声明、发表方式、群发确认弹窗，程序按参数逐项处理，每步只点一次。微信公众号在公开发表时会要求**管理员微信扫码验证身份**，这一步只能由账号管理员本人完成：程序检测到验证二维码后暂停并提示，等待你在浏览器中扫码。超时或验证未完成时，结果文件的状态为 `awaiting_admin_qr` 或 `submission_unknown`，此时**不要重发**，先到后台「已发表 / 发表记录」按标题和时间核实。

结果文件写在账号目录的 `wechat_results/`，含标题、账号、图片清单、正文校验摘要（manifest）和阶段状态。`prepared` 不表示发表成功；只有到后台核实到公开文章才算完成。响应未知时程序禁止自动重试，避免重复群发。

## 示例脚本

以下文件提供登录、检查、预填与发布模板；移除 `--prepare-only` 会进入真实发表流程。

- [PowerShell](scripts/examples/wechat_commands.ps1)
- [Bash](scripts/examples/wechat_commands.sh)
- [Python subprocess](scripts/examples/wechat_cli_template.py)
