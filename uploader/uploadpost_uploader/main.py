# -*- coding: utf-8 -*-
"""Upload-Post uploader (official platform APIs, no browser).

The other uploaders here drive a real browser with a saved cookie. That is the only
option for 抖音 / 小红书 / 视频号 / B站, but for the international platforms it means
cookies that expire, selectors that break on every UI redesign, and a headful Chrome
on the box.

This uploader takes the API route for those platforms through Upload-Post
(https://upload-post.com): one API key, one HTTP request, no cookie files and nothing
to re-login. Accounts are connected once in the Upload-Post dashboard.

It is worth calling out why this does *not* have the drawback that made
`youtube_uploader` choose browser automation: with the raw YouTube Data API, videos
uploaded by an unaudited project are force-locked to private. Upload-Post is an
audited provider, so videos publish public right away without each user having to
pass Google's compliance review.

Platforms: TikTok, Instagram, YouTube, Facebook, LinkedIn, X (Twitter), Threads,
Pinterest, Bluesky, Reddit, Telegram, Discord, Google Business Profile.

Docs: https://docs.upload-post.com
"""
import asyncio
from datetime import datetime
from pathlib import Path

import requests

from uploader.base_video import BaseVideoUploader
from utils.log import uploadpost_logger

API_BASE = "https://api.upload-post.com"

SUPPORTED_PLATFORMS = (
    "tiktok",
    "instagram",
    "youtube",
    "facebook",
    "linkedin",
    "x",
    "threads",
    "pinterest",
    "bluesky",
    "reddit",
    "telegram",
    "discord",
    "google_business",
)

# Platforms that reject an upload without a title.
TITLE_REQUIRED_PLATFORMS = ("youtube", "reddit")


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _credentials() -> tuple[str, str]:
    """Read the Upload-Post credentials from conf.py"""
    try:
        from conf import UPLOAD_POST_API_KEY, UPLOAD_POST_USER
    except ImportError:
        UPLOAD_POST_API_KEY, UPLOAD_POST_USER = "", ""
    return (UPLOAD_POST_API_KEY or "").strip(), (UPLOAD_POST_USER or "").strip()


def _headers(api_key: str) -> dict:
    # Upload-Post API keys use the `Apikey` scheme — `Bearer` returns a misleading 401.
    return {"Authorization": f"Apikey {api_key}"}


def _check_credentials_sync() -> bool:
    api_key, user = _credentials()
    if not api_key or not user:
        return False
    try:
        response = requests.get(
            f"{API_BASE}/api/uploadposts/users",
            headers=_headers(api_key),
            timeout=30,
        )
    except requests.RequestException as exc:
        uploadpost_logger.error(_msg("❌", f"无法连接 Upload-Post: {exc}"))
        return False

    if response.status_code == 401:
        uploadpost_logger.error(_msg("❌", "Upload-Post API key 无效（注意用 Apikey 而不是 Bearer）"))
        return False
    if response.status_code >= 400:
        uploadpost_logger.error(_msg("❌", f"Upload-Post 返回 {response.status_code}: {response.text[:200]}"))
        return False

    profiles = response.json().get("profiles") or []
    names = {p.get("username") for p in profiles if isinstance(p, dict)}
    if names and user not in names:
        uploadpost_logger.error(
            _msg("❌", f"profile '{user}' 不存在，可用的有: {', '.join(sorted(n for n in names if n))}")
        )
        return False
    return True


async def check_credentials() -> bool:
    """凭证是否可用：API key 有效且 conf.py 里配置的 profile 存在。"""
    return await asyncio.to_thread(_check_credentials_sync)


