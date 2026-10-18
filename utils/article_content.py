"""平台无关的文章正文：安全内联 HTML、正文顺序和相对于原稿的图片路径。"""
from __future__ import annotations

import re
from collections import Counter
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import tinycss2


ARTICLE_TAGS = {
    "section", "div", "p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "span",
    "strong", "b", "em", "i", "u", "s", "del", "blockquote", "ol", "ul", "li",
    "hr", "img", "a", "pre", "code", "table", "thead", "tbody", "tfoot", "tr",
    "th", "td", "figure", "figcaption", "sup", "sub",
}
ARTICLE_FORMAT_TAGS = ARTICLE_TAGS - {"section", "div", "p", "br", "span", "img", "b", "i"}


def validate_article_style(style: str) -> None:
    """保留排版声明，拒绝带外部资源或可执行内容的 CSS；不静默删除输入样式。"""
    def inspect(tokens):
        for token in tokens:
            if token.type in {"error", "url", "at-keyword"}:
                raise ValueError("正文 CSS 不能包含语法错误、外部资源或 @ 规则")
            if token.type == "function":
                if token.lower_name in {"url", "expression", "var"}:
                    raise ValueError(f"正文 CSS 不支持 {token.name}()，请提供已内联的具体样式值")
                inspect(token.arguments)
            if hasattr(token, "content"):
                inspect(token.content)
    for declaration in tinycss2.parse_declaration_list(style, skip_comments=True, skip_whitespace=True):
        if declaration.type != "declaration" or declaration.lower_name.startswith(("--", "-moz-binding")):
            raise ValueError("正文 style 必须为具体的 CSS 声明，不支持变量或规则块")
        if declaration.lower_name in {"behavior", "-ms-behavior"}:
            raise ValueError("正文 CSS 不能包含可执行行为")
        inspect(declaration.value)


class ArticleDocument(HTMLParser):
    """解析后保留样式及文字/图片位置；平台可对这份结果增加自己的限制。"""

    VOID_TAGS = {"br", "hr", "img"}

    def __init__(self, html: str, base_dir: Path):
        super().__init__(convert_charrefs=True)
        self.base_dir = base_dir.resolve()
        self.parts: list[str | Path] = []
        self.text: list[str] = []
        self.sequence: list[str] = []
        self.images: list[Path] = []
        self.image_attributes: list[dict] = []
        self.formats: Counter = Counter()
        self.tags: Counter = Counter()
        self.attributes: dict[str, set[str]] = {}
        self.stack: list[str] = []
        self.in_head = False
        self.body_style = ""
        self.html_style = ""
        self.source_format = "html"
        self.theme: str | None = None
        self.metadata: dict = {}
        self.feed(html)
        self.close()
        if self.stack:
            raise ValueError(f"正文 HTML 标签未闭合: {self.stack[-1]}")
        if not "".join(self.text).strip():
            raise ValueError("图文正文不能为空，请提供正文文字")
        image_index = 0
        content = []
        for part in self.parts:
            content.append(self.image_html(image_index) if isinstance(part, Path) else part)
            if isinstance(part, Path):
                image_index += 1
        self.content_html = "".join(content)
        normalize = lambda value: re.sub(r"[\s\u200b\ufeff]+", "", value)
        self.manifest = {
            "text_sha256": sha256(normalize("".join(self.text)).encode()).hexdigest(),
            "structure_sha256": sha256(normalize("".join(self.sequence)).encode()).hexdigest(),
            "image_count": len(self.images), "formats": dict(self.formats),
        }

    def image_html(self, index: int) -> str:
        """重建图片时保留排版属性，以绝对路径保持输出移动后的资源定位。"""
        attrs = {**self.image_attributes[index], "src": quote(self.images[index].as_posix(), safe="/:")}
        return "<img" + "".join(f' {key}="{escape(value or "", quote=True)}"' for key, value in attrs.items()) + ">"

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "head":
            self.in_head = True
            return
        if tag in {"script", "iframe", "object", "embed", "link", "style"}:
            raise ValueError(f"正文不支持 <{tag}>；样式请使用元素内联 style，不引用外部资源")
        if self.in_head:
            return
        if tag == "html":
            if set(attributes) - {"lang", "style"}:
                raise ValueError("<html> 仅支持 lang 和 style 属性")
            self.html_style = attributes.get("style") or ""
            if self.html_style.strip():
                validate_article_style(self.html_style)
                self.parts.append(f'<section style="{escape(self.html_style, quote=True)}">')
            return
        if tag == "body":
            if set(attributes) - {"style", "class", "id"}:
                raise ValueError("<body> 仅支持 style、class、id 属性")
            self.body_style = attributes.get("style") or ""
            if self.body_style.strip():
                validate_article_style(self.body_style)
                self.parts.append(f'<section style="{escape(self.body_style, quote=True)}">')
            return
        if tag not in ARTICLE_TAGS:
            raise ValueError(f"正文暂不支持 <{tag}>")
        self.attributes.setdefault(tag, set()).update(attributes)
        allowed = {"style", "class", "id", "title"}
        if tag == "img":
            allowed |= {"src", "alt", "width", "height"}
        if tag == "a":
            allowed |= {"href"}
        if tag in {"th", "td"}:
            allowed |= {"colspan", "rowspan", "align"}
        if tag == "ol":
            allowed |= {"start"}
        if set(attributes) - allowed - {key for key in attributes if key.startswith("data-")}:
            raise ValueError(f"<{tag}> 不支持属性 {', '.join(sorted(set(attributes) - allowed))}")
        if "style" in attributes:
            validate_article_style(attributes["style"] or "")
        if tag == "a" and "href" in attributes:
            href = attributes["href"] or ""
            if not href.startswith("#") and urlsplit(href).scheme not in {"http", "https", "mailto"}:
                raise ValueError("正文链接仅支持 http/https、mailto 或文内锚点")
        if tag == "img":
            source = unquote(attributes.pop("src", "") or "")
            if (not source or source.startswith("//") or
                    (not Path(source).is_absolute() and re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", source))):
                raise ValueError("正文图片 src 必须为本地相对路径或绝对路径，不支持网络地址、file URL 和 data URL")
            image = (self.base_dir / Path(source).expanduser()).resolve()
            if not image.is_file():
                raise FileNotFoundError(f"图片不存在: {image}")
            self.parts.append(image)
            self.images.append(image)
            self.image_attributes.append(attributes)
            self.sequence.append("\x00IMG\x00")
            return
        normalized = {"b": "strong", "i": "em"}.get(tag, tag)
        self.tags[normalized] += 1
        self.parts.append("<" + normalized + "".join(
            f' {key}="{escape(value or "", quote=True)}"' for key, value in attributes.items()) + ">")
        if tag == "hr":
            self.sequence.append("\x00HR\x00")
        if normalized in ARTICLE_FORMAT_TAGS:
            self.formats[normalized] += 1
        if tag not in self.VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_TAGS and tag not in {"meta", "link"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
            return
        if self.in_head:
            return
        if tag == "html":
            if self.html_style.strip():
                self.parts.append("</section>")
            return
        if tag == "body":
            if self.body_style.strip():
                self.parts.append("</section>")
            return
        if not self.stack or self.stack.pop() != tag:
            raise ValueError(f"正文 HTML 标签未正确闭合: </{tag}>")
        normalized = {"b": "strong", "i": "em"}.get(tag, tag)
        self.parts.append(f'</{normalized}>')

    def handle_data(self, data):
        if not self.in_head:
            self.parts.append(escape(data))
            self.text.append(data)
            self.sequence.append(data)
