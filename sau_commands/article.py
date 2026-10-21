"""article 的命令参数与执行逻辑。"""
from __future__ import annotations
import json
from pathlib import Path
from utils.article_render import ARTICLE_THEMES, render_article_file, setup_article_renderer
from sau_commands.arguments import SCHEDULE_FORMAT, existing_file_path


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
    article_parser = platform_parsers.add_parser("article", help="本地文章转换与主题预览，不登录或发表")
    article_actions = article_parser.add_subparsers(dest="action", required=True)
    article_actions.add_parser("themes", help="列出内置主题")
    article_actions.add_parser("setup", help="安装锁定版本的 Markdown 渲染依赖（需要 Node.js 22+）")
    article_render = article_actions.add_parser("render", help="将正文文件转换为可预览 HTML")
    article_render.add_argument("--content-file", required=True, type=existing_file_path, help="UTF-8 Markdown、HTML 或 TXT 文件")
    article_render.add_argument("--theme", choices=ARTICLE_THEMES, help="Markdown 主题，默认 default；HTML/TXT 不使用主题")
    article_render.add_argument("--output", required=True, type=Path, help="输出 .html 文件路径")
    article_render.add_argument("--overwrite", action="store_true", help="覆盖已有输出文件，不允许覆盖原稿")


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
    if args.action == "setup":
        setup_article_renderer()
        print("文章渲染依赖已安装")
    elif args.action == "themes":
        for name, description in ARTICLE_THEMES.items():
            print(f"{name}\t{description}")
    else:
        print(json.dumps(render_article_file(args.content_file, args.output, args.theme, args.overwrite), ensure_ascii=False))
    return 0
