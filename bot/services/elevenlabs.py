import logging
import httpx
from bot.config import settings
from bot.utils.cache import audio_cache

logger = logging.getLogger(__name__)

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


async def synthesize_ukrainian(text: str, use_cache: bool = True) -> bytes:
    if use_cache:
        cached = await audio_cache.get(text)
        if cached:
            logger.debug("Cache hit for TTS: %s...", text[:30])
            return cached

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ELEVENLABS_API_URL.format(voice_id=settings.ELEVENLABS_VOICE_ID),
                headers={
                    "xi-api-key": settings.ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,
                        "use_speaker_boost": True,
                    },
                },
                timeout=30.0,
            )
            if response.status_code != 200:
                logger.error(
                    "ElevenLabs API error %d: %s",
                    response.status_code,
                    response.text[:500],
                )
            response.raise_for_status()
            audio_bytes = response.content

        if use_cache and len(text) < 500:
            await audio_cache.set(text, audio_bytes)

        logger.info("Synthesized %d bytes of audio for: %s...", len(audio_bytes), text[:30])
        return audio_bytes
    except Exception as e:
        logger.error("ElevenLabs TTS failed: %s", e)
        raise
