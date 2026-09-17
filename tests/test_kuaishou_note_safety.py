"""Offline logic tests using the public atlas contract documented in docs/.

These receipts are simulated, not evidence of a real account or public post.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sau_cli
from uploader.ks_uploader import main as ks
from uploader.ks_uploader.note_evidence import (
    FINISH, PRE, SINGLE, SUBMIT, NoteEvidence, NoteSubmissionError,
)

IDS = {"fileId": "test-file", "atlasId": "test-atlas"}
KEYS = ["first", "second"]


def run(coro):
    return asyncio.run(coro)


def request(path, body):
    return SimpleNamespace(url="https://cp.kuaishou.com" + path, method="POST", post_data_json=body)


def response(path, body, data, *, req=None):
    return SimpleNamespace(request=req or request(path, body), ok=True, json=AsyncMock(return_value=data))


def receipts(count=2):
    yield response(PRE, {"pictureCount": 2}, {"result": 1, "data": {**IDS, "uploadInfo": [{"blobKey": key} for key in KEYS]}})
    for key in KEYS[:count]:
        yield response(SINGLE, {**IDS, "blobKey": key}, {"result": 1, "data": {"url": [{"url": "https://example.invalid/" + key}]}})


def page_stub():
    page = MagicMock()
    page.route = AsyncMock()
    publish = MagicMock(wait_for=AsyncMock(), click=AsyncMock())
    page.get_by_text.return_value = publish
    modal = MagicMock(count=AsyncMock(return_value=0))
    modal.first = modal
    page.locator.return_value = modal
    return page, publish, modal


def note():
    return ks.KSNote(["one.png", "two.png"], "Original body", ["a", "b", "c", "d"], 0, "unused.json", title="Original title", debug=False)


async def ready(evidence):
    for item in receipts():
        await evidence.capture(item)
    assert await evidence.wait_uploaded(timeout=.05) == (IDS, KEYS)


async def submit(evidence, code=1, *, keys=None, identity=None, respond=True):
    await evidence.capture(response(FINISH, {**IDS, "blobKey": KEYS if keys is None else keys}, {"result": 1}))
    route = SimpleNamespace(request=request(SUBMIT, IDS if identity is None else identity), continue_=AsyncMock(), abort=AsyncMock())
    await evidence.guard_submit(route)
    if route.continue_.await_count and respond:
        await evidence.capture(response(SUBMIT, {}, {"result": code}, req=route.request))
    return route


@pytest.mark.parametrize("case", ["missing", "no_uploading_text", "refused", "bad_count", "duplicate_key", "foreign_image", "no_image_url", "http_error", "unreadable_json"])
def test_incomplete_upload_never_submits(case):
    async def scenario():
        page, publish, _ = page_stub()
        ev = NoteEvidence(page, 2)
        items = list(receipts(1 if case == "missing" else 2))
        if case == "no_uploading_text":
            items = []  # No UI text is deliberately irrelevant.
        elif case == "refused":
            items[-1].json.return_value = {"result": -1}
        elif case == "bad_count":
            items[0].request.post_data_json["pictureCount"] = 1
        elif case == "duplicate_key":
            items[0].json.return_value["data"]["uploadInfo"] = [{"blobKey": "first"}] * 2
        elif case == "foreign_image":
            items[-1].request.post_data_json["atlasId"] = "another"
        elif case == "no_image_url":
            items[-1].json.return_value = {"result": 1, "data": {}}
        elif case == "http_error":
            items[-1].ok = False
        elif case == "unreadable_json":
            items[-1].json.side_effect = ValueError("bad JSON")
        async def prepare(_):
            for item in items:
                ev.on_response(item)
        app = note()
        app._prepare_note_content = prepare
        original_wait = ev.wait_uploaded
        ev.wait_uploaded = lambda: original_wait(timeout=.02)
        with patch.object(ks, "NoteEvidence", return_value=ev):
            with pytest.raises(NoteSubmissionError) as exc:
                await app.upload_note_content(page)
        assert exc.value.status == "not_submitted"
        publish.click.assert_not_awaited()
        assert not ev.tasks
    run(scenario())


@pytest.mark.parametrize("confirmation", [False, True])
@pytest.mark.parametrize("delay", [0, .015])
def test_single_submission_with_or_without_confirmation(confirmation, delay):
    async def scenario():
        page, publish, modal = page_stub()
        ev = NoteEvidence(page, 2)
        await ready(ev)
        tasks = []
        async def send():
            await asyncio.sleep(delay)
            await submit(ev)
        async def click(**_):
            if confirmation:
                modal.count.return_value = 1
            else:
                tasks.append(asyncio.create_task(send()))
        async def confirm(_):
            tasks.append(asyncio.create_task(send()))
            return True
        publish.click.side_effect = click
        with patch.object(ks, "_click_visible_publish_confirm", AsyncMock(side_effect=confirm)) as confirm_click:
            result = await note()._submit_note_once(page, ev, timeout=.3)
        await asyncio.gather(*tasks)
        assert result["status"] == "accepted"
        assert result["public_visibility"] == "unverified"
        assert publish.click.await_count == 1
        assert confirm_click.await_count == int(confirmation)
    run(scenario())


@pytest.mark.parametrize("failure", ["no_response", "click_timeout", "confirm_timeout", "business_refusal", "unknown_code", "response_decode_error"])
def test_ambiguous_or_refused_submission_never_replays(failure):
    async def scenario():
        page, publish, modal = page_stub()
        ev = NoteEvidence(page, 2)
        await ready(ev)
        async def click(**_):
            if failure == "confirm_timeout":
                modal.count.return_value = 1
            else:
                route = await submit(ev, code=-1 if failure == "business_refusal" else 99,
                                     respond=failure in ("business_refusal", "unknown_code"))
                if failure == "response_decode_error":
                    item = response(SUBMIT, {}, {}, req=route.request)
                    item.json.side_effect = ValueError("bad response")
                    await ev.capture(item)
                if failure == "click_timeout":
                    raise TimeoutError("click may have happened")
        publish.click.side_effect = click
        with patch.object(ks, "_click_visible_publish_confirm", AsyncMock(side_effect=TimeoutError("ambiguous confirm"))) as confirm:
            with pytest.raises(NoteSubmissionError) as exc:
                await note()._submit_note_once(page, ev, timeout=.025)
        assert exc.value.status == ("rejected" if failure == "business_refusal" else "submission_unknown")
        assert publish.click.await_count == 1
        assert confirm.await_count <= 1
    run(scenario())


def test_accepted_response_survives_click_exception():
    async def scenario():
        page, publish, _ = page_stub()
        ev = NoteEvidence(page, 2)
        await ready(ev)
        async def click(**_):
            await submit(ev)
            raise TimeoutError("navigation after click")
        publish.click.side_effect = click
        assert (await note()._submit_note_once(page, ev, timeout=.025))["status"] == "accepted"
        publish.click.assert_awaited_once()
    run(scenario())


@pytest.mark.parametrize("invalid", ["reordered", "missing", "foreign", "duplicate_submit", "not_started", "missing_finish"])
def test_request_guard_prevents_unverified_or_repeated_submit(invalid):
    async def scenario():
        page, _, _ = page_stub()
        ev = NoteEvidence(page, 2)
        await ready(ev)
        ev.started = invalid != "not_started"
        if invalid == "duplicate_submit":
            first = await submit(ev)
            first.continue_.assert_awaited_once()
        if invalid == "missing_finish":
            route = SimpleNamespace(request=request(SUBMIT, IDS), continue_=AsyncMock(), abort=AsyncMock())
            await ev.guard_submit(route)
        else:
            route = await submit(ev, keys=KEYS[::-1] if invalid == "reordered" else KEYS[:1] if invalid == "missing" else None,
                                 identity={**IDS, "atlasId": "foreign"} if invalid == "foreign" else None)
        route.continue_.assert_not_awaited()
        route.abort.assert_awaited_once()
    run(scenario())


def test_response_listener_is_installed_before_file_assignment():
    async def scenario():
        page, publish, _ = page_stub()
        ev = NoteEvidence(page, 2)
        async def prepare(_):
            page.on.assert_called_once_with("response", ev.on_response)
            for item in receipts():
                ev.on_response(item)
        app = note()
        app._prepare_note_content = prepare
        async def click(**_):
            await submit(ev)
        publish.click.side_effect = click
        with patch.object(ks, "NoteEvidence", return_value=ev):
            assert (await app.upload_note_content(page))["status"] == "accepted"
        page.remove_listener.assert_called_once()
        assert not ev.tasks
    run(scenario())


@pytest.mark.parametrize("status,code", [("accepted", 0), ("not_submitted", 1), ("submission_unknown", 2), ("rejected", 3)])
def test_cli_status_is_structured_and_non_success_is_nonzero(status, code, capsys, tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(b"offline test")
    args = sau_cli.build_parser().parse_args(["kuaishou", "upload-note", "--account", "test", "--images", str(image), "--title", "Original title", "--note", "Original body"])
    uploader = AsyncMock(return_value={"status": "accepted", "public_visibility": "unverified"})
    if status != "accepted":
        uploader.side_effect = NoteSubmissionError(status, "test outcome")
    with patch.object(sau_cli, "upload_kuaishou_note", uploader):
        assert run(sau_cli.dispatch(args)) == code
    import json
    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result["schema"] == "sau.kuaishou.note.v1"
    assert result["status"] == status


def test_cli_does_not_turn_missing_result_into_success(capsys, tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(b"offline test")
    args = sau_cli.build_parser().parse_args(["kuaishou", "upload-note", "--account", "test", "--images", str(image), "--title", "Title"])
    with patch.object(sau_cli, "upload_kuaishou_note", AsyncMock(return_value=None)):
        assert run(sau_cli.dispatch(args)) == 2
    assert '"submission_unknown"' in capsys.readouterr().out


@pytest.mark.parametrize("accepted", [False, True])
def test_storage_and_cleanup_failures_do_not_change_outcome_or_retry(accepted):
    async def scenario():
        app = note()
        app.validate_upload_args = AsyncMock()
        page = MagicMock(goto=AsyncMock(), wait_for_url=AsyncMock())
        context = MagicMock(new_page=AsyncMock(return_value=page), storage_state=AsyncMock(side_effect=OSError("save")), close=AsyncMock(side_effect=OSError("close")))
        browser = MagicMock(new_context=AsyncMock(return_value=context), close=AsyncMock(side_effect=OSError("close")))
        playwright = SimpleNamespace(chromium=SimpleNamespace(launch=AsyncMock(return_value=browser)))
        app.upload_note_content = AsyncMock(return_value={"status": "accepted"})
        if not accepted:
            app.upload_note_content.side_effect = NoteSubmissionError("submission_unknown", "missing receipt")
        with patch.object(ks, "set_init_script", AsyncMock(return_value=context)):
            if accepted:
                assert (await app.upload(playwright))["status"] == "accepted"
            else:
                with pytest.raises(NoteSubmissionError) as exc:
                    await app.upload(playwright)
                assert exc.value.status == "submission_unknown"
        app.upload_note_content.assert_awaited_once()
        assert context.storage_state.await_count == int(accepted)
        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()
    run(scenario())


def test_missing_image_fails_before_browser_launch(tmp_path):
    async def scenario():
        app = note()
        app.validate_base_args = AsyncMock()
        app.image_paths = [str(tmp_path / "missing.png")]
        playwright = SimpleNamespace(chromium=SimpleNamespace(launch=AsyncMock()))
        with pytest.raises((ValueError, FileNotFoundError)):
            await app.upload(playwright)
        playwright.chromium.launch.assert_not_awaited()
    run(scenario())


@pytest.mark.parametrize("status", ["accepted", "submission_unknown", "rejected", "not_submitted"])
def test_driver_exit_failure_preserves_original_result(status):
    async def scenario():
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=object())
        manager.__aexit__ = AsyncMock(side_effect=RuntimeError("driver exit failed"))
        app = note()
        app.upload = AsyncMock(return_value={"status": status})
        if status != "accepted":
            app.upload.side_effect = NoteSubmissionError(status, "original outcome")
        with patch.object(ks, "async_playwright", return_value=manager):
            if status == "accepted":
                assert (await app.main())["status"] == status
            else:
                with pytest.raises(NoteSubmissionError) as exc:
                    await app.main()
                assert exc.value.status == status
        app.upload.assert_awaited_once()
    run(scenario())


def test_cli_wrapper_preserves_note_title_tags_and_headed(tmp_path):
    async def scenario():
        req = sau_cli.KuaishouNoteUploadRequest(account_name="offline", image_files=[tmp_path / "one.png"], title="Original title", note="Original body", tags=["a", "b", "c", "d"], publish_date=0, headless=False)
        app = SimpleNamespace(main=AsyncMock(return_value={"status": "accepted"}))
        with patch.object(sau_cli, "resolve_account_file", return_value=tmp_path / "unused.json"), patch.object(sau_cli, "ks_setup", AsyncMock(return_value=True)), patch.object(sau_cli, "KSNote", return_value=app) as ctor:
            assert (await sau_cli.upload_kuaishou_note(req))["status"] == "accepted"
        assert ctor.call_args.kwargs["title"] == req.title
        assert ctor.call_args.kwargs["note"] == req.note
        assert ctor.call_args.kwargs["tags"] == req.tags
        assert ctor.call_args.kwargs["headless"] is False
    run(scenario())


def test_kuaishou_video_dispatch_contract_unchanged(tmp_path):
    video = tmp_path / "offline.mp4"
    video.write_bytes(b"offline test")
    args = sau_cli.build_parser().parse_args(["kuaishou", "upload-video", "--account", "test", "--file", str(video), "--title", "Video title", "--headed"])
    with patch.object(sau_cli, "upload_kuaishou_video", AsyncMock(return_value=tmp_path / "unused.json")) as upload:
        assert run(sau_cli.dispatch(args)) == 0
    upload.assert_awaited_once()
    assert upload.await_args.args[0].headless is False


def test_late_request_after_observer_stop_is_blocked():
    async def scenario():
        page, _, _ = page_stub()
        ev = NoteEvidence(page, 2)
        await ready(ev)
        ev.started = True
        await ev.capture(response(FINISH, {**IDS, "blobKey": KEYS}, {"result": 1}))
        await ev.stop()
        route = SimpleNamespace(request=request(SUBMIT, IDS), continue_=AsyncMock(), abort=AsyncMock())
        await ev.guard_submit(route)
        route.continue_.assert_not_awaited()
        route.abort.assert_awaited_once()
    run(scenario())


def test_patchright_observer_guard_with_local_http_only():
    """Exercise real request identity/body timing against an ephemeral local server.

    Only the origin check is redirected to localhost; no platform request occurs.
    """
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlsplit
    from patchright.async_api import async_playwright
    from uploader.ks_uploader import note_evidence as protocol

    sent = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<!doctype html><title>Offline atlas transport check</title>")
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            sent.append(self.path)
            data = {"result": 1}
            if self.path == PRE:
                data["data"] = {**IDS, "uploadInfo": [{"blobKey": key} for key in KEYS]}
            elif self.path == SINGLE:
                data["data"] = {"url": [{"url": "https://example.invalid/" + body["blobKey"]}]}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, channel="chrome")
            try:
                context = await browser.new_context(service_workers="block")
                async def local_only(route):
                    if route.request.url.startswith(origin + "/"):
                        await route.continue_()
                    else:
                        await route.abort()
                await context.route("**/*", local_only)
                page = await context.new_page()
                await page.goto(origin)
                await page.evaluate("() => { window.post = (path, data) => fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}).then(r=>r.json()); }")
                ev = NoteEvidence(page, 2)
                def local_api(req):
                    return urlsplit(req.url).path if req.url.startswith(origin + "/") and req.method == "POST" else ""
                with patch.object(protocol, "api_path", side_effect=local_api):
                    await ev.start()
                    await page.evaluate("async ([pre, single, ids, keys]) => { await post(pre,{pictureCount:2}); await Promise.all(keys.map(blobKey=>post(single,{...ids,blobKey}))); }", [PRE, SINGLE, IDS, KEYS])
                    await ev.wait_uploaded(timeout=2)
                    ev.started = ev.click_started = True
                    # Immediately enqueue submit from the frontend's finish callback.
                    await page.evaluate("async ([finish, submit, ids, keys]) => { await post(finish,{...ids,blobKey:keys}); await post(submit,ids); }", [FINISH, SUBMIT, IDS, KEYS])
                    for _ in range(20):
                        if ev.result:
                            break
                        await asyncio.sleep(.01)
                    assert ev.outcome()["status"] == "accepted"
                    # Second fetch reaches the Python route but never the HTTP server.
                    assert await page.evaluate("async ([p,ids])=>{try{await post(p,ids);return 'sent'}catch{return 'blocked'}}", [SUBMIT, IDS]) == "blocked"
                    await ev.stop()
                assert sent.count(SUBMIT) == 1
                await context.close()
            finally:
                await browser.close()
    try:
        run(scenario())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()
