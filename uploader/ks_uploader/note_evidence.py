"""Observe the creator's atlas contract; never issue platform requests ourselves.

Public frontend contract and limitations: docs/kuaishou-note-safety.md.
"""
import asyncio
from urllib.parse import urlsplit

PREFIX = "/rest/cp/works/atlas/pc/"
PRE = PREFIX + "upload/pre"
SINGLE = PREFIX + "upload/single/finish"
FINISH = PREFIX + "upload/finish"
SUBMIT = PREFIX + "publish/submit"
SUBMIT_ROUTE = "**/rest/cp/works/atlas/pc/publish/submit*"


class NoteSubmissionError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def api_path(request):
    url = urlsplit(request.url)
    if url.scheme == "https" and url.netloc == "cp.kuaishou.com" and request.method == "POST":
        return url.path
    return ""


class NoteEvidence:
    def __init__(self, page, expected_count):
        self.page = page
        self.expected_count = expected_count
        self.pre = []
        self.singles = []
        self.finish = []
        self.tasks = set()
        self.changed = asyncio.Event()
        self.error = None
        self.request = None
        self.result = None
        self.started = False
        self.click_started = False

    async def start(self):
        self.page.on("response", self.on_response)
        await self.page.route(SUBMIT_ROUTE, self.guard_submit)

    def on_response(self, response):
        if api_path(response.request) not in (PRE, SINGLE, FINISH, SUBMIT):
            return
        task = asyncio.create_task(self.capture(response))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def capture(self, response):
        try:
            request = response.request
            route = api_path(request)
            body = request.post_data_json
            data = await asyncio.wait_for(response.json(), timeout=5)
            if not isinstance(body, dict) or not isinstance(data, dict) or not response.ok:
                raise ValueError("Invalid atlas response")
            if route == SUBMIT:
                if request != self.request:
                    raise ValueError("Uncorrelated atlas submission response")
                if data.get("result") == 1:
                    self.result = "accepted"
                elif data.get("result") == -1:
                    self.result = "rejected"
                else:
                    self.error = "Unrecognized atlas submission result"
            else:
                if data.get("result") != 1:
                    raise ValueError("Atlas upload was refused")
                {PRE: self.pre, SINGLE: self.singles, FINISH: self.finish}[route].append((body, data))
        except Exception as exc:
            # No response bodies, URLs with credentials, or account data in errors.
            self.error = f"Cannot verify atlas response ({type(exc).__name__})"
        finally:
            self.changed.set()

    def uploaded_batch(self):
        if self.error:
            raise NoteSubmissionError("not_submitted", self.error)
        if len(self.pre) > 1:
            raise NoteSubmissionError("not_submitted", "Multiple atlas upload batches observed")
        if not self.pre:
            return None
        body, response = self.pre[0]
        data = response.get("data") or {}
        info = data.get("uploadInfo")
        if body.get("pictureCount") != self.expected_count or not isinstance(info, list) or len(info) != self.expected_count:
            raise NoteSubmissionError("not_submitted", "Atlas upload count does not match input images")
        keys = [item.get("blobKey") for item in info if isinstance(item, dict)]
        identity = {key: data.get(key) for key in ("fileId", "atlasId")}
        if not all(identity.values()) or len(keys) != self.expected_count or not all(isinstance(key, str) and key for key in keys) or len(set(keys)) != len(keys):
            raise NoteSubmissionError("not_submitted", "Missing or duplicate atlas image identity")
        completed = set()
        for request, result in self.singles:
            if any(request.get(key) != value for key, value in identity.items()) or request.get("blobKey") not in keys:
                raise NoteSubmissionError("not_submitted", "Image receipt belongs to a different atlas batch")
            # The frontend consumes this image URL only after result === 1.
            urls = (result.get("data") or {}).get("url")
            if not isinstance(urls, list) or not urls or not isinstance(urls[0], dict) or not urls[0].get("url"):
                raise NoteSubmissionError("not_submitted", "Image completion receipt has no image URL")
            completed.add(request["blobKey"])
        return (identity, keys) if completed == set(keys) else None

    async def wait_uploaded(self, timeout=120):
        async def wait():
            while True:
                self.changed.clear()
                batch = self.uploaded_batch()
                if batch:
                    return batch
                await self.changed.wait()
        try:
            return await asyncio.wait_for(wait(), timeout)
        except asyncio.TimeoutError as exc:
            raise NoteSubmissionError("not_submitted", "Timed out verifying every input image") from exc

    async def guard_submit(self, route):
        request = route.request
        if api_path(request) != SUBMIT:
            await route.continue_()
            return
        try:
            # The frontend may process its response before our JSON reader finishes.
            pending = list(self.tasks)
            if pending:
                await asyncio.wait_for(asyncio.gather(*pending), timeout=6)
            batch = self.uploaded_batch()
            if not self.started or self.request is not None or not batch:
                raise ValueError("Unpermitted or duplicate submission")
            identity, keys = batch
            if len(self.finish) != 1:
                raise ValueError("Missing unique final image-list receipt")
            final, _ = self.finish[0]
            body = request.post_data_json
            if not isinstance(body, dict) or any(final.get(key) != value or body.get(key) != value for key, value in identity.items()) or final.get("blobKey") != keys:
                raise ValueError("Submission does not match complete ordered image batch")
            # Set before continue: an exception here may already have sent the request.
            self.request = request
            await route.continue_()
        except Exception as exc:
            self.error = f"Atlas submission stopped ({type(exc).__name__})"
            self.changed.set()
            await route.abort()

    def outcome(self):
        if self.result == "accepted":
            return {"status": "accepted", "evidence": "atlas_publish_response", "public_visibility": "unverified"}
        if self.result == "rejected":
            raise NoteSubmissionError("rejected", "Platform refused the atlas submission; no automatic retry")
        status = "submission_unknown" if self.click_started else "not_submitted"
        raise NoteSubmissionError(status, self.error or "No correlated atlas submission result; do not retry automatically")

    async def stop(self):
        self.started = False
        self.page.remove_listener("response", self.on_response)
        # Keep the request guard until page/context close. Unrouting an ambiguous
        # page could allow its delayed or duplicate submit request to escape.
        for task in list(self.tasks):
            task.cancel()
        if self.tasks:
            await asyncio.gather(*list(self.tasks), return_exceptions=True)
        self.tasks.clear()
