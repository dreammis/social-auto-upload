# Language: 中文
import unittest

from uploader.douyin_uploader import main as douyin_main


class DouyinNoStealthTests(unittest.TestCase):
    def test_douyin_uploader_does_not_inject_legacy_stealth_script(self):
        self.assertFalse(
            hasattr(douyin_main, "set_init_script"),
            "douyin_uploader should rely on patchright native stealth instead of utils/stealth.min.js",
        )


if __name__ == "__main__":
    unittest.main()
