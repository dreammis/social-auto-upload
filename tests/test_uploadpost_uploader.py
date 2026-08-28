import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import sau_cli
from uploader.uploadpost_uploader import main as uploadpost


def make_video(directory: str) -> str:
    path = Path(directory) / "demo.mp4"
    path.write_bytes(b"fake-mp4-bytes")
    return str(path)


def fake_response(status_code=200, payload=None, text=""):
    def json_impl():
        if payload is None:
            raise ValueError("no json")
        return payload

    return SimpleNamespace(status_code=status_code, json=json_impl, text=text)


class UploadPostVideoTests(unittest.TestCase):
    def test_rejects_unknown_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                uploadpost.UploadPostVideo("t", make_video(tmp), [], ["myspace"])
            self.assertIn("myspace", str(ctx.exception))

    def test_requires_at_least_one_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                uploadpost.UploadPostVideo("t", make_video(tmp), [], [])

    def test_title_required_for_youtube(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                uploadpost.UploadPostVideo("", make_video(tmp), [], ["youtube"])

    def test_missing_file_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            uploadpost.UploadPostVideo("t", "/does/not/exist.mp4", [], ["tiktok"])

    def test_payload_appends_tags_as_hashtags(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = uploadpost.UploadPostVideo(
                "My title", make_video(tmp), ["ai", "#video"], ["tiktok", "instagram"]
            )
            payload = video._build_payload("my-profile")

        self.assertEqual(payload["user"], "my-profile")
        self.assertEqual(payload["title"], "My title #ai #video")
        self.assertEqual(payload["platform[]"], ["tiktok", "instagram"])

    def test_payload_includes_schedule_and_timezone(self):
        future = datetime.now() + timedelta(days=1)
        with tempfile.TemporaryDirectory() as tmp:
            video = uploadpost.UploadPostVideo(
                "t", make_video(tmp), [], ["tiktok"],
                publish_date=future, timezone="Asia/Shanghai",
            )
            payload = video._build_payload("my-profile")

        self.assertEqual(payload["scheduled_date"], future.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.assertEqual(payload["timezone"], "Asia/Shanghai")

    def test_upload_posts_multipart_with_apikey_scheme(self):
        captured = {}

        def fake_post(url, headers=None, data=None, files=None, timeout=None):
            captured.update(url=url, headers=headers, data=data, files=files)
            return fake_response(payload={"success": True, "request_id": "req_1"})

        with tempfile.TemporaryDirectory() as tmp:
            video = uploadpost.UploadPostVideo("t", make_video(tmp), [], ["tiktok"])
            with patch.object(uploadpost, "_credentials", return_value=("key", "profile")), \
                 patch.object(uploadpost.requests, "post", side_effect=fake_post):
                result = asyncio.run(video.main())

        self.assertEqual(result["request_id"], "req_1")
        self.assertEqual(captured["url"], "https://api.upload-post.com/api/upload")
        # Upload-Post API keys use the Apikey scheme; Bearer returns a misleading 401
        self.assertEqual(captured["headers"]["Authorization"], "Apikey key")
        self.assertIn("video", captured["files"])

    def test_upload_without_credentials_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = uploadpost.UploadPostVideo("t", make_video(tmp), [], ["tiktok"])
            with patch.object(uploadpost, "_credentials", return_value=("", "")):
                with self.assertRaises(RuntimeError) as ctx:
                    asyncio.run(video.main())
        self.assertIn("UPLOAD_POST_API_KEY", str(ctx.exception))

    def test_api_error_raises_with_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = uploadpost.UploadPostVideo("t", make_video(tmp), [], ["tiktok"])
            with patch.object(uploadpost, "_credentials", return_value=("key", "profile")), \
                 patch.object(uploadpost.requests, "post",
                              return_value=fake_response(401, {"error": "Invalid API key"})):
                with self.assertRaises(RuntimeError) as ctx:
                    asyncio.run(video.main())
        self.assertIn("Invalid API key", str(ctx.exception))

    def test_non_json_response_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = uploadpost.UploadPostVideo("t", make_video(tmp), [], ["tiktok"])
            with patch.object(uploadpost, "_credentials", return_value=("key", "profile")), \
                 patch.object(uploadpost.requests, "post",
                              return_value=fake_response(502, None, "<html>Bad Gateway</html>")):
                with self.assertRaises(RuntimeError) as ctx:
                    asyncio.run(video.main())
        self.assertIn("Bad Gateway", str(ctx.exception))


class UploadPostCredentialsTests(unittest.TestCase):
    def test_missing_credentials_is_invalid(self):
        with patch.object(uploadpost, "_credentials", return_value=("", "")):
            self.assertFalse(asyncio.run(uploadpost.check_credentials()))

    def test_unknown_profile_is_invalid(self):
        with patch.object(uploadpost, "_credentials", return_value=("key", "ghost")), \
             patch.object(uploadpost.requests, "get",
                          return_value=fake_response(200, {"profiles": [{"username": "real"}]})):
            self.assertFalse(asyncio.run(uploadpost.check_credentials()))

    def test_known_profile_is_valid(self):
        with patch.object(uploadpost, "_credentials", return_value=("key", "real")), \
             patch.object(uploadpost.requests, "get",
                          return_value=fake_response(200, {"profiles": [{"username": "real"}]})):
            self.assertTrue(asyncio.run(uploadpost.check_credentials()))

    def test_unauthorized_is_invalid(self):
        with patch.object(uploadpost, "_credentials", return_value=("bad", "real")), \
             patch.object(uploadpost.requests, "get", return_value=fake_response(401, {})):
            self.assertFalse(asyncio.run(uploadpost.check_credentials()))


class UploadPostCliTests(unittest.TestCase):
    def test_parser_accepts_upload_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = make_video(tmp)
            parser = sau_cli.build_parser()
            args = parser.parse_args([
                "uploadpost", "upload-video", "--file", video,
                "--title", "Hello", "--platforms", "tiktok,instagram",
            ])
        self.assertEqual(args.platform, "uploadpost")
        self.assertEqual(args.action, "upload-video")
        self.assertEqual(args.platforms, "tiktok,instagram")

    def test_dispatch_platforms_lists_every_platform(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["uploadpost", "platforms"])
        with patch("builtins.print") as printer:
            code = asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(code, 0)
        self.assertIn("tiktok", printer.call_args[0][0])

    def test_dispatch_check_reports_invalid(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["uploadpost", "check"])
        with patch.object(sau_cli, "check_uploadpost_credentials", AsyncMock(return_value=False)):
            code = asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(code, 1)

    def test_dispatch_check_reports_valid(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["uploadpost", "check"])
        with patch.object(sau_cli, "check_uploadpost_credentials", AsyncMock(return_value=True)):
            code = asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
