# Skill 分发与发布说明

这份文档是给 `social-auto-upload` 后续做独立 skill 分发时用的。

当前仓库已经具备两层能力：

- 一个可安装的 CLI：`sau`
- 一个可被安装到 Codex 的内置 skill：`douyin-cli`

后续当主流程和 bug 修复完成后，可以再继续做 PyPI 发布、安装优化、以及更多平台的独立 skill。

## 先说结论

`skill` 不一定必须是一个 Python 包。

它可以是：

- 一个 skill 目录
- 一个独立仓库
- 一个安装器脚本
- 一个 Docker 镜像
- 一个包管理器可安装的分发物

但从“别人最快安装和使用”的角度看，最常见、最省事的仍然是：

1. 用一个安装包分发真正的运行能力
2. 用一个 skill 安装动作把 skill 放到 AI 工具的技能目录

对这个项目来说，最推荐的形式是：

- Python 包负责提供 `sau` 命令
- `sau skill install` 负责把 skill 安装到 `~/.codex/skills/`

也就是：

```bash
pip install social-auto-upload
sau skill install
```

## skill 一定要是包吗

不是。

### 1. skill 只是一个目录

这是最原始也最常见的形式。

通常内容是：

- `SKILL.md`
- `agents/openai.yaml`
- `references/`
- `scripts/`

这种形式本身已经是一个可用 skill 了，不一定需要打包。

问题在于：

- 用户要知道把它复制到哪里
- 用户要手动安装
- skill 如果依赖额外脚本或运行时，安装体验会比较差

适合：

- 内部团队
- 仓库内开发规范
- 还在快速迭代的 skill

### 2. skill 是一个独立仓库

这也完全成立。

例如：

- 一个仓库专门放 `SKILL.md`
- 附带 `scripts/install.py`
- 或者 README 教用户复制到 `~/.codex/skills/`

这种模式的优点是：

- skill 自己独立版本管理
- 不依赖主业务仓库
- 可以公开发布

缺点是：

- 用户还是可能要 clone
- 或者还需要执行安装脚本

适合：

- 想把 skill 当产品独立维护
- skill 和业务代码已经明显拆开

### 3. skill 跟随一个包分发

这是当前这个项目最适合的方向。

思路是：

- Python 包里内置一份 skill 资源
- 安装包后即可执行 `sau skill install`
- CLI 和 skill 一起发版

优点是：

- 用户体验最好
- skill 和实际命令保持一致
- 版本对应关系清晰
- 不需要用户 clone 仓库

适合：

- skill 背后有真实 CLI/SDK/工具
- 用户最终是要“使用能力”而不只是“阅读说明”

### 4. skill 用 Docker 交付

也可以。

常见方式是：

- Docker 里装好运行环境
- skill 告诉 AI 通过 `docker run ...` 去执行命令

优点是：

- 环境一致性很好
- 本地依赖复杂时特别有用

缺点是：

- 用户必须先装 Docker
- 浏览器自动化、桌面登录、cookie、本地文件挂载都会更复杂
- 对抖音这种需要本地浏览器交互的流程不一定更友好

对当前项目来说，Docker 更适合：

- 后端服务
- 批处理任务
- 服务器环境

不太适合作为“普通用户首次使用抖音登录 skill”的唯一交付方式。

## AI 安装环境、启动脚本、仓库，这些算不算 skill

算，但要区分“skill 本体”和“skill 的安装/运行载体”。

可以这样理解：

- `SKILL.md` 是 skill 本体
- 仓库、包、Docker、安装脚本，是 skill 的分发和运行载体

所以：

- skill 可以住在仓库里
- skill 可以被包一起带出去
- skill 也可以借助 Docker 运行它依赖的环境

只要最终用户能：

1. 安装它
2. 让 AI 发现它
3. 真正调用它依赖的能力

那它就是成立的。

## 对这个项目最合适的方案

### 当前推荐方案

第一阶段：

- 继续在这个仓库里修主流程和 bug
- 保持 `sau` 命令稳定
- 保持包内 skill 与 CLI 契约一致

第二阶段：

- 打包并发布到 PyPI
- 用户通过 `pip install social-auto-upload` 安装
- 用户执行 `sau skill install`

第三阶段：

- 根据需要把更多平台拆成独立 skill
- 例如 `douyin-cli`、`tencent-cli`、`tiktok-cli`

### 为什么现在不优先做“独立 skill 仓库”

因为当前最核心的问题还不是“skill 放哪”，而是：

- 上传流程是否稳定
- CLI 契约是否稳定
- 实际用户安装后能不能跑通

在这些都还在收敛的阶段，先让 skill 随包分发是最稳妥的。

## 未来可选的三种正式发布路线

### 路线 A：PyPI 包 + 包内 skill

用户安装：

```bash
pip install social-auto-upload
sau skill install
```

优点：

- 最容易传播
- 安装简单
- 版本管理清晰

这是当前首选路线。

### 路线 B：独立 skill 仓库 + PyPI 包

用户安装能力：

```bash
pip install social-auto-upload
```

用户安装 skill：

- clone skill 仓库
- 或跑 skill 仓库提供的安装脚本

优点：

- skill 可以单独演进
- 可以给不同 AI 工具维护不同 metadata

缺点：

- 安装链路更长

### 路线 C：Docker + skill

用户：

- 安装 Docker
- 拉镜像
- 安装 skill
- skill 内部调用 docker 命令

优点：

- 依赖环境最稳定

缺点：

- 对本地浏览器自动化和交互式登录不够友好

更适合服务端任务，不是当前首选。

## 当前项目的发布建议

当主流程稳定后，建议按这个顺序走：

1. 先保证 `sau douyin login/check/upload` 真机可用
2. 验证 `sau skill install` 安装后的 skill 可以被 Codex 正常识别
3. 本地打 wheel 做一次冷启动安装测试
4. 再发布 PyPI

建议的最终用户路径是：

```bash
pip install social-auto-upload
playwright install chromium
sau skill install
sau douyin login --account my-account
```

## 一句话回答

`skill` 不是必须做成包，但如果你想让别人“最快安装、最少理解成本、最少手工操作”，那就最好让“运行能力”走包分发，让 `skill` 跟着包一起被安装。

对这个项目来说，最佳落地方案不是“只发一个 skill 仓库”，而是：

- `social-auto-upload` 作为可安装包
- `douyin-cli` 作为包内 skill
- `sau skill install` 作为安装桥梁
