# 启动后端（开发模式，热重载）
# 用法: 在项目根目录 powershell 执行  .\scripts\run_backend_dev.ps1
# 与 run_frontend_dev 分开两个终端跑；dev 模式下 Tauri 不拉起 sidecar，
# 后端由本脚本启动，避免抢 5409 端口。

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# conf.py 被 gitignore，全新检出/清理后会缺失，导致后端 import 'conf' 失败。
# 不存在则自动从 conf.example.py 复制一份，省去手动操作。
if (-not (Test-Path "conf.py")) {
    Copy-Item "conf.example.py" "conf.py"
    Write-Host "已从 conf.example.py 创建 conf.py" -ForegroundColor Green
}

# 用 python -m flask（而非裸 flask）确保跑在装了依赖的同一个解释器里，
# 避免 PATH 上的其它 flask（如 anaconda）找不到 flask_cors。
$env:FLASK_APP = "sau_backend"
try {
    python -m flask --app sau_backend --debug run --host 0.0.0.0 --port 5409
} catch {
    Write-Host "flask 不可用，回退 python sau_backend.py" -ForegroundColor Yellow
    python sau_backend.py
}
