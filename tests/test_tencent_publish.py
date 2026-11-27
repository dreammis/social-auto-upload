# Language: 中文
import unittest

from uploader.tencent_uploader.main import format_str_for_short_title


class TencentPublishTests(unittest.TestCase):
    def test_short_title_removes_chinese_comma_and_keeps_minimum_length(self):
        title = format_str_for_short_title("测试,标题")

        self.assertNotIn("，", title)
        self.assertNotIn(",", title)
        self.assertGreaterEqual(len(title), 6)

    def test_short_title_is_trimmed_to_platform_limit(self):
        title = format_str_for_short_title("这是一个超过十五个字符的很长视频标题")

        self.assertGreaterEqual(len(title), 6)
        self.assertLessEqual(len(title), 15)

    def test_empty_short_title_uses_safe_fallback(self):
        self.assertEqual(format_str_for_short_title(""), "精彩视频内容分享")

    def test_short_title_keeps_allowed_special_characters(self):
        title = format_str_for_short_title("《测试》视频")

        self.assertIn("《测试》视频", title)
        self.assertGreaterEqual(len(title), 6)


if __name__ == "__main__":
    unittest.main()
