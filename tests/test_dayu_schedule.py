"""定时参数在上传前校验；平台时间必须独立读回，不能只相信 UI 已选中。"""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from patchright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH

from uploader.dayu_uploader.constants import DAYU_TIMEZONE
from uploader.dayu_uploader.schedule import validate_dayu_schedule, fill_dayu_schedule, read_dayu_schedule
from uploader.dayu_uploader.article import DayuArticle
from uploader.dayu_uploader.main import DayuVideo
from uploader.dayu_uploader.verification import verify_dayu_article, verify_dayu_video


class DayuScheduleTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 12, 31, 20, 0, tzinfo=DAYU_TIMEZONE)

    def test_immediate_remains_default(self):
        self.assertIsNone(validate_dayu_schedule(None, self.now))

    def test_naive_is_beijing_and_aware_is_converted(self):
        expected = datetime(2027, 1, 1, 10, 30, tzinfo=DAYU_TIMEZONE)
        self.assertEqual(validate_dayu_schedule(expected.replace(tzinfo=None), self.now), expected)
        self.assertEqual(validate_dayu_schedule(expected.astimezone(timezone.utc), self.now), expected)

    def test_exact_range_boundaries_are_inclusive(self):
        for delta in (timedelta(hours=2), timedelta(days=7)):
            value = self.now + delta
            self.assertEqual(validate_dayu_schedule(value, self.now), value)

    def test_outside_range_rejected_without_rounding(self):
        for delta in (timedelta(minutes=-5), timedelta(hours=1, minutes=55),
                      timedelta(days=7, minutes=5)):
            with self.subTest(delta=delta), self.assertRaisesRegex(ValueError, "2 小时后至 7 天内"):
                validate_dayu_schedule(self.now + delta, self.now)

    def test_minute_precision_and_step_rejected_without_rounding(self):
        value = self.now + timedelta(days=1)
        for field in ({"minute": 1}, {"second": 1}, {"microsecond": 1}):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "5 分钟一档"):
                validate_dayu_schedule(value.replace(**field), self.now)

    def test_invalid_types_and_naive_reference_clock_rejected(self):
        with self.assertRaisesRegex(ValueError, "必须为 datetime"):
            validate_dayu_schedule("2027-01-01 10:30", self.now)
        with self.assertRaisesRegex(ValueError, "必须包含时区"):
            validate_dayu_schedule(self.now + timedelta(days=1), self.now.replace(tzinfo=None))

    def test_invalid_schedule_rejected_before_reading_any_media(self):
        for app in (DayuArticle("测试文章标题", "missing.md", "missing.json", "AI生成", schedule=self.now),
                    DayuVideo("测试视频标题", "missing.mp4", [], "missing.json", "missing.png", "科技", "AI生成", schedule=self.now)):
            with self.subTest(app=type(app).__name__), self.assertRaisesRegex(ValueError, "2 小时后"):
                app.validate_upload_args()


class DayuScheduleReadbackTests(unittest.IsolatedAsyncioTestCase):
    def context(self, data):
        return SimpleNamespace(request=SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
            ok=True, json=AsyncMock(return_value=data)))))

    async def test_original_draft_time_must_match_exactly(self):
        # 查询已过去的安排也合法；校验范围只在新提交前进行。
        target = datetime(2026, 1, 1, 10, 30, tzinfo=DAYU_TIMEZONE)
        data = {"draft_id": "original", "is_timed_release": True, "time_for_release": target.timestamp() * 1000}
        result = await read_dayu_schedule(self.context(data), "original", target.isoformat())
        self.assertTrue(result["schedule_verified"])
        for field in ({"time_for_release": data["time_for_release"] + 60000},
                      {"is_timed_release": False}, {"time_for_release": True}, {"draft_id": "wrong"}):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                await read_dayu_schedule(self.context(dict(data, **field)), "original", target.isoformat())
        with self.assertRaisesRegex(RuntimeError, "立即发布"):
            await read_dayu_schedule(self.context(data), "original", None)
        self.assertEqual(await read_dayu_schedule(self.context(dict(data, is_timed_release=False)), "original", None), {})

    async def test_original_scheduled_work_is_success_without_waiting_for_audit(self):
        expected = "2026-01-01T10:30:00+08:00"
        epoch = datetime.fromisoformat(expected).timestamp() * 1000
        record = {"content_id": "123", "origin_id": "original", "title": "测试定时作品", "status": 5,
                  "audit_status": 0, "_app_extra": {"time_for_release": epoch}}
        for verify in (verify_dayu_video, verify_dayu_article):
            for schedule in (expected, None):
                with self.subTest(verify=verify.__name__, schedule=schedule):
                    context = self.context({"dataList": {"data": [record], "totalPage": 1}})
                    browser = SimpleNamespace(new_context=AsyncMock(side_effect=AssertionError("不应等待公开")))
                    result = await verify(context, browser, {}, content_id="123", schedule=schedule)
                    self.assertEqual(result["status"], "scheduled")
                    self.assertEqual(result["schedule"], expected)
                    self.assertTrue(result["success"])
                    self.assertEqual(context.request.get.await_count, 1)
                    browser.new_context.assert_not_awaited()
            # 实测视频提交初期 status=3，但安排已保存；无需等待审核转成 status=5。
            context = self.context({"dataList": {"data": [dict(record, status=3)], "totalPage": 1}})
            pending = await verify(context, None, {}, content_id="123", schedule=expected)
            self.assertTrue(pending["success"])
            self.assertEqual(pending["status"], "scheduled")
            for extra in ({}, {"time_for_release": epoch + 60000}):
                context = self.context({"dataList": {"data": [dict(record, _app_extra=extra)], "totalPage": 1}})
                with self.assertRaisesRegex(RuntimeError, "缺少|不一致"):
                    await verify(context, None, {}, content_id="123", schedule=expected)


class DayuScheduleBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=True)
        self.context = await self.browser.new_context(timezone_id="Asia/Shanghai")
        self.page = await self.context.new_page()

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()

    async def test_native_picker_ignores_hidden_copy_and_crosses_year(self):
        # 复现原生组件的可见副本、mask 入口及逐级选择，不直接给 input/Vue 模型赋目标时间。
        await self.page.set_content('''<meta charset="utf-8"><style>.w-radio{width:18px;height:18px;display:inline-block}</style>
            <div hidden><div class="article-write_radio"><div class="w-radio"></div>定时发布</div></div>
            <div class="article-write_radio"><div id="toggle" class="w-radio w-radio_checked"></div>定时发布<span>说明</span></div>
            <div class="widgets-datepicker-m"><input><div class="widgets-datepicker-m_mask">选择时间</div></div>
            <div class="datetimepicker" style="display:none">
             <div class="datetimepicker-days"><table><thead><tr><th class="switch">十二月 2026</th><th class="next">下一月</th></tr></thead>
             <tbody><tr><td class="day old">1</td><td class="day">1</td><td class="day new">1</td></tr></tbody></table></div>
             <div class="datetimepicker-hours" style="display:none"><span class="hour">1:00</span></div>
             <div class="datetimepicker-minutes" style="display:none"><span class="minute">1:05</span></div>
            </div><script>
            const widget=document.querySelector('.widgets-datepicker-m'), picker=document.querySelector('.datetimepicker');
            const days=picker.querySelector('.datetimepicker-days'), hours=picker.querySelector('.datetimepicker-hours'), minutes=picker.querySelector('.datetimepicker-minutes');
            toggle.onclick=()=>{toggle.classList.toggle('w-radio_checked');widget.style.display=toggle.classList.contains('w-radio_checked')?'':'none'};
            widget.querySelector('.widgets-datepicker-m_mask').onclick=()=>picker.style.display='';
            days.querySelector('.next').onclick=()=>days.querySelector('.switch').textContent='一月 2027';
            days.querySelector('td.day:not(.old):not(.new)').onclick=()=>{days.style.display='none';hours.style.display=''};
            hours.querySelector('.hour').onclick=()=>{hours.style.display='none';minutes.style.display=''};
            minutes.querySelector('.minute').onclick=()=>{widget.querySelector('input').value='2027年01月01日 01:05';picker.style.display='none'};
            </script>''')
        target = datetime(2027, 1, 1, 1, 5, tzinfo=DAYU_TIMEZONE)
        with patch("uploader.dayu_uploader.schedule.validate_dayu_schedule", return_value=target):
            await fill_dayu_schedule(self.page, target)
        self.assertEqual(await self.page.locator('.widgets-datepicker-m input').input_value(), "2027年01月01日 01:05")
        await fill_dayu_schedule(self.page, None)
        self.assertNotIn("w-radio_checked", await self.page.locator('#toggle').get_attribute('class'))

    async def test_wrong_browser_timezone_is_rejected(self):
        page = await self.browser.new_page(timezone_id="UTC")
        await page.set_content('<div class="article-write_radio"><div class="w-radio"></div>定时发布</div>')
        target = (datetime.now(DAYU_TIMEZONE) + timedelta(days=1)).replace(hour=10, minute=30, second=0, microsecond=0)
        with self.assertRaisesRegex(RuntimeError, "Asia/Shanghai"):
            await fill_dayu_schedule(page, target)


if __name__ == "__main__":
    unittest.main()
