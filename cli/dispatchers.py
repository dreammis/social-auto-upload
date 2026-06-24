"""Platform dispatchers for CLI commands."""
from __future__ import annotations

import argparse
import sys
from typing import Any

from cli.models import (
    BaijiahaoVideoUploadRequest,
    BilibiliNoteUploadRequest,
    BilibiliVideoUploadRequest,
    DouyinNoteUploadRequest,
    DouyinVideoUploadRequest,
    KuaishouNoteUploadRequest,
    KuaishouVideoUploadRequest,
    TencentNoteUploadRequest,
    TencentVideoUploadRequest,
    TiktokVideoUploadRequest,
    XiaohongshuNoteUploadRequest,
    XiaohongshuVideoUploadRequest,
)
from cli.platforms import (
    baijiahao,
    bilibili,
    douyin,
    kuaishou,
    tencent,
    tiktok,
    xiaohongshu,
)
from cli.utils import parse_image_files, parse_tags

from uploader.douyin_uploader.main import (
    DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
    DOUYIN_PUBLISH_STRATEGY_SCHEDULED,
)
from uploader.ks_uploader.main import (
    KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE,
    KUAISHOU_PUBLISH_STRATEGY_SCHEDULED,
)
from uploader.tencent_uploader.main import (
    TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
    TENCENT_PUBLISH_STRATEGY_SCHEDULED,
)
from uploader.xiaohongshu_uploader.main import (
    XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
    XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
)


async def _dispatch_douyin(args: argparse.Namespace) -> int:
    """Dispatch Douyin commands."""
    if args.action == 'login':
        result = await douyin.login(args.account, headless=args.headless)
        if not result['success']:
            raise RuntimeError(result['message'])
        print(f"Douyin login flow completed: {result['account_file']}")
        return 0
    if args.action == 'check':
        is_valid = await douyin.check(args.account)
        print('valid' if is_valid else 'invalid')
        return 0 if is_valid else 1

    publish_strategy = DOUYIN_PUBLISH_STRATEGY_SCHEDULED if args.schedule else DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
    if args.action == 'upload-video':
        request = DouyinVideoUploadRequest(
            account_name=args.account,
            video_file=args.file,
            title=args.title,
            description=args.desc,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            thumbnail_file=args.thumbnail,
            thumbnail_landscape_file=args.thumbnail_landscape,
            thumbnail_portrait_file=args.thumbnail_portrait,
            product_link=args.product_link,
            product_title=args.product_title,
            publish_strategy=publish_strategy,
            debug=args.debug,
            headless=args.headless,
        )
        await douyin.upload_video(request)
        print(f'Douyin video upload submitted: {request.video_file}')
        return 0
    if args.action == 'upload-note':
        request = DouyinNoteUploadRequest(
            account_name=args.account,
            image_files=parse_image_files(args.images),
            title=args.title,
            note=args.note,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            publish_strategy=publish_strategy,
            debug=args.debug,
            headless=args.headless,
        )
        await douyin.upload_note(request)
        print(f'Douyin note upload submitted: {len(request.image_files)} images')
        return 0
    raise RuntimeError(f'Unsupported Douyin action: {args.action}')


async def _dispatch_kuaishou(args: argparse.Namespace) -> int:
    """Dispatch Kuaishou commands."""
    if args.action == 'login':
        result = await kuaishou.login(args.account, headless=args.headless)
        if not result['success']:
            raise RuntimeError(result['message'])
        print(f"Kuaishou login flow completed: {result['account_file']}")
        return 0
    if args.action == 'check':
        is_valid = await kuaishou.check(args.account)
        print('valid' if is_valid else 'invalid')
        return 0 if is_valid else 1

    publish_strategy = KUAISHOU_PUBLISH_STRATEGY_SCHEDULED if args.schedule else KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE
    if args.action == 'upload-video':
        request = KuaishouVideoUploadRequest(
            account_name=args.account,
            video_file=args.file,
            title=args.title,
            description=args.desc,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            thumbnail_file=args.thumbnail,
            publish_strategy=publish_strategy,
            debug=args.debug,
            headless=args.headless,
        )
        await kuaishou.upload_video(request)
        print(f'Kuaishou video upload submitted: {request.video_file}')
        return 0
    if args.action == 'upload-note':
        request = KuaishouNoteUploadRequest(
            account_name=args.account,
            image_files=parse_image_files(args.images),
            title=args.title,
            note=args.note,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            publish_strategy=publish_strategy,
            debug=args.debug,
            headless=args.headless,
        )
        await kuaishou.upload_note(request)
        print(f'Kuaishou note upload submitted: {len(request.image_files)} images')
        return 0
    raise RuntimeError(f'Unsupported Kuaishou action: {args.action}')


