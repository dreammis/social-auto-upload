"""
截图管理模块 - 用于无头模式自动化调试

功能：
1. 统一管理截图保存路径
2. 关键步骤截图（每个重要操作）
3. 错误自动截图（异常时诊断）
4. 截图文件命名规范（时间戳+平台+步骤）
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class ScreenshotManager:
    """截图管理器"""

    def __init__(self, platform: str, account: str = None, base_dir: str = "screenshots"):
        """
        初始化截图管理器

        Args:
            platform: 平台名称（如 'douyin', 'xiaohongshu', 'kuaishou'）
            account: 账号名称（可选）
            base_dir: 截图保存基础目录
        """
        self.platform = platform
        self.account = account or "unknown"
        self.base_dir = Path(base_dir)

        # 创建本次上传的截图目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.base_dir / platform / f"{timestamp}_{account}"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # 截图计数器
        self.screenshot_count = 0

        print(f"[ScreenshotManager] 截图目录: {self.session_dir}")

    def get_screenshot_path(self, step_name: str) -> Path:
        """
        获取截图保存路径

        Args:
            step_name: 步骤名称（如 'upload_video', 'set_cover', 'click_publish'）

        Returns:
            截图文件完整路径
        """
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{step_name}.png"
        return self.session_dir / filename

    async def take_screenshot(self, page, step_name: str, full_page: bool = False) -> Optional[str]:
        """
        执行截图并保存

        Args:
            page: Playwright Page 对象
            step_name: 步骤名称
            full_page: 是否全页截图

        Returns:
            截图文件路径（字符串），失败返回 None
        """
        try:
            screenshot_path = self.get_screenshot_path(step_name)
            await page.screenshot(path=str(screenshot_path), full_page=full_page)
            print(f"[ScreenshotManager] 截图保存: {screenshot_path}")
            return str(screenshot_path)
        except Exception as e:
            print(f"[ScreenshotManager] 截图失败: {e}")
            return None

    async def take_error_screenshot(self, page, error_msg: str = None) -> Optional[str]:
        """
        错误时截图诊断

        Args:
            page: Playwright Page 对象
            error_msg: 错误信息（可选）

        Returns:
            截图文件路径（字符串）
        """
        step_name = "ERROR"
        if error_msg:
            # 清理错误信息中的特殊字符
            clean_msg = error_msg[:50].replace(" ", "_").replace("/", "_").replace("\\", "_")
            step_name = f"ERROR_{clean_msg}"

        return await self.take_screenshot(page, step_name, full_page=True)

    def get_session_dir(self) -> str:
        """获取本次上传的截图目录路径"""
        return str(self.session_dir)

    def list_screenshots(self) -> list:
        """列出本次上传的所有截图"""
        screenshots = list(self.session_dir.glob("*.png"))
        return sorted([str(s) for s in screenshots])

    def cleanup_old_screenshots(self, days: int = 7):
        """
        清理旧截图（超过指定天数）

        Args:
            days: 保留天数
        """
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        for platform_dir in self.base_dir.iterdir():
            if platform_dir.is_dir():
                for session_dir in platform_dir.iterdir():
                    if session_dir.is_dir():
                        # 检查目录创建时间
                        dir_time = session_dir.stat().st_mtime
                        if dir_time < cutoff_time:
                            # 删除旧截图目录
                            for file in session_dir.glob("*"):
                                file.unlink()
                            session_dir.rmdir()
                            print(f"[ScreenshotManager] 清理旧截图: {session_dir}")


# 全局截图管理器实例（可选使用）
_global_screenshot_manager: Optional[ScreenshotManager] = None


def init_screenshot_manager(platform: str, account: str = None) -> ScreenshotManager:
    """
    初始化全局截图管理器

    Args:
        platform: 平台名称
        account: 账号名称

    Returns:
        ScreenshotManager 实例
    """
    global _global_screenshot_manager
    _global_screenshot_manager = ScreenshotManager(platform, account)
    return _global_screenshot_manager


def get_screenshot_manager() -> Optional[ScreenshotManager]:
    """获取全局截图管理器"""
    return _global_screenshot_manager