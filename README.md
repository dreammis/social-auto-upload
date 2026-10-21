# social-auto-upload

![Python](https://img.shields.io/badge/Python-3.10--3.12-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/github/license/dreammis/social-auto-upload)
![Release](https://img.shields.io/github/v/release/dreammis/social-auto-upload?display_name=tag)

`social-auto-upload` 是一个面向内容创作者和运营者的多平台发布工具，提供统一 CLI 和供 Codex、OpenClaw、Claude Code 等 Agent 使用的 Skill。

支持的视频、文章、图文发布平台及对应入口见下表。

CLI 命令按平台维护在 `sau_commands/`，发布流程位于 `uploader/`。日常变更记录见 [CHANGELOG.md](./CHANGELOG.md)，稳定版本通过 GitHub Release 发布。

<img src="media/show/tkupload.gif" alt="tiktok show" width="800"/>

## 💎 赞助商

<table width="100%">
 <tr>
    <td width="25%" align="center" valign="middle">
      <a href="https://chilltion.com/?ref=1y5k5k">
        <img src="static/DolOffer.png" alt="DolOffer Sponsor" width="180">
      </a>
    </td>
    <td width="75%" align="left" valign="middle">
      感谢 <a href="https://doloffer.com/" target="_blank">DolOffer</a> 对本项目的支持！对于做内容矩阵、多平台分发和 AI 自动化运营的创作者来说，ChatGPT、Claude、YouTube Premium、Spotify、Apple Music、Notion、Office 等数字工具往往是长期成本。DolOffer 提供 AI、视频、音乐和效率工具相关的订阅与充值服务，帮助用户更低成本地配置常用数字产品。更多说明可查看 <a href="https://github.com/Doloffer-g/guide" target="_blank">DolOffer Guide</a>。使用优惠码 <code>AI8888</code> 可额外享受 9 折优惠，具体价格和服务规则以官网为准。  
    </td>
  </tr>
  <tr>
    <td width="25%" align="center" valign="middle">
      <a href="https://chilltion.com/?ref=1y5k5k">
        <img src="static/chilltion.png" alt="chilltion Sponsor" width="180">
      </a>
    </td>
    <td width="75%" align="left" valign="middle">
      轻视AI：一句话生产MG动画，适合知识，科普，讲解，教程，介绍等类型视频的低成本制作，视频矩阵，养号等，成本只有seedance等1%。现在<a href="https://chilltion.com/?ref=1y5k5k">注册</a>送1500积分
    </td>
  </tr>
    <tr>
        <td width="25%" align="center" valign="middle">
          <a href="http://t.clawpower.vip/1005">
            <img src="static/clawpower.png" alt="ClawPower Sponsor" width="180">
          </a>
        </td>
        <td width="75%" align="left" valign="middle">
          ClawPower 是一家稳定可靠 AI 大模型中转服务商，提供 Claude、GPT、Gemini 60+ 大模型接入。无论是 OpenClaw、Hermes 智能体自动化场景，Claude Code、Codex 编程工具接入，还是公众号、小红书内容创作；都能获得稳定、顺滑、可长期使用的模型服务体验。低至官方价格的 30%，点击<a href="http://t.clawpower.vip/1005">免费领取 5 刀现金</a>体验券
        </td>
      </tr>
  <tr>
    <td width="25%" align="center" valign="middle">
      <img src="static/wechat.png" alt="Sponsor Contact" width="150">
    </td>
    <td width="75%" align="left" valign="middle">
      <strong>成为赞助商</strong><br>
      如果您有意赞助本项目，请扫描左侧微信二维码（添加时请注明来意：<strong>赞助</strong>）。
    </td>
  </tr>
</table>

---


## 目录

- [💡 功能特性](#功能特性)
- [💾 安装指南](#安装指南)
- [🤖 AI Agent](#ai-agent)
- [🏁 快速开始](#快速开始)
- [📝 更新日志](./CHANGELOG.md)
- [📃 详细文档](#详细文档)
- [🐾 交流与支持](#交流与支持)
- [🤝 贡献指南](#贡献指南)
- [📜 许可证](#许可证)
- [⭐ Star History](#star-history)

## 💡功能特性

| 平台 | 登录/账号准备 | 视频 | 文章 | 图文 | 定时发布 | CLI | Skill | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 抖音 | ✅ | ✅ | - | ✅ | ✅ | ✅ | ✅ | 视频与图文发布 |
| Bilibili | ✅ | ✅ | - | - | ✅ | ✅ | ✅ | 视频发布；运行时自动准备 `biliup` |
| 小红书（浏览器版） | ✅ | ✅ | - | ✅ | ✅ | ✅ | ✅ | 视频与图文发布 |
| 快手 | ✅ | ✅ | - | ✅ | ✅ | ✅ | ✅ | 视频与图文发布 |
| 视频号 | ✅ | ✅ | - | - | ✅ | ✅ | - | 视频发布 |
| 百家号 | ✅ | ✅ | - | - | - | ✅ | - | 视频发布 |
| 大鱼号 | ✅ | ✅ | ✅ | - | ✅ | ✅ | ✅ | [视频发布](./docs/dayu.md)；[文章发布](./docs/dayu-article.md)支持 HTML/Markdown/TXT、正文图片和封面 |
| 支付宝生活号 | ✅ | ✅ | - | - | - | ✅ | - | 视频发布 |
| 微博 | ✅ | ✅ | - | - | - | ✅ | - | 视频标题最多 30 字 |
| 虎扑 | ✅ | ✅ | - | - | - | ✅ | - | 视频标题 4–40 字 |
| TikTok | ✅ | ✅ | - | - | ✅ | - | - | Chrome 版实现 |
| 雪球 | ✅ | - | ✅ | - | - | ✅ | ✅ | [长文与配图](./docs/xueqiu.md)：支持 HTML/Markdown/TXT、正文图片和封面 |
| YouTube | ✅ | ✅ | - | - | 开发中 | ✅ | - | 视频发布 |
| 知乎 | ✅ | ✅ | ✅ | - | 实验性 | ✅ | ✅ | [文章与视频发布](./skills/zhihu-upload/SKILL.md)，文章支持正文位置配图 |
| Facebook | ✅ | ✅ | - | ✅ | - | ✅ | ✅ | 支持作品查询、移至回收站及永久删除 |
| Facebook Page | ✅ | ✅ | - | ✅ | ✅ | ✅ | ✅ | 支持视频与图文定时发布、查询和取消定时 |
| Instagram | ✅ | ✅ | - | ✅ | - | ✅ | ✅ | 支持 Reels、单图与轮播 |

`✅` 表示支持，`-` 表示不适用或未提供；`开发中`、`实验性` 不计入稳定能力。文章正文可以包含图片，与独立图文发布分列。

### 按内容形态

| 内容形态 | 平台与入口 |
| --- | --- |
| 视频 | 抖音、快手、小红书、Bilibili、视频号、百家号、大鱼号、知乎、YouTube 等；CLI 示例见下方和[CLI 使用说明](./docs/CLI.md) |
| 文章 | 大鱼号[文章发布](./docs/dayu-article.md)、雪球[长文与配图](./docs/xueqiu.md)、知乎[文章发布](./skills/zhihu-upload/SKILL.md#文章) |
| 图文 | 抖音、快手、小红书、Facebook、Facebook Page、Instagram；CLI 示例见[CLI 使用说明](./docs/CLI.md) |

文章主题预览及 Markdown 转 HTML：见 [文章文件与主题渲染](./docs/article.md)。内置 `default/grace/simple/modern/plain` 主题；大鱼号可直接接收 Markdown，并将主题转换为保留文字颜色、背景和近似字号的兼容排版，圆角和精确间距等效果可能与本地预览不同。

## 💾安装指南

### 自己上手使用
普通用户可按以下文档安装和更新：

- [安装说明](./docs/install.md)
- [更新说明](./docs/update.md)


### AI Agent

若使用 `OpenClaw`、`Codex` 或 `Claude Code` 安装和操作本项目，可将仓库与启动提示词一并交给 Agent：

- [Agent Bootstrap Prompt](./docs/agent-bootstrap.md)

它会引导 Agent：

- 优先按当前主线安装项目
- 优先使用 `uv`、`sau` CLI 和 `skills/`
- 先验证 `bilibili`、`douyin`、`kuaishou`、`xiaohongshu` 四个平台入口是否可用


相关入口：

- [CLI 使用说明](./docs/CLI.md)
- [Agent Bootstrap Prompt](./docs/agent-bootstrap.md)
- 平台 Skills：[抖音](./skills/douyin-upload/SKILL.md)、[快手](./skills/kuaishou-upload/SKILL.md)、[小红书](./skills/xiaohongshu-upload/SKILL.md)、[Bilibili](./skills/bilibili-upload/SKILL.md)、[大鱼号](./skills/dayu-upload/SKILL.md)、[雪球](./skills/xueqiu-upload/SKILL.md)、[知乎](./skills/zhihu-upload/SKILL.md)、[Facebook](./skills/facebook-upload/SKILL.md)、[Facebook Page](./skills/meta-upload/SKILL.md)、[Instagram](./skills/instagram-upload/SKILL.md)
- [历史 Web 版本说明](./docs/legacy-web.md)


## 🏁快速开始

### 方式 1：使用 CLI

先按上方平台能力表确认支持范围，再选择下面的内容类型。视频、文章和图文分别使用独立发布命令；文章中的配图仍属于文章正文。

#### 账号准备

每个平台先登录一次，再检查会话。`--account` 是你给本地会话取的名字，例如 `creator`，用于区分多个账号。

```bash
sau douyin login --account creator
sau douyin check --account creator
# 换成 dayu、xueqiu、zhihu 等平台名称即可；具体登录要求见对应文档。
```

#### 视频

按平台选择 `upload-video`：

| 平台 | 平台参数 | 发布说明 |
| --- | --- | --- |
| 抖音、快手、小红书 | `douyin`、`kuaishou`、`xiaohongshu` | [CLI 参数](./docs/CLI.md) |
| Bilibili、视频号 | `bilibili`、`tencent` | [CLI 参数](./docs/CLI.md) |
| 百家号、大鱼号 | `baijiahao`、`dayu` | [大鱼号视频](./docs/dayu.md)、[CLI 参数](./docs/CLI.md) |
| 支付宝生活号、微博、虎扑 | `alipay`、`weibo`、`hupu` | [CLI 参数](./docs/CLI.md) |
| YouTube | `youtube` | [CLI 参数](./docs/CLI.md) |
| 知乎 | `zhihu` | [文章与视频发布](./skills/zhihu-upload/SKILL.md) |
| Facebook、Facebook Page、Instagram | `facebook`、`facebook-page`、`instagram` | [CLI 参数](./docs/CLI.md) |

```bash
sau douyin upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介"
sau kuaishou upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介"
sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介"
sau bilibili upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tid 249
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags tag1,tag2
sau baijiahao upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags tag1,tag2
sau alipay upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags tag1,tag2
sau weibo upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags tag1,tag2
sau hupu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags tag1,tag2
sau youtube upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags tag1,tag2 --playlist "我的系列" --visibility public
sau zhihu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --originality original --category "教育" --video-mark "内容无需标注"
sau facebook upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --tags Facebook,测试
sau facebook-page upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介" --page "我的 Page"
```

#### 文章

文章使用 `upload-article`，正文来自文件，图片应写在原稿对应段落中。支持平台分别如下：

| 平台 | 正文与说明 |
| --- | --- |
| 大鱼号 | HTML / Markdown / TXT、正文插图及封面，见[文章发布](./docs/dayu-article.md) |
| 雪球 | HTML / Markdown / TXT、正文原位置配图及独立封面，见[长文发布](./docs/xueqiu.md) |
| 知乎 | HTML / Markdown / TXT、正文原位置配图，见[文章发布](./skills/zhihu-upload/SKILL.md#文章) |

```bash
sau dayu upload-article --account creator --title "如何阅读作品数据面板" --content-file examples/dayu_article.html --source "无需标注" --cover-indices 1
sau xueqiu upload-article --help
sau zhihu upload-article --account creator --title "文章标题" --content-file examples/article.md
```

#### 图文

图文指独立图片帖、轮播或图片笔记，使用 `upload-note`；支持抖音、快手、小红书、Facebook、Facebook Page 和 Instagram。

```bash
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文正文"
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文正文"
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "图文标题" --note "图文正文"
sau facebook-page upload-note --account <account_name> --images images/1.jpg --title "Page 图文" --note "正文" --page "我的 Page" --schedule "2026-10-21 10:30" --result .local/page-result.json
sau facebook upload-note --account creator --images images/1.jpg images/2.jpg --title "图片帖" --note "正文"
sau instagram upload-note --account creator --images images/1.jpg images/2.jpg --title "图片轮播" --note "正文"
```

知乎的 `--account` 是本地会话别名，不要求和展示名一致；登录时程序直接读取页面当前身份并保存绑定信息。

Facebook、Facebook Page 和 Instagram 默认使用系统网络直连。网络环境需要代理时，给对应命令显式添加 `--proxy "代理地址"`，或设置 `SAU_FACEBOOK_PROXY`、`SAU_FACEBOOK_PAGE_PROXY`、`SAU_INSTAGRAM_PROXY`；传 `--proxy ""` 可忽略环境变量并直连。

> YouTube 说明：登录是交互式的（Google 账号，浏览器里完成，无二维码）。这里走浏览器自动化而不是官方 API，
> 是因为**未通过 Google 合规审核的 API 项目上传的视频会被强制锁为私享、无法改公开**，对个人/单频道不实用；
> 浏览器自动化没有此限制，可直接发布公开视频，也与本项目其它平台的 cookie 方案一致。
> `--playlist` 适合连载/系列追更；`--visibility` 可选 `public`/`unlisted`/`private`。
> 上传会**等进度到 100% 再点发布**（浏览器上传靠窗口开着传，传一半就发布会被掐断卡在中途）。
> youtube.com 被墙的地区：在 `conf.py` 设 `YT_PROXY = "http://127.0.0.1:7890"`（chromium 不吃系统代理，需显式指定）。

Markdown 主题文章首次使用需要 Node.js 22+，先准备渲染依赖，再发布：

```bash
sau article setup
sau article render --content-file examples/article.md --theme modern --output output/article.html
sau dayu upload-article --account <account_name> --title "如何阅读作品数据面板" --content-file examples/article.md --theme modern --source "无需标注" --cover-indices 1
```

`sau article render` 只生成本地 HTML；`sau dayu upload-article` 会实际发表，平台确认发表后即返回成功，不等待审核。HTML/TXT 输入不需要 Node.js，也不使用 `--theme`。大鱼号视频参数和文章格式限制分别见 [视频说明](./docs/dayu.md)、[文章说明](./docs/dayu-article.md)。

补充说明：

- `creator` 之类的名字只是示例值，真正含义是 `account_name`
- 一个 `account_name` 对应一个账号文件，可以准备多个账号，也可以按账号名并发执行任务
- 抖音视频发布若触发短信二次验证，程序会优先读取项目根目录下的 `verify_code.txt`；如果你是在本地交互式终端手动运行 CLI，也可以直接按终端提示输入验证码
- 浏览器平台统一约定：
- 视频使用 `title + desc + tags`
- 抖音、快手、小红书的图片笔记使用 `title + note + tags`
- 大鱼号文章使用 `title + content-file + source`，正文保存在 HTML、Markdown 或 TXT 文件中
- Bilibili CLI 不要求用户手动安装 `biliup`
- 首次运行相关命令时，程序会自动下载 `biliup`
- 后续运行会自动检查上游 release 并更新
- Bilibili 登录建议由用户自己在本地真实终端里执行；如果终端二维码显示不完整，可以直接打开当前目录下的 `qrcode.png` 扫码

### 方式 2：使用 examples

`examples/` 目录里同时存在两类脚本：

- 当前主线 CLI 包装示例
- 历史直连 uploader 示例

对抖音、快手、小红书、Bilibili 来说，当前主线优先使用上面的 `sau ...` CLI。
下面这些脚本主要是历史直连 uploader 示例或调试入口：

- `examples/upload_to_douyin.py`
- `examples/upload_video_to_bilibili.py`
- `examples/upload_to_kuaishou.py`
- `examples/upload_video_to_tencent.py`
- `examples/upload_video_to_baijiahao.py`
- `examples/get_alipay_cookie.py`
- `examples/test_alipay_upload.py`
- `examples/upload_video_to_tiktok.py`
- `examples/upload_video_to_xiaohongshu.py`

## 📃详细文档

安装、更新和平台参数见仓库内对应文档：[安装说明](./docs/install.md)、[更新说明](./docs/update.md)、[CLI 使用说明](./docs/CLI.md)。产品介绍与社区信息见 [social-auto-upload 文档站](https://sap-doc.nasdaddy.com/)。

## 🐾交流与支持

[☕ Donate as u like](https://www.buymeacoffee.com/hysn2001m) - 如果您觉得这个项目对您有帮助，可以考虑赞助。

如果您也是独立开发者、技术爱好者，对 #技术变现 #AI创业 #跨境电商 #自动化工具 #视频创作 等话题感兴趣，欢迎加入社群交流。

### Creator

<table>
    <td align="center">
        <a href="https://sap-doc.nasdaddy.com/">
            <img src="media/mp.jpg" width="200px" alt="NasDaddy公众号"/>
            <br />
            <sub><b>微信公众号</b></sub>
        </a>
        <br />
        <a href="https://github.com/dreammis/social-auto-upload/commits?author=dreammis" title="Code">💻</a>
        <br />
        关注公众号，后台回复 `上传` 获取加群方式
    </td>
    <td align="center">
        <a href="https://sap-doc.nasdaddy.com/">
            <img src="media/QR.png" width="200px" alt="赞赏码/入群引导"/>
            <br />
            <sub><b>交流群 (通过公众号获取)</b></sub>
        </a>
        <br />
        <a href="https://sap-doc.nasdaddy.com/" title="Documentation">📖</a>
        <br />
        如果您觉得项目有用，可以考虑打赏支持一下
    </td>
</table>




## 🤝贡献指南

欢迎各种形式的贡献，包括但不限于：

-   提交 Bug报告 和 Feature请求。
-   改进代码、文档。
-   分享使用经验和教程。

如果您希望贡献代码，请遵循以下步骤：

1.  Fork 本仓库。
2.  创建一个新的分支 (`git checkout -b feature/YourFeature` 或 `bugfix/YourBugfix`)。
3.  提交您的更改 (`git commit -m 'Add some feature'`)。
4.  Push到您的分支 (`git push origin feature/YourFeature`)。
5.  创建一个 Pull Request。

提交代码或文档前，请确认您有权提交相关内容，并同意这些贡献按照本项目的 MIT License 发布。提交第三方代码时，请同时说明来源及其适用的许可证。

## 主要贡献者

<a href="https://github.com/dreammis/social-auto-upload/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=dreammis/social-auto-upload" />
</a>


## 🙏致谢

本项目的 Bilibili 上传能力基于开源项目 `biliup` 的能力进行接入与封装。
感谢 `biliup` 项目及其贡献者提供的基础能力：

- https://github.com/biliup/biliup

本项目依赖的第三方组件和运行时工具仍受其各自许可证约束。下游发行或集成本项目时，请同时检查并保留相关第三方组件要求的版权、许可证和 NOTICE 声明。

## 📜许可证

本项目采用 [MIT License](LICENSE) 开源许可证。除第三方组件外，本项目代码可以在遵守该许可证条款的前提下用于商业软件，包括闭源软件。

## ⭐Star-History

> 如果这个项目对您有帮助，请给一个 ⭐ Star 以表示支持！




[![Star History Chart](https://star-history.dera.page/svg?repos=dreammis/social-auto-upload&type=Date)](https://star-history.dera.page/#dreammis/social-auto-upload&Date)
