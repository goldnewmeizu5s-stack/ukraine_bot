import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import DialogueRepository, ProgressRepository
from bot.services.ai_engine import generate_dialogue_reply
from bot.handlers.voice import send_voice_response
from bot.handlers.states import DialogueStates
from bot.keyboards.inline import (
    dialogue_topics_keyboard, continue_or_stop_keyboard, back_to_menu_keyboard,
)
from bot.utils.constants import DIALOGUE_TOPICS, PROCESSING_THINK

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "mode:dialogue")
async def on_dialogue_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.set_state(DialogueStates.choosing_topic)
    await callback.message.edit_text(
        "💬 Диалоговая практика\n\nВыберите тему диалога:",
        reply_markup=dialogue_topics_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dialogue:"))
async def on_dialogue_topic(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    topic_key = callback.data.split(":")[1]
    topic_name = DIALOGUE_TOPICS.get(topic_key, topic_key)

    async with async_session() as session:
        repo = DialogueRepository(session)
        dialogue = await repo.create_session(db_user.id, topic_name)
        await state.update_data(dialogue_session_id=dialogue.id, dialogue_topic=topic_name)

    await state.set_state(DialogueStates.awaiting_response)
    status_msg = await callback.message.edit_text(PROCESSING_THINK)

    try:
        reply = await generate_dialogue_reply(
            topic=topic_name,
            history=[],
            user_response=None,
            level=db_user.language_level.value,
        )

        async with async_session() as session:
            repo = DialogueRepository(session)
            await repo.add_message(dialogue.id, "bot", reply, reply)

        await status_msg.delete()
        ua_text = None
        for line in reply.split("\n"):
            if line.strip().startswith("ua:"):
                ua_text = line.split("ua:")[-1].strip()
                break

        await send_voice_response(
            callback.message,
            f"💬 Тема: {topic_name}\n\n{reply}\n\n🎙 Ответьте голосовым или текстом на украинском!",
            ua_text_for_tts=ua_text,
        )
    except Exception as e:
        logger.error("Dialogue generation failed: %s", e)
        await status_msg.edit_text("😔 Не удалось начать диалог. Попробуйте ещё раз.",
                                   reply_markup=dialogue_topics_keyboard())

    await callback.answer()


async def handle_dialogue_response(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    session_id = data.get("dialogue_session_id")
    topic = data.get("dialogue_topic", "")

    if not session_id:
        await message.reply("Диалог не найден. Начните новый.", reply_markup=dialogue_topics_keyboard())
        await state.clear()
        return

    status_msg = await message.answer(PROCESSING_THINK)

    try:
        async with async_session() as session:
            repo = DialogueRepository(session)
            dialogue = await repo.get_active_session(db_user.id)
            history = dialogue.messages_json if dialogue else []
            await repo.add_message(session_id, "user", text, text)

        reply = await generate_dialogue_reply(
            topic=topic,
            history=history,
            user_response=text,
            level=db_user.language_level.value,
        )

        async with async_session() as session:
            repo = DialogueRepository(session)
            await repo.add_message(session_id, "bot", reply, reply)

        await status_msg.delete()

        ua_text = None
        for line in reply.split("\n"):
            if line.strip().startswith("ua:"):
                ua_text = line.split("ua:")[-1].strip()
                break

        await send_voice_response(
            message,
            f"{reply}\n\n🎙 Продолжайте диалог или нажмите кнопку ниже.",
            ua_text_for_tts=ua_text,
        )
        await message.answer("Что дальше?", reply_markup=continue_or_stop_keyboard())

    except Exception as e:
        logger.error("Dialogue response failed: %s", e)
        await status_msg.edit_text("😔 Ошибка. Попробуйте ответить ещё раз.")


@router.callback_query(F.data == "action:stop")
async def on_dialogue_stop(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    data = await state.get_data()
    session_id = data.get("dialogue_session_id")

    if session_id:
        async with async_session() as session:
            repo = DialogueRepository(session)
            await repo.finish_session(session_id)
            progress_repo = ProgressRepository(session)
            await progress_repo.increment_dialogues(db_user.id)

    await state.clear()
    await callback.message.edit_text(
        "✅ Диалог завершён! Отличная практика!",
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "action:continue")
async def on_dialogue_continue(callback: CallbackQuery, **kwargs) -> None:
    await callback.message.edit_text("🎙 Продолжайте — отправьте голосовое или текст!")
    await callback.answer()
