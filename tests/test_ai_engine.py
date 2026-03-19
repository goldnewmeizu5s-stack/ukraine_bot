import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


def _make_mock_response(content: str):
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    return mock


@pytest.mark.asyncio
async def test_translate_text():
    response_text = "🔄 Перевод: привіт\n📝 Транскрипция: [прывіт]"
    with patch("bot.services.ai_engine.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response(response_text)
        )
        from bot.services.ai_engine import translate_text
        result = await translate_text("привет", "русского", "украинский")
        assert "Перевод" in result


@pytest.mark.asyncio
async def test_detect_language_and_translate():
    response_text = "🔤 Определён язык: русский\n🔄 Перевод: привіт"
    with patch("bot.services.ai_engine.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response(response_text)
        )
        from bot.services.ai_engine import detect_language_and_translate
        result = await detect_language_and_translate("привет")
        assert "Перевод" in result


@pytest.mark.asyncio
async def test_evaluate_pronunciation_valid_json():
    json_response = json.dumps({
        "score": 8,
        "errors": ["мягкий 'і'"],
        "tips": ["тренуйте звук 'і'"],
        "encouragement": "Чудово!"
    })
    with patch("bot.services.ai_engine.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response(json_response)
        )
        from bot.services.ai_engine import evaluate_pronunciation
        result = await evaluate_pronunciation("привіт", "привіт")
        assert result["score"] == 8
        assert isinstance(result["errors"], list)


@pytest.mark.asyncio
async def test_evaluate_pronunciation_invalid_json():
    with patch("bot.services.ai_engine.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response("not valid json at all")
        )
        from bot.services.ai_engine import evaluate_pronunciation
        result = await evaluate_pronunciation("привіт", "прівет")
        assert "score" in result
        assert result["score"] == 5


@pytest.mark.asyncio
async def test_generate_listening_exercise():
    exercise = json.dumps({
        "text_ua": "Добрий ранок",
        "text_ru": "Доброе утро",
        "key_words": [{"ua": "ранок", "ru": "утро"}],
        "question_ua": "Яка пора доби?",
        "question_ru": "Какое время суток?",
        "answer": "ранок"
    })
    with patch("bot.services.ai_engine.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response(exercise)
        )
        from bot.services.ai_engine import generate_listening_exercise
        result = await generate_listening_exercise()
        assert "text_ua" in result
        assert "text_ru" in result


@pytest.mark.asyncio
async def test_explain_grammar():
    response_text = "📖 Правило: відмінки...\n📝 Примеры..."
    with patch("bot.services.ai_engine.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response(response_text)
        )
        from bot.services.ai_engine import explain_grammar
        result = await explain_grammar("падежи")
        assert "Правило" in result
