"""wechat 的命令参数与执行逻辑（微信公众号图文发布）。"""
from __future__ import annotations
import json
from uploader.wechat_uploader.article import WechatArticle
from uploader.wechat_uploader.constants import WECHAT_ORIGINALITY
from uploader.wechat_uploader.session import check_wechat_account, login_wechat_account
from sau_commands.arguments import (
    add_runtime_flags, existing_file_path, resolve_account_file,
)


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    wechat_parser = platform_parsers.add_parser("wechat", help="微信公众平台图文文章发布")
    wechat_actions = wechat_parser.add_subparsers(dest="action", required=True)

    wechat_login = wechat_actions.add_parser("login", help="在可见 Chrome 中扫码登录并保存本地会话")
    wechat_login.add_argument("--account", required=True, help="本地会话别名，可与公众号昵称不同")
    wechat_login.add_argument("--timeout", type=int, default=600, help="扫码登录等待秒数")

    wechat_check = wechat_actions.add_parser("check", help="检查微信公众号登录态与账号绑定")
    wechat_check.add_argument("--account", required=True, help="本地会话别名")
    add_runtime_flags(wechat_check)
    wechat_check.set_defaults(headless=True)

    wechat_article = wechat_actions.add_parser("upload-article", help="发布微信公众号图文；正文图片保留原稿位置")
    wechat_article.add_argument("--account", required=True, help="本地会话别名")
    wechat_article.add_argument("--title", required=True, help="文章标题，最多 64 字")
    wechat_article.add_argument("--content-file", required=True, type=existing_file_path,
                                help="UTF-8 HTML/Markdown/TXT，图片路径写在原稿对应段落中")
    wechat_article.add_argument("--digest", help="可选摘要，最多 120 字")
    wechat_article.add_argument("--author", help="可选作者名，最多 8 字")
    wechat_article.add_argument("--cover", type=existing_file_path, help="可选独立封面图片")
    wechat_article.add_argument("--originality", choices=WECHAT_ORIGINALITY, default="none",
                                help="创作来源声明：none 不声明，original 声明原创")
    wechat_article.add_argument("--no-broadcast", action="store_true",
                                help="发表但不群发通知；默认开启群发")
    wechat_article.add_argument("--prepare-only", action="store_true", help="填写并检查后结束，不点击发表")
    wechat_article.add_argument("--qr-timeout", type=int, default=600,
                                help="等待管理员扫码验证的秒数")
    add_runtime_flags(wechat_article)
    # 公众号填表与扫码验证需要可见窗口，默认有头；可显式 --headless 关闭。
    wechat_article.set_defaults(headless=False)


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
    account_file = resolve_account_file("wechat", args.account)
    if args.action == "login":
        result = await login_wechat_account(account_file, args.timeout)
    elif args.action == "check":
        valid = await check_wechat_account(account_file, args.headless)
        print("valid" if valid else "invalid")
        return 0 if valid else 1
    else:
        app = WechatArticle(
            title=args.title, content_file=args.content_file, account_file=account_file,
            digest=args.digest, author=args.author, cover=args.cover,
            originality=args.originality, broadcast=not args.no_broadcast,
            prepare_only=args.prepare_only, headless=args.headless, debug=args.debug,
            qr_timeout=args.qr_timeout,
        )
        result = await app.main()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
