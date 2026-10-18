"""大鱼号视频发布：核验主体、等待处理、填写表单、确认发表并记录提交结果。"""
from __future__ import annotations

import asyncio
import json
import math
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import cv2
from patchright.async_api import Page, async_playwright, expect

from conf import LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from uploader.dayu_uploader.publication import submit_dayu_publication
from uploader.dayu_uploader.schedule import fill_dayu_schedule, validate_dayu_schedule
from uploader.dayu_uploader.session import DAYU_VIDEO_URL, load_dayu_identity, read_dayu_identity
from uploader.dayu_uploader.constants import DAYU_SOURCE_REPRINT, DAYU_SOURCE_TYPES, DAYU_VIDEO_CATEGORIES
from utils.log import dayu_logger


async def wait_dayu_processing(page: Page, filename: str, timeout: int = 600) -> None:
    """处理失败优先于完成文案；100% 和“上传成功，处理中”都不能判为可发表。"""
    deadline = time.monotonic() + timeout
    # 视频容器是上传前后保留的业务区域；不把变化中的进度或结果文案写进锚点。
    region = page.locator(".article-write_video-container")
    await expect(region).to_have_count(1)
    previous = None
    while time.monotonic() < deadline:
        text = await region.inner_text(timeout=max(1, min(5000, int((deadline - time.monotonic()) * 1000))))
        if re.search(r"失败|不支持|小于|超出|(?<!不)超过|请重新上传|无法", text):
            raise RuntimeError(f"大鱼号视频处理被拒绝: {text.strip()}")
        if "视频上传成功，处理完成" in text:
            await expect(region.locator(".article-write_video-container-result-desc p span")).to_have_text(filename)
            return
        if text != previous:
            dayu_logger.info(f"大鱼号上传状态: {text.strip()}")
            previous = text
        await asyncio.sleep(min(.5, max(0, deadline - time.monotonic())))
    raise TimeoutError("等待大鱼号上传/处理超时；未提交发表，请检查当前素材状态")


