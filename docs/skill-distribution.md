# Skill 分发与发布

## 目录约定

`skills/` 是 Skills 的源目录，包含一个跨平台总入口和每个平台一个独立入口。CLI 平台的 Skill 使用仓库中的 `sau` 命令；TikTok 没有 CLI，使用本仓库现有的 Chrome 上传器。

| 平台 | Skill 目录 | CLI 入口 |
| --- | --- | --- |
| 跨平台总入口 | `social-auto-upload` | 按用户指定的平台转到下方入口 |
| 抖音 | `douyin-upload` | `sau douyin` |
| Bilibili | `bilibili-upload` | `sau bilibili` |
| 小红书 | `xiaohongshu-upload` | `sau xiaohongshu` |
| 快手 | `kuaishou-upload` | `sau kuaishou` |
| 视频号 | `tencent-upload` | `sau tencent` |
| 百家号 | `baijiahao-upload` | `sau baijiahao` |
| 大鱼号 | `dayu-upload` | `sau dayu` |
| 支付宝生活号 | `alipay-upload` | `sau alipay` |
| 微博 | `weibo-upload` | `sau weibo` |
| 虎扑 | `hupu-upload` | `sau hupu` |
| TikTok | `tiktok-upload` | 无；仓库 Chrome uploader |
| 雪球 | `xueqiu-upload` | `sau xueqiu` |
| YouTube | `youtube-upload` | `sau youtube` |
| 知乎 | `zhihu-upload` | `sau zhihu` |
| Facebook 个人主页 | `facebook-upload` | `sau facebook` |
| Facebook Page | `meta-upload` | `sau facebook-page` |
| Instagram | `instagram-upload` | `sau instagram` |

## 分发渠道

以下状态于 2026-10-23 核对。自动索引站点可能滞后于 GitHub；未确认的条目不会标记为已收录。

