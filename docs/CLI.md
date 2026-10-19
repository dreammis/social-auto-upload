# CLI 使用说明

项目现在提供一个统一的 CLI 入口 `sau`，当前主线已经接入：

- `douyin`
- `kuaishou`
- `xiaohongshu`
- `bilibili`
- `tencent`
- `baijiahao`
- `alipay`
- `weibo`
- `hupu`
- `youtube`
- `facebook`：Facebook 个人主页视频/图文立即发布、查询和删除（默认代理 `http://127.0.0.1:10808`）
- `facebook-page`：Meta Business Suite 的 Facebook Page 视频/图文立即或定时发布
- `dayu`
- `xueqiu`：HTML/Markdown/TXT 长文、原位置配图及封面，默认实际发表，支持按原作品 ID 查询结果；见 [雪球使用说明](./xueqiu.md)，已实测正式 CLI 发表及后台核验

文章本地处理命令为 `sau article`，支持主题列表、环境准备和 Markdown/HTML 文件渲染，见 [文章文件与主题渲染](./article.md)。

实现说明：

- `sau_cli.py` 是当前 CLI 的主入口和唯一主要实现文件
- `sau.exe` 是安装后在 Windows 虚拟环境里自动生成的命令入口，本质上还是调用 `sau_cli.py`
- 如果需要给 OpenClaw、Codex 等 agent 使用，可参考仓库内 skill：
  - `skills/douyin-upload/`
  - `skills/kuaishou-upload/`
  - `skills/xiaohongshu-upload/`
  - `skills/bilibili-upload/`
  - `skills/xueqiu-upload/`
  - `skills/facebook-upload/`
  - `skills/meta-upload/`

视频号、百家号和支付宝生活号目前只有 CLI 入口，暂未提供对应的 skill。

## 安装 CLI 入口

如果你希望直接使用 `sau` 命令，而不是手动执行 `python sau_cli.py`，先在项目根目录安装一次：

```bash
uv pip install -e .
```

安装后就可以直接使用：

```bash
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
sau tencent --help
sau baijiahao --help
sau alipay --help
sau weibo --help
sau hupu --help
sau youtube --help
sau facebook --help
sau facebook-page --help
sau dayu --help
sau xueqiu --help
```

## 安装 patchright 浏览器

Windows 下推荐先指定镜像，再安装 Chromium：

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

## 大鱼号 CLI 子命令

登录、分类和来源选项见 [视频发布](./dayu.md)；正文文件、格式和图片路径见 [图文发布](./dayu-article.md)。Markdown 主题及独立本地渲染命令见 [文章文件与主题渲染](./article.md)。

```powershell
sau dayu upload-article --account creator --title "如何阅读作品数据面板" --content-file examples/dayu_article.html --source "无需标注" --cover-indices 1

# Markdown 首次使用需要 Node.js 22+，先安装渲染依赖
sau article setup
sau dayu upload-article --account creator --title "如何阅读作品数据面板" --content-file examples/article.md --theme modern --source "无需标注" --cover-indices 1
```

Markdown 默认主题为 `default`，可选 `default/grace/simple/modern/plain`；HTML/TXT 不使用 `--theme`。主题会自动转换为大鱼号兼容排版，保留文字颜色、背景和近似字号，圆角、字体和间距等效果可能与本地预览不同。确认发表前会检查服务端预览；平台确认最终发表后即返回成功，不等待审核。

视频和文章均支持 `--schedule "YYYY-MM-DD HH:MM"`：北京时间 2 小时后至 7 天内，分钟为 5 的倍数。平台确认原作品和定时安排后即成功，不等待到点。使用结果文件执行 `sau dayu verify --account creator --result "本次结果文件.json"` 可只读核对原作品与时间，勿重新上传。Agent 可使用仓库的 [大鱼号 Skill](../skills/dayu-upload/SKILL.md)。

## 抖音 CLI 子命令

```bash
sau douyin login --account <account_name>
sau douyin login --account <account_name> --headless
sau douyin check --account <account_name>
sau douyin upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 运动,训练
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文示例" --tags 图文,测试
```

抖音短信验证码补充说明：

