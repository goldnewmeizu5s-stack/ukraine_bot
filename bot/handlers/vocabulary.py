import logging
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.db.models import User
from bot.db.base import async_session
from bot.db.repositories import VocabularyRepository, ProgressRepository
from bot.handlers.states import VocabularyStates
from bot.handlers.voice import send_voice_then_text, send_voice_only
from bot.keyboards.inline import (
    vocab_main_kb, vocab_categories_kb, vocab_train_kb,
    vocab_correct_kb, vocab_incorrect_kb, vocab_result_kb, back_to_menu_kb,
)
from bot.utils.constants import (
    STATUS_PROCESSING, safe, random_correct, random_incorrect, progress_bar,
)

logger = logging.getLogger(__name__)
router = Router()


async def show_vocab_main(message: Message, state: FSMContext, db_user: User) -> None:
    await state.set_state(VocabularyStates.browsing)
    async with async_session() as session:
        repo = VocabularyRepository(session)
        total = await repo.get_word_count(db_user.id)
        due_words = await repo.get_words_for_review(db_user.id, limit=50)
    due = len(due_words)

    text = f"📚 <b>Словник</b> — {total} слів\n\n"
    if due > 0:
        text += f"🎯 На повторення: <b>{due}</b>"
    else:
        text += "✅ Все повторено!"

    await message.answer(text, parse_mode="HTML", reply_markup=vocab_main_kb(due))


@router.callback_query(F.data == "menu:vocab")
async def on_vocab_mode(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    await state.set_state(VocabularyStates.browsing)
    async with async_session() as session:
        repo = VocabularyRepository(session)
        total = await repo.get_word_count(db_user.id)
        due_words = await repo.get_words_for_review(db_user.id, limit=50)
    due = len(due_words)

    text = f"📚 <b>Словник</b> — {total} слів\n\n"
    if due > 0:
        text += f"🎯 На повторення: <b>{due}</b>"
    else:
        text += "✅ Все повторено!"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=vocab_main_kb(due))


@router.callback_query(F.data == "vocab:my_words")
async def on_my_words(callback: CallbackQuery, db_user: User, **kwargs) -> None:
    await callback.answer()
    async with async_session() as session:
        repo = VocabularyRepository(session)
        words = await repo.get_user_words(db_user.id, limit=20)
        total = await repo.get_word_count(db_user.id)

    if not words:
        await callback.message.edit_text(
            "📚 Словник порожній\n\nДодай перші слова:",
            parse_mode="HTML",
            reply_markup=vocab_categories_kb(),
        )
        return

    text = f"📋 <b>Мої слова</b> ({total})\n\n"
    for w in words[:20]:
        bar = progress_bar(w.comfort_level, 5)
        text += f"<b>{safe(w.word_ua)}</b> → {safe(w.word_ru)} {bar}\n"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=vocab_main_kb())


@router.callback_query(F.data == "vocab:sets")
async def on_vocab_sets(callback: CallbackQuery, **kwargs) -> None:
    await callback.answer()
    await callback.message.edit_text("📦 Набори слів", parse_mode="HTML", reply_markup=vocab_categories_kb())


@router.callback_query(F.data.startswith("vocab:set:"))
async def on_category_selected(callback: CallbackQuery, db_user: User, **kwargs) -> None:
    await callback.answer()
    category = callback.data.split(":")[2]

    from scripts.seed_vocabulary import SEED_WORDS
    cat_words = [w for w in SEED_WORDS if w.get("category") == category]
    if not cat_words:
        await callback.message.edit_text("Набір порожній.", parse_mode="HTML", reply_markup=vocab_main_kb())
        return

    added = 0
    async with async_session() as session:
        repo = VocabularyRepository(session)
        for w in cat_words:
            existing = await repo.get_user_words(db_user.id, limit=1)
            word = await repo.add_word(
                user_id=db_user.id,
                word_ua=w["ua"],
                word_ru=w["ru"],
                transcription=w.get("transcription"),
                example_ua=w.get("example"),
                category=w.get("category"),
            )
            if word:
                added += 1

    from bot.keyboards.inline import vocab_main_kb
    text = f"📦 Додано: <b>{category}</b> — {len(cat_words)} слів\n\nПочнемо тренування?"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=vocab_main_kb())


