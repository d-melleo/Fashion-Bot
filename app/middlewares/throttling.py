"""
Throttling Middleware - обмеження частоти запитів (Rate Limiting)
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.config.settings import settings

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для обмеження частоти запитів
    
    Використовує in-memory storage для зберігання часу останніх запитів
    """
    
    def __init__(
        self,
        rate_limit: int = None,
        period: int = None
    ):
        """
        Args:
            rate_limit: Максимальна кількість запитів за період
            period: Період в секундах
        """
        super().__init__()
        self.rate_limit = rate_limit or settings.RATE_LIMIT_REQUESTS
        self.period = period or settings.RATE_LIMIT_PERIOD
        
        # Словник для зберігання часу запитів: {user_id: [timestamp1, timestamp2, ...]}
        self.user_requests: Dict[int, list] = defaultdict(list)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Перевірка rate limit"""
        telegram_id = data.get('telegram_id')
        user_role = data.get('user_role', 'user')
        
        if not telegram_id:
            return await handler(event, data)
        
        # Адміністратори не обмежуються
        if user_role in ['supervisor', 'owner']:
            return await handler(event, data)
        
        # Очищаємо старі записи
        self._cleanup_old_requests(telegram_id)
        
        # Перевіряємо кількість запитів
        request_count = len(self.user_requests[telegram_id])
        
        if request_count >= self.rate_limit:
            # Перевищено ліміт
            logger.warning(
                f"Rate limit exceeded for user {telegram_id}",
                extra={
                    "user_id": telegram_id,
                    "request_count": request_count,
                    "rate_limit": self.rate_limit
                }
            )
            
            await self._send_rate_limit_message(event)
            return
        
        # Додаємо поточний запит
        self.user_requests[telegram_id].append(datetime.utcnow())
        
        return await handler(event, data)
    
    def _cleanup_old_requests(self, user_id: int):
        """Видалення старих запитів поза періодом"""
        if user_id not in self.user_requests:
            return
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.period)
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > cutoff_time
        ]
        
        # Видаляємо користувача якщо немає запитів
        if not self.user_requests[user_id]:
            del self.user_requests[user_id]
    
    async def _send_rate_limit_message(self, event: TelegramObject):
        """Відправити повідомлення про перевищення ліміту"""
        message_text = (
            "⏳ <b>Забагато запитів</b>\n\n"
            f"Ви відправили забагато запитів за короткий час.\n"
            f"Спробуйте знову через {self.period} секунд.\n\n"
            "Це обмеження захищає бота від перевантаження."
        )
        
        if isinstance(event, Message):
            await event.answer(message_text, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer(message_text, show_alert=True)


class CommandThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для обмеження частоти конкретних команд
    Корисно для дорогих операцій (AI генерація, платежі)
    """
    
    def __init__(self, command: str, cooldown: int = 10):
        """
        Args:
            command: Назва команди для обмеження
            cooldown: Час очікування між командами в секундах
        """
        super().__init__()
        self.command = command
        self.cooldown = cooldown
        
        # Словник часу останньої команди: {user_id: timestamp}
        self.last_command_time: Dict[int, datetime] = {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Перевірка cooldown для команди"""
        telegram_id = data.get('telegram_id')
        user_role = data.get('user_role', 'user')
        
        if not telegram_id:
            return await handler(event, data)
        
        # Адміністратори не обмежуються
        if user_role in ['supervisor', 'owner']:
            return await handler(event, data)
        
        # Перевіряємо час останньої команди
        if telegram_id in self.last_command_time:
            time_since_last = (datetime.utcnow() - self.last_command_time[telegram_id]).total_seconds()
            
            if time_since_last < self.cooldown:
                # Ще не минув cooldown
                remaining = int(self.cooldown - time_since_last)
                
                logger.info(
                    f"Command {self.command} on cooldown for user {telegram_id}",
                    extra={"remaining_seconds": remaining}
                )
                
                await self._send_cooldown_message(event, remaining)
                return
        
        # Оновлюємо час останньої команди
        self.last_command_time[telegram_id] = datetime.utcnow()
        
        return await handler(event, data)
    
    async def _send_cooldown_message(self, event: TelegramObject, remaining: int):
        """Відправити повідомлення про cooldown"""
        message_text = (
            f"⏰ <b>Зачекайте трохи</b>\n\n"
            f"Ця команда доступна раз на {self.cooldown} секунд.\n"
            f"Спробуйте знову через {remaining} секунд."
        )
        
        if isinstance(event, Message):
            await event.answer(message_text, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer(message_text, show_alert=True)


def rate_limit(limit: int = 10, period: int = 60):
    """
    Декоратор для обмеження частоти викликів функції
    
    Args:
        limit: Максимальна кількість викликів
        period: Період в секундах
        
    Example:
        @router.message(Command("spam"))
        @rate_limit(limit=5, period=60)
        async def spam_command(message: Message):
            pass
    """
    user_calls = defaultdict(list)
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Отримуємо telegram_id з аргументів
            telegram_id = None
            event = None
            
            for arg in args:
                if isinstance(arg, dict) and 'telegram_id' in arg:
                    telegram_id = arg['telegram_id']
                if isinstance(arg, (Message, CallbackQuery)):
                    event = arg
                    if hasattr(arg, 'from_user'):
                        telegram_id = arg.from_user.id
            
            if not telegram_id:
                return await func(*args, **kwargs)
            
            # Очищаємо старі записи
            cutoff_time = datetime.utcnow() - timedelta(seconds=period)
            user_calls[telegram_id] = [
                call_time for call_time in user_calls[telegram_id]
                if call_time > cutoff_time
            ]
            
            # Перевіряємо ліміт
            if len(user_calls[telegram_id]) >= limit:
                logger.warning(f"Rate limit exceeded in decorator for user {telegram_id}")
                
                if event:
                    message_text = (
                        f"⏳ Забагато запитів!\n"
                        f"Спробуйте через {period} секунд."
                    )
                    if isinstance(event, Message):
                        await event.answer(message_text)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(message_text, show_alert=True)
                return
            
            # Додаємо виклик
            user_calls[telegram_id].append(datetime.utcnow())
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator