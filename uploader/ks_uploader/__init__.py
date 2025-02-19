# -*- coding: utf-8 -*-
from pathlib import Path

from conf import BASE_DIR

from .modules.account import account_manager
from .modules.video import KSVideoUploader, KSBatchUploader
from .modules.validator import validator

__all__ = [
    'account_manager',
    'KSVideoUploader',
    'KSBatchUploader',
    'validator'
]

Path(BASE_DIR / "cookies" / "ks_uploader").mkdir(exist_ok=True)