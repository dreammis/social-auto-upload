"""Smoke tests for the Tencent note (image-text / 图文) uploader wiring.

These tests intentionally avoid touching a real browser/cookie file. They only
verify the *structural* pieces added when TencentNote.upload_note_content was
implemented:

1. ``TencentNote.switch_to_note_mode`` / ``upload_note_images`` /
   ``fill_note_title_and_tags`` / ``_is_in_note_mode`` are real coroutine
   methods (no longer raising NotImplementedError).
2. ``TencentNote.validate_upload_args`` enforces the 18-image cap and accepts
   well-formed input.
3. ``sau_cli`` exposes ``tencent upload-note`` as a CLI subcommand with the
   expected argument surface.
4. ``web_runner.PLATFORM_CONFIG['tencent']['note']`` now advertises note
   support so the backend /api/upload/note route can accept a tencent request.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

import pytest


def _make_fake_page(upload_selectors_visible: bool = True, has_image_input: bool = True) -> object:
    """Build a minimal stand-in for a Playwright ``Page`` for unit-level assertions."""

    class _Locator:
        def __init__(self, count: int = 1, visible: bool = True, attr: str | None = None) -> None:
            self._count = count
            self._visible = visible
            self._attr = attr

        async def count(self) -> int:
            return self._count

        async def is_visible(self) -> bool:
            return self._visible

        async def is_disabled(self) -> bool:
            return False

        async def get_attribute(self, _name: str) -> str | None:
            return self._attr

        async def is_visible_safe(self) -> bool:
            # ``is_visible`` can raise on detached nodes — emulate that branch.
            return self._visible

        async def wait_for(self, *_args, **_kwargs) -> None:
            return None

        async def click(self, *_args, **_kwargs) -> None:
            return None

        async def first(self) -> "_Locator":
            return self

    class _Page:
        def __init__(self) -> None:
            self.url = "https://channels.weixin.qq.com/platform/post/create"
            self.calls: list[str] = []

        def locator(self, selector: str) -> _Locator:
            self.calls.append(selector)
            if "input[type=\"file\"]" in selector:
                return _Locator(count=1 if has_image_input else 0, visible=has_image_input)
            if "div.weui-desktop-loading" in selector or "uploading" in selector:
                # Pretend nothing is loading and publish button is enabled.
                return _Locator(count=0, visible=False)
            if "form-btns button" in selector:
                return _Locator(count=1, visible=True, attr="weui-desktop-btn weui-desktop-btn_primary")
            if "div.input-editor" in selector:
                return _Locator(count=1, visible=True)
            if "div:has-text" in selector or "get_by_text" in selector or "[role=\"tab\"]" in selector:
                return _Locator(count=1 if upload_selectors_visible else 0, visible=upload_selectors_visible)
            return _Locator(count=0, visible=False)

        async def wait_for_load_state(self, *_args, **_kwargs) -> None:
            return None

        async def wait_for_timeout(self, *_args, **_kwargs) -> None:
            return None

        async def wait_for_url(self, *_args, **_kwargs) -> None:
            return None

        async def goto(self, _url: str) -> None:
            self.url = _url

        async def keyboard(self) -> object:
            class _Kbd:
                async def press(self, *_args, **_kwargs) -> None:
                    return None

                async def type(self, *_args, **_kwargs) -> None:
                    return None

            return _Kbd()

    return _Page()


def _build_tencent_note(tmp_path: Path, image_count: int = 2) -> tuple:
    """Lazy import to keep collection resilient against missing playwright deps."""
    from uploader.tencent_uploader.main import TencentNote, TENCENT_NOTE_MAX_IMAGES

    cookie_file = tmp_path / "cookies" / "tencent_account.json"
    cookie_file.parent.mkdir(parents=True, exist_ok=True)
    cookie_file.write_text("{}", encoding="utf-8")

    images: list[Path] = []
    for idx in range(image_count):
        img = tmp_path / f"note_{idx}.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
        images.append(img)

    note = TencentNote(
        image_paths=images,
        note="正文示例",
        tags=["图文", "示例"],
        publish_date=0,
        account_file=str(cookie_file),
        title="图文标题示例",
        publish_strategy="immediate",
        debug=False,
        headless=True,
        is_draft=False,
    )
    return note, TENCENT_NOTE_MAX_IMAGES


def test_tencent_note_methods_are_coroutines() -> None:
    """All three previously-stubbed methods must be real coroutines now."""
    from uploader.tencent_uploader.main import TencentNote

    for name in ("_is_in_note_mode", "switch_to_note_mode", "upload_note_images", "fill_note_title_and_tags"):
        method = getattr(TencentNote, name, None)
        assert method is not None, f"TencentNote.{name} is missing"
        assert inspect.iscoroutinefunction(method), f"TencentNote.{name} must be a coroutine function"


def test_tencent_note_validate_caps_excess_images(tmp_path: Path) -> None:
    """When more than ``TENCENT_NOTE_MAX_IMAGES`` images are supplied, the uploader truncates the list after validation."""
    note, _ = _build_tencent_note(tmp_path, image_count=19)
    asyncio.run(note.validate_upload_args())
    assert len(note.image_paths) == 18


def test_switch_to_note_mode_no_crash_with_truthy_locators(tmp_path: Path) -> None:
    """``switch_to_note_mode`` URL-direct or text-based switch returns cleanly even when mode detection can't be confirmed."""
    from uploader.tencent_uploader.main import TencentNote

    note, _ = _build_tencent_note(tmp_path)
    fake_page = _make_fake_page(upload_selectors_visible=True)
    asyncio.run(note.switch_to_note_mode(fake_page))  # should not raise
    assert any(selector.startswith("http") or "图文" in selector or "tab" in selector for selector in fake_page.calls) or \
           fake_page.url.endswith("?type=image")


