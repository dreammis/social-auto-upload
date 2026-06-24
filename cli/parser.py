"""CLI argument parser."""
from __future__ import annotations

import argparse
from pathlib import Path

from cli.utils import SCHEDULE_FORMAT, parse_schedule


def existing_file_path(value: str) -> Path:
    """Validate that the file path exists."""
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f'File not found: {value}')
    return path


def schedule_value(value: str):
    """Parse schedule value."""
    try:
        return parse_schedule(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid schedule '{value}'. Expected format: {SCHEDULE_FORMAT}"
        ) from exc


def add_runtime_flags(parser: argparse.ArgumentParser) -> None:
    """Add debug and headless flags to parser."""
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument(
        '--headed', dest='headless', action='store_false', help='Run with browser UI'
    )
    headless_group.add_argument(
        '--headless', dest='headless', action='store_true', help='Run in headless mode'
    )
    parser.set_defaults(headless=True)


def _add_douyin_parser(platform_parsers) -> None:
    """Add Douyin subcommands."""
    douyin_parser = platform_parsers.add_parser('douyin', help='Douyin operations')
    douyin_actions = douyin_parser.add_subparsers(dest='action', required=True)

    for action_name in ('login', 'check'):
        action_parser = douyin_actions.add_parser(action_name, help=f'Douyin {action_name}')
        action_parser.add_argument('--account', required=True, help='Douyin user-defined account_name')
        if action_name == 'login':
            add_runtime_flags(action_parser)

    upload_video_parser = douyin_actions.add_parser('upload-video', help='Upload one video to Douyin')
    upload_video_parser.add_argument('--account', required=True, help='Douyin user-defined account_name')
    upload_video_parser.add_argument('--file', required=True, type=existing_file_path, help='Video file path')
    upload_video_parser.add_argument('--title', required=True, help='Video title')
    upload_video_parser.add_argument('--desc', default='', help='Optional video description')
    upload_video_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    upload_video_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    upload_video_parser.add_argument('--thumbnail', type=existing_file_path, help='Optional 3:4 portrait thumbnail path')
    upload_video_parser.add_argument('--thumbnail-landscape', type=existing_file_path, help='Optional 4:3 landscape thumbnail path')
    upload_video_parser.add_argument('--thumbnail-portrait', type=existing_file_path, help='Optional 3:4 portrait thumbnail path')
    upload_video_parser.add_argument('--product-link', default='', help='Optional product link')
    upload_video_parser.add_argument('--product-title', default='', help='Optional product title')
    add_runtime_flags(upload_video_parser)

    upload_note_parser = douyin_actions.add_parser('upload-note', help='Upload one note to Douyin')
    upload_note_parser.add_argument('--account', required=True, help='Douyin user-defined account_name')
    upload_note_parser.add_argument('--images', required=True, nargs='+', type=existing_file_path, help='Image file paths')
    upload_note_parser.add_argument('--title', required=True, help='Note title')
    upload_note_parser.add_argument('--note', default='', help='Optional note content')
    upload_note_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    upload_note_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    add_runtime_flags(upload_note_parser)


def _add_kuaishou_parser(platform_parsers) -> None:
    """Add Kuaishou subcommands."""
    kuaishou_parser = platform_parsers.add_parser('kuaishou', help='Kuaishou operations')
    kuaishou_actions = kuaishou_parser.add_subparsers(dest='action', required=True)

    for action_name in ('login', 'check'):
        action_parser = kuaishou_actions.add_parser(action_name, help=f'Kuaishou {action_name}')
        action_parser.add_argument('--account', required=True, help='Kuaishou user-defined account_name')
        if action_name == 'login':
            add_runtime_flags(action_parser)

    kuaishou_upload_video_parser = kuaishou_actions.add_parser('upload-video', help='Upload one video to Kuaishou')
    kuaishou_upload_video_parser.add_argument('--account', required=True, help='Kuaishou user-defined account_name')
    kuaishou_upload_video_parser.add_argument('--file', required=True, type=existing_file_path, help='Video file path')
    kuaishou_upload_video_parser.add_argument('--title', required=True, help='Video title')
    kuaishou_upload_video_parser.add_argument('--desc', default='', help='Optional video description')
    kuaishou_upload_video_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    kuaishou_upload_video_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    kuaishou_upload_video_parser.add_argument('--thumbnail', type=existing_file_path, help='Optional thumbnail path')
    add_runtime_flags(kuaishou_upload_video_parser)

    kuaishou_upload_note_parser = kuaishou_actions.add_parser('upload-note', help='Upload one note to Kuaishou')
    kuaishou_upload_note_parser.add_argument('--account', required=True, help='Kuaishou user-defined account_name')
    kuaishou_upload_note_parser.add_argument('--images', required=True, nargs='+', type=existing_file_path, help='Image file paths')
    kuaishou_upload_note_parser.add_argument('--title', required=True, help='Note title')
    kuaishou_upload_note_parser.add_argument('--note', default='', help='Optional note content')
    kuaishou_upload_note_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    kuaishou_upload_note_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    add_runtime_flags(kuaishou_upload_note_parser)


