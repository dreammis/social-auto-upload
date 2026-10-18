"""以真实浏览器 DOM 和受控作品响应验证大鱼号的关键成功/失败边界。"""
import copy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from patchright.async_api import async_playwright

from conf import BASE_DIR, LOCAL_CHROME_PATH
from uploader.dayu_uploader.main import DayuVideo, wait_dayu_processing
from uploader.dayu_uploader.verification import verify_dayu_article, verify_dayu_video


class DayuBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=True,
        )
        self.page = await self.browser.new_page()
        self.identity = {"wmid": "a" * 32, "name": "测试账号"}
        self.record = {
            "content_id": "123456789012345678", "origin_id": "b" * 32,
            "title": "大鱼号上传测试", "status": 1, "audit_status": 4,
            "_app_extra": {"audit_remark": "内容质量不符合平台要求，可能无法获得平台推荐。"},
            "ucUrl": "https://mparticle.uc.cn/video.html?wm_id=" + "a" * 32 + "&wm_aid=" + "b" * 32,
        }

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()

    async def test_processing_waits_past_100_percent_and_processing(self):
        await self.page.set_content('''
            <div class="article-write_video-container">文件大小不超过10G</div>
            <script>
            const box = document.querySelector('div');
            setTimeout(() => box.textContent = 'demo.mp4 正在上传中：100.0%', 30);
            setTimeout(() => box.textContent = '视频上传成功，处理中... demo.mp4', 80);
            setTimeout(() => box.innerHTML = '<div class="article-write_video-container-result-desc">'
                + '<p>视频上传成功，处理完成</p><p><span>demo.mp4</span></p></div>', 550);
            </script>
        ''')
        await wait_dayu_processing(self.page, "demo.mp4", timeout=3)
        self.assertIn("处理完成", await self.page.locator("body").inner_text())

    async def test_processing_error_overrides_success_text(self):
        await self.page.set_content('''<div class="article-write_video-container">
            <p>视频上传成功，处理完成</p><p>视频时长小于5秒，请重新上传</p></div>''')
        with self.assertRaisesRegex(RuntimeError, "小于5秒"):
            await wait_dayu_processing(self.page, "demo.mp4", timeout=1)

    async def test_processing_has_a_deadline(self):
        await self.page.set_content('<div class="article-write_video-container">正在上传中：100.0%</div>')
        with self.assertRaises(TimeoutError):
            await wait_dayu_processing(self.page, "demo.mp4", timeout=.05)

    async def make_public_context(self):
        """公开页在本地路由中播放真实 demo，不借用任何登录状态或外网媒体。"""
        context = await self.browser.new_context()
        html = '''<meta charset="utf-8"><div class="pc-videoContent-test">大鱼号上传测试</div>
            <div class="pc-userInfoContainer-test"><span>测试账号</span></div>
            <video src="https://mparticle.uc.cn/test.mp4" preload="auto"></video>'''
        await context.route("https://mparticle.uc.cn/video.html?**",
                            lambda route: route.fulfill(content_type="text/html", body=html))
        await context.route("https://mparticle.uc.cn/test.mp4",
                            lambda route: route.fulfill(content_type="video/mp4", path=str(BASE_DIR / "videos/demo.mp4")))
        return context

    async def test_verification_matches_id_across_pages_and_plays_without_login(self):
        decoy = copy.deepcopy(self.record)
        decoy.update(content_id="wrong-id", origin_id="c" * 32)
        first = {"dataList": {"data": [decoy], "totalPage": 2}}
        second = {"dataList": {"data": [self.record], "totalPage": 2}}
        request = SimpleNamespace(get=AsyncMock(side_effect=[
            SimpleNamespace(ok=True, json=AsyncMock(return_value=first)),
            SimpleNamespace(ok=True, json=AsyncMock(return_value=second)),
        ]))
        result = await verify_dayu_video(
            SimpleNamespace(request=request), SimpleNamespace(new_context=self.make_public_context),
            self.identity, content_id=self.record["content_id"], origin_id=self.record["origin_id"],
            title=self.record["title"], timeout=5, public=True,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "published")
        self.assertEqual(result["audit_status"], 4)
        self.assertIn("可能无法获得平台推荐", result["audit_remark"])
        self.assertGreater(result["public_playback"]["current_time"], .1)
        self.assertEqual([call.kwargs["params"]["page"] for call in request.get.await_args_list], [1, 2])

    async def test_http_200_without_business_data_is_not_success(self):
        request = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
            ok=True, json=AsyncMock(return_value={"error": "login required"}),
        )))
        with self.assertRaisesRegex(RuntimeError, "dataList.data"):
            await verify_dayu_video(SimpleNamespace(request=request), self.browser,
                                    self.identity, content_id=self.record["content_id"], timeout=1, public=True)

    async def test_explicit_public_check_does_not_accept_draft(self):
        pending = dict(self.record, status=0)
        request = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
            ok=True, json=AsyncMock(return_value={"dataList": {"data": [pending], "totalPage": 1}}),
        )))
        with self.assertRaisesRegex(TimeoutError, "勿重新上传"):
            await verify_dayu_video(SimpleNamespace(request=request), self.browser,
                                    self.identity, content_id=self.record["content_id"], timeout=.05, public=True)

    async def test_default_verification_succeeds_during_review_without_public_browser(self):
        # 审核中已经提交成功；公开 URL 即使缺失，也不应触发公开浏览器或等待审核。
        pending = dict(self.record, status=3, audit_status=0, ucUrl="")
        for verify in (verify_dayu_video, verify_dayu_article):
            with self.subTest(verify=verify.__name__):
                request = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
                    ok=True, json=AsyncMock(return_value={"dataList": {"data": [pending], "totalPage": 1}}))))
                browser = SimpleNamespace(new_context=AsyncMock(side_effect=AssertionError("不应访问公开页")))
                result = await verify(SimpleNamespace(request=request), browser, self.identity,
                                      content_id=self.record["content_id"], timeout=1)
                self.assertTrue(result["success"])
                self.assertEqual(result["status"], "submitted")
                self.assertEqual(result["platform_status"], 3)
                self.assertEqual(request.get.await_count, 1)
                browser.new_context.assert_not_awaited()

    async def test_default_verification_does_not_treat_draft_as_submission(self):
        draft = dict(self.record, status=0)
        request = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
            ok=True, json=AsyncMock(return_value={"dataList": {"data": [draft], "totalPage": 1}}))))
        with self.assertRaisesRegex(TimeoutError, "提交发表确认"):
            await verify_dayu_article(SimpleNamespace(request=request), self.browser, self.identity,
                                      content_id=self.record["content_id"], timeout=.05)

    async def test_public_url_must_belong_to_expected_account_and_draft(self):
        wrong_owner = dict(self.record, ucUrl=self.record["ucUrl"].replace("a" * 32, "c" * 32))
        request = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
            ok=True, json=AsyncMock(return_value={"dataList": {"data": [wrong_owner], "totalPage": 1}}),
        )))
        with self.assertRaisesRegex(RuntimeError, "主体或 origin_id 不匹配"):
            await verify_dayu_video(SimpleNamespace(request=request), self.browser,
                                    self.identity, content_id=self.record["content_id"], timeout=1, public=True)


