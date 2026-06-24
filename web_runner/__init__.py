"""Web runner package — Flask application factory."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from flask_cors import CORS

from web_runner.db import init_db
from utils.log import logger as _task_logger


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

    _setup_cors(app)
    init_db()

    from web_runner.routes.accounts import bp as accounts_bp
    from web_runner.routes.upload import bp as upload_bp
    from web_runner.routes.tasks import bp as tasks_bp
    from web_runner.routes.ai import bp as ai_bp
    from web_runner.routes.account_groups import bp as account_groups_bp

    app.register_blueprint(accounts_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(account_groups_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(Exception)
    def _handle_unexpected_error(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            return exc.get_response()
        from flask import jsonify
        _task_logger.error(f"[error] unhandled exception: {exc}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

    @app.errorhandler(413)
    def _handle_request_too_large(exc):
        from flask import jsonify
        return jsonify({"success": False, "message": "Request entity too large (max 200MB)"}), 413

    return app


def _setup_cors(app: Flask) -> None:
    raw = os.environ.get("SAU_CORS_ALLOWED_ORIGINS")
    if not raw:
        _task_logger.warning(
            "[web] CORS disabled (SAU_CORS_ALLOWED_ORIGINS is unset/empty). "
            "Set e.g. SAU_CORS_ALLOWED_ORIGINS='http://localhost:5173,http://localhost:5174' "
            "to allow cross-origin clients."
        )
        return
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if origins:
        CORS(app, resources={r"/api/*": {"origins": origins}})
        _task_logger.info(f"[web] CORS enabled for /api/* origins: {origins}")
