"""xueqiu 的命令参数与执行逻辑。"""
from __future__ import annotations
import json
from uploader.xueqiu_uploader.article import XueqiuArticle
from uploader.xueqiu_uploader.constants import XUEQIU_DECLARATIONS, XUEQIU_VISIBILITY
from uploader.xueqiu_uploader.session import check_xueqiu_account, login_xueqiu_account
from uploader.xueqiu_uploader.verification import verify_xueqiu_result
from sau_commands.arguments import (
    SCHEDULE_FORMAT,
    add_runtime_flags,
    existing_file_path,
    resolve_account_file,
)


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
    xueqiu_parser = platform_parsers.add_parser("xueqiu", help="雪球创作者中心图文长文")
    xueqiu_actions = xueqiu_parser.add_subparsers(dest="action", required=True)
    xueqiu_login = xueqiu_actions.add_parser("login", help="在可见 Chrome 中登录并保存本地会话")
    xueqiu_login.add_argument("--account", required=True, help="本地账号别名")
    xueqiu_login.add_argument("--expected-name", help="期望的雪球昵称")
    xueqiu_login.add_argument("--timeout", type=int, default=600, help="登录等待秒数")
    xueqiu_check = xueqiu_actions.add_parser("check", help="检查登录状态及绑定用户 ID")
    xueqiu_check.add_argument("--account", required=True)
    add_runtime_flags(xueqiu_check)
    xueqiu_check.set_defaults(headless=False)
    xueqiu_verify = xueqiu_actions.add_parser("verify", help="根据结果文件查询原作品，不重复发表")
    xueqiu_verify.add_argument("--account", required=True)
    xueqiu_verify.add_argument("--result", required=True, type=existing_file_path)
    add_runtime_flags(xueqiu_verify)
    xueqiu_verify.set_defaults(headless=False)
    xueqiu_article = xueqiu_actions.add_parser("upload-article", help="HTML/Markdown/TXT 长文及原位置配图")
    xueqiu_article.add_argument("--account", required=True)
    xueqiu_article.add_argument("--title", required=True, help="非空单行标题")
    xueqiu_article.add_argument("--content-file", required=True, type=existing_file_path, help="UTF-8 HTML/Markdown/TXT；图片由原稿位置决定")
    xueqiu_article.add_argument("--cover", type=existing_file_path, help="独立封面；采用平台默认裁剪区域")
    xueqiu_article.add_argument("--visibility", choices=XUEQIU_VISIBILITY, default="公开", help="分享范围")
    xueqiu_article.add_argument("--declaration", choices=XUEQIU_DECLARATIONS, required=True, help="按实际创作方式选择")
    xueqiu_article.add_argument("--prepare-only", action="store_true", help="检查预览后结束；雪球会自动保存远端草稿")
    add_runtime_flags(xueqiu_article)
    # 本机真实验收使用可见 Chrome；headless 访问曾触发下载/访问拦截，用户可显式选择。
    xueqiu_article.set_defaults(headless=False)


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
    account_file = resolve_account_file("xueqiu", args.account)
    if args.action == "login":
        result = await login_xueqiu_account(account_file, args.expected_name, args.timeout)
    elif args.action == "check":
        valid = await check_xueqiu_account(account_file, args.headless)
        print("valid" if valid else "invalid")
        return 0 if valid else 1
    elif args.action == "verify":
        result = await verify_xueqiu_result(account_file, args.result, args.headless)
    else:
        app = XueqiuArticle(
            title=args.title, content_file=args.content_file, account_file=account_file,
            visibility=args.visibility, declaration=args.declaration,
            prepare_only=args.prepare_only, headless=args.headless, debug=args.debug,
            cover=args.cover,
        )
        result = await app.main()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
