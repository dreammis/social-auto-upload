"""Shared Playwright browser manager for reliable persistent sessions.

This module intentionally does not hide automation signals or spoof browser
fingerprints. It centralizes legitimate reliability controls: persistent profile
storage, explicit proxy config, user-selected locale/timezone, timeout defaults,
and sensitive-value redaction for logs/errors.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)

DEFAULT_LOCALE = os.getenv("BROWSER_LOCALE", "vi-VN")
DEFAULT_TIMEZONE_ID = os.getenv("BROWSER_TIMEZONE_ID", "Asia/Ho_Chi_Minh")
DEFAULT_PROFILE_ROOT = Path(os.getenv("BROWSER_PROFILE_ROOT", "/app/cookiesFile"))
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}
DEFAULT_USER_AGENT = os.getenv(
    "BROWSER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36",
)

T = TypeVar("T")

_SECRET_PATTERNS = [
    re.compile(r"(https?://[^:/\s]+:)([^@/\s]+)(@[^\s]+)", re.IGNORECASE),
    re.compile(r"(socks5?h?://[^:/\s]+:)([^@/\s]+)(@[^\s]+)", re.IGNORECASE),
    re.compile(r"(proxy[_-]?authorization\s*[:=]\s*)([^\s,;]+)", re.IGNORECASE),
    re.compile(r"(authorization\s*[:=]\s*bearer\s+)([a-z0-9._\-]+)", re.IGNORECASE),
    re.compile(r"((?:access|refresh|session)[_-]?token\s*[:=]\s*)([^\s,;]+)", re.IGNORECASE),
    re.compile(r"(cookie\s*[:=]\s*)([^\n]+)", re.IGNORECASE),
    re.compile(r"('password'\s*:\s*')[^']+(')", re.IGNORECASE),
    re.compile(r"(\"password\"\s*:\s*\")[^\"]+(\")", re.IGNORECASE),
]


def redact_sensitive(value: Any) -> str:
    """Return a log-safe string with common credentials removed."""
    text = str(value)
    for pattern in _SECRET_PATTERNS:
        if "password" in pattern.pattern and pattern.groups == 2:
            text = pattern.sub(r"\1***REDACTED***\2", text)
        else:
            text = pattern.sub(r"\1***REDACTED***\3" if pattern.groups >= 3 else r"\1***REDACTED***", text)
    return text


def _safe_profile_name(account_id: str | int) -> str:
    raw = str(account_id or "default")
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", raw).strip("._")
    return safe or "default"


def _normalize_proxy(proxy_url: str | None) -> dict[str, str] | None:
    if not proxy_url:
        return None
    parsed = urlparse(proxy_url)
    if not parsed.scheme or not parsed.hostname or not parsed.port:
        raise ValueError("Invalid proxy_url format; expected http://user:pass@host:port")

    config: dict[str, str] = {
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
    }
    if parsed.username:
        config["username"] = unquote(parsed.username)
    if parsed.password:
        config["password"] = unquote(parsed.password)
    return config


@dataclass
class BrowserSession:
    playwright: Any
    context: Any
    page: Any
    user_data_dir: Path

    def close(self) -> None:
        try:
            if self.context:
                self.context.close()
        finally:
            if self.playwright:
                self.playwright.stop()


class BrowserManager:
    """Create persistent Playwright contexts for uploaders.

    The manager keeps real browser storage per account. It does not apply stealth
    plugins, fingerprint randomization, webdriver patches, or WebRTC overrides.
    """

    def __init__(
        self,
        playwright: Any,
        account_id: str | int,
        proxy_url: str | None = None,
        headless: bool = True,
        locale: str | None = None,
        timezone_id: str | None = None,
        user_agent: str | None = None,
        viewport: dict[str, int] | None = None,
        profile_root: str | Path | None = None,
        action_timeout_ms: int = 30000,
    ):
        self.playwright = playwright
        self.account_id = account_id
        self.proxy_url = proxy_url
        self.headless = headless
        self.locale = locale or DEFAULT_LOCALE
        self.timezone_id = timezone_id or DEFAULT_TIMEZONE_ID
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.viewport = viewport or DEFAULT_VIEWPORT
        self.profile_root = Path(profile_root) if profile_root else DEFAULT_PROFILE_ROOT
        self.action_timeout_ms = action_timeout_ms

    @property
    def user_data_dir(self) -> Path:
        return self.profile_root / f"profile_{_safe_profile_name(self.account_id)}"

    def _launch_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "headless": self.headless,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "viewport": self.viewport,
            "user_agent": self.user_agent,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        }
        proxy_config = _normalize_proxy(self.proxy_url)
        if proxy_config:
            kwargs["proxy"] = proxy_config
            logger.info("Browser proxy configured: %s", proxy_config["server"])
        return kwargs

    def launch_persistent_session(self, cookies: list[dict] | None = None) -> BrowserSession:
        """Launch Chromium persistent context and return first page session."""
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        try:
            context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                **self._launch_kwargs(),
            )
            context.set_default_timeout(self.action_timeout_ms)
            if cookies:
                context.add_cookies(cookies)
                logger.info("Loaded %d cookies into persistent browser profile", len(cookies))
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(self.action_timeout_ms)
            logger.info("Browser profile active: %s", self.user_data_dir)
            return BrowserSession(
                playwright=self.playwright,
                context=context,
                page=page,
                user_data_dir=self.user_data_dir,
            )
        except Exception as exc:
            raise RuntimeError(f"Browser launch failed: {redact_sensitive(exc)}") from exc

    @staticmethod
    def with_backoff(
        action: Callable[[], T],
        attempts: int = 3,
        base_delay: float = 0.5,
        on_retry: Callable[[int, Exception], None] | None = None,
    ) -> T:
        """Run an action with small exponential backoff for flaky DOM timing."""
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return action()
            except Exception as exc:  # pragma: no cover - caller decides retry scope
                last_exc = exc
                if attempt >= attempts:
                    break
                if on_retry:
                    on_retry(attempt, exc)
                time.sleep(base_delay * (2 ** (attempt - 1)))
        raise last_exc or RuntimeError("Backoff action failed")
