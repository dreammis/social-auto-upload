"""Entry point for the web server.

Thin wrapper around the web_runner package's create_app() factory.
Run with: python run.py
"""
from __future__ import annotations

import atexit

from web_runner import create_app
from web_runner.utils import task_executor

app = create_app()

if __name__ == "__main__":
    atexit.register(task_executor.shutdown, wait=False)
    app.run(host="0.0.0.0", port=6001, debug=True)
