from aiogram import Router
from bot.handlers.start import router as start_router
from bot.handlers.voice import router as voice_router
from bot.handlers.text import router as text_router
from bot.handlers.translate import router as translate_router
from bot.handlers.vocabulary import router as vocabulary_router
from bot.handlers.dialogue import router as dialogue_router
from bot.handlers.pronunciation import router as pronunciation_router
from bot.handlers.listening import router as listening_router
from bot.handlers.grammar import router as grammar_router
from bot.handlers.settings import router as settings_router


def get_main_router() -> Router:
    main_router = Router()
    main_router.include_router(start_router)
    main_router.include_router(voice_router)
    main_router.include_router(translate_router)
    main_router.include_router(vocabulary_router)
    main_router.include_router(dialogue_router)
    main_router.include_router(pronunciation_router)
    main_router.include_router(listening_router)
    main_router.include_router(grammar_router)
    main_router.include_router(settings_router)
    main_router.include_router(text_router)
    return main_router
