# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：把 Flask 后端（sau_backend.py）打成可独立运行的 exe，
作为 Tauri sidecar。

要点：
- collect_all('patchright')：把 102MB 的 driver（含 node.exe + package/cli.js）
  一起收进去，冻结后 patchright 用 inspect.getfile 定位 _MEIPASS/patchright/driver。
- 本地包（myUtils/uploader/utils/db）用 collect_submodules 全量收，避免动态 import 漏收。
- onefile：先验证链路通；启动慢的话后续转 onedir + Tauri resources。
- 浏览器依赖用户机器的 Chrome（channel="chrome"），不收 chromium。
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# playwright + patchright 全量（含各自 driver/node.exe）。
# 两个都要：myUtils/login.py 的 SSE 扫码用 playwright，
# uploader/taobao_guanghe_uploader 用 patchright。
for _drv in ('playwright', 'patchright'):
    d, b, h = collect_all(_drv)
    datas += d
    binaries += b
    hiddenimports += h

# xhs 第三方库（小红书）。numpy 不收：项目无直接 import，仅 cv2 传递依赖，
# 已随 cv2 一起在 excludes 排除（省 ~150M）。
for _pkg in ('xhs',):
    d, b, h = collect_all(_pkg)
    datas += d
    binaries += b
    hiddenimports += h

# 本地包：动态 import 较多，全量收子模块
for _local in ('myUtils', 'uploader', 'utils', 'db'):
    hiddenimports += collect_submodules(_local)

# 其它易漏的隐藏导入
hiddenimports += [
    'flask',
    'flask_cors',
    'segno',
    'loguru',
    'sqlite3',
]

a = Analysis(
    ['sau_backend.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['cv2', 'numpy'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='sau-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
