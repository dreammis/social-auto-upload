# 大鱼号图文发布

使用 UTF-8 正文文件发布文章：有格式的正文用 `.html`、`.htm` 或 Markdown（`.md`、`.markdown`），纯文字用 `.txt`。文章内容保存在文件中，CLI 只接收文件路径，适合长文章、多段落和图文混排。正文上限为 2 万字，超限会在上传前报错。

## 登录

与视频发布共用账号，无需重复登录：

```powershell
sau dayu login --account creator --expected-name "你的大鱼号名称"
sau dayu check --account creator
```

安装方法见 [CLI 使用说明](./CLI.md)。Windows 中找不到 `sau` 时可使用 `.\.venv\Scripts\sau.exe`。

## 发布一篇文章

```powershell
sau dayu upload-article --account creator --title "如何阅读作品数据面板" --content-file "examples/dayu_article.html" --source "无需标注" --author "你的作者名称" --cover-indices 1
```

此命令会实际发表；平台确认发表后即返回成功，不等待审核。可先用 `--prepare-only` 上传图片并检查填表结果；该模式保存本地截图后结束，未发表，也不生成服务端预览，不能据此判断最终主题效果。

| 必填内容 | 参数 | 要求 |
| --- | --- | --- |
| 账号 | `--account` | 已登录的本地账号名称 |
| 文章标题 | `--title` | 5–50 字，英文字符按半字计数并向上取整 |
| 正文文件 | `--content-file` | UTF-8 的 HTML、Markdown 或 TXT 文件；正文文字最多 2 万字 |
| 信息来源 | `--source` | 无需标注、AI生成、虚构演绎、营销信息、转载、个人观点、不适宜未成年人 |
| 原文链接 | `--source-url` | 选择“转载”时必填，提供 http/https 原文链接 |

当前图文页没有视频发布中的“分类”或“标签”字段，无需提供对应参数。

## 定时发表

在上述命令中增加 `--schedule "YYYY-MM-DD HH:MM"`，按**北京时间（Asia/Shanghai，UTC+8）**解释。时间须在当前时间 2 小时后至 7 天内，分钟为 5 的倍数；例如 `10:30`、`10:35`。请预留图片上传和正文处理的时间，填表时也会重新检查范围；无效时间不会自动取整或改成立即发表。

```powershell
sau dayu upload-article --account creator --title "如何阅读作品数据面板" --content-file examples/article.md --theme modern --source "无需标注" --cover-indices 1 --schedule "2027-01-01 10:30"
```

请将示例日期换成实际范围内的时间。省略该参数默认立即发表。平台确认原作品及预定时间后，命令即返回定时安排成功，不等待到点或审核；审核延长时平台可能晚于预定时间公开。

## 如何提供带格式的正文

用 HTML 标签表达文章结构，例如：

```html
<h1>小节标题</h1>
<p>正文段落，可以包含<strong>加粗重点</strong>。</p>
<img src="images/example.png">
<blockquote>引用内容。</blockquote>
<ol>
  <li>第一步。</li>
  <li>第二步。</li>
</ol>
<ul>
  <li>列表项目。</li>
</ul>
<hr>
<p>最后一段。</p>
```

| 文章格式 | 写法 |
| --- | --- |
| 段落、换行 | `<p>`、`<br>` |
| 小节标题 | `<h1>` 至 `<h6>` |
| 加粗 | `<strong>` 或 `<b>` |
| 引用 | `<blockquote>` |
| 有序、无序列表 | `<ol>`、`<ul>`，其中用 `<li>` 写每一项 |
| 分隔线 | `<hr>` |
| 图片 | `<img src="本地图片路径">` |

可以直接提供上述 HTML 片段，也可以使用带 `html/head/body` 的完整 HTML 文件。标签需要正确闭合；图片和换行等空标签除外。

当前命令支持上表中的格式，以及带内联 CSS 的主题 HTML、`section/div/span/figure` 布局容器。带样式的正文会自动转换为**大鱼号兼容排版**：保留文字颜色、背景色和近似字号，正文仍是可选择、可复制的文字。圆角不能保留，字体、间距和边框可能与本地预览不同；不保证所有 CSS 原样显示。确认发表前会核对服务端预览的完整正文、图文顺序、文字颜色和背景色，检查失败时中止发表。

请保留原始 Markdown/HTML 文件。大鱼号网页编辑器再次导入兼容排版时可能清理颜色、布局或图片；网页重新编辑后的效果不在本命令的保留范围内。`--prepare-only` 的编辑器截图也不代表最终主题效果。

