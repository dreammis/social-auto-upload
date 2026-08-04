"""Persistent browser profiles shared by login, checks, and uploads."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from patchright.async_api import Playwright

from conf import BASE_DIR


PROFILE_ROOT = BASE_DIR / "browser_profiles"


def profile_dir(platform: str, account_file: str | Path) -> Path:
    """Return the stable profile directory for one platform/account pair."""
    account_name = Path(account_file).stem
    path = PROFILE_ROOT / f"{platform}_{account_name}"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def launch_profile(
    playwright: Playwright,
    platform: str,
    account_file: str | Path,
    *,
    headless: bool,
    executable_path: str | None = None,
    channel: str | None = None,
    args: list[str] | None = None,
    permissions: list[str] | None = None,
):
    """Launch a persistent context, seeding it from legacy storage_state once."""
    account_path = Path(account_file)
    profile = profile_dir(platform, account_path)
    options = {"headless": headless}
    if executable_path:
        options["executable_path"] = executable_path
    elif channel:
        options["channel"] = channel
    browser_args = list(args or [])
    if "--disable-crash-reporter" not in browser_args:
        browser_args.append("--disable-crash-reporter")
    options["args"] = browser_args
    if permissions:
        options["permissions"] = permissions

    try:
        context = await playwright.chromium.launch_persistent_context(
            str(profile), **options
        )
    except Exception as first_exc:
        # A stale Chromium lock or a transient Patchright driver disconnect
        # should not consume a scheduled publish. Keep the stable profile and
        # retry once in an isolated recovery profile.
        await asyncio.sleep(1)
        recovery = Path(
            tempfile.mkdtemp(prefix=f".recovery-{platform}-", dir=str(PROFILE_ROOT))
        )
        try:
            context = await playwright.chromium.launch_persistent_context(
                str(recovery), **options
            )
        except Exception:
            raise first_exc

    # launch_persistent_context has no storage_state option. Import the legacy
    # account file explicitly so existing logins can seed the new profile.
    if account_path.exists():
        try:
            state = json.loads(account_path.read_text(encoding="utf-8"))
            cookies = state.get("cookies") or []
            if cookies:
                await context.add_cookies(cookies)
            local_storage = {
                item["origin"]: item.get("localStorage") or []
                for item in state.get("origins") or []
                if item.get("origin")
            }
            if local_storage:
                await context.add_init_script(
                    script=(
                        "const saved = "
                        + json.dumps(local_storage, ensure_ascii=False)
                        + "; const entries = saved[location.origin];"
                        " if (entries) for (const item of entries)"
                        " localStorage.setItem(item.name, item.value);"
                    )
                )
        except (OSError, json.JSONDecodeError, TypeError, KeyError):
            # A malformed legacy file will be reported by the platform check;
            # do not prevent the persistent browser from opening.
            pass

    return context
