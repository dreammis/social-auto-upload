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

| 渠道 | 上架方式 | 状态与限制 |
| --- | --- | --- |
| GitHub 源仓库 | 以公开仓库的 `skills/` 为源；按目录安装 | 已发布到 `main`，提交 `404560e` |
| GitHub Skills CLI | `gh skill publish skills --tag <version>` | Preview CLI；Release `v1.0.0-skills.1` 已发布，仓库已加 `agent-skills` topic。安装命令：`gh skill install dreammis/social-auto-upload` |
| skills.sh | 直接从 GitHub 安装：`npx skills add dreammis/social-auto-upload --skill <skill-name>` | 源已公开；无单独上传表单，等待索引器更新。安装统计来自 Skills CLI，维护者不应通过自装制造安装量 |
| SkillsMP | 从公开 GitHub 仓库索引 `SKILL.md` | 源已公开；无独立上传，等待索引器收录 |
| SkillHub.space | 网页上传，或用 `shsc publish` 发布 | 尚未提交；需要该站点账号，发布后核对审核状态 |
| SkillHub.cn | 网页、CLI 或 Agent 发布 | 尚未提交；个人发布需仓库所有者本人完成实名认证，再经过内容与安全审核 |
| SkillHub（useskillhub.com） | 申请 Publisher 权限；按 `skillhub.json` 预检、保存草稿，再提交具体版本审核 | 这是带 API、调用权限和运行时契约的注册平台；当前 Markdown Skills 不能直接作为完整服务发布 |
| ClawHub | 对每个 Skill 目录运行 `clawhub skill publish <path>` | 18 个唯一 slug 的本地 dry-run 已通过，正式提交等待账号设备登录。所有上架内容固定按 MIT-0 分发；根目录 MIT License 仍适用于仓库其他内容 |
| SkillHub Registry（skillhub.fyi） | 向自己拥有的 Registry 发布 | 属于 Registry/包服务，不是面向所有用户的公共发现目录；本次不作为公共市场渠道 |

平台名称相似但账号体系和发布流程不同。本文分别记录 `skillhub.space`、`skillhub.cn`、`useskillhub.com` 与 `skillhub.fyi`，不要把一个站点的登录或 CLI 用到另一个站点。

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
- 在 Skill frontmatter 中写明许可证；上架 ClawHub 前确认有权按 MIT-0 发布
- 更新 README 功能表和 17 平台 Skill 链接
- 更新本页平台映射与渠道状态
- 更新 `docs/CLI.md`，写清可用命令及不支持的能力
- 检查独立安装所需的说明和文件都在对应 Skill 目录内；不要依赖该目录之外的相对路径
- 检查发布包没有账号文件、Cookie、截图、密钥或本机路径
- 公开发布前核对该平台的许可、审核、账号和版本要求；记录真实提交结果，未提交或待审核不得标成已上架

GitHub PR 模板也包含相同的提醒清单。更改 CLI 参数、登录流程或平台限制时，同步修改对应 Skill，避免 Skill 与实现逐渐失配。
