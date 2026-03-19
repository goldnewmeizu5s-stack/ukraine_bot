import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import ProgressRepository
from bot.services.ai_engine import generate_listening_exercise
from bot.handlers.voice import send_voice_only
from bot.handlers.states import ListeningStates
from bot.keyboards.inline import (
    listening_mode_kb, listening_task_kb, listening_result_kb, back_to_menu_kb,
)
from bot.utils.constants import STATUS_PROCESSING, ERROR_GENERAL, safe

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:listening")
async def on_listening_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    await state.set_state(ListeningStates.choosing_mode)
    await callback.message.edit_text(
        "👂 <b>Аудіювання</b>\n\nЯк тренуємось?",
        parse_mode="HTML",
        reply_markup=listening_mode_kb(),
    )


@router.callback_query(F.data.startswith("list:mode:"))
async def on_listening_type(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    mode = callback.data.split(":")[2]
    await state.update_data(listening_mode=mode, listen_count=0)
    await _generate_exercise(callback.message, state, db_user, edit=True)


async def _generate_exercise(message: Message, state: FSMContext, db_user: User, edit: bool = False) -> None:
    data = await state.get_data()
    mode = data.get("listening_mode", "dictation")
    count = data.get("listen_count", 0) + 1

    if edit:
        status_msg = await message.edit_text(STATUS_PROCESSING, parse_mode="HTML")
    else:
        status_msg = await message.answer(STATUS_PROCESSING)

    try:
        exercise = await generate_listening_exercise(level=db_user.language_level.value)
        text_ua = exercise.get("text_ua", "")
        text_ru = exercise.get("text_ru", "")
        question_ru = exercise.get("question_ru", "")
        answer = exercise.get("answer", "")
        key_words = exercise.get("key_words", [])

        await state.update_data(
            listening_text_ua=text_ua,
            listening_text_ru=text_ru,
            listening_question_ru=question_ru,
            listening_answer=answer,
            listening_key_words=key_words,
            listen_count=count,
        )
        await state.set_state(ListeningStates.awaiting_answer)
        await status_msg.delete()

        await send_voice_only(message, text_ua)

        if mode == "dictation":
            text = f"👂  {count}\n\nНапиши або скажи що почув/ла."
        elif mode == "translate":
            text = f"👂  {count}\n\nПереклади на російську:"
        else:
            text = f"👂  {count}\n\n{safe(question_ru)}"

        await message.answer(text, parse_mode="HTML", reply_markup=listening_task_kb())

    except Exception as e:
        logger.error("Listening exercise generation failed: %s", e)
        await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML", reply_markup=back_to_menu_kb())


async def handle_listening_answer(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    text_ua = data.get("listening_text_ua", "")
    text_ru = data.get("listening_text_ru", "")
    answer = data.get("listening_answer", "")
    key_words = data.get("listening_key_words", [])
    mode = data.get("listening_mode", "dictation")

    user_answer = text.strip().lower()

    if mode == "dictation":
        original = text_ua.strip().lower()
        if user_answer == original:
            response = f"✅ <b>{safe(text_ua)}</b> → {safe(text_ru)}"
        elif _similar(user_answer, original):
            response = (
                f"👍 Майже!\n"
                f"Ти: <i>{safe(text)}</i>\n"
                f"✅ <b>{safe(text_ua)}</b>"
            )
        else:
            response = (
                f"❌ Спробуй ще!\n"
                f"✅ <b>{safe(text_ua)}</b> → {safe(text_ru)}"
            )
    else:
        response = (
            f"📝 Ти: <i>{safe(text)}</i>\n\n"
            f"✅ <b>{safe(text_ua)}</b>\n"
            f"→ {safe(text_ru)}\n"
        )
        if answer:
            response += f"\n✅ Відповідь: {safe(answer)}"

    if key_words:
        response += "\n\n📚 Ключові слова:"
        for kw in key_words[:5]:
            response += f"\n• <b>{safe(kw.get('ua', ''))}</b> → {safe(kw.get('ru', ''))}"

    async with async_session() as session:
        progress_repo = ProgressRepository(session)
        await progress_repo.increment_listening(db_user.id)

    await message.answer(response, parse_mode="HTML", reply_markup=listening_result_kb())


@router.callback_query(F.data == "list:repeat")
async def on_listen_repeat(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    text_ua = data.get("listening_text_ua", "")
    if text_ua:
        await send_voice_only(callback.message, text_ua)


@router.callback_query(F.data == "list:slow")
async def on_listen_slow(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    text_ua = data.get("listening_text_ua", "")
    if text_ua:
        await send_voice_only(callback.message, text_ua)


@router.callback_query(F.data == "list:next")
async def on_listen_next(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    await _generate_exercise(callback.message, state, db_user, edit=False)


def _similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    common = sum(1 for ca, cb in zip(a, b) if ca == cb)
    return common / max(len(a), len(b)) > 0.7
