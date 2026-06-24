"""CLI entry point for social-auto-upload.

This module provides backward compatibility by re-exporting from the new cli package.
"""
from __future__ import annotations

import sys

from cli.dispatchers import dispatch
from cli.main import main
from cli.parser import build_parser
from cli.platforms.baijiahao import login as login_baijiahao_account
from cli.platforms.bilibili import check as check_bilibili_account
from cli.platforms.bilibili import login as login_bilibili_account
from cli.platforms.douyin import check as check_douyin_account
from cli.platforms.douyin import login as login_douyin_account
from cli.platforms.douyin import upload_note, upload_video
from cli.platforms.kuaishou import check as check_kuaishou_account
from cli.platforms.kuaishou import login as login_kuaishou_account
from cli.platforms.tencent import login as login_tencent_account
from cli.platforms.tencent import upload_video as upload_tencent_video
from cli.platforms.tiktok import login as login_tiktok_account
from cli.platforms.xiaohongshu import check as check_xiaohongshu_account
from cli.platforms.xiaohongshu import login as login_xiaohongshu_account
from cli.platforms.xiaohongshu import upload_note as upload_xiaohongshu_note
from cli.platforms.xiaohongshu import upload_video as upload_xiaohongshu_video

__all__ = [
    'build_parser',
    'dispatch',
    'main',
    'check_douyin_account',
    'check_kuaishou_account',
    'check_xiaohongshu_account',
    'check_bilibili_account',
    'login_baijiahao_account',
    'login_bilibili_account',
    'login_douyin_account',
    'login_kuaishou_account',
    'login_tencent_account',
    'login_tiktok_account',
    'login_xiaohongshu_account',
    'upload_note',
    'upload_video',
    'upload_tencent_video',
    'upload_xiaohongshu_note',
    'upload_xiaohongshu_video',
]

if __name__ == '__main__':
    sys.exit(main())
