import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.services.ai_engine import detect_language_and_translate
from bot.handlers.voice import send_voice_response
from bot.handlers.states import TranslateStates
from bot.keyboards.inline import back_to_menu_keyboard
from bot.utils.constants import PROCESSING_TRANSLATE

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "mode:translate")
async def on_translate_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.set_state(TranslateStates.active)
    await callback.message.edit_text(
        "🔄 Режим переводчика\n\n"
        "Отправьте текст или голосовое сообщение на русском или украинском — я переведу!\n\n"
        "Автоопределение языка включено.",
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


async def handle_translate(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    status_msg = await message.answer(PROCESSING_TRANSLATE)
    try:
        result = await detect_language_and_translate(text, level=db_user.language_level.value)
        await status_msg.delete()

        ua_text = None
        for line in result.split("\n"):
            if "Перевод:" in line:
                ua_text = line.split("Перевод:")[-1].strip()
                break

        await send_voice_response(message, result, ua_text_for_tts=ua_text)
    except Exception as e:
        logger.error("Translation failed: %s", e)
        await status_msg.edit_text("😔 Не удалось перевести. Попробуйте ещё раз.")
