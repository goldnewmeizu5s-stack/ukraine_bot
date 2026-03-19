import enum
from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    BigInteger, Integer, String, Float, Date, DateTime,
    Enum, JSON, ForeignKey, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.db.base import Base


class LanguageLevel(str, enum.Enum):
    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel), default=LanguageLevel.BEGINNER
    )
    current_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    daily_goal: Mapped[int] = mapped_column(Integer, default=10)
    words_today: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_words_learned: Mapped[int] = mapped_column(Integer, default=0)
    total_voice_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    settings_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    vocabulary: Mapped[list["VocabularyWord"]] = relationship(back_populates="user", lazy="selectin")
    dialogue_sessions: Mapped[list["DialogueSession"]] = relationship(back_populates="user", lazy="selectin")
    progress: Mapped[list["LearningProgress"]] = relationship(back_populates="user", lazy="selectin")


class VocabularyWord(Base):
    __tablename__ = "vocabulary_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    word_ua: Mapped[str] = mapped_column(String(255))
    word_ru: Mapped[str] = mapped_column(String(255))
    transcription: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    example_ua: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comfort_level: Mapped[int] = mapped_column(Integer, default=0)
    times_seen: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    audio_cache_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="vocabulary")


class DialogueSession(Base):
    __tablename__ = "dialogue_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(255))
    messages_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="dialogue_sessions")


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date)
    words_learned: Mapped[int] = mapped_column(Integer, default=0)
    words_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    voice_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    listening_exercises: Mapped[int] = mapped_column(Integer, default=0)
    dialogues_completed: Mapped[int] = mapped_column(Integer, default=0)
    pronunciation_score_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="progress")