def test_tencent_upload_note_images_runs_with_stubbed_page(tmp_path: Path) -> None:
    """Image upload should find the file input and never raise on the happy path."""
    note, _ = _build_tencent_note(tmp_path)
    fake_page = _make_fake_page(upload_selectors_visible=True, has_image_input=True)
    asyncio.run(note.upload_note_images(fake_page))


def test_fill_note_title_and_tags_types_through_stubbed_page(tmp_path: Path) -> None:
    """Title / body / tags are emitted via keyboard.type without exceptions on a contenteditable stub."""
    note, _ = _build_tencent_note(tmp_path)
    fake_page = _make_fake_page(upload_selectors_visible=True)
    asyncio.run(note.fill_note_title_and_tags(fake_page))


def test_cli_tencent_upload_note_parser_has_expected_flags() -> None:
    """sau_cli must register tencent upload-note with --images/--title/--note/--tags/--schedule/--draft."""
    import sau_cli

    parser = sau_cli.build_parser()
    args = parser.parse_args(
        [
            "tencent",
            "upload-note",
            "--account", "demo",
            "--images", "/tmp/a.png", "/tmp/b.png",
            "--title", "demo",
            "--note", "正文",
            "--tags", "a,b",
            "--schedule", "2099-01-01 10:00",
            "--draft",
            "--headless",
        ]
    )
    assert args.platform == "tencent"
    assert args.action == "upload-note"
    assert args.account == "demo"
    assert args.images == [Path("/tmp/a.png"), Path("/tmp/b.png")]
    assert args.title == "demo"
    assert args.note == "\u6b63\u6587"
    assert args.tags == "a,b"
    assert args.schedule is not None
    assert args.draft is True
    assert args.headless is True


def test_web_runner_marks_tencent_supporting_notes() -> None:
    """Backend must report tencent.note=True so /api/upload/note can dispatch a tencent request."""
    # Lazy import: load lazily to avoid running Flask app init side-effects on collection.
    import importlib
    web_runner = importlib.import_module("web_runner")  # noqa: WPS433 - intentional lazy import

    cfg = web_runner.PLATATFORM_CONFIG["tencent"]
    assert cfg["note"] is True, "tencent entry should advertise note support"
    assert "tencent" in web_runner.NOTE_PLATFORMS
