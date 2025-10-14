"""
Bot Initialization - ініціалізація бота та dispatcher
"""

import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Ініціалізація бота
bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

# Ініціалізація dispatcher
dp = Dispatcher()


async def setup_bot():
    """Налаштування бота перед запуском"""
    from app.database.mongodb import init_database
    from app.services.queue.rabbitmq import init_producers
    from app.services.ai.manager import init_ai_manager
    
    # Підключення до бази даних
    await init_database()
    logger.info("Database initialized")
    
    # Ініціалізація RabbitMQ producers
    await init_producers()
    logger.info("RabbitMQ producers initialized")
    
    # Ініціалізація AI Manager
    await init_ai_manager()
    logger.info("AI Manager initialized")
    
    # Реєстрація middlewares
    from app.middlewares.auth import AuthMiddleware
    from app.middlewares.logging import LoggingMiddleware, UserActionLogger
    from app.middlewares.throttling import ThrottlingMiddleware
    
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    
    dp.message.middleware(UserActionLogger())
    dp.callback_query.middleware(UserActionLogger())
    
    logger.info("Middlewares registered")
    
    # Реєстрація handlers
    from app.handlers.user import start, registration, generation
    
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(generation.router)
    
    logger.info("Handlers registered")


async def shutdown_bot():
    """Закриття з'єднань при зупинці бота"""
    from app.database.mongodb import close_database
    from app.services.queue.rabbitmq import close_connections
    
    await close_database()
    await close_connections()
    
    logger.info("Bot shutdown complete")