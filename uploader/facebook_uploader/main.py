"""
Facebook Upload Worker — Phase 5 Part 2.

Flask blueprint providing POST /upload/facebook.
Processes uploads in background threads with Playwright automation
and full DB status tracking.
"""

import os
import json
import logging
import threading
from datetime import datetime

from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker

from uploader.facebook_uploader.upload_models import (
    UploadBase,
    UploadJob,
    UploadJobStatus,
)
from uploader.core.browser_manager import redact_sensitive
from uploader.facebook_uploader.crypto_utils import decrypt_session_data
from uploader.facebook_uploader.playwright_engine import (
    FacebookPlaywrightUploader,
    FacebookUploadError,
)

logger = logging.getLogger(__name__)

# ── Database (shared PostgreSQL) ──────────────────────────────────
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

# Ensure upload_jobs table exists (safe for shared DB — only adds if missing)
try:
    UploadBase.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE upload_jobs "
                "ADD COLUMN IF NOT EXISTS affiliate_comment TEXT"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE upload_jobs "
                "ADD COLUMN IF NOT EXISTS proxy_url VARCHAR(500)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE upload_jobs "
                "ALTER COLUMN video_job_id TYPE UUID "
                "USING video_job_id::text::uuid"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE accounts "
                "ADD COLUMN IF NOT EXISTS proxy_url VARCHAR(500)"
            )
        )
except (ProgrammingError, OperationalError) as exc:
    logger.warning(
        "Database migration skipped (tables might not be initialized by NestJS yet): %s",
        redact_sensitive(exc),
    )
except Exception as exc:
    logger.error("Unexpected error during DB migration: %s", redact_sensitive(exc))

# ── Blueprint ─────────────────────────────────────────────────────
facebook_bp = Blueprint("facebook_upload", __name__)


def _update_upload_status(
    job_id: str,
    status: UploadJobStatus,
    **extra,
) -> None:
    """Update an UploadJob row."""
    db = SessionLocal()
    try:
        job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
        if job:
            job.status = status
            for k, v in extra.items():
                setattr(job, k, v)
            job.updated_at = datetime.utcnow()
            db.commit()
            logger.info("UploadJob %s → %s", job_id, status.value)
    except Exception as exc:
        db.rollback()
        logger.error("DB update failed for upload %s: %s", job_id, redact_sensitive(exc))
    finally:
        db.close()


def _do_facebook_upload(upload_job_id: str) -> None:
    """Background thread: execute the full Facebook upload pipeline.

    Steps:
      1. Fetch UploadJob → get video_job_id, account_id, caption.
      2. Fetch video path from video_jobs table.
      3. Fetch encrypted session_data from accounts table → decrypt.
      4. Post to Facebook via Playwright automation.
      5. Update status + post_url.
    """
    db = SessionLocal()
    try:
        # ── Step 1: Load upload job ──
        _update_upload_status(upload_job_id, UploadJobStatus.UPLOADING)
        upload_job = (
            db.query(UploadJob).filter(UploadJob.id == upload_job_id).first()
        )
        if not upload_job:
            logger.error("UploadJob %s not found", upload_job_id)
            return

        # ── Step 2: Get video file path from video_jobs ──
        row = db.execute(
            text("SELECT video_url FROM video_jobs WHERE id = :vid"),
            {"vid": upload_job.video_job_id},
        ).fetchone()

        if not row or not row[0]:
            raise FileNotFoundError(
                f"No video_url for video_job_id={upload_job.video_job_id}"
            )
        video_path = row[0]

        # ── Step 3: Decrypt Facebook session ──
        acct_row = db.execute(
            text(
                "SELECT session_data, account_name, platform, proxy_url "
                "FROM accounts WHERE id = :aid"
            ),
            {"aid": upload_job.account_id},
        ).fetchone()

        if not acct_row:
            raise ValueError(f"Account {upload_job.account_id} not found")

        session_json = decrypt_session_data(acct_row[0])
        session_data = json.loads(session_json)
        logger.info(
            "Session decrypted for account '%s' (platform=%s)",
            acct_row[1],
            acct_row[2],
        )

        # ── Step 4: Upload to Facebook via Playwright ──
        account_name = acct_row[1]
        proxy_url = upload_job.proxy_url or acct_row[3]
        logger.info(
            "Starting Playwright upload — video=%s, account=%s proxy=%s",
            video_path,
            account_name,
            "configured" if proxy_url else "none",
        )

        uploader = FacebookPlaywrightUploader(
            cookies=session_data,
            page_name=account_name,
            proxy_url=proxy_url,
            account_id=upload_job.account_id,
        )
        post_url = uploader.upload(
            video_path=video_path,
            caption=upload_job.caption or "",
            upload_job_id=upload_job_id,
        )

        resolved_post_url = post_url or f"https://www.facebook.com/{account_name}"

        # ── Phase 6: Affiliate seeding comment (best-effort add-on) ──
        if upload_job.affiliate_comment and post_url:
            try:
                logger.info(
                    "Starting affiliate comment seeding — job=%s post_url=%s",
                    upload_job_id,
                    post_url,
                )
                uploader.post_comment(
                    post_url=post_url,
                    comment_text=upload_job.affiliate_comment,
                    upload_job_id=upload_job_id,
                )
                logger.info("Affiliate comment seeded — job=%s", upload_job_id)
            except FacebookUploadError as exc:
                logger.error(
                    "Affiliate comment seeding failed — job=%s: %s (screenshot=%s)",
                    upload_job_id,
                    exc,
                    exc.screenshot_path,
                )
            except Exception as exc:
                logger.error(
                    "Affiliate comment seeding failed — job=%s: %s",
                    upload_job_id,
                    redact_sensitive(exc),
                    exc_info=True,
                )
        elif upload_job.affiliate_comment:
            logger.warning(
                "Affiliate comment skipped — job=%s has no extractable post_url",
                upload_job_id,
            )

        # ── Step 5: Mark success ──
        _update_upload_status(
            upload_job_id,
            UploadJobStatus.SUCCESS,
            post_url=resolved_post_url,
        )
        logger.info(
            "Upload complete — job=%s post_url=%s",
            upload_job_id,
            post_url,
        )

    except FacebookUploadError as exc:
        logger.error(
            "Playwright upload failed — job=%s: %s (screenshot=%s)",
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
            "Upload failed — job=%s: %s", upload_job_id, redact_sensitive(exc), exc_info=True
        )
        _update_upload_status(
            upload_job_id,
            UploadJobStatus.FAILED,
            error_log=redact_sensitive(exc),
        )
    finally:
        db.close()