| 渠道 | 上架方式 | 状态与限制 |
| --- | --- | --- |
| GitHub 源仓库 | 以公开仓库的 `skills/` 为源；按目录安装 | 已发布到 `main`；当前 Skill 更新提交为 [`7023053`](https://github.com/dreammis/social-auto-upload/commit/7023053) |
| GitHub Skills CLI | `gh skill publish skills --tag <version>` | Preview CLI；Release [`v1.0.0-skills.2`](https://github.com/dreammis/social-auto-upload/releases/tag/v1.0.0-skills.2) 已发布，仓库已有 `agent-skills` topic。安装命令：`gh skill install dreammis/social-auto-upload` |
| skills.sh | 直接从 GitHub 安装：`npx skills add dreammis/social-auto-upload --skill <skill-name>` | GitHub 源自动索引，无单独上传表单。已确认[抖音 Skill 页面](https://www.skills.sh/dreammis/social-auto-upload/douyin-upload)；其余入口的索引状态以站点查询为准。安装统计来自 Skills CLI，维护者不应通过自装制造安装量 |
| SkillsMP | 从公开 GitHub 仓库索引 `SKILL.md` | 无独立上传。本仓库创作者页于 2026-10-12 显示已收录 4 个 Skill，源活动显示为 2026-03-25；索引明显落后于当前仓库，尚未确认其余入口收录。见[创作者页](https://skillsmp.com/zh/creators/dreammis/social-auto-upload) |
| SkillHub.club | 将公开 GitHub 仓库中的 `SKILL.md` 推送到 GitHub，由站点自动索引 | 官方说明支持 GitHub 自动索引；本仓库收录状态待核实，无需重复上传文件。见[站点说明](https://www.skillhub.club/docs) |
| SkillHub.space | 网页上传，或用 `shsc publish` 发布 | 尚未提交；需要该站点账号，发布后核对审核状态。见[官方快速开始](https://docs.skillhub.space/docs/quick-start) |
| SkillHub.cn | 网页、CLI 或 Agent 发布 | frontmatter 需有 `slug`、`displayName`、`version`、`summary`、`license`；本仓库已补齐。尚未提交；个人发布需仓库所有者本人完成账号注册、腾讯云人脸实名认证并创建 API Token；Windows CLI 需通过 WSL。见[官方发布指南](https://skillhub.cn/install/skillhub.md) |
| 讯飞星辰 SkillHub（`skill.xfyun.cn`） | 官方 CLI：`@astron-team/skillhub publish <path> --namespace <namespace>` | 公开 Registry，需配置该站点账号的 API Token 和 namespace；尚未配置。与 `skillhub.cn`、`skillhub.space` 是不同平台，CLI 和账号不能混用。见[官方 CLI 文档](https://github.com/iflytek/skillhub/blob/main/docs/skillhub/en/guide/cli.md) |
| SkillHub（`useskillhub.com`） | 申请 Publisher 权限；按 `skillhub.json` 预检、保存草稿，再提交具体版本审核 | 这是带 API、调用权限和运行时契约的注册平台；当前 Markdown Skills 不能直接作为完整服务发布 |
| ClawHub | 对每个 Skill 目录运行 `clawhub skill publish <path>` | 18 个唯一 slug 的本地 dry-run 已通过；CLI 当前未登录。设备码已签发，但本机轮询 `clawhub.ai:443` 超时，网页授权后仍须确认 CLI 登录成功，再发布并核对条目。所有上架内容按 MIT-0 分发；根目录 MIT License 仍适用于仓库其他内容。见[官方 CLI 文档](https://docs.openclaw.ai/clawhub/cli) |
| SkillHub Registry（skillhub.fyi） | 向自己拥有的 Registry 发布 | 属于 Registry/包服务，不是面向所有用户的公共发现目录；本次不作为公共市场渠道 |

平台名称相似但账号体系和发布流程不同。本文分别记录 `skillhub.space`、`skillhub.cn`、`skill.xfyun.cn`、`useskillhub.com` 与 `skillhub.fyi`，不要把一个站点的登录或 CLI 用到另一个站点。

当前发布目标共 18 个：跨平台总入口和 17 个平台 Skill。每个 Skill 的许可证写在对应 frontmatter；ClawHub 发布会按 MIT-0 授权。

ClawHub 当前有 4 个同名条目由其他发布者持有：`bilibili-upload`、`douyin-upload`、`tiktok-upload`、`youtube-upload`。本仓库的跨平台总入口使用 `social-auto-upload`；其余 Skill 使用 `social-auto-upload-<skill-directory>`，不覆盖他人条目。

## 安装示例

从 `skills.sh` CLI 安装总入口或一个平台 Skill：

```bash
npx skills add dreammis/social-auto-upload --skill social-auto-upload
npx skills add dreammis/social-auto-upload --skill douyin-upload
```

将 `douyin-upload` 换成上表中的目录名。此命令用于安装 GitHub 源；不会安装 Python 项目本身，也不会创建 `sau` 命令。CLI 运行环境仍按 [安装说明](./install.md) 配置。`sau skill install` 并不存在，不要在文档或 Skill 中引用。

## 新增平台发布清单

新增平台时，在同一个 PR 完成以下更新：

- 新增或更新 `skills/<platform>-upload/SKILL.md`；若无 CLI，写清楚实际入口和依赖，不编造命令
- 在 Skill frontmatter 中写明 `license`、唯一 `slug`、`displayName`、`version` 和 `summary`；上架 ClawHub 前确认有权按 MIT-0 发布
- 更新 README 功能表和所有平台 Skill 链接；平台或 Skill 数量变化时同步更新 README 徽章
- 更新本页平台映射与渠道状态
- 更新 `docs/CLI.md`，写清可用命令及不支持的能力
- 检查独立安装所需的说明和文件都在对应 Skill 目录内；不要依赖该目录之外的相对路径
- 检查发布包没有账号文件、Cookie、截图、密钥或本机路径
- 对每个适用的公开 Skills 市场完成提交，或记录明确的账号、格式、许可等阻塞原因；核对许可、审核和版本要求，未提交或待审核不得标成已上架

GitHub PR 模板也包含相同的提醒清单。更改 CLI 参数、登录流程或平台限制时，同步修改对应 Skill，避免 Skill 与实现逐渐失配。