@router.callback_query(F.data.in_({"vocab:srs", "vocab:train", "vocab:quick"}))
async def on_srs_review(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    await state.set_state(VocabularyStates.srs_review)

    is_quick = callback.data == "vocab:quick"
    limit = 5 if is_quick else 10

    async with async_session() as session:
        repo = VocabularyRepository(session)
        words = await repo.get_words_for_review(db_user.id, limit=limit)
        if not words:
            words = await repo.get_user_words(db_user.id, limit=limit)

    if not words:
        await callback.message.edit_text(
            "📚 Словник порожній. Додай слова з наборів!",
            parse_mode="HTML",
            reply_markup=vocab_categories_kb(),
        )
        return

    random.shuffle(words)
    word_ids = [w.id for w in words]
    word_data = {w.id: {"ua": w.word_ua, "ru": w.word_ru, "tr": w.transcription, "ex": w.example_ua, "cat": w.category, "cl": w.comfort_level} for w in words}

    await state.update_data(
        srs_word_ids=word_ids,
        srs_word_data=word_data,
        srs_index=0,
        srs_correct=0,
        srs_total=len(word_ids),
    )

    await _send_srs_card(callback.message, state, db_user, edit=True)


async def _send_srs_card(message: Message, state: FSMContext, db_user: User, edit: bool = False) -> None:
    data = await state.get_data()
    idx = data.get("srs_index", 0)
    word_ids = data.get("srs_word_ids", [])
    word_data = data.get("srs_word_data", {})
    total = data.get("srs_total", 0)

    if idx >= len(word_ids):
        correct = data.get("srs_correct", 0)
        text = (
            f"📚 Готово!\n\n"
            f"✅ {correct}/{total}\n\n"
            f"{random_correct() if correct > total // 2 else 'Продовжуй тренуватися!'}"
        )
        if edit:
            await message.edit_text(text, parse_mode="HTML", reply_markup=vocab_result_kb())
        else:
            await message.answer(text, parse_mode="HTML", reply_markup=vocab_result_kb())
        return

    wid = word_ids[idx]
    w = word_data.get(str(wid), word_data.get(wid, {}))
    word_ua = w.get("ua", "")

    await send_voice_only(message, word_ua)

    text = f"📚  {idx + 1}/{total}\n\n🔊 <b>{safe(word_ua)}</b>\n\nЯк перекласти?"
    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=vocab_train_kb())
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=vocab_train_kb())


@router.callback_query(F.data == "vocab:hint")
async def on_vocab_hint(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    idx = data.get("srs_index", 0)
    word_ids = data.get("srs_word_ids", [])
    word_data = data.get("srs_word_data", {})

    if idx < len(word_ids):
        wid = word_ids[idx]
        w = word_data.get(str(wid), word_data.get(wid, {}))
        word_ru = w.get("ru", "")
        cat = w.get("cat", "")
        first_letter = word_ru[0] if word_ru else "?"
        hint = f"💡 Перша буква: <b>{safe(first_letter)}...</b>"
        if cat:
            hint += f"\nКатегорія: {safe(cat)}"
        await callback.message.answer(hint, parse_mode="HTML")


@router.callback_query(F.data == "vocab:next")
async def on_vocab_next(callback: CallbackQuery, state: FSMContext, db_user: User, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    idx = data.get("srs_index", 0)
    await state.update_data(srs_index=idx + 1)
    await _send_srs_card(callback.message, state, db_user, edit=False)


@router.callback_query(F.data == "vocab:listen")
async def on_vocab_listen(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    await callback.answer()
    data = await state.get_data()
    idx = data.get("srs_index", 0)
    word_ids = data.get("srs_word_ids", [])
    word_data = data.get("srs_word_data", {})
    actual_idx = max(0, idx - 1)
    if actual_idx < len(word_ids):
        wid = word_ids[actual_idx]
        w = word_data.get(str(wid), word_data.get(wid, {}))
        await send_voice_only(callback.message, w.get("ua", ""))


async def handle_add_word_input(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    if "-" not in text:
        await message.reply(
            "Формат: <code>слово - переклад</code>",
            parse_mode="HTML",
        )
        return

    parts = text.split("-", 1)
    word_ua = parts[0].strip()
    word_ru = parts[1].strip()

    if not word_ua or not word_ru:
        await message.reply("Обидва слова мають бути вказані.", parse_mode="HTML")
        return

    async with async_session() as session:
        repo = VocabularyRepository(session)
        await repo.add_word(user_id=db_user.id, word_ua=word_ua, word_ru=word_ru)

    await message.reply(
        f"✅ <b>{safe(word_ua)}</b> → {safe(word_ru)}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )


async def handle_vocab_answer(message: Message, text: str, state: FSMContext, db_user: User) -> None:
    data = await state.get_data()
    idx = data.get("srs_index", 0)
    word_ids = data.get("srs_word_ids", [])
    word_data = data.get("srs_word_data", {})

    if idx >= len(word_ids):
        return

    wid = word_ids[idx]
    w = word_data.get(str(wid), word_data.get(wid, {}))
    word_ua = w.get("ua", "")
    word_ru = w.get("ru", "")
    example = w.get("ex", "")
    cl = w.get("cl", 0)

    user_answer = text.strip().lower()
    correct_answer = word_ru.strip().lower()
    is_correct = user_answer == correct_answer or user_answer in correct_answer.split("/")

    async with async_session() as session:
        repo = VocabularyRepository(session)
        await repo.update_word_progress(wid, is_correct)
        progress_repo = ProgressRepository(session)
        await progress_repo.increment_words_reviewed(db_user.id)

    if is_correct:
        new_cl = min(cl + 1, 5)
        bar = progress_bar(new_cl, 5)
        response = (
            f"✅  <b>{safe(word_ua)}</b> → {safe(word_ru)}\n\n"
        )
        if example:
            response += f"📝 {safe(example)}\n"
        response += f"{bar}"
        correct_count = data.get("srs_correct", 0) + 1
        await state.update_data(srs_correct=correct_count)
        await message.answer(response, parse_mode="HTML", reply_markup=vocab_correct_kb())
    else:
        new_cl = max(0, cl - 2)
        bar = progress_bar(new_cl, 5)
        response = (
            f"❌  <b>{safe(word_ua)}</b> → {safe(word_ru)}\n\n"
            f"Ти: <i>{safe(text)}</i>\n"
        )
        if example:
            response += f"\n📝 {safe(example)}"
        response += f"\n{bar}"
        await message.answer(response, parse_mode="HTML", reply_markup=vocab_incorrect_kb())
