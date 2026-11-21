"""微信公众号 uploader 的纯逻辑与 CLI 注册验证（不依赖真实浏览器）。"""
import tempfile
import unittest
from pathlib import Path

from sau_cli import build_parser
from uploader.wechat_uploader.article import WechatArticle, build_article_url
from uploader.wechat_uploader.constants import WECHAT_ARTICLE_PATH
from uploader.wechat_uploader.session import wechat_is_login_url, wechat_token_from_url


class WechatUrlTests(unittest.TestCase):
    def test_token_from_valid_home_url(self):
        url = "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&token=123456789&lang=zh_CN"
        self.assertEqual(wechat_token_from_url(url), "123456789")

    def test_token_missing_or_malformed_returns_none(self):
        self.assertIsNone(wechat_token_from_url("https://mp.weixin.qq.com/cgi-bin/home?lang=zh_CN"))
        self.assertIsNone(wechat_token_from_url("https://mp.weixin.qq.com/cgi-bin/home?token=abc"))

    def test_article_url_contains_current_token_and_new_params(self):
        url = build_article_url("123456789")
        self.assertIn(WECHAT_ARTICLE_PATH, url)
        self.assertIn("token=123456789", url)
        self.assertIn("isNew=1", url)
        self.assertIn("type=77", url)
        self.assertNotIn("token=987654321", url)

    def test_login_url_detection(self):
        self.assertTrue(wechat_is_login_url("https://mp.weixin.qq.com/"))
        self.assertTrue(wechat_is_login_url("https://mp.weixin.qq.com/cgi-bin/loginpage"))
        self.assertFalse(wechat_is_login_url(
            "https://mp.weixin.qq.com/cgi-bin/home?token=123456789"))


class WechatArticleValidationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.content = self.root / "article.txt"
        self.content.write_text("正文第一段，用来验证校验逻辑。", encoding="utf-8")

    def _article(self, **kwargs):
        options = dict(title="标题", content_file=self.content, account_file=self.root / "wechat_a.json")
        options.update(kwargs)
        return WechatArticle(**options)

    def test_validate_rejects_overlong_title_and_digest(self):
        with self.assertRaises(ValueError):
            self._article(title="字" * 65).validate_upload_args()
        with self.assertRaises(ValueError):
            self._article(digest="字" * 121).validate_upload_args()

    def test_validate_rejects_invalid_originality(self):
        with self.assertRaises(ValueError):
            self._article(originality="unknown").validate_upload_args()

    def test_validate_rejects_missing_account(self):
        with self.assertRaises(FileNotFoundError):
            self._article().validate_upload_args()


class WechatCliTests(unittest.TestCase):
    def test_wechat_commands_registered(self):
        parser = build_parser()
        args = parser.parse_args(["wechat", "login", "--account", "creator"])
        self.assertEqual(args.platform, "wechat")
        self.assertEqual(args.action, "login")

    def test_upload_article_flags(self):
        parser = build_parser()
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as handle:
            handle.write("正文")
            content_path = handle.name
        self.addCleanup(lambda: Path(content_path).unlink(missing_ok=True))
        args = parser.parse_args([
            "wechat", "upload-article", "--account", "creator",
            "--title", "标题", "--content-file", content_path,
            "--no-broadcast", "--prepare-only", "--originality", "original",
        ])
        self.assertTrue(args.no_broadcast)
        self.assertTrue(args.prepare_only)
        self.assertEqual(args.originality, "original")


if __name__ == "__main__":
    unittest.main()
