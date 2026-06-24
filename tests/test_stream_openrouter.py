"""Unit tests for _stream_openrouter — the shared SSE streaming generator."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest


def sse_events(generator):
    """Consume SSE generator and return list of (event_type, data_dict) tuples."""
    events = []
    for line in generator:
        event_type = ""
        data = {}
        for part in line.strip().split("\n"):
            if part.startswith("event: "):
                event_type = part[7:]
            elif part.startswith("data: "):
                try:
                    data = json.loads(part[6:])
                except (json.JSONDecodeError, TypeError):
                    data = {"raw": part[6:]}
        events.append((event_type, data))
    return events


def _chunk_event(content: str) -> str:
    return json.dumps({"choices": [{"delta": {"content": content}}]})


def _mock_resp_iter_lines(*chunks: str):
    """Build a response mock whose .iter_lines() yields SSE data chunks."""
    lines = []
    for c in chunks:
        lines.append(f"data: {_chunk_event(c)}".encode())
    lines.append(b"data: [DONE]")
    resp = Mock()
    resp.iter_lines.return_value = lines
    return resp


# ── helpers for key pool mocks ──────────────────────────────────────────

def _key_rows(*masked_ids):
    return [{"id": mid, "api_key": f"sk-key-{mid}", "masked": m} for mid, m in masked_ids]


# ── Tests ───────────────────────────────────────────────────────────────

class TestStreamOpenRouterSuccess:
    """Normal 200 response with streamed content."""

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_200_streams_content_and_done(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"), (2, "sk-****ef01"))
        mock_next_key.return_value = "sk-key-1"
        mock_post.return_value = _mock_resp_iter_lines("Hello", " world", "!")
        mock_post.return_value.status_code = 200

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        # Should emit: key_info, data(Hello), data( world), data(!), done
        types = [e[0] for e in events]
        assert types[0] == "key_info"
        assert events[0][1] == {"id": 1, "masked": "sk-****abcd"}
        assert types[1:4] == ["data", "data", "data"]
        assert types[-1] == "done"
        assert events[-1][1]["content"] == "Hello world!"
        assert mock_mark.call_count == 0

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_empty_stream_returns_done_with_empty_content(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"))
        mock_next_key.return_value = "sk-key-1"
        resp = Mock()
        resp.status_code = 200
        resp.iter_lines.return_value = [b"data: [DONE]"]
        mock_post.return_value = resp

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )
        assert events[-1][0] == "done"
        assert events[-1][1]["content"] == ""


class TestStreamOpenRouterRetryOn429:
    """429 rate-limit triggers key rotation."""

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_429_retries_with_next_key(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****aaaa"), (2, "sk-****bbbb"))
        mock_next_key.side_effect = ["sk-key-1", "sk-key-2"]

        resp_429 = Mock()
        resp_429.status_code = 429
        resp_200 = _mock_resp_iter_lines("ok")
        resp_200.status_code = 200
        mock_post.side_effect = [resp_429, resp_200]

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        # First key_info should be key-1, second key_info should be key-2
        key_infos = [e for e in events if e[0] == "key_info"]
        assert len(key_infos) == 2
        assert key_infos[0][1] == {"id": 1, "masked": "sk-****aaaa"}
        assert key_infos[1][1] == {"id": 2, "masked": "sk-****bbbb"}

        # verify _mark_rate_limited was called for the first key
        mock_mark.assert_called_once_with("sk-key-1")

        # verify final result
        assert events[-1][0] == "done"
        assert events[-1][1]["content"] == "ok"

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_multiple_429s_rotate_through_all_keys(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows(
            (1, "sk-****aa"), (2, "sk-****bb"), (3, "sk-****cc")
        )
        mock_next_key.side_effect = ["sk-key-1", "sk-key-2", "sk-key-3"]

        resp_429 = Mock()
        resp_429.status_code = 429
        resp_200 = _mock_resp_iter_lines("finally")
        resp_200.status_code = 200
        mock_post.side_effect = [resp_429, resp_429, resp_200]

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        key_infos = [e for e in events if e[0] == "key_info"]
        assert len(key_infos) == 3
        assert key_infos[0][1]["id"] == 1
        assert key_infos[1][1]["id"] == 2
        assert key_infos[2][1]["id"] == 3

        assert mock_mark.call_count == 2  # keys 1 and 2 marked
        assert mock_mark.call_args_list[0][0][0] == "sk-key-1"
        assert mock_mark.call_args_list[1][0][0] == "sk-key-2"

        assert events[-1][0] == "done"
        assert events[-1][1]["content"] == "finally"


class TestStreamOpenRouterKeyExhaustion:
    """All keys rate-limited — graceful error."""

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_all_keys_429_emits_exhaustion_error(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****aa"))
        mock_next_key.side_effect = ["sk-key-1"] * 2

        resp_429 = Mock()
        resp_429.status_code = 429
        mock_post.return_value = resp_429

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        # Last event should be the exhaustion error
        assert events[-1][0] == "error"
        assert "All API keys rate-limited" in events[-1][1]["message"]
        assert mock_mark.call_count == 1  # only 1 key to mark

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_no_keys_available_emits_error(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = []  # empty pool
        mock_next_key.return_value = ""

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        assert len(events) == 1
        assert events[0][0] == "error"
        assert "No API keys" in events[0][1]["message"]
        mock_post.assert_not_called()


class TestStreamOpenRouterApiError:
    """Non-200, non-429 responses yield error events."""

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_500_emits_error_with_message(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"))
        mock_next_key.return_value = "sk-key-1"

        resp = Mock()
        resp.status_code = 500
        resp.json.return_value = {"error": {"message": "Internal server error"}}
        mock_post.return_value = resp

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        # Should have key_info then error
        assert events[0][0] == "key_info"
        assert events[1][0] == "error"
        assert "Internal server error" in events[1][1]["message"]
        assert mock_mark.call_count == 0

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_401_emits_error_with_status(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"))
        mock_next_key.return_value = "sk-key-1"

        resp = Mock()
        resp.status_code = 401
        resp.json.return_value = {}
        mock_post.return_value = resp

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        assert events[1][0] == "error"
        assert "API error: 401" in events[1][1]["message"]


class TestStreamOpenRouterHttpException:
    """HTTP request-level exceptions yield error events."""

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_connection_error_emits_error(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"))
        mock_next_key.return_value = "sk-key-1"

        import requests as http_requests

        mock_post.side_effect = http_requests.ConnectionError("refused")

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        assert events[0][0] == "key_info"
        assert events[1][0] == "error"
        assert "refused" in events[1][1]["message"] or "ConnectionError" in events[1][1]["message"]


class TestStreamOpenRouterKeyInfo:
    """key_info SSE event contains correct key metadata."""

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_key_info_emitted_before_data(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((5, "sk-****zzzz"), (7, "sk-****yyyy"))
        mock_next_key.return_value = "sk-key-5"
        mock_post.return_value = _mock_resp_iter_lines("content")
        mock_post.return_value.status_code = 200

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        assert events[0][0] == "key_info"
        assert events[0][1] == {"id": 5, "masked": "sk-****zzzz"}
        assert events[1][0] == "data"

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_key_info_uses_first_matching_key(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        # Two keys with the same api_key — should match the first one
        mock_all_keys.return_value = _key_rows((99, "sk-****zz"), (100, "sk-****ww"))
        mock_next_key.return_value = "sk-key-99"
        mock_post.return_value = _mock_resp_iter_lines("ok")
        mock_post.return_value.status_code = 200

        events = sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        assert events[0][1]["id"] == 99


class TestStreamOpenRouterCustomParams:
    """max_tokens and temperature are passed through to the API call."""

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_model_param_passed_to_api(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"))
        mock_next_key.return_value = "sk-key-1"
        mock_post.return_value = _mock_resp_iter_lines("ok")
        mock_post.return_value.status_code = 200

        sse_events(
            _stream_openrouter("custom/model-id", [{"role": "user", "content": "hi"}])
        )

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "custom/model-id"
        assert call_kwargs["json"]["messages"] == [{"role": "user", "content": "hi"}]

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_custom_max_tokens_and_temperature(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"))
        mock_next_key.return_value = "sk-key-1"
        mock_post.return_value = _mock_resp_iter_lines("ok")
        mock_post.return_value.status_code = 200

        sse_events(
            _stream_openrouter(
                "test/model",
                [{"role": "user", "content": "hi"}],
                max_tokens=500,
                temperature=0.3,
            )
        )

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["max_tokens"] == 500
        assert call_kwargs["json"]["temperature"] == 0.3

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_default_max_tokens_and_temperature(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"))
        mock_next_key.return_value = "sk-key-1"
        mock_post.return_value = _mock_resp_iter_lines("ok")
        mock_post.return_value.status_code = 200

        sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["max_tokens"] == 2000
        assert call_kwargs["json"]["temperature"] == 0.7


class TestStreamOpenRouterConnectTimeout:
    """Verify timeout=(10, 120) is used."""

    @patch("web_runner._get_all_keys")
    @patch("web_runner._get_next_key")
    @patch("web_runner.http_requests.post")
    @patch("web_runner._mark_rate_limited")
    def test_connect_timeout_is_tuple(
        self, mock_mark, mock_post, mock_next_key, mock_all_keys
    ):
        from web_runner import _stream_openrouter

        mock_all_keys.return_value = _key_rows((1, "sk-****abcd"))
        mock_next_key.return_value = "sk-key-1"
        mock_post.return_value = _mock_resp_iter_lines("ok")
        mock_post.return_value.status_code = 200

        sse_events(
            _stream_openrouter("test/model", [{"role": "user", "content": "hi"}])
        )

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] == (10, 120)
