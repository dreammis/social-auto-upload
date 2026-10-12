import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from utils.account_browser import account_browser, account_profile_dir, profile_lock


class AccountBrowserTests(unittest.TestCase):
    def test_profiles_are_stable_and_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / 'douyin_a.json'
            self.assertEqual(account_profile_dir(a, 'douyin'), account_profile_dir(a, 'douyin'))
            self.assertNotEqual(account_profile_dir(a, 'douyin'), account_profile_dir(a.with_name('douyin_b.json'), 'douyin'))
            self.assertNotEqual(account_profile_dir(a, 'douyin'), account_profile_dir(a, 'kuaishou'))
            self.assertNotEqual(account_profile_dir(a, 'douyin'), account_profile_dir(a.parent / 'other' / a.name, 'douyin'))

    def test_lock_rejects_same_account_and_releases_after_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / 'one'
            with profile_lock(profile):
                with self.assertRaisesRegex(RuntimeError, '正在使用'):
                    with profile_lock(profile):
                        pass
                with profile_lock(Path(tmp) / 'two'):
                    pass
            with profile_lock(profile):
                pass

    def test_cookie_import_and_profile_reuse(self):
        async def run(tmp):
            account = Path(tmp) / 'a.json'
            cookies = [{'name': 'test', 'value': 'one', 'domain': 'example.com', 'path': '/'}]
            account.write_text(json.dumps({'cookies': cookies, 'origins': []}), encoding='utf-8')
            context = MagicMock()
            context.add_cookies = AsyncMock()
            context.close = AsyncMock()
            pw = MagicMock()
            pw.chromium.launch_persistent_context = AsyncMock(return_value=context)
            for _ in range(2):
                async with account_browser(pw, account, 'douyin', headless=True):
                    pass
            self.assertEqual(context.add_cookies.await_count, 2)
            context.add_cookies.assert_awaited_with(cookies)
            self.assertEqual(context.close.await_count, 2)
            paths = [call.kwargs['user_data_dir'] for call in pw.chromium.launch_persistent_context.call_args_list]
            self.assertEqual(paths[0], paths[1])
        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(run(tmp))

    def test_failure_closes_context_and_releases_lock(self):
        async def run(tmp):
            account = Path(tmp) / 'a.json'
            context = MagicMock()
            context.close = AsyncMock(side_effect=OSError('close failed'))
            pw = MagicMock()
            pw.chromium.launch_persistent_context = AsyncMock(return_value=context)
            with self.assertRaisesRegex(ValueError, 'original failure'):
                async with account_browser(pw, account, 'douyin', headless=True):
                    raise ValueError('original failure')
            context.close.assert_awaited_once()
            with profile_lock(account_profile_dir(account, 'douyin')):
                pass
        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(run(tmp))

    def test_invalid_cookie_does_not_launch_browser(self):
        async def run(tmp):
            account = Path(tmp) / 'a.json'
            account.write_text('bad json', encoding='utf-8')
            pw = MagicMock()
            pw.chromium.launch_persistent_context = AsyncMock()
            with self.assertRaises(ValueError):
                async with account_browser(pw, account, 'douyin', headless=True):
                    pass
            pw.chromium.launch_persistent_context.assert_not_awaited()
        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(run(tmp))
