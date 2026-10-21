"""dayu 的命令参数与执行逻辑。"""
from __future__ import annotations
import json
from patchright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH
from utils.article_render import ARTICLE_THEMES
from uploader.dayu_uploader.article import DayuArticle
from uploader.dayu_uploader.constants import (
    DAYU_SOURCE_TYPES,
    DAYU_VIDEO_CATEGORIES,
    DAYU_SCHEDULE_MIN_HOURS,
    DAYU_SCHEDULE_MAX_DAYS,
    DAYU_SCHEDULE_STEP_MINUTES,
)
from uploader.dayu_uploader.main import DayuVideo
from uploader.dayu_uploader.session import (
    DAYU_HOME_URL,
    check_dayu_account,
    load_dayu_identity,
    login_dayu_account,
    read_dayu_identity,
)
from uploader.dayu_uploader.verification import verify_dayu_article, verify_dayu_video
from sau_commands.arguments import (
    SCHEDULE_FORMAT,
    add_runtime_flags,
    existing_file_path,
    parse_tags,
    resolve_account_file,
    schedule_value,
)


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
    dayu_parser = platform_parsers.add_parser("dayu", help="Dayu (大鱼号) video publishing and verification")
    dayu_actions = dayu_parser.add_subparsers(dest="action", required=True)
    dayu_login = dayu_actions.add_parser("login", help="Log in manually with visible Chrome")
    dayu_login.add_argument("--account", required=True, help="Local account alias")
    dayu_login.add_argument("--expected-name", help="Expected name displayed by Dayu")
    dayu_login.add_argument("--timeout", type=int, default=600, help="Login timeout in seconds")
    dayu_check = dayu_actions.add_parser("check", help="Check login and bound Dayu identity")
    dayu_check.add_argument("--account", required=True)
    dayu_upload = dayu_actions.add_parser("upload-video", help="Publish a video; succeed when Dayu confirms submission")
    dayu_upload.add_argument("--account", required=True)
    dayu_upload.add_argument("--file", required=True, type=existing_file_path)
    dayu_upload.add_argument("--title", required=True, help="Title, 5-60 Chinese character units")
    dayu_upload.add_argument("--desc", default="")
    dayu_upload.add_argument("--tags", default="", help="Comma-separated tags")
    dayu_upload.add_argument("--category", required=True, choices=DAYU_VIDEO_CATEGORIES, help="视频分类，按页面选项选择")
    dayu_upload.add_argument("--source", required=True, choices=DAYU_SOURCE_TYPES, help="按实际内容选择信息来源")
    dayu_upload.add_argument("--source-url", default="", help="转载时必填的 http/https 原文链接")
    dayu_upload.add_argument("--thumbnail", required=True, type=existing_file_path)
    dayu_upload.add_argument("--schedule", type=schedule_value,
                            help=f"{schedule_help}，北京时间，{DAYU_SCHEDULE_MIN_HOURS}小时后至{DAYU_SCHEDULE_MAX_DAYS}天内，分钟为{DAYU_SCHEDULE_STEP_MINUTES}的倍数")
    dayu_upload.add_argument("--prepare-only", action="store_true", help="Upload and fill only; do not click publish")
    dayu_upload.add_argument("--upload-timeout", type=int, default=600, help="Upload/processing timeout in seconds")
    add_runtime_flags(dayu_upload)
    dayu_article = dayu_actions.add_parser("upload-article", help="从正文文件发表图文，平台确认发表后返回成功")
    dayu_article.add_argument("--account", required=True, help="已登录的本地账号名称")
    dayu_article.add_argument("--title", required=True, help="图文标题，5–50字")
    dayu_article.add_argument("--content-file", required=True, type=existing_file_path, help="UTF-8 HTML、Markdown 或 TXT 正文文件")
    dayu_article.add_argument("--theme", choices=ARTICLE_THEMES, help="Markdown 渲染主题，默认 default；按大鱼号兼容排版发表")
    dayu_article.add_argument("--source", required=True, choices=DAYU_SOURCE_TYPES, help="按实际内容选择信息来源")
    dayu_article.add_argument("--source-url", default="", help="转载时必填的 http/https 原文链接")
    dayu_article.add_argument("--author", help="选填作者名称；省略时沿用网页已有值")
    dayu_article.add_argument("--cover-indices", nargs="+", type=int, help="选填1或3个正文图片序号（从1开始），对应单封面或三封面")
    dayu_article.add_argument("--schedule", type=schedule_value,
                             help=f"{schedule_help}，北京时间，{DAYU_SCHEDULE_MIN_HOURS}小时后至{DAYU_SCHEDULE_MAX_DAYS}天内，分钟为{DAYU_SCHEDULE_STEP_MINUTES}的倍数")
    dayu_article.add_argument("--prepare-only", action="store_true", help="上传和填写后结束，不发表")
    dayu_article.add_argument("--upload-timeout", type=int, default=600, help="每张图片上传等待秒数")
    add_runtime_flags(dayu_article)
    dayu_verify = dayu_actions.add_parser("verify", help="Check an existing publication without uploading again")
    dayu_verify.add_argument("--account", required=True)
    dayu_verify.add_argument("--type", choices=("video", "article"), help="作品类型；使用结果文件时自动识别，其余情况默认为video")
    dayu_target = dayu_verify.add_mutually_exclusive_group(required=True)
    dayu_target.add_argument("--content-id", help="Published content_id returned by Dayu")
    dayu_target.add_argument("--origin-id", help="Draft ID captured before confirming publication")
    dayu_target.add_argument("--result", type=existing_file_path, help="Saved Dayu result JSON to recover")
    dayu_verify.add_argument("--public", action="store_true", help="额外等待审核后检查公开正文或播放；不影响发表命令的成功判定")
    dayu_verify.add_argument("--timeout", type=int, default=60)
    add_runtime_flags(dayu_verify)


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
    account_file = resolve_account_file("dayu", args.account)
    if args.action == "login":
        if args.timeout <= 0:
            raise ValueError("登录期限必须大于 0 秒")
        result = await login_dayu_account(account_file, args.expected_name, args.timeout)
    elif args.action == "check":
        valid = await check_dayu_account(account_file)
        print("valid" if valid else "invalid")
        return 0 if valid else 1
    elif args.action == "upload-video":
        app = DayuVideo(
            title=args.title, file_path=args.file, tags=parse_tags(args.tags),
            account_file=account_file, thumbnail_path=args.thumbnail, category=args.category,
            source=args.source, desc=args.desc, headless=args.headless, debug=args.debug,
            prepare_only=args.prepare_only, upload_timeout=args.upload_timeout,
            source_url=args.source_url, schedule=args.schedule,
        )
        result = await app.main()
    elif args.action == "upload-article":
        app = DayuArticle(
            title=args.title, content_file=args.content_file, account_file=account_file,
            source=args.source, source_url=args.source_url, author=args.author,
            theme=args.theme, schedule=args.schedule,
            cover_indices=args.cover_indices, headless=args.headless, debug=args.debug,
            prepare_only=args.prepare_only, upload_timeout=args.upload_timeout,
        )
        result = await app.main()
    elif args.action == "verify":
        if args.timeout <= 0:
            raise ValueError("核验期限必须大于 0 秒")
        saved = json.loads(args.result.read_text(encoding="utf-8")) if args.result else {}
        expected = load_dayu_identity(account_file)
        if saved and saved.get("identity", {}).get("wmid") != expected["wmid"]:
            raise RuntimeError("结果文件与所选大鱼号主体不一致")
        kind = args.type or saved.get("type", "video")
        if saved.get("type") and saved["type"] != kind:
            raise ValueError("指定作品类型与结果文件不一致")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=args.headless,
            )
            try:
                context = await browser.new_context(storage_state=str(account_file))
                page = await context.new_page()
                await page.goto(DAYU_HOME_URL, wait_until="domcontentloaded", timeout=45000)
                identity = await read_dayu_identity(page)
                if identity["wmid"] != expected["wmid"]:
                    raise RuntimeError("核验时大鱼号主体与账号绑定不一致")
                if kind == "article":
                    result = await verify_dayu_article(
                        context, browser, identity,
                        content_id=args.content_id or saved.get("content_id"),
                        origin_id=args.origin_id or saved.get("origin_id"),
                        title=saved.get("title"), timeout=args.timeout, manifest=saved.get("manifest"), public=args.public,
                        schedule=saved.get("schedule"),
                    )
                else:
                    result = await verify_dayu_video(
                        context, browser, identity,
                        content_id=args.content_id or saved.get("content_id"),
                        origin_id=args.origin_id or saved.get("origin_id"),
                        title=saved.get("title"), timeout=args.timeout, public=args.public,
                        schedule=saved.get("schedule"),
                    )
                if args.result:
                    saved.update(result)
                    saved.pop("error", None)
                    args.result.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
            finally:
                await browser.close()
    else:
        raise RuntimeError(f"Unsupported Dayu action: {args.action}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
