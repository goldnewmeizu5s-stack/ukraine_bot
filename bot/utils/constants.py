import random
from html import escape as _html_escape

MAX_VOICE_DURATION = 60
RATE_LIMIT_PER_MINUTE = 30
MAX_MSG_LEN = 4000

WELCOME_TEXT = (
    "🇺🇦 <b>Привіт!</b>\n\n"
    "Я допоможу тебе вивчити українську. "
    "Говори — я переведу, озвучу і навчу.\n\n"
    "Який у тебе рівень?"
)

ONBOARDING_VOICE_PROMPT = (
    "Чудово! Рівень: {level_emoji} {level_name}\n\n"
    "🎙 Скажи щось голосом — будь-що російською.\n"
    "Я переведу і озвучу українською."
)

ONBOARDING_TOUR = (
    "🎉 <b>Перший крок зроблено!</b>\n\n"
    "Що я вмію:\n\n"
    "📚 Словник — вчити слова з повторенням\n"
    "💬 Діалоги — говорити в ситуаціях\n"
    "🎙 Вимова — тренувати вимову\n"
    "👂 Слухати — розуміти на слух\n\n"
    "🎙 Просто записуй голосові — я завжди переведу."
)

HELP_TEXT = (
    "🇺🇦 <b>Бот для вивчення української</b>\n\n"
    "Команди:\n"
    "/start — почати спочатку\n"
    "/help — ця довідка\n"
    "/menu — головне меню\n"
    "/stats — мій прогрес\n"
    "/cancel — вийти з режиму\n\n"
    "Просто відправ голосове або текст!"
)

MAIN_MENU_TEXT = "🇺🇦 Що робимо?"
CANCEL_TEXT = "↩️ Вийшли з режиму."
UNSUPPORTED_CONTENT = "😊 Я поки що працюю тільки з голосом та текстом.\n\n🎙 Запиши голосове або напиши текст."

STATUS_LISTENING = "🎧 Слухаю..."
STATUS_PROCESSING = "🤔 Обробляю..."
STATUS_SPEAKING = "🔊 Озвучую..."

ERROR_GENERAL = "😔 Щось пішло не так. Спробуй ще раз."
ERROR_VOICE_TOO_LONG = f"⏱ Голосове занадто довге. Максимум {MAX_VOICE_DURATION} секунд."
ERROR_RATE_LIMIT = "⏳ Забагато повідомлень. Зачекай трохи."

DIALOGUE_TOPICS = {
    "cafe": "☕ В кав'ярні",
    "shop": "🛒 В магазині",
    "taxi": "🚕 В таксі",
    "greeting": "👋 Знайомство",
    "doctor": "🏥 У лікаря",
    "hotel": "🏨 В готелі",
    "phone": "📞 Телефонна розмова",
    "work": "💼 На роботі",
    "random": "🎲 Випадкова",
}

GRAMMAR_TOPICS = {
    "alphabet": "🔤 Абетка і звуки",
    "pronouns": "👤 Займенники",
    "gender": "📐 Рід іменників",
    "numbers": "🔢 Числівники",
    "verbs_present": "🏃 Дієслова: теп. час",
    "verbs_past": "🕐 Дієслова: мин. час",
    "prepositions": "📍 Прийменники",
    "questions": "❓ Питальні слова",
    "false_friends": "🔀 Фальшиві друзі UA/RU",
}

VOCABULARY_CATEGORIES = {
    "greetings": "👋 Привітання",
    "food": "🍽 Їжа",
    "transport": "🚌 Транспорт",
    "numbers": "🔢 Числа",
    "days_months": "📅 Дні і місяці",
    "phrases": "🗣 Розмовні фрази",
    "family": "👨‍👩‍👧‍👦 Сім'я",
    "body": "🧍 Тіло",
    "colors": "🎨 Кольори",
    "house": "🏠 Дім",
}

LEVEL_NAMES = {
    "beginner": "🟢 Початківець (A1)",
    "elementary": "🟡 Елементарний (A2)",
    "intermediate": "🟠 Середній (B1)",
}

LEVEL_EMOJIS = {
    "beginner": "🟢",
    "elementary": "🟡",
    "intermediate": "🟠",
}

LEVEL_SHORT = {
    "beginner": "З нуля",
    "elementary": "Розумію трохи",
    "intermediate": "Можу говорити",
}

PRONUNCIATION_DIFFICULTIES = {
    "word": "📗 Слова",
    "phrase": "📘 Фрази",
    "sentence": "📙 Речення",
    "tongue_twister": "📕 Скоромовки",
}

SCORE_EMOJIS = {
    10: "🏆", 9: "🏆", 8: "👏", 7: "👏",
    6: "👍", 5: "👍", 4: "💪", 3: "💪",
    2: "🌱", 1: "🌱",
}

CORRECT_PHRASES = [
    "Так!", "Вірно!", "Точно!", "Бездоганно!",
    "Саме так!", "Правильно!", "Чудово!", "Молодець!",
]

INCORRECT_PHRASES = [
    "Майже!", "Не зовсім.", "Спробуй ще.",
    "Близько!", "Ще трішки.", "Не цього разу.",
]

ACHIEVEMENTS = {
    "first_word": ("Перше слово", "1 слово в словнику"),
    "ten_words": ("Десятка", "10 слів"),
    "fifty_words": ("Півсотні", "50 слів"),
    "hundred_words": ("Сотня", "100 слів"),
    "polyglot": ("Поліглот", "500 слів"),
    "week_streak": ("Тиждень", "7 днів поспіль"),
    "month_streak": ("Місяць", "30 днів поспіль"),
    "voice_30": ("Говорун", "30 хв голосових"),
    "dialogues_10": ("Співрозмовник", "10 діалогів"),
    "first_dialogue": ("Перший діалог", "1 завершений діалог"),
    "pronunciation_10": ("Вимова 10", "оцінка 10 за вимову"),
}

_last_correct_idx = -1
_last_incorrect_idx = -1


def random_correct() -> str:
    global _last_correct_idx
    idx = _last_correct_idx
    while idx == _last_correct_idx:
        idx = random.randint(0, len(CORRECT_PHRASES) - 1)
    _last_correct_idx = idx
    return CORRECT_PHRASES[idx]


def random_incorrect() -> str:
    global _last_incorrect_idx
    idx = _last_incorrect_idx
    while idx == _last_incorrect_idx:
        idx = random.randint(0, len(INCORRECT_PHRASES) - 1)
    _last_incorrect_idx = idx
    return INCORRECT_PHRASES[idx]


def score_emoji(score: int) -> str:
    return SCORE_EMOJIS.get(max(1, min(10, score)), "👍")


def progress_bar(current: int, total: int) -> str:
    if total <= 0:
        return "░" * 8
    filled = round(current / total * 8)
    return "▓" * filled + "░" * (8 - filled)


def safe(text: str) -> str:
    return _html_escape(text)


def split_message(text: str, max_len: int = MAX_MSG_LEN) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_len:
            if current:
                parts.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para
    if current:
        parts.append(current.strip())
    return parts if parts else [text[:max_len]]
