# -*- coding: utf-8 -*-
from datetime import datetime
import base64
from pathlib import Path

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


def print_terminal_qrcode(qrcode_content: str, qrcode_path: Path, app_name: str) -> None:
    print()
    print(f"请使用{app_name}扫描下方二维码登录：")
    segno.make(qrcode_content, error='L', boost_error=False).terminal(compact=True, border=0)
    print("在 Windows 下建议使用 Windows Terminal（支持 UTF-8，可完整显示二维码）")
    print(f"否则请打开 {qrcode_path} 扫码")
    print()
