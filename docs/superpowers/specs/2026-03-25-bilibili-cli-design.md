# Bilibili CLI 设计

日期：2026-03-25

## 概要

这份设计要把 `bilibili` 挂到 `sau` 下面，用户侧体验尽量和现在的 `douyin`、`kuaishou` 保持一致。

核心约束只有两个：

- 用户不需要自己安装 `biliup`
- 外部统一走 `sau bilibili ...`

程序会把 `biliup` 当作内部运行时依赖来处理：

- `sau bilibili ...` 是唯一公开入口
- 本地没有 `biliup` 时自动下载
- 每次运行都检查 GitHub Release 最新版本
- 如果发现有更新，先自动更新，再继续执行当前命令

这份设计刻意保持轻量，不重新发明一套 B 站上传语义，而是直接复用仓库里现有的 B 站上传模型。

## 目标

- 让 `sau bilibili ...` 和 `sau douyin ...`、`sau kuaishou ...` 保持统一心智
- 隐藏 `biliup` 的安装细节，降低用户使用成本
- 复用项目里已经存在的账号文件、`VideoZoneTypes`、定时发布等能力
- 不做过度封装

## 非目标

- 第一版不把 `biliup` 二进制直接提交进仓库
- 第一版不维护本地 release manifest
- 第一版不做 B 站图文发布
- 第一版不重做现有的 B 站上传领域模型

## 当前项目基础

仓库里已经有 B 站上传能力：

- `uploader/bilibili_uploader/main.py` 目前直接封装了 `biliup.plugins.bili_webup`
- `examples/upload_video_to_bilibili.py` 已经在使用现有上传参数
- `utils/constant.py` 已经定义了完整的 `VideoZoneTypes`

也就是说，你现在项目里的 B 站上传语义已经很明确，核心就是：

- `file`
- `title`
- `desc`
- `tid`
- `tags`
- `dtime`

所以第一版 CLI 不需要重新造模型，直接沿用这套。

## 用户侧 CLI 设计

### 支持的命令

- `sau bilibili login`
- `sau bilibili check`
- `sau bilibili upload-video`

### 命令契约

#### `sau bilibili login`

作用：

- 自动准备 `biliup`
- 如果有更新则先升级
- 然后调用 `biliup` 完成登录
- 将账号数据按项目自己的账号文件规则保存下来

第一版行为：

- 本地没有 `biliup` 时自动下载最新 release
- 本地已有但上游有更新时自动升级
- 升级完成后继续执行登录流程

#### `sau bilibili check`

作用：

- 自动准备 `biliup`
- 检查当前账号是否可用

第一版行为：

- 结合本地账号文件存在性和 `biliup` 实际可用性来判断
- 输出风格和其他平台保持一致：
  - `valid`
  - `invalid`

#### `sau bilibili upload-video`

作用：

- 自动准备 `biliup`
- 走项目当前已有的 B 站上传参数体系完成视频上传

第一版参数：

- `--account` 必填
- `--file` 必填
- `--title` 必填
- `--desc` 必填
- `--tid` 必填
- `--tags` 选填
- `--schedule` 选填

明确决定：

- `tid` 在第一版里必须传
- 不给默认分区，避免猜测和隐式错误

## 运行时依赖策略

### 选定方案

`biliup` 不提交进仓库，也不要求用户手工安装。

`sau bilibili ...` 在运行时自动处理它：

1. 查找本地是否已有 `biliup`
2. 检查 GitHub Release 最新版本
3. 如果缺失或过期，则自动下载最新版本
4. 替换本地运行时副本
5. 继续执行本次命令

### 选择这个方案的原因

- 仓库体积更干净
- 用户不需要自己找 release、自己下载
- 对外仍然只有一个统一入口 `sau`
- 不需要使用 `git submodule`

### 接受的代价

这套方案明确接受一个现实：

- 每次运行都会检查上游 release
- 上游如果改 CLI 行为，可能会影响这层适配

所以这里的应对方式不是做重封装，而是保持 wrapper 很薄，减少被动维护成本。

## 存储与解析

`biliup` 应该存放在本地运行时缓存目录中，而不是源码目录中。

缓存目录只需要满足：

- 当前用户可写
- 可跨命令复用
- 不进入 git 管理

解析器的职责应当是：

- 识别当前操作系统
- 选择对应平台的 release asset
- 下载并替换可执行文件
- 返回最终可执行路径

## 轻量封装边界

为了避免过度封装，第一版只建议拆成 3 个很薄的部分。

### 1. Resolver

职责：

- 判断本地是否已有 `biliup`
- 检查 GitHub Release 最新版本
- 下载或更新可执行文件
- 返回最终可执行文件路径

### 2. Runner

职责：

- 调用解析出来的 `biliup`
- 收集退出码、标准输出、标准错误
- 对明显的进程级错误做一层项目内友好的报错转换

### 3. `sau_cli.py` 中的 bilibili 子命令

职责：

- 解析 `sau bilibili ...` 参数
- 把这些参数翻译成底层运行逻辑
- 让帮助信息风格和其他平台一致

第一版不需要更多层，也不需要再抽一套很重的统一框架。

## 与现有项目概念的映射

### 账号文件

B 站也继续沿用现在项目的账号别名机制：

- 用户传 `--account <name>`
- 程序解析成对应的账号文件路径

### 分区

`tid` 保持为一等参数。

`VideoZoneTypes` 继续保留并服务于：

- example
- 文档
- 后续可能的辅助工具

### 定时发布

`--schedule` 保持和当前 `sau` 其他平台一致的使用方式：

- 不传就是立即发布
- 传了就是定时发布

具体如何映射到底层 B 站执行逻辑，由 adapter 负责，不暴露给用户。

## 错误处理

第一版错误处理保持直接，不做花哨包装：

- 下载失败：明确告诉用户自动下载 `biliup` 失败
- 更新失败：明确告诉用户最新 release 准备失败
- 登录失败：保留 `biliup` 登录失败上下文
- 检查失败：输出 `invalid`
- 上传失败：返回非零退出码，并展示上游错误摘要

第一版不追求把所有 `biliup` 错误文本都重新翻译一遍。

## 文档影响范围

实现完成后，至少需要补齐这些地方：

- `README.md`
- `docs/CLI.md`
- 安装与更新文档
- 一套对应的 Bilibili skill
- Bilibili example 脚本

对外表达应当统一成：

- 用户使用的是 `sau bilibili ...`
- `biliup` 由程序自动准备

## 测试策略

第一版最少需要验证这些路径：

- `sau bilibili login --account <name>`
- `sau bilibili check --account <name>`
- `sau bilibili upload-video ...`
- 本地没有 `biliup` 时能自动下载
- 本地已有旧版本时能先升级再执行
- 本地已有最新版本时能直接复用

因为登录和上传涉及真实外部平台，第一版以手工验证为主是可以接受的。

## 推荐实现顺序

1. 在 `sau_cli.py` 中加入 `bilibili` 子命令
2. 增加一个最小可用的 `biliup` resolver
3. 增加一个最小可用的 `biliup` runner
4. 接上 `login / check / upload-video`
5. 补文档、example、skill

## 最终结论

- 对外入口固定为 `sau bilibili ...`
- 第一版支持 `login`、`check`、`upload-video`
- `tid` 必填
- `biliup` 不需要用户手动安装
- 每次运行都检查 GitHub Release
- 有新版本时先自动更新，再继续执行
- 整体实现保持轻量，不做过度封装
