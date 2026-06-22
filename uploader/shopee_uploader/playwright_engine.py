"""
Patchright/Playwright Shopee Video uploader with proxy, screenshots, and
product attachment for affiliate videos.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from uploader.core.browser_manager import BrowserManager, redact_sensitive

try:
    from patchright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except Exception:  # pragma: no cover - fallback for local dev if patchright is absent
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

ERROR_LOGS_DIR = Path(os.getenv("ERROR_LOGS_DIR", "./error_logs"))
ERROR_LOGS_DIR.mkdir(parents=True, exist_ok=True)

HEADLESS = os.getenv("SHOPEE_HEADLESS", os.getenv("FB_HEADLESS", "1")) == "1"
UPLOAD_TIMEOUT_MS = int(os.getenv("SHOPEE_UPLOAD_TIMEOUT_MS", "300000"))
ACTION_TIMEOUT_MS = int(os.getenv("SHOPEE_ACTION_TIMEOUT_MS", "30000"))
SHOPEE_UPLOAD_URL = os.getenv("SHOPEE_UPLOAD_URL", "https://creator.shopee.vn/")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}


class ShopeeUploadError(Exception):
    """Raised when Shopee upload fails, includes screenshot path."""

    def __init__(self, message: str, screenshot_path: str | None = None):
        self.screenshot_path = screenshot_path
        super().__init__(
            f"{message} | screenshot={screenshot_path}" if screenshot_path else message
        )


class ShopeePlaywrightUploader:
    """Automate Shopee video publishing and product attachment."""

    def __init__(
        self,
        cookies: list[dict],
        account_id: str | int = "shopee_default",
        proxy_url: str | None = None,
        headless: bool = HEADLESS,
        locale: str | None = None,
        timezone_id: str | None = None,
    ):
        self.cookies = self._normalize_cookies(cookies)
        self.account_id = account_id
        self.proxy_url = proxy_url
        self.headless = headless
        self.locale = locale
        self.timezone_id = timezone_id
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._session = None

    @staticmethod
    def _normalize_cookies(cookies: list[dict]) -> list[dict]:
        normalized = []
        for c in cookies:
            cookie = {
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": c.get("domain", ".shopee.vn"),
                "path": c.get("path", "/"),
            }
            for key in ("expires", "httpOnly", "secure"):
                if key in c:
                    cookie[key] = c[key]
            if "sameSite" in c:
                same_site = c["sameSite"]
                if isinstance(same_site, str):
                    cookie["sameSite"] = {
                        "strict": "Strict",
                        "lax": "Lax",
                        "none": "None",
                        "no_restriction": "None",
                        "unspecified": "Lax",
                    }.get(same_site.lower(), "Lax")
            normalized.append(cookie)
        return normalized

    @staticmethod
    def _is_proxy_error(exc: Exception) -> bool:
        message = str(exc).lower()
        markers = (
            "proxy",
            "net::err_proxy",
            "err_tunnel_connection_failed",
            "err_proxy_connection_failed",
            "tunnel connection failed",
            "socks",
            "407",
            "connection refused",
            "connection timed out",
        )
        return any(marker in message for marker in markers)

    def _start(self) -> None:
        self._playwright = sync_playwright().start()
        manager = BrowserManager(
            playwright=self._playwright,
            account_id=self.account_id,
            proxy_url=self.proxy_url,
            headless=self.headless,
            locale=self.locale,
            timezone_id=self.timezone_id,
            action_timeout_ms=ACTION_TIMEOUT_MS,
        )
        self._session = manager.launch_persistent_session(cookies=self.cookies)
        self._context = self._session.context
        self._page = self._session.page

    def _cleanup(self) -> None:
        try:
            if self._session:
                self._session.close()
            elif self._playwright:
                self._playwright.stop()
        except Exception as exc:
            logger.warning("Shopee cleanup error: %s", redact_sensitive(exc))
        finally:
            self._session = None
            self._context = None
            self._page = None
            self._playwright = None

    def _take_screenshot(self, upload_job_id: str, step: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = str(ERROR_LOGS_DIR / f"shopee_upload_{upload_job_id}_{step}_{ts}.png")
        try:
            if self._page:
                self._page.screenshot(path=path, full_page=True)
                logger.info("Shopee screenshot saved: %s", path)
        except Exception as exc:
            logger.warning("Shopee screenshot failed: %s", exc)
            path = ""
        return path

    def _fail(self, upload_job_id: str, step: str, message: str) -> None:
        raise ShopeeUploadError(message, self._take_screenshot(upload_job_id, step))

    def _dismiss_popups(self) -> None:
        page = self._page
        selectors = [
            '[aria-label="Close"]',
            '[aria-label="Đóng"]',
            'button:has-text("Đóng")',
            'button:has-text("Close")',
            'button:has-text("Bỏ qua")',
            'button:has-text("Skip")',
            '.shopee-modal__close',
            '.eds-modal__close',
        ]
        for selector in selectors:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=1000):
                    button.click(timeout=3000)
                    page.wait_for_timeout(500)
                    logger.info("Shopee popup dismissed: %s", selector)
            except Exception:
                pass
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    def _click_first_visible(self, selectors: list[str], timeout: int = 5000) -> bool:
        page = self._page
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=timeout):
                    locator.click(timeout=timeout)
                    logger.info("Shopee clicked: %s", selector)
                    return True
            except Exception:
                pass
        return False

    def _locate_file_input(self):
        page = self._page
        selectors = [
            'input[type="file"][accept*="video"]',
            'input[type="file"]',
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count():
                    return locator
            except Exception:
                pass
        for frame in page.frames:
            for selector in selectors:
                try:
                    locator = frame.locator(selector).first
                    if locator.count():
                        return locator
                except Exception:
                    pass
        return None

    def _go_to_upload_surface(self) -> None:
        page = self._page
        self._dismiss_popups()
        self._click_first_visible(
            [
                'a:has-text("Video")',
                'button:has-text("Video")',
                'div[role="button"]:has-text("Video")',
                'a:has-text("Đăng video")',
                'button:has-text("Đăng video")',
                'button:has-text("Tải lên")',
                'button:has-text("Upload")',
                'div[role="button"]:has-text("Upload")',
                'div[role="button"]:has-text("Tải lên")',
            ],
            timeout=3000,
        )
        try:
            page.wait_for_selector('input[type="file"]', timeout=15000)
        except PlaywrightTimeout:
            logger.info("Shopee upload input not immediately visible — trying current page")

    def _find_caption_box(self):
        page = self._page
        selectors = [
            'textarea[placeholder*="mô tả" i]',
            'textarea[placeholder*="caption" i]',
            'textarea[placeholder*="description" i]',
            '[contenteditable="true"][aria-label*="mô tả" i]',
            '[contenteditable="true"][aria-label*="caption" i]',
            '[contenteditable="true"]',
            'textarea',
        ]
        for selector in selectors:
            try:
                box = page.locator(selector).first
                if box.is_visible(timeout=3000):
                    logger.info("Shopee caption box found: %s", selector)
                    return box
            except Exception:
                pass
        return None

    def _wait_upload_ready(self, upload_job_id: str) -> None:
        page = self._page
        try:
            page.wait_for_function(
                """() => {
                    const text = document.body.innerText.toLowerCase();
                    const busy = document.querySelector('[role="progressbar"], [class*="progress"], [class*="uploading"]');
                    return !busy || text.includes('100%') || text.includes('hoàn tất') || text.includes('publish') || text.includes('đăng');
                }""",
                timeout=UPLOAD_TIMEOUT_MS,
            )
        except PlaywrightTimeout:
            self._fail(upload_job_id, "upload_wait", "Shopee upload processing timed out")

    def _attach_product(self, product_ref: str, upload_job_id: str) -> None:
        if not product_ref:
            logger.info("Shopee product attach skipped — empty product_ref")
            return
        page = self._page
        self._dismiss_popups()
        clicked = self._click_first_visible(
            [
                'button:has-text("Thêm sản phẩm")',
                'button:has-text("Add Product")',
                'div[role="button"]:has-text("Thêm sản phẩm")',
                'div[role="button"]:has-text("Add Product")',
                'span:has-text("Thêm sản phẩm")',
            ],
            timeout=8000,
        )
        if not clicked:
            self._fail(upload_job_id, "add_product_button", "Cannot find Shopee Add Product button")

        search_selectors = [
            'input[placeholder*="URL" i]',
            'input[placeholder*="ID" i]',
            'input[placeholder*="sản phẩm" i]',
            'input[placeholder*="product" i]',
            'input[type="text"]',
        ]
        search_box = None
        for selector in search_selectors:
            try:
                candidate = page.locator(selector).last
                if candidate.is_visible(timeout=5000):
                    search_box = candidate
                    logger.info("Shopee product search box found: %s", selector)
                    break
            except Exception:
                pass
        if not search_box:
            self._fail(upload_job_id, "product_search", "Cannot find Shopee product search input")

        search_box.fill(product_ref)
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)

        selected = self._click_first_visible(
            [
                'button:has-text("Chọn")',
                'button:has-text("Select")',
                'label:has-text("Chọn")',
                'div[role="checkbox"]',
                'input[type="checkbox"]',
            ],
            timeout=8000,
        )
        if not selected:
            self._fail(upload_job_id, "product_select", "Cannot select Shopee product")

        confirmed = self._click_first_visible(
            [
                'button:has-text("Xác nhận")',
                'button:has-text("Confirm")',
                'button:has-text("Thêm")',
                'button:has-text("Add")',
            ],
            timeout=8000,
        )
        if not confirmed:
            self._fail(upload_job_id, "product_confirm", "Cannot confirm Shopee product")
        logger.info("Shopee product attached: %s", product_ref)

    def _click_publish(self, upload_job_id: str) -> None:
        clicked = self._click_first_visible(
            [
                'button:has-text("Đăng")',
                'button:has-text("Publish")',
                'button:has-text("Post")',
                'div[role="button"]:has-text("Đăng")',
                'div[role="button"]:has-text("Publish")',
            ],
            timeout=12000,
        )
        if not clicked:
            self._fail(upload_job_id, "publish_button", "Cannot find Shopee Publish button")

    def _extract_post_url(self) -> str | None:
        page = self._page
        try:
            page.wait_for_timeout(5000)
            current_url = page.url
            if "shopee" in current_url and ("video" in current_url or "creator" in current_url):
                return current_url
            links = page.locator('a[href*="shopee"][href*="video"], a[href*="shopee.vn"]').all()
            for link in links[:10]:
                href = link.get_attribute("href")
                if href and "shopee" in href:
                    return href if href.startswith("http") else f"https://creator.shopee.vn{href}"
        except Exception as exc:
            logger.info("Shopee post URL extraction failed: %s", exc)
        return None

    def upload(
        self,
        video_path: str,
        caption: str,
        product_ref: str | None,
        upload_job_id: str,
    ) -> str | None:
        if not os.path.isfile(video_path):
            raise ShopeeUploadError(f"Video file not found: {video_path}")
        try:
            self._start()
            page = self._page
            logger.info("Navigating to Shopee Creator: %s", SHOPEE_UPLOAD_URL)
            page.goto(SHOPEE_UPLOAD_URL, wait_until="domcontentloaded", timeout=UPLOAD_TIMEOUT_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except PlaywrightTimeout:
                logger.info("Shopee networkidle timeout — continuing")
            self._go_to_upload_surface()

            file_input = self._locate_file_input()
            if not file_input:
                self._fail(upload_job_id, "file_input", "Cannot find Shopee video file input")
            file_input.set_input_files(video_path)
            logger.info("Shopee video attached: %s", video_path)

            self._wait_upload_ready(upload_job_id)

            if caption:
                box = self._find_caption_box()
                if box:
                    box.click(timeout=10000)
                    try:
                        box.fill("")
                    except Exception:
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                    page.keyboard.type(caption, delay=20)
                    logger.info("Shopee caption filled (%d chars)", len(caption))
                else:
                    logger.warning("Shopee caption box not found — continuing")
                    self._take_screenshot(upload_job_id, "caption_box_missing")

            self._attach_product(product_ref or "", upload_job_id)
            self._click_publish(upload_job_id)
            post_url = self._extract_post_url()
            logger.info("Shopee upload succeeded — post_url=%s", post_url)
            return post_url
        except ShopeeUploadError:
            raise
        except Exception as exc:
            step = "proxy_connection_failed" if self._is_proxy_error(exc) else "unexpected_error"
            message = f"Proxy connection failed: {exc}" if self._is_proxy_error(exc) else f"Unexpected Shopee upload error: {exc}"
            raise ShopeeUploadError(message, self._take_screenshot(upload_job_id, step)) from exc
        finally:
            self._cleanup()
