"""SAU 命令入口；平台参数与执行逻辑位于 sau_commands。"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Sequence

from sau_commands import (
    article, douyin, kuaishou, xiaohongshu, bilibili, tencent, alipay, weibo,
    hupu, facebook, facebook_page, instagram, youtube, baijiahao, dayu, xueqiu, zhihu,
)
from sau_commands.arguments import resolve_account_file


PLATFORMS = {
    "article": article,
    "douyin": douyin,
    "kuaishou": kuaishou,
    "xiaohongshu": xiaohongshu,
    "bilibili": bilibili,
    "tencent": tencent,
    "alipay": alipay,
    "weibo": weibo,
    "hupu": hupu,
    "facebook": facebook,
    "facebook-page": facebook_page,
    "instagram": instagram,
    "youtube": youtube,
    "baijiahao": baijiahao,
    "dayu": dayu,
    "xueqiu": xueqiu,
    "zhihu": zhihu,
}


def build_parser() -> argparse.ArgumentParser:
    """组装平台命令；每个平台维护自己的参数和执行函数。"""
    parser = argparse.ArgumentParser(prog="sau", description="CLI for social-auto-upload.")
    platform_parsers = parser.add_subparsers(dest="platform", required=True)
    for platform in PLATFORMS.values():
        platform.register(platform_parsers)
    return parser


async def dispatch(args: argparse.Namespace) -> int:
    """只按平台分发，不在入口重复平台的业务判断。"""
    if args.platform not in PLATFORMS:
        raise RuntimeError(f"Unsupported platform: {args.platform}")
    return await PLATFORMS[args.platform].run(args)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return asyncio.run(dispatch(args))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
