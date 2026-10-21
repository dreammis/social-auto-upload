---
name: zhihu-upload
description: 使用 social-auto-upload 的 sau CLI 发布知乎文章或视频；文章支持按原稿位置导入配图，视频分类从页面实时读取。
---

# 知乎文章与视频

通过仓库的 `sau zhihu` 命令操作。文章已用原登录浏览器验证正式发表；Python CLI 的视频文件交接和完整分类菜单仍待验收，不把本地测试当成线上发布成功。

## 登录

```powershell
sau zhihu login --account creator
sau zhihu check --account creator
```

`--account` 是保存会话的本地别名，与昵称无须相同。登录时程序直接从页头读取当前身份并保存绑定信息；CLI 的 Chrome 与内置浏览器会话独立。

## 文章

标题最多 100 字，正文支持 UTF-8 HTML/Markdown/TXT；Markdown 首次使用先执行 `sau article setup`。图片直接写在原稿相应段落：

```markdown
第一段正文。

![配图](images/1.png)

第二段正文。
```

相对图片路径从原稿目录解析。正文通过富文本粘贴导入，再按原位置逐张上传；提交前核对全部文字、图片交错位置、基本格式及链接。平台若过滤格式或改变图片位置，校验失败即停止提交。自定义 CSS、封面、专栏收录、芝士任务、文档导入未验收。`--images` 已移除。

```powershell
sau zhihu upload-article --account creator --title "文章标题" --content-file "文章.md" --prepare-only
```

恢复出非空草稿时仍中止保护原文；自动新建独立草稿的行为尚未在当前账号验收，不要求用户删除已有草稿。

## 视频

单文件最大 20GB、最长 4 小时。当前代码检查标题 5–50 字、简介最多 300 字；相关新表单限制仍需实际素材核对。

```powershell
# 上传后读取该账号、该素材表单的全部候选，不发表。
sau zhihu upload-video --account creator --file "视频.mp4" --title "视频标题示例" --originality original --show-options
# 终端显示完整菜单，用户按编号选领域和视频标记；只验收到提交前。
sau zhihu upload-video --account creator --file "视频.mp4" --title "视频标题示例" --originality original --prepare-only
```

`--originality` 固定可选 `original`、`reprint`。非交互调用先从 `--show-options` 的 JSON 结果读取 `options.category`、`options.video_mark`，再以 `--category`、`--video-mark` 传入其中完整值；不接受菜单不存在的值。分类来自实时菜单，尚未获得当前账号完整清单，不编造固定枚举。

新版公开页面代码只渲染一个“所属领域”；已删除未经证实的二级领域参数及其必填校验。话题为动态搜索，`--topics` 选填，搜索选择流程仍待验收。默认使用平台生成的封面。

## 定时与结果

`--schedule "YYYY-MM-DD HH:MM"` 代码按北京时间、30 分钟后至 48 小时内校验，排期读回与最终受理仍待真实验证。

`--show-options` 和 `--prepare-only` 都可能留下远端草稿。`prepared` 只表示代码完成表单检查，不表示发表成功。结果为 `submission_unknown` 时先在创作中心核查原作品，不直接重新上传。结果文件已有作品 URL 时可只读查询：

```powershell
sau zhihu verify --account creator --result "本次结果.json"
```

原登录浏览器已实际发表富文本文章并保留两张段间 PNG。该次由浏览器工具完成，尚不能算 Python CLI 发布验收。视频文件选择器返回后页面仍未收到文件，未取得完整领域菜单；视频发布和排期尚未验证。
