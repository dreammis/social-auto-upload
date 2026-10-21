"""zhihu 的命令参数与执行逻辑。"""
from __future__ import annotations
import json
from uploader.zhihu_uploader.article import ZhihuArticle
from uploader.zhihu_uploader.constants import (
    ZHIHU_SCHEDULE_MAX_HOURS,
    ZHIHU_SCHEDULE_MINUTES,
    ZHIHU_ORIGINALITY,
    ZHIHU_VIDEO_CATEGORIES,
    ZHIHU_VIDEO_MARKS,
)
from uploader.zhihu_uploader.session import check_zhihu_account, login_zhihu_account
from uploader.zhihu_uploader.verification import verify_zhihu_result
from uploader.zhihu_uploader.video import ZhihuVideo
from sau_commands.arguments import (
    SCHEDULE_FORMAT,
    add_runtime_flags,
    existing_file_path,
    resolve_account_file,
    schedule_value,
)


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
    zhihu_parser = platform_parsers.add_parser("zhihu", help="知乎创作中心文章与视频发布")
    zhihu_actions = zhihu_parser.add_subparsers(dest="action", required=True)
    zhihu_login = zhihu_actions.add_parser("login", help="在可见 Chrome 中登录并保存本地会话")
    zhihu_login.add_argument("--account", required=True, help="本地会话别名，可与知乎展示名不同")
    zhihu_login.add_argument("--timeout", type=int, default=600, help="登录等待秒数")
    zhihu_check = zhihu_actions.add_parser("check", help="检查知乎登录态和页头账号绑定")
    zhihu_check.add_argument("--account", required=True, help="本地会话别名")
    add_runtime_flags(zhihu_check)
    zhihu_check.set_defaults(headless=False)
    zhihu_verify = zhihu_actions.add_parser("verify", help="按已保存的作品 URL 只读核对提交结果")
    zhihu_verify.add_argument("--account", required=True, help="本地会话别名")
    zhihu_verify.add_argument("--result", required=True, type=existing_file_path)
    add_runtime_flags(zhihu_verify)
    zhihu_verify.set_defaults(headless=False)
    zhihu_article = zhihu_actions.add_parser("upload-article", help="发布知乎文章；正文配图由原稿位置决定")
    zhihu_article.add_argument("--account", required=True, help="本地会话别名")
    zhihu_article.add_argument("--title", required=True, help="文章标题，最多 100 字")
    zhihu_article.add_argument("--content-file", required=True, type=existing_file_path, help="UTF-8 HTML/Markdown/TXT，图片路径写在原稿对应段落中")
    zhihu_article.add_argument("--schedule", type=schedule_value,
                               help=f"实验性定时发布，格式 {schedule_help}，北京时间 {ZHIHU_SCHEDULE_MINUTES} 分钟后至 {ZHIHU_SCHEDULE_MAX_HOURS} 小时内")
    zhihu_article.add_argument("--prepare-only", action="store_true", help="填写并检查编辑器后结束，不点击发布")
    zhihu_article.add_argument("--upload-timeout", type=int, default=600, help="每张正文图片上传等待秒数")
    add_runtime_flags(zhihu_article)
    zhihu_article.set_defaults(headless=False)
    zhihu_video = zhihu_actions.add_parser("upload-video", help="上传并发布一个知乎视频")
    zhihu_video.add_argument("--account", required=True, help="本地会话别名")
    zhihu_video.add_argument("--file", required=True, type=existing_file_path, help="视频文件，大于 100KB、最大 20GB、最长 4 小时")
    zhihu_video.add_argument("--title", required=True, help="视频标题，5–50 字")
    zhihu_video.add_argument("--desc", default="", help="可选视频简介，最多 300 字")
    zhihu_video.add_argument("--category", choices=ZHIHU_VIDEO_CATEGORIES,
                             help="所属领域；省略时在终端按编号选择，提交前核对实时菜单")
    zhihu_video.add_argument("--video-mark", choices=ZHIHU_VIDEO_MARKS,
                             help="视频声明；省略时在终端按编号选择")
    zhihu_video.add_argument("--show-options", action="store_true", help="上传素材后列出全部领域和视频标记，保存到结果 JSON 后退出，不发布")
    zhihu_video.add_argument("--originality", choices=ZHIHU_ORIGINALITY, required=True,
                             help="内容为原创或转载")
    zhihu_video.add_argument("--schedule", type=schedule_value,
                             help=f"实验性定时发布，格式 {schedule_help}，北京时间 {ZHIHU_SCHEDULE_MINUTES} 分钟后至 {ZHIHU_SCHEDULE_MAX_HOURS} 小时内")
    zhihu_video.add_argument("--prepare-only", action="store_true", help="上传并填写后结束，不点击发布")
    zhihu_video.add_argument("--upload-timeout", type=int, default=1200, help="视频上传等待秒数")
    add_runtime_flags(zhihu_video)
    zhihu_video.set_defaults(headless=False)


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
    account_file = resolve_account_file("zhihu", args.account)
    if args.action == "login":
        result = await login_zhihu_account(account_file, args.timeout)
    elif args.action == "check":
        valid = await check_zhihu_account(account_file, args.headless)
        print("valid" if valid else "invalid")
        return 0 if valid else 1
    elif args.action == "verify":
        result = await verify_zhihu_result(account_file, args.result, args.headless)
    elif args.action == "upload-article":
        app = ZhihuArticle(
            title=args.title, content_file=args.content_file, account_file=account_file,
            schedule=args.schedule, prepare_only=args.prepare_only,
            upload_timeout=args.upload_timeout, headless=args.headless, debug=args.debug,
        )
        result = await app.main()
    else:
        app = ZhihuVideo(
            title=args.title, file_path=args.file, account_file=account_file,
            description=args.desc, category=args.category,
            topics=[], video_mark=args.video_mark, show_options=args.show_options,
            originality=args.originality, schedule=args.schedule,
            prepare_only=args.prepare_only, upload_timeout=args.upload_timeout,
            headless=args.headless, debug=args.debug,
        )
        result = await app.main()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
