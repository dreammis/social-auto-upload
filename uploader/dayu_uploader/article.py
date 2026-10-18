"""大鱼号图文：正文文件、富文本粘贴、本地图片上传及发表确认。"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from patchright.async_api import Locator, Page, async_playwright, expect

from conf import LOCAL_CHROME_PATH
from uploader.dayu_uploader.article_content import load_dayu_article
from uploader.dayu_uploader.article_style import render_dayu_compatible_html
from uploader.dayu_uploader.constants import DAYU_SOURCE_REPRINT, DAYU_SOURCE_TYPES
from uploader.dayu_uploader.publication import submit_dayu_publication
from uploader.dayu_uploader.schedule import fill_dayu_schedule, validate_dayu_schedule
from uploader.dayu_uploader.session import load_dayu_identity, read_dayu_identity
from uploader.dayu_uploader.verification import check_dayu_article_content
from utils.log import dayu_logger

DAYU_ARTICLE_URL = "https://mp.dayu.com/dashboard/article/write"
DAYU_ARTICLE_COVER_MODES = {1: "单封面", 3: "三封面"}
# 实测页面还有 UEditor 辅助 iframe；限定正文编辑区与 iframeholder 才唯一指向文章正文。
ARTICLE_BODY = ".article-write_box-editor .edui-editor-iframeholder iframe"


async def wait_dayu_article_body_stable(body: Locator) -> None:
    """粘贴后的异步清理会替换容器节点；稳定后才缓存插图选区或核对最终正文。"""
    deadline = time.monotonic() + 15
    previous = None
    stable = 0
    while time.monotonic() < deadline:
        current = await body.inner_html()
        stable = stable + 1 if current == previous else 0
        previous = current
        if stable >= 3:
            return
        await body.page.wait_for_timeout(1000)
    raise RuntimeError("大鱼号正文持续变化，未确认最终编辑结果")


class DayuArticle:
    """正文以 UTF-8 文件传入；图片顺序由 HTML 中 img 的位置决定。"""

    def __init__(self, title, content_file, account_file, source, source_url="", author=None,
                 cover_indices=None, headless=True, debug=False, prepare_only=False,
                 upload_timeout=600, theme=None, schedule=None):
        self.title = title
        self.content_file = Path(content_file).expanduser().resolve()
        self.account_file = Path(account_file).resolve()
        self.source = source
        self.source_url = source_url
        self.author = author
        self.cover_indices = cover_indices or []
        self.headless = headless
        self.debug = debug
        self.prepare_only = prepare_only
        self.upload_timeout = upload_timeout
        self.theme = theme
        self.schedule = schedule

    def validate_upload_args(self):
        """在接触远端素材之前，检查正文格式、封面序号及来源的条件必填项。"""
        self.schedule = validate_dayu_schedule(self.schedule)
        self.document = load_dayu_article(self.content_file, self.theme)
        title_length = math.ceil(sum(.5 if ord(char) <= 255 else 1 for char in self.title.strip()))
        if not 5 <= title_length <= 50:
            raise ValueError("大鱼号图文标题需要 5–50 字（英文字符按半字计数并向上取整）")
        if not self.account_file.is_file():
            raise FileNotFoundError("请先执行 sau dayu login 保存账号")
        load_dayu_identity(self.account_file)
        if self.source not in DAYU_SOURCE_TYPES:
            raise ValueError(f"信息来源必须为: {', '.join(DAYU_SOURCE_TYPES)}")
        if self.source == DAYU_SOURCE_REPRINT:
            original = urlsplit(self.source_url)
            if original.scheme not in ("http", "https") or not original.hostname:
                raise ValueError("转载时必须使用 --source-url 提供 http/https 原文链接")
        elif self.source_url:
            raise ValueError("仅信息来源为转载时可以填写 --source-url")
        if self.author is not None:
            author_length = math.ceil(sum(.5 if ord(char) <= 255 else 1 for char in self.author.strip()))
            if not 1 <= author_length <= 10:
                raise ValueError("作者名称需要 1–10 字（英文字符按半字计数并向上取整）")
        if self.cover_indices:
            if len(self.cover_indices) not in DAYU_ARTICLE_COVER_MODES:
                raise ValueError("--cover-indices 需要提供 1 个或 3 个正文图片序号，对应单封面或三封面")
            if any(index < 1 or index > len(self.document.images) for index in self.cover_indices):
                raise ValueError("封面序号超出正文图片范围，图片从 1 开始计数")
            if len(set(self.cover_indices)) != len(self.cover_indices):
                raise ValueError("三封面请提供不同的正文图片序号")
        if self.upload_timeout <= 0:
            raise ValueError("上传期限必须大于 0 秒")

    async def fill_article_body(self, page: Page):
        """经原生粘贴导入格式，再在各图片位置使用平台上传器插图，保留编辑器元数据。"""
        document = self.document
        insertions = []
        parts = []
        for part in document.parts:
            if isinstance(part, Path) or part == "<hr>":
                marker = f"SAU_ITEM_{uuid4().hex}"
                parts.append(marker)
                insertions.append((marker, part if isinstance(part, Path) else None))
            else:
                parts.append(part)
        # 平台把 section 改成 span、把 figure 放进 p，导致图片回调无法定位图片说明。
        # 这两种元素在主题中是布局容器；仅改为 div，保留主题内联样式和正文顺序。
        html = re.sub(r"<(\/?)(?:section|figure)(?=[\s>])", r"<\1div", "".join(parts), flags=re.I)
        await page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://mp.dayu.com")
        await page.evaluate("""async html => navigator.clipboard.write([
            new ClipboardItem({'text/html': new Blob([html], {type: 'text/html'})})
        ])""", html)
        # 正文位于独立 iframe，其可编辑 body 才是粘贴目标，不能在主文档查 contenteditable。
        body = page.frame_locator(ARTICLE_BODY).locator("body[contenteditable=true]")
        await expect(body).to_have_count(1, timeout=30000)
        await body.click()
        shortcut = "Meta" if sys.platform == "darwin" else "Control"
        await body.press(f"{shortcut}+A")
        await body.press(f"{shortcut}+V")
        await expect(body).to_contain_text(next(text.strip()[:30] for text in document.text if text.strip()))
        # 主题包含多层容器，粘贴后平台异步重建节点；过早选中标记会使插图位置失效。
        await page.locator("#title").click()
        await wait_dayu_article_body_stable(body)
        image_number = 0
        for marker, image_path in insertions:
            await expect(body).to_contain_text(marker)
            # 选中唯一图片标记；按键和 mouseup 刷新 UEditor 的选区缓存，工具栏才能替换正确位置。
            await body.evaluate("""(body, marker) => {
                body.focus(); const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
                let node;
                while (node = walker.nextNode()) {
                    const offset = node.textContent.indexOf(marker);
                    if (offset < 0) continue;
                    const range = document.createRange(); range.setStart(node, offset);
                    range.setEnd(node, offset + marker.length);
                    const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
                    return;
                }
                throw Error('正文中未找到本次图片位置标记');
            }""", marker)
            await body.press("Shift")
            await body.dispatch_event("mouseup")
            if image_path is None:
                # 原生粘贴会过滤 hr，使用页面本身的分隔线命令保留其发布语义。
                # 工具栏 datatitle 表达具体动作，不依赖图标样式和按钮序号。
                await page.locator('.edui-toolbar [datatitle="分隔线"]').click()
                await expect(body).not_to_contain_text(marker)
                continue
            # 用动作语义 datatitle 找插图工具；正文与封面共用弹窗，仅选择当前可见实例。
            await page.locator('.edui-toolbar [datatitle="插入图片"]').click()
            dialog = page.locator(".article-material-image-dialog:visible")
            # 本地上传 input 在打开弹窗后才生成；限定当前弹窗排除封面等隐藏上传器。
            upload = dialog.locator('input[type="file"]')
            await expect(upload).to_have_count(1)
            await upload.set_input_files(str(image_path))
            # chosen 是本次已选素材状态，结合文件名及远端 src 确认本次上传对象。
            chosen = dialog.locator(".article-material-localImage_list_item_chosen")
            await expect(chosen).to_have_count(1, timeout=self.upload_timeout * 1000)
            await expect(chosen.locator("p")).to_have_text(image_path.name)
            await expect(chosen.locator("img")).to_have_attribute("src", re.compile(r"^https://mp\.dayu\.com/dayu/image\?"))
            await dialog.get_by_role("button", name="确认", exact=True).click()
            await expect(dialog).to_have_count(0)
            await expect(body).not_to_contain_text(marker)
            image_number += 1
            await expect(body.locator("img")).to_have_count(image_number)
            # 插图逐张按正文顺序完成，已有图片数量已断言；序号对应本次插入的正文位置。
            await expect(body.locator("img").nth(image_number - 1)).to_have_attribute("data-infoed", "1")
            # data-infoed 后仍会异步补写图片说明并清理正文；这次清理会删除过早插入的 hr。
            # 先失焦并确认本次插图稳定，再处理后续分隔线/图片，不能仅等图片元数据出现。
            await page.locator("#title").click()
            await wait_dayu_article_body_stable(body)
            dayu_logger.info(f"大鱼号正文图片 {image_number}/{len(document.images)} 已插入: {image_path.name}")
        # 页面会异步规范化正文；必须在失焦并连续三次读回一致后核对，避免瞬时 DOM 误报成功。
        # 标题 ID 是正文外的实际表单字段，切换焦点不会提交或改变文章正文。
        await page.locator("#title").click()
        await wait_dayu_article_body_stable(body)
        # 独立核对文字和语义格式；不因粘贴成功就假设正文完整、样式保留。
        await check_dayu_article_content(body, document.manifest)
        self.publication_html = None
        self.style_result = {"mode": "native"}
        if re.search(r'\sstyle="[^\"]+"', document.content_html):
            # 编辑器和保存接口均会过滤 CSS；从原稿转换表现属性，图片沿用本次原生上传的元数据。
            images = await body.locator("img").evaluate_all("images => images.map(image => image.outerHTML)")
            compatible = await render_dayu_compatible_html(page, document.content_html, images)
            self.publication_html = compatible["html"]
            document.manifest["dayu_style"] = compatible["expectations"]
            self.style_result = {"mode": compatible["mode"], "limitations": compatible["limitations"],
                                 "preview_checked": False}
        for index in range(len(document.images)):
            await expect(body.locator("img").nth(index)).to_have_js_property("complete", True)
            if await body.locator("img").nth(index).evaluate("e => e.naturalWidth") <= 0:
                raise RuntimeError(f"正文第 {index + 1} 张图片无法加载")

    async def fill_article_form(self, page: Page):
        """正文、标题、作者及来源填写后逐项读回；作者缺省时沿用页面值。"""
        await self.fill_article_body(page)
        # title、author 是表单字段的语义 ID，避免把正文中的标题和作者文字当成输入控件。
        await page.locator("#title").fill(self.title)
        await expect(page.locator("#title")).to_have_value(self.title)
        if self.author is not None:
            await page.locator("#author input").fill(self.author)
            await expect(page.locator("#author input")).to_have_value(self.author)
        # 限定来源组件并按 radio 的业务 value 选择，避免其他单选组或选项顺序变化干扰。
        source = page.locator(f'.article-write-source-remark input[value="{self.source}"]')
        # 当前页 CSS 把透明 radio input 拉宽到 240px，指针中心会落到相邻选项；原生键盘选择不受影响。
        await source.focus()
        await source.press("Space")
        await expect(source).to_be_checked()
        # 条件原文链接没有独立语义 ID，使用字段 label 与同容器 input 的局部关系定位。
        original = page.locator(".article-write_box-form-filed").filter(
            has=page.locator("label").filter(has_text="原文链接"),
        ).locator('input[type="text"]')
        if self.source == DAYU_SOURCE_REPRINT:
            await original.fill(self.source_url)
            await expect(original).to_have_value(self.source_url)
        else:
            await expect(original).to_have_count(0)
        if self.cover_indices:
            mode = DAYU_ARTICLE_COVER_MODES[len(self.cover_indices)]
            # 封面模式限定横版封面组件并匹配选项文本，避免与竖版封面和来源单选组混淆。
            option = page.locator(".article-write-article-cover_normal-option").filter(has_text=mode)
            await option.locator(".w-radio").click()
            await expect(option.locator(".w-radio")).to_have_class(re.compile(r"w-radio_checked"))
            slots = page.locator(".article-write-article-cover_normal-item")
            await expect(slots).to_have_count(len(self.cover_indices))
            for slot_number, image_index in enumerate(self.cover_indices):
                # 槽位顺序对应用户给定的封面顺序；弹窗图片顺序对应正文图片顺序。
                await slots.nth(slot_number).locator(".article-write-article-cover-cover-item").click()
                dialog = page.locator(".article-material-image-dialog:visible")
                choices = dialog.locator(".article-material-image_image-choose img")
                await expect(choices).to_have_count(len(self.document.images))
                await choices.nth(image_index - 1).click()
                await expect(dialog.locator(".article-material-image_image-choose .chosen")).to_have_count(1)
                await dialog.get_by_role("button", name="下一步", exact=True).click()
                await expect(dialog.get_by_role("button", name="保存", exact=True)).to_be_visible()
                await dialog.get_by_role("button", name="保存", exact=True).click()
                await expect(dialog).to_have_count(0, timeout=30000)
                preview = slots.nth(slot_number).locator("img")
                await expect(preview).to_have_count(1)
                await expect(preview).to_have_attribute("src", re.compile(r"^https?://image\.uc\.cn/"))
        await fill_dayu_schedule(page, self.schedule)

    async def main(self) -> dict:
        """核对编辑器内容并提交发表，平台确认本次作品 ID 后即成功。"""
        self.validate_upload_args()
        expected = load_dayu_identity(self.account_file)
        results_dir = self.account_file.parent / "dayu_results"
        results_dir.mkdir(exist_ok=True)
        result_file = results_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.json"
        result = {"success": False, "status": "preparing", "type": "article", "title": self.title,
                  "content_file": str(self.content_file), "identity": expected,
                  "manifest": self.document.manifest, "result_file": str(result_file)}
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
                await page.goto(DAYU_ARTICLE_URL, wait_until="domcontentloaded", timeout=45000)
                identity = await read_dayu_identity(page)
                if identity["wmid"] != expected["wmid"]:
                    raise RuntimeError("大鱼号主体不匹配，图文上传已中止")
                result["identity"] = identity
                await self.fill_article_form(page)
                result.update(source_format=self.document.source_format, theme=self.document.theme,
                              style_check=self.style_result)
                if (await read_dayu_identity(page))["wmid"] != identity["wmid"]:
                    raise RuntimeError("填表期间大鱼号主体发生变化，拒绝发表")
                if self.prepare_only:
                    await page.screenshot(path=str(result_file.with_suffix(".png")), full_page=True)
                    result.update(success=True, status="prepared")
                    return result
                await submit_dayu_publication(page, result, result_file, article_html=self.publication_html)
                await context.storage_state(path=str(self.account_file))
                action = "定时发布已安排" if self.schedule else "发表成功"
                dayu_logger.success(f"大鱼号图文{action}: {result['content_id']}")
                return result
            except Exception as exc:
                result["error"] = str(exc)
                dayu_logger.error(f"大鱼号图文阶段={result['status']}，结果文件={result_file}: {exc}")
                if self.debug and page is not None:
                    await page.screenshot(path=str(result_file.with_suffix(".png")))
                raise
            finally:
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                await browser.close()
