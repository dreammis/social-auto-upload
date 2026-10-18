"""将原稿转换为雪球实测可接收的结构，图片仍保留原位置和本地路径。"""
from html import escape
from html.parser import HTMLParser

from utils.article_content import ArticleDocument
from utils.article_render import ARTICLE_MARKDOWN_EXTENSIONS, load_article


class XueqiuHTML(HTMLParser):
    """平台会过滤 CSS、统一标题并展开列表；导入前保留可见列表编号。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.lists = []
        self.changes = set()

    def handle_starttag(self, tag, attrs):
        """仅转换已有安全解析器接受的结构；未知格式明确报错，不悄悄丢内容。"""
        attrs = dict(attrs)
        if tag not in {"section", "div", "p", "br", "span", "strong", "b", "em", "i", "a", "img",
                       "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "blockquote", "figure", "figcaption"}:
            raise ValueError(f"雪球原生编辑器尚未验证 <{tag}>，请转换为段落或本地图片后上传")
        if attrs.get("style"):
            self.changes.add("自定义样式使用雪球原生样式")
        if tag.startswith("h") and len(tag) == 2:
            if tag != "h4":
                self.changes.add("各级标题统一为雪球小标题")
            tag = "h4"
        elif tag in {"ul", "ol"}:
            self.changes.add("列表转换为带序号或圆点的段落")
            self.lists.append([tag, int(attrs.get("start", "1"))])
            tag = "div"
        elif tag == "li":
            if not self.lists:
                raise ValueError("列表项必须位于 ul 或 ol 中")
            kind, number = self.lists[-1]
            self.lists[-1][1] += 1
            self.parts.append(f'<div>{number}. ' if kind == "ol" else '<div>• ')
            return
        elif tag == "blockquote":
            self.changes.add("引用保留文字和段落，使用雪球原生段落样式")
            tag = "div"
        elif tag in {"section", "figure", "figcaption"}:
            tag = "div"
        # 原稿已通过 ArticleDocument 校验；不把 CSS/class 导入编辑器，避免样式保留的假象。
        keep = {key: value for key, value in attrs.items()
                if (tag == "a" and key == "href") or (tag == "img" and key in {"src", "alt"})}
        self.parts.append("<" + tag + "".join(f' {key}="{escape(value or "", quote=True)}"'
                                                for key, value in keep.items()) + ">")

    def handle_endtag(self, tag):
        """结束标签与开始标签使用同一转换，避免生成失配的富文本。"""
        if tag in {"ul", "ol"}:
            self.lists.pop()
        if tag in {"section", "figure", "figcaption", "ul", "ol", "li", "blockquote"}:
            tag = "div"
        elif tag.startswith("h") and len(tag) == 2:
            tag = "h4"
        self.parts.append(f"</{tag}>")

    def handle_data(self, value):
        """保留原始文字和空白，特殊字符按 HTML 文本转义。"""
        self.parts.append(escape(value))


def load_xueqiu_article(path):
    """复用仓库的 HTML/Markdown/TXT 输入与相对图片路径，返回待核对的转换后正文。"""
    original = load_article(path, "plain" if path.suffix.lower() in ARTICLE_MARKDOWN_EXTENSIONS else None)
    converted = XueqiuHTML()
    converted.feed(original.content_html)
    converted.close()
    document = ArticleDocument("".join(converted.parts), path.parent)
    document.source_format = original.source_format
    document.normalizations = sorted(converted.changes)
    return document
