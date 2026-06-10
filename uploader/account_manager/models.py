"""账号管理数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class AccountMetadata:
    """账号元数据"""
    created_at: datetime = field(default_factory=datetime.now)
    last_login: datetime | None = None
    last_check: datetime | None = None
    total_uploads: int = 0
    failed_uploads: int = 0
    cookie_expires_at: datetime | None = None


@dataclass
class Account:
    """账号模型"""

    # 基本信息
    name: str
    display_name: str
    platform: str = "taobao_guanghe"

    # Cookie 配置
    cookie_file: Path | None = None

    # 状态
    enabled: bool = True
    status: Literal["active", "inactive", "expired", "error"] = "active"

    # 分组和优先级
    group: str = "default"
    priority: int = 5

    # 限制
    max_daily_uploads: int = 100
    current_daily_uploads: int = 0

    # 代理
    proxy: str | None = None

    # 备注
    remark: str = ""

    # 元数据
    metadata: AccountMetadata = field(default_factory=AccountMetadata)

    def __post_init__(self):
        if isinstance(self.cookie_file, str):
            self.cookie_file = Path(self.cookie_file)

    def is_available(self) -> bool:
        """检查账号是否可用"""
        return (
            self.enabled
            and self.status == "active"
            and self.current_daily_uploads < self.max_daily_uploads
            and self.cookie_file
            and self.cookie_file.exists()
        )

    def reset_daily_uploads(self):
        """重置每日上传计数"""
        self.current_daily_uploads = 0

    def increment_uploads(self):
        """增加上传计数"""
        self.current_daily_uploads += 1
        self.metadata.total_uploads += 1
