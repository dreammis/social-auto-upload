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
- `facebook`：Facebook 个人主页视频/图文立即发布、查询和删除
- `facebook-page`：Meta Business Suite 的 Facebook Page 视频/图文立即或定时发布
- `dayu`
- `xueqiu`：HTML/Markdown/TXT 长文、原位置配图及封面，默认实际发表，支持按原作品 ID 查询结果；见 [雪球使用说明](./xueqiu.md)，已实测正式 CLI 发表及后台核验
- `zhihu`：文章、视频和定时发布；见仓库内 [知乎 Skill](../skills/zhihu-upload/SKILL.md)

文章本地处理命令为 `sau article`，支持主题列表、环境准备和 Markdown/HTML 文件渲染，见 [文章文件与主题渲染](./article.md)。

实现说明：

- `sau_cli.py` 负责组装命令和启动执行；`sau_commands/<平台>.py` 各自维护参数、请求数据和执行逻辑，`sau_commands/arguments.py` 维护共用参数规则
- `sau.exe` 是安装后在 Windows 虚拟环境里自动生成的命令入口，本质上还是调用 `sau_cli.py`
- 如果需要给 OpenClaw、Codex 等 agent 使用，可参考仓库内 skill：
  - `skills/douyin-upload/`
  - `skills/kuaishou-upload/`
  - `skills/xiaohongshu-upload/`
  - `skills/bilibili-upload/`
  - `skills/dayu-upload/`
  - `skills/xueqiu-upload/`
  - `skills/zhihu-upload/`
  - `skills/facebook-upload/`
  - `skills/meta-upload/`
  - `skills/instagram-upload/`

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
sau zhihu --help
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

## 知乎 CLI 子命令

知乎提供文章和视频发布。文章使用 HTML/Markdown/TXT 原稿，正文图片按原稿位置导入；视频文件须大于 100KB（102400 字节）、最大 20GB、最长 4 小时。

```powershell
sau zhihu login --account creator
sau zhihu check --account creator
sau zhihu upload-article --account creator --title "知乎文章标题" --content-file examples/article.md
sau zhihu upload-video --account creator --file videos/demo.mp4 --title "知乎视频标题" --desc "视频简介" --originality original --category "教育" --video-mark "含 AI 生成内容"
# 上传素材后导出该表单的全部领域和视频标记；不发表，但可能留下草稿。
sau zhihu upload-video --account creator --file videos/demo.mp4 --title "知乎视频标题" --originality original --show-options
```

`--account` 是本地会话别名，与知乎展示名无须相同。登录命令读取页面当前身份并保存本地会话。

`--category` 与 `--video-mark` 使用 CLI 可选值，完整领域清单见 `sau zhihu upload-video --help`。省略时在交互终端按编号选择；非交互调用必须指定。程序提交前仍核对实时菜单，`--show-options` 将候选写入结果 JSON 的 `options`。

`--originality` 可选 `original`（原创）、`reprint`（转载）。`--video-mark` 可选 `内容无需标注`、`含 AI 生成内容`、`含虚构演绎内容`、`内容含营销信息`、`内容为转载`、`个人观点仅供参考`，须按实际内容选择。视频标题 5–50 字，简介最多 300 字；暂不支持自动选择话题、自定义封面、专栏和内容来源。

文章标题最多 100 字。图片写在原稿里，例如 `![配图](images/1.png)`，相对路径从原稿目录解析。提交前核对文字、图片位置、基本格式和链接；恢复非空草稿时停止以保护原文。Markdown 首次使用先执行 `sau article setup`。暂不支持自定义主题 CSS、手动封面、专栏收录和文档导入。

文章和视频加 `--prepare-only` 可只填写检查，平台仍可能自动保存草稿。`published` 表示平台确认发表；结果为 `submission_unknown` 时先检查创作中心原作品，勿重复上传。已有链接时用 `sau zhihu verify --account creator --result "本次结果.json"` 核对，视频详情地址可为 `/pin/<作品ID>`。

`--schedule "YYYY-MM-DD HH:MM"` 为实验性选项，按北京时间限制在 30 分钟后至 48 小时内，尚不保证完整排期流程可用。更多用法见 [知乎 Skill](../skills/zhihu-upload/SKILL.md)。

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

