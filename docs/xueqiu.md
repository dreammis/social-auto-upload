# 雪球长文

支持 UTF-8 HTML、Markdown、TXT 正文。图片写在原稿对应位置，程序上传本地图片并在该处插入；支持独立封面、公开/私人分享和创作声明。已使用正式 CLI 验证 HTML 结构、段间配图、封面、真实发表及后台原作品查询。

## 首次安装

先按[项目安装说明](./install.md)安装 Python 3.10–3.12、依赖和 `sau` 命令，并从 `conf.example.py` 复制生成本地 `conf.py`。雪球使用已安装的 Google Chrome；安装 Chromium 不等于安装 Chrome。Chrome 不在默认位置时，在 `conf.py` 中配置 `LOCAL_CHROME_PATH` 为本机实际可执行文件路径，默认留空则使用系统 Chrome 通道。

推荐使用 Markdown 原稿。需要 Node.js 22+，首次执行 `sau article setup` 安装渲染依赖。仓库提供带两张段间配图的 [Markdown 示例](../examples/xueqiu_article.md)，配图文件随仓库提供，直接从项目根目录运行：

```powershell
sau article setup
sau xueqiu upload-article --account creator --title "雪球文章示例" --content-file examples/xueqiu_article.md --visibility 私人 --declaration "本文包含AI生成内容" --prepare-only
```

运行前先按下一节登录。准备预览仍会自动保存远端草稿；确认内容后，实际发表时去掉 `--prepare-only`。

也支持 [HTML 示例](../examples/xueqiu_article.html)和 TXT，这两种格式不需要 Node.js。

## 登录一次

```powershell
sau xueqiu login --account creator --expected-name "你的雪球昵称"
sau xueqiu check --account creator
```

登录时在打开的 Chrome 中完成验证。程序保存本地会话并绑定用户 ID，同一别名不会覆盖其他账号。账号密码无需写入命令或源码。后续上传与查询复用该会话。

默认使用可见 Chrome；本机无头访问曾被平台拦截，可显式传 `--headless`，但不能把访问拦截当作登录失效。

## 原稿与配图

Markdown 示例，图片路径相对于**原稿文件所在目录**：

```markdown
# 第一部分

图片前面的段落，含**加粗**文字。

![第一张配图](images/第一张.png)

## 第二部分

这段位于两张图片之间。

![第二张配图](images/第二张.jpg)

第二张图之后的结尾。
```

HTML 也使用同样的原稿顺序：

```html
<h1>第一部分</h1>
<p>图片前面的段落，含<strong>加粗</strong>文字。</p>
<img src="images/第一张.png">
<h2>第二部分</h2>
<p>这段位于两张图片之间。</p>
<img src="images/第二张.jpg">
<p>第二张图之后的结尾。</p>
```

Markdown 使用 `# 标题`、`## 小标题`、`**加粗**` 和 `![说明](images/配图.png)`。首次使用 Markdown 需要 Node.js 22+，在仓库中执行 `sau article setup` 安装现有渲染依赖。图片接受本地 GIF/JPEG/PNG，必须存在且非空；不接受网络图片地址或 data URL。

雪球采用自己的原生样式：各级标题统一为平台小标题；保留段落、加粗、斜体和链接；列表转为保留编号/圆点的段落；引用保留文字和段落。自定义颜色、字体、间距等 CSS 不保证保留，结果文件会列出发生的转换。表格、代码块、分隔线等尚未验证的结构会在创建远端草稿前明确报错。

## 发表

```powershell
sau xueqiu upload-article --account creator --title "文章标题" --content-file "文章.md" --declaration "本文包含AI生成内容"
```

不传 `--prepare-only` 就会实际发表。`--visibility` 可选 `公开`、`私人`，默认公开；测试或仅自己查看时明确传 `--visibility 私人`。`--declaration` 必须按实际情况选择 `不添加创作声明` 或 `本文包含AI生成内容`。

独立封面可选 `--cover "封面.png"`，采用平台默认裁剪区域。正文图片只从原稿读取，没有文末追加图片参数。标题须为非空单行，正文须有文字；大小及长度限制以平台校验为准。

只想检查时增加 `--prepare-only`。雪球在编辑时会自动保存远端草稿，此模式会核对预览并保存截图；重复运行可能新增草稿。若页面恢复了已有文章，程序会拒绝覆盖。`--debug` 保存失败截图。

## 结果与异常查询

发表成功返回 `status: published` 和作品 ID；程序核对最终受理的主体、标题、分享范围与正文，并在已发布管理列表按 ID 查询。`management_verified: true` 表示后台原作品查询也通过。私人文章显示“仅自己可见”，不代表未发表。

`prepared` 只表示草稿/预览检查完成。命令输出结果 JSON 路径，结果及截图保存在账号目录的 `xueqiu_results` 下。

提交遇到超时或 `submission_unknown` 时，只查询原作品，不重复上传：

```powershell
sau xueqiu verify --account creator --result "本次结果文件.json"
```

此命令按结果文件中的原作品 ID、标题、账号及分享范围核对后台，并使用发表时记录的原稿路径重查后台正文和图片。查询前请保留原稿和图片且不要修改内容；原稿改变时明确报错。旧版未记录原稿路径的成功结果仅核查作品身份和分享范围，不代表重新验证正文。没有 ID 时应先在后台按标题和时间核查，不直接重跑发表。平台已受理但后续检查报错时，保留该 ID 查询，避免重复作品。

本次账号的完整长文表单没有观察到定时设置；视频、Word 导入、自定义封面裁剪、@好友、话题和股票关联尚未接入。

## 开发验证

完成项目安装、Chrome 安装和 `sau article setup` 后，可执行：

```powershell
python -m unittest tests.test_xueqiu_uploader tests.test_article_render tests.test_sau_browser_cli -v
```

这些测试使用临时文件、本地浏览器页面和模拟查询响应，不需要雪球账号，也不会发表文章。分页查询包含模拟测试；不同系统和账号仍需在各自环境验证，当前真实发表验收环境为 Windows Chrome。
