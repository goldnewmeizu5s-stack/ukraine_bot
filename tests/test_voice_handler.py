import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path


@pytest.mark.asyncio
async def test_ogg_to_wav():
    with patch("bot.services.audio.AudioSegment") as mock_audio:
        mock_segment = MagicMock()
        mock_audio.from_ogg.return_value = mock_segment
        from bot.services.audio import ogg_to_wav
        result = await ogg_to_wav(Path("/tmp/test.ogg"))
        assert result.suffix == ".wav"
        mock_audio.from_ogg.assert_called_once_with("/tmp/test.ogg")
        mock_segment.export.assert_called_once()


@pytest.mark.asyncio
async def test_mp3_to_ogg():
    with patch("bot.services.audio.AudioSegment") as mock_audio:
        mock_segment = MagicMock()
        mock_audio.from_mp3.return_value = mock_segment
        with patch("bot.services.audio.Path.unlink"):
            from bot.services.audio import mp3_to_ogg
            result = await mp3_to_ogg(b"fake_mp3_data")
            assert result.suffix == ".ogg"


def test_save_temp_ogg():
    from bot.services.audio import save_temp_ogg
    result = save_temp_ogg(b"fake_ogg_data")
    assert result.suffix == ".ogg"
    assert result.exists()
    result.unlink()


def test_cleanup_temp():
    import tempfile
    from bot.services.audio import cleanup_temp
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        path = Path(f.name)
    assert path.exists()
    cleanup_temp(path)
    assert not path.exists()


def test_cleanup_temp_nonexistent():
    from bot.services.audio import cleanup_temp
    cleanup_temp(Path("/tmp/nonexistent_file_12345.ogg"))


@pytest.mark.asyncio
async def test_cache_in_memory():
    from bot.utils.cache import InMemoryCache
    cache = InMemoryCache(maxsize=3)

    await cache.set("hello", b"world")
    result = await cache.get("hello")
    assert result == b"world"

    result = await cache.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_cache_lru_eviction():
    from bot.utils.cache import InMemoryCache
    cache = InMemoryCache(maxsize=2)

    await cache.set("key1", b"val1")
    await cache.set("key2", b"val2")
    await cache.set("key3", b"val3")

    result = await cache.get("key1")
    assert result is None

    result = await cache.get("key2")
    assert result == b"val2"

    result = await cache.get("key3")
    assert result == b"val3"


def test_seed_words_structure():
    from scripts.seed_vocabulary import SEED_WORDS
    assert len(SEED_WORDS) >= 90
    for word in SEED_WORDS:
        assert "ua" in word
        assert "ru" in word
        assert "category" in word
        assert isinstance(word["ua"], str)
        assert isinstance(word["ru"], str)


def test_seed_words_categories():
    from scripts.seed_vocabulary import SEED_WORDS
    categories = {w["category"] for w in SEED_WORDS}
    expected = {"greetings", "food", "transport", "numbers", "days_months", "phrases"}
    assert expected.issubset(categories)


def test_safe_html_escape():
    from bot.utils.constants import safe
    assert safe("<b>test</b>") == "&lt;b&gt;test&lt;/b&gt;"
    assert safe("normal text") == "normal text"
    assert safe("a & b") == "a &amp; b"


def test_progress_bar():
    from bot.utils.constants import progress_bar
    assert progress_bar(0, 10) == "░░░░░░░░"
    assert progress_bar(10, 10) == "▓▓▓▓▓▓▓▓"
    assert progress_bar(5, 10) == "▓▓▓▓░░░░"
    assert progress_bar(0, 0) == "░░░░░░░░"


def test_split_message():
    from bot.utils.constants import split_message
    short = "Hello world"
    assert split_message(short) == [short]

    long = ("paragraph one\n\n" * 100).strip()
    parts = split_message(long, max_len=200)
    assert len(parts) > 1
    for part in parts:
        assert len(part) <= 200 or "\n\n" not in part


def test_random_correct_no_repeat():
    from bot.utils.constants import random_correct
    results = [random_correct() for _ in range(20)]
    for i in range(1, len(results)):
        assert results[i] != results[i - 1]


def test_score_emoji():
    from bot.utils.constants import score_emoji
    assert score_emoji(10) == "🏆"
    assert score_emoji(7) == "👏"
    assert score_emoji(5) == "👍"
    assert score_emoji(3) == "💪"
    assert score_emoji(1) == "🌱"


def test_persistent_reply_kb():
    from bot.keyboards.inline import persistent_reply_kb
    kb = persistent_reply_kb()
    assert kb.is_persistent is True
    assert kb.resize_keyboard is True
    assert len(kb.keyboard) == 1
    assert len(kb.keyboard[0]) == 3


def test_main_menu_kb_callback_data():
    from bot.keyboards.inline import main_menu_kb
    kb = main_menu_kb()
    callbacks = []
    for row in kb.inline_keyboard:
        for btn in row:
            callbacks.append(btn.callback_data)
    assert "menu:translate" in callbacks
    assert "menu:vocab" in callbacks
    assert "menu:dialogue" in callbacks
    assert "menu:pronunciation" in callbacks
    assert "menu:listening" in callbacks
    assert "menu:grammar" in callbacks
    assert "menu:progress" in callbacks
    assert "menu:settings" in callbacks


def test_inline_button_text_length():
    from bot.keyboards.inline import (
        main_menu_kb, dialogue_topics_kb, grammar_topics_kb,
        pronunciation_difficulty_kb, vocab_categories_kb,
    )
    for kb_func in [main_menu_kb, dialogue_topics_kb, grammar_topics_kb, pronunciation_difficulty_kb, vocab_categories_kb]:
        kb = kb_func()
        for row in kb.inline_keyboard:
            for btn in row:
                assert len(btn.text) <= 25, f"Button text too long: '{btn.text}' ({len(btn.text)} chars)"
