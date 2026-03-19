import logging
import tempfile
from pathlib import Path
from pydub import AudioSegment

logger = logging.getLogger(__name__)


async def ogg_to_wav(ogg_path: Path) -> Path:
    try:
        audio = AudioSegment.from_ogg(str(ogg_path))
        wav_path = ogg_path.with_suffix(".wav")
        audio.export(str(wav_path), format="wav")
        logger.debug("Converted OGG to WAV: %s", wav_path)
        return wav_path
    except Exception as e:
        logger.error("OGG to WAV conversion failed: %s", e)
        raise


async def mp3_to_ogg(mp3_bytes: bytes) -> Path:
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(mp3_bytes)
            mp3_path = Path(f.name)

        audio = AudioSegment.from_mp3(str(mp3_path))
        ogg_path = mp3_path.with_suffix(".ogg")
        audio.export(str(ogg_path), format="ogg", codec="libopus")
        mp3_path.unlink(missing_ok=True)
        logger.debug("Converted MP3 to OGG: %s", ogg_path)
        return ogg_path
    except Exception as e:
        logger.error("MP3 to OGG conversion failed: %s", e)
        raise


def cleanup_temp(*paths: Path) -> None:
    for path in paths:
        try:
            if path and path.exists():
                path.unlink()
        except Exception as e:
            logger.warning("Failed to cleanup temp file %s: %s", path, e)


def save_temp_ogg(file_data: bytes) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        if isinstance(file_data, bytes):
            f.write(file_data)
        else:
            f.write(file_data.read())
        return Path(f.name)
