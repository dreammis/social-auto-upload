"""素材管理器"""

from pathlib import Path
import json
import random

from materials.models import Material, MaterialType
from utils.log import taobao_guanghe_logger


class MaterialManager:
    """素材管理器"""

    def __init__(
        self,
        materials_dir: Path = Path("materials"),
        database_file: Path = Path("materials/database.json"),
    ):
        self.materials_dir = Path(materials_dir)
        self.database_file = Path(database_file)

        (self.materials_dir / "videos").mkdir(parents=True, exist_ok=True)
        (self.materials_dir / "covers").mkdir(parents=True, exist_ok=True)
        (self.materials_dir / "music").mkdir(parents=True, exist_ok=True)
        (self.materials_dir / "subtitles").mkdir(parents=True, exist_ok=True)

        self.materials: dict[str, Material] = {}

        if self.database_file.exists():
            self.load_database()

    def add_material(
        self,
        file_path: Path,
        material_type: MaterialType,
        title: str = "",
        description: str = "",
        tags: list[str] = None,
    ) -> Material:
        """添加素材"""
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        material = Material(file_path=file_path, type=material_type)

        material.metadata.title = title or file_path.stem
        material.metadata.description = description
        material.metadata.tags = tags or []

        # 检查重复
        for existing_id, existing in self.materials.items():
            if material.is_duplicate(existing):
                taobao_guanghe_logger.warning(
                    f"⚠️ 素材已存在: {existing.file_name} (ID: {existing_id})"
                )
                return existing

        self.materials[material.id] = material
        self.save_database()

        taobao_guanghe_logger.info(f"✅ 添加素材: {material.file_name}")

        return material

    def get_material(self, material_id: str) -> Material | None:
        """获取素材"""
        return self.materials.get(material_id)

    def find_materials(
        self,
        material_type: MaterialType | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
    ) -> list[Material]:
        """查找素材"""
        results = list(self.materials.values())

        if material_type:
            results = [m for m in results if m.type == material_type]

        if tags:
            results = [
                m for m in results
                if any(tag in m.metadata.tags for tag in tags)
            ]

        if status:
            results = [m for m in results if m.status == status]

        return results

    def get_random_material(
        self,
        material_type: MaterialType | None = None,
        tags: list[str] | None = None,
    ) -> Material | None:
        """随机获取一个素材"""
        materials = self.find_materials(material_type=material_type, tags=tags)
        return random.choice(materials) if materials else None

    def save_database(self):
        """保存素材数据库"""
        data = {
            "materials": [
                {
                    "id": m.id,
                    "type": m.type.value,
                    "file_path": str(m.file_path),
                    "file_name": m.file_name,
                    "file_hash": m.file_hash,
                    "metadata": {
                        "title": m.metadata.title,
                        "description": m.metadata.description,
                        "tags": m.metadata.tags,
                        "duration": m.metadata.duration,
                        "width": m.metadata.width,
                        "height": m.metadata.height,
                        "size": m.metadata.size,
                        "format": m.metadata.format,
                        "publish_count": m.metadata.publish_count,
                        "platforms": m.metadata.platforms,
                    },
                    "status": m.status,
                }
                for m in self.materials.values()
            ]
        }

        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.database_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_database(self):
        """加载素材数据库"""
        with open(self.database_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item in data.get('materials', []):
            material = Material(
                id=item['id'],
                file_path=Path(item['file_path']),
                type=MaterialType(item['type']),
            )
            material.metadata.title = item['metadata'].get('title', '')
            material.metadata.tags = item['metadata'].get('tags', [])
            self.materials[material.id] = material

        taobao_guanghe_logger.info(f"✅ 加载 {len(self.materials)} 个素材")
