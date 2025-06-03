from pathlib import Path

from sau_backend.conf import BASE_DIR

Path(BASE_DIR / "cookies" / "douyin_uploader").mkdir(exist_ok=True)