斜体、代码块、用户输入的表格、外部样式表、脚本及其他未接入标签会在上传前提示修改。Word 文件尚未接入。

Markdown 会先在本地渲染为 HTML，再导入大鱼号。默认主题为 `default`，可选 `default/grace/simple/modern/plain`；`plain` 仅转换结构。首次使用 Markdown 前执行 `sau article setup`，需要 Node.js 22+。预览与转换方法见 [文章文件与主题渲染](./article.md)。

```powershell
sau dayu upload-article --account creator --title "如何阅读作品数据面板" --content-file examples/article.md --theme modern --source "无需标注" --cover-indices 1

# 先生成主题 HTML，再发表同一份 HTML；HTML 输入不再传 --theme
sau article render --content-file examples/article.md --theme modern --output output/article.html
sau dayu upload-article --account creator --title "如何阅读作品数据面板" --content-file output/article.html --source "无需标注" --cover-indices 1
```

完整示例见 [dayu_article.html](../examples/dayu_article.html)。纯文字文件会按每一行生成段落，不把其中的 HTML 字符当作格式。

## 图片和封面

正文中的图片使用本地路径。相对路径以 **正文文件所在目录** 为起点；绝对路径也可以使用。程序按文章中的图片位置上传，保留图文顺序。

每张图片最大 5 MB，须能在本地正常解码。网络图片地址、`data:` 图片和 `file:` URL 尚未支持，请先准备本地图片。可以传入带图片内联样式的 HTML，但图片通过平台上传器插入，使用平台默认图片排版，原图 CSS 或尺寸不会保留。

横版封面可以从正文图片中选择，序号按正文出现顺序从 1 开始：

```powershell
# 单封面：使用正文第 1 张图片
--cover-indices 1

# 三封面：按指定顺序使用正文第 1、3、2 张图片
--cover-indices 1 3 2
```

三封面需要 3 个不同的正文图片序号。程序会按页面的默认裁剪框生成封面。省略 `--cover-indices` 时沿用页面的封面设置。

## 页面其他功能

下表按当前图文发布页整理，部分功能可能受账号权限影响。

| 页面功能 | 当前命令支持情况 |
| --- | --- |
| 作者名称 | 选填，使用 `--author`；最多 10 字，英文按半字计数并向上取整；省略时沿用网页值 |
| 设为默认作者 | 尚未支持修改 |
| 单封面、三封面 | 支持从正文图片选择，使用 `--cover-indices` |
| 竖版封面 | 尚未支持 |
| 个人素材库选图 | 尚未支持，当前使用正文文件引用的本地图片 |
| 定时发布 | 支持 `--schedule`；北京时间 2 小时后至 7 天内，5 分钟一档 |
| 导入文档 | 网页支持 doc/docx/pdf/txt，最大 5 MB；尚未接入，当前命令使用 HTML/Markdown/TXT 文件 |
| 正文插入视频 | 尚未支持 |
| 创作助手：标题、错别字、违规广告检测 | 沿用网站设置，尚未提供配置参数 |
| 网页预览 | 发表过程中会进入预览并确认；没有独立预览命令 |
| 保存草稿、清空 | 尚未提供对应命令 |

## 查看发布结果

发表成功时返回作品 ID，表示平台已确认本次发表；不等待审核或公开访问。提交前会核对编辑器的正文、图片顺序及支持的格式；有主题样式时还会检查服务端预览中的兼容排版。

如果网络中断等原因导致发表结果未确认，使用日志给出的结果文件只读查询原作品，避免重复发表：

```powershell
sau dayu verify --account creator --result "cookies/dayu_results/本次结果文件.json"
```

查询找到已提交的原作品即成功，仍在审核中也会返回成功。定时作品会同时核对结果文件里的预定时间，确认安排即成功。也可以按作品 ID 查询：

```powershell
sau dayu verify --account creator --type article --content-id "作品ID"
```

需要额外核对公开文章时，主动添加 `--public`：

```powershell
sau dayu verify --account creator --result "cookies/dayu_results/本次结果文件.json" --public --timeout 900
```

公开检查会等待文章可公开访问，核对标题、账号和图片加载；使用本次结果文件还会比对完整正文、图文顺序和支持的格式，主题文章还会核对文字颜色和背景色，成功时返回公开文章链接。公开检查是独立操作，不影响发表操作已确认的成功结果。

默认等待每张图片上传最多 600 秒，可用 `--upload-timeout` 调整，单位为秒。`--headed` 显示 Chrome，`--debug` 出错时保存截图。
