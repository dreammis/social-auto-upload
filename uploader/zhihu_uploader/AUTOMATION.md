# 知乎自动化（开发验收中）

## 入口与流程

CLI 参数和分发在 `sau_commands/zhihu.py`，`sau_cli.py` 仅组装各平台入口。文章、视频、会话、定时、查询分别位于本目录的同名模块。会话文件为 `cookies/zhihu_<alias>.json`，身份绑定为相邻 `.identity.json`。

文章复用 `utils.article_render.load_article` 的 HTML/Markdown/TXT 与原稿图片路径。`article.py::fill_article_form` 使用原生 HTML 粘贴和图片位置标记；逐张上传后 `check_article_body` 检查完整文字/图片交错顺序、基本格式与链接。恢复非空草稿时中止保护原文；自动新建独立草稿尚未确认，不删除旧稿。

视频在素材上传成功后读取领域和视频标记完整菜单。`video.py::video_options` 返回候选，`select_option` 负责编号选择与合法值校验，`--show-options` 仅导出候选后退出。公开 chunk 中新版 pin_video 组件只渲染一个“所属领域”，旧组件的二级领域必填校验不适用于此处，已删除。

## 定位依据与边界

文章标题 `textarea[placeholder="请输入标题（最多 100 个字）"]`、正文 `div[contenteditable="true"][role="textbox"]` 来自真实页面。2026-10-21 已在原登录会话中发布带两张段间 PNG 的文章，HTML 粘贴保留 h2、加粗、编号列表、引用与外链。PNG 通过剪贴板粘贴上传；图片按钮先打开素材面板，不能直接当作文件选择器。其他图片格式的 input 路径尚未实测。DraftJS 加粗是 styled span，链接文字可能带零宽字符。

视频首页 `.VideoUploadButton-fileInput` 来自真实观察；上传后 `.VideoUploadForm-item` 按“所属领域”“视频标记”限域，展开 `.VideoUploadForm-selectList:visible` 读取各领域名称。弹层 `.VideoUploadForm-videoTypeModalOption` 的 role=button、确认/取消按钮来自公开 chunk。候选按菜单渲染顺序读取，不假定第一个候选是默认值。此处控件和上传成功等待仍未经过真实素材验收。

页头账号使用 `session.py::PROFILE_IMAGE` 的 `button.AppHeader-profileEntry img[alt^='点击打开'][alt$='的主页']`。展示名和头像不是唯一用户 ID，改名/换头像会导致绑定不一致；主体强校验仍待改进。

## 验收状态

2026-10-21 原登录会话的文章已真实发布，页面出现“发布成功”并进入正式文章页，两张图片位于原稿对应段间。该次由浏览器工具完成，不能算 Python CLI 端到端验收；内置会话尚无受支持的 CLI 接入点。视频文件选择器 setFiles 返回后仍在首页、文件控件为空，未进入上传后表单；领域完整候选和视频发布均未验证。尚未验证非 PNG、新建独立草稿及定时受理。此前将旧组件校验当作当前表单规则的探索结论已撤回。

文章成功条件必须是完整匹配 `/p/<id>` 的正式详情 URL 并出现文章标题；`/p/<id>/edit` 是草稿，不能据此返回 published。发布后可能出现分享面板和“送礼物”权益提示；本次未开启权益或分享。

`--prepare-only` 不点击最终发布；页面仍可能自动保存草稿。提交只触发一次，URL未知则 `submission_unknown`，先查原作品，不自动重发。定时仍需确认实际安排，不以本地时间校验冒充平台受理。开发证据在 git ignored 的 `.local/zhihu-exploration.md`。