- 视频发布过程中如果触发短信二次验证，CLI 会优先读取项目根目录下的 `verify_code.txt`
- 如果未找到 `verify_code.txt`，并且当前命令是在交互式终端中手动运行，CLI 会直接在终端提示输入验证码
- 对 agent、自动任务、远程桥接这类场景，仍然可以继续用写入 `verify_code.txt` 的方式喂验证码
- 验证通过后，程序会自动清理 `verify_code.txt`

## 快手 CLI 子命令

```bash
sau kuaishou login --account <account_name>
sau kuaishou check --account <account_name>
sau kuaishou upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 运动,训练
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文示例" --tags 图文,测试
```

## 小红书 CLI 子命令

```bash
sau xiaohongshu login --account <account_name>
sau xiaohongshu check --account <account_name>
sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 小红书,视频
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文示例" --tags 图文,测试
```

海外环境如果无法登录默认创作者后台，可以通过环境变量切换到 RedNote 域名。该设置同时作用于登录、cookie 校验、视频发布和图文发布：

```bash
SAU_XHS_CREATOR_BASE_URL=https://creator.rednote.com sau xiaohongshu login --account <account_name>
```

## Bilibili CLI 子命令

```bash
sau bilibili login --account <account_name>
sau bilibili check --account <account_name>
sau bilibili upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tid 249 --tags 足球,测试 --thumbnail covers/demo.png
```

补充说明：

- `creator` 之类的名字只是示例值，真正传的是用户自定义的 `account_name`
- 一个 `account_name` 对应一个账号文件，可以准备多个账号并发使用
- 浏览器平台统一元数据约定：
- 视频使用 `title + desc + tags`
- 抖音、快手、小红书的图片笔记使用 `title + note + tags`
- 大鱼号文章使用 `title + content-file + source`，正文从 UTF-8 文件读取
- `sau bilibili ...` 会自动准备 `biliup`
- 如果本地没有 `biliup`，第一次运行会自动下载
- 如果上游 GitHub Release 有更新，运行时会先自动更新
- `sau bilibili login --account <name>` 建议由用户自己在本地真实终端里执行；如果终端里的二维码显示不完整，可直接打开当前目录下的 `qrcode.png` 扫码

## 视频号 CLI 子命令

```bash
sau tencent login --account <account_name>
sau tencent check --account <account_name>
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 视频号,测试
```

视频号支持定时发布、草稿、合集和双比例封面：

```bash
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --schedule "2026-03-24 21:30" --thumbnail-landscape covers/landscape.png --thumbnail-portrait covers/portrait.png --collection "我的合集"
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --draft
```

视频号登录和上传依赖浏览器中的登录态。无头模式下如果需要扫码，CLI 会生成临时二维码；需要人工查看页面时可以加 `--headed`。

## 百家号 CLI 子命令

```bash
sau baijiahao login --account <account_name>
sau baijiahao check --account <account_name>
sau baijiahao upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 百家号,测试
```

百家号当前支持登录、账号检查和视频上传；支持 `--thumbnail` 与 `--collection`，暂不支持 `--schedule`。上传前需要先完成百度账号登录并保存账号文件。

## 支付宝生活号 CLI 子命令

```bash
sau alipay login --account <account_name>
sau alipay check --account <account_name>
sau alipay upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 生活号,测试
```

支付宝生活号当前支持登录、账号检查和视频上传；支持 `--thumbnail` 与 `--collection`，暂不支持图文上传和 `--schedule`。首次使用前需要在支付宝内容创作后台完成登录，并确认账号已开通生活号内容创作权限。

## YouTube CLI 子命令

```bash
sau youtube login --account <account_name>
sau youtube check --account <account_name>
sau youtube upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags tag1,tag2 --playlist "我的系列" --visibility public
sau youtube upload-video --account <account_name> --file videos/demo.mp4 --title "定时视频" --schedule "2026-10-21 10:30"
```

YouTube 登录需要在浏览器中完成 Google 账号登录，不使用二维码。`--visibility` 可选 `public`、`unlisted` 或 `private`，`--playlist` 可选；传 `--schedule` 时使用 YouTube Studio 的 Schedule 状态并核对日期/时间控件，不传则立即按 `--visibility` 发布。

## Facebook CLI 子命令

