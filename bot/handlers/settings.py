import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User, LanguageLevel
from bot.db.base import async_session
from bot.db.repositories import UserRepository, ProgressRepository, VocabularyRepository
from bot.handlers.states import SettingsStates
from bot.keyboards.inline import settings_kb, level_kb, goal_kb, main_menu_kb, back_to_menu_kb
from bot.utils.constants import LEVEL_NAMES, LEVEL_EMOJIS, progress_bar

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:settings")
async def on_settings_mode(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    await state.set_state(SettingsStates.main)
    level_name = LEVEL_NAMES.get(db_user.language_level.value, "?")
    text = (
        f"⚙️ <b>Налаштування</b>\n\n"
        f"📊 Рівень: {level_name}\n"
        f"🎯 Ціль: {db_user.daily_goal} слів/день"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=settings_kb(level_name, db_user.daily_goal),
    )


@router.callback_query(F.data == "set:change_level")
async def on_settings_level(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Оберіть рівень:",
        parse_mode="HTML",
        reply_markup=level_kb(),
    )


@router.callback_query(F.data == "set:change_goal")
async def on_settings_goal(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "🎯 Оберіть ціль:",
        parse_mode="HTML",
        reply_markup=goal_kb(),
    )


@router.callback_query(F.data.startswith("set:goal:"))
async def on_goal_selected(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    goal = int(callback.data.split(":")[2])
    from sqlalchemy import update
    from bot.db.models import User as UserModel
    from datetime import datetime
    async with async_session() as session:
        await session.execute(
            update(UserModel).where(UserModel.id == db_user.id).values(
                daily_goal=goal, updated_at=datetime.utcnow()
            )
        )
        await session.commit()

    await callback.message.edit_text(
        f"✅ Збережено: {goal} слів/день",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )


@router.callback_query(F.data == "menu:progress")
async def on_progress(callback: CallbackQuery, db_user: User, **kwargs) -> None:
    await callback.answer()
    text = await _build_stats(db_user)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb())


@router.message(Command("stats"))
async def cmd_stats(message: Message, db_user: User, **kwargs) -> None:
    text = await _build_stats(db_user)
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())


@router.message(Command("level"))
async def cmd_level(message: Message, **kwargs) -> None:
    await message.answer("Оберіть рівень:", parse_mode="HTML", reply_markup=level_kb())


async def _build_stats(db_user: User) -> str:
    async with async_session() as session:
        progress_repo = ProgressRepository(session)
        weekly = await progress_repo.get_weekly_stats(db_user.id)
        vocab_repo = VocabularyRepository(session)
        word_count = await vocab_repo.get_word_count(db_user.id)

    streak_text = f"🔥 <b>{db_user.streak_days}</b> днів поспіль" if db_user.streak_days > 0 else ""
    bar = progress_bar(db_user.words_today, db_user.daily_goal)
    total_hours = db_user.total_voice_minutes / 60

    text = "📊 <b>Прогрес</b>\n\n"
    if streak_text:
        text += f"{streak_text}\n\n"

    text += (
        f"▪️ Сьогодні:\n"
        f"📚 {db_user.words_today}/{db_user.daily_goal} слів  {bar}\n"
        f"🎙 {db_user.total_voice_minutes:.0f} хв практики\n\n"
        f"▪️ Загалом:\n"
        f"📚 {word_count} слів в словнику\n"
        f"📖 {db_user.total_words_learned} вивчено\n"
        f"🎙 {total_hours:.1f} год практики"
    )

    if weekly:
        text += "\n\n▪️ Тиждень:"
        for day in weekly:
            text += (
                f"\n{day.date.strftime('%d.%m')}: "
                f"📖{day.words_learned} 🔄{day.words_reviewed} "
                f"💬{day.dialogues_completed} 👂{day.listening_exercises}"
            )

    return text
