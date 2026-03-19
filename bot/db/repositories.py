import logging
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.models import User, VocabularyWord, DialogueSession, LearningProgress, LanguageLevel

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(
        self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None
    ) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(id=user_id, username=username, first_name=first_name)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            logger.info("New user created: %d", user_id)
        return user

    async def get(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_level(self, user_id: int, level: LanguageLevel) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(language_level=level, updated_at=datetime.utcnow())
        )
        await self.session.commit()

    async def update_mode(self, user_id: int, mode: Optional[str]) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(current_mode=mode, updated_at=datetime.utcnow())
        )
        await self.session.commit()

    async def update_activity(self, user_id: int, voice_minutes: float = 0.0) -> None:
        user = await self.get(user_id)
        if not user:
            return
        today = date.today()
        if user.last_active_date == today:
            streak = user.streak_days
        elif user.last_active_date == today - timedelta(days=1):
            streak = user.streak_days + 1
        else:
            streak = 1
        await self.session.execute(
            update(User).where(User.id == user_id).values(
                last_active_date=today,
                streak_days=streak,
                total_voice_minutes=User.total_voice_minutes + voice_minutes,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.commit()

    async def increment_words_today(self, user_id: int) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(
                words_today=User.words_today + 1,
                total_words_learned=User.total_words_learned + 1,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.commit()


class VocabularyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_word(
        self,
        user_id: int,
        word_ua: str,
        word_ru: str,
        transcription: Optional[str] = None,
        example_ua: Optional[str] = None,
        category: Optional[str] = None,
    ) -> VocabularyWord:
        existing = await self.session.execute(
            select(VocabularyWord).where(
                VocabularyWord.user_id == user_id,
                VocabularyWord.word_ua == word_ua,
            )
        )
        if existing.scalar_one_or_none():
            return existing.scalar_one_or_none()
        word = VocabularyWord(
            user_id=user_id,
            word_ua=word_ua,
            word_ru=word_ru,
            transcription=transcription,
            example_ua=example_ua,
            category=category,
            next_review_at=datetime.utcnow(),
        )
        self.session.add(word)
        await self.session.commit()
        await self.session.refresh(word)
        return word

    async def get_user_words(
        self, user_id: int, category: Optional[str] = None, limit: int = 50
    ) -> list[VocabularyWord]:
        query = select(VocabularyWord).where(VocabularyWord.user_id == user_id)
        if category:
            query = query.where(VocabularyWord.category == category)
        query = query.order_by(VocabularyWord.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_words_for_review(self, user_id: int, limit: int = 10) -> list[VocabularyWord]:
        now = datetime.utcnow()
        result = await self.session.execute(
            select(VocabularyWord)
            .where(
                VocabularyWord.user_id == user_id,
                VocabularyWord.next_review_at <= now,
            )
            .order_by(VocabularyWord.comfort_level.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_word_progress(self, word_id: int, correct: bool) -> None:
        result = await self.session.execute(
            select(VocabularyWord).where(VocabularyWord.id == word_id)
        )
        word = result.scalar_one_or_none()
        if not word:
            return

        intervals = [60, 600, 86400, 259200, 604800, 1209600, 2592000]
        word.times_seen += 1
        if correct:
            word.times_correct += 1
            word.comfort_level = min(word.comfort_level + 1, 6)
        else:
            word.comfort_level = max(0, word.comfort_level - 2)

        interval_seconds = intervals[min(word.comfort_level, len(intervals) - 1)]
        word.next_review_at = datetime.utcnow() + timedelta(seconds=interval_seconds)
        await self.session.commit()

    async def get_word_count(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(VocabularyWord.id)).where(VocabularyWord.user_id == user_id)
        )
        return result.scalar() or 0

    async def get_categories(self, user_id: int) -> list[str]:
        result = await self.session.execute(
            select(VocabularyWord.category)
            .where(VocabularyWord.user_id == user_id, VocabularyWord.category.isnot(None))
            .distinct()
        )
        return [row[0] for row in result.all()]


class DialogueRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, user_id: int, topic: str) -> DialogueSession:
        dialogue = DialogueSession(user_id=user_id, topic=topic, messages_json=[])
        self.session.add(dialogue)
        await self.session.commit()
        await self.session.refresh(dialogue)
        return dialogue

    async def get_active_session(self, user_id: int) -> Optional[DialogueSession]:
        result = await self.session.execute(
            select(DialogueSession)
            .where(DialogueSession.user_id == user_id, DialogueSession.finished_at.is_(None))
            .order_by(DialogueSession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def add_message(self, session_id: int, role: str, content_ru: str, content_ua: str) -> None:
        result = await self.session.execute(
            select(DialogueSession).where(DialogueSession.id == session_id)
        )
        dialogue = result.scalar_one_or_none()
        if not dialogue:
            return
        messages = list(dialogue.messages_json or [])
        messages.append({"role": role, "content_ru": content_ru, "content_ua": content_ua})
        dialogue.messages_json = messages
        await self.session.commit()

    async def finish_session(self, session_id: int, score: Optional[int] = None) -> None:
        await self.session.execute(
            update(DialogueSession)
            .where(DialogueSession.id == session_id)
            .values(finished_at=datetime.utcnow(), score=score)
        )
        await self.session.commit()


class ProgressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_today(self, user_id: int) -> LearningProgress:
        today = date.today()
        result = await self.session.execute(
            select(LearningProgress).where(
                LearningProgress.user_id == user_id,
                LearningProgress.date == today,
            )
        )
        progress = result.scalar_one_or_none()
        if not progress:
            progress = LearningProgress(user_id=user_id, date=today)
            self.session.add(progress)
            await self.session.commit()
            await self.session.refresh(progress)
        return progress

    async def increment_words_learned(self, user_id: int) -> None:
        progress = await self.get_or_create_today(user_id)
        progress.words_learned += 1
        await self.session.commit()

    async def increment_words_reviewed(self, user_id: int) -> None:
        progress = await self.get_or_create_today(user_id)
        progress.words_reviewed += 1
        await self.session.commit()

    async def add_voice_minutes(self, user_id: int, minutes: float) -> None:
        progress = await self.get_or_create_today(user_id)
        progress.voice_minutes += minutes
        await self.session.commit()

    async def increment_dialogues(self, user_id: int) -> None:
        progress = await self.get_or_create_today(user_id)
        progress.dialogues_completed += 1
        await self.session.commit()

    async def increment_listening(self, user_id: int) -> None:
        progress = await self.get_or_create_today(user_id)
        progress.listening_exercises += 1
        await self.session.commit()

    async def update_pronunciation_score(self, user_id: int, score: float) -> None:
        progress = await self.get_or_create_today(user_id)
        if progress.pronunciation_score_avg is None:
            progress.pronunciation_score_avg = score
        else:
            progress.pronunciation_score_avg = (progress.pronunciation_score_avg + score) / 2
        await self.session.commit()

    async def get_weekly_stats(self, user_id: int) -> list[LearningProgress]:
        week_ago = date.today() - timedelta(days=7)
        result = await self.session.execute(
            select(LearningProgress)
            .where(LearningProgress.user_id == user_id, LearningProgress.date >= week_ago)
            .order_by(LearningProgress.date.desc())
        )
        return list(result.scalars().all())
