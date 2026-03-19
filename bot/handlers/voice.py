import logging
import io
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.services.whisper import transcribe_voice
from bot.services.audio import ogg_to_wav, save_temp_ogg, cleanup_temp
from bot.services.elevenlabs import synthesize_ukrainian
from bot.services.audio import mp3_to_ogg
from bot.handlers.states import (
    PronunciationStates, ListeningStates, DialogueStates, TranslateStates,
)
from bot.utils.constants import (
    PROCESSING_TRANSCRIBE, ERROR_GENERAL, ERROR_VOICE_TOO_LONG, MAX_VOICE_DURATION,
)

logger = logging.getLogger(__name__)
router = Router()


async def send_voice_response(message: Message, text_response: str, ua_text_for_tts: str | None = None) -> None:
    await message.answer(text_response)
    tts_text = ua_text_for_tts or text_response
    if len(tts_text) > 2000:
        return
    try:
        mp3_bytes = await synthesize_ukrainian(tts_text)
        ogg_path = await mp3_to_ogg(mp3_bytes)
        try:
            voice_file = FSInputFile(ogg_path)
            await message.answer_voice(voice_file)
        finally:
            cleanup_temp(ogg_path)
    except Exception as e:
        logger.error("TTS or voice send failed: %s", e)


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext, db_user: User, **kwargs) -> None:
    if message.voice.duration and message.voice.duration > MAX_VOICE_DURATION:
        await message.reply(ERROR_VOICE_TOO_LONG)
        return

    ogg_path = None
    wav_path = None
    try:
        status_msg = await message.reply(PROCESSING_TRANSCRIBE)

        file = await message.bot.get_file(message.voice.file_id)
        file_data = io.BytesIO()
        await message.bot.download_file(file.file_path, file_data)
        file_data.seek(0)

        ogg_path = save_temp_ogg(file_data.read())
        wav_path = await ogg_to_wav(ogg_path)

        current_state = await state.get_state()
        whisper_lang = "uk" if current_state in (
            PronunciationStates.awaiting_repeat.state,
            ListeningStates.awaiting_answer.state,
            DialogueStates.awaiting_response.state,
        ) else "ru"

        transcription = await transcribe_voice(wav_path, language=whisper_lang)
        await status_msg.edit_text(f"🎙 Распознано: {transcription}")

        voice_minutes = (message.voice.duration or 0) / 60.0
        from bot.db.base import async_session
        from bot.db.repositories import UserRepository
        async with async_session() as session:
            repo = UserRepository(session)
            await repo.update_activity(db_user.id, voice_minutes=voice_minutes)

        if current_state == DialogueStates.awaiting_response.state:
            from bot.handlers.dialogue import handle_dialogue_response
            await handle_dialogue_response(message, transcription, state, db_user)
        elif current_state == PronunciationStates.awaiting_repeat.state:
            from bot.handlers.pronunciation import handle_pronunciation_check
            await handle_pronunciation_check(message, transcription, state, db_user)
        elif current_state == ListeningStates.awaiting_answer.state:
            from bot.handlers.listening import handle_listening_answer
            await handle_listening_answer(message, transcription, state, db_user)
        else:
            from bot.handlers.translate import handle_translate
            await handle_translate(message, transcription, state, db_user)

    except Exception as e:
        logger.error("Voice processing failed: %s", e)
        await message.reply(ERROR_GENERAL)
    finally:
        cleanup_temp(ogg_path, wav_path)
