import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.handlers.states import (
    DialogueStates, ListeningStates, VocabularyStates, GrammarStates,
)
from bot.utils.constants import ERROR_GENERAL

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, state: FSMContext, db_user: User, **kwargs) -> None:
    try:
        current_state = await state.get_state()
        text = message.text.strip()

        if current_state == VocabularyStates.adding_word.state:
            from bot.handlers.vocabulary import handle_add_word_input
            await handle_add_word_input(message, text, state, db_user)
        elif current_state == DialogueStates.awaiting_response.state:
            from bot.handlers.dialogue import handle_dialogue_response
            await handle_dialogue_response(message, text, state, db_user)
        elif current_state == ListeningStates.awaiting_answer.state:
            from bot.handlers.listening import handle_listening_answer
            await handle_listening_answer(message, text, state, db_user)
        elif current_state == GrammarStates.exercising.state:
            from bot.handlers.grammar import handle_grammar_answer
            await handle_grammar_answer(message, text, state, db_user)
        else:
            from bot.handlers.translate import handle_translate
            await handle_translate(message, text, state, db_user)
    except Exception as e:
        logger.error("Text processing failed: %s", e)
        await message.reply(ERROR_GENERAL)
