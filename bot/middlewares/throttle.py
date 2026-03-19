import logging
import time
from collections import defaultdict
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from bot.utils.constants import RATE_LIMIT_PER_MINUTE, ERROR_RATE_LIMIT

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self):
        self._user_timestamps: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()
        window_start = now - 60

        self._user_timestamps[user_id] = [
            ts for ts in self._user_timestamps[user_id] if ts > window_start
        ]

        if len(self._user_timestamps[user_id]) >= RATE_LIMIT_PER_MINUTE:
            logger.warning("Rate limit hit for user %d", user_id)
            await event.reply(ERROR_RATE_LIMIT)
            return None

        self._user_timestamps[user_id].append(now)
        return await handler(event, data)
