"""
SocialFlow AI Worker — Trend Engine
FastAPI server + APScheduler for periodic trend data collection.
Mockup mode: generates fake trend data every 1 minute for testing.
Production: crawl TikTok Creative Center / Facebook every 2 hours.
"""

import os
import asyncio
import logging
import random
from datetime import datetime
from fastapi import BackgroundTasks, FastAPI
from contextlib import asynccontextmanager
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import engine, SessionLocal
from models import Base, Trend, TrendPlatform, VideoJob, VideoJobStatus
from video_factory.editor_ffmpeg import FFmpegEditor
from video_factory.generator_script import generate_script
from video_factory.generator_voice import generate_voice

# Environment
TEST_MODE = os.getenv("TREND_TEST_MODE", "1") == "1"
TREND_INTERVAL_MINUTES = int(os.getenv("TREND_INTERVAL_MINUTES", "1" if TEST_MODE else "120"))
OUTPUT_DIR = os.getenv("VIDEO_OUTPUT_DIR", "./output")
STOCK_VIDEO = os.getenv("STOCK_VIDEO_PATH", "./assets/stock_background.mp4")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database init ---
Base.metadata.create_all(bind=engine)
logger.info("Trend tables ensured in database")


# --- Mockup Trend Data ---
MOCKUP_TRENDS: dict[TrendPlatform, list[dict[str, str | int]]] = {
    TrendPlatform.TIKTOK: [
        {"keyword": "#CapCut", "base_volume": 950000},
        {"keyword": "#Tet2026", "base_volume": 780000},
        {"keyword": "#LearnOnTikTok", "base_volume": 650000},
        {"keyword": "#VietNamTrending", "base_volume": 520000},
        {"keyword": "#DanceChallenge", "base_volume": 890000},
        {"keyword": "#CookingHacks", "base_volume": 430000},
        {"keyword": "#FashionHaul", "base_volume": 370000},
    ],
    TrendPlatform.FACEBOOK: [
        {"keyword": "Lunar New Year", "base_volume": 820000},
        {"keyword": "Reels Challenge", "base_volume": 710000},
        {"keyword": "AI Art Generator", "base_volume": 550000},
        {"keyword": "Travel Vietnam", "base_volume": 480000},
        {"keyword": "Street Food", "base_volume": 440000},
    ],
    TrendPlatform.YOUTUBE: [
        {"keyword": "Shorts Viral", "base_volume": 990000},
        {"keyword": "Music Cover", "base_volume": 670000},
        {"keyword": "Tech Reviews", "base_volume": 510000},
        {"keyword": "Vlog Daily", "base_volume": 460000},
        {"keyword": "Gaming Live", "base_volume": 730000},
    ],
}


def crawl_trends():
    """
    Collect trend data and insert into PostgreSQL.
    In mockup mode: generates randomized volumes around base values.
    In production: uses Playwright to scrape TikTok/Facebook.
    """
    logger.info(f"Trend crawl starting (mockup={TEST_MODE})...")

    db = SessionLocal()
    try:
        count = 0
        for platform, keywords in MOCKUP_TRENDS.items():
            for item in keywords:
                # Randomize volume ±25% to simulate fluctuation
                jitter = random.uniform(0.75, 1.25)
                volume = int(item["base_volume"] * jitter)

                trend = Trend(
                    platform=platform,
                    keyword=item["keyword"],
                    volume=volume,
                    extracted_at=datetime.utcnow(),
                )
                db.add(trend)
                count += 1

        db.commit()
        logger.info(f"Trend crawl complete — inserted {count} rows across {len(MOCKUP_TRENDS)} platforms")

    except Exception as e:
        db.rollback()
        logger.error(f"Trend crawl failed: {e}", exc_info=True)
    finally:
        db.close()


# --- Scheduler ---
scheduler = BackgroundScheduler(daemon=True)


def start_scheduler():
    trigger = IntervalTrigger(minutes=TREND_INTERVAL_MINUTES)
    scheduler.add_job(
        crawl_trends,
        trigger=trigger,
        id="trend_crawl_job",
        name="Trend Crawl",
        replace_existing=True,
        max_instances=1,  # prevent overlap
    )
    scheduler.start()
    logger.info(f"Scheduler started — interval={TREND_INTERVAL_MINUTES}min, mockup={TEST_MODE}")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Worker starting — Trend Engine Initializing")
    start_scheduler()
    # Immediate first crawl so DB has data on startup
    crawl_trends()
    yield
    stop_scheduler()
    logger.info("AI Worker shutting down")


