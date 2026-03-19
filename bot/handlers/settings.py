import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import UserRepository, ProgressRepository, VocabularyRepository
from bot.handlers.states import SettingsStates
from bot.keyboards.inline import settings_keyboard, level_keyboard, back_to_menu_keyboard, main_menu_keyboard
from bot.utils.constants import LEVEL_NAMES

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "mode:settings")
async def on_settings_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.set_state(SettingsStates.main)
    await callback.message.edit_text("⚙️ Настройки:", reply_markup=settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings:level")
async def on_settings_level(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.set_state(SettingsStates.choosing_level)
    await callback.message.edit_text("Выберите уровень:", reply_markup=level_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings:daily_goal")
async def on_settings_goal(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.message.edit_text(
        f"📊 Текущая дневная цель: {db_user.daily_goal} слов\n\n"
        "Отправьте новое число (5-50):",
        reply_markup=back_to_menu_keyboard(),
    )
    await state.set_state(SettingsStates.setting_goal)
    await callback.answer()


@router.callback_query(F.data == "action:stats")
async def on_stats(callback: CallbackQuery, db_user: User, **kwargs) -> None:
    async with async_session() as session:
        progress_repo = ProgressRepository(session)
        weekly = await progress_repo.get_weekly_stats(db_user.id)
        vocab_repo = VocabularyRepository(session)
        word_count = await vocab_repo.get_word_count(db_user.id)

    level_name = LEVEL_NAMES.get(db_user.language_level.value, db_user.language_level.value)

    text = f"📊 Статистика\n\n"
    text += f"🎯 Уровень: {level_name}\n"
    text += f"🔥 Серия дней: {db_user.streak_days}\n"
    text += f"📚 Слов в словаре: {word_count}\n"
    text += f"📖 Всего выучено слов: {db_user.total_words_learned}\n"
    text += f"🎙 Голосовых минут: {db_user.total_voice_minutes:.1f}\n"
    text += f"📅 Сегодня слов: {db_user.words_today}/{db_user.daily_goal}\n\n"

    if weekly:
        text += "📈 За неделю:\n"
        for day in weekly:
            text += (
                f"  {day.date.strftime('%d.%m')}: "
                f"📖{day.words_learned} 🔄{day.words_reviewed} "
                f"💬{day.dialogues_completed} 👂{day.listening_exercises}\n"
            )

    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())
    await callback.answer()


from aiogram.filters import Command


@router.message(Command("stats"))
async def cmd_stats(message: Message, db_user: User, **kwargs) -> None:
    async with async_session() as session:
        progress_repo = ProgressRepository(session)
        weekly = await progress_repo.get_weekly_stats(db_user.id)
        vocab_repo = VocabularyRepository(session)
        word_count = await vocab_repo.get_word_count(db_user.id)

    level_name = LEVEL_NAMES.get(db_user.language_level.value, db_user.language_level.value)

    text = f"📊 Статистика\n\n"
    text += f"🎯 Уровень: {level_name}\n"
    text += f"🔥 Серия дней: {db_user.streak_days}\n"
    text += f"📚 Слов в словаре: {word_count}\n"
    text += f"📖 Всего выучено: {db_user.total_words_learned}\n"
    text += f"🎙 Голосовых минут: {db_user.total_voice_minutes:.1f}\n"

    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("level"))
async def cmd_level(message: Message, state: FSMContext, **kwargs) -> None:
    await message.answer("Выберите уровень:", reply_markup=level_keyboard())
