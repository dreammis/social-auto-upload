# -*- coding: utf-8 -*-
from pathlib import Path

from conf import BASE_DIR
from .main import weixin_setup
from .modules.video import TencentVideo
from .modules.cookie import get_tencent_cookie

# 确保cookie目录存在
Path(BASE_DIR / "cookies" / "tencent_uploader").mkdir(exist_ok=True)

__all__ = [
    'weixin_setup',
    'TencentVideo',
    'get_tencent_cookie',
]