import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_synthesize_ukrainian_success():
    mock_response = MagicMock()
    mock_response.content = b"fake_audio_bytes"
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("bot.services.elevenlabs.httpx.AsyncClient", return_value=mock_client_instance):
        with patch("bot.services.elevenlabs.audio_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            from bot.services.elevenlabs import synthesize_ukrainian
            result = await synthesize_ukrainian("Привіт")
            assert result == b"fake_audio_bytes"


@pytest.mark.asyncio
async def test_synthesize_ukrainian_cache_hit():
    cached_audio = b"cached_audio_data"
    with patch("bot.services.elevenlabs.audio_cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=cached_audio)
        from bot.services.elevenlabs import synthesize_ukrainian
        result = await synthesize_ukrainian("Привіт", use_cache=True)
        assert result == cached_audio


@pytest.mark.asyncio
async def test_synthesize_ukrainian_no_cache():
    mock_response = MagicMock()
    mock_response.content = b"fresh_audio"
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("bot.services.elevenlabs.httpx.AsyncClient", return_value=mock_client_instance):
        with patch("bot.services.elevenlabs.audio_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            from bot.services.elevenlabs import synthesize_ukrainian
            result = await synthesize_ukrainian("Привіт", use_cache=False)
            assert result == b"fresh_audio"