def _add_xiaohongshu_parser(platform_parsers) -> None:
    """Add Xiaohongshu subcommands."""
    xiaohongshu_parser = platform_parsers.add_parser('xiaohongshu', help='Xiaohongshu operations')
    xiaohongshu_actions = xiaohongshu_parser.add_subparsers(dest='action', required=True)

    for action_name in ('login', 'check'):
        action_parser = xiaohongshu_actions.add_parser(action_name, help=f'Xiaohongshu {action_name}')
        action_parser.add_argument('--account', required=True, help='Xiaohongshu user-defined account_name')
        if action_name == 'login':
            add_runtime_flags(action_parser)

    xiaohongshu_upload_video_parser = xiaohongshu_actions.add_parser('upload-video', help='Upload one video to Xiaohongshu')
    xiaohongshu_upload_video_parser.add_argument('--account', required=True, help='Xiaohongshu user-defined account_name')
    xiaohongshu_upload_video_parser.add_argument('--file', required=True, type=existing_file_path, help='Video file path')
    xiaohongshu_upload_video_parser.add_argument('--title', required=True, help='Video title')
    xiaohongshu_upload_video_parser.add_argument('--desc', default='', help='Optional video description')
    xiaohongshu_upload_video_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    xiaohongshu_upload_video_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    xiaohongshu_upload_video_parser.add_argument('--thumbnail', type=existing_file_path, help='Optional thumbnail path')
    add_runtime_flags(xiaohongshu_upload_video_parser)

    xiaohongshu_upload_note_parser = xiaohongshu_actions.add_parser('upload-note', help='Upload one note to Xiaohongshu')
    xiaohongshu_upload_note_parser.add_argument('--account', required=True, help='Xiaohongshu user-defined account_name')
    xiaohongshu_upload_note_parser.add_argument('--images', required=True, nargs='+', type=existing_file_path, help='Image file paths')
    xiaohongshu_upload_note_parser.add_argument('--title', required=True, help='Note title')
    xiaohongshu_upload_note_parser.add_argument('--note', default='', help='Optional note content')
    xiaohongshu_upload_note_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    xiaohongshu_upload_note_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    add_runtime_flags(xiaohongshu_upload_note_parser)


def _add_bilibili_parser(platform_parsers) -> None:
    """Add Bilibili subcommands."""
    bilibili_parser = platform_parsers.add_parser('bilibili', help='Bilibili operations')
    bilibili_actions = bilibili_parser.add_subparsers(dest='action', required=True)

    for action_name in ('login', 'check'):
        action_parser = bilibili_actions.add_parser(action_name, help=f'Bilibili {action_name}')
        action_parser.add_argument('--account', required=True, help='Bilibili user-defined account_name')
        if action_name == 'login':
            add_runtime_flags(action_parser)

    bilibili_upload_video_parser = bilibili_actions.add_parser('upload-video', help='Upload one video to Bilibili')
    bilibili_upload_video_parser.add_argument('--account', required=True, help='Bilibili user-defined account_name')
    bilibili_upload_video_parser.add_argument('--file', required=True, type=existing_file_path, help='Video file path')
    bilibili_upload_video_parser.add_argument('--title', required=True, help='Video title')
    bilibili_upload_video_parser.add_argument('--desc', required=True, help='Video description')
    bilibili_upload_video_parser.add_argument('--tid', required=True, type=int, help='Bilibili category id')
    bilibili_upload_video_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    bilibili_upload_video_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')

    bilibili_upload_note_parser = bilibili_actions.add_parser('upload-note', help='Upload note with images to Bilibili')
    bilibili_upload_note_parser.add_argument('--account', required=True, help='Bilibili user-defined account_name')
    bilibili_upload_note_parser.add_argument('--images', nargs='+', required=True, type=existing_file_path, help='Image file paths')
    bilibili_upload_note_parser.add_argument('--title', required=True, help='Note title')
    bilibili_upload_note_parser.add_argument('--note', default='', help='Optional note content')
    bilibili_upload_note_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    bilibili_upload_note_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    add_runtime_flags(bilibili_upload_note_parser)


