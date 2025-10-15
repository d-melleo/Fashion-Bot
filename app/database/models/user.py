"""
User Model - модель користувача
"""

from datetime import datetime
from typing import Optional, Dict
from bson import ObjectId

from app.database.mongodb import get_database


class User:
    """Модель користувача"""
    
    def __init__(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: str = "user",
        created_at: Optional[datetime] = None,
        last_active: Optional[datetime] = None,
        is_blocked: bool = False,
        has_used_trial: bool = False,
        total_generations: int = 0,
        _id: Optional[ObjectId] = None
    ):
        self._id = _id
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.created_at = created_at or datetime.utcnow()
        self.last_active = last_active or datetime.utcnow()
        self.is_blocked = is_blocked
        self.has_used_trial = has_used_trial
        self.total_generations = total_generations
    
    def to_dict(self) -> Dict:
        """Конвертувати в словник для MongoDB"""
        data = {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "is_blocked": self.is_blocked,
            "has_used_trial": self.has_used_trial,
            "total_generations": self.total_generations
        }
        
        if self._id:
            data["_id"] = self._id
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Створити об'єкт з словника MongoDB"""
        return cls(
            _id=data.get("_id"),
            telegram_id=data["telegram_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            role=data.get("role", "user"),
            created_at=data.get("created_at"),
            last_active=data.get("last_active"),
            is_blocked=data.get("is_blocked", False),
            has_used_trial=data.get("has_used_trial", False),
            total_generations=data.get("total_generations", 0)
        )
    
    async def save(self):
        """Зберегти користувача в БД"""
        db = await get_database()
        
        if self._id:
            # Оновлення існуючого
            await db.users.update_one(
                {"_id": self._id},
                {"$set": self.to_dict()}
            )
        else:
            # Створення нового
            result = await db.users.insert_one(self.to_dict())
            self._id = result.inserted_id
    
    async def delete(self):
        """Видалити користувача з БД"""
        if self._id:
            db = await get_database()
            await db.users.delete_one({"_id": self._id})
    
    @classmethod
    async def get_by_telegram_id(cls, telegram_id: int) -> Optional['User']:
        """Отримати користувача за Telegram ID"""
        db = await get_database()
        data = await db.users.find_one({"telegram_id": telegram_id})
        
        if data:
            return cls.from_dict(data)
        return None
    
    @classmethod
    async def get_by_id(cls, user_id: ObjectId) -> Optional['User']:
        """Отримати користувача за MongoDB ID"""
        db = await get_database()
        data = await db.users.find_one({"_id": user_id})
        
        if data:
            return cls.from_dict(data)
        return None
    
    async def update_activity(self):
        """Оновити час останньої активності"""
        self.last_active = datetime.utcnow()
        await self.save()
    
    async def block(self):
        """Заблокувати користувача"""
        self.is_blocked = True
        await self.save()
    
    async def unblock(self):
        """Розблокувати користувача"""
        self.is_blocked = False
        await self.save()
    
    async def mark_trial_used(self):
        """Позначити trial як використаний"""
        self.has_used_trial = True
        await self.save()
    
    async def increment_generations(self):
        """Збільшити лічильник генерацій"""
        self.total_generations += 1
        await self.save()
    
    def get_full_name(self) -> str:
        """Отримати повне ім'я"""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        
        return " ".join(parts) if parts else f"User {self.telegram_id}"
    
    def is_admin(self) -> bool:
        """Перевірити чи є користувач адміном"""
        return self.role in ['stylist', 'supervisor', 'owner']
    
    def can_manage_users(self) -> bool:
        """Перевірити чи може керувати користувачами"""
        return self.role in ['supervisor', 'owner']
    
    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} role={self.role}>"
    
    def __str__(self) -> str:
        return self.get_full_name()