import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import ProgressRepository
from bot.services.ai_engine import generate_listening_exercise
from bot.handlers.voice import send_voice_response
from bot.handlers.states import ListeningStates
from bot.keyboards.inline import listening_options_keyboard, back_to_menu_keyboard
from bot.utils.constants import PROCESSING_THINK

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "mode:listening")
async def on_listening_mode(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await state.set_state(ListeningStates.listening)
    status_msg = await callback.message.edit_text(PROCESSING_THINK)

    try:
        exercise = await generate_listening_exercise(level=db_user.language_level.value)
        text_ua = exercise.get("text_ua", "")
        text_ru = exercise.get("text_ru", "")
        question_ua = exercise.get("question_ua", "")
        question_ru = exercise.get("question_ru", "")
        answer = exercise.get("answer", "")
        key_words = exercise.get("key_words", [])

        await state.update_data(
            listening_text_ua=text_ua,
            listening_text_ru=text_ru,
            listening_question_ua=question_ua,
            listening_question_ru=question_ru,
            listening_answer=answer,
            listening_key_words=key_words,
        )
        await state.set_state(ListeningStates.awaiting_answer)

        await status_msg.delete()
        await send_voice_response(
            callback.message,
            f"👂 Аудирование\n\n🎧 Прослушайте и ответьте:\n\n❓ {question_ru}\n\n"
            "Отправьте ответ голосовым или текстом.",
            ua_text_for_tts=text_ua,
        )
    except Exception as e:
        logger.error("Listening exercise generation failed: %s", e)
        await status_msg.edit_text("😔 Ошибка генерации упражнения.",
                                   reply_markup=back_to_menu_keyboard())

    await callback.answer()


async def handle_listening_answer(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    text_ua = data.get("listening_text_ua", "")
    text_ru = data.get("listening_text_ru", "")
    answer = data.get("listening_answer", "")
    key_words = data.get("listening_key_words", [])

    response = f"📝 Ваш ответ: {text}\n\n"
    response += f"📖 Текст был:\n🇺🇦 {text_ua}\n🇷🇺 {text_ru}\n\n"
    response += f"✅ Правильный ответ: {answer}\n\n"

    if key_words:
        response += "📚 Ключевые слова:\n"
        for kw in key_words:
            response += f"  • {kw.get('ua', '')} — {kw.get('ru', '')}\n"

    async with async_session() as session:
        progress_repo = ProgressRepository(session)
        await progress_repo.increment_listening(db_user.id)

    await message.answer(response, reply_markup=listening_options_keyboard())


@router.callback_query(F.data == "listen:repeat")
async def on_listen_repeat(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    text_ua = data.get("listening_text_ua", "")
    if text_ua:
        await send_voice_response(callback.message, "🔄 Повторяю аудио...", ua_text_for_tts=text_ua)
    else:
        await callback.message.answer("Нет аудио для повторения.")
    await callback.answer()


@router.callback_query(F.data == "listen:show_text")
async def on_listen_show_text(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    text_ua = data.get("listening_text_ua", "")
    text_ru = data.get("listening_text_ru", "")
    await callback.message.answer(
        f"📖 Текст:\n\n🇺🇦 {text_ua}\n\n🇷🇺 {text_ru}",
        reply_markup=listening_options_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "listen:next")
async def on_listen_next(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await on_listening_mode(callback, state, db_user=db_user)