app = FastAPI(title="SocialFlow AI Worker — Trend Engine", lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "ai-worker",
        "scheduler_running": scheduler.running,
        "mockup_mode": TEST_MODE,
        "trend_interval_min": TREND_INTERVAL_MINUTES,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    return {"message": "SocialFlow AI Worker API — Trend Engine + Video Factory"}


# --- Video Factory (Phase 4 Part 2) ---

class VideoProcessRequest(BaseModel):
    job_id: str
    topic: str


def _update_job_status(
    job_id: str,
    status: VideoJobStatus,
    **extra_fields,
) -> None:
    """Update a VideoJob row in PostgreSQL."""
    db = SessionLocal()
    try:
        job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
        if not job:
            job = VideoJob(job_id=job_id, topic="", status=status)
            db.add(job)
        else:
            job.status = status
        for field, value in extra_fields.items():
            setattr(job, field, value)
        job.updated_at = datetime.utcnow()
        db.commit()
        logger.info("Job %s status -> %s", job_id, status.value)
    except Exception as exc:
        db.rollback()
        logger.error("DB update failed for job %s: %s", job_id, exc)
    finally:
        db.close()


def _process_video(job_id: str, topic: str) -> None:
    """Background task: full Video Factory pipeline.

    Steps:
      1. Generate narration script (OpenAI / mock)
      2. Text-to-speech via edge-tts
      3. Merge TTS audio onto stock background video
      4. Mark done & store output path
    On any error: mark job as failed with error log.
    """
    logger.info("Pipeline start — job=%s topic=%s", job_id, topic)

    # Ensure output directory exists
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        # --- Step 1: Generate Script ---
        _update_job_status(job_id, VideoJobStatus.GENERATING_SCRIPT, topic=topic)
        script_text = generate_script(topic)
        logger.info("Script ready (%d chars): %.80s...", len(script_text), script_text)

        # --- Step 2: Text-to-Speech ---
        _update_job_status(job_id, VideoJobStatus.GENERATING_VOICE, script=script_text)
        audio_path = os.path.join(job_dir, "narration.mp3")
        # edge-tts is async — run in a new event loop from this sync context
        asyncio.run(generate_voice(script_text, audio_path))
        logger.info("TTS audio saved: %s", audio_path)

        # --- Step 3: Render — merge audio onto stock video ---
        _update_job_status(job_id, VideoJobStatus.RENDERING, audio_url=audio_path)
        output_path = os.path.join(job_dir, "final.mp4")

        if os.path.isfile(STOCK_VIDEO):
            FFmpegEditor.merge_audio_video(STOCK_VIDEO, audio_path, output_path)
            logger.info("Render complete: %s", output_path)
        else:
            # No stock video available — skip merge, log warning
            logger.warning(
                "Stock video not found at %s — skipping merge, marking audio-only",
                STOCK_VIDEO,
            )
            output_path = audio_path  # fallback: audio is the deliverable

        # --- Step 4: Done ---
        _update_job_status(
            job_id,
            VideoJobStatus.DONE,
            video_url=output_path,
        )
        logger.info("Pipeline complete — job=%s output=%s", job_id, output_path)

    except Exception as exc:
        logger.error("Pipeline failed — job=%s: %s", job_id, exc, exc_info=True)
        _update_job_status(
            job_id,
            VideoJobStatus.FAILED,
            error_log=str(exc),
        )


@app.post("/video/process")
async def process_video(req: VideoProcessRequest, background_tasks: BackgroundTasks):
    logger.info("Received job %s for topic %s", req.job_id, req.topic)

    # Create initial job record in DB
    _update_job_status(req.job_id, VideoJobStatus.PENDING, topic=req.topic)

    background_tasks.add_task(_process_video, req.job_id, req.topic)
    return {"job_id": req.job_id, "status": "accepted"}


@app.get("/video/status/{job_id}")
async def get_job_status(job_id: str):
    """Check the current status of a video processing job."""
    db = SessionLocal()
    try:
        job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
        if not job:
            return {"error": "Job not found", "job_id": job_id}
        return {
            "job_id": job.job_id,
            "topic": job.topic,
            "status": job.status.value,
            "video_url": job.video_url,
            "error_log": job.error_log,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
