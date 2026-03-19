import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.db.base import init_db, close_db
from bot.utils.cache import init_cache
from bot.handlers import get_main_router
from bot.middlewares.user_middleware import UserMiddleware
from bot.middlewares.throttle import ThrottleMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    await init_db()
    await init_cache()
    me = await bot.get_me()
    logger.info("Bot started: @%s", me.username)


async def on_shutdown(bot: Bot) -> None:
    await close_db()
    logger.info("Bot stopped")


def create_dispatcher() -> Dispatcher:
    storage = MemoryStorage()

    if settings.REDIS_URL:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            storage = RedisStorage.from_url(settings.REDIS_URL)
            logger.info("Using Redis FSM storage")
        except Exception as e:
            logger.warning("Redis FSM storage unavailable, using memory: %s", e)

    dp = Dispatcher(storage=storage)

    dp.message.middleware(ThrottleMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    dp.include_router(get_main_router())

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return dp


async def main() -> None:
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()

    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
