# 启动后端（开发模式，热重载）
# 用法: 在项目根目录 powershell 执行  .\scripts\run_backend_dev.ps1
# 与 run_frontend_dev 分开两个终端跑；dev 模式下 Tauri 不拉起 sidecar，
# 后端由本脚本启动，避免抢 5409 端口。

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 用 python -m flask（而非裸 flask）确保跑在装了依赖的同一个解释器里，
# 避免 PATH 上的其它 flask（如 anaconda）找不到 flask_cors。
$env:FLASK_APP = "sau_backend"
try {
    python -m flask --app sau_backend --debug run --host 0.0.0.0 --port 5409
} catch {
    Write-Host "flask 不可用，回退 python sau_backend.py" -ForegroundColor Yellow
    python sau_backend.py
}
