import logging
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from bot.db.models import LanguageLevel, User
from bot.db.repositories import UserRepository, VocabularyRepository
from bot.db.base import async_session
from bot.keyboards.inline import (
    main_menu_kb, level_kb, persistent_reply_kb, back_to_menu_kb, quick_review_kb,
)
from bot.utils.constants import (
    WELCOME_TEXT, ONBOARDING_VOICE_PROMPT, HELP_TEXT, CANCEL_TEXT,
    MAIN_MENU_TEXT, LEVEL_NAMES, LEVEL_EMOJIS, UNSUPPORTED_CONTENT,
    progress_bar,
)
from bot.handlers.states import OnboardingStates
from scripts.seed_vocabulary import SEED_WORDS

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: User, **kwargs) -> None:
    await state.clear()
    await message.answer(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=level_kb(),
    )
    await message.answer(
        "⬆️",
        reply_markup=persistent_reply_kb(),
    )


@router.callback_query(F.data.startswith("set:level:"))
async def on_level_selected(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    level_key = callback.data.split(":")[2]
    try:
        level = LanguageLevel(level_key)
    except ValueError:
        return

    async with async_session() as session:
        user_repo = UserRepository(session)
        await user_repo.update_level(db_user.id, level)

        vocab_repo = VocabularyRepository(session)
        word_count = await vocab_repo.get_word_count(db_user.id)
        if word_count == 0:
            for word_data in SEED_WORDS:
                await vocab_repo.add_word(
                    user_id=db_user.id,
                    word_ua=word_data["ua"],
                    word_ru=word_data["ru"],
                    transcription=word_data.get("transcription"),
                    example_ua=word_data.get("example"),
                    category=word_data.get("category"),
                )
            logger.info("Seeded %d words for user %d", len(SEED_WORDS), db_user.id)

    await state.set_state(OnboardingStates.awaiting_first_voice)
    level_name = LEVEL_NAMES.get(level_key, level_key)
    level_emoji = LEVEL_EMOJIS.get(level_key, "🟢")
    await callback.message.edit_text(
        ONBOARDING_VOICE_PROMPT.format(level_emoji=level_emoji, level_name=level_name),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message, **kwargs) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML", reply_markup=main_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, **kwargs) -> None:
    await state.clear()
    await message.answer(MAIN_MENU_TEXT, parse_mode="HTML", reply_markup=main_menu_kb())


@router.message(F.text == "🏠 Меню")
async def reply_menu(message: Message, state: FSMContext, **kwargs) -> None:
    await state.clear()
    await message.answer(MAIN_MENU_TEXT, parse_mode="HTML", reply_markup=main_menu_kb())


@router.message(F.text == "📚 Словник")
async def reply_vocab(message: Message, state: FSMContext, db_user: User, **kwargs) -> None:
    from bot.handlers.vocabulary import show_vocab_main
    await show_vocab_main(message, state, db_user)


@router.message(F.text == "🎙 Вимова")
async def reply_pronunciation(message: Message, state: FSMContext, **kwargs) -> None:
    from bot.handlers.pronunciation import show_pronunciation_menu
    await show_pronunciation_menu(message, state)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, **kwargs) -> None:
    await state.clear()
    await message.answer(CANCEL_TEXT, parse_mode="HTML", reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:open")
async def on_main_menu(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(MAIN_MENU_TEXT, parse_mode="HTML", reply_markup=main_menu_kb())


@router.message(F.sticker | F.photo | F.video | F.document | F.animation)
async def on_unsupported(message: Message, **kwargs) -> None:
    await message.answer(UNSUPPORTED_CONTENT, parse_mode="HTML")


async def build_welcome_back(db_user: User) -> tuple[str, InlineKeyboardMarkup | None]:
    async with async_session() as session:
        vocab_repo = VocabularyRepository(session)
        due_count = len(await vocab_repo.get_words_for_review(db_user.id, limit=50))

    today = date.today()
    is_new_day = db_user.last_active_date != today

    if not is_new_day:
        return "", None

    if db_user.streak_days > 0 and db_user.last_active_date == today - timedelta(days=1):
        streak = db_user.streak_days + 1
        text = f"🔥 {streak} день поспіль!\n\n"
        if due_count > 0:
            text += f"📚 {due_count} слів чекають повторення"
    elif db_user.last_active_date and db_user.last_active_date < today - timedelta(days=1):
        text = "👋 З поверненням!\n\n"
        if due_count > 0:
            text += f"У тебе {due_count} слів на повторення — почнемо?"
        else:
            text += "Готовий продовжити?"
    else:
        return "", None

    kb = quick_review_kb(due_count) if due_count > 0 else None
    return text, kb
