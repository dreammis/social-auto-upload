"""大鱼号视频/图文共用的时间校验和原生日期选择。"""
import re
from datetime import datetime, timedelta

from patchright.async_api import BrowserContext, Page, expect

from uploader.dayu_uploader.constants import (
    DAYU_MONTH_NAMES, DAYU_SCHEDULE_MAX_DAYS, DAYU_SCHEDULE_MIN_HOURS,
    DAYU_SCHEDULE_STEP_MINUTES, DAYU_TIMEZONE,
)


async def read_dayu_schedule(context: BrowserContext, origin_id: str, expected: str | None) -> dict:
    """读原稿的服务端保存值；查询旧结果时不再检查未来范围，也不改写平台时间。"""
    response = await context.request.get("https://mp.dayu.com/dashboard/getDraftInfo",
                                         params={"draft_id": origin_id}, timeout=30000)
    if not response.ok:
        raise RuntimeError(f"查询原作品定时设置失败: HTTP {response.status}")
    data = await response.json()
    if data.get("draft_id") != origin_id:
        raise RuntimeError("定时查询未返回本次原稿，可能登录失效或接口变化")
    enabled = data.get("is_timed_release")
    if expected is None:
        if enabled is not False:
            raise RuntimeError("平台未确认立即发布设置，拒绝确认发表")
        return {}
    target = datetime.fromisoformat(expected)
    if target.tzinfo is None:
        raise ValueError("结果文件中的定时时间必须包含时区")
    epoch = data.get("time_for_release")
    # 保存接口实测将控件隐藏秒数归整到分钟；核对精确 epoch，不能容忍平台错排一分钟。
    if enabled is not True or isinstance(epoch, bool) or not isinstance(epoch, (int, float)):
        raise RuntimeError("平台未保存本次定时发布设置")
    actual = datetime.fromtimestamp(epoch / 1000, DAYU_TIMEZONE)
    if actual != target:
        raise RuntimeError(f"平台保存的定时时间不一致: 预期={target.isoformat()}，实际={actual.isoformat()}")
    return {"schedule": actual.isoformat(), "schedule_verified": True}


def validate_dayu_schedule(value: datetime | None, now: datetime | None = None) -> datetime | None:
    """CLI 的无时区时间按北京时间解释，直接调用的带时区时间转换后校验，不自动取整。"""
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValueError("大鱼号定时时间必须为 datetime；CLI 使用 --schedule YYYY-MM-DD HH:MM")
    target = value.replace(tzinfo=DAYU_TIMEZONE) if value.tzinfo is None else value.astimezone(DAYU_TIMEZONE)
    current = now or datetime.now(DAYU_TIMEZONE)
    if current.tzinfo is None:
        raise ValueError("校验当前时间必须包含时区")
    if target.second or target.microsecond or target.minute % DAYU_SCHEDULE_STEP_MINUTES:
        raise ValueError(f"大鱼号定时按 {DAYU_SCHEDULE_STEP_MINUTES} 分钟一档，请提供整分钟时间（例如 10:30）")
    if not current + timedelta(hours=DAYU_SCHEDULE_MIN_HOURS) <= target <= current + timedelta(days=DAYU_SCHEDULE_MAX_DAYS):
        raise ValueError(f"大鱼号定时必须在北京时间的 {DAYU_SCHEDULE_MIN_HOURS} 小时后至 {DAYU_SCHEDULE_MAX_DAYS} 天内")
    return target


async def fill_dayu_schedule(page: Page, value: datetime | None) -> None:
    """使用页面实际提供的日、时、分选项；立即发布时也读回未启用状态。"""
    target = validate_dayu_schedule(value)
    # 正文普通布局与全屏布局各有一份设置；可见 radio 容器配合直接文本前缀排除隐藏副本和其他选项。
    option = page.locator(".article-write_radio:visible").filter(has_text=re.compile(r"^\s*定时发布"))
    await expect(option).to_have_count(1)
    toggle = option.locator(":scope > .w-radio")
    if "w-radio_checked" in (await toggle.get_attribute("class") or ""):
        await toggle.click()
    await expect(toggle).not_to_have_class(re.compile(r"\bw-radio_checked\b"))
    # 此输入只显示选中值，点击入口是其同组件的 mask；直接点击 input 会被 mask 拦截。
    widget = page.locator(".widgets-datepicker-m:visible")
    if target is None:
        await expect(widget).to_have_count(0)
        return
    if await page.evaluate("new Date().getTimezoneOffset()") != -480:
        raise RuntimeError("大鱼号定时浏览器必须使用 Asia/Shanghai 时区")
    await toggle.click()
    await expect(toggle).to_have_class(re.compile(r"\bw-radio_checked\b"))
    await expect(widget).to_have_count(1)
    await widget.locator(".widgets-datepicker-m_mask").click()
    # 两份布局各自创建日历实例；只操作打开的日历，视图类区分日期、小时和分钟。
    picker = page.locator(".datetimepicker:visible")
    await expect(picker).to_have_count(1)
    days = picker.locator(".datetimepicker-days")
    heading = days.locator("th.switch")
    desired_month = f"{DAYU_MONTH_NAMES[target.month - 1]} {target.year}"
    if (await heading.inner_text()).strip() != desired_month:
        # 七天范围最多跨到下个月，下一月按钮在此范围可用；不按未知月份循环点击。
        await days.locator("th.next").click()
    await expect(heading).to_have_text(desired_month)
    day = days.locator("td.day:not(.old):not(.new)").filter(has_text=re.compile(f"^{target.day}$"))
    await expect(day).not_to_have_class(re.compile(r"\bdisabled\b"))
    await day.click()
    hour = picker.locator(".datetimepicker-hours .hour").filter(has_text=re.compile(f"^{target.hour}:00$"))
    await expect(hour).not_to_have_class(re.compile(r"\bdisabled\b"))
    await hour.click()
    # 原生日历的小时不补零（1:05），输入框则补零（01:05）；不能共用显示格式定位分钟。
    minute = picker.locator(".datetimepicker-minutes .minute").filter(has_text=re.compile(f"^{target.hour}:{target.minute:02d}$"))
    await expect(minute).not_to_have_class(re.compile(r"\bdisabled\b"))
    await minute.click()
    await expect(picker).to_have_count(0)
    await expect(widget.locator("input")).to_have_value(target.strftime("%Y年%m月%d日 %H:%M"))
