from aiogram.fsm.state import StatesGroup, State


class TranslateStates(StatesGroup):
    active = State()


class VocabularyStates(StatesGroup):
    browsing = State()
    adding_word = State()
    training = State()
    srs_review = State()


class DialogueStates(StatesGroup):
    choosing_topic = State()
    awaiting_response = State()


class PronunciationStates(StatesGroup):
    choosing_difficulty = State()
    awaiting_repeat = State()


class ListeningStates(StatesGroup):
    listening = State()
    awaiting_answer = State()


class GrammarStates(StatesGroup):
    choosing_topic = State()
    studying = State()
    exercising = State()


class SettingsStates(StatesGroup):
    main = State()
    choosing_level = State()
    setting_goal = State()
