import os
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Upload Engine starting")
    yield
    logger.info("Upload Engine shutting down")

app = FastAPI(title="SocialFlow Upload Engine", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "upload-engine",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    return {"message": "SocialFlow Upload Engine API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
