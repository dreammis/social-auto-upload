---
name: facebook-upload
description: 使用 sau CLI 登录 Facebook 个人主页，立即发布视频或图文，查询原作品、移至垃圾箱或永久删除。
license: MIT-0
slug: social-auto-upload-facebook-upload
displayName: Facebook 个人主页发布
version: 1.0.0
summary: 管理 Facebook 个人主页登录、视频图文发布和作品核验。
---

# Facebook 个人主页发布与删除

本 Skill 调用现有 CLI。默认不配置代理，浏览器按系统网络直连；网络环境需要代理时显式传 `--proxy` 或设置 `SAU_FACEBOOK_PROXY`。传 `--proxy ""` 可忽略环境变量并直连。

```powershell
sau facebook login --account creator
sau facebook check --account creator
sau facebook upload-video --account creator --file videos/demo.mp4 --title "标题" --desc "正文" --tags 生活,分享
sau facebook upload-note --account creator --images images/1.jpg images/2.jpg --title "图文标题" --note "正文"
```

登录时在可见 Chrome 完成登录，账号保存为 `cookies/facebook_creator.json`。`check` 验证个人主页登录态，不代表 Page 权限或作品发布结果。标题、正文、标签合并为一段配文。当前支持立即发布，未接入个人主页定时；Page 使用独立 `facebook-page` 命令。

取得原作品链接后管理作品：

```powershell
sau facebook verify --account creator --post-url "原作品链接" --owner-id "作者数字ID" --expected-text "原作品正文"
sau facebook delete --account creator --post-url "原作品链接" --owner-id "作者数字ID" --expected-text "原作品正文" --result .local/trash-result.json
sau facebook delete --account creator --post-url "原作品链接" --owner-id "作者数字ID" --expected-text "原作品正文" --from-trash --permanent --result .local/delete-result.json
```

删除前同时核对登录用户、作者、原作品编号和正文。默认移至垃圾箱，30 天后由平台删除，返回 `trashed`；加 `--permanent` 立即永久删除，已经在垃圾箱时再加 `--from-trash`。永久删除不可恢复。

`verify --from-trash` 查询垃圾箱原记录；`verify --deleted` 仅确认编号不在垃圾箱，返回 `absent_from_trash`，不能单凭缺席证明过去发生过永久删除。当前仅检索有限滚动范围的近期作品；没有找到或同文案无法唯一定位时明确失败。

只有平台出现本次提交的成功提示才认为发表已确认。点击后超时或浏览器断开应视为结果未知：先在同一账号个人主页或垃圾箱核对原作品，不重复上传或重复删除。本地素材不会被删除。完整参数以 `sau facebook upload-video --help`、`upload-note --help`、`verify --help` 和 `delete --help` 为准。

## 示例脚本

`scripts/examples/` 下的文件是复制用示例，不是运行时依赖。执行前先查看当前 CLI 的 `--help`，替换账号、素材和正文；这些命令可能创建真实作品。

- `facebook_commands.ps1`：PowerShell
- `facebook_commands.sh`：Bash
- `facebook_cli_template.py`：Python subprocess