async def _dispatch_xiaohongshu(args: argparse.Namespace) -> int:
    """Dispatch Xiaohongshu commands."""
    if args.action == 'login':
        result = await xiaohongshu.login(args.account, headless=args.headless)
        if not result['success']:
            raise RuntimeError(result['message'])
        print(f"Xiaohongshu login flow completed: {result['account_file']}")
        return 0
    if args.action == 'check':
        is_valid = await xiaohongshu.check(args.account)
        print('valid' if is_valid else 'invalid')
        return 0 if is_valid else 1

    publish_strategy = XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED if args.schedule else XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    if args.action == 'upload-video':
        parsed_tags = parse_tags(args.tags)
        if len(parsed_tags) > 10:
            print(f'错误：小红书标签最多 10 个，当前提供了 {len(parsed_tags)} 个: {parsed_tags}', file=sys.stderr)
            return 1
        request = XiaohongshuVideoUploadRequest(
            account_name=args.account,
            video_file=args.file,
            title=args.title,
            description=args.desc,
            tags=parsed_tags,
            publish_date=args.schedule or 0,
            thumbnail_file=args.thumbnail,
            publish_strategy=publish_strategy,
            debug=args.debug,
            headless=args.headless,
        )
        await xiaohongshu.upload_video(request)
        print(f'Xiaohongshu video upload submitted: {request.video_file}')
        return 0
    if args.action == 'upload-note':
        parsed_tags = parse_tags(args.tags)
        if len(parsed_tags) > 10:
            print(f'错误：小红书标签最多 10 个，当前提供了 {len(parsed_tags)} 个: {parsed_tags}', file=sys.stderr)
            return 1
        request = XiaohongshuNoteUploadRequest(
            account_name=args.account,
            image_files=parse_image_files(args.images),
            title=args.title,
            note=args.note,
            tags=parsed_tags,
            publish_date=args.schedule or 0,
            publish_strategy=publish_strategy,
            debug=args.debug,
            headless=args.headless,
        )
        await xiaohongshu.upload_note(request)
        print(f'Xiaohongshu note upload submitted: {len(request.image_files)} images')
        return 0
    raise RuntimeError(f'Unsupported Xiaohongshu action: {args.action}')


async def _dispatch_bilibili(args: argparse.Namespace) -> int:
    """Dispatch Bilibili commands."""
    if args.action == 'login':
        result = await bilibili.login(args.account, headless=args.headless)
        if not result['success']:
            raise RuntimeError(result['message'])
        print(f"Bilibili login flow completed: {result['account_file']}")
        return 0
    if args.action == 'check':
        is_valid = await bilibili.check(args.account)
        print('valid' if is_valid else 'invalid')
        return 0 if is_valid else 1
    if args.action == 'upload-video':
        request = BilibiliVideoUploadRequest(
            account_name=args.account,
            video_file=args.file,
            title=args.title,
            description=args.desc,
            tid=args.tid,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
        )
        await bilibili.upload_video(request)
        print(f'Bilibili video upload submitted: {request.video_file}')
        return 0
    if args.action == 'upload-note':
        parsed_tags = parse_tags(args.tags)
        request = BilibiliNoteUploadRequest(
            account_name=args.account,
            image_files=parse_image_files(args.images),
            title=args.title,
            note=args.note,
            tags=parsed_tags,
            publish_date=args.schedule or 0,
            publish_strategy='scheduled' if args.schedule else 'immediate',
            debug=args.debug,
            headless=args.headless,
        )
        await bilibili.upload_note(request)
        print(f'Bilibili note upload submitted: {len(request.image_files)} images')
        return 0
    raise RuntimeError(f'Unsupported Bilibili action: {args.action}')


