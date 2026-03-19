import logging
import io
import edge_tts
from bot.utils.cache import audio_cache

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "uk-UA-PolinaNeural"


async def synthesize_ukrainian(text: str, voice: str = DEFAULT_VOICE, use_cache: bool = True) -> bytes:
    cache_key = f"{voice}:{text}"

    if use_cache:
        cached = await audio_cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for TTS: %s...", text[:30])
            return cached

    try:
        communicate = edge_tts.Communicate(text, voice)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])

        audio_bytes = buffer.getvalue()
        if not audio_bytes:
            raise RuntimeError("edge-tts returned empty audio")

        if use_cache and len(text) < 500:
            await audio_cache.set(cache_key, audio_bytes)

        logger.info("Synthesized %d bytes of audio for: %s...", len(audio_bytes), text[:30])
        return audio_bytes
    except Exception as e:
        logger.error("edge-tts TTS failed: %s", e)
        raise
