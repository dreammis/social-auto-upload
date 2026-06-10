"""Cookie 管理器"""

from pathlib import Path
from datetime import datetime, timedelta
import shutil
import json

from utils.log import taobao_guanghe_logger


class CookieManager:
    """Cookie 管理器"""

    def __init__(
        self,
        cookie_dir: Path = Path("cookies"),
        backup_dir: Path = Path("cookies/backups"),
        check_interval: int = 3600,
    ):
        self.cookie_dir = Path(cookie_dir)
        self.backup_dir = Path(backup_dir)
        self.check_interval = check_interval

        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def validate_cookie(
        self,
        cookie_file: Path,
        platform: str = "taobao_guanghe",
        use_system_chrome: bool = True,
        skip_online_check: bool = False,
    ) -> tuple[bool, str]:
        """验证 Cookie 有效性"""
        if not cookie_file.exists():
            return False, "Cookie 文件不存在"

        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)

            if not isinstance(cookie_data, dict):
                return False, "Cookie 文件格式错误"

            # 检查文件格式
            if 'cookies' not in cookie_data or len(cookie_data['cookies']) == 0:
                return False, "Cookie 文件格式不完整"

            # 如果跳过在线检查，只验证格式
            if skip_online_check:
                return True, "文件格式有效（未在线验证）"

            if platform == "taobao_guanghe":
                try:
                    from uploader.taobao_guanghe_uploader.login import cookie_auth
                    is_valid = await cookie_auth(cookie_file, use_system_chrome=use_system_chrome)
                    return is_valid, "有效" if is_valid else "已失效"
                except Exception as e:
                    # 网络问题时降级到格式验证
                    if "ERR_NAME_NOT_RESOLVED" in str(e):
                        taobao_guanghe_logger.warning("⚠️ 网络问题，跳过在线验证")
                        return True, "文件格式有效（网络问题，未在线验证）"
                    raise

            return False, "不支持的平台"

        except json.JSONDecodeError:
            return False, "Cookie 文件格式错误"
        except Exception as e:
            return False, f"验证失败: {str(e)}"

    def backup_cookie(self, cookie_file: Path) -> Path:
        """备份 Cookie 文件"""
        if not cookie_file.exists():
            raise FileNotFoundError(f"Cookie 文件不存在: {cookie_file}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{cookie_file.stem}_{timestamp}.json"
        backup_file = self.backup_dir / backup_name

        shutil.copy2(cookie_file, backup_file)
        taobao_guanghe_logger.info(f"💾 Cookie 已备份: {backup_file}")

        return backup_file

    def restore_cookie(self, backup_file: Path, target_file: Path):
        """恢复 Cookie 文件"""
        if not backup_file.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_file}")

        if target_file.exists():
            self.backup_cookie(target_file)

        shutil.copy2(backup_file, target_file)
        taobao_guanghe_logger.info(f"♻️ Cookie 已恢复: {target_file}")

    def get_cookie_info(self, cookie_file: Path) -> dict:
        """获取 Cookie 文件信息"""
        if not cookie_file.exists():
            return {"exists": False, "path": str(cookie_file)}

        stat = cookie_file.stat()

        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)
            cookie_count = len(cookie_data.get('cookies', []))
        except:
            cookie_count = 0

        return {
            "exists": True,
            "path": str(cookie_file),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "cookie_count": cookie_count,
        }

    def cleanup_old_backups(self, keep_days: int = 30):
        """清理旧的备份文件"""
        cutoff = datetime.now() - timedelta(days=keep_days)
        deleted = 0

        for backup_file in self.backup_dir.glob("*.json"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff:
                backup_file.unlink()
                deleted += 1

        if deleted > 0:
            taobao_guanghe_logger.info(f"🗑️ 清理 {deleted} 个过期备份")