async def _dispatch_tencent(args: argparse.Namespace) -> int:
    """Dispatch Tencent/WeChat Channels commands."""
    if args.action == 'login':
        result = await tencent.login(args.account, headless=args.headless)
        if not result['success']:
            raise RuntimeError(result['message'])
        print(f"Tencent/WeChat Channels login flow completed: {result['account_file']}")
        return 0
    if args.action == 'check':
        is_valid = await tencent.check(args.account)
        print('valid' if is_valid else 'invalid')
        return 0 if is_valid else 1

    publish_strategy = TENCENT_PUBLISH_STRATEGY_SCHEDULED if args.schedule else TENCENT_PUBLISH_STRATEGY_IMMEDIATE
    if args.action == 'upload-video':
        request = TencentVideoUploadRequest(
            account_name=args.account,
            video_file=args.file,
            title=args.title,
            description=args.desc,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            thumbnail_file=args.thumbnail,
            thumbnail_landscape_file=args.thumbnail_landscape,
            thumbnail_portrait_file=args.thumbnail_portrait,
            short_title=args.short_title,
            category=args.category,
            is_draft=args.draft,
            publish_strategy=publish_strategy,
            debug=args.debug,
            headless=args.headless,
        )
        await tencent.upload_video(request)
        print(f'Tencent/WeChat Channels video upload submitted: {request.video_file}')
        return 0
    if args.action == 'upload-note':
        request = TencentNoteUploadRequest(
            account_name=args.account,
            image_files=parse_image_files(args.images),
            title=args.title,
            note=args.note,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            publish_strategy=publish_strategy,
            debug=args.debug,
            headless=args.headless,
            is_draft=args.draft,
        )
        await tencent.upload_note(request)
        print(f'Tencent/WeChat Channels note upload submitted: {len(request.image_files)} images')
        return 0
    raise RuntimeError(f'Unsupported Tencent/WeChat Channels action: {args.action}')


async def _dispatch_tiktok(args: argparse.Namespace) -> int:
    """Dispatch TikTok commands."""
    if args.action == 'login':
        result = await tiktok.login(args.account, headless=args.headless)
        if not result['success']:
            raise RuntimeError(result['message'])
        print(f"TikTok login flow completed: {result['account_file']}")
        return 0
    if args.action == 'check':
        is_valid = await tiktok.check(args.account)
        print('valid' if is_valid else 'invalid')
        return 0 if is_valid else 1
    if args.action == 'upload-video':
        request = TiktokVideoUploadRequest(
            account_name=args.account,
            video_file=args.file,
            title=args.title,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            debug=args.debug,
            headless=args.headless,
        )
        await tiktok.upload_video(request)
        print(f'TikTok video upload submitted: {request.video_file}')
        return 0
    raise RuntimeError(f'Unsupported TikTok action: {args.action}')


async def _dispatch_baijiahao(args: argparse.Namespace) -> int:
    """Dispatch Baijiahao commands."""
    if args.action == 'login':
        result = await baijiahao.login(args.account, headless=args.headless)
        if not result['success']:
            raise RuntimeError(result['message'])
        print(f"Baijiahao login flow completed: {result['account_file']}")
        return 0
    if args.action == 'check':
        is_valid = await baijiahao.check(args.account)
        print('valid' if is_valid else 'invalid')
        return 0 if is_valid else 1
    if args.action == 'upload-video':
        request = BaijiahaoVideoUploadRequest(
            account_name=args.account,
            video_file=args.file,
            title=args.title,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            debug=args.debug,
            headless=args.headless,
        )
        await baijiahao.upload_video(request)
        print(f'Baijiahao video upload submitted: {request.video_file}')
        return 0
    raise RuntimeError(f'Unsupported Baijiahao action: {args.action}')


PLATFORM_REGISTRY: dict[str, Any] = {
    'douyin': _dispatch_douyin,
    'kuaishou': _dispatch_kuaishou,
    'xiaohongshu': _dispatch_xiaohongshu,
    'bilibili': _dispatch_bilibili,
    'tencent': _dispatch_tencent,
    'tiktok': _dispatch_tiktok,
    'baijiahao': _dispatch_baijiahao,
}


async def dispatch(args: argparse.Namespace) -> int:
    """Dispatch command to appropriate platform handler."""
    handler = PLATFORM_REGISTRY.get(args.platform)
    if handler is None:
        valid_platforms = ', '.join(sorted(PLATFORM_REGISTRY.keys()))
        raise RuntimeError(f'Unsupported platform: {args.platform}. Valid platforms: {valid_platforms}')
    return await handler(args)
