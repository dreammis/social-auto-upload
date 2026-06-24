"""Tests for `/api/ai/generate/stream` multi-turn `messages` entry-point.

Covers `specs/ai-stream-multimessage`:
  - Multi-turn `messages` forwarded verbatim to `_stream_openrouter` (bypasses single-turn assembly).
  - Legacy single-turn `prompt` / `system_prompt` / `images` path still works as fallback.
  - Oversized `messages` array rejected with a single SSE error event.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest


# ─── Fixture ──────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    """Flask test client built via the package's create_app() factory.

    web_runner does not expose a module-level `app` (only `create_app()`),
    so each test instantiates its own. The factory also calls init_db(),
    which is safe under the conftest.py sqlite3.connect patch.
    """
    import web_runner as wr

    application = wr.create_app()
    application.config["TESTING"] = True
    with application.test_client() as client:
        yield client


def _done_event(content: str = "ok") -> str:
    return f"event: done\ndata: {json.dumps({'content': content})}\n\n"


# ─── Multi-turn path: messages forwarded verbatim ──────────────────────────


class TestMultiTurnForwardedVerbatim:
    """`messages` array reaches `_stream_openrouter` exactly as posted."""

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_non_empty_messages_forwarded_exactly(self, mock_stream, _keys, app):
        msgs = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Follow-up"},
        ]
        mock_stream.return_value = iter([_done_event("reply")])

        resp = app.post(
            "/api/ai/generate/stream",
            json={"model": "google/gemma-4-26b-a4b-it:free", "messages": msgs},
        )

        assert resp.status_code == 200
        # `_stream_openrouter` is called with (model, full_messages) verbatim
        args, _ = mock_stream.call_args
        assert args[0] == "google/gemma-4-26b-a4b-it:free"
        assert args[1] == msgs  # exact same list, same order, same content
        assert len(args[1]) == 4

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_messages_take_precedence_over_prompt(self, mock_stream, _keys, app):
        """When BOTH `messages` and `prompt` are present, `messages` wins.

        The legacy system-prompt wrapping is NOT executed.
        """
        msgs = [{"role": "user", "content": "raw user turn"}]
        mock_stream.return_value = iter([_done_event("ok")])

        resp = app.post(
            "/api/ai/generate/stream",
            json={
                "model": "m",
                "messages": msgs,
                "prompt": "should_be_ignored",
                "system_prompt": "should_be_ignored",
                "platform": "douyin",
                "images": ["data:image/png;base64,AA=="],
            },
        )

        assert resp.status_code == 200
        args, _ = mock_stream.call_args
        sent = args[1]
        # No auto-injected system prompt; no auto-wrapped multimodal user.
        assert sent == msgs
        assert len(sent) == 1
        assert sent[0]["role"] == "user"

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_model_value_is_propagated(self, mock_stream, _keys, app):
        msgs = [{"role": "user", "content": "x"}]
        mock_stream.return_value = iter([_done_event("ok")])

        app.post(
            "/api/ai/generate/stream",
            json={"model": "deepseek/deepseek-chat-v3-0324:free", "messages": msgs},
        )

        args, _ = mock_stream.call_args
        assert args[0] == "deepseek/deepseek-chat-v3-0324:free"

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_default_model_when_omitted(self, mock_stream, _keys, app):
        msgs = [{"role": "user", "content": "x"}]
        mock_stream.return_value = iter([_done_event("ok")])

        app.post(
            "/api/ai/generate/stream",
            json={"messages": msgs},  # no model
        )

        args, _ = mock_stream.call_args
        assert args[0] == "google/gemma-4-26b-a4b-it:free"


# ─── Multi-turn path: cap ─────────────────────────────────────────────────


class TestMultiTurnMessageCap:
    """Sized array is rejected with an SSE error event; never reaches the API."""

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_oversized_messages_rejected_with_sse_error(self, mock_stream, _keys, app):
        msgs = [{"role": "user", "content": f"turn {i}"} for i in range(31)]
        mock_stream.return_value = iter([])  # should not be invoked

        resp = app.post(
            "/api/ai/generate/stream",
            json={"model": "m", "messages": msgs},
        )

        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        # Exactly one SSE error event
        assert body.startswith("event: error\ndata: ")
        assert "Too many messages in conversation" in body
        assert "max 30" in body
        assert mock_stream.call_count == 0  # never called the LLM

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_exactly_30_messages_accepted(self, mock_stream, _keys, app):
        """Boundary: length == cap is allowed (strict greater-than)."""
        msgs = [{"role": "user", "content": f"turn {i}"} for i in range(30)]
        mock_stream.return_value = iter([_done_event("ok")])

        resp = app.post(
            "/api/ai/generate/stream",
            json={"model": "m", "messages": msgs},
        )

        assert resp.status_code == 200
        assert mock_stream.call_count == 1
        args, _ = mock_stream.call_args
        assert len(args[1]) == 30


# ─── Single-turn fallback: preserved ──────────────────────────────────────


class TestSingleTurnFallbackPreserved:
    """Empty / missing `messages` reuses the legacy single-turn assembly."""

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_empty_messages_list_falls_back_when_prompt_given(
        self, mock_stream, _keys, app
    ):
        mock_stream.return_value = iter([_done_event("ok")])

        resp = app.post(
            "/api/ai/generate/stream",
            json={
                "model": "m",
                "messages": [],            # empty list → NOT the multi-turn path
                "prompt": "give me a title",
                "platform": "douyin",
            },
        )

        assert resp.status_code == 200
        args, _ = mock_stream.call_args
        sent = args[1]
        # Legacy assembly: 2 messages (system, user); system = PLATFORM_PROMPTS['douyin']
        assert len(sent) == 2
        assert sent[0]["role"] == "system"
        assert "抖音" in sent[0]["content"]
        assert sent[1] == {"role": "user", "content": "give me a title"}

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_missing_messages_field_falls_back_with_default_platform_prompt(
        self, mock_stream, _keys, app
    ):
        mock_stream.return_value = iter([_done_event("ok")])

        resp = app.post(
            "/api/ai/generate/stream",
            json={"model": "m", "prompt": "hello"},  # no `messages`
        )

        assert resp.status_code == 200
        args, _ = mock_stream.call_args
        sent = args[1]
        assert len(sent) == 2
        assert sent[0]["role"] == "system"
        # No platform → DEFAULT_SYSTEM_PROMPT
        assert sent[0]["content"].startswith("你是一个专业的社交媒体内容创作者")
        assert sent[1] == {"role": "user", "content": "hello"}

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_missing_messages_field_with_images_assembles_multimodal(
        self, mock_stream, _keys, app
    ):
        mock_stream.return_value = iter([_done_event("ok")])

        resp = app.post(
            "/api/ai/generate/stream",
            json={
                "model": "m",
                "prompt": "describe",
                "images": ["data:image/png;base64,AA=="],
            },
        )

        assert resp.status_code == 200
        args, _ = mock_stream.call_args
        sent = args[1]
        assert len(sent) == 2
        assert sent[0]["role"] == "system"
        # User message is a multimodal list (image + text), not a plain string
        assert isinstance(sent[1]["content"], list)
        kinds = [item["type"] for item in sent[1]["content"]]
        assert "image_url" in kinds
        assert "text" in kinds

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_explicit_system_prompt_in_single_turn_path(
        self, mock_stream, _keys, app
    ):
        """Caller-supplied `system_prompt` overrides PLATFORM_PROMPTS default."""
        mock_stream.return_value = iter([_done_event("ok")])

        app.post(
            "/api/ai/generate/stream",
            json={
                "model": "m",
                "prompt": "hi",
                "platform": "douyin",  # would otherwise inject 抖音 prompt
                "system_prompt": "CUSTOM_SYSTEM",
            },
        )

        args, _ = mock_stream.call_args
        sent = args[1]
        assert sent[0]["content"] == "CUSTOM_SYSTEM"

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_non_list_messages_value_falls_back(self, mock_stream, _keys, app):
        """Defensive: garbage `messages` value (string, dict) → single-turn fallback."""
        mock_stream.return_value = iter([_done_event("ok")])

        for bogus in ("just a string", {"foo": "bar"}, 42):
            mock_stream.reset_mock()
            resp = app.post(
                "/api/ai/generate/stream",
                json={"model": "m", "messages": bogus, "prompt": "hi"},
            )
            assert resp.status_code == 200
            args, _ = mock_stream.call_args
            sent = args[1]
            # Single-turn path: a [system, user] pair
            assert len(sent) == 2
            assert sent[0]["role"] == "system"
            assert sent[1] == {"role": "user", "content": "hi"}


# ─── Empty-everything error path ──────────────────────────────────────────


class TestEmptyRequestGuard:
    """When NEITHER `messages` nor `prompt` nor `images` is supplied, error."""

    @patch("web_runner.routes.ai._has_any_api_key", return_value=True)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_empty_messages_and_no_prompt_emits_sse_error(
        self, mock_stream, _keys, app
    ):
        # Both multi-turn path and single-turn path have nothing.
        resp = app.post(
            "/api/ai/generate/stream",
            json={"model": "m", "messages": []},  # empty list, no prompt, no images
        )

        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert body.startswith("event: error\ndata: ")
        assert "Prompt or image is required" in body
        assert mock_stream.call_count == 0

    @patch("web_runner.routes.ai._has_any_api_key", return_value=False)
    @patch("web_runner.routes.ai._stream_openrouter")
    def test_no_api_key_short_circuits(self, mock_stream, _keys, app):
        # Even a valid multi-turn request is rejected if no keys are configured.
        resp = app.post(
            "/api/ai/generate/stream",
            json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "AI service not configured" in body
        assert mock_stream.call_count == 0
