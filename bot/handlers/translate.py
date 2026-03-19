import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.services.ai_engine import detect_language_and_translate
from bot.handlers.voice import send_voice_then_text
from bot.handlers.states import TranslateStates
from bot.keyboards.inline import back_to_menu_kb, translate_save_kb, main_menu_kb
from bot.utils.constants import (
    STATUS_PROCESSING, ERROR_GENERAL, ONBOARDING_TOUR, safe,
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:translate")
async def on_translate_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    await state.set_state(TranslateStates.active)
    await callback.message.edit_text(
        "🔄 <b>Перекладач</b>\n\n"
        "Відправ текст або голосове — я переведу.\n"
        "Автовизначення мови.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )


async def handle_translate(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    status_msg = await message.answer(STATUS_PROCESSING)
    try:
        result = await detect_language_and_translate(text, level=db_user.language_level.value)
        await status_msg.delete()

        ua_text = _extract_ua_text(result)
        await state.update_data(last_ua_text=ua_text or "", last_ru_text=text)
        await send_voice_then_text(
            message,
            result,
            ua_text_for_tts=ua_text,
            reply_markup=translate_save_kb(),
        )
    except Exception as e:
        logger.error("Translation failed: %s", e)
        try:
            await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML")
        except Exception:
            await message.reply(ERROR_GENERAL, parse_mode="HTML")


async def handle_translate_onboarding(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    status_msg = await message.answer(STATUS_PROCESSING)
    try:
        result = await detect_language_and_translate(text, level=db_user.language_level.value)
        await status_msg.delete()

        ua_text = _extract_ua_text(result)
        await state.update_data(last_ua_text=ua_text or "", last_ru_text=text)
        await send_voice_then_text(message, result, ua_text_for_tts=ua_text)

        await state.clear()
        await message.answer(ONBOARDING_TOUR, parse_mode="HTML", reply_markup=main_menu_kb())
    except Exception as e:
        logger.error("Onboarding translation failed: %s", e)
        try:
            await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML")
        except Exception:
            await message.reply(ERROR_GENERAL, parse_mode="HTML")
        await state.clear()


@router.callback_query(F.data.startswith("tr:listen:"))
async def on_translate_listen(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    ua_text = data.get("last_ua_text", "")
    if ua_text:
        from bot.handlers.voice import send_voice_only
        await send_voice_only(callback.message, ua_text)


@router.callback_query(F.data.startswith("tr:save:"))
async def on_translate_save(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer("📚 Збережено!")
    data = await state.get_data()
    ua_text = data.get("last_ua_text", "")
    ru_text = data.get("last_ru_text", "")
    if ua_text and ru_text:
        from bot.db.base import async_session
        from bot.db.repositories import VocabularyRepository
        async with async_session() as session:
            repo = VocabularyRepository(session)
            await repo.add_word(user_id=db_user.id, word_ua=ua_text, word_ru=ru_text)


def _extract_ua_text(result: str) -> str | None:
    for line in result.split("\n"):
        if "Перевод:" in line or "Переклад:" in line:
            return line.split(":", 1)[-1].strip()
    return None
