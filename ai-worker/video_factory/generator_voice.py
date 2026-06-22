"""Voice generator — converts text to speech using edge-tts."""

import os
import logging

import edge_tts

logger = logging.getLogger(__name__)

# Default Vietnamese voice; override via env var
DEFAULT_VOICE = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")


async def generate_voice(
    text: str,
    output_path: str,
    voice: str | None = None,
) -> str:
    """Convert text to an MP3 audio file via edge-tts.

    Args:
        text: The narration script to synthesize.
        output_path: Where to write the .mp3 file.
        voice: Edge-TTS voice identifier. Defaults to ``vi-VN-HoaiMyNeural``.

    Returns:
        The output_path on success.
    """
    voice = voice or DEFAULT_VOICE
    logger.info("TTS starting — voice=%s, output=%s, text_len=%d", voice, output_path, len(text))

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

    logger.info("TTS complete: %s", output_path)
    return output_path
