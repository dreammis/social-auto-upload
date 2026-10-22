"""Real Flask WSGI dispatch with synthetic uploader/auth boundaries only."""
import importlib.util
import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class BatchProductTests(unittest.TestCase):
    def test_douyin_product_fields(self):
        for link, title in [("", ""), ("https://example.invalid/product", ""), ("", "synthetic product"), ("https://example.invalid/product", "synthetic product")]:
            with self.subTest(link=bool(link), title=bool(title)):
                records = []

                class RecordingUploader:
                    def __init__(self, *args, **kwargs):
                        records.append((args, kwargs))

                    async def main(self):
                        pass

                    async def douyin_upload_video(self):
                        pass

                def forbidden(*args, **kwargs):
                    raise AssertionError("authentication boundary must not execute")

                conf = types.ModuleType("conf")
                conf.BASE_DIR = ROOT / "synthetic-batch-root"
                auth = types.ModuleType("myUtils.auth")
                auth.check_cookie = forbidden
                login = types.ModuleType("myUtils.login")
                for name in ["get_tencent_cookie", "douyin_cookie_gen", "get_ks_cookie", "xiaohongshu_cookie_gen"]:
                    setattr(login, name, forbidden)
                modules = {"conf": conf, "myUtils.auth": auth, "myUtils.login": login}
                for platform, cls in [("douyin", "DouYinVideo"), ("ks", "KSVideo"), ("tencent", "TencentVideo"), ("xiaohongshu", "XiaoHongShuVideo")]:
                    name = f"uploader.{platform}_uploader.main"
                    modules[name] = types.ModuleType(name)
                    setattr(modules[name], cls, RecordingUploader)

                with patch.dict(sys.modules, modules):
                    helper_spec = importlib.util.spec_from_file_location("utils.files_times", ROOT / "utils/files_times.py")
                    helper = importlib.util.module_from_spec(helper_spec)
                    helper_spec.loader.exec_module(helper)
                    with patch.dict(sys.modules, {"utils.files_times": helper}):
                        dispatch_spec = importlib.util.spec_from_file_location("myUtils.postVideo", ROOT / "myUtils/postVideo.py")
                        dispatch = importlib.util.module_from_spec(dispatch_spec)
                        dispatch_spec.loader.exec_module(dispatch)
                        with patch.dict(sys.modules, {"myUtils.postVideo": dispatch}):
                            backend_spec = importlib.util.spec_from_file_location("batch_backend_under_test", ROOT / "sau_backend.py")
                            backend = importlib.util.module_from_spec(backend_spec)
                            with patch.dict(sys.modules, {"batch_backend_under_test": backend}):
                                backend_spec.loader.exec_module(backend)

                                def close_recording_coroutine(coroutine, *, debug=False):
                                    coroutine.close()

                                with patch.object(dispatch.asyncio, "run", side_effect=close_recording_coroutine), redirect_stdout(io.StringIO()):
                                    response = backend.app.test_client().post("/postVideoBatch", json=[{
                                        "type": 3, "title": "synthetic video", "tags": ["tag"],
                                        "fileList": ["synthetic.mp4"], "accountList": ["synthetic.account"],
                                        "enableTimer": False, "productLink": link, "productTitle": title,
                                    }])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["code"], 200)
                self.assertEqual(len(records), 1)
                args, kwargs = records[0]
                self.assertEqual(args[5], "")
                self.assertEqual(args[6], link)
                self.assertEqual(args[7], title)
                self.assertEqual(args[3], 0)


if __name__ == "__main__":
    unittest.main()
