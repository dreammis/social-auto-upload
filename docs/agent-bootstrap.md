# Agent Bootstrap Prompt

这份文档是写给 `OpenClaw`、`Codex`、`Claude Code / cc` 这类 agent 客户端用户的。

目标不是让 agent 先通读整个仓库，而是先把 `social-auto-upload` 安装到可运行、可验证、可继续执行任务的状态。

当前主线已接入的平台：

- `bilibili`
- `douyin`
- `kuaishou`
- `xiaohongshu`

## 这份文档解决什么问题

现在仓库里已经有：

- 安装说明
- CLI 文档
- 平台 skill

但这些内容更偏向“agent 进入仓库之后怎么执行”。

这份文档补的是“用户第一次把仓库交给 agent 客户端时，应该怎么说”。

## 推荐使用方式

1. 把整个仓库给你的 agent 客户端。
2. 把下面这段启动提示词完整发给它。
3. 等 agent 完成安装和 CLI 验证后，再继续给它下达登录、上传、定时发布等任务。

## 通用启动提示词

复制下面整段，发给你的 agent：

```text
你现在在一个名为 `social-auto-upload` 的仓库中工作。

这是一个多平台社交媒体自动发布项目。当前主线已经接入：

- bilibili
- douyin
- kuaishou
- xiaohongshu

你的第一目标不是通读全部源码，也不是优先运行历史 examples，而是先把项目安装到“可运行、可验证、可继续执行任务”的状态。

请遵守以下规则：

1. 默认把仓库根目录视为当前工作目录。
2. 优先使用 `uv` 管理 Python 环境，不要默认回退到旧的 `requirements.txt`。
3. 优先使用当前主线 CLI：`sau`。
4. 优先参考这些文档：
   - `docs/install.md`
   - `docs/CLI.md`
   - `docs/update.md`
5. 如果需要平台级操作，优先参考这些 skill：
   - `skills/douyin-upload/`
   - `skills/kuaishou-upload/`
   - `skills/xiaohongshu-upload/`
   - `skills/bilibili-upload/`
6. 不要默认走历史 `examples/` 和旧 Web 路径，除非当前 CLI 主线不可用。
7. 如果登录流程生成二维码图片，不要只返回图片路径；请直接展示图片，或者明确告诉我该打开哪个本地图片文件扫码。
8. 如果是 Bilibili 登录，不要在非交互环境里强行代跑；应改为指导我在本地真实终端执行。
9. 安装完成后，请优先验证以下命令：
   - `sau --help`
   - `sau douyin --help`
   - `sau kuaishou --help`
   - `sau xiaohongshu --help`
   - `sau bilibili --help`
10. 完成后，请明确输出：
   - 你实际执行了哪些命令
   - 哪些验证通过了
   - 当前项目是否已经进入“可继续登录/上传”的状态
   - 推荐我下一步执行什么

如果过程中遇到错误，不要跳过，请先说明错误，再给出你准备采取的下一步动作。
```

## 安装完成后，你可以继续怎么说

下面这些是你可以继续发给 agent 的任务示例。

### 做一次平台登录

```text
请继续帮我登录小红书账号，使用有头模式，账号名用 `creator`。
```

```text
请继续帮我登录抖音账号，使用无头模式，账号名用 `creator`。
```

### 做一次 CLI 可用性检查

```text
请检查 bilibili、douyin、kuaishou、xiaohongshu 四个平台的 CLI 入口是否都可用，并告诉我缺什么依赖。
```

### 做一次真实上传

```text
请使用 xiaohongshu CLI，帮我上传一个图文草稿，使用定时发布，不要立即发布。
```

```text
请使用 douyin CLI，帮我上传一个视频，优先走当前主线，不要走历史 example。
```

## OpenClaw / Codex / Claude Code 使用建议

### OpenClaw

- 适合直接粘贴上面的完整启动提示词
- 如果支持把仓库作为工作目录挂载进去，优先先挂载仓库，再发提示词
- 如果支持本地文件展示，登录二维码应让 agent 直接展示图片

### Codex

- 建议先让它完成 bootstrap，再继续发平台任务
- 让它优先使用 `docs/install.md`、`docs/CLI.md` 和 `skills/`
- 不要让它一开始自由探索整个仓库，否则容易走到历史路径

### Claude Code / cc

- 建议先让仓库成为当前 workspace
- 再发完整启动提示词
- 后续按“安装 -> 验证 -> 登录 -> 上传”顺序继续给任务

## 为什么不按平台拆四套提示词

因为这个项目现在已经有统一的 CLI 主线。

用户第一次把仓库交给 agent 时，更需要的是：

- agent 知道主入口是什么
- agent 知道应该优先走哪条路径
- agent 知道哪些是历史路径
- agent 安装完成后先给出明确验收结果

等进入执行阶段，再让 agent 根据你的实际目标去选择：

- `bilibili`
- `douyin`
- `kuaishou`
- `xiaohongshu`

这样比给用户准备四套平台 prompt 更稳，也更容易维护。
