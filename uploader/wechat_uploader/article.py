"""微信公众号图文发布：标题、摘要、正文、封面与多步发表确认。

微信公众号正文编辑器（UEditor / ProseMirror）会过滤外部样式，且发表前需要连过
创作来源声明、发表方式、群发确认和管理员扫码验证。扫码验证只能由账号管理员
本人完成，本模块在检测到验证二维码后暂停并明确提示，不代劳、不绕过。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from patchright.async_api import Page, async_playwright, expect

from utils.article_render import load_article
from uploader.wechat_uploader.constants import (
    WECHAT_ARTICLE_PATH, WECHAT_ARTICLE_TITLE_MAX, WECHAT_AUTHOR_MAX,
    WECHAT_DIGEST_MAX, WECHAT_IMAGE_SUFFIXES, WECHAT_TIMEZONE, WECHAT_ORIGINALITY,
)
from uploader.wechat_uploader.session import (
    browser_launch_kwargs, load_wechat_identity, read_wechat_identity, read_wechat_token,
)


TITLE_EDITOR = '.title-editor__input .ProseMirror, #title-editor .ProseMirror, .title-editor__input'
BODY_EDITOR = '#ueditor_0 .ProseMirror, .ProseMirror[contenteditable="true"]'
DIGEST_INPUT = '#js_description'


def build_article_url(token: str) -> str:
    """用当前会话 token 构造新建图文地址。"""
    return (f"https://mp.weixin.qq.com{WECHAT_ARTICLE_PATH}"
            f"?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77"
            f"&createType=0&token={token}&lang=zh_CN")


class WechatArticle:
    """按原稿填写图文并核对；发表只触发一次，扫码验证交给管理员。"""

    def __init__(self, title, content_file, account_file, digest=None, author=None,
                 cover=None, originality="none", broadcast=True, prepare_only=False,
                 headless=False, debug=False, qr_timeout=600):
        self.title = title
        self.content_file = Path(content_file).expanduser().resolve()
        self.account_file = Path(account_file).resolve()
        self.digest = digest
        self.author = author
        self.cover = Path(cover).expanduser().resolve() if cover else None
        self.originality = originality
        self.broadcast = broadcast
        self.prepare_only = prepare_only
        self.headless = headless
        self.debug = debug
        self.qr_timeout = qr_timeout

    def validate_upload_args(self) -> None:
        """启动浏览器前检查标题、正文、封面、账号与选项。"""
        if not self.title.strip() or len(self.title) > WECHAT_ARTICLE_TITLE_MAX:
            raise ValueError(f"微信公众号文章标题需为 1–{WECHAT_ARTICLE_TITLE_MAX} 字")
        if self.digest is not None and len(self.digest) > WECHAT_DIGEST_MAX:
            raise ValueError(f"微信公众号摘要最多 {WECHAT_DIGEST_MAX} 字")
        if self.author is not None and len(self.author) > WECHAT_AUTHOR_MAX:
            raise ValueError(f"微信公众号作者最多 {WECHAT_AUTHOR_MAX} 字")
        if self.originality not in WECHAT_ORIGINALITY:
            raise ValueError(f"创作来源声明必须为: {', '.join(WECHAT_ORIGINALITY)}")
        if self.qr_timeout <= 0:
            raise ValueError("扫码验证期限必须大于 0 秒")
        self.document = load_article(self.content_file)
        if not "".join(self.document.text).strip():
            raise ValueError("微信公众号文章正文不能为空")
        if not self.account_file.is_file():
            raise FileNotFoundError("请先执行 sau wechat login 保存账号")
        self.identity = load_wechat_identity(self.account_file)
        if self.cover is not None:
            if not self.cover.is_file():
                raise FileNotFoundError(f"封面图片不存在: {self.cover}")
            if self.cover.suffix.lower() not in WECHAT_IMAGE_SUFFIXES:
                raise ValueError(f"封面图片格式不支持: {self.cover.suffix}")
        for image in self.document.images:
            if not image.is_file():
                raise FileNotFoundError(f"正文图片不存在: {image}")
            if image.suffix.lower() not in WECHAT_IMAGE_SUFFIXES:
                raise ValueError(f"正文图片格式不支持: {image.suffix}")

    async def fill_article_form(self, page: Page) -> None:
        """填写标题、摘要与正文；图片按原稿位置逐个上传。"""
        title = page.locator(TITLE_EDITOR).first
        await expect(title).to_be_visible(timeout=30000)
        await title.click()
        await title.press("ControlOrMeta+A")
        await title.fill(self.title)
        await expect(page.locator('#title, input[name="title"]').first).to_have_value(
            self.title, timeout=15000)

        if self.digest:
            digest = page.locator(DIGEST_INPUT)
            await expect(digest).to_have_count(1)
            await digest.fill(self.digest)
            await expect(digest).to_have_value(self.digest)
        if self.author:
            author = page.locator('#author')
            if await author.count():
                await author.fill(self.author)

        body = page.locator(BODY_EDITOR).first
        await expect(body).to_be_visible(timeout=30000)
        await body.click()
        await body.press("ControlOrMeta+A")
        # clipboard HTML 粘贴让编辑器自行建模，保留标题、加粗、链接与图片位置。
        parts, insertions = [], []
        for part in self.document.parts:
            if isinstance(part, Path):
                marker = f"SAU_WX_IMAGE_{uuid4().hex}"
                parts.append(marker)
                insertions.append((marker, part))
            else:
                parts.append(part)
        await page.context.grant_permissions(
            ["clipboard-read", "clipboard-write"], origin="https://mp.weixin.qq.com")
        await page.evaluate("""async html => navigator.clipboard.write([
            new ClipboardItem({'text/html': new Blob([html], {type: 'text/html'})})
        ])""", "".join(parts))
        await body.press("ControlOrMeta+V")

        self.uploaded_images = []
        for index, (marker, image) in enumerate(insertions, 1):
            await expect(body).to_contain_text(marker, timeout=15000)
            await body.evaluate("""(body, marker) => {
                body.focus(); const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
                let node;
                while (node = walker.nextNode()) {
                    const offset = node.textContent.indexOf(marker);
                    if (offset < 0) continue;
                    const range = document.createRange();
                    range.setStart(node, offset);
                    range.setEnd(node, offset + marker.length);
                    const selection = getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    return;
                }
                throw Error('找不到原稿图片位置标记');
            }""", marker)
            if image.suffix.lower() == ".png":
                import base64
                await page.evaluate("""async encoded => {
                    const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
                    await navigator.clipboard.write([
                        new ClipboardItem({'image/png': new Blob([bytes], {type: 'image/png'})})
                    ]);
                }""", base64.b64encode(image.read_bytes()).decode("ascii"))
                await body.press("ControlOrMeta+A")
                # 撤销全选对正文的影响：重新把光标放回标记处再粘贴。
                await body.evaluate("""(body, marker) => {
                    const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
                    let node;
                    while (node = walker.nextNode()) {
                        const offset = node.textContent.indexOf(marker);
                        if (offset < 0) continue;
                        const range = document.createRange();
                        range.setStart(node, offset);
                        range.setEnd(node, offset + marker.length);
                        const selection = getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                        return;
                    }
                }""", marker)
                await body.press("Backspace")
                await body.press("ControlOrMeta+V")
            else:
                image_input = page.locator('input[type="file"][accept*="image"]').last
                await image_input.set_input_files(str(image))
            await expect(body).not_to_contain_text(marker, timeout=30000)
            self.uploaded_images.append(str(image))

        await self.verify_form(page, title, body)

    async def verify_form(self, page: Page, title, body) -> None:
        """提交前核对标题、摘要和正文首段，防止粘贴丢失或串位。"""
        actual_title = await page.locator('#title, input[name="title"]').first.input_value()
        if actual_title.strip() != self.title:
            raise RuntimeError("微信公众号标题与本地稿不一致，停止提交")
        body_text = (await body.inner_text()).strip()
        first_text = next((text.strip() for text in self.document.text if text.strip()), "")
        if not first_text or first_text[:12] not in body_text:
            raise RuntimeError("微信公众号正文首段未正确写入，停止提交")
        if self.digest:
            actual_digest = await page.locator(DIGEST_INPUT).input_value()
            if actual_digest.strip() != self.digest.strip():
                raise RuntimeError("微信公众号摘要与本地稿不一致，停止提交")
        if await read_wechat_identity(page) != self.identity:
            raise RuntimeError("微信公众号填写期间账号发生变化，已中止")

    async def upload_cover(self, page: Page) -> None:
        """通过图片库上传独立封面；封面为可选项，失败时明确报错。"""
        if self.cover is None:
            return
        # 封面 "+" 框用真实鼠标点击才会弹出选图菜单；DOM click 实测无效。
        cover_box = page.locator('.appmsg_cover, .cover, [class*="cover_area"]').first
        await cover_box.click(position={"x": 20, "y": 20})
        await page.get_by_text("从图片库选择", exact=True).click()
        file_input = page.locator('.js_upload_btn_container input[type="file"]').first
        await expect(file_input).to_have_count(1, timeout=15000)
        await file_input.set_input_files(str(self.cover))
        await page.get_by_text(self.cover.name, exact=False).first.wait_for(state="visible", timeout=30000)
        await page.get_by_role("button", name="确定", exact=True).last.click()
        # 封面裁剪确认弹窗；不同账号可能不出现，仅在出现时点击。
        try:
            confirm = page.get_by_role("button", name="确认", exact=True)
            if await confirm.count() and await confirm.last.is_visible():
                await confirm.last.click()
        except Exception:
            pass

    async def main(self) -> dict:
        """填写并可发表；扫码验证由管理员完成，程序在二维码处暂停等待。"""
        self.validate_upload_args()
        results_dir = self.account_file.parent / "wechat_results"
        results_dir.mkdir(exist_ok=True)
        result_file = results_dir / f"{datetime.now(WECHAT_TIMEZONE):%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.json"
        result = {
            "success": False, "status": "preparing", "type": "article",
            "title": self.title, "content_file": str(self.content_file),
            "digest": self.digest, "author": self.author,
            "cover": str(self.cover) if self.cover else None,
            "originality": self.originality, "broadcast": self.broadcast,
            "identity": self.identity, "result_file": str(result_file),
        }

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**browser_launch_kwargs(self.headless))
            page = None
            submitted = False
            try:
                context = await browser.new_context(
                    storage_state=str(self.account_file), timezone_id="Asia/Shanghai")
                page = await context.new_page()
                token = await read_wechat_token(page)
                result["token_prefix"] = token[:4] + "***"
                article_url = build_article_url(token)
                response = await page.goto(article_url, wait_until="domcontentloaded", timeout=45000)
                if response is not None and response.status >= 400:
                    raise RuntimeError(f"微信公众号图文编辑器访问失败，HTTP {response.status}")
                if await read_wechat_identity(page) != self.identity:
                    raise RuntimeError("微信公众号编辑器账号与本地绑定不一致")

                await self.fill_article_form(page)
                await self.upload_cover(page)
                result.update(images=self.uploaded_images, manifest=self.document.manifest,
                              editor_url=page.url)
                result["status"] = "prepared"
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                screenshot = result_file.with_suffix(".png")
                await page.screenshot(path=str(screenshot), full_page=True)
                result["screenshot"] = str(screenshot)
                if self.prepare_only:
                    return result

                # 发表后依次处理创作来源声明、发表方式与群发确认；每步只点一次。
                publish = page.get_by_role("button", name="发表", exact=True).last
                await expect(publish).to_be_enabled(timeout=30000)
                result["status"] = "submission_unknown"
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                await publish.click()

                # 创作来源声明：按用户选择处理，不擅自替作者声明原创。
                try:
                    declare = page.get_by_role("button", name=re.compile("声明|原创|不声明|无需声明"))
                    if await declare.count() and await declare.first.is_visible(timeout=5000):
                        if self.originality == "original":
                            await page.get_by_role("button", name=re.compile("声明原创")).first.click()
                        else:
                            await page.get_by_role("button", name=re.compile("无需声明|不声明")).first.click()
                except Exception:
                    pass

                # 发表方式弹窗：群发通知开关按 --broadcast 决定。
                try:
                    if await page.get_by_text("发表方式", exact=False).count():
                        if self.broadcast:
                            toggle = page.locator('.weui-desktop-switch, [role="switch"]').first
                            if await toggle.count() and "on" not in (await toggle.get_attribute("class") or ""):
                                await toggle.click()
                        await page.get_by_role("button", name="发表", exact=True).last.click()
                        # 已开启群发通知的二次确认。
                        continue_btn = page.get_by_role("button", name=re.compile("继续发表"))
                        if await continue_btn.count() and await continue_btn.last.is_visible(timeout=5000):
                            await continue_btn.last.click()
                except Exception:
                    pass

                submitted = True
                # 管理员扫码验证：检测到二维码后暂停等待，超时则如实报告未知。
                try:
                    qr_hint = page.get_by_text(re.compile("扫码.*验证|管理员.*验证"))
                    if await qr_hint.count() and await qr_hint.first.is_visible(timeout=5000):
                        result["status"] = "awaiting_admin_qr"
                        result["message"] = "请用管理员微信扫码完成验证"
                        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                        print("请用管理员微信扫描页面二维码完成验证；程序正在等待...", flush=True)
                        await expect(page).to_have_url(
                            re.compile(r"mp\.weixin\.qq\.com.*(home|appmsg)"),
                            timeout=self.qr_timeout * 1000)
                except Exception:
                    pass

                await page.wait_for_timeout(3000)
                result["status"] = "submitted"
                result["message"] = ("已提交发表；如触发扫码验证请确认已完成，"
                                     "并到「已发表」核实发布结果")
                result["success"] = True
                await page.screenshot(path=str(result_file.with_suffix(".submitted.png")), full_page=True)
                return result
            except Exception as exc:
                result["error"] = str(exc)
                if submitted:
                    result["status"] = "submission_unknown"
                elif result["status"] == "preparing":
                    result["status"] = "failed_before_submit"
                if self.debug and page is not None:
                    screenshot = result_file.with_suffix(".error.png")
                    await page.screenshot(path=str(screenshot), full_page=True)
                    result["screenshot"] = str(screenshot)
                raise RuntimeError(f"微信公众号阶段={result['status']}，结果文件={result_file}: {exc}") from exc
            finally:
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                await browser.close()
