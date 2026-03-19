import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.db.models import LanguageLevel, User
from bot.db.repositories import UserRepository, VocabularyRepository
from bot.db.base import async_session
from bot.keyboards.inline import main_menu_keyboard, level_keyboard
from bot.utils.constants import WELCOME_TEXT, LEVEL_SELECTED_TEXT, HELP_TEXT, CANCEL_TEXT, LEVEL_NAMES
from bot.handlers.states import SettingsStates
from scripts.seed_vocabulary import SEED_WORDS

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: User, **kwargs) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=level_keyboard())


@router.callback_query(F.data.startswith("level:"))
async def on_level_selected(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    level_key = callback.data.split(":")[1]
    try:
        level = LanguageLevel(level_key)
    except ValueError:
        await callback.answer("Неизвестный уровень")
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

    await state.clear()
    level_name = LEVEL_NAMES.get(level_key, level_key)
    await callback.message.edit_text(
        LEVEL_SELECTED_TEXT.format(level_name=level_name),
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message, **kwargs) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, **kwargs) -> None:
    await state.clear()
    await message.answer("📋 Главное меню:", reply_markup=main_menu_keyboard())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, **kwargs) -> None:
    await state.clear()
    await message.answer(CANCEL_TEXT, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "action:main_menu")
async def on_main_menu(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.clear()
    await callback.message.edit_text("📋 Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
