"""工具函数：保存 Canvas 二维码"""

from pathlib import Path


def save_canvas_qrcode(canvas_screenshot_path: Path) -> Path:
    """
    保存 Canvas 截图作为二维码

    Args:
        canvas_screenshot_path: Canvas 截图路径

    Returns:
        Path: 保存的二维码路径
    """
    # Canvas 截图已经是二维码图片，直接返回路径
    return canvas_screenshot_path
