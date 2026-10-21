# 知乎自动化

## 入口与职责

`sau_commands/zhihu.py` 声明 CLI；本目录的 `session.py`、`article.py`、`video.py`、`schedule.py`、`verification.py` 分别处理会话、文章、视频、定时和原作品查询。使用说明见 `skills/zhihu-upload/SKILL.md`。

会话为 `cookies/zhihu_<alias>.json`，账号绑定为相邻 `.identity.json`。`session.py::PROFILE_IMAGE` 从页头当前用户入口读取昵称和头像路径；它们并非永久用户 ID，改名或换头像会导致绑定不一致。不要将登录超时或网络错误直接判为会话失效。

## 文章

`utils.article_render.load_article` 解析 HTML/Markdown/TXT。`article.py::fill_article_form` 通过 HTML 粘贴和图片位置标记导入正文；`check_article_body` 核对全文、图片交错顺序、格式和链接。恢复非空草稿时停止，不覆盖原文。

- 标题：`textarea[placeholder="请输入标题（最多 100 个字）"]`，使用编辑器业务提示定位。
- 正文：`div[contenteditable="true"][role="textbox"]`，与标题 textarea 区分。
- PNG 走剪贴板；其他格式走图片 input，后者尚需真实页面验证。图片工具栏先打开素材面板，不能把图片按钮直接当作文件选择器。
- DraftJS 加粗可能是 styled span，链接可能带零宽字符；校验时按呈现含义读取。

成功必须为正式 `/p/<id>`，不能把 `/edit` 草稿地址算作发表。发表后可能出现分享与权益提示，不自动分享或开启权益。

## 视频

`video.py::main` 依次完成文件校验、账号核对、上传、菜单读取、表单检查、提交与详情链接读取。

```python
video_input = page.locator("input.VideoUploadButton-fileInput[type=file]")
field = page.locator(".VideoUploadForm-item").filter(
    has=page.get_by_text("所属领域", exact=True),
)
control = field.get_by_role("combobox")
```

文件 input 的 class 来自上传首页；业务行标签限定领域、声明和原创开关，排除其他下拉框与 checkbox。领域列表为 `.VideoUploadForm-selectList:visible` 中的 `role=option`，过滤“选择领域”占位项。声明弹层使用 `.VideoUploadForm-videoTypeModal:visible`，选项为 `.VideoUploadForm-videoTypeModalOption[role=button]`，选择后确认。

完整领域与声明文案维护在 `constants.py`，供 CLI choices 使用；提交时仍与本次实时菜单核对。菜单新增或更名时同步更新常量。当前话题工具栏按钮无可访问名称，尚未接入自动选择，不提供可执行的 `--topics` 参数。

视频大小必须严格大于 102400 字节。页面处理 change 后会清空 input，所以 `files=0` 不能证明未选文件；以“上传成功”、失败提示及实际表单判断上传状态。

当前入口在原页显示“发布成功”，点击“查看详情”另开 `/pin/<id>`。`video.py` 先记录平台已确认发表，再读取详情链接；读取链接失败不得退回未发表状态或重新上传。`verification.py` 接受文章、pin 视频及旧版视频详情路径。

## 验证边界

原登录浏览器中的文章和视频均已完成真实发表及详情核对。Python CLI 整条链路、非 PNG 图片及定时受理仍需独立验证；本地测试不替代线上提交证据。排查素材、截图与账号结果保存在忽略目录 `.local/`，不纳入公开使用文档。

`--prepare-only` 和候选查询可能自动保存草稿。结果未知时先查原作品，禁止自动重发。定时是实验性路径，必须核对平台实际排期后才能返回定时成功。