个人主页使用 `facebook`，Page 使用 `facebook-page`。默认不配置代理，浏览器按系统网络直连。需要代理时可在命令中传 `--proxy "代理地址"`，或设置 `SAU_FACEBOOK_PROXY`、`SAU_FACEBOOK_PAGE_PROXY`；传 `--proxy ""` 可忽略环境变量并直连。账号文件分别保存，首次使用先登录对应入口。

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

## Instagram 独立网页发布

Instagram 使用工程的 Patchright Chrome，不依赖 Facebook Page 或 Business Suite 绑定。默认可见浏览器，未配置代理时按系统网络直连；需要代理时可使用 `--proxy` 或 `SAU_INSTAGRAM_PROXY`。传 `--proxy ""` 可忽略环境变量并直连。首次使用先安装依赖和 Chrome，按本文的项目环境准备步骤执行。

```powershell
sau instagram login --account creator
sau instagram check --account creator
sau instagram upload-video --account creator --file videos/demo.mp4 --thumbnail covers/demo.png --title "视频标题" --desc "正文" --tags 生活,分享 --result .local/instagram-video.json
sau instagram upload-note --account creator --images images/1.jpg --title "单图标题" --note "正文"
sau instagram upload-note --account creator --images images/1.jpg images/2.jpg --title "轮播标题" --note "正文" --result .local/instagram-carousel.json
```

视频/Reel 可用 `--thumbnail` 指定 JPG/JPEG/PNG 封面；省略时使用 Instagram 默认封面。指定图片后会检查主预览确实使用该图片，失败则停止提交。封面按当前视频画幅居中裁剪，图片边缘的重要文字应留出安全区域。图文发布不接受此参数。

`login` 在工程浏览器中等待人工登录和必要验证，将状态保存为 `cookies/instagram_creator.json`，并通过新会话验证。`check` 检查该账号的登录状态和用户绑定，不能代替发布权限检查；网络或未知页面超时会报告错误，不会直接视为 Cookie 失效。

视频输入为 MP4/MOV；照片为 JPG/JPEG/PNG/AVIF/HEIC/HEIF，实际解码与处理受平台限制。多个图片路径按传入顺序创建轮播；当前已实测单张照片及两张不同照片。标题、正文、标签合并为配文，合计最多 2200 字符。`--headless` 可切换无头运行，人工登录使用默认可见模式。

当前账号的照片/Reels 发布页及高级设置中没有定时入口，因此此独立网页实现只支持立即发布，不提供 `--schedule`；这不代表所有 Instagram 账号和客户端都没有定时能力。页面还提供地点、协作者、AI 标签、隐藏点赞/播放数、关闭评论，照片提供替代文字与滤镜，视频提供裁剪和声音；上述选填功能当前未接入 CLI，保留页面默认设置。首次通知提示会自动选择稍后，视频上传时的 Reels 介绍会自动确认；没有提示则继续。登录、验证仍由用户在工程浏览器完成，未知弹窗或操作失败会明确报错。

成功返回 `published`、`content_id`、`post_id`、`post_url` 和 `media_count`。Reels 可能先处于 `processing`，程序会等待本次提交的最终创建结果；超时后保留已观察状态。`submission_unknown` 表示已进入提交但未确认平台结果，`processing` 表示平台已受理且尚未取得最终作品，均不可直接重复上传。默认结果保存在 `.local/instagram-results/`；建议用 `--result` 指定路径。

如果已取得原作品链接：

```powershell
sau instagram verify --account creator --post-url "https://www.instagram.com/p/作品编号/" --expected-text "原作品中的准确文字" --result .local/instagram-verify.json
sau instagram delete --account creator --post-url "https://www.instagram.com/reel/作品编号/" --expected-text "原作品中的准确文字" --result .local/instagram-delete.json
```

接受 `/p/编号/`、`/reel/编号/` 以及带作者名的原作品链接。操作前核对账号绑定、作者、作品编号和正文，拒绝删除其他作者的作品。`delete` 将作品移至 Instagram 的“最近删除”，最终返回 `deleted`；不实现批量删除或提前永久清空。“最近删除”的保留规则由平台决定，本地素材不会被删除。

结果未知且没有链接时，先在同一账号主页按配文、素材和发布时间查找原作品，复制原作品链接再运行 `verify`；找不到不能证明提交失败，也不要直接重发。删除出现 `deletion_unknown` 时同样先查原作品和“最近删除”，不要重复删除。失败结果会包含阶段/错误和本地证据目录；账号状态、截图及页面记录均放在 Git 忽略目录，不应提交到仓库。

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
