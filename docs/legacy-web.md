# 历史 Web 版本说明

这套 Web 相关代码主要包括：

- `sau_backend.py`
- `sau_backend/`
- `sau_frontend/`

它们属于项目过去阶段的实现，当前已经不是主线维护方向。

## 当前定位

- 作为历史版本保留
- 作为过去 API / Web 封装思路的参考
- 不承诺当前一定可直接运行
- 不承诺和当前 `uploader/`、`sau_cli.py` 的最新实现完全同步

## 为什么单独拆出来说明

当前工程正在整体重构，主线已经切到：

- `uploader/`：核心平台实现
- `sau_cli.py`：CLI 主入口
- `skills/`：面向 agent 的 skill

所以 README 不再把 Web 版本当成主入口来介绍，避免让新用户误以为这是当前最稳定的使用方式。

## 如果你仍然想研究这套历史 Web 版本

可以参考这些文件：

- `sau_backend/README.md`
- `sau_frontend/README.md`
- `sau_backend.py`

但请预期：

- 接口契约可能与当前主线不一致
- 平台能力覆盖可能落后于当前 `uploader/`
- 依赖和运行方式可能需要自行排障

## 当前推荐入口

如果你要使用当前主线能力，优先看：

- `uploader/`
- `sau_cli.py`
- `docs/CLI.md`
- `skills/douyin-upload/SKILL.md`
