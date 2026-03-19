import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import ProgressRepository
from bot.services.ai_engine import generate_pronunciation_task, evaluate_pronunciation
from bot.handlers.voice import send_voice_response
from bot.handlers.states import PronunciationStates
from bot.keyboards.inline import (
    pronunciation_difficulty_keyboard, continue_or_stop_keyboard, back_to_menu_keyboard,
)
from bot.utils.constants import PROCESSING_THINK

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "mode:pronunciation")
async def on_pronunciation_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.set_state(PronunciationStates.choosing_difficulty)
    await callback.message.edit_text(
        "🎙 Тренировка произношения\n\nВыберите сложность:",
        reply_markup=pronunciation_difficulty_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pronun:"))
async def on_difficulty_selected(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    difficulty = callback.data.split(":")[1]
    await state.update_data(pronunciation_difficulty=difficulty)

    status_msg = await callback.message.edit_text(PROCESSING_THINK)

    try:
        task = await generate_pronunciation_task(
            level=db_user.language_level.value,
            difficulty=difficulty,
        )

        target_text = ""
        for line in task.split("\n"):
            if "Текст:" in line:
                target_text = line.split("Текст:")[-1].strip()
                break
        if not target_text:
            target_text = task.split("\n")[0]

        await state.update_data(pronunciation_target=target_text)
        await state.set_state(PronunciationStates.awaiting_repeat)

        await status_msg.delete()
        await send_voice_response(
            callback.message,
            f"🎙 Повторите за мной:\n\n{task}\n\n🎤 Запишите голосовое сообщение!",
            ua_text_for_tts=target_text,
        )
    except Exception as e:
        logger.error("Pronunciation task generation failed: %s", e)
        await status_msg.edit_text("😔 Ошибка генерации задания.",
                                   reply_markup=pronunciation_difficulty_keyboard())

    await callback.answer()


async def handle_pronunciation_check(message: Message, transcription: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    target = data.get("pronunciation_target", "")
    difficulty = data.get("pronunciation_difficulty", "word")

    if not target:
        await message.reply("Ошибка: нет целевого текста.", reply_markup=pronunciation_difficulty_keyboard())
        await state.set_state(PronunciationStates.choosing_difficulty)
        return

    status_msg = await message.answer(PROCESSING_THINK)

    try:
        result = await evaluate_pronunciation(target, transcription, level=db_user.language_level.value)

        score = result.get("score", 5)
        errors = result.get("errors", [])
        tips = result.get("tips", [])
        encouragement = result.get("encouragement", "")

        score_bar = "🟢" * (score // 2) + "⚪" * (5 - score // 2)

        text = f"🎙 Оценка произношения: {score}/10 {score_bar}\n\n"
        text += f"🎯 Цель: {target}\n"
        text += f"🎤 Распознано: {transcription}\n\n"

        if errors:
            text += "❌ Ошибки:\n"
            for err in errors:
                text += f"  • {err}\n"
            text += "\n"

        if tips:
            text += "💡 Советы:\n"
            for tip in tips:
                text += f"  • {tip}\n"
            text += "\n"

        if encouragement:
            text += f"✨ {encouragement}"

        async with async_session() as session:
            progress_repo = ProgressRepository(session)
            await progress_repo.update_pronunciation_score(db_user.id, float(score))

        await status_msg.delete()
        await message.answer(text, reply_markup=continue_or_stop_keyboard())

    except Exception as e:
        logger.error("Pronunciation evaluation failed: %s", e)
        await status_msg.edit_text("😔 Ошибка оценки. Попробуйте ещё раз.")


@router.callback_query(F.data == "action:continue", PronunciationStates.awaiting_repeat)
async def on_pronunciation_continue(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    data = await state.get_data()
    difficulty = data.get("pronunciation_difficulty", "word")

    status_msg = await callback.message.edit_text(PROCESSING_THINK)
    try:
        task = await generate_pronunciation_task(
            level=db_user.language_level.value,
            difficulty=difficulty,
        )

        target_text = ""
        for line in task.split("\n"):
            if "Текст:" in line:
                target_text = line.split("Текст:")[-1].strip()
                break
        if not target_text:
            target_text = task.split("\n")[0]

        await state.update_data(pronunciation_target=target_text)
        await status_msg.delete()
        await send_voice_response(
            callback.message,
            f"🎙 Повторите за мной:\n\n{task}\n\n🎤 Запишите голосовое!",
            ua_text_for_tts=target_text,
        )
    except Exception as e:
        logger.error("Pronunciation continue failed: %s", e)
        await status_msg.edit_text("😔 Ошибка.", reply_markup=pronunciation_difficulty_keyboard())

    await callback.answer()
