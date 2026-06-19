import os
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Worker starting")
    yield
    logger.info("AI Worker shutting down")

app = FastAPI(title="SocialFlow AI Worker", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "ai-worker",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    return {"message": "SocialFlow AI Worker API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