# ── API Endpoints ─────────────────────────────────────────────────


@facebook_bp.route("/upload/facebook", methods=["POST"])
def upload_facebook():
    """Submit a Facebook upload job.

    Request JSON:
        {
            "video_job_id": 42,
            "account_id": 7,
            "caption": "Check this out! 🔥 #trending",
            "affiliate_comment": "Link mua hàng ở đây: https://..."
        }

    Creates an UploadJob row, dispatches background processing,
    returns the upload_job_id immediately.
    """
    data = request.get_json(force=True)

    video_job_id = data.get("video_job_id")
    account_id = data.get("account_id")
    caption = data.get("caption", "")
    affiliate_comment = data.get("affiliate_comment")
    proxy_url = data.get("proxy_url")

    if not video_job_id or not account_id:
        return jsonify({"error": "video_job_id and account_id required"}), 400

    # Create upload job record
    db = SessionLocal()
    try:
        job = UploadJob(
            video_job_id=video_job_id,
            account_id=account_id,
            caption=caption,
            proxy_url=proxy_url,
            affiliate_comment=affiliate_comment,
            status=UploadJobStatus.PENDING,
        )
        db.add(job)
        db.commit()
        job_id = str(job.id)
        logger.info("UploadJob created: %s", job_id)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create UploadJob: %s", redact_sensitive(exc))
        return jsonify({"error": redact_sensitive(exc)}), 500
    finally:
        db.close()

    # Dispatch background upload
    thread = threading.Thread(
        target=_do_facebook_upload,
        args=(job_id,),
        daemon=True,
    )
    thread.start()

    return jsonify({"upload_job_id": job_id, "status": "accepted"}), 202


@facebook_bp.route("/upload/status/<upload_job_id>", methods=["GET"])
def upload_status(upload_job_id):
    """Check current status of an upload job."""
    db = SessionLocal()
    try:
        job = (
            db.query(UploadJob)
            .filter(UploadJob.id == upload_job_id)
            .first()
        )
        if not job:
            return jsonify({"error": "Upload job not found"}), 404
        return jsonify(
            {
                "upload_job_id": str(job.id),
                "video_job_id": job.video_job_id,
                "account_id": job.account_id,
                "status": job.status.value,
                "post_url": job.post_url,
                "affiliate_comment": job.affiliate_comment,
                "error_log": job.error_log,
                "created_at": (
                    job.created_at.isoformat() if job.created_at else None
                ),
            }
        )
    finally:
        db.close()
