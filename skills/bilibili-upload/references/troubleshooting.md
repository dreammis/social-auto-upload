# Bilibili 常见问题

## 1. 首次运行很慢

这是正常情况。

原因通常是程序正在自动下载 `biliup`。

## 2. 自动下载失败

先检查：

- 当前网络是否能访问 GitHub
- GitHub Release 是否可访问
- 本地目录是否有写权限

## 3. `check` 返回 `invalid`

常见原因：

- 账号文件不存在
- 登录信息已失效
- `biliup renew` 失败

建议：

```bash
sau bilibili login --account <account>
```

## 4. 上传失败

优先检查：

- `--tid` 是否正确
- 视频文件是否真实存在
- 标题、简介、标签是否符合平台要求
- 当前登录信息是否仍然有效

## 5. 上游更新后行为变化

当前 Bilibili 集成会自动跟随上游 `biliup` 最新 release。

如果上游命令行为变化，可能会影响本项目的 Bilibili CLI。

排障时请同时确认：

- 当前下载到的 `biliup` 版本
- 上游 release 是否有最近变更
