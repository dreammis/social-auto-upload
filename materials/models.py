"""素材管理数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
import hashlib


class MaterialType(Enum):
    """素材类型"""
    VIDEO = "video"
    COVER = "cover"
    MUSIC = "music"
    SUBTITLE = "subtitle"


@dataclass
class MaterialMetadata:
    """素材元数据"""
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = ""

    duration: float = 0.0
    width: int = 0
    height: int = 0
    size: int = 0
    format: str = ""

    publish_count: int = 0
    platforms: list[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Material:
    """素材基类"""

    id: str = ""
    file_path: Path = None
    file_name: str = ""
    file_hash: str = ""

    type: MaterialType = MaterialType.VIDEO

    metadata: MaterialMetadata = field(default_factory=MaterialMetadata)

    status: str = "draft"

    def __post_init__(self):
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)

        if not self.file_name and self.file_path:
            self.file_name = self.file_path.name

        if not self.file_hash and self.file_path and self.file_path.exists():
            self.file_hash = self.calculate_hash()

        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())

    def calculate_hash(self) -> str:
        """计算文件 MD5"""
        if not self.file_path or not self.file_path.exists():
            return ""

        md5 = hashlib.md5()
        with open(self.file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def is_duplicate(self, other: 'Material') -> bool:
        """检查是否与另一个素材重复"""
        return self.file_hash == other.file_hash and self.file_hash != ""
