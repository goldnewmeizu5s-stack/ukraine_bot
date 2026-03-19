import logging
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from bot.db.base import async_session
from bot.db.repositories import UserRepository

logger = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            tg_user = event.from_user
        else:
            return await handler(event, data)

        async with async_session() as session:
            repo = UserRepository(session)
            user = await repo.get_or_create(
                user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
            )
            data["db_session"] = session
            data["db_user"] = user
            data["user_repo"] = repo
            return await handler(event, data)