个人主页使用 `facebook`，Page 使用 `facebook-page`。默认代理为 `http://127.0.0.1:10808`；个人主页也可通过 `SAU_FACEBOOK_PROXY` 配置，`--proxy ""` 明确关闭代理。账号文件分别保存，首次使用先登录对应入口。

```powershell
sau facebook login --account creator
sau facebook check --account creator
sau facebook upload-video --account creator --file videos/demo.mp4 --title "视频标题" --desc "正文"
sau facebook upload-note --account creator --images images/1.jpg --title "图文标题" --note "正文"
sau facebook-page login --account creator
sau facebook-page upload-note --account creator --page "我的 Page" --images images/1.jpg --title "图文标题" --note "正文" --schedule "2026-10-21 10:30" --result .local/page-result.json
sau facebook-page upload-video --account creator --page "我的 Page" --file videos/demo.mp4 --title "视频标题" --desc "正文" --schedule "2026-10-21 10:30" --result .local/reel-result.json
```

个人主页支持视频、图片及正文立即发布，目前未接入个人主页定时。Page 视频和图文支持 `--schedule "YYYY-MM-DD HH:MM"`，使用北京时间，要求至少提前 2 小时；不传即立即提交。当前实现核对 `Asia/Shanghai` 浏览器时区、页面日期/时间及原作品列表安排。`--page` 应填写准确 Page 名称。

Page 发布结果默认保存在 `.local/meta-results/`，也可用 `--result` 指定 JSON 文件。结果包含 `page_id`、`page_name`、`content_id`（视频处理中可能暂时没有）和状态。`scheduled` 表示平台已确认排期并核对原记录；`published` 表示图文已发布并核对原记录；立即发布视频在创建响应无错误且完成弹窗出现后返回 `processing`，表示平台已受理并正在处理，不能当成已经公开播放，后续作品编号由平台生成时再查询。`submission_unknown` 仅表示提交响应或完成证据没有确认，必须先查原记录，禁止直接重发。

### 查询与删除

```powershell
sau facebook verify --account creator --post-url "https://www.facebook.com/reel/作品编号/" --owner-id "作者数字ID" --expected-text "原作品正文"
sau facebook delete --account creator --post-url "原作品链接" --owner-id "作者数字ID" --expected-text "原作品正文"
sau facebook delete --account creator --post-url "原作品链接" --owner-id "作者数字ID" --expected-text "原作品正文" --from-trash --permanent
sau facebook-page verify --account creator --page "我的 Page" --page-id "Page数字ID" --content-id "内容编号" --expected-text "原作品正文" --scheduled
sau facebook-page delete --account creator --page "我的 Page" --page-id "Page数字ID" --content-id "内容编号" --expected-text "原作品正文" --scheduled --result .local/delete-result.json
```

个人主页删除默认移至垃圾箱；加 `--permanent` 可永久删除，已经在垃圾箱中的作品再加 `--from-trash`。查询垃圾箱同样使用 `verify --from-trash`。`verify --deleted` 仅查询原编号是否已不在垃圾箱，返回 `absent_from_trash`，不凭“没找到”证明曾经永久删除。

Page 的 `--scheduled` 选择定时列表，删除会取消排期并永久移除。已发布作品不加该参数，当前平台执行移至垃圾箱，返回 `trashed`，30 天后由平台删除；CLI 尚未接入 Page 垃圾箱的提前永久删除。定时作品发布后编号可能变化，管理已发布作品请使用已发布列表中的编号。

所有删除动作先核对作者或 Page、原作品编号和正文。正文相同且无法唯一定位时明确失败。当前查询覆盖列表已加载的近期作品，不保证自动翻页检索全部历史作品。删除之后重新查询服务器列表；若结果未知，先查询，不自动重删。删除远端作品不会删除本地素材。

Instagram 按用户要求暂停；后续走独立 Instagram 网页发布，不使用 Business Suite 绑定方式。本轮不增加前后端页面或接口。

## 微博 CLI 子命令

```bash
sau weibo login --account <account_name>
sau weibo check --account <account_name>
sau weibo upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 微博,测试 --thumbnail covers/demo.png
```

微博当前支持登录、账号检查和视频上传；标题最多 30 个字，封面图建议小于 5 MB，暂不支持图文上传和 `--schedule`。

## 虎扑 CLI 子命令

