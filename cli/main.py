"""Main entry point for CLI."""
from __future__ import annotations

import asyncio
import sys
from typing import Sequence

from cli.dispatchers import dispatch
from cli.parser import build_parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return asyncio.run(dispatch(args))
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
