import logging
import io
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.services.whisper import transcribe_voice
from bot.services.audio import ogg_to_wav, save_temp_ogg, cleanup_temp, mp3_to_ogg
from bot.services.tts import synthesize_ukrainian
from bot.handlers.states import (
    PronunciationStates, ListeningStates, DialogueStates, OnboardingStates,
)
from bot.utils.constants import (
    STATUS_LISTENING, STATUS_PROCESSING, STATUS_SPEAKING,
    ERROR_GENERAL, ERROR_VOICE_TOO_LONG, MAX_VOICE_DURATION, safe,
)

logger = logging.getLogger(__name__)
router = Router()


async def send_voice_only(message: Message, tts_text: str) -> None:
    if not tts_text or len(tts_text) > 2000:
        logger.warning("TTS skipped: text empty or too long (%d chars)", len(tts_text) if tts_text else 0)
        return
    ogg_path = None
    try:
        mp3_bytes = await synthesize_ukrainian(tts_text)
        ogg_path = await mp3_to_ogg(mp3_bytes)
        await message.answer_voice(FSInputFile(ogg_path))
    except Exception as e:
        logger.error("TTS send failed: %s", e, exc_info=True)
        await message.answer("⚠️ Не вдалося озвучити. Спробуйте пізніше.")
    finally:
        if ogg_path:
            cleanup_temp(ogg_path)


async def send_voice_then_text(
    message: Message,
    text_response: str,
    ua_text_for_tts: str | None = None,
    reply_markup=None,
) -> None:
    tts_text = ua_text_for_tts or text_response
    if tts_text and len(tts_text) <= 2000:
        ogg_path = None
        try:
            mp3_bytes = await synthesize_ukrainian(tts_text)
            ogg_path = await mp3_to_ogg(mp3_bytes)
            await message.answer_voice(FSInputFile(ogg_path))
        except Exception as e:
            logger.error("TTS failed for text '%s...': %s", tts_text[:50], e, exc_info=True)
        finally:
            if ogg_path:
                cleanup_temp(ogg_path)

    await message.answer(text_response, parse_mode="HTML", reply_markup=reply_markup)


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext, db_user: User, **kwargs) -> None:
    if message.voice.duration and message.voice.duration > MAX_VOICE_DURATION:
        await message.reply(ERROR_VOICE_TOO_LONG, parse_mode="HTML")
        return

    ogg_path = None
    wav_path = None
    try:
        status_msg = await message.answer(STATUS_LISTENING)
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

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
        preview = safe(transcription[:50])
        dots = "..." if len(transcription) > 50 else ""
        await status_msg.edit_text(f"✏️ <i>{preview}{dots}</i>\n\n{STATUS_PROCESSING}", parse_mode="HTML")

        voice_minutes = (message.voice.duration or 0) / 60.0
        from bot.db.base import async_session
        from bot.db.repositories import UserRepository
        async with async_session() as session:
            repo = UserRepository(session)
            await repo.update_activity(db_user.id, voice_minutes=voice_minutes)

        if current_state == OnboardingStates.awaiting_first_voice.state:
            await status_msg.delete()
            from bot.handlers.translate import handle_translate_onboarding
            await handle_translate_onboarding(message, transcription, state, db_user)
        elif current_state == DialogueStates.awaiting_response.state:
            await status_msg.delete()
            from bot.handlers.dialogue import handle_dialogue_response
            await handle_dialogue_response(message, transcription, state, db_user)
        elif current_state == PronunciationStates.awaiting_repeat.state:
            await status_msg.delete()
            from bot.handlers.pronunciation import handle_pronunciation_check
            await handle_pronunciation_check(message, transcription, state, db_user)
        elif current_state == ListeningStates.awaiting_answer.state:
            await status_msg.delete()
            from bot.handlers.listening import handle_listening_answer
            await handle_listening_answer(message, transcription, state, db_user)
        else:
            await status_msg.delete()
            from bot.handlers.translate import handle_translate
            await handle_translate(message, transcription, state, db_user)

    except Exception as e:
        logger.error("Voice processing failed: %s", e)
        await message.reply(ERROR_GENERAL, parse_mode="HTML")
    finally:
        cleanup_temp(ogg_path, wav_path)
