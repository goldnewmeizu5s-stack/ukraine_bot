import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.services.ai_engine import explain_grammar, check_grammar_answer
from bot.handlers.states import GrammarStates
from bot.keyboards.inline import grammar_topics_keyboard, back_to_menu_keyboard
from bot.utils.constants import GRAMMAR_TOPICS, PROCESSING_THINK

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "mode:grammar")
async def on_grammar_mode(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await state.set_state(GrammarStates.choosing_topic)
    await callback.message.edit_text(
        "📖 Грамматика\n\nВыберите тему:",
        reply_markup=grammar_topics_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("grammar:"))
async def on_grammar_topic(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    topic_key = callback.data.split(":")[1]
    topic_name = GRAMMAR_TOPICS.get(topic_key, topic_key)

    await state.set_state(GrammarStates.studying)
    await state.update_data(grammar_topic=topic_name)

    status_msg = await callback.message.edit_text(PROCESSING_THINK)

    try:
        explanation = await explain_grammar(topic_name, level=db_user.language_level.value)
        await state.set_state(GrammarStates.exercising)
        await state.update_data(grammar_explanation=explanation)
        await status_msg.delete()
        await callback.message.answer(
            f"{explanation}\n\n✏️ Напишите ответ на упражнение или вернитесь в меню.",
            reply_markup=back_to_menu_keyboard(),
        )
    except Exception as e:
        logger.error("Grammar explanation failed: %s", e)
        await status_msg.edit_text("😔 Ошибка. Попробуйте другую тему.",
                                   reply_markup=grammar_topics_keyboard())

    await callback.answer()


async def handle_grammar_answer(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    topic = data.get("grammar_topic", "")
    explanation = data.get("grammar_explanation", "")

    status_msg = await message.answer(PROCESSING_THINK)

    try:
        result = await check_grammar_answer(
            topic=topic,
            exercise=explanation,
            user_answer=text,
            level=db_user.language_level.value,
        )
        await status_msg.delete()
        await message.answer(
            f"{result}\n\nВыберите другую тему или вернитесь в меню.",
            reply_markup=grammar_topics_keyboard(),
        )
        await state.set_state(GrammarStates.choosing_topic)
    except Exception as e:
        logger.error("Grammar answer check failed: %s", e)
        await status_msg.edit_text("😔 Ошибка проверки. Попробуйте ещё раз.")
