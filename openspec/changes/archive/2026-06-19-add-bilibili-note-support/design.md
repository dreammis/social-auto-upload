## Context

当前 Bilibili 平台仅支持视频上传（通过 biliup CLI），不支持图文笔记上传。biliup 是 Rust 编写的 CLI 工具，仅提供 video upload 相关命令，无图片发布能力。Bilibili 的图文笔记（"发布图文" 功能）是通过 Web 端实现的，需要浏览器自动化方式完成。

## Goals / Non-Goals

**Goals:**
- 复用现有 patchright 浏览器自动化框架（与其他平台 note uploader 保持一致）
- 新增 `bilibili upload-note` CLI 子命令
- 在 Web Shell 中支持 Bilibili 图文上传
- 支持定时发布（发布/定时发布策略）

**Non-Goals:**
- 不修改现有 bilibili video upload 行为
- 不实现 biliup 的图片上传功能（biliup 不支持）
- 不支持专栏（column）格式的长文章，仅支持图文笔记

## Decisions

**1. 采用浏览器自动化，而非扩展 biliup**

biliup CLI 仅支持视频上传，没有图文接口。扩展 biliup 需要修改 Rust 代码，成本高。
现有 douyin/kuaishou/xiaohongshu 的 note uploader 都使用 patchright 浏览器自动化，技术栈一致，可复用架构。

**2. 上传器采用独立 BilibiliNote 类**

参考 DouYinNote 模式：继承一个轻量基类，实现 validate_upload_args() 和 upload_note_content(page) 方法。
基类处理：cookie 加载、浏览器启动、headless 配置、publish_date 策略。

**3. 发布目标页面**

Bilibili 图文发布入口：`https://member.bilibili.com/platform/upload/text/edit`（创作中心-发布图文）。
页面结构：标题输入框 + 正文编辑区 + 图片上传区 + 标签输入 + 发布按钮。

## Risks / Trade-offs

- **R1: Bilibili 网页结构变更** → 定位元素选择器可能失效，需要维护
  - Mitigation: 使用语义化选择器（role/text），减少对 DOM 结构的依赖
- **R2: 图片数量限制未知** → Bilibili 对单条图文笔记的图片数量限制待确认
  - Mitigation: 初期限制 20 张，后续根据测试调整
- **R3: 定时发布方式** → Bilibili 的定时发布可能需要在发布弹窗中设置
  - Mitigation: 实现时先做立即发布，定时发布后续迭代