class DayuMediaTests(unittest.TestCase):
    def test_invalid_category_and_conditional_source_are_rejected_before_upload(self):
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as folder:
            account_file = Path(folder) / "account.json"
            account_file.write_text("{}", encoding="utf-8")
            account_file.with_suffix(".identity.json").write_text(
                json.dumps({"wmid": "a" * 32, "name": "测试账号"}), encoding="utf-8",
            )
            for category, source, source_url, message in (
                ("不存在的分类", "无需标注", "", "视频分类必须为"),
                ("科技", "转载", "", "原文链接"),
                ("科技", "转载", "ftp://example.com/video", "原文链接"),
                ("科技", "无需标注", "https://example.com/video", "仅信息来源为转载"),
            ):
                with self.subTest(category=category, source=source, source_url=source_url):
                    video = DayuVideo("大鱼号视频上传测试", BASE_DIR / "videos/demo.mp4", [],
                                      account_file, BASE_DIR / "videos/demo.png", category, source,
                                      source_url=source_url)
                    with self.assertRaisesRegex(ValueError, message):
                        video.validate_upload_args()

    def test_original_demo_is_rejected_before_upload(self):
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as folder:
            account_file = Path(folder) / "account.json"
            account_file.write_text("{}", encoding="utf-8")
            account_file.with_suffix(".identity.json").write_text(
                json.dumps({"wmid": "a" * 32, "name": "测试账号"}), encoding="utf-8",
            )
            video = DayuVideo("大鱼号视频上传测试", BASE_DIR / "videos/demo.mp4", [],
                              account_file, BASE_DIR / "videos/demo.png", "其他", "无需标注")
            with self.assertRaisesRegex(ValueError, "至少需要 5 秒"):
                video.validate_upload_args()


if __name__ == "__main__":
    unittest.main()
