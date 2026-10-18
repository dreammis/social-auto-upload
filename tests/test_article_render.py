"""验证文章渲染的内容完整性、资源路径、平台边界及 CLI 参数。"""
import tempfile
import unittest
from pathlib import Path

from sau_cli import build_parser
from conf import BASE_DIR
from uploader.dayu_uploader.article_content import load_dayu_article
from utils.article_render import ARTICLE_THEMES, load_article, render_article_file


class ArticleRenderTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / "正文.md"

    def test_all_themes_preserve_code_tables_headings_and_inline_styles(self):
        self.source.write_text('# 小节标题\n\n正文**加粗重点**与*斜体*。\n\n'
                               '```python\nprint("你好")\n```\n\n'
                               '|项目|数量|\n|---|---|\n|甲|1|\n', encoding="utf-8-sig")
        themed = []
        for theme in ARTICLE_THEMES:
            with self.subTest(theme=theme):
                doc = load_article(self.source, theme)
                text = "".join(doc.text)
                for expected in ('小节标题', '加粗重点', '斜体', 'print("你好")', '项目', '甲'):
                    self.assertIn(expected, text)
                for tag in ("h1", "strong", "em", "pre", "code", "table"):
                    self.assertEqual(doc.formats[tag], 1)
                if theme == "plain":
                    self.assertNotIn('style=', doc.content_html)
                else:
                    self.assertIn('style=', doc.content_html)
                    self.assertNotIn('<svg', doc.content_html)
                    themed.append(doc.content_html)
        self.assertEqual(len(set(themed)), 4)

    def test_moved_output_preserves_chinese_image_paths_order_and_styles(self):
        image = self.root / "图片 #1.png"
        image.write_bytes(b"local preview resource")
        self.source.write_text('前文\n\n![示例图片](<图片 #1.png>)\n\n后文', encoding="utf-8")
        output = self.root / "preview" / "result.html"
        render_article_file(self.source, output, "grace")
        original = load_article(self.source, "grace")
        restored = load_article(output)
        self.assertEqual(restored.images, [image.resolve()])
        self.assertEqual(restored.manifest, original.manifest)
        self.assertIn('alt="示例图片"', restored.content_html)
        self.assertIn('style=', restored.content_html)

    def test_html_keeps_inline_style_and_does_not_need_theme(self):
        source = self.root / "inline.html"
        source.write_text('<h2 style="color:red;border-left:3px solid blue">标题</h2>'
                          '<p style="line-height:1.8">正文<strong>重点</strong></p>', encoding="utf-8")
        doc = load_article(source)
        self.assertIn('color:red;border-left:3px solid blue', doc.content_html)
        with self.assertRaisesRegex(ValueError, "仅适用于 Markdown"):
            load_article(source, "grace")
        self.assertEqual(load_dayu_article(source).content_html, doc.content_html)

    def test_large_markdown_uses_file_and_platform_checks_its_own_limit(self):
        self.source.write_text('正文段落。\n\n' * 6000, encoding="utf-8")
        doc = load_article(self.source, "plain")
        self.assertEqual("".join(doc.text).count("正文段落。"), 6000)
        with self.assertRaisesRegex(ValueError, "20000"):
            load_dayu_article(self.source)

    def test_output_never_overwrites_source_or_existing_file_implicitly(self):
        self.source.write_text('正文', encoding="utf-8")
        target = self.root / "result.html"
        target.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            render_article_file(self.source, target)
        self.assertEqual(target.read_text(), "existing")
        render_article_file(self.source, target, overwrite=True)
        with self.assertRaisesRegex(ValueError, "输入原稿"):
            render_article_file(target, target, overwrite=True)

    def test_unsafe_or_unimplemented_formats_are_explicit_errors(self):
        for content in ('<script>alert(1)</script>正文', '<p onclick="alert(1)">正文</p>',
                        '<p style="background:url(https://example.com/a.png)">正文</p>',
                        '<p style="color:var(--color)">正文</p>',
                        '```mermaid\ngraph TD;A-->B;\n```',
                        '```plantuml\nAlice -> Bob\n```',
                        '![外部图片](https://example.com/a.png)'):
            with self.subTest(content=content):
                self.source.write_text(content, encoding="utf-8")
                with self.assertRaises((ValueError, RuntimeError)):
                    load_article(self.source, "plain")

    def test_dayu_markdown_renders_selected_theme_without_plain_downgrade(self):
        self.source.write_text('# 标题\n\n## 次标题\n\n正文**重点**\n\n> 引用\n\n- 第一项\n- 第二项\n\n---\n', encoding="utf-8")
        doc = load_dayu_article(self.source)
        self.assertEqual(doc.theme, "default")
        self.assertIn('style=', doc.content_html)
        self.assertEqual(doc.formats["h2"], 1)
        self.assertEqual(doc.formats["li"], 2)
        self.assertEqual(load_dayu_article(self.source, "grace").content_html,
                         load_article(self.source, "grace").content_html)
        self.assertNotIn('style=', load_dayu_article(self.source, "plain").content_html)
        self.source.write_text('正文*斜体*', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "em"):
            load_dayu_article(self.source)

    def test_cli_exposes_shared_themes_and_platform_choices(self):
        self.source.write_text('正文', encoding="utf-8")
        parser = build_parser()
        args = parser.parse_args(['article', 'render', '--content-file', str(self.source),
                                  '--theme', 'modern', '--output', str(self.root / 'out.html')])
        self.assertEqual(args.theme, 'modern')
        args = parser.parse_args(['dayu', 'upload-article', '--account', 'creator', '--title', '测试文章标题',
                                  '--content-file', str(self.source), '--source', 'AI生成', '--theme', 'modern'])
        self.assertEqual(args.theme, 'modern')

    def test_dayu_accepts_exported_theme_html_with_the_same_text_and_image_order(self):
        output = self.root / 'preview' / 'modern.html'
        render_article_file(BASE_DIR / 'examples/article.md', output, 'modern')
        direct = load_dayu_article(BASE_DIR / 'examples/article.md', 'modern')
        exported = load_dayu_article(output)
        self.assertEqual(exported.content_html, direct.content_html)
        self.assertEqual(exported.images, direct.images)
        self.assertEqual(exported.manifest, direct.manifest)
        self.assertIn('background: #D97757', exported.content_html)

    def test_theme_lists_do_not_duplicate_markers_when_platform_removes_css(self):
        self.source.write_text('3. 第三项\n4. 第四项\n\n- 无序甲\n- 无序乙\n', encoding='utf8')
        plain = load_article(self.source, 'plain')
        for theme in ('default', 'grace', 'simple', 'modern'):
            with self.subTest(theme=theme):
                document = load_article(self.source, theme)
                self.assertEqual(document.manifest['text_sha256'], plain.manifest['text_sha256'])
                self.assertEqual(document.manifest['formats'], plain.manifest['formats'])
                self.assertIn('start="3"', document.content_html)
                self.assertIn('display: list-item', document.content_html)


if __name__ == "__main__":
    unittest.main()
