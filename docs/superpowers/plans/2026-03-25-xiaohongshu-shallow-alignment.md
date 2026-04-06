# Xiaohongshu Shallow Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the browser-based Xiaohongshu uploader with the current Douyin/Kuaishou style for login QR flow, patchright usage, and formal video/note entry points without expanding into CLI or docs work.

**Architecture:** Keep the work inside `uploader/xiaohongshu_uploader/main.py` as a shallow refactor. Introduce a thin login flow with QR extraction, cookie validation, and result payloads, then add a shared base uploader plus separate video and note browser flows that reuse common setup.

**Tech Stack:** Python, patchright, async Playwright-compatible browser automation, unittest

---

### Task 1: Lock expected login/setup behavior

**Files:**
- Create: `tests/test_xiaohongshu_uploader.py`
- Modify: `uploader/xiaohongshu_uploader/main.py`

- [ ] Add tests for `xiaohongshu_setup(..., return_detail=True)` invalid-cookie behavior and uploader validation behavior.
- [ ] Run the targeted test file and confirm it fails for the expected missing behavior.
- [ ] Implement the minimal production changes to satisfy those tests.

### Task 2: Refactor Xiaohongshu uploader module

**Files:**
- Modify: `uploader/xiaohongshu_uploader/main.py`

- [ ] Switch the module from `playwright.async_api` to `patchright.async_api`.
- [ ] Replace `page.pause()` login with QR extraction, terminal printing, QR file saving, polling, and cookie persistence.
- [ ] Add a shared base uploader plus formal video and note entry points while keeping legacy public names callable.

### Task 3: Refresh local debug examples

**Files:**
- Modify: `examples/get_xiaohongshu_cookie.py`
- Modify: `examples/upload_video_to_xiaohongshu.py`

- [ ] Update the login example to use the aligned setup entry.
- [ ] Update the upload example to expose direct video/note debug functions.

### Task 4: Verify

**Files:**
- Test: `tests/test_xiaohongshu_uploader.py`

- [ ] Run the targeted unittest file.
- [ ] Run a quick Python syntax/import check for the modified uploader and examples.
