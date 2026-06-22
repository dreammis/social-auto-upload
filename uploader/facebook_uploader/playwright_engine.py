"""
Playwright-based Facebook Page video uploader.

Uses sync_api (runs inside a background thread) to:
  1. Launch Chromium with stealth settings
  2. Inject decrypted cookies into a browser context
  3. Navigate to Facebook Page composer / Meta Business Suite
  4. Upload video, fill caption, publish
  5. Capture post URL or confirm success

On ANY failure: captures a screenshot to error_logs/ for debugging.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
ERROR_LOGS_DIR = Path(os.getenv("ERROR_LOGS_DIR", "./error_logs"))
ERROR_LOGS_DIR.mkdir(parents=True, exist_ok=True)

HEADLESS = os.getenv("FB_HEADLESS", "1") == "1"
UPLOAD_TIMEOUT_MS = int(os.getenv("FB_UPLOAD_TIMEOUT_MS", "300000"))  # 5 min
ACTION_TIMEOUT_MS = int(os.getenv("FB_ACTION_TIMEOUT_MS", "30000"))   # 30 sec

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}


class FacebookUploadError(Exception):
    """Raised when the upload pipeline fails, includes screenshot path."""

    def __init__(self, message: str, screenshot_path: str | None = None):
        self.screenshot_path = screenshot_path
        super().__init__(
            f"{message} | screenshot={screenshot_path}" if screenshot_path else message
        )


class FacebookPlaywrightUploader:
    """Automate video publishing to a Facebook Page via Playwright."""

    def __init__(
        self,
        cookies: list[dict],
        page_name: str | None = None,
        headless: bool = HEADLESS,
    ):
        """
        Args:
            cookies: List of cookie dicts (Playwright format).
                     Each must have: name, value, domain, path.
            page_name: Facebook Page name (for URL routing).
            headless: Run browser headlessly (True for prod).
        """
        self.cookies = self._normalize_cookies(cookies)
        self.page_name = page_name
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    @staticmethod
    def _normalize_cookies(cookies: list[dict]) -> list[dict]:
        """Ensure every cookie has required Playwright fields."""
        normalized = []
        for c in cookies:
            cookie = {
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": c.get("domain", ".facebook.com"),
                "path": c.get("path", "/"),
            }
            # Optional fields
            if "expires" in c:
                cookie["expires"] = c["expires"]
            if "httpOnly" in c:
                cookie["httpOnly"] = c["httpOnly"]
            if "secure" in c:
                cookie["secure"] = c["secure"]
            if "sameSite" in c:
                ss = c["sameSite"]
                # Playwright expects capitalized: Strict, Lax, None
                if isinstance(ss, str):
                    ss_map = {"strict": "Strict", "lax": "Lax", "none": "None",
                              "no_restriction": "None", "unspecified": "Lax"}
                    cookie["sameSite"] = ss_map.get(ss.lower(), "Lax")
            normalized.append(cookie)
        return normalized

    def _take_screenshot(self, upload_job_id: str, step: str) -> str:
        """Capture current page state for debugging."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"fb_upload_{upload_job_id}_{step}_{ts}.png"
        path = str(ERROR_LOGS_DIR / filename)
        try:
            if self._page:
                self._page.screenshot(path=path, full_page=True)
                logger.info("Screenshot saved: %s", path)
        except Exception as exc:
            logger.warning("Screenshot failed: %s", exc)
            path = ""
        return path

    def _fail(self, upload_job_id: str, step: str, message: str) -> None:
        """Take screenshot and raise FacebookUploadError."""
        screenshot = self._take_screenshot(upload_job_id, step)
        raise FacebookUploadError(message, screenshot_path=screenshot)

    def upload(
        self,
        video_path: str,
        caption: str,
        upload_job_id: str,
    ) -> str | None:
        """Execute the full upload pipeline.

        Args:
            video_path: Absolute path to the video file.
            caption: Post text (can include hashtags, links).
            upload_job_id: For error log filenames.

        Returns:
            Post URL if extractable, else None on success.

        Raises:
            FacebookUploadError: On any failure (with screenshot).
        """
        if not os.path.isfile(video_path):
            raise FacebookUploadError(f"Video file not found: {video_path}")

        post_url = None

        try:
            self._playwright = sync_playwright().start()

            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            self._context = self._browser.new_context(
                user_agent=DEFAULT_USER_AGENT,
                viewport=DEFAULT_VIEWPORT,
                locale="en-US",
                timezone_id="Asia/Ho_Chi_Minh",
            )

            # Inject cookies
            self._context.add_cookies(self.cookies)
            logger.info("Injected %d cookies into browser context", len(self.cookies))

            self._page = self._context.new_page()
            self._page.set_default_timeout(ACTION_TIMEOUT_MS)

            # ── Step 1: Navigate to Facebook ──
            logger.info("Navigating to Facebook...")
            self._page.goto("https://www.facebook.com/", wait_until="networkidle")

            # Verify login — check for logged-in indicator
            try:
                self._page.wait_for_selector(
                    '[aria-label="Your profile"], [aria-label="Account"], '
                    '[data-pagelet="ProfileTile"], [aria-label="Facebook"]',
                    timeout=15000,
                )
                logger.info("Facebook login verified via cookies")
            except PlaywrightTimeout:
                self._fail(upload_job_id, "login_check",
                           "Cookie login failed — not authenticated")

            # ── Step 2: Navigate to Page video upload ──
            # Try Meta Business Suite first, fall back to direct page composer
            composer_url = self._resolve_composer_url()
            logger.info("Navigating to composer: %s", composer_url)
            self._page.goto(composer_url, wait_until="domcontentloaded")
            self._page.wait_for_timeout(3000)  # Let SPA render

            # ── Step 3: Initiate video upload ──
            logger.info("Looking for video upload trigger...")
            post_url = self._do_upload_flow(video_path, caption, upload_job_id)

            logger.info("Upload pipeline succeeded — post_url=%s", post_url)
            return post_url

        except FacebookUploadError:
            raise  # Already has screenshot
        except Exception as exc:
            screenshot = self._take_screenshot(upload_job_id, "unexpected_error")
            raise FacebookUploadError(
                f"Unexpected error: {exc}", screenshot_path=screenshot
            ) from exc
        finally:
            self._cleanup()

    def _resolve_composer_url(self) -> str:
        """Pick the best upload URL based on config."""
        if self.page_name:
            # Direct Page video upload
            return f"https://www.facebook.com/{self.page_name}/videos/"
        # Default: Meta Business Suite composer
        return "https://business.facebook.com/latest/home"

    def _do_upload_flow(
        self, video_path: str, caption: str, upload_job_id: str
    ) -> str | None:
        """Core DOM interaction: upload video, fill caption, publish.

        This method handles two main flows:
        1. Meta Business Suite (business.facebook.com)
        2. Direct Facebook Page video upload
        """
        page = self._page

        # ── Try to find "Create post" or "Create reel" button ──
        try:
            # Business Suite: look for create button
            create_btn = page.locator(
                'text="Create post", text="Create reel", '
                'text="Tạo bài viết", text="Create Post"'
            ).first
            if create_btn.is_visible(timeout=5000):
                create_btn.click()
                page.wait_for_timeout(2000)
        except (PlaywrightTimeout, Exception):
            logger.info("No 'Create post' button found — trying direct upload")

        # ── Upload video via file input ──
        try:
            # Method 1: Find file input directly
            file_input = page.locator('input[type="file"][accept*="video"]').first
            if not file_input.count():
                # Method 2: Broader file input search
                file_input = page.locator('input[type="file"]').first

            if file_input.count():
                file_input.set_input_files(video_path)
                logger.info("Video file attached via input element")
            else:
                # Method 3: Click "Photo/video" button to reveal input
                photo_video_btn = page.locator(
                    'text="Photo/video", text="Ảnh/video", '
                    'text="Photo/Video", text="Add photos/videos",'
                    '[aria-label="Photo/video"], [aria-label="Photo/Video"]'
                ).first
                photo_video_btn.click(timeout=10000)
                page.wait_for_timeout(2000)

                file_input = page.locator('input[type="file"]').first
                if not file_input.count():
                    self._fail(upload_job_id, "find_file_input",
                               "Cannot find file input element")
                file_input.set_input_files(video_path)
                logger.info("Video file attached after clicking Photo/video")

        except PlaywrightTimeout:
            self._fail(upload_job_id, "file_upload",
                       "Timed out looking for file upload element")

        # ── Wait for upload to process ──
        logger.info("Waiting for video upload to complete (timeout=%dms)...",
                     UPLOAD_TIMEOUT_MS)
        try:
            # Wait for upload progress to finish — look for the publish button
            # becoming enabled, or upload progress bar disappearing
            page.wait_for_timeout(5000)  # Initial processing time

            # Wait for either: publish button enabled OR progress gone
            page.wait_for_function(
                """() => {
                    // Check if any progress bar or spinner is still active
                    const progress = document.querySelector(
                        '[role="progressbar"], [aria-label*="uploading"], '
                        + '[aria-label*="Uploading"], [aria-label*="processing"]'
                    );
                    return !progress || progress.getAttribute('aria-valuenow') === '100';
                }""",
                timeout=UPLOAD_TIMEOUT_MS,
            )
            logger.info("Video upload/processing complete")
        except PlaywrightTimeout:
            self._fail(upload_job_id, "upload_wait",
                       f"Video upload timed out after {UPLOAD_TIMEOUT_MS}ms")

        # ── Fill caption ──
        if caption:
            try:
                # Facebook uses contenteditable divs for post text
                text_area = page.locator(
                    '[contenteditable="true"][role="textbox"], '
                    '[contenteditable="true"][aria-label*="Write"], '
                    '[contenteditable="true"][aria-label*="what"], '
                    '[contenteditable="true"][data-contents="true"], '
                    'textarea[name="xhpc_message_text"]'
                ).first
                text_area.click()
                text_area.fill("")  # Clear existing
                page.keyboard.type(caption, delay=20)
                logger.info("Caption filled (%d chars)", len(caption))
            except PlaywrightTimeout:
                logger.warning("Could not fill caption — continuing without it")
                self._take_screenshot(upload_job_id, "caption_failed")

        # ── Click Publish ──
        try:
            publish_btn = page.locator(
                'text="Post", text="Đăng", text="Publish", text="Share", '
                'text="Share now", text="Chia sẻ ngay", '
                '[aria-label="Post"], [aria-label="Publish"], '
                '[data-testid="react-composer-post-button"]'
            ).first

            # Wait for button to be enabled
            publish_btn.wait_for(state="visible", timeout=10000)
            page.wait_for_timeout(2000)  # Brief pause before clicking
            publish_btn.click()
            logger.info("Publish button clicked")

        except PlaywrightTimeout:
            self._fail(upload_job_id, "publish_click",
                       "Could not find or click Publish button")

        # ── Wait for post confirmation ──
        try:
            page.wait_for_timeout(5000)  # Wait for Facebook to process

            # Try to extract post URL from confirmation or redirect
            current_url = page.url
            if "/posts/" in current_url or "/videos/" in current_url:
                post_url = current_url
                logger.info("Post URL captured from redirect: %s", post_url)
                return post_url

            # Try to find success notification
            success_indicator = page.locator(
                'text="Your post is now published", '
                'text="Bài viết của bạn đã được đăng", '
                'text="shared", text="Posted"'
            ).first
            if success_indicator.is_visible(timeout=10000):
                logger.info("Post success confirmed via UI notification")
                # Try to find post link in notification
                try:
                    link = page.locator('a[href*="/posts/"], a[href*="/videos/"]').first
                    if link.is_visible(timeout=3000):
                        post_url = link.get_attribute("href")
                        if post_url and not post_url.startswith("http"):
                            post_url = f"https://www.facebook.com{post_url}"
                        return post_url
                except Exception:
                    pass

            # Take success screenshot even without URL
            self._take_screenshot(upload_job_id, "post_success")
            logger.info("Post published — URL not extractable")
            return None

        except PlaywrightTimeout:
            # Not necessarily failure — Facebook might have processed silently
            self._take_screenshot(upload_job_id, "post_confirmation_timeout")
            logger.warning("Post confirmation timed out — may have succeeded")
            return None

    def post_comment(
        self,
        post_url: str,
        comment_text: str,
        upload_job_id: str = "affiliate_comment",
    ) -> None:
        """Open a Facebook post and submit the first affiliate comment.

        Comment seeding is best-effort. Any failure is logged and swallowed so
        the primary video upload success state is never downgraded.
        """
        if not post_url:
            logger.warning("Affiliate comment skipped — missing post_url")
            return
        if not comment_text:
            logger.info("Empty affiliate comment — skipping")
            return

        try:
            self._playwright = sync_playwright().start()

            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            self._context = self._browser.new_context(
                user_agent=DEFAULT_USER_AGENT,
                viewport=DEFAULT_VIEWPORT,
                locale="en-US",
                timezone_id="Asia/Ho_Chi_Minh",
            )
            self._context.add_cookies(self.cookies)
            logger.info("Injected %d cookies for affiliate comment", len(self.cookies))

            self._page = self._context.new_page()
            self._page.set_default_timeout(ACTION_TIMEOUT_MS)
            page = self._page

            logger.info("Navigating to Facebook post for comment: %s", post_url)
            page.goto(post_url, wait_until="domcontentloaded", timeout=UPLOAD_TIMEOUT_MS)
            self._wait_for_post_ready()
            self._dismiss_comment_interceptors()

            comment_box = self._wait_for_comment_box()
            if not comment_box:
                page.mouse.wheel(0, 900)
                self._dismiss_comment_interceptors()
                comment_box = self._wait_for_comment_box(timeout=15000)

            if not comment_box:
                self._fail(
                    upload_job_id,
                    "comment_box",
                    "Cannot find Facebook comment textbox",
                )
                return

            comment_box.click(timeout=10000)
            page.keyboard.type(comment_text, delay=20)
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            logger.info("Affiliate comment submitted (%d chars)", len(comment_text))

        except Exception as exc:
            screenshot = self._take_screenshot(upload_job_id, "comment_failed")
            logger.error(
                "Affiliate comment failed — job=%s: %s (screenshot=%s)",
                upload_job_id,
                exc,
                screenshot,
                exc_info=True,
            )
        finally:
            self._cleanup()

    def _wait_for_post_ready(self, timeout: int = 30000) -> None:
        """Wait until the Facebook post shell is rendered enough to comment."""
        page = self._page
        try:
            page.wait_for_selector(
                '[role="article"], div[aria-posinset], '
                'div[aria-label*="Comment"], div[aria-label*="Bình luận"], '
                'div[aria-label*="Write a comment"], div[aria-label*="Viết bình luận"]',
                state="visible",
                timeout=timeout,
            )
        except PlaywrightTimeout:
            logger.info("Post shell wait timed out — trying comment selectors anyway")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            logger.info("Network idle timed out on post page — continuing")

    def _dismiss_comment_interceptors(self) -> None:
        """Best-effort close for Facebook popups that can cover comment box."""
        page = self._page
        popup_selectors = [
            '[aria-label="Close"]',
            '[aria-label="Đóng"]',
            '[aria-label="Not now"]',
            '[aria-label="Không phải bây giờ"]',
            '[role="dialog"] [aria-label="Close"]',
            '[role="dialog"] [aria-label="Đóng"]',
            '[role="dialog"] div[role="button"]:has-text("Not now")',
            '[role="dialog"] div[role="button"]:has-text("Không phải bây giờ")',
            '[role="dialog"] div[role="button"]:has-text("Skip")',
            '[role="dialog"] div[role="button"]:has-text("Bỏ qua")',
        ]
        for selector in popup_selectors:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=1200):
                    button.click(timeout=3000)
                    page.wait_for_timeout(500)
                    logger.info("Dismissed Facebook popup via selector: %s", selector)
            except Exception:
                continue
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    def _wait_for_comment_box(self, timeout: int = 30000):
        """Wait for a visible Facebook comment textbox across common locales."""
        page = self._page
        selectors = [
            'div[aria-label="Write a comment"][contenteditable="true"]',
            'div[aria-label="Viết bình luận"][contenteditable="true"]',
            'div[aria-label="Write a public comment"][contenteditable="true"]',
            'div[role="textbox"][contenteditable="true"][aria-label*="Write a comment"]',
            'div[role="textbox"][contenteditable="true"][aria-label*="Viết bình luận"]',
            'div[role="textbox"][contenteditable="true"][aria-label*="Bình luận"]',
            'div[role="textbox"][contenteditable="true"][aria-label*="comment"]',
            'div[role="textbox"][contenteditable="true"][aria-label*="Comment"]',
            'div[role="textbox"][contenteditable="true"]',
            'form div[contenteditable="true"]',
            '[contenteditable="true"][data-lexical-editor="true"]',
        ]
        joined_selectors = ", ".join(selectors)
        try:
            page.wait_for_selector(joined_selectors, state="visible", timeout=timeout)
        except PlaywrightTimeout:
            logger.warning("Timed out waiting for Facebook comment textbox")
            return None

        for selector in selectors:
            try:
                box = page.locator(selector).first
                if box.is_visible(timeout=1500):
                    logger.info("Comment textbox found with selector: %s", selector)
                    return box
            except Exception:
                continue
        return None

    def _cleanup(self) -> None:
        """Close browser resources."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as exc:
            logger.warning("Cleanup error: %s", exc)
