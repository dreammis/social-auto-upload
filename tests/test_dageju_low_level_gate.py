"""Offline entrypoint regression; no cookies, browser, or platform requests."""

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from uploader.douyin_uploader import main as douyin_main
import sau_cli


class LowerLevelApprovalTests(unittest.IsolatedAsyncioTestCase):
    def video(self, cookie="/tmp/douyin_dagaju.json", media="/tmp/unapproved.mp4"):
        return douyin_main.DouYinVideo("候选标题", media, ["测试"], 0, cookie)

    async def test_protected_video_rejected_before_cookie_or_browser(self):
        uploader = self.video()
        with (
            patch.object(uploader, "validate_upload_args", AsyncMock()) as validate,
            patch.object(douyin_main, "launch_douyin_context", AsyncMock()) as launch,
            self.assertRaisesRegex(RuntimeError, "BLOCKED_APPROVAL_GATE"),
        ):
            await uploader.upload(object())
        validate.assert_not_awaited()
        launch.assert_not_awaited()

    async def test_direct_legacy_main_rejected_before_playwright(self):
        class CheckedVideo(douyin_main.DouYinVideo):
            pass

        uploader = CheckedVideo("候选标题", "/tmp/legacy.mp4", [], 0,
                                "/some/old/location/douyin_dagaju.json")
        with (
            patch.object(douyin_main, "async_playwright") as driver,
            self.assertRaisesRegex(RuntimeError, "BLOCKED_APPROVAL_GATE"),
        ):
            await uploader.main()
        driver.assert_not_called()

    async def test_protected_video_path_rejected_even_with_other_cookie_name(self):
        from dageju_autopilot.approval_gate import ACCOUNT_VIDEOS

        target = ACCOUNT_VIDEOS / "fixture" / "renders" / "video.mp4"
        uploader = self.video(cookie="/tmp/douyin_other.json", media=str(target))
        with self.assertRaisesRegex(RuntimeError, "BLOCKED_APPROVAL_GATE"):
            await uploader.upload(object())

    async def test_note_rejected_before_browser(self):
        note = douyin_main.DouYinNote(["/tmp/image.jpg"], "文字", [], 0,
                                     "/tmp/douyin_dagaju.json")
        with (
            patch.object(note, "validate_upload_args", AsyncMock()) as validate,
            patch.object(douyin_main, "launch_douyin_context", AsyncMock()) as launch,
            self.assertRaisesRegex(RuntimeError, "BLOCKED_APPROVAL_GATE"),
        ):
            await note.upload(object())
        validate.assert_not_awaited()
        launch.assert_not_awaited()

    async def test_direct_note_entrypoint_blocked_before_playwright(self):
        note = douyin_main.DouYinNote(["/tmp/image.jpg"], "文字", [], 0,
                                     "/tmp/douyin_dagaju.json")
        with (
            patch.object(douyin_main, "async_playwright") as driver,
            self.assertRaisesRegex(RuntimeError, "BLOCKED_APPROVAL_GATE"),
        ):
            await note.douyin_upload_note()
        driver.assert_not_called()

    async def test_other_account_reaches_existing_validation(self):
        uploader = self.video(cookie="/tmp/douyin_other.json",
                              media="/tmp/other_account_clip.mp4")
        with (
            patch.object(uploader, "validate_upload_args",
                         AsyncMock(side_effect=ValueError("existing_validator_called"))) as validate,
            patch.object(douyin_main, "launch_douyin_context", AsyncMock()) as launch,
            self.assertRaisesRegex(ValueError, "existing_validator_called"),
        ):
            await uploader.upload(object())
        validate.assert_awaited_once()
        launch.assert_not_awaited()

    def collection_page(self, *, selected_text=None, has_placeholder=True):
        page = MagicMock()
        trigger = MagicMock()
        trigger.count = AsyncMock(return_value=1)
        trigger.first = trigger
        selected = MagicMock()
        selected.count = AsyncMock(return_value=1 if selected_text is not None else 0)
        selected.first = selected
        selected.inner_text = AsyncMock(return_value=selected_text or "")
        placeholder = MagicMock()
        placeholder.count = AsyncMock(return_value=1 if has_placeholder else 0)
        trigger.locator.side_effect = lambda query: (
            selected if query == ".semi-select-selection-text" else placeholder
        )
        page.locator.return_value = trigger
        return page

    async def test_explicit_no_collection_requires_visible_empty_form(self):
        video = self.video()
        video._dageju_protected_submission = True
        video.collection_name = ""
        await video.apply_collection(self.collection_page())
        with self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                    "approved_empty_collection_unverifiable"):
            await video.apply_collection(self.collection_page(selected_text="旧合集"))
        with self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                    "approved_empty_collection_unverifiable"):
            await video.apply_collection(self.collection_page(has_placeholder=False))

    async def test_approved_collection_requires_matching_visible_selection(self):
        video = self.video()
        video._dageju_protected_submission = True
        video.collection_name = "金融"
        await video._verify_approved_collection_form(self.collection_page(selected_text="金融"))
        with self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                    "approved_collection_selection_mismatch"):
            await video._verify_approved_collection_form(self.collection_page(selected_text="科技"))
        with self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                    "approved_collection_selection_unverifiable"):
            await video._verify_approved_collection_form(self.collection_page())

    async def test_missing_collection_selector_blocks_approved_upload(self):
        video = self.video()
        video._dageju_protected_submission = True
        video.collection_name = ""
        page = self.collection_page()
        page.locator.return_value.count = AsyncMock(return_value=0)
        with self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                    "approved_collection_selector_missing"):
            await video.apply_collection(page)

    async def test_missing_collection_option_blocks_approved_upload(self):
        video = self.video()
        video._dageju_protected_submission = True
        video.collection_name = "不存在的合集"
        page = MagicMock()
        trigger = MagicMock()
        trigger.first = trigger
        trigger.count = AsyncMock(return_value=1)
        selection = MagicMock()
        selection.click = AsyncMock()
        trigger.locator.return_value = selection
        option = MagicMock()
        option.filter.return_value = option
        option.count = AsyncMock(return_value=0)
        page.locator.side_effect = lambda query: (
            trigger if query.startswith('[class*="select-collection-"]') else option
        )
        page.wait_for_timeout = AsyncMock()
        video._clear_blocking_overlays = AsyncMock()
        with self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                    "approved_collection_option_missing"):
            await video.apply_collection(page)

    async def test_cover_editor_unavailable_blocks_without_fallback(self):
        video = self.video()
        video._dageju_protected_submission = True
        video.thumbnail_portrait_path = "/tmp/isolated-cover.jpg"
        page = MagicMock()
        page.evaluate = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.wait_for_selector = AsyncMock(side_effect=TimeoutError("mock dialog unavailable"))
        cover_area = MagicMock()
        cover_area.first = cover_area
        cover_area.filter.return_value = cover_area
        cover_area.count = AsyncMock(return_value=1)
        cover_area.wait_for = AsyncMock()
        cover_area.hover = AsyncMock()
        page.locator.return_value = cover_area
        title = MagicMock()
        title.first = title
        title.count = AsyncMock(return_value=0)
        page.get_by_text.return_value = title
        with (
            patch.object(douyin_main, "_native_click", AsyncMock()) as click,
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_cover_editor_not_opened"),
        ):
            await video.set_thumbnail(page)
        self.assertEqual(click.await_count, 5)

    async def test_only_one_submit_attempt_and_recheck_before_click(self):
        video = self.video()
        video._dageju_protected_submission = True
        button = MagicMock()
        button.click = AsyncMock()
        with patch.object(douyin_main, "_enforce_dageju_upload_approval",
                          side_effect=RuntimeError("BLOCKED_APPROVAL_GATE: approval_revoked")) as gate:
            with self.assertRaisesRegex(RuntimeError, "approval_revoked"):
                await video._click_approved_publish_once(button)
        gate.assert_called_once_with(video)
        button.click.assert_not_awaited()

        button.click = AsyncMock(side_effect=TimeoutError("mock platform timeout"))
        with (
            patch.object(douyin_main, "_enforce_dageju_upload_approval") as gate,
            patch("dageju_autopilot.approval_gate.reserve_submission_attempt",
                  return_value=(True, "submission_attempt_reserved")) as reserve,
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_submission_ambiguous_do_not_retry"),
        ):
            await video._click_approved_publish_once(button)
        gate.assert_called_once_with(video)
        reserve.assert_called_once_with(Path(video.file_path))
        button.click.assert_awaited_once()

        button.click.reset_mock()
        with (
            patch.object(douyin_main, "_enforce_dageju_upload_approval") as gate,
            patch("dageju_autopilot.approval_gate.reserve_submission_attempt",
                  return_value=(False, "submission_already_attempted_do_not_retry")),
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_submission_already_attempted_do_not_retry"),
        ):
            await video._click_approved_publish_once(button)
        gate.assert_called_once_with(video)
        button.click.assert_not_awaited()

    async def test_protected_manager_navigation_requires_platform_readback(self):
        video = self.video()
        video._dageju_protected_submission = True
        page = MagicMock()
        page.wait_for_url = AsyncMock(return_value=None)
        with self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                    "approved_platform_result_unverified_do_not_retry"):
            await video._await_submission_navigation_once(page)
        page.wait_for_url.assert_awaited_once()

    async def test_protected_submit_navigation_timeout_never_reclicks(self):
        video = self.video()
        video._dageju_protected_submission = True
        button = MagicMock()
        button.click = AsyncMock(return_value=None)
        page = MagicMock()
        page.wait_for_url = AsyncMock(side_effect=TimeoutError("mock delayed manager page"))
        with (
            patch.object(douyin_main, "_enforce_dageju_upload_approval"),
            patch("dageju_autopilot.approval_gate.reserve_submission_attempt",
                  return_value=(True, "submission_attempt_reserved")),
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_submission_ambiguous_do_not_retry"),
        ):
            await video._click_approved_publish_once(button)
            await video._await_submission_navigation_once(page)
        button.click.assert_awaited_once()
        page.wait_for_url.assert_awaited_once()

    async def test_nonprotected_navigation_keeps_legacy_success_path(self):
        video = self.video(cookie="/tmp/other.json")
        page = MagicMock()
        page.wait_for_url = AsyncMock(return_value=None)
        await video._await_submission_navigation_once(page)
        page.wait_for_url.assert_awaited_once()

    async def test_protected_upload_page_timeout_never_reaches_editor(self):
        video = self.video()
        video._dageju_protected_submission = True
        page = MagicMock()
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.wait_for_url = AsyncMock(side_effect=[None, TimeoutError("mock page not ready"), TimeoutError("mock old page not ready")])
        upload_field = MagicMock()
        upload_field.first = upload_field
        upload_field.count = AsyncMock(return_value=1)
        upload_field.wait_for = AsyncMock()
        upload_field.set_input_files = AsyncMock()
        page.locator.return_value = upload_field
        context = MagicMock(pages=[page])
        with (
            patch.object(douyin_main, "monotonic", side_effect=[0, 181]),
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_publish_page_timeout"),
        ):
            await video._upload_in_context(context)
        upload_field.set_input_files.assert_awaited_once()

    async def test_protected_upload_processing_timeout_and_no_auto_reupload(self):
        video = self.video()
        video._dageju_protected_submission = True
        page = MagicMock()
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.wait_for_url = AsyncMock(return_value=None)
        upload_field = MagicMock()
        upload_field.first = upload_field
        upload_field.count = AsyncMock(return_value=1)
        upload_field.wait_for = AsyncMock()
        upload_field.set_input_files = AsyncMock()
        in_progress = MagicMock()
        in_progress.count = AsyncMock(return_value=0)
        page.locator.side_effect = lambda query: (
            in_progress if query.startswith('[class^="long-card"]') else upload_field
        )
        context = MagicMock(pages=[page])
        with (
            patch.object(douyin_main, "monotonic", side_effect=[0, 1, 2, 902]),
            patch.object(video, "fill_title_and_description", AsyncMock()),
            patch.object(video, "handle_upload_error", AsyncMock()) as retry,
            patch.object(douyin_main.asyncio, "sleep", AsyncMock()),
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_media_upload_timeout"),
        ):
            await video._upload_in_context(context)
        retry.assert_not_awaited()

    def isolated_upload_page(self, *, failure=False, state_error=False, secondary_verify=False):
        """Build an offline publishing page with no browser or account access."""
        page = MagicMock()
        page.goto = AsyncMock()
        page.wait_for_url = AsyncMock(return_value=None)
        page.wait_for_timeout = AsyncMock()
        page.evaluate = AsyncMock()
        upload_field = MagicMock()
        upload_field.first = upload_field
        upload_field.count = AsyncMock(return_value=1)
        upload_field.wait_for = AsyncMock()
        upload_field.set_input_files = AsyncMock()
        progress = MagicMock()
        progress.count = AsyncMock(side_effect=RuntimeError("mock state unavailable")
                                   if state_error else None,
                                   return_value=1 if secondary_verify else 0)
        upload_failed = MagicMock()
        upload_failed.count = AsyncMock(return_value=1 if failure else 0)
        sms = MagicMock()
        sms.first = sms
        sms.count = AsyncMock(return_value=1 if secondary_verify else 0)
        sms.is_visible = AsyncMock(return_value=secondary_verify)
        other = MagicMock()
        other.count = AsyncMock(return_value=0)
        page.locator.side_effect = lambda query: (
            progress if query.startswith('[class^="long-card"]') else
            upload_failed if query.startswith('div.progress-div >') else
            sms if query.startswith('input[placeholder*="验证码"]') else
            other if query.startswith('[class^="info"]') else upload_field
        )
        context = MagicMock(pages=[page])
        return page, context, upload_field

    async def test_explicit_upload_failure_blocks_without_reupload(self):
        video = self.video()
        video._dageju_protected_submission = True
        page, context, field = self.isolated_upload_page(failure=True)
        with (
            patch.object(video, "fill_title_and_description", AsyncMock()),
            patch.object(video, "handle_upload_error", AsyncMock()) as retry,
            patch.object(douyin_main.asyncio, "sleep", AsyncMock()),
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_media_upload_failed_manual_review"),
        ):
            await video._upload_in_context(context)
        field.set_input_files.assert_awaited_once()
        retry.assert_not_awaited()

    async def test_upload_status_exception_blocks_without_reupload(self):
        video = self.video()
        video._dageju_protected_submission = True
        page, context, field = self.isolated_upload_page(state_error=True)
        with (
            patch.object(video, "fill_title_and_description", AsyncMock()),
            patch.object(video, "handle_upload_error", AsyncMock()) as retry,
            patch.object(douyin_main.asyncio, "sleep", AsyncMock()),
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_media_upload_state_unverifiable"),
        ):
            await video._upload_in_context(context)
        field.set_input_files.assert_awaited_once()
        retry.assert_not_awaited()

    async def test_secondary_verification_blocks_without_requesting_code_or_submitting(self):
        video = self.video()
        video._dageju_protected_submission = True
        video.declaration = "无需添加自主声明"
        page, context, field = self.isolated_upload_page(secondary_verify=True)
        with (
            patch.object(video, "fill_title_and_description", AsyncMock()),
            patch.object(video, "apply_self_declaration", AsyncMock()),
            patch.object(video, "apply_collection", AsyncMock()),
            patch.object(video, "set_thumbnail", AsyncMock()),
            patch.object(video, "_submit_sms_verify_code", AsyncMock()) as sms_submit,
            patch.object(video, "_click_approved_publish_once", AsyncMock()) as publish,
            patch.object(douyin_main.asyncio, "sleep", AsyncMock()),
            self.assertRaisesRegex(douyin_main.DouyinPublishBlocked,
                                   "approved_secondary_verification_requires_user"),
        ):
            await video._upload_in_context(context)
        field.set_input_files.assert_awaited_once()
        sms_submit.assert_not_awaited()
        publish.assert_not_awaited()
        page.get_by_text.assert_not_called()

    async def test_sau_cli_rechecks_exact_scheduled_slot_before_account_access(self):
        from dageju_autopilot import approval_gate

        request = sau_cli.DouyinVideoUploadRequest(
            account_name="dagaju", video_file=Path("/tmp/fake-video.mp4"),
            title="test", description="test", tags=["测试"],
            publish_date=datetime(2026, 10, 20, 9, 0),
            publish_strategy=douyin_main.DOUYIN_PUBLISH_STRATEGY_SCHEDULED,
            declaration="无需添加自主声明", collection_name="",
        )
        with (
            patch.object(approval_gate, "verify_upload_request",
                         return_value=(False, "mock_no_signed_approval")) as gate,
            patch.object(sau_cli, "resolve_account_file") as cookies,
            self.assertRaisesRegex(RuntimeError, "mock_no_signed_approval"),
        ):
            await sau_cli.upload_video(request)
        self.assertEqual(gate.call_args.kwargs["scheduled_at"], "2026-10-20 09:00")
        self.assertEqual(gate.call_args.kwargs["collection"], "")
        cookies.assert_not_called()


if __name__ == "__main__":
    unittest.main()
