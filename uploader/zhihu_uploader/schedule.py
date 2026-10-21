"""知乎文章和视频的北京时间定时设置。"""
from datetime import datetime, timedelta
import re

from patchright.async_api import Page, expect

from uploader.zhihu_uploader.constants import (
    ZHIHU_SCHEDULE_MAX_HOURS, ZHIHU_SCHEDULE_MINUTES, ZHIHU_TIMEZONE,
)


def validate_zhihu_schedule(value: datetime | None, now: datetime | None = None) -> datetime | None:
    """按页面实际支持的范围校验时间；无时区 CLI 输入按北京时间解释。"""
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValueError("知乎定时时间必须为 datetime；CLI 使用 --schedule YYYY-MM-DD HH:MM")
    target = value.replace(tzinfo=ZHIHU_TIMEZONE) if value.tzinfo is None else value.astimezone(ZHIHU_TIMEZONE)
    current = now or datetime.now(ZHIHU_TIMEZONE)
    if current.tzinfo is None:
        raise ValueError("知乎定时校验时钟必须包含时区")
    if target.second or target.microsecond:
        raise ValueError("知乎定时精确到分钟，不接受秒或微秒")
    if not current + timedelta(minutes=ZHIHU_SCHEDULE_MINUTES) <= target <= current + timedelta(hours=ZHIHU_SCHEDULE_MAX_HOURS):
        raise ValueError("知乎定时需在北京时间当前时刻 30 分钟后至 48 小时内")
    return target


async def fill_zhihu_article_schedule(page: Page, value: datetime | None) -> None:
    """通过文章发布面板的日期、小时、分钟选择器填写并读回排期。"""
    target = validate_zhihu_schedule(value)
    if target is None:
        return

    # 文章表单将“定时发布”作为单独开关；点击后弹出已观察到的计划时间面板。
    await page.get_by_text("定时发布", exact=True).click()
    panel_label = page.get_by_text("开启定时发布", exact=True)
    await expect(panel_label).to_be_visible()
    picker = page.locator(".DateTimePicker")
    await expect(picker).to_have_count(1)
    date_button = page.locator(".DatePicker-Button")
    await expect(date_button).to_have_count(1)
    shown_date = await date_button.inner_text()
    if shown_date != target.strftime("%Y-%m-%d"):
        await date_button.click()
        calendar = page.locator(".Calendar")
        await expect(calendar).to_be_visible()
        shown_month = (await calendar.locator(".Calendar-topToolDate").inner_text()).strip()
        wanted_month = f"{target.year} 年 {target.month} 月"
        if shown_month != wanted_month:
            # 48 小时范围最多只跨到相邻月份；按钮职责 class 来自页面日历实际 DOM。
            await calendar.locator(".Calendar-topToolButton--nextMonth").click()
        await expect(calendar.locator(".Calendar-topToolDate")).to_have_text(wanted_month)
        day = calendar.locator("td.Calendar-day:not(.is-disabled):not(.is-not-this-month)").filter(
            has_text=re.compile(rf"^{target.day}$"),
        )
        await expect(day).to_have_count(1)
        await day.click()
        await expect(date_button).to_have_text(target.strftime("%Y-%m-%d"))

    # 页面将小时与分钟分成两个同构下拉；DOM 顺序已由实际弹层验证。
    time_selects = picker.locator(".Select-button")
    await expect(time_selects).to_have_count(2)
    await time_selects.nth(0).click()
    hour = page.get_by_role("option", name=f"{target.hour:02d}", exact=True)
    await expect(hour).to_have_count(1)
    if not await hour.is_enabled():
        raise RuntimeError("知乎定时小时选项当前不可选，请检查时间范围")
    await hour.click()
    await time_selects.nth(1).click()
    minute = page.get_by_role("option", name=f"{target.minute:02d}", exact=True)
    await expect(minute).to_have_count(1)
    if not await minute.is_enabled():
        raise RuntimeError("知乎定时分钟选项当前不可选，请检查时间范围")
    await minute.click()
    await expect(time_selects.nth(0)).to_have_text(f"{target.hour:02d}")
    await expect(time_selects.nth(1)).to_have_text(f"{target.minute:02d}")
    confirm = page.get_by_role("button", name="确认", exact=True)
    await expect(confirm).to_be_enabled()
    await confirm.click()
    await expect(panel_label).to_have_count(0)


async def fill_zhihu_video_schedule(page: Page, value: datetime | None) -> None:
    """通过视频表单自己的定时区启用并读回日期与时间。"""
    target = validate_zhihu_schedule(value)
    if target is None:
        return
    schedule = page.locator(".VideoUploadForm-scheduledPublish")
    await expect(schedule).to_have_count(1)
    # 视频页脚本将该组件挂在 VideoUploadForm-scheduledPublish 行内。
    toggle = schedule.locator('input[type="checkbox"]')
    await expect(toggle).to_have_count(1)
    if not await toggle.is_checked():
        await toggle.check()
    picker = schedule.locator(".DateTimePicker")
    await expect(picker).to_be_visible()
    date_button = picker.locator(".DatePicker-Button")
    await expect(date_button).to_have_count(1)
    shown_date = await date_button.inner_text()
    if shown_date != target.strftime("%Y-%m-%d"):
        await date_button.click()
        calendar = page.locator(".Calendar")
        await expect(calendar).to_be_visible()
        shown_month = (await calendar.locator(".Calendar-topToolDate").inner_text()).strip()
        wanted_month = f"{target.year} 年 {target.month} 月"
        if shown_month != wanted_month:
            await calendar.locator(".Calendar-topToolButton--nextMonth").click()
        await expect(calendar.locator(".Calendar-topToolDate")).to_have_text(wanted_month)
        day = calendar.locator("td.Calendar-day:not(.is-disabled):not(.is-not-this-month)").filter(
            has_text=re.compile(rf"^{target.day}$"),
        )
        await expect(day).to_have_count(1)
        await day.click()
        await expect(date_button).to_have_text(target.strftime("%Y-%m-%d"))
    time_selects = picker.locator(".Select-button")
    await expect(time_selects).to_have_count(2)
    await time_selects.nth(0).click()
    hour = page.get_by_role("option", name=f"{target.hour:02d}", exact=True)
    await expect(hour).to_have_count(1)
    if not await hour.is_enabled():
        raise RuntimeError("知乎定时小时选项当前不可选，请检查时间范围")
    await hour.click()
    await time_selects.nth(1).click()
    minute = page.get_by_role("option", name=f"{target.minute:02d}", exact=True)
    await expect(minute).to_have_count(1)
    if not await minute.is_enabled():
        raise RuntimeError("知乎定时分钟选项当前不可选，请检查时间范围")
    await minute.click()
    await expect(time_selects.nth(0)).to_have_text(f"{target.hour:02d}")
    await expect(time_selects.nth(1)).to_have_text(f"{target.minute:02d}")
