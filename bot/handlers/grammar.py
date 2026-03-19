import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.services.ai_engine import explain_grammar, check_grammar_answer
from bot.handlers.states import GrammarStates
from bot.keyboards.inline import grammar_topics_kb, grammar_lesson_kb, grammar_exercise_kb, back_to_menu_kb
from bot.utils.constants import GRAMMAR_TOPICS, STATUS_PROCESSING, ERROR_GENERAL, split_message

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:grammar")
async def on_grammar_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    await state.set_state(GrammarStates.choosing_topic)
    await callback.message.edit_text(
        "📖 <b>Граматика</b>",
        parse_mode="HTML",
        reply_markup=grammar_topics_kb(),
    )


@router.callback_query(F.data.startswith("gram:topic:"))
async def on_grammar_topic(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    topic_key = callback.data.split(":")[2]
    topic_name = GRAMMAR_TOPICS.get(topic_key, topic_key)

    await state.set_state(GrammarStates.studying)
    await state.update_data(grammar_topic=topic_name, grammar_topic_key=topic_key)

    status_msg = await callback.message.edit_text(STATUS_PROCESSING, parse_mode="HTML")

    try:
        explanation = await explain_grammar(topic_name, level=db_user.language_level.value)
        await state.set_state(GrammarStates.exercising)
        await state.update_data(grammar_explanation=explanation)
        await status_msg.delete()

        parts = split_message(explanation)
        for part in parts[:-1]:
            await callback.message.answer(part, parse_mode="HTML")
        await callback.message.answer(
            parts[-1],
            parse_mode="HTML",
            reply_markup=grammar_lesson_kb(),
        )
    except Exception as e:
        logger.error("Grammar explanation failed: %s", e)
        await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML", reply_markup=grammar_topics_kb())


@router.callback_query(F.data == "gram:exercise")
async def on_grammar_exercise(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    await state.set_state(GrammarStates.exercising)
    await callback.message.answer(
        "✏️ Напиши відповідь на вправу:",
        parse_mode="HTML",
        reply_markup=grammar_exercise_kb(),
    )


@router.callback_query(F.data == "gram:listen")
async def on_grammar_listen(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    explanation = data.get("grammar_explanation", "")
    examples = []
    for line in explanation.split("\n"):
        if line.strip().startswith("•") or line.strip().startswith("-"):
            ua_part = line.split("—")[0].strip().lstrip("•-").strip()
            if ua_part:
                examples.append(ua_part)
    if examples:
        from bot.handlers.voice import send_voice_only
        await send_voice_only(callback.message, ". ".join(examples[:5]))


async def handle_grammar_answer(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    topic = data.get("grammar_topic", "")
    explanation = data.get("grammar_explanation", "")

    status_msg = await message.answer(STATUS_PROCESSING)

    try:
        result = await check_grammar_answer(
            topic=topic,
            exercise=explanation,
            user_answer=text,
            level=db_user.language_level.value,
        )
        await status_msg.delete()
        await message.answer(
            result,
            parse_mode="HTML",
            reply_markup=grammar_topics_kb(),
        )
        await state.set_state(GrammarStates.choosing_topic)
    except Exception as e:
        logger.error("Grammar answer check failed: %s", e)
        try:
            await status_msg.edit_text(ERROR_GENERAL, parse_mode="HTML")
        except Exception:
            await message.reply(ERROR_GENERAL, parse_mode="HTML")
