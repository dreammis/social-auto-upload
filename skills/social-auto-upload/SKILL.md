---
name: social-auto-upload
description: 为 social-auto-upload 提供总入口，按平台和内容类型选择对应发布流程。Use when 用户要在本仓库支持的平台发布视频、文章或图文，或需要把内容分发到多个指定平台。
license: MIT-0
slug: social-auto-upload
displayName: social-auto-upload 多平台发布入口
version: 1.0.0
summary: 按用户指定的平台和内容类型选择发布流程。
---

# social-auto-upload 总入口

先确认用户指定的平台、内容类型、账号别名和发布方式。用户没有指定平台时先询问，不自行选择目标平台。

## 选择平台入口

| 平台 | 专用 Skill | CLI 平台名 |
| --- | --- | --- |
| 抖音 | `douyin-upload` | `douyin` |
| Bilibili | `bilibili-upload` | `bilibili` |
| 小红书 | `xiaohongshu-upload` | `xiaohongshu` |
| 快手 | `kuaishou-upload` | `kuaishou` |
| 视频号 | `tencent-upload` | `tencent` |
| 百家号 | `baijiahao-upload` | `baijiahao` |
| 大鱼号 | `dayu-upload` | `dayu` |
| 支付宝生活号 | `alipay-upload` | `alipay` |
| 微博 | `weibo-upload` | `weibo` |
| 虎扑 | `hupu-upload` | `hupu` |
| TikTok | `tiktok-upload` | 无 `sau` 命令 |
| 雪球 | `xueqiu-upload` | `xueqiu` |
| YouTube | `youtube-upload` | `youtube` |
| 知乎 | `zhihu-upload` | `zhihu` |
| Facebook 个人主页 | `facebook-upload` | `facebook` |
| Facebook Page | `meta-upload` | `facebook-page` |
| Instagram | `instagram-upload` | `instagram` |

## 工作流程

1. 如已安装对应平台 Skill，先读取并遵循它；从仓库运行时读取 `skills/<skill-name>/SKILL.md`。
2. 若仓库可用，从 `skills/<skill-name>/SKILL.md` 读取平台说明；否则先提供对应安装命令。执行 CLI 前使用 `sau <平台> --help` 确认当前参数。不要猜测参数或声称 TikTok 有 CLI。
3. 先检查目标账号状态；登录需要用户在平台页面完成时，交给用户操作，不索取或保存密码。
4. 发布前核对文件、标题、文案、标签、可见范围、发布时间及目标账号。只发布用户明确指定的平台；同一份内容也要逐个平台核对要求。
5. 只有命令或平台提供本次提交的成功证据才报告已发布。超时或结果未知时先查原作品，不盲目重发。

## 安装入口

从公开 GitHub 仓库安装总入口：

```bash
npx skills add dreammis/social-auto-upload --skill social-auto-upload
```

指定平台时将 `social-auto-upload` 换成表格中的专用 Skill 名称。完整平台能力和分发状态见 GitHub 源仓库的 README 与分发文档。
