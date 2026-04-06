# 浏览器平台 CLI 统一与小红书 Skill 设计

日期：2026-03-25

## 概要

这份设计处理三个浏览器自动化平台的主线接口统一：

- 抖音
- 快手
- 小红书

目标不是重写 uploader，也不是再抽一层复杂框架，而是把当前已经存在但不一致的 CLI、skill、文档、示例收口成一套统一契约。

这次设计同时解决两个现实问题：

1. 小红书虽然已经有可用的浏览器 uploader，但还没有接入 `sau` CLI，也没有对应 skill。
2. 抖音、快手当前的 CLI 契约还带着历史字段，比如视频没有单独 `--desc`，而图文正文命名和视频描述语义混杂，不利于三家浏览器平台形成稳定统一的主线接口。

这次统一后的对外入口固定为：

- `sau douyin ...`
- `sau kuaishou ...`
- `sau xiaohongshu ...`

并让三家浏览器平台的视频、图文上传都遵循统一的主线参数模型：

- 视频：`title + desc + tags`
- 图文：`title + note + tags`

## 目标

- 给小红书补齐主线 CLI：
  - `login`
  - `check`
  - `upload-video`
  - `upload-note`
- 统一抖音、快手、小红书三家浏览器平台的 CLI 上传参数模型
- 补齐小红书 skill、示例脚本、README、CLI 文档、安装/更新文档
- 修正抖音、快手现有 CLI 契约里缺失的 `desc` 能力
- 保持现有 uploader 主体逻辑不大改，不做过度封装

## 非目标

- 这次不重构 uploader 架构
- 这次不改 Web 旧路径
- 这次不改 Bilibili 的上传契约
- 这次不做浏览器集成测试
- 这次不保留公开的 `--note` 主契约

## 当前项目基础

### 已有能力

- 抖音、快手已经接入 `sau_cli.py`
- Bilibili 已经接入 CLI 和 skill
- 小红书已经具备：
  - 登录
  - cookie 校验
  - 视频上传
  - 图文上传
  - 定时发布
- 小红书 uploader 内部已经支持：
  - 视频：`title + desc + tags`
  - 图文：`title + desc + tags`
  - 图文里的 `desc` 可选

### 当前不一致点

- 抖音视频 CLI：`--title`、`--tags`，没有 `--desc`
- 快手视频 CLI：`--title`、`--tags`，没有 `--desc`
- 抖音图文 CLI：`--note`、`--tags`
- 快手图文 CLI：`--note`、`--tags`
- 小红书还没有 CLI/skill 接口

也就是说，当前三家浏览器平台的主线能力并不统一，尤其是：

- 视频描述没有统一暴露为 `desc`
- 图文正文是否应该沿用 `note` 语义没有统一

## 统一后的 CLI 设计

### 支持的平台

- `douyin`
- `kuaishou`
- `xiaohongshu`

### 支持的动作

每个平台统一支持：

- `login`
- `check`
- `upload-video`
- `upload-note`

### 统一后的上传参数模型

#### 视频上传

```bash
sau <platform> upload-video \
  --account <account_name> \
  --file <video-path> \
  --title "<title>" \
  [--desc "<description>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"] \
  [平台特有参数...]
```

统一规则：

- `--title` 必填
- `--desc` 选填
- `--tags` 选填
- `--schedule` 选填

平台特有参数：

- 抖音：
  - `--thumbnail`
  - `--product-link`
  - `--product-title`
- 快手：
  - `--thumbnail`
- 小红书：
  - `--thumbnail`

#### 图文上传

```bash
sau <platform> upload-note \
  --account <account_name> \
  --images <image-1> [image-2 ...] \
  --title "<title>" \
  [--note "<content>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"]
```

统一规则：

- `--images` 必填
- `--title` 必填
- `--note` 选填
- `--tags` 选填
- `--schedule` 选填

明确决定：

- 图文主线正文统一叫 `note`
- 视频主线描述统一叫 `desc`
- 文档、skill、示例统一使用：
  - 视频：`--title + --desc + --tags`
  - 图文：`--title + --note + --tags`

## 数据模型设计

为了让 CLI 层和 uploader 层映射清晰，每个平台都保持各自的 request dataclass，但字段命名统一。

### 视频请求对象

统一字段：

- `account_name`
- `video_file`
- `title`
- `description`
- `tags`
- `publish_date`
- `publish_strategy`
- `debug`
- `headless`

平台特有字段保留：

- 抖音：
  - `thumbnail_file`
  - `product_link`
  - `product_title`
- 快手：
  - `thumbnail_file`
- 小红书：
  - `thumbnail_file`

### 图文请求对象

统一字段：

- `account_name`
- `image_files`
- `title`
- `note`
- `tags`
- `publish_date`
- `publish_strategy`
- `debug`
- `headless`

这里明确保留 `note`，因为它更符合图文正文语义，不应强行复用视频里的 `description / desc` 命名。

## 与现有 uploader 的映射

### 抖音

- 视频上传继续复用 `DouYinVideo`
- 给抖音视频补齐 `desc` 输入映射
- 图文上传改为显式接收 `title + note + tags`
- `note` 在 CLI 层映射到抖音图文正文输入区

### 快手

