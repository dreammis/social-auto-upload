"""知乎单视频上传：传输、元数据、定时选项和提交状态分开核对。"""
from __future__ import annotations

import asyncio
import json
import sys
import math
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2
from patchright.async_api import Page, async_playwright, expect

from conf import LOCAL_CHROME_PATH
from uploader.zhihu_uploader.constants import (
    ZHIHU_ORIGINALITY, ZHIHU_TIMEZONE, ZHIHU_VIDEO_DESCRIPTION_MAX, ZHIHU_VIDEO_EXTENSIONS,
    ZHIHU_VIDEO_MAX_BYTES, ZHIHU_VIDEO_MIN_BYTES, ZHIHU_VIDEO_MAX_SECONDS, ZHIHU_VIDEO_TITLE_MAX,
    ZHIHU_VIDEO_TITLE_MIN, ZHIHU_VIDEO_URL, ZHIHU_VIDEO_TOPICS_MAX,
)
from uploader.zhihu_uploader.schedule import fill_zhihu_video_schedule, validate_zhihu_schedule
from uploader.zhihu_uploader.session import load_zhihu_identity, read_zhihu_identity


class ZhihuVideo:
    """上传并发布一个知乎视频，未知提交结果会保留在本地 JSON 中。"""

    def __init__(self, title, file_path, account_file, description, category,
                 topics, video_mark, originality, schedule=None, show_options=False,
                 headless=True, debug=False, prepare_only=False, upload_timeout=1200):
        self.title = title
        self.file_path = Path(file_path).expanduser().resolve()
        self.account_file = Path(account_file).resolve()
        self.description = description
        self.category = category
        self.show_options = show_options
        self.topics = topics
        self.video_mark = video_mark
        self.originality = originality
        self.schedule = schedule
        self.headless = headless
        self.debug = debug
        self.prepare_only = prepare_only
        self.upload_timeout = upload_timeout

    def validate_upload_args(self) -> None:
        """依据页面提示检查视频、标题、简介和当前上传所需的分类参数。"""
        if not self.file_path.is_file():
            raise FileNotFoundError(f"知乎视频不存在: {self.file_path}")
        if self.file_path.suffix.lower() not in ZHIHU_VIDEO_EXTENSIONS:
            raise ValueError(f"知乎视频格式不受页面支持: {self.file_path.suffix}")
        if self.file_path.stat().st_size <= ZHIHU_VIDEO_MIN_BYTES:
            raise ValueError("知乎视频必须大于 100KB")
        if self.file_path.stat().st_size > ZHIHU_VIDEO_MAX_BYTES:
            raise ValueError("知乎视频文件不能超过 20 GB")
        capture = cv2.VideoCapture(str(self.file_path))
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        finally:
            capture.release()
        if not math.isfinite(fps) or not math.isfinite(frames) or fps <= 0 or frames <= 0:
            raise ValueError("无法读取视频帧率或帧数，拒绝上传未知素材")
        if frames / fps > ZHIHU_VIDEO_MAX_SECONDS:
            raise ValueError("知乎视频时长不能超过 4 小时")
        if not ZHIHU_VIDEO_TITLE_MIN <= len(self.title.strip()) <= ZHIHU_VIDEO_TITLE_MAX:
            raise ValueError(f"知乎视频标题需为 {ZHIHU_VIDEO_TITLE_MIN}–{ZHIHU_VIDEO_TITLE_MAX} 字")
        if len(self.description) > ZHIHU_VIDEO_DESCRIPTION_MAX:
            raise ValueError(f"知乎视频简介不能超过 {ZHIHU_VIDEO_DESCRIPTION_MAX} 字")
        if len(self.topics) > ZHIHU_VIDEO_TOPICS_MAX:
            raise ValueError(f"知乎视频最多 {ZHIHU_VIDEO_TOPICS_MAX} 个话题")
        if any(not topic.strip() for topic in self.topics):
            raise ValueError("知乎视频话题不能为空")
        if self.topics:
            raise ValueError("知乎视频暂不支持自动选择话题，请使用简介描述内容")
        if self.originality not in ZHIHU_ORIGINALITY:
            raise ValueError("原创标记必须为 original 或 reprint")
        self.schedule = validate_zhihu_schedule(self.schedule)
        if not self.account_file.is_file():
            raise FileNotFoundError("请先执行 sau zhihu login 保存账号")
        self.identity = load_zhihu_identity(self.account_file)
        if self.upload_timeout <= 0:
            raise ValueError("上传期限必须大于 0 秒")

    async def video_options(self, page: Page) -> dict:
        """从本次素材实际渲染的菜单读取完整候选；不拿旧版二级领域代替新版表单。"""
        # 所属领域标签限定业务行，visible 限定本次展开的列表，排除隐藏菜单。
        field = page.locator(".VideoUploadForm-item").filter(has=page.get_by_text("所属领域", exact=True))
        await expect(field).to_have_count(1)
        control = field.get_by_role("combobox")
        await control.click()
        menu = page.locator(".VideoUploadForm-selectList:visible")
        await expect(menu).to_have_count(1)
        # 页面源码对每个领域只渲染一个 name；逐行读取完整菜单，不依赖未观察的子组件 class。
        await expect(menu).to_contain_text(re.compile(r"\S"))
        categories = [text.strip() for text in await menu.get_by_role("option").all_inner_texts()
                      if text.strip() and text.strip() != "选择领域"]
        await control.click()
        mark_field = page.locator(".VideoUploadForm-item").filter(has=page.get_by_text("视频标记", exact=True))
        await mark_field.get_by_role("button", name="选择视频标记", exact=True).click()
        modal = page.locator(".VideoUploadForm-videoTypeModal:visible")
        await expect(modal).to_be_visible()
        marks = [text.strip() for text in await modal.locator(".VideoUploadForm-videoTypeModalOption").all_inner_texts()
                 if text.strip() and text.strip() not in {"确认", "取消", "关闭"}]
        # 只读完选项后取消弹层，不把第一个候选当成用户选择。
        await modal.get_by_role("button", name="取消", exact=True).click()
        await expect(modal).to_be_hidden()
        if not categories or not marks or len(categories) != len(set(categories)) or len(marks) != len(set(marks)):
            raise RuntimeError("知乎候选为空或重复，无法安全生成选择菜单")
        return {"category": categories, "video_mark": marks}

    async def select_option(self, label: str, value: str | None, choices: list[str]) -> str:
        """终端显示实际候选并按编号选择；脚本调用只能使用本次菜单中存在的值。"""
        if value is not None:
            if value not in choices:
                raise ValueError(f"{label}必须为: {'、'.join(choices)}")
            return value
        print(label + "：", file=sys.stderr)
        for index, choice in enumerate(choices, 1):
            print(f"  {index}. {choice}", file=sys.stderr)
        if not sys.stdin.isatty():
            raise ValueError(f"非交互调用必须指定{label}；可先使用 --show-options 获取完整候选")
        answer = await asyncio.to_thread(input, f"选择{label}编号（1–{len(choices)}）：")
        if not answer.isdecimal() or not 1 <= int(answer) <= len(choices):
            raise ValueError(f"{label}编号无效")
        return choices[int(answer) - 1]

    async def fill_video_options(self, page: Page) -> None:
        """只选择已核对的实时菜单值，选择后读回表单。"""
        field = page.locator(".VideoUploadForm-item").filter(has=page.get_by_text("所属领域", exact=True))
        control = field.get_by_role("combobox")
        await control.click()
        await page.locator(".VideoUploadForm-selectList:visible").get_by_role("option", name=self.category, exact=True).click()
        await expect(control).to_contain_text(self.category)
        mark_field = page.locator(".VideoUploadForm-item").filter(has=page.get_by_text("视频标记", exact=True))
        await mark_field.get_by_role("button", name="选择视频标记", exact=True).click()
        modal = page.locator(".VideoUploadForm-videoTypeModal:visible")
        await modal.get_by_role("button", name=self.video_mark, exact=True).click()
        await modal.get_by_role("button", name="确认", exact=True).click()
        await expect(modal).to_be_hidden()

    async def fill_video_form(self, page: Page) -> None:
        """等本次视频传输成功，再填写并读回页面要求的元数据。"""
        form = page.locator(".VideoUploadForm-item").filter(
            has=page.get_by_text("标题与介绍", exact=True),
        )
        await expect(form).to_be_visible(timeout=self.upload_timeout * 1000)
        failure = page.get_by_text("视频上传失败", exact=True)
        if await failure.count():
            raise RuntimeError("知乎明确显示视频上传失败")
        # 页面代码以“上传成功”作为 uploaded 状态；只等该状态，不把表单出现或进度完成当作处理完成。
        await expect(page.get_by_text("上传成功", exact=True)).to_be_visible(timeout=self.upload_timeout * 1000)

        title = form.locator("textarea")
        await expect(title).to_have_count(1)
        await title.fill(self.title)
        await expect(title).to_have_value(self.title)
        description = form.locator('[contenteditable="true"][role="textbox"]')
        await expect(description).to_have_count(1)
        await description.fill(self.description)
        if self.description.strip():
            await expect(description).to_contain_text(self.description[:80])

        await self.fill_video_options(page)

        # 原创/转载是页面的独立 checkbox；按参数状态设置，不依赖控件视觉顺序。
        # 按“原创视频”业务行限定，避免与定时发布等其它 checkbox 混淆。
        originality = page.locator(".VideoUploadForm-item").filter(
            has=page.get_by_text("原创视频", exact=True),
        ).get_by_role("checkbox")
        await expect(originality).to_have_count(1)
        wanted_original = self.originality == "original"
        if await originality.is_checked() != wanted_original:
            await originality.click()
        if wanted_original:
            await expect(originality).to_be_checked()
        else:
            await expect(originality).not_to_be_checked()

        await fill_zhihu_video_schedule(page, self.schedule)

    async def main(self) -> dict:
        """只提交一次；页面没有确认本次作品 URL 时记录为 submission_unknown。"""
        self.validate_upload_args()
        results_dir = self.account_file.parent / "zhihu_results"
        results_dir.mkdir(exist_ok=True)
        result_file = results_dir / f"{datetime.now(ZHIHU_TIMEZONE):%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.json"
        result = {
            "success": False, "status": "preparing", "type": "video", "title": self.title,
            "video_file": str(self.file_path), "identity": self.identity, "topics": self.topics,
            "category": self.category,
            "video_mark": self.video_mark, "originality": self.originality,
            "result_file": str(result_file),
        }
        if self.schedule:
            result["schedule"] = self.schedule.isoformat()
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=self.headless,
            )
            page = None
            submitted = False
            try:
                context = await browser.new_context(
                    storage_state=str(self.account_file), timezone_id="Asia/Shanghai",
                )
                page = await context.new_page()
                response = await page.goto(ZHIHU_VIDEO_URL, wait_until="domcontentloaded", timeout=45000)
                if response is not None and response.status >= 400:
                    raise RuntimeError(f"知乎视频上传页访问失败，HTTP {response.status}")
                if await read_zhihu_identity(page) != self.identity:
                    raise RuntimeError("知乎视频页头与本地账号绑定不一致")
                # 该 input 的 class 和 accept 来自上传首页实际 DOM；不与封面/正文图片 input 混用。
                video_input = page.locator("input.VideoUploadButton-fileInput[type=file]")
                await expect(video_input).to_have_count(1)
                await video_input.set_input_files(str(self.file_path))
                result["status"] = "uploading"
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                # 表单在素材选择后才出现；候选来自该账号、该素材的实际页面。
                await expect(page.get_by_text("上传成功", exact=True)).to_be_visible(timeout=self.upload_timeout * 1000)
                choices = await self.video_options(page)
                result["options"] = choices
                if self.show_options:
                    result["status"] = "options_listed"
                    return result
                self.category = await self.select_option("所属领域", self.category, choices["category"])
                self.video_mark = await self.select_option("视频标记", self.video_mark, choices["video_mark"])
                result.update(category=self.category, video_mark=self.video_mark)
                await self.fill_video_form(page)
                if await read_zhihu_identity(page) != self.identity:
                    raise RuntimeError("知乎视频填写期间当前账号发生变化")
                result["status"] = "prepared"
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                if self.prepare_only:
                    return result

                # 当前视频入口在原页显示成功弹层，“查看详情”另开 /pin/<id>。
                # 不能等待原页跳转到旧版 /zvideo/，否则已发表也会被误判为未知。
                publish = page.get_by_role("button", name="发布视频", exact=True)
                await expect(publish).to_be_enabled()
                submitted = True
                result["status"] = "submission_unknown"
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                await publish.click()
                await expect(page.get_by_text("发布成功", exact=True)).to_be_visible(timeout=60000)
                result.update(success=True, status="published")
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                async with page.expect_popup() as detail_info:
                    await page.get_by_text("查看详情", exact=True).click()
                detail = await detail_info.value
                await detail.wait_for_url(re.compile(r"^https://www\.zhihu\.com/(?:pin|zvideo|video)/\d+"), timeout=60000)
                result["url"] = detail.url
                return result
            except Exception as exc:
                result["error"] = str(exc)
                if result["status"] != "published":
                    result["status"] = "submission_unknown" if submitted else "failed_before_submit"
                if submitted and page is not None and re.match(r"^https://www\.zhihu\.com/(?:pin|zvideo|video)/\d+", page.url):
                    result["url"] = page.url
                if self.debug and page is not None:
                    screenshot = result_file.with_suffix(".png")
                    await page.screenshot(path=str(screenshot))
                    result["screenshot"] = str(screenshot)
                if result["status"] == "published":
                    # 平台已经确认发表；保留详情读取错误供原作品查询，不返回可重试的发表失败。
                    return result
                raise RuntimeError(f"知乎视频阶段={result['status']}，结果文件={result_file}: {exc}") from exc
            finally:
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                await browser.close()
