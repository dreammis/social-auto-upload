"""大鱼号正文的能力与素材限制；文件读取和渲染由共用文章模块负责。"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from utils.article_content import ArticleDocument
from utils.article_render import load_article


DAYU_ARTICLE_TAGS = {"section", "div", "span", "figure", "p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "blockquote", "ol", "ul", "li", "hr"}


def load_dayu_article(content_file: str | Path, theme: str | None = None) -> ArticleDocument:
    """共用主题渲染，保留原稿样式供大鱼号兼容转换，并在上传前校验平台能力。"""
    path = Path(content_file).expanduser().resolve()
    if path.suffix.lower() not in {".md", ".markdown"} and theme is not None:
        raise ValueError("--theme 仅适用于 Markdown")
    document = load_article(path, theme)
    unsupported = set(document.tags) - DAYU_ARTICLE_TAGS
    if unsupported:
        raise ValueError(f"大鱼号当前未支持这些格式: {', '.join(sorted(unsupported))}；请调整原稿")
    # figure 在导入时适配为 div；图片数量与位置仍严格校验，布局容器不计作必须保留的语义格式。
    document.manifest["formats"].pop("figure", None)
    text = "".join(document.text).strip()
    if len(text) > 20000:
        raise ValueError(f"大鱼号正文最多 20000 字，当前 {len(text)} 字")
    for image in set(document.images):
        validate_dayu_article_image(image)
    return document


def validate_dayu_article_image(image: str | Path) -> Path:
    """图文正文和封面共用页面观察到的单张 5M 限制，并拒绝无法解码的图片。"""
    path = Path(image).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"图片不存在: {path}")
    size = path.stat().st_size
    if not size:
        raise ValueError(f"图片文件为空: {path}")
    if size > 5 * 1024 ** 2:
        raise ValueError(f"图片不能超过 5 MB: {path}")
    # Windows 的 imread 不能可靠打开中文路径；由 pathlib 读字节后解码，不改写用户文件。
    if cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_UNCHANGED) is None:
        raise ValueError(f"图片无法解码: {path}")
    return path
