import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import ProgressRepository
from bot.services.ai_engine import generate_pronunciation_task, evaluate_pronunciation
from bot.handlers.voice import send_voice_then_text, send_voice_only
from bot.handlers.states import PronunciationStates
from bot.keyboards.inline import (
    pronunciation_difficulty_kb, pronunciation_task_kb, pronunciation_result_kb,
    back_to_menu_kb,
)
from bot.utils.constants import STATUS_PROCESSING, ERROR_GENERAL, score_emoji, safe

logger = logging.getLogger(__name__)
router = Router()


async def show_pronunciation_menu(message: Message, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.choosing_difficulty)
    await message.answer(
        "🎙 <b>Вимова</b>\n\nОберіть рівень:",
        parse_mode="HTML",
        reply_markup=pronunciation_difficulty_kb(),
    )


@router.callback_query(F.data == "menu:pronunciation")
async def on_pronunciation_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    await state.set_state(PronunciationStates.choosing_difficulty)
    await callback.message.edit_text(
        "🎙 <b>Вимова</b>\n\nОберіть рівень:",
        parse_mode="HTML",
        reply_markup=pronunciation_difficulty_kb(),
    )


@router.callback_query(F.data.startswith("pron:level:"))
async def on_difficulty_selected(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    difficulty = callback.data.split(":")[2]
    await state.update_data(pronunciation_difficulty=difficulty, pron_count=0)
    await _generate_and_send_task(callback.message, state, db_user, edit=True)


async def _generate_and_send_task(message: Message, state: FSMContext, db_user: User, edit: bool = False) -> None:
    data = await state.get_data()
    difficulty = data.get("pronunciation_difficulty", "word")
    count = data.get("pron_count", 0) + 1

    if edit:
        status_msg = await message.edit_text(STATUS_PROCESSING, parse_mode="HTML")
    else:
        status_msg = await message.answer(STATUS_PROCESSING)

    try:
        task = await generate_pronunciation_task(
            level=db_user.language_level.value,
            difficulty=difficulty,
        )

        target_text = ""
        translation = ""
        for line in task.split("\n"):
            if "Текст:" in line:
                target_text = line.split("Текст:", 1)[-1].strip()
            elif "Перевод:" in line or "Переклад:" in line:
                translation = line.split(":", 1)[-1].strip()
        if not target_text:
            target_text = task.split("\n")[0].strip()

        await state.update_data(
            pronunciation_target=target_text,
            pronunciation_translation=translation,
            pron_count=count,
        )
        await state.set_state(PronunciationStates.awaiting_repeat)

        await status_msg.delete()

        await send_voice_only(message, target_text)

        text = (
            f"🎙  {count}\n\n"
            f"<b>{safe(target_text)}</b>\n"
            f"↳ <i>{safe(translation)}</i>\n\n"
            f"Повтори 🎙"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=pronunciation_task_kb())

    except Exception as e:
        logger.error("Pronunciation task generation failed: %s", e)
        await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML", reply_markup=pronunciation_difficulty_kb())


async def handle_pronunciation_check(message: Message, transcription: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    target = data.get("pronunciation_target", "")

    if not target:
        await message.reply(ERROR_GENERAL, parse_mode="HTML", reply_markup=pronunciation_difficulty_kb())
        await state.set_state(PronunciationStates.choosing_difficulty)
        return

    status_msg = await message.answer(STATUS_PROCESSING)

    try:
        result = await evaluate_pronunciation(target, transcription, level=db_user.language_level.value)

        score = result.get("score", 5)
        errors = result.get("errors", [])
        emoji = score_emoji(score)

        text = f"{emoji} <b>{score}/10</b>\n\n"
        text += f"Ти: «{safe(transcription)}»\n"

        if score < 7 and errors:
            text += f"\n🔍 {safe(errors[0])}"
        elif score >= 9:
            text += "\n🏆"

        async with async_session() as session:
            progress_repo = ProgressRepository(session)
            await progress_repo.update_pronunciation_score(db_user.id, float(score))

        await status_msg.delete()
        await message.answer(text, parse_mode="HTML", reply_markup=pronunciation_result_kb())

    except Exception as e:
        logger.error("Pronunciation evaluation failed: %s", e)
        try:
            await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML")
        except Exception:
            await message.reply(ERROR_GENERAL, parse_mode="HTML")


@router.callback_query(F.data == "pron:retry")
async def on_pronunciation_retry(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    target = data.get("pronunciation_target", "")
    translation = data.get("pronunciation_translation", "")
    count = data.get("pron_count", 1)

    if target:
        await state.set_state(PronunciationStates.awaiting_repeat)
        await send_voice_only(callback.message, target)
        text = (
            f"🎙  {count}\n\n"
            f"<b>{safe(target)}</b>\n"
            f"↳ <i>{safe(translation)}</i>\n\n"
            f"Повтори 🎙"
        )
        await callback.message.answer(text, parse_mode="HTML", reply_markup=pronunciation_task_kb())


@router.callback_query(F.data == "pron:listen")
async def on_pronunciation_listen(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    target = data.get("pronunciation_target", "")
    if target:
        await send_voice_only(callback.message, target)


@router.callback_query(F.data == "pron:next")
async def on_pronunciation_next(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    await _generate_and_send_task(callback.message, state, db_user, edit=False)
