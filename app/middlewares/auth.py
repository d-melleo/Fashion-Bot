"""
Authorization Middleware - перевірка ролей та доступу
"""

import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.database.mongodb import get_user, create_user, update_user_activity

logger = logging.getLogger(__name__)


# Права доступу для різних ролей
ROLE_PERMISSIONS = {
    'user': [
        'start', 'menu', 'help', 'profile', 'generate', 
        'history', 'subscription', 'subscribe', 'request_stylist', 'webapp'
    ],
    'stylist': [
        'start', 'menu', 'help', 'profile', 'generate', 
        'history', 'subscription', 'subscribe', 'request_stylist', 'webapp',
        'stylist_requests', 'my_chats', 'view_client'
    ],
    'supervisor': [
        'start', 'menu', 'help', 'profile', 'generate', 
        'history', 'subscription', 'subscribe', 'request_stylist', 'webapp',
        'stylist_requests', 'my_chats', 'view_client',
        'add_stylist', 'remove_stylist', 'list_stylists',
        'statistics', 'block_user', 'unblock_user'
    ],
    'owner': [
        '*'  # Повний доступ
    ]
}


class AuthMiddleware(BaseMiddleware):
    """Middleware для авторизації та перевірки доступу"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Перевірка авторизації користувача
        
        Args:
            handler: Наступний handler
            event: Telegram event
            data: Дані контексту
            
        Returns:
            Результат виконання handler
        """
        user: User = data.get("event_from_user")
        
        if not user:
            return await handler(event, data)
        
        telegram_id = user.id
        
        # Отримуємо або створюємо користувача
        db_user = await get_user(telegram_id)
        
        if not db_user:
            # Створюємо нового користувача
            db_user = await create_user(
                telegram_id=telegram_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            logger.info(f"New user registered: {telegram_id}")
        else:
            # Оновлюємо активність
            await update_user_activity(telegram_id)
        
        # Перевірка чи користувач заблокований
        if db_user.get('is_blocked', False):
            logger.warning(f"Blocked user tried to access bot: {telegram_id}")
            
            if hasattr(event, 'answer'):
                await event.answer(
                    "⛔ Ваш обліковий запис заблоковано.\n"
                    "Для отримання додаткової інформації зверніться до підтримки."
                )
            return
        
        # Додаємо дані користувача в контекст
        data['db_user'] = db_user
        data['user_role'] = db_user.get('role', 'user')
        data['telegram_id'] = telegram_id
        
        return await handler(event, data)


class RoleCheckMiddleware(BaseMiddleware):
    """Middleware для перевірки прав доступу на основі ролі"""
    
    def __init__(self, required_role: str = None, required_permissions: list = None):
        """
        Args:
            required_role: Мінімальна необхідна роль
            required_permissions: Список необхідних прав
        """
        super().__init__()
        self.required_role = required_role
        self.required_permissions = required_permissions or []
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Перевірка прав доступу"""
        user_role = data.get('user_role', 'user')
        
        # Owner має доступ до всього
        if user_role == 'owner':
            return await handler(event, data)
        
        # Перевірка мінімальної ролі
        if self.required_role:
            role_hierarchy = ['user', 'stylist', 'supervisor', 'owner']
            
            if user_role not in role_hierarchy:
                return await self._access_denied(event)
            
            user_level = role_hierarchy.index(user_role)
            required_level = role_hierarchy.index(self.required_role)
            
            if user_level < required_level:
                return await self._access_denied(event)
        
        # Перевірка конкретних прав
        if self.required_permissions:
            user_permissions = ROLE_PERMISSIONS.get(user_role, [])
            
            if '*' not in user_permissions:
                for permission in self.required_permissions:
                    if permission not in user_permissions:
                        return await self._access_denied(event)
        
        return await handler(event, data)
    
    async def _access_denied(self, event: TelegramObject):
        """Відповідь при відсутності доступу"""
        logger.warning(f"Access denied for user")
        
        if hasattr(event, 'answer'):
            await event.answer(
                "⛔ У вас немає доступу до цієї функції.\n"
                "Зверніться до адміністратора для отримання прав."
            )


def role_required(role: str):
    """
    Декоратор для перевірки ролі
    
    Args:
        role: Мінімальна необхідна роль
        
    Example:
        @router.message(Command("admin"))
        @role_required("supervisor")
        async def admin_command(message: Message):
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Отримуємо data з аргументів
            data = None
            for arg in args:
                if isinstance(arg, dict) and 'user_role' in arg:
                    data = arg
                    break
            
            if not data:
                # Якщо data не знайдено в args, шукаємо в kwargs
                data = kwargs.get('data', {})
            
            user_role = data.get('user_role', 'user')
            
            # Owner має доступ до всього
            if user_role == 'owner':
                return await func(*args, **kwargs)
            
            # Перевірка ролі
            role_hierarchy = ['user', 'stylist', 'supervisor', 'owner']
            
            if user_role not in role_hierarchy or role not in role_hierarchy:
                logger.warning(f"Invalid role in role_required decorator")
                return
            
            user_level = role_hierarchy.index(user_role)
            required_level = role_hierarchy.index(role)
            
            if user_level < required_level:
                logger.warning(f"Access denied: user role {user_role}, required {role}")
                
                # Відправляємо повідомлення про відсутність доступу
                message = None
                for arg in args:
                    if hasattr(arg, 'answer'):
                        message = arg
                        break
                
                if message:
                    await message.answer(
                        "⛔ У вас немає доступу до цієї функції."
                    )
                return
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_user_permission(user_role: str, permission: str) -> bool:
    """
    Перевірити чи має користувач певний дозвіл
    
    Args:
        user_role: Роль користувача
        permission: Необхідний дозвіл
        
    Returns:
        True якщо є дозвіл
    """
    if user_role == 'owner':
        return True
    
    user_permissions = ROLE_PERMISSIONS.get(user_role, [])
    
    return '*' in user_permissions or permission in user_permissions