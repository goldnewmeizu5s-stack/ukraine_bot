import logging
from pathlib import Path
from openai import AsyncOpenAI
from bot.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def transcribe_voice(file_path: Path, language: str = "ru") -> str:
    try:
        with open(file_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="text",
            )
        transcription = response.strip() if isinstance(response, str) else str(response).strip()
        logger.info("Transcribed %s chars (lang=%s)", len(transcription), language)
        return transcription
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        raise