- 视频上传继续复用 `KSVideo`
- 给快手视频补齐 `desc` 输入映射
- 图文上传改为显式接收 `title + note + tags`

### 小红书

- 登录、校验直接接 `xiaohongshu_setup` / `cookie_auth`
- 视频上传复用 `XiaoHongShuVideo`
- 图文上传复用 `XiaoHongShuNote`
- 因为小红书 uploader 已经支持 `title + desc + tags`，CLI 层把 `note` 稳定映射到图文正文即可

## 兼容与迁移策略

这次采用“直接统一，不保留旧的模糊公开契约”的策略。

具体表现：

- `README.md`
- `docs/CLI.md`
- `docs/install.md`
- `docs/update.md`
- `skills/douyin-upload/...`
- `skills/kuaishou-upload/...`
- 新增 `skills/xiaohongshu-upload/...`
- `scripts/examples/...`

都会在同一轮里切换到新契约，避免出现：

- 一部分文档把图文正文写成 `--note`
- 一部分文档把图文正文写成 `--desc`

这样做的代价是旧示例命令会失效，但换来的是主线契约彻底统一：

- 视频永远是 `desc`
- 图文永远是 `note`

## Skill 设计

新增：

- `skills/xiaohongshu-upload/SKILL.md`
- `skills/xiaohongshu-upload/references/cli-contract.md`
- `skills/xiaohongshu-upload/references/runtime-requirements.md`
- `skills/xiaohongshu-upload/references/troubleshooting.md`
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.ps1`
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.sh`
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_cli_template.py`

并同步更新：

- `skills/douyin-upload/SKILL.md`
- `skills/douyin-upload/references/cli-contract.md`
- `skills/kuaishou-upload/SKILL.md`
- `skills/kuaishou-upload/references/cli-contract.md`

skill 原则继续保持：

- 优先走 `sau`
- agent 不要先读 uploader 源码
- CLI 失败时再看 troubleshooting
- 登录二维码图片优先直接展示给用户扫码

## 文档设计

至少更新：

- `README.md`
- `docs/CLI.md`
- `docs/install.md`
- `docs/update.md`

统一后的表达口径：

- 三家浏览器平台都已经接入 CLI
- 三家浏览器平台都已经接入 skill
- 视频上传统一字段：
  - `title`
  - `desc`
  - `tags`
- 图文上传统一字段：
  - `title`
  - `note`
  - `tags`
- `account_name` 是用户自定义账号名，不是固定只能叫 `creator`
- 一个 `account_name` 对应一个账号文件，可多账号隔离并发

## Example 设计

examples 保留两类路径：

1. CLI 主线示例
2. 历史直连 uploader 示例

小红书需要补到和其他平台同等级的主线表达里：

- `examples/get_xiaohongshu_cookie.py`
- `examples/upload_video_to_xiaohongshu.py`
- 如有必要，补一份更贴近 CLI 契约的调用示例

README 和 docs 中要明确说明：

- 推荐优先使用 `sau xiaohongshu ...`
- 历史直连 uploader 示例只是调试入口

## 错误处理

### 参数级错误

由 CLI parser 负责：

- 文件不存在
- 时间格式非法
- 缺少 `--title`
- 缺少 `--images`

### 业务级错误

由 uploader 和现有校验负责：

- cookie 不存在
- cookie 已失效
- 上传失败
- 页面结构异常

### 二维码口径

三家浏览器平台统一保留这条说明：

- 如果登录流程生成了本地二维码图片，agent 应优先直接展示/发送图片给用户扫码，而不是只返回路径

## 测试策略

这次只做最小但有价值的 CLI 级验证，不做浏览器集成测试。

至少补这些测试：

- parser 能识别 `xiaohongshu`
- 三个平台新契约能正确解析：
  - `upload-video --title --desc --tags`
  - `upload-note --images --title --note --tags`
- dispatch 能正确把参数转成对应 request
- 小红书 `login/check/upload-video/upload-note` 分支能被正确路由

保留现有：

- `tests/test_xiaohongshu_uploader.py`

## 文件影响范围

### 必改

- `sau_cli.py`
- `README.md`
- `docs/CLI.md`
- `docs/install.md`
- `docs/update.md`

### 新增

- `skills/xiaohongshu-upload/` 全套文件
- 对应 CLI 单测文件

### 同步修改

- `skills/douyin-upload/...`
- `skills/kuaishou-upload/...`
- `examples/get_xiaohongshu_cookie.py`
- `examples/upload_video_to_xiaohongshu.py`

## 推荐实现顺序

1. 先改 `sau_cli.py` 和 request 模型
2. 接上小红书 CLI 路由
3. 给抖音、快手补 `desc` / 图文新字段映射
4. 补 CLI 单测
5. 新增小红书 skill
6. 更新抖音、快手 skill 契约
7. 更新 README / CLI / install / update 文档
8. 更新 examples

## 最终结论

- 三家浏览器平台统一成同一套 CLI 动作：
  - `login`
  - `check`
  - `upload-video`
  - `upload-note`
- 三家浏览器平台统一成同一套主线元数据模型：
  - 视频：`title + desc + tags`
  - 图文：`title + note + tags`
- 小红书补齐 CLI 与 skill
- 抖音、快手补齐 `desc` 能力，并统一图文正文字段为 `note`
- 实现保持轻量，不做过度封装
