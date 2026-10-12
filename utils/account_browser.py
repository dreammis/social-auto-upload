"""Persistent browser sessions owned by one platform and cookie-file identity."""
import hashlib
import json
import os
import re
import sys
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path


def account_profile_dir(account_file, platform):
    if not re.fullmatch(r"[a-z0-9_-]+", platform):
        raise ValueError("Invalid browser profile platform")
    account = Path(account_file).expanduser().resolve()
    identity = os.path.normcase(str(account))
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", account.stem)[:48]
    return account.parent / "browser_profiles" / platform / f"{name}-{suffix}"


@contextmanager
def profile_lock(profile):
    profile.mkdir(parents=True, exist_ok=True)
    # Keep the file: removing a lock file permits races between waiting processes.
    with (profile / '.sau.lock').open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f'账号浏览器正在使用中，请等待当前任务结束: {profile}') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


async def import_storage_state(context, state):
    await context.add_cookies(state.get('cookies', []))
    for origin in state.get('origins', []):
        if not origin.get('localStorage'):
            continue
        page = await context.new_page()
        try:
            async def serve_empty(route):
                await route.fulfill(status=200, content_type='text/html', body='<!doctype html>')
            await page.route('**/*', serve_empty)
            await page.goto(origin['origin'], wait_until='domcontentloaded')
            await page.evaluate('items => { for (const {name, value} of items) localStorage.setItem(name, value); }', origin['localStorage'])
        finally:
            await page.close()


@asynccontextmanager
async def account_browser(playwright, account_file, platform, *, headless, **options):
    account = Path(account_file).expanduser().resolve()
    profile = account_profile_dir(account, platform)
    with profile_lock(profile):
        marker = profile / '.sau-imported'
        # Read before starting Chrome so malformed legacy files cannot leak a process.
        state = None
        if account.exists():
            state = json.loads(account.read_text(encoding='utf-8-sig'))
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile), headless=headless, channel='chromium', **options
        )
        try:
            if state is not None:
                if not marker.exists():
                    await import_storage_state(context, state)
                else:
                    # Session cookies need restoring even with a persistent profile.
                    await context.add_cookies(state.get('cookies', []))
            if not marker.exists():
                marker.write_text('1', encoding='ascii')
            yield context
        finally:
            failed = sys.exc_info()[0] is not None
            try:
                await context.close()
            except Exception:
                if not failed:
                    raise
