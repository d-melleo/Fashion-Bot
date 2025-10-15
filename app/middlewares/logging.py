from typing import Any, Callable, Dict, Awaitable
import logging
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.utils.logger import get_logger, log_user_action

# Initialize logger
logger = get_logger(__name__, component="middleware")


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логування всіх вхідних повідомлень та callback queries"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Prepare common fields
        user_id = event.from_user.id if event.from_user else None
        username = event.from_user.username if event.from_user else None
        
        # Get event specific data
        if isinstance(event, Message):
            event_type = "message"
            content = event.text or event.caption or "[no text]"
        else:  # CallbackQuery
            event_type = "callback"
            content = event.data
            
        # Log the incoming event
        logger.info(
            f"Received {event_type}",
            user_id=user_id,
            username=username,
            content=content,
            chat_id=event.chat.id if hasattr(event, 'chat') else None,
            event_type=event_type
        )
        
        try:
            # Process the event
            start_time = datetime.now()
            result = await handler(event, data)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log successful processing
            logger.info(
                f"Processed {event_type}",
                user_id=user_id,
                processing_time=processing_time,
                success=True
            )
            return result
            
        except Exception as e:
            # Log error if processing failed
            logger.error(
                f"Failed to process {event_type}",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise


class UserActionLogger(BaseMiddleware):
    """Middleware для логування конкретних дій користувача"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return await handler(event, data)
            
        # Визначення типу дії користувача
        action = self._determine_action(event)
        if action:
            # Логуємо дію користувача
            log_user_action(
                user_id=user_id,
                action=action,
                username=event.from_user.username,
                chat_id=event.chat.id if hasattr(event, 'chat') else None
            )
            
        return await handler(event, data)
    
    def _determine_action(self, event: Message | CallbackQuery) -> str | None:
        """Визначає тип дії на основі події"""
        if isinstance(event, Message):
            if event.text:
                if event.text.startswith('/start'):
                    return "bot_start"
                elif event.text.startswith('/register'):
                    return "registration_start"
                elif event.text.startswith('/generate'):
                    return "generation_start"
            # Логуємо завантаження фото
            if event.photo:
                return "photo_upload"
                
        elif isinstance(event, CallbackQuery):
            # Розбір callback data для визначення дії
            callback_data = event.data
            if callback_data.startswith('register'):
                return "registration_step"
            elif callback_data.startswith('generate'):
                return "generation_process"
            elif callback_data.startswith('outfit'):
                return "outfit_interaction"
                
        return None