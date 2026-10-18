"""共用文章输入及 Markdown 主题渲染；此模块不登录、不上传，也不处理平台限制。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from html import escape
from pathlib import Path

from utils.article_content import ArticleDocument


ARTICLE_THEMES = {
    "plain": "原生：仅转换正文结构，不添加主题样式",
    "default": "经典：居中标题与强调色",
    "grace": "优雅：圆角引用与柔和装饰",
    "simple": "简洁：清晰留白与轻量装饰",
    "modern": "现代：暖色、圆角与宽松行距",
}
ARTICLE_MARKDOWN_EXTENSIONS = {".md", ".markdown"}
ARTICLE_HTML_EXTENSIONS = {".html", ".htm"}
ARTICLE_RENDERER_DIR = Path(__file__).with_name("article_renderer")


def load_article(content_file: str | Path, theme: str | None = None) -> ArticleDocument:
    """从原稿所在目录解析资源；长正文通过标准输入传递，不进入命令行参数。"""
    path = Path(content_file).expanduser().resolve()
    source = path.read_text(encoding="utf-8-sig")
    suffix = path.suffix.lower()
    metadata = {}
    if suffix in ARTICLE_MARKDOWN_EXTENSIONS:
        theme = theme or "default"
        if theme not in ARTICLE_THEMES:
            raise ValueError(f"主题必须为: {', '.join(ARTICLE_THEMES)}")
        node = shutil.which("node")
        if not node or not (ARTICLE_RENDERER_DIR / "node_modules/baoyu-md").is_dir():
            raise RuntimeError("Markdown 渲染需要 Node.js 22+ 及依赖；请执行 sau article setup")
        completed = subprocess.run(
            [node, str(ARTICLE_RENDERER_DIR / "render.mjs")],
            input=json.dumps({"content": source, "theme": theme}, ensure_ascii=False),
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        if completed.returncode:
            raise RuntimeError(f"Markdown 渲染失败: {completed.stderr.strip()}")
        payload = json.loads(completed.stdout)
        source, metadata = payload["html"], payload["metadata"]
    elif suffix in ARTICLE_HTML_EXTENSIONS | {".txt"}:
        if theme is not None:
            raise ValueError("--theme 仅适用于 Markdown；HTML 和 TXT 不重新套用主题")
        if suffix == ".txt":
            source = "".join(f"<p>{escape(line) if line else '<br>'}</p>" for line in source.splitlines())
    else:
        raise ValueError("正文文件支持 .html/.htm、.md/.markdown，以及兼容的 .txt")
    document = ArticleDocument(source, path.parent)
    document.source_format = "markdown" if suffix in ARTICLE_MARKDOWN_EXTENSIONS else ("text" if suffix == ".txt" else "html")
    document.theme = theme
    document.metadata = metadata
    return document


def render_article_file(content_file: str | Path, output: str | Path,
                        theme: str | None = None, overwrite: bool = False) -> dict:
    """保存可独立预览的 HTML；输出路径改变时仍能找到原稿中的本地图片。"""
    source = Path(content_file).expanduser().resolve()
    target = Path(output).expanduser().resolve()
    if target == source:
        raise ValueError("输出文件不能覆盖输入原稿")
    if target.suffix.lower() not in ARTICLE_HTML_EXTENSIONS:
        raise ValueError("--output 必须为 .html 或 .htm 文件")
    if target.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在；使用 --overwrite 明确覆盖: {target}")
    document = load_article(source, theme)
    title = escape(document.metadata.get("title", source.stem))
    html = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title></head><body>{document.content_html}</body></html>')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return {"output": str(target), "format": document.source_format,
            "theme": document.theme, "image_count": len(document.images)}


def setup_article_renderer() -> None:
    """按锁文件安装本地渲染依赖；发表和渲染过程中不下载程序。"""
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        raise RuntimeError("请先安装 Node.js 22+（含 npm），再执行 sau article setup")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    if int(version.lstrip("v").split(".")[0]) < 22:
        raise RuntimeError(f"文章渲染需要 Node.js 22+，当前为 {version}")
    subprocess.run([npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
                   cwd=ARTICLE_RENDERER_DIR, check=True, timeout=180)
