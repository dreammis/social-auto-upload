"""验证文件正文、样式边界、图文顺序及只提交一次的实际浏览器行为。"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from patchright.async_api import async_playwright

from conf import BASE_DIR, LOCAL_CHROME_PATH
from uploader.dayu_uploader.article import DayuArticle
from uploader.dayu_uploader.article_content import load_dayu_article
from uploader.dayu_uploader.article_style import render_dayu_compatible_html
from uploader.dayu_uploader.publication import submit_dayu_publication
from uploader.dayu_uploader.verification import check_dayu_article_content, verify_dayu_article


class DayuArticleFileTests(unittest.TestCase):
    def test_html_file_resolves_images_and_preserves_supported_formats(self):
        document = load_dayu_article(BASE_DIR / "examples/dayu_article.html")
        self.assertEqual(document.images, [(BASE_DIR / "videos/demo1.png").resolve()])
        self.assertEqual(document.formats["h1"], 3)
        self.assertEqual(document.formats["strong"], 1)
        self.assertEqual(document.manifest["image_count"], 1)
        self.assertNotEqual(document.manifest["text_sha256"], document.manifest["structure_sha256"])

    def test_large_plain_text_file_is_read_without_command_line_body(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "长文章.txt"
            path.write_text("正文<&>\n" * 2800, encoding="utf-8-sig")
            document = load_dayu_article(path)
            self.assertEqual("".join(document.text).count("正文<&>"), 2800)
            self.assertIn("&lt;&amp;&gt;", "".join(document.parts))
            path.write_text("字" * 20001, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "20000"):
                load_dayu_article(path)

    def test_unsupported_formats_and_malformed_html_are_explicit_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "article.html"
            for html in ('<p><em>正文</em></p>',
                         '<script>alert(1)</script>', '<p>正文', '<p><strong>正文</p></strong>',
                         '<p>正文</p><img src="https://example.com/a.jpg">'):
                with self.subTest(html=html):
                    path.write_text(html, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_dayu_article(path)

    def test_image_order_changes_structure_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "article.html"
            image = (BASE_DIR / "videos/demo1.png").as_posix()
            path.write_text(f'<p>前文</p><img src="{image}"><p>后文</p>', encoding="utf-8")
            first = load_dayu_article(path).manifest
            path.write_text(f'<p>前文</p><p>后文</p><img src="{image}">', encoding="utf-8")
            second = load_dayu_article(path).manifest
            self.assertEqual(first["text_sha256"], second["text_sha256"])
            self.assertNotEqual(first["structure_sha256"], second["structure_sha256"])

    def test_chinese_image_path_is_decoded(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "中文图片.png"
            image.write_bytes((BASE_DIR / "videos/demo1.png").read_bytes())
            path = Path(folder) / "正文.html"
            path.write_text('<p>中文路径图片</p><img src="中文图片.png">', encoding="utf-8")
            self.assertEqual(load_dayu_article(path).images, [image.resolve()])

    def test_source_and_cover_conditions_are_checked_before_browser_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            account = Path(folder) / "account.json"
            account.write_text("{}", encoding="utf-8")
            account.with_suffix(".identity.json").write_text(
                json.dumps({"wmid": "a" * 32, "name": "测试账号"}), encoding="utf-8")
            for source, link, indices, message in (
                ("转载", "", [], "原文链接"),
                ("无需标注", "https://example.com", [], "仅信息来源"),
                ("无需标注", "", [2], "超出"),
                ("无需标注", "", [1, 1], "1 个或 3 个"),
                ("无需标注", "", [1, 1, 1], "不同"),
            ):
                with self.subTest(source=source, indices=indices):
                    app = DayuArticle("图文条件检查标题", BASE_DIR / "examples/dayu_article.html",
                                      account, source, source_url=link, cover_indices=indices)
                    with self.assertRaisesRegex(ValueError, message):
                        app.validate_upload_args()


class DayuArticleBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=True)
        self.identity = {"wmid": "a" * 32, "name": "测试账号"}
        self.record = {"content_id": "123", "origin_id": "b" * 32,
                       "title": "图文发布检查标题", "status": 1, "audit_status": 4}

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()

    async def make_public_context(self):
        context = await self.browser.new_context()
        await context.route("https://mparticle.uc.cn/article.html?**", lambda route: route.fulfill(
            content_type="text/html", body=self.public_html))
        await context.route("https://image.uc.cn/test.png", lambda route: route.fulfill(
            content_type="image/png", path=str(BASE_DIR / "videos/demo1.png")))
        return context

    async def verify_article(self, manifest):
        request = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
            ok=True, json=AsyncMock(return_value={"dataList": {"data": [self.record], "totalPage": 1}}))))
        return await verify_dayu_article(
            SimpleNamespace(request=request), SimpleNamespace(new_context=self.make_public_context),
            self.identity, content_id="123", title=self.record["title"], timeout=5, manifest=manifest, public=True)

    async def test_anonymous_article_checks_text_styles_images_and_order(self):
        document = load_dayu_article(BASE_DIR / "examples/dayu_article.html")
        html = "".join('<img src="https://image.uc.cn/test.png">' if isinstance(p, Path) else p
                       for p in document.parts)
        self.public_html = f'''<meta charset="utf-8"><div class="index-articleContainer-test">
            <h1>{self.record['title']}</h1>
            <div class="article-userInfoName-test">测试账号</div>
            <div class="index-articleSummary-test">{html}</div></div>'''
        result = await self.verify_article(document.manifest)
        self.assertTrue(result["success"])
        self.assertTrue(result["public_article"]["content_checked"])
        self.assertEqual(result["public_article"]["image_count"], 1)
        # 文字和图数相同，但图片被移到末尾，必须拒绝成功。
        image = '<img src="https://image.uc.cn/test.png">'
        self.public_html = self.public_html.replace(image, "").replace('</div></div>', image + '</div></div>')
        with self.assertRaisesRegex(RuntimeError, "顺序"):
            await self.verify_article(document.manifest)

    @patch("uploader.dayu_uploader.publication.read_dayu_schedule", new_callable=AsyncMock, return_value={})
    async def test_submission_saves_ids_and_never_confirms_twice(self, read_schedule):
        page = await self.browser.new_page()
        await page.route("https://mp.dayu.com/dashboard/save-draft", lambda route: route.fulfill(
            json={"data": {"_id": "b" * 32}}))
        await page.route("https://mp.dayu.com/dashboard/submit-article", lambda route: route.fulfill(
            json={"data": {"content_id": "123", "_id": "internal-id"}}))
        html = '''<meta charset="utf-8">
            <button id="preview">发表</button><button id="confirm" hidden>确认发表</button>
            <script>
            document.body.dataset.confirmCount = '0';
            document.querySelector('#preview').onclick = async () => {
                await fetch('/dashboard/save-draft', {method:'POST'});
                document.querySelector('#confirm').hidden = false;
            };
            document.querySelector('#confirm').onclick = () => {
                document.body.dataset.confirmCount = String(Number(document.body.dataset.confirmCount) + 1);
                fetch('/dashboard/submit-article', {method:'POST'});
            };
            </script>'''
        await page.route("https://mp.dayu.com/test-page", lambda route: route.fulfill(
            content_type="text/html", body=html))
        await page.goto("https://mp.dayu.com/test-page")
        with tempfile.TemporaryDirectory() as folder:
            result = {"success": False}
            path = Path(folder) / "result.json"
            await submit_dayu_publication(page, result, path)
            self.assertEqual(await page.locator("body").get_attribute("data-confirm-count"), "1")
            self.assertEqual(result["status"], "submitted")
            self.assertEqual(result["origin_id"], "b" * 32)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["content_id"], "123")
            self.assertTrue(result["success"])
            self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["success"])
            # HTTP 成功但没有最终作品 ID，不能沿用草稿 ID 误报发表成功。
            await page.unroute("https://mp.dayu.com/dashboard/submit-article")
            await page.route("https://mp.dayu.com/dashboard/submit-article", lambda route: route.fulfill(
                json={"error": "submission rejected"}))
            await page.goto("https://mp.dayu.com/test-page")
            rejected = {"success": False}
            with self.assertRaisesRegex(RuntimeError, "未返回 content_id"):
                await submit_dayu_publication(page, rejected, path)
            self.assertFalse(rejected["success"])
            self.assertEqual(rejected["status"], "submission_unknown")
            await page.unroute("https://mp.dayu.com/dashboard/submit-article")
            await page.route("https://mp.dayu.com/dashboard/submit-article", lambda route: route.fulfill(
                json={"data": {"content_id": "123"}}))
            # 定时先核对服务端保存值，再确认一次；列表查询超时只保留原 ID，不得重试确认。
            for scenario in ("scheduled", "wrong_time", "query_timeout"):
                with self.subTest(scenario=scenario):
                    await page.goto("https://mp.dayu.com/test-page")
                    timed = {"success": False, "schedule": "2027-01-01T10:30:00+08:00"}
                    read_schedule.side_effect = RuntimeError("定时时间不一致") if scenario == "wrong_time" else None
                    with patch("uploader.dayu_uploader.publication.wait_dayu_publication", new_callable=AsyncMock) as query:
                        query.return_value = {"status": 5}
                        if scenario == "query_timeout":
                            query.side_effect = TimeoutError("查询超时")
                        if scenario == "scheduled":
                            await submit_dayu_publication(page, timed, path)
                            self.assertEqual(timed["status"], "scheduled")
                            self.assertTrue(timed["schedule_verified"])
                            self.assertEqual(query.call_args.kwargs["schedule"], timed["schedule"])
                        else:
                            with self.assertRaisesRegex((RuntimeError, TimeoutError), "不一致|查询超时"):
                                await submit_dayu_publication(page, timed, path)
                            self.assertFalse(timed["success"])
                        count = "0" if scenario == "wrong_time" else "1"
                        self.assertEqual(await page.locator("body").get_attribute("data-confirm-count"), count)
                        saved = json.loads(path.read_text(encoding="utf8"))
                        self.assertEqual(saved["origin_id"], "b" * 32)
                        if scenario == "query_timeout":
                            self.assertEqual(saved["content_id"], "123")
                            self.assertEqual(saved["status"], "submission_unknown")

    async def test_theme_conversion_preserves_all_theme_content_images_and_colors(self):
        page = await self.browser.new_page()
        await page.route("https://image.uc.cn/test.png", lambda route: route.fulfill(
            content_type="image/png", path=str(BASE_DIR / "videos/demo1.png")))
        for theme in ("default", "grace", "simple", "modern"):
            with self.subTest(theme=theme):
                document = load_dayu_article(BASE_DIR / "examples/article.md", theme)
                image = '<img src="https://image.uc.cn/test.png" data-infoed="1" data-width="735">'
                rendered = await render_dayu_compatible_html(page, document.content_html, [image])
                document.manifest["dayu_style"] = rendered["expectations"]
                await page.set_content('<div id="body">' + rendered["html"] + '</div>')
                body = page.locator("#body")
                await check_dayu_article_content(body, document.manifest)
                self.assertEqual(await body.locator("[style]").count(), 0)
                self.assertEqual(await body.locator("img").get_attribute("data-width"), "735")
                self.assertTrue(rendered["expectations"]["text_colors"])
                # 属性虽在，但被目标页 CSS 覆盖时必须拒绝，不能只检查 font[color] 存在。
                await page.add_style_tag(content="font { color: lime !important; }")
                with self.assertRaisesRegex(RuntimeError, "主题"):
                    await check_dayu_article_content(body, document.manifest)

    async def test_transparent_colors_nested_emphasis_and_large_text(self):
        page = await self.browser.new_page()
        html = '<div style="background:#000;color:rgba(255,255,255,.5)"><p>前文<strong>重点</strong></p>' + '<p>正文</p>' * 5000 + '</div>'
        rendered = await render_dayu_compatible_html(page, html, [])
        self.assertEqual(rendered["expectations"]["text_colors"][0]["color"], "rgb(128, 128, 128)")
        await page.set_content(rendered["html"])
        self.assertEqual(await page.locator("strong").inner_text(), "重点")
        self.assertEqual(await page.locator("p").count(), 5001)
        with self.assertRaisesRegex(Exception, "图片数量"):
            await render_dayu_compatible_html(page, '<img src="local.png">', [])

    @patch("uploader.dayu_uploader.publication.read_dayu_schedule", new_callable=AsyncMock, return_value={})
    async def test_styled_submission_checks_server_preview_before_confirming(self, read_schedule):
        context = await self.browser.new_context()
        page = await context.new_page()
        rendered = await render_dayu_compatible_html(page, '<p style="color:red">主题正文</p>', [])
        from utils.article_content import ArticleDocument
        document = ArticleDocument('<p>主题正文</p>', BASE_DIR)
        document.manifest["dayu_style"] = rendered["expectations"]
        saved_bodies = []
        async def save(route):
            from urllib.parse import parse_qs
            saved_bodies.append(parse_qs(route.request.post_data))
            await route.fulfill(json={"data": {"_id": "b" * 32,
                "previewUrl": "https://mparticle.uc.cn/preview.html?wm_aid=" + "b" * 32}})
        # context 级路由模拟服务器，page 级路由仍由生产代码实际改写本次保存请求。
        await page.context.route("https://mp.dayu.com/dashboard/save-draft", save)
        await page.route("https://mp.dayu.com/dashboard/submit-article", lambda route: route.fulfill(
            json={"data": {"content_id": "123"}}))
        preview_html = '<div class="article-content">' + rendered["html"] + '</div>'
        await page.context.route("https://mparticle.uc.cn/preview.html?**", lambda route: route.fulfill(
            content_type="text/html; charset=utf-8", body=preview_html))
        await page.route("https://mp.dayu.com/test", lambda route: route.fulfill(content_type="text/html", body='''
            <meta charset="utf-8"><button id="save">发表</button><button id="submit" hidden>确认发表</button>
            <script>window.confirms=0;
            save.onclick=async()=>{await fetch('/dashboard/save-draft',{method:'POST',body:new URLSearchParams({content:'被编辑器清理的正文',title:'测试标题',simpleMode:'true'})});submit.hidden=false};
            submit.onclick=()=>{window.confirms++;fetch('/dashboard/submit-article',{method:'POST'})};</script>'''))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            for styled in (True, False):
                await page.goto("https://mp.dayu.com/test")
                result = {"success": False, "manifest": document.manifest, "style_check": {"preview_checked": False}}
                if not styled:
                    preview_html = '<div class="article-content"><p>主题正文</p></div>'
                    with self.assertRaisesRegex(RuntimeError, "主题"):
                        await submit_dayu_publication(page, result, path, rendered["html"])
                    self.assertEqual(await page.evaluate("window.confirms", isolated_context=False), 0)
                    self.assertEqual(result["status"], "preview_ready")
                    self.assertEqual(json.loads(path.read_text(encoding="utf8"))["origin_id"], "b" * 32)
                else:
                    await submit_dayu_publication(page, result, path, rendered["html"])
                    self.assertTrue(result["style_check"]["preview_checked"])
                    self.assertEqual(await page.evaluate("window.confirms", isolated_context=False), 1)
                self.assertEqual(saved_bodies[-1]["content"], [rendered["html"]])
                self.assertEqual(saved_bodies[-1]["simpleMode"], ["true"])
                self.assertEqual(saved_bodies[-1]["title"], ["测试标题"])


if __name__ == "__main__":
    unittest.main()
