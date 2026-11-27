# Language: 中文
import threading
import unittest

from utils import verify_codes


class VerifyCodesTests(unittest.TestCase):
    def setUp(self):
        verify_codes.reset()

    def tearDown(self):
        verify_codes.reset()

    def test_creates_pending_request_with_context(self):
        verify_codes.set_context(title="测试视频", platform="抖音", file_name="demo.mp4")

        request = verify_codes.create_request(
            platform="抖音",
            account_file="/tmp/cookies/account.json",
        )
        pending = verify_codes.latest_pending()

        self.assertTrue(verify_codes.is_enabled())
        self.assertEqual(pending["id"], request["id"])
        self.assertEqual(pending["title"], "测试视频")
        self.assertEqual(pending["platform"], "抖音")
        self.assertEqual(pending["file_name"], "demo.mp4")
        self.assertEqual(pending["status"], "pending")
        self.assertNotIn("code", pending)

    def test_reuses_active_request_for_same_account(self):
        verify_codes.set_context(title="测试视频", platform="抖音")

        first = verify_codes.create_request(account_file="/tmp/account.json")
        second = verify_codes.create_request(account_file="/tmp/account.json")

        self.assertEqual(first["id"], second["id"])

    def test_submit_and_consume_code_once(self):
        verify_codes.set_context(title="测试视频", platform="抖音")
        request = verify_codes.create_request(account_file="/tmp/account.json")

        ok, message = verify_codes.submit_code(request["id"], "123456")

        self.assertTrue(ok)
        self.assertEqual(message, "")
        self.assertEqual(verify_codes.poll_code(request["id"]), "123456")
        self.assertEqual(verify_codes.poll_code(request["id"]), "")
        self.assertIsNone(verify_codes.latest_pending())

    def test_failed_verification_reopens_request(self):
        verify_codes.set_context(title="测试视频", platform="抖音")
        request = verify_codes.create_request(account_file="/tmp/account.json")
        verify_codes.submit_code(request["id"], "123456")
        verify_codes.poll_code(request["id"])

        verify_codes.report_result(request["id"], False, "验证码错误或已过期")
        pending = verify_codes.latest_pending()

        self.assertEqual(pending["id"], request["id"])
        self.assertEqual(pending["status"], "pending")
        self.assertEqual(pending["error"], "验证码错误或已过期")
        self.assertTrue(pending["resend_requested"])

    def test_resend_is_consumed_by_worker(self):
        verify_codes.set_context(title="测试视频", platform="抖音")
        request = verify_codes.create_request(account_file="/tmp/account.json")

        ok, message = verify_codes.request_resend(request["id"])

        self.assertTrue(ok)
        self.assertEqual(message, "")
        self.assertTrue(verify_codes.consume_resend(request["id"]))
        self.assertFalse(verify_codes.consume_resend(request["id"]))

    def test_clear_context_cancels_outstanding_request(self):
        verify_codes.set_context(title="测试视频", platform="抖音")
        request = verify_codes.create_request(account_file="/tmp/account.json")

        verify_codes.clear_context()

        self.assertFalse(verify_codes.is_enabled())
        self.assertIsNone(verify_codes.latest_pending())
        self.assertEqual(verify_codes._requests[request["id"]]["status"], "cancelled")

    def test_context_is_thread_local(self):
        verify_codes.set_context(title="主线程", platform="抖音")
        result = {}

        def worker():
            result["enabled"] = verify_codes.is_enabled()
            verify_codes.set_context(title="工作线程", platform="抖音")
            result["request"] = verify_codes.create_request(account_file="/tmp/worker.json")
            verify_codes.clear_context()

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        self.assertFalse(result["enabled"])
        self.assertEqual(result["request"]["title"], "工作线程")
        self.assertIsNone(verify_codes.latest_pending())


if __name__ == "__main__":
    unittest.main()
