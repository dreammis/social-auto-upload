from queue import Queue
import unittest
from unittest.mock import AsyncMock, patch

import sau_backend


class BackendLoginRouteTests(unittest.TestCase):
    def test_run_async_function_routes_bilibili_login(self):
        status_queue = Queue()
        with patch("sau_backend.bilibili_cookie_gen", new=AsyncMock()) as mock_login:
            sau_backend.run_async_function("5", "creator", status_queue)
        mock_login.assert_awaited_once_with("creator", status_queue)

    def test_run_async_function_routes_baijiahao_login(self):
        status_queue = Queue()
        with patch("sau_backend.baijiahao_cookie_gen_for_frontend", new=AsyncMock()) as mock_login:
            sau_backend.run_async_function("6", "creator", status_queue)
        mock_login.assert_awaited_once_with("creator", status_queue)

    def test_run_async_function_routes_tiktok_login(self):
        status_queue = Queue()
        with patch("sau_backend.tiktok_cookie_gen_for_frontend", new=AsyncMock()) as mock_login:
            sau_backend.run_async_function("7", "creator", status_queue)
        mock_login.assert_awaited_once_with("creator", status_queue)


if __name__ == "__main__":
    unittest.main()
