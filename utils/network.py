"""Network / async-retry helpers used by platform uploaders.

Two decorators are exported:

* :func:`async_retry` — narrow defaults: ``(RuntimeError, OSError, TimeoutError,
  asyncio.TimeoutError)``. Use for retry-eligible work that is pure runtime /
  OS level (filesystem, sockets).
* :func:`async_retry_with_browser` — same defaults plus
  ``patchright.async_api.Error``. Use for wrappers around Playwright ops
  (.click, .wait_for, .fill, .locator(...).count()) so transient browser
  errors are retried instead of aborting the whole pipeline.

Both decorators catch only the small explicit tuples above. ``asyncio.CancelledError``
and ``KeyboardInterrupt`` (both ``BaseException`` subclasses) propagate upward,
preserving cooperative cancellation semantics.

Notes
-----
* ``IOError`` is a historic alias of :class:`OSError` in Python 3 and is
  intentionally NOT listed separately to avoid silent duplicates.
* ``patchright`` is imported lazily inside ``async_retry_with_browser`` so this
  module can be imported without the browser layer installed (e.g. for tests
  that only exercise ``async_retry``).
"""
from __future__ import annotations

import asyncio
import time
from functools import wraps

# Pure-runtime retry defaults (no browser coupling).
_RUNTIME_RETRYABLE = (
    RuntimeError,
    OSError,           # covers IOError, ConnectionError, FileNotFoundError, ...
    TimeoutError,      # builtin TimeoutError (matches asyncio.TimeoutError if aliased)
    asyncio.TimeoutError,
)


def async_retry(timeout: float = 60, max_retries: int | None = None,
                exceptions=_RUNTIME_RETRYABLE):
    """Retry on `exceptions` until `max_retries` or `timeout` seconds elapse."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            attempts = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    attempts += 1
                    if max_retries is not None and attempts >= max_retries:
                        raise RuntimeError(
                            f"{func.__name__}: failed after {max_retries} retries; last error: {exc}"
                        ) from exc
                    if time.time() - start > timeout:
                        raise TimeoutError(
                            f"{func.__name__}: exceeded {timeout}s timeout after {attempts} attempts"
                        ) from exc
                    await asyncio.sleep(1)
        return wrapper

    return decorator


def async_retry_with_browser(timeout: float = 60, max_retries: int | None = None,
                              exceptions=None):
    """Async-retry decorator that also catches ``patchright.async_api.Error``.

    Lazy-imports ``patchright`` so this module is importable without the
    browser layer present.
    """
    if exceptions is None:
        try:
            from patchright.async_api import Error as PlaywrightError
        except ImportError as exc:
            raise RuntimeError(
                "async_retry_with_browser needs patchright installed; pass "
                "exceptions= explicitly if you want a Playwright-free tuple."
            ) from exc
        exceptions = _RUNTIME_RETRYABLE + (PlaywrightError,)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            attempts = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    attempts += 1
                    if max_retries is not None and attempts >= max_retries:
                        raise RuntimeError(
                            f"{func.__name__}: failed after {max_retries} retries; last error: {exc}"
                        ) from exc
                    if time.time() - start > timeout:
                        raise TimeoutError(
                            f"{func.__name__}: exceeded {timeout}s timeout after {attempts} attempts"
                        ) from exc
                    await asyncio.sleep(1)
        return wrapper

    return decorator
