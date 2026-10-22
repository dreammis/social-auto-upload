"""Offline dispatch tests; uploader coroutines only record metadata, never publish."""
import importlib.util
import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2030, 1, 1, 12, 0, tzinfo=tz)


class PostVideoScheduleTests(unittest.TestCase):
    def test_dispatch_schedule(self):
        platforms = [
            ("douyin", "DouYinVideo", "post_video_DouYin"),
            ("ks", "KSVideo", "post_video_ks"),
            ("tencent", "TencentVideo", "post_video_tencent"),
            ("xiaohongshu", "XiaoHongShuVideo", "post_video_xhs"),
        ]
        for platform, class_name, function_name in platforms:
            for enabled, start_days in [(False, 0), (True, 0), (True, 3)]:
                with self.subTest(platform=platform, enabled=enabled, start_days=start_days):
                    records = []

                    class RecordingUploader:
                        def __init__(self, *args, **kwargs):
                            records.append((args, kwargs))

                        async def main(self):
                            pass

                        async def douyin_upload_video(self):
                            pass

                    conf = types.ModuleType("conf")
                    conf.BASE_DIR = ROOT / "synthetic-dispatch-root"
                    modules = {"conf": conf}
                    for name, cls, _ in platforms:
                        module_name = f"uploader.{name}_uploader.main"
                        module = types.ModuleType(module_name)
                        setattr(module, cls, RecordingUploader)
                        modules[module_name] = module

                    with patch.dict(sys.modules, modules):
                        # Load the real helper and dispatcher without importing browser code.
                        spec = importlib.util.spec_from_file_location(
                            "utils.files_times", ROOT / "utils/files_times.py"
                        )
                        helper = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(helper)
                        with patch.dict(sys.modules, {"utils.files_times": helper}):
                            spec = importlib.util.spec_from_file_location(
                                "schedule_dispatch_under_test", ROOT / "myUtils/postVideo.py"
                            )
                            dispatch = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(dispatch)
                            def close_recording_coroutine(coroutine, *, debug=False):
                                coroutine.close()

                            with patch.object(helper, "datetime", FixedDateTime), redirect_stdout(io.StringIO()), patch.object(dispatch.asyncio, "run", side_effect=close_recording_coroutine):
                                getattr(dispatch, function_name)(
                                    "synthetic title", ["one.mp4", "two.mp4"], ["tag"],
                                    ["one.synthetic", "two.synthetic"],
                                    enableTimer=enabled, videos_per_day=1,
                                    daily_times=[16], start_days=start_days,
                                )

                    self.assertEqual(len(records), 4)
                    for index, (args, kwargs) in enumerate(records):
                        expected = (
                            FixedDateTime(2030, 1, 1, 16) + timedelta(days=1 + start_days + index // 2)
                            if enabled else 0
                        )
                        self.assertEqual(args[3], expected)
                        if enabled:
                            self.assertIsInstance(args[3], datetime)
                        if platform != "ks":
                            self.assertEqual(
                                kwargs.get("publish_strategy", "immediate"),
                                "scheduled" if enabled else "immediate",
                            )
                        self.assertEqual(Path(args[1]).name, ["one.mp4", "two.mp4"][index // 2])
                        self.assertEqual(Path(args[4]).name, ["one.synthetic", "two.synthetic"][index % 2])


if __name__ == "__main__":
    unittest.main()
