import pytest
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from pathlib import Path


@pytest.mark.asyncio
async def test_transcribe_voice_russian():
    mock_response = "привет как дела"
    with patch("bot.services.whisper.client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
        with patch("builtins.open", mock_open(read_data=b"fake_audio")):
            from bot.services.whisper import transcribe_voice
            result = await transcribe_voice(Path("/tmp/test.wav"), language="ru")
            assert result == "привет как дела"
            mock_client.audio.transcriptions.create.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_voice_ukrainian():
    mock_response = "привіт як справи"
    with patch("bot.services.whisper.client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
        with patch("builtins.open", mock_open(read_data=b"fake_audio")):
            from bot.services.whisper import transcribe_voice
            result = await transcribe_voice(Path("/tmp/test.wav"), language="uk")
            assert result == "привіт як справи"


@pytest.mark.asyncio
async def test_transcribe_voice_strips_whitespace():
    mock_response = "  текст з пробілами  "
    with patch("bot.services.whisper.client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
        with patch("builtins.open", mock_open(read_data=b"fake_audio")):
            from bot.services.whisper import transcribe_voice
            result = await transcribe_voice(Path("/tmp/test.wav"))
            assert result == "текст з пробілами"


@pytest.mark.asyncio
async def test_transcribe_voice_error():
    with patch("bot.services.whisper.client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(side_effect=Exception("API Error"))
        with patch("builtins.open", mock_open(read_data=b"fake_audio")):
            from bot.services.whisper import transcribe_voice
            with pytest.raises(Exception, match="API Error"):
                await transcribe_voice(Path("/tmp/test.wav"))
