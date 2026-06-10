# 启动前端 + Tauri 桌面窗口（开发模式，Vue HMR 热更新）
# 用法: 在项目根目录 powershell 执行  .\scripts\run_frontend_dev.ps1
# dev 模式下不拉起 sidecar，后端请另开终端跑 run_backend_dev.ps1。

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $ProjectRoot "sau_frontend")

npm run tauri dev
