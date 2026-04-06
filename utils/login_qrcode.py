# -*- coding: utf-8 -*-
from datetime import datetime
import base64
from pathlib import Path
import sys

import cv2
import segno


def build_login_qrcode_path(account_file: str, suffix: str = "login_qrcode") -> Path:
    account_path = Path(account_file)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return account_path.with_name(f"{account_path.stem}_{suffix}_{timestamp}.png")


def save_data_url_image(data_url: str, output_path: Path) -> Path:
    if not data_url.startswith("data:image/"):
        raise ValueError("二维码地址不是 data:image 格式")

    header, encoded = data_url.split(",", 1)
    if ";base64" not in header:
        raise ValueError("二维码图片不是 base64 编码")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(encoded))
    return output_path


def remove_qrcode_file(qrcode_path: Path | None) -> bool:
    if qrcode_path and qrcode_path.exists():
        qrcode_path.unlink()
        return True
    return False


def decode_qrcode_from_path(qrcode_path: Path) -> str | None:
    image = cv2.imread(str(qrcode_path))
    if image is None:
        return None

    detector = cv2.QRCodeDetector()
    qrcode_content, _, _ = detector.detectAndDecode(image)
    return qrcode_content or None


def _print_ascii_qrcode(qrcode) -> None:
    border = 1
    rows = list(qrcode.matrix)
    empty_line = "  " * (len(rows[0]) + border * 2)
    print(empty_line)
    for row in rows:
        line = ["  "] * border
        line.extend("##" if cell else "  " for cell in row)
        line.extend(["  "] * border)
        print("".join(line))
    print(empty_line)


def print_terminal_qrcode(
    qrcode_content: str,
    qrcode_path: Path,
    app_name: str,
    compact: bool = True,
    border: int = 0,
) -> None:
    print()
    print(f"请使用{app_name}扫描下方二维码登录：")
    qrcode = segno.make(qrcode_content, error="L", boost_error=False)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        qrcode.terminal(compact=compact, border=border)
    except (UnicodeEncodeError, OSError):
        print("当前终端不支持 Unicode 二维码字符，已切换为 ASCII 打印：")
        _print_ascii_qrcode(qrcode)
    print("在 Windows 下建议使用 Windows Terminal（支持 UTF-8，可完整显示二维码）")
    print(f"否则请打开 {qrcode_path} 扫码")
    print()
