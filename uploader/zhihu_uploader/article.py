"""知乎文章发布：正文文本、正文图片、定时设置和提交结果记录。"""
from __future__ import annotations

import base64
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from patchright.async_api import Page, async_playwright, expect

from conf import LOCAL_CHROME_PATH
from utils.article_render import load_article, ARTICLE_MARKDOWN_EXTENSIONS
from uploader.zhihu_uploader.constants import (
    ZHIHU_ARTICLE_TITLE_MAX, ZHIHU_ARTICLE_URL, ZHIHU_IMAGE_EXTENSIONS, ZHIHU_TIMEZONE,
)
from uploader.zhihu_uploader.schedule import fill_zhihu_article_schedule, validate_zhihu_schedule
from uploader.zhihu_uploader.session import load_zhihu_identity, read_zhihu_identity


class ZhihuArticle:
    """按原稿结构导入正文，在原稿位置上传图片，核对后只发表一次。"""

    def __init__(self, title, content_file, account_file, schedule=None,
                 headless=True, debug=False, prepare_only=False, upload_timeout=600):
        self.title = title
        self.content_file = Path(content_file).expanduser().resolve()
        self.account_file = Path(account_file).resolve()
        self.schedule = schedule
        self.headless = headless
        self.debug = debug
        self.prepare_only = prepare_only
        self.upload_timeout = upload_timeout

    def validate_upload_args(self) -> None:
        """在启动浏览器前检查标题、正文、图片及定时时间。"""
        if not self.title.strip() or len(self.title) > ZHIHU_ARTICLE_TITLE_MAX:
            raise ValueError(f"知乎文章标题需为 1–{ZHIHU_ARTICLE_TITLE_MAX} 字")
        self.document = load_article(
            self.content_file, "plain" if self.content_file.suffix.lower() in ARTICLE_MARKDOWN_EXTENSIONS else None,
        )
        self.images = self.document.images
        if not "".join(self.document.text).strip():
            raise ValueError("知乎文章正文不能为空")
        if not self.account_file.is_file():
            raise FileNotFoundError("请先执行 sau zhihu login 保存账号")
        self.identity = load_zhihu_identity(self.account_file)
        self.schedule = validate_zhihu_schedule(self.schedule)
        if self.upload_timeout <= 0:
            raise ValueError("上传期限必须大于 0 秒")
        for image in self.images:
            if not image.is_file():
                raise FileNotFoundError(f"知乎正文图片不存在: {image}")
            if image.suffix.lower() not in ZHIHU_IMAGE_EXTENSIONS:
                raise ValueError(f"知乎文章图片格式不支持: {image.suffix}")

    async def fill_article_form(self, page: Page) -> None:
        """通过原生粘贴导入富文本；按原稿位置上传图片并核对交错顺序。"""
        # 标题 placeholder 来自文章表单的实际 textarea，避免误填正文和搜索框。
        title = page.locator('textarea[placeholder="请输入标题（最多 100 个字）"]')
        await expect(title).to_have_count(1)
        body = page.locator('div[contenteditable="true"][role="textbox"]')
        await expect(body).to_have_count(1)
        # 知乎编辑器会自动保存；新任务只写空编辑器，避免覆盖账号中恢复出的旧草稿。
        if ((await title.input_value()).strip() or (await body.inner_text()).strip()
                or await body.locator("img").count()):
            raise RuntimeError("知乎文章编辑器已有草稿内容，拒绝覆盖；请先处理该草稿")
        await title.fill(self.title)
        await expect(title).to_have_value(self.title)
        # 不改写 DraftJS innerHTML；原生 HTML 粘贴使编辑器自己更新内部模型。
        # 图片先替换成唯一标记，避免把本地路径粘贴为无法加载的远端图片。
        parts, insertions = [], []
        for part in self.document.parts:
            if isinstance(part, Path):
                marker = f"SAU_IMAGE_{uuid4().hex}"
                parts.append(marker)
                insertions.append((marker, part))
            else:
                parts.append(part)
        await page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://zhuanlan.zhihu.com")
        await page.evaluate("""async html => navigator.clipboard.write([
            new ClipboardItem({'text/html': new Blob([html], {type: 'text/html'})})
        ])""", "".join(parts))
        await body.click()
        await body.press("Meta+V" if sys.platform == "darwin" else "Control+V")
        await title.click()
        for marker, _ in insertions:
            await expect(body).to_contain_text(marker)
        self.uploaded_images = []
        for index, (marker, image) in enumerate(insertions, 1):
            # 文本节点中的唯一标记确定原稿图片位置，不能用点击正文后默认光标位置代替。
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
                throw Error('找不到原稿图片位置标记');
            }""", marker)
            await body.press("Shift")
            await body.press("Backspace")
            await expect(body).not_to_contain_text(marker)
            # 当前文章编辑器实测支持图片剪贴板粘贴，图片按钮则先打开素材面板。
            # 在已确认的原稿光标位置粘贴，让 DraftJS 自行创建图片块及发起上传。
            # 浏览器 ClipboardItem 支持 PNG；其他格式继续使用原生文件 input。
            if image.suffix.lower() == ".png":
                await page.evaluate("""async encoded => {
                    const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
                    await navigator.clipboard.write([
                        new ClipboardItem({'image/png': new Blob([bytes], {type: 'image/png'})})
                    ]);
                }""", base64.b64encode(image.read_bytes()).decode("ascii"))
                await body.press("Meta+V" if sys.platform == "darwin" else "Control+V")
            else:
                # accept/multiple 排除封面和文档导入 input，非 PNG 路径仍待真实上传验证。
                image_input = page.locator('input[type="file"][accept^="image/webp"][multiple]')
                await expect(image_input).to_have_count(1)
                await image_input.evaluate("input => { input.value = ''; }")
                await image_input.set_input_files(str(image))
            await expect(body.locator("img")).to_have_count(index, timeout=self.upload_timeout * 1000)
            # 已断言图片数量，按本次逐张插入顺序核对服务器地址和实际解码状态。
            inserted = body.locator("img").nth(index - 1)
            await expect(inserted).to_have_attribute("src", re.compile(r"^https://"), timeout=self.upload_timeout * 1000)
            await expect(inserted).to_have_js_property("complete", True, timeout=self.upload_timeout * 1000)
            if await inserted.evaluate("image => image.naturalWidth") <= 0:
                raise RuntimeError(f"知乎文章第 {index} 张图片无法加载")
            self.uploaded_images.append(await inserted.get_attribute("src"))
        await title.click()
        sources = await body.locator("img").evaluate_all("images => images.map(image => image.getAttribute('src'))")
        if sources != self.uploaded_images:
            raise RuntimeError("知乎文章图片被重排或替换，停止提交")
        await self.check_article_body(body)

        await fill_zhihu_article_schedule(page, self.schedule)

    async def check_article_body(self, body) -> None:
        """核对全部文字、段间图片位置和基本格式，平台过滤或重排时中止提交。"""
        # 知乎 DraftJS 实测将行内加粗/斜体写为带样式的 span，不能只数 strong/em 标签。
        actual = await body.evaluate(r"""body => {
            let sequence = '';
            function visit(node) {
                if (node.nodeType === Node.TEXT_NODE) { sequence += node.nodeValue; return; }
                if (node.nodeName === 'IMG') { sequence += '\x00IMG\x00'; return; }
                node.childNodes.forEach(visit);
            }
            visit(body);
            return {sequence, formats: Object.fromEntries(
                ['h1','h2','h3','h4','h5','h6','strong','em','ul','ol','blockquote','pre'].map(
                    tag => [tag, tag === 'strong'
                        ? body.querySelectorAll('strong,b,span[style*="font-weight: bold"],span[style*="font-weight: 700"]').length
                        : tag === 'em' ? body.querySelectorAll('em,i,span[style*="font-style: italic"]').length
                        : body.querySelectorAll(tag).length]
                )), links: [...body.querySelectorAll('a')].map(a => [a.textContent, a.getAttribute('href')])};
        }""")
        normalize = lambda text: re.sub(r"[\s\u200b\ufeff]+", "", text)
        if normalize(actual["sequence"]) != normalize("".join(self.document.sequence)):
            raise RuntimeError("知乎文章文字或段间图片位置与原稿不一致，停止提交")
        for tag, count in actual["formats"].items():
            if count != self.document.tags[tag]:
                raise RuntimeError(f"知乎文章格式不一致: {tag} 期望 {self.document.tags[tag]}，实际 {count}")
        expected_links = await body.page.evaluate("""html => {
            const template = document.createElement('template'); template.innerHTML = html;
            return [...template.content.querySelectorAll('a')].map(a => [a.textContent, a.getAttribute('href')]);
        }""", self.document.content_html)
        if [[normalize(text), href] for text, href in actual["links"]] != [[normalize(text), href] for text, href in expected_links]:
            raise RuntimeError("知乎文章链接文字或目标与原稿不一致")

    async def main(self) -> dict:
        """仅以作品详情 URL 作为已发表证据；提交响应未知时禁止自动重试。"""
        self.validate_upload_args()
        results_dir = self.account_file.parent / "zhihu_results"
        results_dir.mkdir(exist_ok=True)
        result_file = results_dir / f"{datetime.now(ZHIHU_TIMEZONE):%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.json"
        result = {
            "success": False, "status": "preparing", "type": "article", "title": self.title,
            "content_file": str(self.content_file), "images": [str(image) for image in self.images],
            "identity": self.identity, "result_file": str(result_file),
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
                response = await page.goto(ZHIHU_ARTICLE_URL, wait_until="domcontentloaded", timeout=45000)
                if response is not None and response.status >= 400:
                    raise RuntimeError(f"知乎文章编辑器访问失败，HTTP {response.status}")
                if await read_zhihu_identity(page) != self.identity:
                    raise RuntimeError("知乎文章编辑器页头与本地账号绑定不一致")
                await self.fill_article_form(page)
                result.update(images=self.uploaded_images, manifest=self.document.manifest)
                result["status"] = "prepared"
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                if self.prepare_only:
                    return result

                # 发布按钮只有标题和正文满足编辑器要求后才可用；提交只触发一次。
                publish = page.get_by_role("button", name="发布", exact=True)
                await expect(publish).to_be_enabled()
                submitted = True
                result["status"] = "submission_unknown"
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                await publish.click()
                # 草稿也有 /p/<id>/edit 地址；必须到正式详情页并读到作品标题才算发表。
                await page.wait_for_url(re.compile(r"^https://zhuanlan\.zhihu\.com/p/\d+/?(?:\?.*)?$"), timeout=60000)
                await expect(page.get_by_role("article").get_by_role("heading", name=self.title, exact=True)).to_be_visible()
                result.update(success=True, status="published", url=page.url)
                return result
            except Exception as exc:
                result["error"] = str(exc)
                if submitted:
                    result["status"] = "submission_unknown"
                    if page is not None and re.fullmatch(r"https://zhuanlan\.zhihu\.com/p/\d+/?(?:\?.*)?", page.url):
                        result["url"] = page.url
                else:
                    result["status"] = "failed_before_submit"
                if self.debug and page is not None:
                    screenshot = result_file.with_suffix(".png")
                    await page.screenshot(path=str(screenshot))
                    result["screenshot"] = str(screenshot)
                raise RuntimeError(f"知乎文章阶段={result['status']}，结果文件={result_file}: {exc}") from exc
            finally:
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                await browser.close()
