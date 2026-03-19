import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_synthesize_ukrainian_success():
    async def fake_stream():
        yield {"type": "audio", "data": b"fake_audio_bytes"}

    mock_communicate = MagicMock()
    mock_communicate.stream = fake_stream

    with patch("bot.services.tts.edge_tts.Communicate", return_value=mock_communicate):
        with patch("bot.services.tts.audio_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            from bot.services.tts import synthesize_ukrainian
            result = await synthesize_ukrainian("Привіт")
            assert result == b"fake_audio_bytes"


@pytest.mark.asyncio
async def test_synthesize_ukrainian_cache_hit():
    cached_audio = b"cached_audio_data"
    with patch("bot.services.tts.audio_cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=cached_audio)
        from bot.services.tts import synthesize_ukrainian
        result = await synthesize_ukrainian("Привіт", use_cache=True)
        assert result == cached_audio


@pytest.mark.asyncio
async def test_synthesize_ukrainian_no_cache():
    async def fake_stream():
        yield {"type": "audio", "data": b"fresh_audio"}

    mock_communicate = MagicMock()
    mock_communicate.stream = fake_stream

    with patch("bot.services.tts.edge_tts.Communicate", return_value=mock_communicate):
        with patch("bot.services.tts.audio_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            from bot.services.tts import synthesize_ukrainian
            result = await synthesize_ukrainian("Привіт", use_cache=False)
            assert result == b"fresh_audio"
