"""AST rewriter that narrows bare ``except:`` / ``except Exception`` handlers.

The uploader / CLI modules historically swallow ``Exception`` everywhere, which
masks programming errors and makes debugging harder. This tool rewrites those
handlers to a small, intent-driven tuple while leaving already-narrow handlers
alone.

Rules (applied per ExceptHandler):

* bare ``except:``  -> ``except (patchright.async_api.Error, OSError, asyncio.TimeoutError):``
* ``except Exception as X:`` -> same tuple, alias preserved
* login-flow wrappers (functions whose name contains 'cookie_auth' / 'cookie_gen')
  expand the tuple with ``RuntimeError`` so programmer-level errors still reach the
  result-dict build.
* Already-narrow tuples / specific class names are left untouched.
* Files that don't import patchright (utils/, helpers) get a smaller tuple:
  ``(OSError, RuntimeError, ValueError)``.

Run ``python tools/strict_exceptions.py --apply`` to commit changes after the
default dry-run prints a per-site summary.
"""
from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_GLOBS = (
    "sau_cli.py",
    "uploader/**/*.py",
)
EXCLUDE_DIRS = ("legacy", "tests", "tools", ".kilocode", ".kilo", "kilo")


@dataclass
class Site:
    file: Path
    lineno: int
    before: str
    after: str
    enclosing: str
    login_wrapper: bool


PROBE_TUPLE = ("patchright.async_api.Error", "OSError", "asyncio.TimeoutError")
LOGIN_TUPLE = PROBE_TUPLE + ("RuntimeError",)
NON_PLW_TUPLE = ("OSError", "RuntimeError", "ValueError")


def _iter_target_files() -> Iterable[Path]:
    for pattern in TARGET_GLOBS:
        for f in REPO_ROOT.glob(pattern):
            if not f.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in f.relative_to(REPO_ROOT).parts):
                continue
            yield f


def _uses_patchright(source_text: str) -> bool:
    return "from patchright" in source_text or "import patchright" in source_text


def _is_login_wrapper(name: str) -> bool:
    return "cookie_auth" in name or "cookie_gen" in name


def _handler_is_broad(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Tuple):
        elt_ids = {elt.id for elt in handler.type.elts if isinstance(elt, ast.Name)}
    elif isinstance(handler.type, ast.Name):
        elt_ids = {handler.type.id}
    else:
        return False
    return bool(elt_ids & {"Exception", "BaseException"})


def _make_handler_tuple_expr(type_names: tuple[str, ...]) -> ast.AST:
    elts = []
    for name in type_names:
        parts = name.split(".")
        node: ast.AST = ast.Name(id=parts[0], ctx=ast.Load())
        for part in parts[1:]:
            node = ast.Attribute(value=node, attr=part, ctx=ast.Load())
        elts.append(node)
    return ast.Tuple(elts=elts, ctx=ast.Load())


def _find_enclosing(tree: ast.AST, handler: ast.ExceptHandler) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if child is handler:
                    return node.name
    return "<module>"


def _rewrite_tree(tree: ast.AST, has_patchright: bool) -> list[Site]:
    """Mutate handlers in-place; return Site list describing mutations."""
    sites: list[Site] = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        login = _is_login_wrapper(func.name)
        for handler in ast.walk(func):
            if not isinstance(handler, ast.ExceptHandler):
                continue
            if not _handler_is_broad(handler):
                continue
            tuple_for_site = (
                LOGIN_TUPLE if (login and has_patchright)
                else PROBE_TUPLE if has_patchright
                else NON_PLW_TUPLE
            )
            before = ast.unparse(ast.ExceptHandler(
                type=handler.type,
                name=handler.name,
                body=[],
            ))
            after = f"except ({', '.join(tuple_for_site)})" + (
                f" as {handler.name}" if handler.name else ""
            )
            handler.type = _make_handler_tuple_expr(tuple_for_site)
            sites.append(Site(
                file=Path(),  # caller fills
                lineno=handler.lineno,
                before=before,
                after=after,
                enclosing=func.name,
                login_wrapper=login,
            ))
    return sites


def process_file(path: Path, apply_changes: bool) -> list[Site]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    has_patchright = _uses_patchright(src)
    sites = _rewrite_tree(tree, has_patchright)
    for s in sites:
        s.file = path
    if apply_changes and sites:
        path.write_text(ast.unparse(tree), encoding="utf-8")
    return sites


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Commit edits; default is dry-run")
    args = parser.parse_args(argv)

    total_sites = 0
    for f in _iter_target_files():
        sites = process_file(f, apply_changes=args.apply)
        if not sites:
            continue
        for s in sites:
            tag = "APPLY " if args.apply else "DRY   "
            wrap = " (login-wrap)" if s.login_wrapper else ""
            print(f"[{tag}] {s.file.relative_to(REPO_ROOT)}:{s.lineno} in `{s.enclosing}`{wrap}")
            print(f"          - {s.before.splitlines()[-1][:90]}")
            print(f"          + {s.after}")
            total_sites += 1

    mode = "apply" if args.apply else "dry-run"
    print(f"--- {mode}: {total_sites} sites ---")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
