import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import VocabularyRepository, UserRepository, ProgressRepository
from bot.handlers.states import VocabularyStates
from bot.handlers.voice import send_voice_response
from bot.keyboards.inline import (
    vocabulary_menu_keyboard, vocabulary_categories_keyboard,
    back_to_menu_keyboard, continue_or_stop_keyboard,
)
from bot.utils.constants import PROCESSING_THINK

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "mode:vocabulary")
async def on_vocabulary_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.set_state(VocabularyStates.browsing)
    await callback.message.edit_text(
        "📚 Словарь\n\nВыберите действие:",
        reply_markup=vocabulary_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "vocab:my_words")
async def on_my_words(callback: CallbackQuery, db_user: User, **kwargs) -> None:
    async with async_session() as session:
        repo = VocabularyRepository(session)
        words = await repo.get_user_words(db_user.id, limit=20)

    if not words:
        await callback.message.edit_text(
            "📚 Ваш словарь пуст. Добавьте слова или начните с /start!",
            reply_markup=vocabulary_menu_keyboard(),
        )
        await callback.answer()
        return

    text = "📚 Ваши последние слова:\n\n"
    for w in words[:20]:
        level_bar = "🟢" * min(w.comfort_level, 5) + "⚪" * (5 - min(w.comfort_level, 5))
        text += f"**{w.word_ua}** — {w.word_ru} {level_bar}\n"

    text += f"\nВсего слов: {len(words)}"
    await callback.message.edit_text(text, reply_markup=vocabulary_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "vocab:add_word")
async def on_add_word(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.set_state(VocabularyStates.adding_word)
    await callback.message.edit_text(
        "➕ Добавление слова\n\n"
        'Отправьте слово в формате:\n`украинское слово - русский перевод`\n\nНапример: `кохання - любовь`',
        reply_markup=back_to_menu_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


async def handle_add_word_input(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    if "-" not in text:
        await message.reply(
            'Используйте формат: `украинское слово - русский перевод`',
            parse_mode="Markdown",
        )
        return

    parts = text.split("-", 1)
    word_ua = parts[0].strip()
    word_ru = parts[1].strip()

    if not word_ua or not word_ru:
        await message.reply("Оба слова должны быть указаны.")
        return

    async with async_session() as session:
        repo = VocabularyRepository(session)
        await repo.add_word(user_id=db_user.id, word_ua=word_ua, word_ru=word_ru)

    await message.reply(
        f"✅ Слово добавлено!\n\n**{word_ua}** — {word_ru}\n\nОтправьте ещё слово или вернитесь в меню.",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "vocab:categories")
async def on_categories(callback: CallbackQuery, **kwargs) -> None:
    await callback.message.edit_text(
        "📋 Тематические наборы:",
        reply_markup=vocabulary_categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vocabcat:"))
async def on_category_selected(callback: CallbackQuery, db_user: User, **kwargs) -> None:
    category = callback.data.split(":")[1]
    async with async_session() as session:
        repo = VocabularyRepository(session)
        words = await repo.get_user_words(db_user.id, category=category, limit=30)

    if not words:
        await callback.message.edit_text(
            f"В категории пока нет слов.",
            reply_markup=vocabulary_menu_keyboard(),
        )
        await callback.answer()
        return

    text = f"📋 Категория: {category}\n\n"
    for w in words:
        text += f"**{w.word_ua}** [{w.transcription or ''}] — {w.word_ru}\n"

    await callback.message.edit_text(text, reply_markup=vocabulary_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "vocab:train")
async def on_train(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await state.set_state(VocabularyStates.training)
    async with async_session() as session:
        repo = VocabularyRepository(session)
        words = await repo.get_user_words(db_user.id, limit=100)

    if not words:
        await callback.message.edit_text(
            "Словарь пуст! Начните с /start для загрузки базовых слов.",
            reply_markup=vocabulary_menu_keyboard(),
        )
        await callback.answer()
        return

    import random
    word = random.choice(words)
    await state.update_data(training_word_id=word.id, training_word_ua=word.word_ua, training_word_ru=word.word_ru)

    await send_voice_response(
        callback.message,
        f"🎯 Переведите на русский:\n\n🇺🇦 **{word.word_ua}**",
        ua_text_for_tts=word.word_ua,
    )
    await callback.answer()


@router.callback_query(F.data == "vocab:srs")
async def on_srs_review(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await state.set_state(VocabularyStates.srs_review)
    async with async_session() as session:
        repo = VocabularyRepository(session)
        words = await repo.get_words_for_review(db_user.id, limit=1)

    if not words:
        await callback.message.edit_text(
            "🎉 Нет слов для повторения! Все слова повторены.",
            reply_markup=vocabulary_menu_keyboard(),
        )
        await callback.answer()
        return

    word = words[0]
    await state.update_data(srs_word_id=word.id, srs_word_ua=word.word_ua, srs_word_ru=word.word_ru)

    await send_voice_response(
        callback.message,
        f"🔄 Повторение (SRS)\n\nПереведите на русский:\n\n🇺🇦 **{word.word_ua}**",
        ua_text_for_tts=word.word_ua,
    )
    await callback.answer()
