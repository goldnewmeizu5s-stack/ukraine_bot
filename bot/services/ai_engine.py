import json
import logging
from typing import Optional
from openai import AsyncOpenAI
from bot.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """Ты — профессиональный преподаватель украинского языка для русскоговорящих студентов. \
Ты прекрасно знаешь оба языка и понимаешь типичные ошибки русскоговорящих. \
Уровень студента: {level}.

Ключевые принципы:
- Всегда показывай украинское слово + транскрипцию в квадратных скобках + русский перевод
- Акцентируй внимание на различиях между украинским и русским
- Используй мнемонические приёмы для запоминания
- Будь дружелюбным, поддерживающим, но точным
- Отвечай структурированно, используй эмодзи для наглядности
- При переводе всегда давай контекст использования"""


async def _chat(system: str, user_message: str, temperature: float = 0.7) -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=1500,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error("GPT request failed: %s", e)
        raise


async def translate_text(text: str, source_lang: str, target_lang: str, level: str = "beginner") -> str:
    system = SYSTEM_PROMPT.format(level=level)
    prompt = f"""Переведи следующий текст с {source_lang} на {target_lang}.
Формат ответа:
🔄 Перевод: [перевод]
📝 Транскрипция: [фонетическая транскрипция украинского текста]
💡 Примечание: [если есть важные нюансы — ложные друзья, разница в употреблении, etc.]
📚 Пример: [пример в контексте предложения]

Текст: {text}"""
    return await _chat(system, prompt)


async def detect_language_and_translate(text: str, level: str = "beginner") -> str:
    system = SYSTEM_PROMPT.format(level=level)
    prompt = f"""Определи язык текста (русский или украинский) и переведи на другой язык.
Формат ответа:
🔤 Определён язык: [язык]
🔄 Перевод: [перевод]
📝 Транскрипция: [фонетическая транскрипция украинского текста]
💡 Примечание: [если есть важные нюансы]
📚 Пример: [пример в контексте предложения]

Текст: {text}"""
    return await _chat(system, prompt)


async def generate_dialogue_reply(
    topic: str, history: list[dict], user_response: Optional[str], level: str = "beginner"
) -> str:
    system = SYSTEM_PROMPT.format(level=level)
    history_str = "\n".join(
        f"{m['role']}: {m.get('content_ua', '')} ({m.get('content_ru', '')})"
        for m in history
    )
    prompt = f"""Мы ведём учебный диалог на тему "{topic}". Уровень: {level}.
История диалога:
{history_str}

"""
    if user_response:
        prompt += f"""Студент ответил: "{user_response}"
Оцени ответ (правильность, грамматика, уместность) и продолжи диалог.

"""
    prompt += """Сгенерируй следующую реплику собеседника на украинском.
Формат:
ua: [реплика на украинском]
ru_hint: [подсказка перевода на русском, в скобках]
expected_response_hint: [подсказка, что примерно должен ответить студент]"""
    return await _chat(system, prompt)


async def evaluate_pronunciation(original_text: str, transcribed_text: str, level: str = "beginner") -> dict:
    system = SYSTEM_PROMPT.format(level=level)
    prompt = f"""Студент должен был произнести: "{original_text}"
Whisper распознал его речь как: "{transcribed_text}"
Язык распознавания: украинский.

Оцени произношение по шкале 1-10. Укажи конкретные ошибки и что нужно исправить.
Дай совет по улучшению произношения этих конкретных звуков.
Ответ СТРОГО в формате JSON:
{{
  "score": number,
  "errors": ["ошибка 1", "ошибка 2"],
  "tips": ["совет 1", "совет 2"],
  "encouragement": "мотивационная фраза"
}}"""
    result = await _chat(system, prompt, temperature=0.3)
    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse pronunciation evaluation as JSON: %s", result[:200])
        return {"score": 5, "errors": [], "tips": [], "encouragement": result[:200]}


async def generate_listening_exercise(level: str = "beginner", topic: Optional[str] = None) -> dict:
    system = SYSTEM_PROMPT.format(level=level)
    topic_str = topic or "любая бытовая"
    length = {"beginner": 2, "elementary": 3, "intermediate": 5}.get(level, 2)
    prompt = f"""Сгенерируй текст для аудирования на украинском языке.
Уровень: {level}
Тема: {topic_str}
Длина: {length} предложений.

Ответ СТРОГО в формате JSON:
{{
  "text_ua": "текст на украинском",
  "text_ru": "перевод на русский",
  "key_words": [{{"ua": "слово", "ru": "перевод"}}],
  "question_ua": "вопрос по содержанию на украинском",
  "question_ru": "этот же вопрос на русском",
  "answer": "правильный ответ"
}}"""
    result = await _chat(system, prompt, temperature=0.5)
    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse listening exercise as JSON: %s", result[:200])
        return {
            "text_ua": "Вибачте, сталася помилка.",
            "text_ru": "Извините, произошла ошибка.",
            "key_words": [],
            "question_ua": "",
            "question_ru": "",
            "answer": "",
        }


async def explain_grammar(topic: str, level: str = "beginner") -> str:
    system = SYSTEM_PROMPT.format(level=level)
    prompt = f"""Объясни грамматическую тему: "{topic}" для русскоговорящего студента уровня {level}.

Структура:
1. 📖 Правило — кратко и чётко
2. 🔍 Сравнение с русским — где похоже, где отличается
3. 📝 Примеры — 3-5 примеров с переводом
4. ⚠️ Типичные ошибки — что русскоговорящие делают не так
5. 🎯 Мини-упражнение — 3 задания на закрепление с ответами"""
    return await _chat(system, prompt)


async def check_grammar_answer(topic: str, exercise: str, user_answer: str, level: str = "beginner") -> str:
    system = SYSTEM_PROMPT.format(level=level)
    prompt = f"""Тема: "{topic}"
Упражнение: {exercise}
Ответ студента: {user_answer}

Проверь ответ. Если правильно — похвали. Если нет — объясни ошибку и дай правильный ответ.
Будь кратким и полезным."""
    return await _chat(system, prompt)


async def generate_pronunciation_task(level: str = "beginner", difficulty: str = "word") -> str:
    system = SYSTEM_PROMPT.format(level=level)
    difficulty_map = {
        "word": "простое украинское слово",
        "phrase": "короткую фразу на украинском (2-4 слова)",
        "sentence": "предложение на украинском (5-8 слов)",
        "tongue_twister": "украинскую скороговорку",
    }
    task_type = difficulty_map.get(difficulty, "простое украинское слово")
    prompt = f"""Дай {task_type} для тренировки произношения.
Формат:
🎯 Текст: [текст на украинском]
📝 Транскрипция: [фонетическая транскрипция]
🔄 Перевод: [перевод на русский]
💡 Совет: [совет по произношению]"""
    return await _chat(system, prompt)