def _add_tencent_parser(platform_parsers) -> None:
    """Add Tencent/WeChat Channels subcommands."""
    tencent_parser = platform_parsers.add_parser('tencent', help='Tencent/WeChat Channels operations')
    tencent_actions = tencent_parser.add_subparsers(dest='action', required=True)

    for action_name in ('login', 'check'):
        action_parser = tencent_actions.add_parser(action_name, help=f'Tencent/WeChat Channels {action_name}')
        action_parser.add_argument('--account', required=True, help='Tencent user-defined account_name')
        if action_name == 'login':
            add_runtime_flags(action_parser)

    tencent_upload_video_parser = tencent_actions.add_parser('upload-video', help='Upload one video to WeChat Channels')
    tencent_upload_video_parser.add_argument('--account', required=True, help='Tencent user-defined account_name')
    tencent_upload_video_parser.add_argument('--file', required=True, type=existing_file_path, help='Video file path')
    tencent_upload_video_parser.add_argument('--title', required=True, help='Video title')
    tencent_upload_video_parser.add_argument('--desc', default='', help='Optional video description')
    tencent_upload_video_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    tencent_upload_video_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    tencent_upload_video_parser.add_argument('--thumbnail', type=existing_file_path, help='Optional 3:4 portrait thumbnail path')
    tencent_upload_video_parser.add_argument('--thumbnail-landscape', type=existing_file_path, help='Optional 4:3 landscape thumbnail path')
    tencent_upload_video_parser.add_argument('--thumbnail-portrait', type=existing_file_path, help='Optional 3:4 portrait thumbnail path')
    tencent_upload_video_parser.add_argument('--short-title', help='Optional WeChat Channels short title')
    tencent_upload_video_parser.add_argument('--category', help='Optional original content category')
    tencent_upload_video_parser.add_argument('--draft', action='store_true', help='Save as draft instead of publishing')
    add_runtime_flags(tencent_upload_video_parser)

    tencent_upload_note_parser = tencent_actions.add_parser('upload-note', help='Upload image note (图文) to WeChat Channels')
    tencent_upload_note_parser.add_argument('--account', required=True, help='Tencent user-defined account_name')
    tencent_upload_note_parser.add_argument('--images', required=True, nargs='+', type=existing_file_path, help='Image file paths')
    tencent_upload_note_parser.add_argument('--title', required=True, help='Note title')
    tencent_upload_note_parser.add_argument('--note', default='', help='Optional note content')
    tencent_upload_note_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    tencent_upload_note_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    tencent_upload_note_parser.add_argument('--draft', action='store_true', help='Save as draft instead of publishing')
    add_runtime_flags(tencent_upload_note_parser)


def _add_tiktok_parser(platform_parsers) -> None:
    """Add TikTok subcommands."""
    tiktok_parser = platform_parsers.add_parser('tiktok', help='TikTok operations')
    tiktok_actions = tiktok_parser.add_subparsers(dest='action', required=True)

    for action_name in ('login', 'check'):
        action_parser = tiktok_actions.add_parser(action_name, help=f'TikTok {action_name}')
        action_parser.add_argument('--account', required=True, help='TikTok user-defined account_name')
        if action_name == 'login':
            add_runtime_flags(action_parser)

    tiktok_upload_video_parser = tiktok_actions.add_parser('upload-video', help='Upload one video to TikTok')
    tiktok_upload_video_parser.add_argument('--account', required=True, help='TikTok user-defined account_name')
    tiktok_upload_video_parser.add_argument('--file', required=True, type=existing_file_path, help='Video file path')
    tiktok_upload_video_parser.add_argument('--title', required=True, help='Video title')
    tiktok_upload_video_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    tiktok_upload_video_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    add_runtime_flags(tiktok_upload_video_parser)


def _add_baijiahao_parser(platform_parsers) -> None:
    """Add Baijiahao subcommands."""
    baijiahao_parser = platform_parsers.add_parser('baijiahao', help='Baijiahao operations')
    baijiahao_actions = baijiahao_parser.add_subparsers(dest='action', required=True)

    for action_name in ('login', 'check'):
        action_parser = baijiahao_actions.add_parser(action_name, help=f'Baijiahao {action_name}')
        action_parser.add_argument('--account', required=True, help='Baijiahao user-defined account_name')
        if action_name == 'login':
            add_runtime_flags(action_parser)

    baijiahao_upload_video_parser = baijiahao_actions.add_parser('upload-video', help='Upload one video to Baijiahao')
    baijiahao_upload_video_parser.add_argument('--account', required=True, help='Baijiahao user-defined account_name')
    baijiahao_upload_video_parser.add_argument('--file', required=True, type=existing_file_path, help='Video file path')
    baijiahao_upload_video_parser.add_argument('--title', required=True, help='Video title')
    baijiahao_upload_video_parser.add_argument('--tags', default='', help='Comma-separated tags, such as tag1,tag2')
    baijiahao_upload_video_parser.add_argument('--schedule', type=schedule_value, help=f'Schedule time in {SCHEDULE_FORMAT}')
    add_runtime_flags(baijiahao_upload_video_parser)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(prog='sau', description='CLI for social-auto-upload.')
    platform_parsers = parser.add_subparsers(dest='platform', required=True)

    _add_douyin_parser(platform_parsers)
    _add_kuaishou_parser(platform_parsers)
    _add_xiaohongshu_parser(platform_parsers)
    _add_bilibili_parser(platform_parsers)
    _add_tencent_parser(platform_parsers)
    _add_tiktok_parser(platform_parsers)
    _add_baijiahao_parser(platform_parsers)

    return parser
