"""Script generator — produces short video narration from a topic."""

import os
import logging

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def generate_script(topic: str) -> str:
    """Generate a short narration script (3-5 sentences) for a video topic.

    Uses OpenAI when an API key is configured; falls back to a
    deterministic mock so the pipeline can run without credentials.

    Args:
        topic: The video topic / trend keyword.

    Returns:
        Plain-text narration script.
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning mock script")
        return _mock_script(topic)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a short-form video scriptwriter. "
                        "Write a compelling narration script in 3-5 sentences. "
                        "Keep it punchy, suitable for TikTok / YouTube Shorts. "
                        "Output ONLY the narration text, no stage directions."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Write a script about: {topic}",
                },
            ],
            max_tokens=300,
            temperature=0.8,
        )
        script = response.choices[0].message.content.strip()
        logger.info("Script generated via OpenAI (%d chars)", len(script))
        return script

    except Exception as exc:
        logger.error("OpenAI call failed, falling back to mock: %s", exc)
        return _mock_script(topic)


def _mock_script(topic: str) -> str:
    """Deterministic fallback when OpenAI is unavailable."""
    return (
        f"Did you know about {topic}? "
        f"It's one of the hottest trends right now. "
        f"In this video, we'll break down everything you need to know about {topic}. "
        f"Stay tuned — you don't want to miss this. "
        f"Like, follow, and share for more trending content!"
    )
