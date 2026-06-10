# 启动后端（开发模式，热重载）
# 用法: 在项目根目录 powershell 执行  .\scripts\run_backend_dev.ps1
# 与 run_frontend_dev 分开两个终端跑；dev 模式下 Tauri 不拉起 sidecar，
# 后端由本脚本启动，避免抢 5409 端口。

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 优先用 flask --debug 自动 reload（改 py 存盘即重启）；
# 没装 flask CLI 时回退到 python sau_backend.py。
$env:FLASK_APP = "sau_backend"
try {
    flask --app sau_backend --debug run --host 0.0.0.0 --port 5409
} catch {
    Write-Host "flask CLI 不可用，回退 python sau_backend.py" -ForegroundColor Yellow
    python sau_backend.py
}