class UploadPostVideo(BaseVideoUploader):
    """Publish one video to several platforms in a single API request."""

    def __init__(
        self,
        title: str,
        file_path: str,
        tags: list[str],
        platforms: list[str],
        publish_date: datetime | int = 0,
        description: str = "",
        timezone: str | None = None,
        extra_params: dict | None = None,
    ):
        self.title = title
        self.file_path = self.validate_video_file(file_path)
        self.tags = tags or []
        self.platforms = self._validate_platforms(platforms)
        self.publish_date = self.validate_publish_date(publish_date)
        self.description = description
        self.timezone = timezone
        self.extra_params = extra_params or {}

        if not self.title.strip() and any(p in TITLE_REQUIRED_PLATFORMS for p in self.platforms):
            raise ValueError(f"发布到 {', '.join(TITLE_REQUIRED_PLATFORMS)} 必须提供标题")

    @staticmethod
    def _validate_platforms(platforms: list[str]) -> list[str]:
        cleaned = [p.strip().lower() for p in (platforms or []) if p and p.strip()]
        if not cleaned:
            raise ValueError("至少需要指定一个发布平台")
        unknown = [p for p in cleaned if p not in SUPPORTED_PLATFORMS]
        if unknown:
            raise ValueError(
                f"不支持的平台: {', '.join(unknown)}。支持: {', '.join(SUPPORTED_PLATFORMS)}"
            )
        return cleaned

    def _build_payload(self, user: str) -> dict:
        title = self.title
        if self.tags:
            hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in self.tags)
            title = f"{title} {hashtags}".strip()

        payload = {
            "user": user,
            "title": title[:2200],
            "platform[]": self.platforms,
            "async_upload": "true",
        }
        if self.description:
            payload["description"] = self.description
        if isinstance(self.publish_date, datetime):
            payload["scheduled_date"] = self.publish_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            if self.timezone:
                payload["timezone"] = self.timezone

        for key, value in self.extra_params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                value = "true" if value else "false"
            payload[key] = value if isinstance(value, (list, tuple)) else str(value)

        return payload

    def _upload_sync(self) -> dict:
        api_key, user = _credentials()
        if not api_key or not user:
            raise RuntimeError(
                "Upload-Post 未配置。请在 conf.py 中设置 UPLOAD_POST_API_KEY 和 UPLOAD_POST_USER"
                "（免费额度见 https://upload-post.com）。"
            )

        payload = self._build_payload(user)
        uploadpost_logger.info(_msg("📤", f"正在发布到 {', '.join(self.platforms)}: {self.file_path.name}"))

        with open(self.file_path, "rb") as video:
            response = requests.post(
                f"{API_BASE}/api/upload",
                headers=_headers(api_key),
                data=payload,
                files={"video": (self.file_path.name, video, "video/mp4")},
                timeout=600,
            )

        try:
            result = response.json()
        except ValueError:
            raise RuntimeError(f"Upload-Post 返回了非 JSON 响应 ({response.status_code}): {response.text[:200]}")

        if response.status_code >= 400 or result.get("success") is False:
            message = result.get("message") or result.get("error") or response.text[:200]
            raise RuntimeError(f"发布失败 ({response.status_code}): {message}")

        request_id = result.get("request_id")
        if isinstance(self.publish_date, datetime):
            uploadpost_logger.success(
                _msg("🗓️", f"已定时到 {self.publish_date}（request_id={request_id}）")
            )
        else:
            uploadpost_logger.success(_msg("✅", f"已提交发布（request_id={request_id}）"))
        return result

    def _status_sync(self, request_id: str) -> dict:
        api_key, _ = _credentials()
        response = requests.get(
            f"{API_BASE}/api/uploadposts/status",
            headers=_headers(api_key),
            params={"request_id": request_id},
            timeout=30,
        )
        try:
            return response.json()
        except ValueError:
            return {"success": False, "message": response.text[:200]}

    async def status(self, request_id: str) -> dict:
        """查询某次发布的状态（各平台结果）。"""
        return await asyncio.to_thread(self._status_sync, request_id)

    async def main(self) -> dict:
        return await asyncio.to_thread(self._upload_sync)