class DayuVideo(BaseVideoUploader):
    """以实际页面流程发表一个视频，持久化提交 ID 供断线后只读核验。"""

    SUPPORTED_VIDEO_EXTENSIONS = {
        ".3gp", ".avi", ".flv", ".mp4", ".m3u8", ".mpg", ".asf", ".wmv",
        ".mkv", ".mov", ".ts", ".webm", ".mts",
    }
    SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".gif", ".png", ".bmp", ".jpeg"}

    def __init__(self, title, file_path, tags, account_file, thumbnail_path, category,
                 source, desc="", headless=True, debug=False, prepare_only=False,
                 upload_timeout=600, source_url="", schedule=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.account_file = Path(account_file).resolve()
        self.thumbnail_path = thumbnail_path
        self.category = category
        self.source = source
        self.source_url = source_url
        self.desc = desc
        self.headless = headless
        self.debug = debug
        self.prepare_only = prepare_only
        self.upload_timeout = upload_timeout
        self.schedule = schedule

    def validate_upload_args(self) -> None:
        """上传前拒绝无法解码、时长不足、超限素材及缺失必填信息。"""
        self.schedule = validate_dayu_schedule(self.schedule)
        self.file_path = self.validate_video_file(self.file_path)
        self.thumbnail_path = self.validate_image_file(self.thumbnail_path)
        if not self.account_file.is_file():
            raise FileNotFoundError("请先执行 sau dayu login 保存账号")
        load_dayu_identity(self.account_file)
        # 编辑器按汉字 1、ASCII 0.5 计数（页面上 demo 显示 2/60）。
        title_length = sum(.5 if ord(char) <= 255 else 1 for char in self.title.strip())
        if not 5 <= title_length <= 60:
            raise ValueError("大鱼号标题长度需在 5–60 字之间（ASCII 按半字计数）")
        if len(self.desc) > 200:
            raise ValueError("大鱼号视频简介不能超过 200 字")
        if self.category not in DAYU_VIDEO_CATEGORIES:
            raise ValueError(f"视频分类必须为: {', '.join(DAYU_VIDEO_CATEGORIES)}")
        if self.source not in DAYU_SOURCE_TYPES:
            raise ValueError(f"必须明确提供信息来源: {', '.join(DAYU_SOURCE_TYPES)}")
        if self.source == DAYU_SOURCE_REPRINT:
            original = urlsplit(self.source_url)
            if original.scheme not in ("http", "https") or not original.hostname:
                raise ValueError("信息来源为转载时，必须使用 --source-url 提供 http/https 原文链接")
        elif self.source_url:
            raise ValueError("仅信息来源为转载时可以填写 --source-url 原文链接")
        if any(not tag.strip() or len(tag) > 10 for tag in self.tags):
            raise ValueError("视频标签不能为空且每个不能超过 10 字")
        if self.upload_timeout <= 0:
            raise ValueError("上传及发布核验期限必须大于 0 秒")
        if self.thumbnail_path.stat().st_size > 5 * 1024 ** 2:
            raise ValueError("大鱼号视频封面不能超过 5 MiB")
        capture = cv2.VideoCapture(str(self.file_path))
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
            width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        finally:
            capture.release()
        if not all(math.isfinite(value) and value > 0 for value in (fps, frames, width, height)):
            raise ValueError("无法读取视频尺寸、帧数或帧率，拒绝上传未知素材")
        duration = frames / fps
        if duration < 5:
            raise ValueError(f"大鱼号视频至少需要 5 秒，当前约 {duration:.3f} 秒")
        portrait = height > width
        if self.file_path.stat().st_size > (5 if portrait else 10) * 1024 ** 3:
            raise ValueError("视频超过大鱼号文件大小限制（横屏 10 GiB、竖屏 5 GiB）")
        if portrait and duration > 1800:
            raise ValueError("大鱼号竖屏视频时长不能超过 30 分钟")

    async def fill_video_form(self, page: Page) -> None:
        """填写并读回标题、简介、分类、标签、封面与来源，不代选来源。"""
        # 标题实际为 contenteditable；固定 placeholder 区分简介输入框和其他可编辑区域。
        title = page.locator('[contenteditable="true"][placeholder="视频标题最少5个字"]')
        await title.fill(self.title)
        await expect(title).to_have_text(self.title)
        # 表单中简介使用 textarea；分类通过字段 label 限定，避免点击其他同构下拉框。
        description = page.locator(".w-form-field").filter(has=page.locator("textarea")).locator("textarea")
        await description.fill(self.desc)
        await expect(description).to_have_value(self.desc)
        category = page.locator(".w-form-field").filter(
            has=page.locator("label").filter(has_text="视频分类"),
        )
        await category.locator(".widgets-selects_container").click()
        await category.get_by_role("link", name=self.category, exact=True).click()
        await expect(category.locator(".widgets-selects_container")).to_have_text(self.category)
        if self.tags:
            # 标签组件内会动态增加输入槽，先限定组件再按用户输入顺序选槽位。
            tags = page.locator(".article-write_video-tags")
            await tags.click()
            for index, tag in enumerate(self.tags):
                # 标签槽按用户给定顺序排列；Enter 在末尾新增一个空槽，并非任意选第 N 个控件。
                inputs = tags.locator("input")
                await expect(inputs).to_have_count(index + 1)
                await inputs.nth(index).fill(tag)
                await inputs.nth(index).press("Enter")
            await title.click()
            # 实测 Enter/失焦后会短暂少一个字并保留空槽，Vue 随后才恢复最终标签值。
            await expect(tags.locator("input")).to_have_count(len(self.tags))
            for index, tag in enumerate(self.tags):
                await expect(tags.locator("input").nth(index)).to_have_value(tag)
        # coverImg 是封面字段的语义 ID，限定其中 input 避免把封面传给主视频上传器。
        await page.locator("#coverImg input[type=file]").set_input_files(str(self.thumbnail_path))
        # 裁剪与素材选择共用弹窗组件，只定位本次可见实例，排除隐藏模板。
        dialog = page.locator(".article-material-image-dialog:visible")
        await expect(dialog).to_have_count(1, timeout=30000)
        await dialog.get_by_role("button", name="保存", exact=True).click()
        await expect(page.locator(".article-material-image-dialog:visible")).to_have_count(0, timeout=30000)
        cover = page.locator("#coverImg #form_main_cover_img")
        await expect(cover).to_be_visible()
        await expect(cover).to_have_attribute("src", re.compile(r"^https?://image\.uc\.cn/"))
        # 来源 radio 的 value 与页面选项一致；用业务值区分选项，不依赖左右排列顺序。
        source = page.locator(f'input[type=radio][value="{self.source}"]')
        await source.check()
        await expect(source).to_be_checked()
        # 原文链接按来源区域内的 label 定位，排除其他文本框；非转载时该条件字段应消失。
        original_link = page.locator(".source-remark-detail .article-write_box-form-filed").filter(
            has=page.locator("label").filter(has_text="原文链接"),
        ).locator('input[type="text"]')
        if self.source == DAYU_SOURCE_REPRINT:
            await original_link.fill(self.source_url)
            await expect(original_link).to_have_value(self.source_url)
        else:
            await expect(original_link).to_have_count(0)
        await fill_dayu_schedule(page, self.schedule)

    async def main(self) -> dict:
        """提交只执行一次；平台最终发表响应确认本次作品 ID 后即成功。"""
        self.validate_upload_args()
        expected = load_dayu_identity(self.account_file)
        results_dir = self.account_file.parent / "dayu_results"
        results_dir.mkdir(exist_ok=True)
        result_file = results_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.json"
        result = {"success": False, "status": "preparing", "type": "video", "title": self.title,
                  "video_file": str(self.file_path), "identity": expected,
                  "result_file": str(result_file)}
        if self.schedule:
            result["schedule"] = self.schedule.isoformat()
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=self.headless,
            )
            page = None
            try:
                context = await browser.new_context(storage_state=str(self.account_file), timezone_id="Asia/Shanghai")
                page = await context.new_page()
                await page.goto(DAYU_VIDEO_URL, wait_until="domcontentloaded", timeout=45000)
                identity = await read_dayu_identity(page)
                if identity["wmid"] != expected["wmid"]:
                    raise RuntimeError("大鱼号主体不匹配，上传已中止")
                result["identity"] = identity
                # 主视频上传器有 name=file，封面 input 没有此属性，可据此区分两种上传入口。
                file_input = page.locator('input[type="file"][name="file"]')
                await expect(file_input).to_have_count(1, timeout=30000)
                await file_input.set_input_files(str(self.file_path))
                await wait_dayu_processing(page, self.file_path.name, self.upload_timeout)
                await self.fill_video_form(page)
                # 填表和异步封面处理之后，再次核对同一主体及视频处理结果。
                if (await read_dayu_identity(page))["wmid"] != identity["wmid"]:
                    raise RuntimeError("填表期间大鱼号主体发生变化，拒绝提交")
                await wait_dayu_processing(page, self.file_path.name, self.upload_timeout)
                if self.prepare_only:
                    await page.screenshot(path=str(result_file.with_suffix(".png")), full_page=True)
                    result.update(success=True, status="prepared")
                    return result

                await submit_dayu_publication(page, result, result_file)
                await context.storage_state(path=str(self.account_file))
                action = "定时发布已安排" if self.schedule else "发表成功"
                dayu_logger.success(f"大鱼号{action}: {result['content_id']}")
                return result
            except Exception as exc:
                result["error"] = str(exc)
                dayu_logger.error(f"大鱼号阶段={result['status']}，结果文件={result_file}: {exc}")
                if self.debug and page is not None:
                    await page.screenshot(path=str(result_file.with_suffix(".png")))
                raise
            finally:
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                await browser.close()
