from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.utils.constants import (
    DIALOGUE_TOPICS, GRAMMAR_TOPICS, VOCABULARY_CATEGORIES,
    LEVEL_NAMES, LEVEL_SHORT, PRONUNCIATION_DIFFICULTIES,
)


def persistent_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="🏠 Меню"),
            KeyboardButton(text="📚 Словник"),
            KeyboardButton(text="🎙 Вимова"),
        ]],
        resize_keyboard=True,
        is_persistent=True,
    )


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔄 Перекладач", callback_data="menu:translate")
    b.button(text="📚 Словник", callback_data="menu:vocab")
    b.button(text="💬 Діалоги", callback_data="menu:dialogue")
    b.button(text="🎙 Вимова", callback_data="menu:pronunciation")
    b.button(text="👂 Аудіювання", callback_data="menu:listening")
    b.button(text="📖 Граматика", callback_data="menu:grammar")
    b.button(text="📊 Прогрес", callback_data="menu:progress")
    b.button(text="⚙️ Налаштування", callback_data="menu:settings")
    b.adjust(2)
    return b.as_markup()


def level_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, short in LEVEL_SHORT.items():
        emoji = LEVEL_NAMES[key].split()[0]
        b.button(text=f"{emoji} {short}", callback_data=f"set:level:{key}")
    b.adjust(1)
    return b.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🏠 Меню", callback_data="menu:open")
    return b.as_markup()


def vocab_main_kb(due_count: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if due_count > 0:
        b.button(text=f"🎯 Повторення ({due_count})", callback_data="vocab:srs")
    else:
        b.button(text="✅ Все повторено", callback_data="vocab:sets")
    b.button(text="📋 Мої слова", callback_data="vocab:my_words")
    b.button(text="📦 Набори слів", callback_data="vocab:sets")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(1)
    return b.as_markup()


def vocab_train_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💡 Підказка", callback_data="vocab:hint")
    b.button(text="⏭ Далі", callback_data="vocab:next")
    b.adjust(2)
    return b.as_markup()


def vocab_correct_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⏭ Далі", callback_data="vocab:next")
    b.button(text="🔊 Послухати", callback_data="vocab:listen")
    b.adjust(2)
    return b.as_markup()


def vocab_incorrect_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔊 Послухати", callback_data="vocab:listen")
    b.button(text="⏭ Далі", callback_data="vocab:next")
    b.adjust(2)
    return b.as_markup()


def vocab_result_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Ще раунд", callback_data="vocab:srs")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(2)
    return b.as_markup()


def vocab_categories_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, name in VOCABULARY_CATEGORIES.items():
        b.button(text=name, callback_data=f"vocab:set:{key}")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(1)
    return b.as_markup()


def translate_save_kb(msg_id: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔊 Послухати", callback_data=f"tr:listen:{msg_id}")
    b.button(text="📚 Зберегти", callback_data=f"tr:save:{msg_id}")
    b.adjust(2)
    return b.as_markup()


def dialogue_topics_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, name in DIALOGUE_TOPICS.items():
        b.button(text=name, callback_data=f"dlg:topic:{key}")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(1)
    return b.as_markup()


def dialogue_hint_kb(turn: int = 1) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💡 Підказка", callback_data="dlg:hint")
    b.button(text="🔊 Повторити", callback_data="dlg:repeat")
    if turn > 1:
        b.button(text="⏭ Пропустити", callback_data="dlg:skip")
        b.button(text="🏁 Завершити", callback_data="dlg:finish")
        b.adjust(2, 2)
    else:
        b.adjust(2)
    return b.as_markup()


def dialogue_result_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Ще раз", callback_data="dlg:restart")
    b.button(text="🎲 Нова тема", callback_data="menu:dialogue")
    b.button(text="📚 Зберегти слова", callback_data="dlg:save_words")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(2, 2)
    return b.as_markup()


def pronunciation_difficulty_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, name in PRONUNCIATION_DIFFICULTIES.items():
        b.button(text=name, callback_data=f"pron:level:{key}")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(2, 2, 1)
    return b.as_markup()


def pronunciation_task_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔊 Ще раз", callback_data="pron:listen")
    b.button(text="⏭ Далі", callback_data="pron:next")
    b.adjust(2)
    return b.as_markup()


def pronunciation_result_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔁 Ще раз", callback_data="pron:retry")
    b.button(text="🔊 Еталон", callback_data="pron:listen")
    b.button(text="⏭ Далі", callback_data="pron:next")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(3, 1)
    return b.as_markup()


def listening_mode_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📝 Диктант", callback_data="list:mode:dictation")
    b.button(text="🔄 Переклад", callback_data="list:mode:translate")
    b.button(text="❓ Питання", callback_data="list:mode:question")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(1)
    return b.as_markup()


def listening_task_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔊 Повторити", callback_data="list:repeat")
    b.button(text="🐌 Повільніше", callback_data="list:slow")
    b.adjust(2)
    return b.as_markup()


def listening_result_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔊 Послухати", callback_data="list:repeat")
    b.button(text="⏭ Далі", callback_data="list:next")
    b.adjust(2)
    return b.as_markup()


def grammar_topics_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, name in GRAMMAR_TOPICS.items():
        b.button(text=name, callback_data=f"gram:topic:{key}")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(1)
    return b.as_markup()


def grammar_lesson_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🎯 Вправи", callback_data="gram:exercise")
    b.button(text="🔊 Приклади", callback_data="gram:listen")
    b.button(text="◀️ Назад", callback_data="menu:grammar")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(2, 2)
    return b.as_markup()


def grammar_exercise_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💡 Підказка", callback_data="gram:hint")
    b.button(text="⏭ Далі", callback_data="gram:next")
    b.adjust(2)
    return b.as_markup()


def settings_kb(level_name: str, goal: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Змінити рівень", callback_data="set:change_level")
    b.button(text="🎯 Змінити ціль", callback_data="set:change_goal")
    b.button(text="🏠 Меню", callback_data="menu:open")
    b.adjust(1)
    return b.as_markup()


def goal_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for n in [5, 10, 15, 20]:
        b.button(text=f"{n} слів", callback_data=f"set:goal:{n}")
    b.adjust(4)
    return b.as_markup()


def quick_review_kb(due: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=f"⚡ Швидке повторення — {min(due, 5)} слів", callback_data="vocab:quick")
    b.adjust(1)
    return b.as_markup()


def first_dialogue_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="▶️ Почнемо!", callback_data="dlg:start_first")
    b.adjust(1)
    return b.as_markup()
