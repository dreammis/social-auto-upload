"""
Patchright/Playwright TikTok video uploader with proxy, screenshots, and
best-effort affiliate comment seeding.
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

HEADLESS = os.getenv("TIKTOK_HEADLESS", os.getenv("FB_HEADLESS", "1")) == "1"
UPLOAD_TIMEOUT_MS = int(os.getenv("TIKTOK_UPLOAD_TIMEOUT_MS", "300000"))
ACTION_TIMEOUT_MS = int(os.getenv("TIKTOK_ACTION_TIMEOUT_MS", "30000"))

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}
UPLOAD_URL = "https://www.tiktok.com/creator-center/upload"


class TikTokUploadError(Exception):
    """Raised when TikTok upload fails, includes screenshot path."""

    def __init__(self, message: str, screenshot_path: str | None = None):
        self.screenshot_path = screenshot_path
        super().__init__(
            f"{message} | screenshot={screenshot_path}" if screenshot_path else message
        )


class TikTokPlaywrightUploader:
    """Automate TikTok upload + optional affiliate comment seeding."""

    def __init__(
        self,
        cookies: list[dict],
        account_id: str | int = "tiktok_default",
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
                "domain": c.get("domain", ".tiktok.com"),
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
            logger.warning("TikTok cleanup error: %s", redact_sensitive(exc))
        finally:
            self._session = None
            self._context = None
            self._page = None
            self._playwright = None

    def _take_screenshot(self, upload_job_id: str, step: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = str(ERROR_LOGS_DIR / f"tiktok_upload_{upload_job_id}_{step}_{ts}.png")
        try:
            if self._page:
                self._page.screenshot(path=path, full_page=True)
                logger.info("TikTok screenshot saved: %s", path)
        except Exception as exc:
            logger.warning("TikTok screenshot failed: %s", exc)
            path = ""
        return path

    def _fail(self, upload_job_id: str, step: str, message: str) -> None:
        raise TikTokUploadError(message, self._take_screenshot(upload_job_id, step))

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

    def _find_caption_box(self):
        page = self._page
        selectors = [
            '[contenteditable="true"][data-e2e*="caption"]',
            'div[contenteditable="true"][role="textbox"]',
            '[contenteditable="true"]',
            'textarea[placeholder*="caption" i]',
            'textarea',
        ]
        for selector in selectors:
            try:
                box = page.locator(selector).first
                if box.is_visible(timeout=4000):
                    logger.info("TikTok caption box found: %s", selector)
                    return box
            except Exception:
                pass
        for frame in page.frames:
            for selector in selectors:
                try:
                    box = frame.locator(selector).first
                    if box.is_visible(timeout=2000):
                        logger.info("TikTok caption box found in frame: %s", selector)
                        return box
                except Exception:
                    pass
        return None

    def _click_publish(self, upload_job_id: str) -> None:
        page = self._page
        selectors = [
            'button:has-text("Post")',
            'button:has-text("Đăng")',
            'div[role="button"]:has-text("Post")',
            'div[role="button"]:has-text("Đăng")',
            '[data-e2e="post_video_button"]',
        ]
        for selector in selectors:
            try:
                button = page.locator(selector).first
                button.wait_for(state="visible", timeout=10000)
                button.click(timeout=10000)
                logger.info("TikTok publish clicked: %s", selector)
                return
            except Exception:
                pass
        self._fail(upload_job_id, "publish_button", "Cannot find TikTok Post button")

    def _wait_upload_ready(self, upload_job_id: str) -> None:
        page = self._page
        try:
            page.wait_for_function(
                """() => {
                    const busy = document.querySelector('[role="progressbar"], .upload-progress, [class*="progress"]');
                    const text = document.body.innerText.toLowerCase();
                    return !busy || text.includes('uploaded') || text.includes('post') || text.includes('đăng');
                }""",
                timeout=UPLOAD_TIMEOUT_MS,
            )
        except PlaywrightTimeout:
            self._fail(upload_job_id, "upload_wait", "TikTok upload processing timed out")

    def _extract_post_url(self) -> str | None:
        page = self._page
        try:
            page.wait_for_timeout(5000)
            current_url = page.url
            if "/video/" in current_url:
                return current_url
            links = page.locator('a[href*="/video/"]').all()
            for link in links[:10]:
                href = link.get_attribute("href")
                if href and "/video/" in href:
                    if href.startswith("http"):
                        return href
                    return f"https://www.tiktok.com{href}"
        except Exception as exc:
            logger.info("TikTok post URL extraction failed: %s", exc)
        return None

    def upload(self, video_path: str, caption: str, upload_job_id: str) -> str | None:
        if not os.path.isfile(video_path):
            raise TikTokUploadError(f"Video file not found: {video_path}")
        try:
            self._start()
            page = self._page
            logger.info("Navigating to TikTok upload page")
            page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=UPLOAD_TIMEOUT_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except PlaywrightTimeout:
                logger.info("TikTok networkidle timeout — continuing")

            file_input = self._locate_file_input()
            if not file_input:
                self._fail(upload_job_id, "file_input", "Cannot find TikTok video file input")
            file_input.set_input_files(video_path)
            logger.info("TikTok video attached: %s", video_path)

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
                    logger.info("TikTok caption filled (%d chars)", len(caption))
                else:
                    logger.warning("TikTok caption box not found — posting without caption")
                    self._take_screenshot(upload_job_id, "caption_box_missing")

            self._click_publish(upload_job_id)
            post_url = self._extract_post_url()
            logger.info("TikTok upload succeeded — post_url=%s", post_url)
            return post_url
        except TikTokUploadError:
            raise
        except Exception as exc:
            step = "proxy_connection_failed" if self._is_proxy_error(exc) else "unexpected_error"
            message = f"Proxy connection failed: {exc}" if self._is_proxy_error(exc) else f"Unexpected TikTok upload error: {exc}"
            raise TikTokUploadError(message, self._take_screenshot(upload_job_id, step)) from exc
        finally:
            self._cleanup()

    def _find_comment_box(self):
        page = self._page
        selectors = [
            '[contenteditable="true"][placeholder*="comment" i]',
            '[contenteditable="true"][aria-label*="comment" i]',
            '[contenteditable="true"]',
            'textarea[placeholder*="comment" i]',
        ]
        for selector in selectors:
            try:
                box = page.locator(selector).first
                if box.is_visible(timeout=4000):
                    return box
            except Exception:
                pass
        return None

    def post_comment(
        self,
        post_url: str,
        comment_text: str,
        upload_job_id: str = "tiktok_affiliate_comment",
    ) -> None:
        """Best-effort affiliate comment; never raises to caller."""
        if not post_url or not comment_text:
            logger.info("TikTok affiliate comment skipped — missing post_url/comment_text")
            return
        try:
            self._start()
            page = self._page
            page.goto(post_url, wait_until="domcontentloaded", timeout=UPLOAD_TIMEOUT_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeout:
                logger.info("TikTok comment networkidle timeout — continuing")
            box = self._find_comment_box()
            if not box:
                page.mouse.wheel(0, 900)
                box = self._find_comment_box()
            if not box:
                self._take_screenshot(upload_job_id, "comment_box_missing")
                logger.warning("TikTok comment box not found")
                return
            box.click(timeout=10000)
            page.keyboard.type(comment_text, delay=20)
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            logger.info("TikTok affiliate comment submitted (%d chars)", len(comment_text))
        except Exception as exc:
            step = "comment_proxy_failed" if self._is_proxy_error(exc) else "comment_failed"
            screenshot = self._take_screenshot(upload_job_id, step)
            logger.error("TikTok affiliate comment failed: %s (screenshot=%s)", exc, screenshot, exc_info=True)
        finally:
            self._cleanup()
