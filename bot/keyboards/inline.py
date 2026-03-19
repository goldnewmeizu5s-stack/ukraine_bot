from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.constants import (
    DIALOGUE_TOPICS, GRAMMAR_TOPICS, VOCABULARY_CATEGORIES,
    LEVEL_NAMES, PRONUNCIATION_DIFFICULTIES,
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Переводчик", callback_data="mode:translate"),
            InlineKeyboardButton(text="📚 Словарь", callback_data="mode:vocabulary"),
        ],
        [
            InlineKeyboardButton(text="💬 Диалоги", callback_data="mode:dialogue"),
            InlineKeyboardButton(text="🎙 Произношение", callback_data="mode:pronunciation"),
        ],
        [
            InlineKeyboardButton(text="👂 Аудирование", callback_data="mode:listening"),
            InlineKeyboardButton(text="📖 Грамматика", callback_data="mode:grammar"),
        ],
        [
            InlineKeyboardButton(text="📊 Мой прогресс", callback_data="action:stats"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="mode:settings"),
        ],
    ])


def level_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"level:{key}")]
        for key, name in LEVEL_NAMES.items()
    ])


def vocabulary_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Мои слова", callback_data="vocab:my_words"),
            InlineKeyboardButton(text="➕ Добавить слово", callback_data="vocab:add_word"),
        ],
        [
            InlineKeyboardButton(text="🎯 Тренировка", callback_data="vocab:train"),
            InlineKeyboardButton(text="📋 Тематические наборы", callback_data="vocab:categories"),
        ],
        [
            InlineKeyboardButton(text="🔄 Повторение (SRS)", callback_data="vocab:srs"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад в меню", callback_data="action:main_menu"),
        ],
    ])


def dialogue_topics_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    topics = list(DIALOGUE_TOPICS.items())
    for i in range(0, len(topics), 2):
        row = [InlineKeyboardButton(text=topics[i][1], callback_data=f"dialogue:{topics[i][0]}")]
        if i + 1 < len(topics):
            row.append(InlineKeyboardButton(text=topics[i + 1][1], callback_data=f"dialogue:{topics[i + 1][0]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад в меню", callback_data="action:main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def grammar_topics_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    topics = list(GRAMMAR_TOPICS.items())
    for i in range(0, len(topics), 2):
        row = [InlineKeyboardButton(text=topics[i][1], callback_data=f"grammar:{topics[i][0]}")]
        if i + 1 < len(topics):
            row.append(InlineKeyboardButton(text=topics[i + 1][1], callback_data=f"grammar:{topics[i + 1][0]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад в меню", callback_data="action:main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vocabulary_categories_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    cats = list(VOCABULARY_CATEGORIES.items())
    for i in range(0, len(cats), 2):
        row = [InlineKeyboardButton(text=cats[i][1], callback_data=f"vocabcat:{cats[i][0]}")]
        if i + 1 < len(cats):
            row.append(InlineKeyboardButton(text=cats[i + 1][1], callback_data=f"vocabcat:{cats[i + 1][0]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="mode:vocabulary")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pronunciation_difficulty_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"pronun:{key}")]
        for key, name in PRONUNCIATION_DIFFICULTIES.items()
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад в меню", callback_data="action:main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="action:main_menu")],
    ])


def continue_or_stop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="▶️ Продолжить", callback_data="action:continue"),
            InlineKeyboardButton(text="⏹ Завершить", callback_data="action:stop"),
        ],
    ])


def listening_options_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Повторить аудио", callback_data="listen:repeat")],
        [InlineKeyboardButton(text="📝 Показать текст", callback_data="listen:show_text")],
        [InlineKeyboardButton(text="▶️ Следующее", callback_data="listen:next")],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="action:main_menu")],
    ])


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Уровень языка", callback_data="settings:level")],
        [InlineKeyboardButton(text="📊 Дневная цель", callback_data="settings:daily_goal")],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="action:main_menu")],
    ])
