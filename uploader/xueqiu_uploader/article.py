"""雪球长文：结构化原稿、原位置插图、封面、预览与单次发表。"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from patchright.async_api import Page, async_playwright, expect

from conf import LOCAL_CHROME_PATH
from uploader.xueqiu_uploader.constants import (
    XUEQIU_ARTICLE_URL, XUEQIU_DECLARATIONS, XUEQIU_IMAGE_SUFFIXES, XUEQIU_VISIBILITY,
)
from uploader.xueqiu_uploader.session import load_xueqiu_identity, read_xueqiu_identity
from uploader.xueqiu_uploader.content import load_xueqiu_article
from uploader.xueqiu_uploader.verification import check_xueqiu_article_content, query_xueqiu_article


class XueqiuArticle:
    """通过原生粘贴与图片上传保留文章结构，以服务端确认作为发表结果。"""

    def __init__(self, title, content_file, account_file, visibility="公开",
                 declaration="不添加创作声明", prepare_only=False, headless=False, debug=False,
                 cover=None):
        self.title = title.strip()
        self.content_file = Path(content_file).expanduser().resolve()
        self.account_file = Path(account_file).resolve()
        self.visibility = visibility
        self.declaration = declaration
        self.prepare_only = prepare_only
        self.headless = headless
        self.debug = debug
        self.cover = Path(cover).expanduser().resolve() if cover else None

    def validate_upload_args(self):
        """所有本地参数在创建远端草稿前校验，不猜测尚未观察到的长度上限。"""
        if not self.title or "\n" in self.title or "\r" in self.title:
            raise ValueError("雪球标题必须为非空单行文字")
        self.document = load_xueqiu_article(self.content_file)
        if self.visibility not in XUEQIU_VISIBILITY:
            raise ValueError(f"分享范围必须为: {', '.join(XUEQIU_VISIBILITY)}")
        if self.declaration not in XUEQIU_DECLARATIONS:
            raise ValueError(f"创作声明必须为: {', '.join(XUEQIU_DECLARATIONS)}")
        for image in self.document.images + ([self.cover] if self.cover else []):
            if image.suffix.lower() not in XUEQIU_IMAGE_SUFFIXES:
                raise ValueError(f"雪球图片支持: {', '.join(XUEQIU_IMAGE_SUFFIXES)}")
            if not image.is_file():
                raise FileNotFoundError(f"图片不存在: {image}")
            if image.stat().st_size == 0:
                raise ValueError(f"图片不能为空: {image}")
        if not self.account_file.is_file():
            raise FileNotFoundError("请先执行 sau xueqiu login 保存账号")
        self.identity = load_xueqiu_identity(self.account_file)

    async def fill_article_body(self, page, body):
        """在原稿图片位置放置唯一标记，原生上传后再核对完整图文交错顺序。"""
        parts = []
        insertions = []
        for part in self.document.parts:
            if isinstance(part, Path):
                marker = f"SAU_IMAGE_{uuid4().hex}"
                parts.append(marker)
                insertions.append((marker, part))
            else:
                parts.append(part)
        await page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://mp.xueqiu.com")
        await page.evaluate("""async html => navigator.clipboard.write([
            new ClipboardItem({'text/html': new Blob([html], {type: 'text/html'})})
        ])""", "".join(parts))
        await body.click()
        await body.press("Meta+V" if sys.platform == "darwin" else "Control+V")
        # 标题字段用于失焦；等待本次末尾文字实际进入模型，再开始选择图片标记。
        await page.get_by_placeholder("请输入标题", exact=True).click()
        for marker, _ in insertions:
            await expect(body).to_contain_text(marker)
        self.uploaded_images = []
        for index, (marker, image) in enumerate(insertions):
            # 在正文实际文本节点选择唯一标记；使用原生选区而非改写 ProseMirror innerHTML。
            # 实测该选区经 Shift 刷新后会被工具栏上传替换，后续段落保持原位。
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
                throw Error('找不到本次原稿图片位置标记');
            }""", marker)
            await body.press("Shift")
            # data-tip 是实测上传动作语义；限定 snb_toolbar 排除独立封面 input。
            async with page.expect_file_chooser() as chooser:
                await page.locator('#snb_toolbar [data-tip="上传图片"]').click()
            file_chooser = await chooser.value
            # input 保留旧文件；只清空原生值而不派发空 change，允许相同文件在不同原稿位置出现。
            await file_chooser.element.evaluate("input => { input.value = ''; }")
            await file_chooser.set_files(str(image))
            await expect(body).not_to_contain_text(marker)
            await expect(body.locator("img")).to_have_count(index + 1, timeout=60000)
            # 图片按原稿顺序逐个替换，已断言数量；data/blob 预览不代表服务端完成。
            inserted = body.locator("img").nth(index)
            await expect(inserted).to_have_attribute("src", re.compile(r"^(?:https:)?//xqimg\.imedao\.com/"), timeout=60000)
            await expect(inserted).to_have_js_property("complete", True, timeout=60000)
            if await inserted.evaluate("e => e.naturalWidth") <= 0:
                raise RuntimeError(f"正文图片无法加载: {image.name}")
            self.uploaded_images.append(await inserted.evaluate("e => e.src"))
        await page.get_by_placeholder("请输入标题", exact=True).click()
        await check_xueqiu_article_content(body, self.document)

    async def fill_article_form(self, page: Page):
        """按真实字段填写、读回选项和正文，再独立检查预览与自动保存。"""
        # 标题占位符表达字段职责；正文 placeholder 在输入后消失，使用 editor 直属可编辑节点，
        # 排除上传图片内部 contenteditable=false 的工具容器，填表前后使用同一定位器。
        title = page.get_by_placeholder("请输入标题", exact=True)
        body = page.locator('#editor > [contenteditable="true"]')
        await expect(title).to_have_count(1)
        await expect(body).to_have_count(1)
        # 新任务只写空编辑器；页面若恢复已有草稿，不覆盖用户原文。
        if (await title.input_value()).strip() or (await body.inner_text()).strip() or await body.locator("img").count():
            raise RuntimeError("雪球编辑器已有内容，拒绝覆盖；请先处理现有草稿")
        await title.fill(self.title)
        await expect(title).to_have_value(self.title)
        await self.fill_article_body(page, body)
        self.cover_url = None
        if self.cover:
            # 封面字段行以 label 限域，input 的 type 表达上传用途，不与工具栏正文上传器混用。
            cover_row = page.locator('div[class*="index_sectionFlex_"]').filter(
                has=page.get_by_text("封面图片：", exact=True),
            )
            await cover_row.locator('input[type="file"]').set_input_files(str(self.cover))
            # 实测封面必须经过独立裁剪弹窗；保留默认裁剪框，不猜测尺寸或操作隐藏状态。
            crop = page.locator('div[class*="modal_modal-content_"]').filter(
                has=page.get_by_text("选择封面图片", exact=True),
            )
            await expect(crop).to_be_visible()
            await expect(crop.locator('img[alt="Crop"]')).to_have_js_property("complete", True)
            if await crop.locator('img[alt="Crop"]').evaluate("e => e.naturalWidth") <= 0:
                raise RuntimeError("封面裁剪预览无法加载")
            await crop.get_by_role("button", name="确认裁剪", exact=True).click()
            await expect(crop).to_have_count(0, timeout=60000)
            # 实测成功封面以背景图展示，原上传按钮被 hidden；不能检查占位 img 的固定地址。
            cover_preview = cover_row.locator('div[class*="index_input-cover-pic-btn_"]')
            await expect(cover_preview).to_have_attribute("style", re.compile(r".*xqimg\.imedao\.com/.*"), timeout=60000)
            self.cover_url = await cover_preview.evaluate(
                "e => new URL(getComputedStyle(e).backgroundImage.slice(5, -2), location.href).href")
        for label, value in (("分享范围：", self.visibility), ("创作声明：", self.declaration)):
            # class 仅保留字段行和组件职责前缀；以本行 label 限域，排除另一组同构下拉菜单。
            row = page.locator('div[class*="index_sectionFlex_"]').filter(
                has=page.get_by_text(label, exact=True),
            )
            selected = row.locator('div[class*="index_selectWrap_"]')
            await selected.click()
            # optionContainer 是展开选项容器；visible 排除当前未展开的另一菜单。
            option = row.locator('div[class*="index_optionContainer_"]:visible').get_by_text(value, exact=True)
            await expect(option).to_have_count(1)
            await option.click()
            await expect(selected).to_contain_text(value)
        # publish_state 是独立自动保存状态区域，不以正文里的同名文字判断保存完成。
        await expect(page.locator('div[class*="publish_state_"]')).to_contain_text("已经保存至草稿", timeout=60000)
        await page.get_by_role("button", name="预览", exact=True).click()
        # 预览容器的业务前缀在实测 DOM 中稳定；h1 与 content-text 分别承载预览标题、正文。
        preview = page.locator('div[class*="index_preview-content_"]')
        await expect(preview).to_be_visible()
        await expect(preview.locator("h1")).to_have_text(self.title)
        # 预览由异步服务端结果填入，先等本次文字，不能只等空预览外壳可见。
        preview_body = preview.locator('div[class*="index_content-text_"] > div')
        await expect(preview_body).to_contain_text(next(text.strip() for text in self.document.text if text.strip()), timeout=30000)
        await check_xueqiu_article_content(preview_body, self.document)
        # 预览 content-text 直属封面 img 与直属 div 内的正文图片并存；只在后者核对插图。
        preview_images = preview.locator('div[class*="index_content-text_"] > div img')
        await expect(preview_images).to_have_count(len(self.uploaded_images))
        for index, source in enumerate(self.uploaded_images):
            # 平台预览会给 // 地址补 https；比较解析后的 src，并按正文顺序排除错图或重排。
            await expect(preview_images.nth(index)).to_have_js_property("src", source)
            await expect(preview_images.nth(index)).to_have_js_property("complete", True)
            if await preview_images.nth(index).evaluate("e => e.naturalWidth") <= 0:
                raise RuntimeError(f"预览中第 {index + 1} 张正文图片无法加载")
        if self.cover_url:
            # 实测 index_first-pic 是预览直属封面，独立于正文 div，核对本次裁剪结果。
            cover_image = preview.locator('div[class*="index_content-text_"] > img[class*="index_first-pic_"]')
            await expect(cover_image).to_have_js_property("src", self.cover_url)
            await expect(cover_image).to_have_js_property("complete", True)
            if await cover_image.evaluate("e => e.naturalWidth") <= 0:
                raise RuntimeError("预览中的封面无法加载")
        if (await read_xueqiu_identity(page))["uid"] != self.identity["uid"]:
            raise RuntimeError("雪球填写期间账号发生变化，已中止")

    async def main(self) -> dict:
        """准备模式保留草稿和预览；提交模式只点击一次，结果未知时禁止自动重发。"""
        self.validate_upload_args()
        results_dir = self.account_file.parent / "xueqiu_results"
        results_dir.mkdir(exist_ok=True)
        result_file = results_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.json"
        result = {"success": False, "status": "preparing", "title": self.title,
                  "content_file": str(self.content_file),
                  "identity": self.identity, "visibility": self.visibility, "declaration": self.declaration,
                  "result_file": str(result_file), "remote_draft_possible": False}
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=self.headless,
            )
            page = None
            try:
                context = await browser.new_context(storage_state=str(self.account_file))
                page = await context.new_page()
                response = await page.goto(XUEQIU_ARTICLE_URL, wait_until="domcontentloaded", timeout=45000)
                if response is not None and response.status >= 400:
                    raise RuntimeError(f"雪球编辑器访问失败，HTTP {response.status}")
                if (await read_xueqiu_identity(page))["uid"] != self.identity["uid"]:
                    raise RuntimeError("雪球主体与绑定账号不一致")
                result["remote_draft_possible"] = True
                await self.fill_article_form(page)
                result.update(images=self.uploaded_images, cover=self.cover_url,
                              source_format=self.document.source_format, normalizations=self.document.normalizations,
                              manifest=self.document.manifest)
                await page.screenshot(path=str(result_file.with_suffix(".png")), full_page=True)
                result["screenshot"] = str(result_file.with_suffix(".png"))
                if self.prepare_only:
                    result.update(success=True, status="prepared", url=page.url)
                    return result
                # index_preview_ 是预览遮罩，直接子级 index_close_ 是实测关闭控件；不删除遮罩或强制点击。
                await page.locator('div[class*="index_preview_"] > div[class*="index_close_"]').click()
                # 关闭后组件仍保留在 DOM，由父层隐藏；不能要求节点被删除。
                await expect(page.locator('div[class*="index_preview-content_"]')).to_be_hidden()
                publish = page.get_by_role("button", name="发布", exact=True)
                # 页面用 class 表达禁用态，不能仅依赖 HTML disabled；保留语义前缀排除哈希变化。
                await expect(publish).not_to_have_class(re.compile(r".*publish_disabled_.*"), timeout=30000)
                result.update(status="submission_unknown", editor_url=page.url)
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                # 实测最终发表 POST /xq/statuses/update.json 返回作品 ID、user_id、title、text、is_private。
                # 页面随后回首页，因此不能用“跳转作者详情”这一错误假设判断成功。
                async with page.expect_response(lambda response: response.request.method == "POST"
                                                and response.url == "https://mp.xueqiu.com/xq/statuses/update.json",
                                                timeout=60000) as submitted:
                    await publish.click()
                response = await submitted.value
                payload = await response.json()
                content_id = payload.get("id")
                if not response.ok or not isinstance(content_id, int) or isinstance(content_id, bool) or content_id <= 0:
                    raise RuntimeError(f"雪球未确认受理: HTTP {response.status}，{payload.get('error_description', payload.get('error_code', '缺少作品 ID'))}")
                # 先持久化已返回的 ID，即使后续内容核对异常也只能查询原作品，禁止重发。
                result["content_id"] = str(content_id)
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                if str(payload.get("user_id")) != self.identity["uid"] or payload.get("title") != self.title:
                    raise RuntimeError("雪球受理作品的主体或标题不符，请核查原作品")
                if payload.get("is_private") is not (self.visibility == "私人"):
                    raise RuntimeError("雪球受理作品的分享范围不符，请核查原作品")
                # 用平台返回的已发表正文创建独立页面核对，不改写编辑器模型，也不追加真实发表动作。
                check_page = await context.new_page()
                await check_page.set_content(payload.get("text") or "")
                await check_xueqiu_article_content(check_page.locator("body"), self.document, self.uploaded_images)
                result.update(success=True, status="published",
                              url=f"https://xueqiu.com/{self.identity['uid']}/{content_id}")
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                # 发表响应已确认受理；再查已发布原 ID，核验不能误触发第二次提交。
                record = await query_xueqiu_article(page, self.identity, content_id, self.title, self.visibility)
                await check_page.set_content(record.get("text") or "")
                await check_xueqiu_article_content(check_page.locator("body"), self.document, self.uploaded_images)
                await check_page.close()
                result["management_verified"] = True
                await page.screenshot(path=str(result_file.with_suffix(".published.png")), full_page=True)
                result["published_screenshot"] = str(result_file.with_suffix(".published.png"))
                await context.storage_state(path=str(self.account_file))
                return result
            except Exception as exc:
                result["error"] = str(exc)
                if result["status"] == "preparing":
                    result["status"] = "failed"
                if self.debug and page is not None:
                    await page.screenshot(path=str(result_file.with_suffix(".error.png")), full_page=True)
                raise
            finally:
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"雪球操作结果: {result_file}", flush=True)
                await browser.close()
