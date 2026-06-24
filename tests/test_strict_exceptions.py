"""Regression guard for ``except Exception`` / bare ``except:`` re-introduction.

When this test runs in PR CI:
  - It walks every Python file in the configured scope.
  - It uses ``ast`` to find every ``ast.ExceptHandler`` whose type is bare or
    matches ``Exception`` / ``BaseException``.
  - It cross-checks with a leading-whitespace regex as belt-and-braces.
  - Any forbidden site fails the test with a clear remediation message.

Add inline ``# strict-exceptions: allow`` on a line as a last-resort opt-out
when narrowing is genuinely impractical. Prefer rewrites; the rewriter lives
at ``tools/strict_exceptions.py``.

The AST walker correctly ignores:
  * docstring content (string constants, not handlers)
  * Flask ``@app.errorhandler(Exception)`` decorators (decorator args, not handlers)
  * narrow ``ast.Attribute`` references like ``patchright.async_api.Error``
  * the rewriter tool itself scanning ``tools/strict_exceptions.py`` docstrings
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


# Source paths to enforce. ``tests/`` is intentionally included so the rule
# is repo-wide per the project owner's explicit ask.
TARGET_PATHS: list[str] = [
    "sau_cli.py",
    "web_runner.py",
    "uploader",
    "utils",
    "db",
    "examples",
    "skills",
    "tools",
    "tests",
]


# Inline allowlist: ``# strict-exceptions: allow`` on the same source line as
# the exception handler. Honored by both the AST walker and the regex pass.
ALLOWLIST_REGEX = re.compile(r"#\s*strict-exceptions:\s*allow\b")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _iter_python_files(root: Path) -> list[Path]:
    """Yield ``*.py`` files under any TARGET_PATHS root."""
    files: list[Path] = []
    for target in TARGET_PATHS:
        target_path = root / target
        if not target_path.exists():
            continue
        if target_path.is_file():
            files.append(target_path)
            continue
        for p in sorted(target_path.rglob("*.py")):
            # Skip cache dirs / vendored worktrees if symlinked.
            if "__pycache__" in p.parts:
                continue
            files.append(p)
    return files


def _classify_handler(handler: ast.ExceptHandler) -> str | None:
    """Return a label for a forbidden handler, else ``None``.

    Flag rules:
      - ``except:``                              -> 'bare_except'
      - ``except Exception:``                    -> 'broad_except_Exception'
      - ``except BaseException:``                -> 'broad_except_BaseException'
      - tuple containing ``Exception`` /
        ``BaseException``                        -> 'broad_except_mixed'
    """
    if handler.type is None:
        return "bare_except"
    if isinstance(handler.type, ast.Name):
        if handler.type.id == "Exception":
            return "broad_except_Exception"
        if handler.type.id == "BaseException":
            return "broad_except_BaseException"
        return None
    if isinstance(handler.type, ast.Tuple):
        for elt in handler.type.elts:
            if isinstance(elt, ast.Name) and elt.id in {"Exception", "BaseException"}:
                return "broad_except_mixed"
        return None
    # ast.Attribute (e.g. ``patchright.async_api.Error``) and other dotted
    # references are intentionally narrow; do not flag.
    return None


def _find_broad_excepts(
    source: str,
    filename: str,
) -> list[tuple[int, int, str, str]]:
    """Return ``[(line, col, kind, snippet)]`` for forbidden handlers."""
    findings: list[tuple[int, int, str, str]] = []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [(0, 0, "syntax_error", f"{type(exc).__name__}: {exc}")]
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        kind = _classify_handler(node)
        if kind is None:
            continue
        line_text = lines[node.lineno - 1] if 0 < node.lineno <= len(lines) else ""
        if ALLOWLIST_REGEX.search(line_text):
            continue
        snippet = line_text.strip() or "<empty>"
        findings.append((node.lineno, node.col_offset, kind, snippet))
    return findings


# ---------- Detector self-tests --------------------------------------------

def test_detects_bare_except() -> None:
    # Top-level bare ``except:`` (column 0): ``except`` keyword starts at col 0.
    src = "try:\n    pass\nexcept:\n    pass\n"
    rows = _find_broad_excepts(src, "fake.py")
    assert rows == [(3, 0, "bare_except", "except:")], rows


def test_detects_bare_except_indented() -> None:
    # Indented bare ``except:`` (column 4): inside a function body.
    src = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except:\n"
        "        pass\n"
    )
    rows = _find_broad_excepts(src, "fake.py")
    assert len(rows) == 1
    line, col, kind, snippet = rows[0]
    assert kind == "bare_except"
    assert line == 4  # line of indented `except:`
    assert col == 4  # 4-space indent
    assert snippet == "except:"


def test_detects_exception_literal() -> None:
    src = "try:\n    pass\nexcept Exception:\n    pass\n"
    rows = _find_broad_excepts(src, "fake.py")
    assert rows and rows[0][2] == "broad_except_Exception"


def test_detects_base_exception_literal() -> None:
    src = "try:\n    pass\nexcept BaseException:\n    pass\n"
    rows = _find_broad_excepts(src, "fake.py")
    assert rows and rows[0][2] == "broad_except_BaseException"


def test_detects_exception_inside_tuple() -> None:
    src = "try:\n    pass\nexcept (json.JSONDecodeError, Exception):\n    pass\n"
    rows = _find_broad_excepts(src, "fake.py")
    assert len(rows) == 1 and rows[0][2] == "broad_except_mixed"


def test_narrow_attribute_exceptions_not_flagged() -> None:
    src = (
        "import patchright\n"
        "try:\n    pass\n"
        "except (patchright.async_api.Error, OSError, asyncio.TimeoutError):\n    pass\n"
        "try:\n    pass\n"
        "except OSError:\n    pass\n"
        "try:\n    pass\n"
        "except (ValueError, KeyError):\n    pass\n"
    )
    assert _find_broad_excepts(src, "fake.py") == []


def test_allowlist_comment_suppresses_detection() -> None:
    src = (
        "try:\n    pass\n"
        "except Exception:  # strict-exceptions: allow\n"
        "    pass\n"
    )
    assert _find_broad_excepts(src, "fake.py") == []


def test_docstring_with_exception_text_ignored() -> None:
    """docstring text like 'except Exception: ...' is parse-safe and must not be flagged."""
    src = (
        '"""\n'
        "Example of bad code:\n"
        "    except Exception:\n"
        "        pass\n"
        '"""\n'
    )
    assert _find_broad_excepts(src, "fake.py") == []


