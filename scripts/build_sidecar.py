#!/usr/bin/env python3
"""构建后端 sidecar：PyInstaller 打包 sau_backend.py → 重命名为 Tauri
sidecar 要求的 `<name>-<target-triple>.exe` → 放到 src-tauri/binaries/。

用法：
    python scripts/build_sidecar.py

依赖：已 pip install pyinstaller。浏览器依赖用户机器的 Chrome，不打包 chromium。
"""

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC = PROJECT_ROOT / "sau_backend.spec"
DIST = PROJECT_ROOT / "dist_backend"
WORK = PROJECT_ROOT / "build_backend"
BINARIES_DIR = PROJECT_ROOT / "sau_frontend" / "src-tauri" / "binaries"

# PyInstaller 产物名（见 sau_backend.spec 的 EXE name）
EXE_NAME = "sau-backend"
SIDECAR_BASENAME = "sau-backend"  # 对应 tauri.conf.json externalBin: binaries/sau-backend


def rust_target_triple() -> str:
    """读取 `rustc -Vv` 的 host triple，例如 x86_64-pc-windows-msvc。"""
    out = subprocess.check_output(["rustc", "-Vv"], text=True)
    for line in out.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("无法从 rustc -Vv 解析 host triple")


def main() -> int:
    print("[1/3] PyInstaller 打包后端...")
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller", str(SPEC),
            "--noconfirm",
            "--distpath", str(DIST),
            "--workpath", str(WORK),
        ],
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    src_exe = DIST / f"{EXE_NAME}.exe"
    if not src_exe.exists():
        # 非 Windows 没有 .exe 后缀
        src_exe = DIST / EXE_NAME
    if not src_exe.exists():
        print(f"❌ 找不到打包产物: {src_exe}", file=sys.stderr)
        return 1

    triple = rust_target_triple()
    suffix = ".exe" if src_exe.suffix == ".exe" else ""
    target_name = f"{SIDECAR_BASENAME}-{triple}{suffix}"

    print(f"[2/3] 重命名 → {target_name}")
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    target_path = BINARIES_DIR / target_name
    shutil.copy2(src_exe, target_path)

    print(f"[3/3] sidecar 就位: {target_path}")
    print("    现在可以在 sau_frontend 下 `npm run tauri dev` / `build`。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
