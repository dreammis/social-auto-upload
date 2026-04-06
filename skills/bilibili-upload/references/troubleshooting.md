# Bilibili 常见问题

## 1. 首次运行很慢

这是正常情况。

原因通常是程序正在自动下载 `biliup`。

## 2. 自动下载失败

先检查：

- 当前网络是否能访问 GitHub
- GitHub Release 是否可访问
- 本地目录是否有写权限
- 国内网络较慢时，可先用 `https://gh-proxy.com/` 或 `https://gh-proxy.org/` 辅助访问对应 release 地址排障
- 示例：
  - `https://gh-proxy.org/https://github.com/biliup/biliup/releases/download/v1.1.29/biliupR-v1.1.29-aarch64-linux.tar.xz`

## 3. `check` 返回 `invalid`

常见原因：

- 账号文件不存在
- 登录信息已失效
- `biliup renew` 失败

建议：

```bash
sau bilibili login --account <account>
```

## 4. 登录时报 `not a terminal`

常见原因：

- 你是在非交互环境里触发了 `sau bilibili login`
- 例如 agent 的命令执行器、管道环境、被接管标准输出的进程

建议：

- 改成由用户自己在本地真实终端里执行：

```bash
sau bilibili login --account <account>
```

- 如果终端里的二维码显示不完整，直接打开当前目录下的 `qrcode.png` 扫码

## 5. 上传失败

优先检查：

- `--tid` 是否正确
- 视频文件是否真实存在
- 标题、简介、标签是否符合平台要求
- 当前登录信息是否仍然有效

## 6. 上游更新后行为变化

当前 Bilibili 集成会自动跟随上游 `biliup` 最新 release。

如果上游命令行为变化，可能会影响本项目的 Bilibili CLI。

排障时请同时确认：

- 当前下载到的 `biliup` 版本
- 上游 release 是否有最近变更