```bash
sau hupu login --account <account_name>
sau hupu check --account <account_name>
sau hupu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags 虎扑,测试 --thumbnail covers/demo.png
```

虎扑当前支持登录、账号检查和视频上传；标题长度要求为 4–40 个字，暂不支持图文上传和 `--schedule`。虎扑登录可能需要在浏览器中完成 QQ 或手机号登录，需要人工查看页面时可以加 `--headed`。

## 登录二维码说明

- 抖音、快手、小红书、视频号、百家号、支付宝生活号、微博和虎扑登录过程中，CLI / uploader 可能会生成临时二维码图片
- 对普通用户来说，可以直接打开该图片扫码
- 对可操作本地文件的 agent 来说，不要只把图片路径告诉用户
- 这类二维码图片本身就是给用户扫码的，agent 应优先直接展示/发送本地图片给用户
- Bilibili 和 YouTube 当前不走这套本地二维码图片托管链路，登录按上面的平台说明处理即可

## 定时发布

抖音、快手、小红书、视频号的图文或视频上传、Bilibili 的视频上传，以及大鱼号的视频和文章上传支持 `--schedule`。只要传了 `--schedule`，CLI 就会自动切换到对应平台的定时发布策略；不传则默认立即发布。大鱼号时间固定为北京时间，范围为 2 小时后至 7 天内、5 分钟一档。百家号、支付宝生活号、微博和虎扑当前不支持 `--schedule`。

```bash
sau douyin upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --schedule "2026-03-24 21:30"
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文示例" --schedule "2026-03-24 21:30"
sau kuaishou upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --schedule "2026-03-24 21:30"
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文示例" --schedule "2026-03-24 21:30"
sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --schedule "2026-03-24 21:30"
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文示例" --schedule "2026-03-24 21:30"
sau bilibili upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tid 249 --schedule "2026-03-24 21:30"
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --schedule "2026-03-24 21:30"
```

## 运行时参数

CLI 将 `debug` 和 `headless` 拆成了两个独立维度：

```bash
--debug
--headless
--headed
```

- `--debug`: 打开调试行为，例如失败时保留更多调试信息
- `--headless`: 无头模式运行
- `--headed`: 有头模式运行

如果都不传，CLI 当前默认按 `headless=True` 运行。

补充：

- 抖音和快手的 CLI 默认都是无头模式
- 如果用户明确要求可见浏览器窗口，或确实需要人工看页面，再显式传 `--headed`

## 视频上传参数

```bash
--file videos/demo.mp4
--title "示例标题"
--desc "示例简介"
--tags 运动,训练
--thumbnail videos/demo.png
--thumbnail-landscape videos/cover-4x3.png
--thumbnail-portrait videos/cover-3x4.png
```

抖音和视频号支持同时设置两种比例的封面图：

- `--thumbnail-landscape`: 4:3 横版封面
- `--thumbnail-portrait`: 3:4 竖版封面
- `--thumbnail`: 兼容旧参数，等同于 3:4 竖版封面

视频号、百家号和支付宝生活号支持使用 `--collection` 指定已有合集；百家号和支付宝生活号还支持 `--thumbnail` 指定封面图。

抖音额外支持：

```bash
--product-link https://example.com/item
--product-title 示例商品
```

Bilibili 额外要求：

```bash
--tid 249
```

- `--tid` 第一版是必填
- `--tags` 会映射到 `biliup upload --tag`
- `--schedule` 会映射到 Bilibili 所需的时间戳参数

## 图片笔记上传参数

```bash
--images videos/1.png videos/2.png videos/3.png
--title "图文标题"
--note "图文内容"
--tags 图文,测试
```

图片笔记上传当前限制：

- 抖音：最多 35 张图片，不支持 GIF
- 快手：支持多张图片，建议传真实不同文件，不要把同一路径重复多次
- 小红书：支持多张图片，正文 `--note` 可选，但 `--title` 建议始终显式传入

大鱼号文章使用 `--content-file` 提供 HTML、Markdown 或 TXT 正文文件，支持本地图片和图文混排，正文最多 2 万字；来源与封面等参数见 [大鱼号图文发布](./dayu-article.md)。

后续维护 CLI 时，优先看 `sau_cli.py`、`uploader/` 和 `skills/`。