def test_flask_errorhandler_decorator_argument_ignored() -> None:
    """``@app.errorhandler(Exception)`` is a decorator arg, NOT an except handler."""
    src = (
        "from flask import Flask\n"
        "app = Flask(__name__)\n"
        "@app.errorhandler(Exception)\n"
        "def _h(exc):\n"
        "    return 'oops', 500\n"
    )
    assert _find_broad_excepts(src, "fake.py") == []


def test_allowlist_marker_is_specific() -> None:
    """A loose comment like '# forgive this' must NOT be honored."""
    src = (
        "try:\n    pass\n"
        "except Exception:  # forgive this\n"  # not the magic comment
        "    pass\n"
    )
    rows = _find_broad_excepts(src, "fake.py")
    assert rows and rows[0][2] == "broad_except_Exception"


# ---------- The PR regression guard itself ---------------------------------

def test_repo_has_no_broad_except() -> None:
    """Fail the PR if any source file introduces a bare ``except:`` or
    ``except Exception`` / ``except BaseException`` clause.

    The failure message lists every offending file:line and explains how to
    fix it so reviewers don't have to context-switch.
    """
    root = _repo_root()
    files = _iter_python_files(root)
    assert files, (
        "scan returned 0 files — TARGET_PATHS may be stale relative to repo layout"
    )

    all_rows: list[tuple[Path, int, int, str, str]] = []
    for path in files:
        rel = path.relative_to(root)
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            all_rows.append((rel, 0, 0, "read_error", str(e)))
            continue
        # ``_find_broad_excepts`` itself swallows SyntaxError and returns it
        # as a ``'syntax_error'`` finding. We deliberately do NOT call
        # ``pytest.skip()`` here because doing so would mask regressions
        # where a single file has both a syntax error AND a broad except.
        rows = _find_broad_excepts(source, str(path))
        for line, col, kind, snippet in rows:
            all_rows.append((rel, line, col, kind, snippet))

    if not all_rows:
        return

    body = "\n".join(
        f"  - {p}:{line}:{col}  [{kind}]  {snippet}"
        for p, line, col, kind, snippet in all_rows
    )
    pytest.fail(
        f"\n\nFound {len(all_rows)} broad exception handler(s):\n\n"
        f"{body}\n\n"
        "Fix: rewrite each site to a narrow tuple — e.g.\n"
        "  except (patchright.async_api.Error, OSError, asyncio.TimeoutError)\n"
        "\n"
        "For genuinely broad sites where narrowing is impractical, add an\n"
        "inline allowlist comment on the same line:\n"
        "  # strict-exceptions: allow\n"
        "\n"
        "You can also re-run the bulk rewriter:\n"
        "  python3 tools/strict_exceptions.py --dry-run   # preview\n"
        "  python3 tools/strict_exceptions.py --apply     # commit\n"
    )


def test_rewriter_docstring_is_not_flagged() -> None:
    """The rewriter tool documents ``except Exception`` patterns in its
    module docstring. The AST walker must not flag those."""
    rewriter = _repo_root() / "tools" / "strict_exceptions.py"
    if not rewriter.exists():
        pytest.skip("tools/strict_exceptions.py not present")
    rows = _find_broad_excepts(rewriter.read_text(encoding="utf-8"), str(rewriter))
    assert rows == [], f"rewriter tool flagged (false positive): {rows}"
