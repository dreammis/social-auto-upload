# social-auto-upload 工作约定

## 上下文

- 本仓库在 Independent-Media 中负责多平台登录、上传和发布，是具有真实外部副作用的边界组件。
- 开始行为变更前读取 `../AGENTS.md`；跨仓库目标与契约以 `../docs/自媒体自动化工作流实施方案.md` 为准。
- 需要变更产物时写入 `../docs/changes/<change-id>/`。

## 主线入口

- Python 3.10–3.12，优先使用 `uv` 和已注册 CLI `sau`。
- 安装与使用优先读取 `docs/install.md`、`docs/CLI.md`、`docs/update.md` 和 `docs/agent-bootstrap.md`。
- 平台操作优先读取 `skills/<platform>-upload/`；除非主线不可用，不默认使用历史 `examples/` 或旧 Web 路径。
- 前端位于 `sau_frontend/`，脚本以其 `package.json` 为准。

## 实施与验证

- 先检查 `tests/` 中相邻用例；行为变化添加回归测试。
- Python 测试：`python -m unittest discover -s tests -p "test_*.py"`。
- CLI 变化至少验证 `sau --help` 和受影响平台的 `sau <platform> --help`。
- 前端变化在 `sau_frontend/` 运行 `npm run build`，并对受影响流程做真实浏览器验证。
- 浏览器/平台验证应使用测试账号或受控草稿；不可用时明确记录，而不是把 Mock 测试宣称为真实平台成功。

## 强制安全边界

- Cookie、二维码、Token、账号文件和个人数据不得出现在日志、变更产物、截图说明或提交中。
- 未经用户对本次具体动作明确授权，不执行真实登录、上传、立即发布、定时发布、删除或覆盖。
- 即使获得执行授权，也必须先确认平台、账号、内容、可见性/发布时间和合规声明；优先生成草稿或预览。
- Bilibili 等需要交互终端的登录流程不得在非交互环境强行代跑。
