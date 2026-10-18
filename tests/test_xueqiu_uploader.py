"""原稿解析与本地浏览器内容核对；线上发表验收另有真实 CLI 结果记录。"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from patchright.async_api import async_playwright

from conf import LOCAL_CHROME_PATH
from sau_cli import build_parser, resolve_account_file
from uploader.xueqiu_uploader.article import XueqiuArticle
from uploader.xueqiu_uploader.content import load_xueqiu_article
from uploader.xueqiu_uploader.verification import check_xueqiu_article_content, query_xueqiu_article, verify_xueqiu_result


class XueqiuInputTests(unittest.TestCase):
    def test_cli_uses_article_file_instead_of_appending_images(self):
        args = build_parser().parse_args([
            'xueqiu', 'upload-article', '--account', 'test', '--title', '标题',
            '--content-file', str(Path(__file__)), '--visibility', '私人',
            '--declaration', '本文包含AI生成内容',
        ])
        self.assertFalse(args.prepare_only)
        self.assertFalse(args.headless)
        self.assertFalse(hasattr(args, 'images'))
        self.assertEqual(resolve_account_file('xueqiu', 'test').name, 'xueqiu_test.json')

    def test_relative_images_stay_between_original_paragraphs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'image.png').write_bytes(b'test')
            source = root / 'article.html'
            source.write_text('<h1 style="color:red">标题</h1><p>前文</p><img src="image.png"><h2>次标题</h2><p>后文</p>', encoding='utf-8')
            document = load_xueqiu_article(source)
            self.assertEqual(document.images, [root / 'image.png'])
            self.assertEqual(document.sequence, ['标题', '前文', '\x00IMG\x00', '次标题', '后文'])
            self.assertEqual(document.tags['h4'], 2)
            self.assertNotIn('style=', document.content_html)
            self.assertIn('自定义样式使用雪球原生样式', document.normalizations)

    def test_markdown_keeps_heading_and_image_position(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'image.png').write_bytes(b'test')
            source = root / 'article.md'
            source.write_text('# 标题\n\n**前文**\n\n![配图](image.png)\n\n## 小标题\n\n后文', encoding='utf-8')
            document = load_xueqiu_article(source)
            self.assertEqual(document.source_format, 'markdown')
            self.assertEqual(document.tags['h4'], 2)
            self.assertEqual(document.tags['strong'], 1)
            self.assertEqual(document.images, [root / 'image.png'])
            self.assertLess(document.sequence.index('前文'), document.sequence.index('\x00IMG\x00'))
            self.assertGreater(document.sequence.index('后文'), document.sequence.index('\x00IMG\x00'))

    def test_numbered_lists_keep_visible_numbers(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'article.html'
            source.write_text('<ol start="3"><li>甲</li><li>乙</li></ol>', encoding='utf-8')
            document = load_xueqiu_article(source)
            self.assertIn('3. 甲', ''.join(document.text))
            self.assertIn('4. 乙', ''.join(document.text))

    def test_unsupported_structure_fails_before_browser(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'article.html'
            source.write_text('<table><tr><td>表格</td></tr></table>', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'table'):
                XueqiuArticle('标题', source, Path(folder) / 'account.json').validate_upload_args()


class XueqiuContentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        (root / 'image.png').write_bytes(b'test')
        source = root / 'article.html'
        source.write_text('<h2>小标题</h2><p><strong>前文</strong><a href="https://xueqiu.com/">链接</a></p><img src="image.png"><p>后文</p>', encoding='utf-8')
        self.document = load_xueqiu_article(source)
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(executable_path=LOCAL_CHROME_PATH or None, channel='chrome', headless=True)
        self.page = await self.browser.new_page()

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()
        self.folder.cleanup()

    async def test_native_bold_and_heading_are_accepted(self):
        await self.page.set_content('<h4>小标题</h4><p><b>前文</b><a href="https://xueqiu.com/">链接</a></p><img><p>后文</p>')
        await check_xueqiu_article_content(self.page.locator('body'), self.document)

    async def test_moving_image_to_end_is_rejected_with_same_image_count(self):
        await self.page.set_content('<h4>小标题</h4><p><b>前文</b><a href="https://xueqiu.com/">链接</a></p><p>后文</p><img>')
        with self.assertRaisesRegex(RuntimeError, '段间图片位置'):
            await check_xueqiu_article_content(self.page.locator('body'), self.document)

    async def test_lost_heading_structure_is_rejected(self):
        await self.page.set_content('<p>小标题</p><p><b>前文</b><a href="https://xueqiu.com/">链接</a></p><img><p>后文</p>')
        with self.assertRaisesRegex(RuntimeError, '结构不一致'):
            await check_xueqiu_article_content(self.page.locator('body'), self.document)

    async def test_changed_link_target_is_rejected(self):
        await self.page.set_content('<h4>小标题</h4><p><b>前文</b><a href="https://example.com/">链接</a></p><img><p>后文</p>')
        with self.assertRaisesRegex(RuntimeError, '链接文字或目标'):
            await check_xueqiu_article_content(self.page.locator('body'), self.document)

    async def test_wrong_image_is_rejected_even_at_correct_position(self):
        await self.page.set_content('<h4>小标题</h4><p><b>前文</b><a href="https://xueqiu.com/">链接</a></p><img src="//xqimg.imedao.com/wrong.png"><p>后文</p>')
        with self.assertRaisesRegex(RuntimeError, '图片内容或顺序'):
            await check_xueqiu_article_content(self.page.locator('body'), self.document,
                                              ['https://xqimg.imedao.com/expected.png'])

    async def test_protocol_relative_uploaded_image_is_accepted(self):
        await self.page.set_content('<h4>小标题</h4><p><b>前文</b><a href="https://xueqiu.com/">链接</a></p><img src="//xqimg.imedao.com/expected.png"><p>后文</p>')
        await check_xueqiu_article_content(self.page.locator('body'), self.document,
                                          ['https://xqimg.imedao.com/expected.png'])

    async def test_verify_rejects_changed_source_before_opening_browser(self):
        root = Path(self.folder.name)
        account = root / 'account.json'
        account.with_suffix('.identity.json').write_text(json.dumps({'uid': '123', 'name': '测试'}), encoding='utf-8')
        result = root / 'result.json'
        result.write_text(json.dumps({'identity': {'uid': '123'}, 'content_id': '789',
                                     'content_file': str(root / 'article.html'),
                                     'manifest': {'structure_sha256': 'original'}}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '原稿与发表时'):
            await verify_xueqiu_result(account, result)

    async def test_old_result_with_content_error_is_not_reported_as_success(self):
        root = Path(self.folder.name)
        account = root / 'account.json'
        account.with_suffix('.identity.json').write_text(json.dumps({'uid': '123', 'name': '测试'}), encoding='utf-8')
        result = root / 'result.json'
        result.write_text(json.dumps({'identity': {'uid': '123'}, 'content_id': '789',
                                     'error': '正文核对失败'}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '保留核对错误'):
            await verify_xueqiu_result(account, result)

    async def test_verify_rejects_wrong_account_before_opening_browser(self):
        root = Path(self.folder.name)
        account = root / 'account.json'
        account.with_suffix('.identity.json').write_text(json.dumps({'uid': '123', 'name': '测试'}), encoding='utf-8')
        result = root / 'result.json'
        result.write_text(json.dumps({'identity': {'uid': '456'}, 'content_id': '789'}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '账号不一致'):
            await verify_xueqiu_result(account, result)


class XueqiuQueryTests(unittest.IsolatedAsyncioTestCase):
    """模拟分页响应，保证原作品查询不会退化为重发或无限翻页。"""

    async def test_original_id_can_be_found_on_later_page(self):
        first = Mock(ok=True, status=200)
        first.url = 'https://mp.xueqiu.com/xq/query/v1/search/long?type=success&page=1&count=10'
        first.json = AsyncMock(return_value={'page': 1, 'maxPage': 2, 'list': [{'id': 111}]})
        first.request.all_headers = AsyncMock(return_value={'x-test': 'test-header'})
        record = {'id': 789, 'user_id': 123, 'title': '原作品', 'is_private': True}
        second = Mock(ok=True, status=200)
        second.json = AsyncMock(return_value={'page': 2, 'maxPage': 2, 'list': [record]})
        page = Mock()
        page.goto = AsyncMock()
        page.get_by_role.return_value.click = AsyncMock()
        page.context.request.get = AsyncMock(return_value=second)
        page.expect_response.return_value = MagicMock()
        page.expect_response.return_value.__aenter__ = AsyncMock()
        page.expect_response.return_value.__aexit__ = AsyncMock(return_value=False)
        future = asyncio.get_running_loop().create_future()
        future.set_result(first)
        page.expect_response.return_value.__aenter__.return_value.value = future
        with patch('uploader.xueqiu_uploader.verification.read_xueqiu_identity', AsyncMock(return_value={'uid': '123'})):
            actual = await query_xueqiu_article(page, {'uid': '123'}, '789', '原作品', '私人')
        self.assertEqual(actual, record)
        self.assertIn('page=2', page.context.request.get.call_args.args[0])
        self.assertEqual(page.context.request.get.call_args.kwargs['headers'], {'x-test': 'test-header'})
        page.context.request.post.assert_not_called()

    async def test_repeated_page_stops_without_republishing(self):
        response = Mock(ok=True, status=200)
        response.url = 'https://mp.xueqiu.com/xq/query/v1/search/long?type=success&page=1&count=10'
        response.json = AsyncMock(return_value={'page': 1, 'maxPage': 3, 'list': []})
        response.request.all_headers = AsyncMock(return_value={})
        page = Mock()
        page.goto = AsyncMock()
        page.get_by_role.return_value.click = AsyncMock()
        page.context.request.get = AsyncMock(return_value=response)
        page.expect_response.return_value = MagicMock()
        page.expect_response.return_value.__aenter__ = AsyncMock()
        page.expect_response.return_value.__aexit__ = AsyncMock(return_value=False)
        future = asyncio.get_running_loop().create_future()
        future.set_result(response)
        page.expect_response.return_value.__aenter__.return_value.value = future
        with patch('uploader.xueqiu_uploader.verification.read_xueqiu_identity', AsyncMock(return_value={'uid': '123'})):
            with self.assertRaisesRegex(RuntimeError, '重复返回同一页'):
                await query_xueqiu_article(page, {'uid': '123'}, '789')
        page.context.request.get.assert_awaited_once()
        page.context.request.post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
