# 文章文件与主题渲染

文章正文通过 UTF-8 文件传入，支持 HTML、Markdown 和纯文字 TXT。长正文留在文件中，命令行只需要提供路径。

## Markdown 渲染准备

安装 Node.js 22 或更新版本（包含 npm），然后在安装本项目的 Python 环境中执行一次：

```powershell
sau article setup
```

此命令按项目锁定版本安装渲染依赖。后续本地渲染不需要联网。只使用 HTML/TXT 时无需安装 Node.js。

## 转换与预览

```powershell
# 列出主题
sau article themes

# Markdown 转为带主题的 HTML
sau article render --content-file examples/article.md --theme grace --output output/article.html

# 仅转换文章结构，不附加主题样式
sau article render --content-file examples/article.md --theme plain --output output/plain.html

# 已有 HTML 生成预览文件；保留原有内联样式
sau article render --content-file article.html --output output/preview.html
```

用浏览器打开输出文件即可预览。输出文件已存在时会报错，需要覆盖时加 `--overwrite`；输入原稿始终不能被覆盖。

| 主题 | 用途 |
| --- | --- |
| `default` | 默认主题，经典标题和强调色 |
| `grace` | 圆角引用、柔和装饰 |
| `simple` | 轻量装饰、清晰留白 |
| `modern` | 暖色、圆角、宽松行距 |
| `plain` | 只转换标题、段落、列表等结构，使用目标平台原生排版 |

Markdown 省略 `--theme` 时使用 `default`。HTML/TXT 不接受 `--theme`，不会再次套用主题。四套彩色主题使用 [baoyu-md](https://github.com/JimLiu/baoyu-skills/tree/main/packages/baoyu-md) 渲染。

## 正文和图片

Markdown 支持标题、加粗、斜体、引用、列表、分隔线、链接、代码块、表格和本地图片。HTML 支持对应的文章元素及内联 `style`；例如：

```html
<h2 style="color:#2563eb">本节标题</h2>
<p style="line-height:1.8">正文与<strong>重点</strong>。</p>
<img src="images/example.png" alt="配图说明">
```

图片相对路径以原稿所在目录为起点。输出到其他目录后仍引用原稿的本地图片，因此可在同一台电脑上预览，也可再次作为文章文件传入。本地图片不会嵌入输出文件，分享或迁移时还需一并提供图片。

当前不支持网络图片、`data:` 图片、`file:` URL、外部样式表、`<style>`、脚本、iframe、SVG、公式和图表扩展。Mermaid、PlantUML 等图表请先导出为本地图片。TXT 按行生成段落，文件中的 HTML 字符会作为普通文字显示。

## 发布到平台

本地渲染命令只生成文件。发布时继续使用对应平台的文章命令，并按该平台支持的格式准备正文。渲染器支持的格式不代表每个平台都支持。

大鱼号可以直接接收 Markdown 并先渲染主题，再导入 HTML：

```powershell
sau dayu upload-article --account creator --title "如何阅读作品数据面板" --content-file examples/article.md --theme modern --source "无需标注" --cover-indices 1
```

也可以先用 `sau article render` 生成主题 HTML，再把输出文件交给 `--content-file`。两条路径均不会切换成 `plain`；省略主题时使用 `default`。

大鱼号会自动将主题 HTML 转换为兼容排版，保留文字颜色、背景色和近似字号，正文仍可选择和复制；确认发表前会检查服务端预览。圆角、精确字号、字体、间距和边框可能与本地预览不同。本地渲染器仍输出完整主题 HTML，其他平台可以使用同一份原稿和渲染结果，再按各自的格式要求接入。

需要大鱼号原生排版时可显式指定 `--theme plain`。斜体、代码块、用户输入的表格等未接入格式会在上传前报错。其他要求见 [大鱼号图文发布](./dayu-article.md)。
