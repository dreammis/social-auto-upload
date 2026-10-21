---
name: meta-upload
description: 使用 sau CLI 登录 Facebook Page，发布视频或图文、设置北京时间排期、查询原作品并删除。
---

# Facebook Page 发布与删除

本 Skill 调用现有 `sau facebook-page`，不重复实现浏览器逻辑。Instagram 当前暂停，后续使用独立网页方式；不使用 Business Suite 绑定 Instagram。

默认不配置代理，浏览器按系统网络直连；网络环境需要代理时显式传 `--proxy` 或设置 `SAU_FACEBOOK_PAGE_PROXY`。

先登录并保存账号别名：

```powershell
sau facebook-page login --account creator
sau facebook-page check --account creator
sau facebook-page upload-note --account creator --page "我的 Page" --images images/1.jpg --title "标题" --note "正文" --result .local/page-result.json
sau facebook-page upload-video --account creator --page "我的 Page" --file videos/demo.mp4 --title "标题" --desc "正文" --schedule "2026-10-21 10:30" --result .local/reel-result.json
```

视频与图文均可传 `--schedule "YYYY-MM-DD HH:MM"`，使用北京时间、至少提前 2 小时，浏览器时区必须为 Asia/Shanghai；留空立即提交。`--page` 填准确 Page 名称。`--tags` 为英文逗号分隔标签。传 `--proxy ""` 可忽略环境变量并直连。

结果默认保存到 `.local/meta-results/`，建议显式传 `--result`，避免手工抄写编号。`scheduled` 表示平台确认排期并核对原记录；`published` 表示图文已发布；视频立即提交在创建响应无错误且完成弹窗出现后返回 `processing`，表示平台已受理并正在处理，尚不能证明已公开播放，`content_id` 可能暂时没有。`submission_unknown` 只表示提交证据不足，必须先查询原记录，不重发。

用结果中的 Page ID、Page 名、内容编号和正文查询或删除：

```powershell
sau facebook-page verify --account creator --page "我的 Page" --page-id "Page数字ID" --content-id "内容编号" --expected-text "原作品正文" --scheduled
sau facebook-page delete --account creator --page "我的 Page" --page-id "Page数字ID" --content-id "内容编号" --expected-text "原作品正文" --scheduled --result .local/delete-result.json
```

`--scheduled` 选择定时列表；删除会取消排期并永久移除，返回 `deleted`。管理已发布作品时不加它，当前平台会移至垃圾箱，返回 `trashed`，30 天后自动删除；未接入 Page 垃圾箱提前永久删除。已定时作品实际发布后编号可能变化，需使用已发布列表中的编号。

只覆盖已加载的近期列表，不保证自动查找全部历史作品。同文案不能唯一定位、Page 或编号不符时不删除。删除后超时或浏览器断开时先核对原记录，不自动重删；本地素材保留。完整参数见仓库 `docs/CLI.md`。

## 示例脚本

`scripts/examples/` 下的文件是复制用示例，不是运行时依赖。执行前先查看当前 CLI 的 `--help`，替换账号、素材和正文；这些命令可能创建真实作品。

- `meta_commands.ps1`：PowerShell
- `meta_commands.sh`：Bash
- `meta_cli_template.py`：Python subprocess
