from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: str
    ELEVENLABS_API_KEY: str
    ELEVENLABS_VOICE_ID: str = "EXAVITQu4vr4xnSDxMaL"
    DATABASE_URL: str
    REDIS_URL: Optional[str] = None
    ADMIN_USER_IDS: str = ""

    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_USER_IDS:
            return []
        return [int(uid.strip()) for uid in self.ADMIN_USER_IDS.split(",") if uid.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
