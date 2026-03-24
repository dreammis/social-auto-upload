# social-auto-upload

`social-auto-upload` 是一个强大的自动化工具，旨在帮助内容创作者和运营者高效地将视频内容一键发布到多个国内外主流社交媒体平台。
项目实现了对 `抖音`、`Bilibili`、`小红书`、`快手`、`视频号`、`百家号` 以及 `TikTok` 等平台的视频上传、定时发布等功能。
结合各平台 `uploader` 模块，您可以轻松配置和扩展支持的平台，并通过示例脚本快速上手。

<img src="media/show/tkupload.gif" alt="tiktok show" width="800"/>

## 目录

- [💡 功能特性](#💡功能特性)
- [🚀 当前主线](#🚀当前主线)
- [📊 平台能力矩阵](#📊平台能力矩阵)
- [💾 安装指南](#💾安装指南)
- [🏁 快速开始](#🏁快速开始)
- [🗂️ 重构计划](#🗂️重构计划)
- [📣 近况说明](#📣近况说明)
- [🐇 项目背景](#🐇项目背景)
- [📃 详细文档](#📃详细文档)
- [🐾 交流与支持](#🐾交流与支持)
- [🤝 贡献指南](#🤝贡献指南)
- [📜 许可证](#📜许可证)
- [⭐ Star History](#⭐Star-History)

## 💡功能特性

这个项目不是在和 agent 抢活，而是在补 AI 自媒体最后一公里里最容易翻车的那一段。

- `social-auto-upload` 更偏向“经过大量验证的脚本化、程序化执行”
- agent 更擅长“理解任务、编排流程、生成内容、调用工具”
- 两者结合，通常比单纯依赖 agent 直接操作浏览器更稳

为什么 agent 已经能操作浏览器了，还是需要这个项目？

- agent 直接操作浏览器，很多时候要反复解析网页、读 DOM、截图理解、再决定下一步动作
- 这类流程每次执行路径都可能不太一样，稳定性依赖当下页面状态、模型判断和上下文质量
- 对上传、登录、定时发布这类高重复动作来说，这会额外消耗大量 token、算力和执行时间
- 一旦平台页面有轻微波动，agent 还可能重新理解、重新试错，成本会继续上升

这个项目的价值就在这里：

- 把高频、重复、已经跑通过很多次的平台动作，沉淀成稳定的 uploader / CLI / skill
- 把“理解网页并临场决策”的不确定性，尽量收敛成“直接调用一个被验证过的能力”
- 让 agent 少走弯路，少烧 token，把算力留给更适合 AI 的环节，比如选题、写文案、排流程、调度任务
- 让整条链路更接近真正可持续的生产化，而不是每次都从零开始看页面、猜按钮、试流程

## 📊平台能力矩阵

下表描述的是当前仓库内“实际已有实现”的能力，不代表都已经完成 CLI 化或 skill 化。

| 平台 | 登录/账号准备 | 视频上传 | 图文上传 | 定时发布 | CLI | Skill | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 抖音 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 当前主线重构最完整 |
| Bilibili | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | 依赖 `biliup` |
| 小红书（浏览器版） | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | 当前仓库有浏览器 uploader |
| 快手 | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | 浏览器自动化 |
| 视频号 | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | 对应 `tencent_uploader` |
| 百家号 | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | 浏览器自动化 |
| TikTok | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | 当前示例走 Chrome 版实现 |


## 🚀当前主线

当前仓库这轮重构的主线很明确：

- 先把抖音链路打磨完整，作为 uploader / CLI / skill 的样板
- 逐步把其他平台往统一结构上收敛
- 默认围绕 `uv`、`patchright`、无头模式、CLI 化、Skill 化推进
- Web 相关代码目前保留为历史版本，不是当前主要维护方向

如果你是第一次使用这个项目：

- 安装看：[安装说明](./docs/install.md)
- 更新看：[更新说明](./docs/update.md)
- CLI 看：[CLI 使用说明](./docs/CLI.md)
- agent / skill 看：[Douyin Upload Skill](./skills/douyin-upload/SKILL.md)
- 历史 Web 说明看：[历史 Web 版本说明](./docs/legacy-web.md)


## 📣近况说明

`2026.03.24`

最近我的重心一直都在创业上，而且手里还有一些项目没完全跑通，所以这个仓库前面有很长一段时间，我确实没有办法投入特别多精力去持续维护。

这个项目不知不觉已经 `9k+ star` 了，社群里也已经有 `2000+` 小伙伴了。看到它真的在持续帮到大家，我心里还是挺开心的，也是真的很感谢大家一直以来的支持、反馈。

所以我想，决定先停一下，抽一段时间出来，把这个项目好好重构和优化一轮。

接下来这段时间，这个仓库应该会进入一个相对密集更新的阶段。我现在最想先做的事情主要有这几件：

1. 使用更隐蔽、更稳定的自动化方案，尽量降低平台检测风险
2. 补齐一些常用平台的图文能力，并逐步完成 CLI 化、Skill 化
3. 陆续测试并上架到更多 skill 平台，让大家的龙虾、螃蟹、毛毛虫都能打通 AI 自媒体的最后一道关

所以如果你之前觉得这个项目更新有点慢，哈哈哈，后面大概率会快很多。也欢迎大家继续关注，最近应该会是一段持续修、持续更、持续重构的阶段。

## 🗂️重构计划

项目正在进行一轮整体重构，当前重构重点是：

- 各平台 uploader 的结构收敛
- CLI 统一接入
- 面向 OpenClaw、Codex、 Claude Code 等工具的 skill 化
- 更换为 `patchright` 驱动，提升兼容性与隐蔽性
- 主线优先围绕无头模式推进

“无头模式（headless）”，指的是浏览器在后台运行，不弹出可见窗口，但自动化流程仍然会照常执行。这样更适合 CLI、服务端、自动任务和 agent 场景。

Web 端相关代码仍然保留，但已经不是当前主线，不保证可直接运行，也不保证与当前 uploader/CLI 完全同步。

## 💾安装指南

安装、更新、环境准备不再在首页重复展开，统一收敛到文档里：

- 人类用户优先看：[安装说明](./docs/install.md)
- 需要更新仓库时看：[更新说明](./docs/update.md)
- 如果你是 CLI 用户，再配合看：[CLI 使用说明](./docs/CLI.md)

当前主线默认使用：

- `uv` 管理环境
- `pyproject.toml` 管理依赖
- `patchright` 作为浏览器驱动
- `sau` 作为 CLI 入口

`requirements.txt` 目前主要用于历史兼容路径，普通用户不需要优先使用它。

## 🏁快速开始

### 方式 1：使用 CLI

当前只有抖音已经完成 CLI 化：

```bash
sau douyin login --account creator
sau douyin check --account creator
sau douyin upload-video --account creator --file videos/demo.mp4 --title "示例标题"
```

### 方式 2：使用 examples

其他平台当前仍以 `examples/` 下的示例脚本为主，例如：

- `examples/upload_to_douyin.py`
- `examples/upload_video_to_bilibili.py`
- `examples/upload_video_to_kuaishou.py`
- `examples/upload_video_to_tencent.py`
- `examples/upload_video_to_baijiahao.py`
- `examples/upload_video_to_tiktok.py`
- `examples/upload_video_to_xiaohongshu.py`

## 🐇项目背景

该项目最初是我个人用于自动化管理社交媒体视频发布的工具。我的主要发布策略是提前一天设置定时发布，因此项目中很多定时发布相关的逻辑是基于“第二天”的时间进行计算的。

如果您需要立即发布或其他定制化的发布策略，欢迎研究源码或在社区提问。

## 📃详细文档

更详细的文档和说明，请查看：[social-auto-upload 官方文档](https://sap-doc.nasdaddy.com/)

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

### Active Core Team

<table>
    <td align="center">
        <a href="https://leedebug.github.io/">
            <img src="media/edan-qrcode.png" width="200px" alt="Edan Lee"/>
            <br />
            <sub><b>Edan Lee</b></sub>
        </a>
        <br />
        <a href="https://github.com/dreammis/social-auto-upload/commits?author=LeeDebug" title="Code">💻</a>
        <a href="https://leedebug.github.io/" title="Documentation">📖</a>
        <br />
        封装了 api 接口和 web 前端管理界面
        <br />
        （请注明来意：进群、学习、企业咨询等）
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

## 📜许可证

本项目暂时采用 [MIT License](LICENSE) 开源许可证。

## ⭐Star-History

> 如果这个项目对您有帮助，请给一个 ⭐ Star 以表示支持！

[![Star History Chart](https://api.star-history.com/svg?repos=dreammis/social-auto-upload&type=Date)](https://star-history.com/#dreammis/social-auto-upload&Date)
