"""TikTok Upload Worker — Phase 7."""

import json
import logging
import os
import threading
import time
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from uploader.core.browser_manager import redact_sensitive
from uploader.facebook_uploader.crypto_utils import decrypt_session_data
from uploader.facebook_uploader.upload_models import UploadJob, UploadJobStatus
from uploader.tiktok_uploader.playwright_engine import (
    TikTokPlaywrightUploader,
    TikTokUploadError,
)

logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "socialflow")
DB_PASSWORD = os.getenv("DB_PASSWORD", "socialflow_dev")
DB_NAME = os.getenv("DB_NAME", "socialflow")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, pool_size=5, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

tiktok_bp = Blueprint("tiktok_upload", __name__)


def _extract_cookies(session_data):
    """Accept raw Playwright cookie list or session object containing cookies."""
    if isinstance(session_data, list):
        return session_data
    if isinstance(session_data, dict):
        cookies = session_data.get("cookies") or session_data.get("cookie")
        if isinstance(cookies, list):
            return cookies
    raise ValueError("TikTok session_data must be a cookie list or object with cookies[]")


def _update_upload_status(
    job_id: str,
    status: UploadJobStatus,
    **extra,
) -> None:
    db = SessionLocal()
    try:
        job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
        if job:
            job.status = status
            for key, value in extra.items():
                setattr(job, key, value)
            job.updated_at = datetime.utcnow()
            db.commit()
            logger.info("TikTok UploadJob %s -> %s", job_id, status.value)
    except Exception as exc:
        db.rollback()
        logger.error("TikTok DB update failed for upload %s: %s", job_id, redact_sensitive(exc))
    finally:
        db.close()


def _do_tiktok_upload(upload_job_id: str) -> None:
    db = SessionLocal()
    try:
        _update_upload_status(upload_job_id, UploadJobStatus.UPLOADING)
        upload_job = db.query(UploadJob).filter(UploadJob.id == upload_job_id).first()
        if not upload_job:
            logger.error("TikTok UploadJob %s not found", upload_job_id)
            return

        video_row = db.execute(
            text("SELECT video_url FROM video_jobs WHERE id = :vid"),
            {"vid": upload_job.video_job_id},
        ).fetchone()
        if not video_row or not video_row[0]:
            raise FileNotFoundError(
                f"No video_url for video_job_id={upload_job.video_job_id}"
            )
        video_path = video_row[0]

        account_row = db.execute(
            text(
                "SELECT session_data, account_name, platform, proxy_url "
                "FROM accounts WHERE id = :aid"
            ),
            {"aid": upload_job.account_id},
        ).fetchone()
        if not account_row:
            raise ValueError(f"Account {upload_job.account_id} not found")

        session_json = decrypt_session_data(account_row[0])
        session_data = json.loads(session_json)
        cookies = _extract_cookies(session_data)
        proxy_url = upload_job.proxy_url or account_row[3]

        logger.info(
            "Starting TikTok upload — job=%s video=%s account=%s proxy=%s",
            upload_job_id,
            video_path,
            account_row[1],
            "configured" if proxy_url else "none",
        )

        uploader = TikTokPlaywrightUploader(
            cookies=cookies,
            account_id=upload_job.account_id,
            proxy_url=proxy_url,
        )
        post_url = uploader.upload(
            video_path=video_path,
            caption=upload_job.caption or "",
            upload_job_id=upload_job_id,
        )

        if upload_job.affiliate_comment and post_url:
            logger.info("TikTok affiliate seeding scheduled — job=%s", upload_job_id)
            time.sleep(8)
            uploader.post_comment(
                post_url=post_url,
                comment_text=upload_job.affiliate_comment,
                upload_job_id=upload_job_id,
            )
        elif upload_job.affiliate_comment:
            logger.warning(
                "TikTok affiliate comment skipped — no extractable post_url job=%s",
                upload_job_id,
            )

        _update_upload_status(
            upload_job_id,
            UploadJobStatus.SUCCESS,
            post_url=post_url,
        )
        logger.info("TikTok upload complete — job=%s post_url=%s", upload_job_id, post_url)

    except TikTokUploadError as exc:
        logger.error(
            "TikTok upload failed — job=%s: %s (screenshot=%s)",
            upload_job_id,
            exc,
            exc.screenshot_path,
        )
        error_detail = str(exc)
        if exc.screenshot_path:
            error_detail += f"\nScreenshot: {exc.screenshot_path}"
        _update_upload_status(
            upload_job_id,
            UploadJobStatus.FAILED,
            error_log=error_detail,
        )
    except Exception as exc:
        logger.error(
            "TikTok upload failed — job=%s: %s",
            upload_job_id,
            redact_sensitive(exc),
            exc_info=True,
        )
        _update_upload_status(
            upload_job_id,
            UploadJobStatus.FAILED,
            error_log=redact_sensitive(exc),
        )
    finally:
        db.close()


@tiktok_bp.route("/upload/tiktok", methods=["POST"])
def upload_tiktok():
    data = request.get_json(force=True)
    upload_job_id = data.get("upload_job_id")
    if not upload_job_id:
        return jsonify({"error": "upload_job_id required"}), 400

    thread = threading.Thread(
        target=_do_tiktok_upload,
        args=(upload_job_id,),
        daemon=True,
    )
    thread.start()
    return jsonify({"upload_job_id": upload_job_id, "status": "accepted"}), 202
