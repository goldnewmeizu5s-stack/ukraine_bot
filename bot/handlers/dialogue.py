import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import DialogueRepository, ProgressRepository
from bot.services.ai_engine import generate_dialogue_reply
from bot.handlers.voice import send_voice_then_text, send_voice_only
from bot.handlers.states import DialogueStates
from bot.keyboards.inline import (
    dialogue_topics_kb, dialogue_hint_kb, dialogue_result_kb,
    back_to_menu_kb, first_dialogue_kb,
)
from bot.utils.constants import DIALOGUE_TOPICS, STATUS_PROCESSING, ERROR_GENERAL, safe

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:dialogue")
async def on_dialogue_mode(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    await state.set_state(DialogueStates.choosing_topic)

    async with async_session() as session:
        repo = DialogueRepository(session)
        has_dialogues = await repo.get_active_session(db_user.id)

    total_dialogues = sum(1 for _ in (db_user.dialogue_sessions or []))

    if total_dialogues == 0:
        await callback.message.edit_text(
            "💬 <b>Перший діалог!</b>\n\n"
            "Я скажу репліку — ти відповідай українською.\n"
            "Не страшно помилятися — я підкажу.\n"
            "Говори голосом або пиши текстом.\n\n"
            "Готовий?",
            parse_mode="HTML",
            reply_markup=dialogue_topics_kb(),
        )
    else:
        await callback.message.edit_text(
            "💬 <b>Діалог</b>\n\nОберіть ситуацію:",
            parse_mode="HTML",
            reply_markup=dialogue_topics_kb(),
        )


@router.callback_query(F.data.startswith("dlg:topic:"))
async def on_dialogue_topic(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    topic_key = callback.data.split(":")[2]
    topic_name = DIALOGUE_TOPICS.get(topic_key, topic_key)

    async with async_session() as session:
        repo = DialogueRepository(session)
        dialogue = await repo.create_session(db_user.id, topic_name)
        await state.update_data(
            dialogue_session_id=dialogue.id,
            dialogue_topic=topic_name,
            dialogue_turn=0,
        )

    await state.set_state(DialogueStates.awaiting_response)
    status_msg = await callback.message.edit_text(STATUS_PROCESSING, parse_mode="HTML")

    try:
        reply = await generate_dialogue_reply(
            topic=topic_name, history=[], user_response=None,
            level=db_user.language_level.value,
        )

        async with async_session() as session:
            repo = DialogueRepository(session)
            await repo.add_message(dialogue.id, "bot", reply, reply)

        ua_text = _extract_ua(reply)
        await status_msg.delete()

        text = (
            f"💬 <b>{safe(topic_name)}</b>\n\n"
            f"🗣 {reply}\n\n"
            f"🎙 Відповідай українською!"
        )
        await send_voice_then_text(
            callback.message, text, ua_text_for_tts=ua_text,
            reply_markup=dialogue_hint_kb(turn=1),
        )
        await state.update_data(dialogue_turn=1, last_bot_ua=ua_text or "")
    except Exception as e:
        logger.error("Dialogue generation failed: %s", e)
        await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML", reply_markup=dialogue_topics_kb())


async def handle_dialogue_response(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    session_id = data.get("dialogue_session_id")
    topic = data.get("dialogue_topic", "")
    turn = data.get("dialogue_turn", 1)

    if not session_id:
        await message.reply("Діалог не знайдено.", parse_mode="HTML", reply_markup=dialogue_topics_kb())
        await state.clear()
        return

    status_msg = await message.answer(STATUS_PROCESSING)

    try:
        async with async_session() as session:
            repo = DialogueRepository(session)
            dialogue = await repo.get_active_session(db_user.id)
            history = dialogue.messages_json if dialogue else []
            await repo.add_message(session_id, "user", text, text)

        reply = await generate_dialogue_reply(
            topic=topic, history=history, user_response=text,
            level=db_user.language_level.value,
        )

        async with async_session() as session:
            repo = DialogueRepository(session)
            await repo.add_message(session_id, "bot", reply, reply)

        await status_msg.delete()
        ua_text = _extract_ua(reply)
        new_turn = turn + 1

        await send_voice_then_text(
            message, reply, ua_text_for_tts=ua_text,
            reply_markup=dialogue_hint_kb(turn=new_turn),
        )
        await state.update_data(dialogue_turn=new_turn, last_bot_ua=ua_text or "")

    except Exception as e:
        logger.error("Dialogue response failed: %s", e)
        try:
            await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML")
        except Exception:
            await message.reply(ERROR_GENERAL, parse_mode="HTML")


@router.callback_query(F.data == "dlg:hint")
async def on_dialogue_hint(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    topic = data.get("dialogue_topic", "")
    async with async_session() as session:
        repo = DialogueRepository(session)
        dialogue = await repo.get_active_session(db_user.id)
        history = dialogue.messages_json if dialogue else []

    from bot.services.ai_engine import generate_dialogue_reply
    hint = await generate_dialogue_reply(
        topic=topic, history=history, user_response=None,
        level=db_user.language_level.value,
    )
    await callback.message.answer(f"💡 {hint}", parse_mode="HTML")


@router.callback_query(F.data == "dlg:repeat")
async def on_dialogue_repeat(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    ua = data.get("last_bot_ua", "")
    if ua:
        await send_voice_only(callback.message, ua)


@router.callback_query(F.data == "dlg:skip")
async def on_dialogue_skip(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    session_id = data.get("dialogue_session_id")
    topic = data.get("dialogue_topic", "")
    turn = data.get("dialogue_turn", 1)

    status_msg = await callback.message.answer(STATUS_PROCESSING)
    try:
        async with async_session() as session:
            repo = DialogueRepository(session)
            dialogue = await repo.get_active_session(db_user.id)
            history = dialogue.messages_json if dialogue else []

        reply = await generate_dialogue_reply(
            topic=topic, history=history, user_response="(пропущено)",
            level=db_user.language_level.value,
        )

        if session_id:
            async with async_session() as session:
                repo = DialogueRepository(session)
                await repo.add_message(session_id, "bot", reply, reply)

        await status_msg.delete()
        ua_text = _extract_ua(reply)
        new_turn = turn + 1
        await send_voice_then_text(
            callback.message, reply, ua_text_for_tts=ua_text,
            reply_markup=dialogue_hint_kb(turn=new_turn),
        )
        await state.update_data(dialogue_turn=new_turn, last_bot_ua=ua_text or "")
    except Exception as e:
        logger.error("Dialogue skip failed: %s", e)
        await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML")


@router.callback_query(F.data == "dlg:finish")
async def on_dialogue_finish(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    session_id = data.get("dialogue_session_id")
    turn = data.get("dialogue_turn", 0)

    if session_id:
        async with async_session() as session:
            repo = DialogueRepository(session)
            await repo.finish_session(session_id)
            progress_repo = ProgressRepository(session)
            await progress_repo.increment_dialogues(db_user.id)

    text = (
        f"💬 Діалог завершено!\n\n"
        f"🗣 {turn} реплік"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=dialogue_result_kb())
    await state.clear()


@router.callback_query(F.data == "dlg:restart")
async def on_dialogue_restart(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    data = await state.get_data()
    topic_key = None
    for k, v in DIALOGUE_TOPICS.items():
        if v == data.get("dialogue_topic"):
            topic_key = k
            break
    if topic_key:
        callback.data = f"dlg:topic:{topic_key}"
        await on_dialogue_topic(callback, state, db_user=db_user)
    else:
        await on_dialogue_mode(callback, state, db_user=db_user)


def _extract_ua(text: str) -> str | None:
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("ua:"):
            return stripped.split("ua:", 1)[-1].strip()
        if stripped.startswith("🗣"):
            content = stripped.split("🗣", 1)[-1].strip().strip("«»\"")
            if content:
                return content
    return None
