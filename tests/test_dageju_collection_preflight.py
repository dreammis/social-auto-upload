"""Collection failures must block before any media-upload page is opened."""
import unittest
from unittest.mock import AsyncMock
from uploader.douyin_uploader.main import (DouYinVideo, DouyinPublishBlocked,
    _collection_present_in_manager_text, _approved_collection_selection_matches)


class CollectionPreflightTest(unittest.IsolatedAsyncioTestCase):
    def uploader(self):
        u = DouYinVideo.__new__(DouYinVideo)
        u._dageju_protected_submission = True
        u.collection_name = '中国在竞争中的底牌'
        return u

    def page(self, inventory, identity='大格局视界\n89535275463'):
        p = AsyncMock()
        p.inner_text.side_effect = [identity, inventory]
        return p

    async def test_existing_collection_passes(self):
        p = self.page('作品合集 (6)\n创建合集\n中国在竞争中的底牌\n编辑合集\n没有更多合集')
        await self.uploader()._preflight_approved_collection_before_upload(p)
        self.assertEqual(p.goto.await_count, 2)

    async def test_identity_wait_timeout_blocks_before_inventory(self):
        p = self.page('')
        p.wait_for_function.side_effect = TimeoutError('identity not hydrated')
        with self.assertRaisesRegex(DouyinPublishBlocked, 'collection_preflight_failed'):
            await self.uploader()._preflight_approved_collection_before_upload(p)
        self.assertEqual(p.goto.await_count, 1)
        p.inner_text.assert_not_awaited()

    async def test_missing_collection_blocks_before_upload(self):
        p = self.page('作品合集 (5)\n创建合集\n其他合集\n编辑合集\n没有更多合集')
        with self.assertRaisesRegex(DouyinPublishBlocked, 'collection_missing'):
            await self.uploader()._preflight_approved_collection_before_upload(p)
        self.assertFalse(any('/upload' in str(c) for c in p.goto.call_args_list))

    async def test_incomplete_inventory_blocks(self):
        p = self.page('作品合集 (6)\n创建合集\n中国在竞争中的底牌\n编辑合集')
        with self.assertRaisesRegex(DouyinPublishBlocked, 'inventory_unverifiable'):
            await self.uploader()._preflight_approved_collection_before_upload(p)

    async def test_wrong_identity_blocks_before_inventory(self):
        p = self.page('', identity='其他账号')
        with self.assertRaisesRegex(DouyinPublishBlocked, 'account_identity_unverified'):
            await self.uploader()._preflight_approved_collection_before_upload(p)
        self.assertEqual(p.goto.await_count, 1)

    def test_similar_name_is_not_a_match(self):
        self.assertFalse(_collection_present_in_manager_text('中国在竞争中的底牌第二季\n编辑合集', '中国在竞争中的底牌'))

    def test_selected_title_allows_observed_work_count_line(self):
        self.assertTrue(_approved_collection_selection_matches('中国科技与AI新基建\n共34个作品', '中国科技与AI新基建'))

    def test_selected_title_rejects_prefix_only_match(self):
        self.assertFalse(_approved_collection_selection_matches('中国在竞争中的底牌第二季', '中国在竞争中的底牌'))
