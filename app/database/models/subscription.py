"""
Subscription Model - модель підписки
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
from bson import ObjectId

from app.database.mongodb import get_database
from app.config.settings import settings


class Subscription:
    """Модель підписки користувача"""
    
    def __init__(
        self,
        user_id: int,
        status: str = "active",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        amount: float = float(settings.SUBSCRIPTION_PRICE),
        currency: str = settings.SUBSCRIPTION_CURRENCY,
        auto_renew: bool = False,
        created_at: Optional[datetime] = None,
        _id: Optional[ObjectId] = None
    ):
        self._id = _id
        self.user_id = user_id
        self.status = status
        self.start_date = start_date or datetime.utcnow()
        self.end_date = end_date or (self.start_date + timedelta(days=30))
        self.amount = amount
        self.currency = currency
        self.auto_renew = auto_renew
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Конвертувати в словник для MongoDB"""
        data = {
            "user_id": self.user_id,
            "status": self.status,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "amount": self.amount,
            "currency": self.currency,
            "auto_renew": self.auto_renew,
            "created_at": self.created_at
        }
        
        if self._id:
            data["_id"] = self._id
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Subscription':
        """Створити об'єкт з словника MongoDB"""
        return cls(
            _id=data.get("_id"),
            user_id=data["user_id"],
            status=data.get("status", "active"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            amount=data.get("amount", float(settings.SUBSCRIPTION_PRICE)),
            currency=data.get("currency", settings.SUBSCRIPTION_CURRENCY),
            auto_renew=data.get("auto_renew", False),
            created_at=data.get("created_at")
        )
    
    async def save(self):
        """Зберегти підписку в БД"""
        db = await get_database()
        
        if self._id:
            # Оновлення існуючого
            await db.subscriptions.update_one(
                {"_id": self._id},
                {"$set": self.to_dict()}
            )
        else:
            # Створення нового
            result = await db.subscriptions.insert_one(self.to_dict())
            self._id = result.inserted_id
    
    async def delete(self):
        """Видалити підписку з БД"""
        if self._id:
            db = await get_database()
            await db.subscriptions.delete_one({"_id": self._id})
    
    @classmethod
    async def get_by_user_id(cls, user_id: int) -> Optional['Subscription']:
        """Отримати активну підписку користувача"""
        db = await get_database()
        data = await db.subscriptions.find_one({
            "user_id": user_id,
            "status": "active"
        })
        
        if data:
            return cls.from_dict(data)
        return None
    
    @classmethod
    async def get_all_by_user(cls, user_id: int) -> list:
        """Отримати всі підписки користувача"""
        db = await get_database()
        cursor = db.subscriptions.find({"user_id": user_id}).sort("created_at", -1)
        subscriptions = await cursor.to_list(length=None)
        
        return [cls.from_dict(data) for data in subscriptions]
    
    def is_active(self) -> bool:
        """Перевірити чи активна підписка"""
        return (
            self.status == "active" and
            self.end_date > datetime.utcnow()
        )
    
    def days_left(self) -> int:
        """Кількість днів до закінчення"""
        if not self.is_active():
            return 0
        
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
    
    async def activate(self, duration_days: int = 30):
        """Активувати підписку"""
        self.status = "active"
        self.start_date = datetime.utcnow()
        self.end_date = self.start_date + timedelta(days=duration_days)
        await self.save()
    
    async def cancel(self):
        """Скасувати підписку"""
        self.status = "cancelled"
        await self.save()
    
    async def expire(self):
        """Позначити підписку як закінчену"""
        self.status = "expired"
        await self.save()
    
    async def renew(self, duration_days: int = 30):
        """Продовжити підписку"""
        self.start_date = datetime.utcnow()
        self.end_date = self.start_date + timedelta(days=duration_days)
        self.status = "active"
        await self.save()
    
    @classmethod
    async def check_and_expire_subscriptions(cls):
        """
        Перевірити та закінчити expired підписки
        Викликається періодично (наприклад, щодня)
        """
        db = await get_database()
        
        result = await db.subscriptions.update_many(
            {
                "status": "active",
                "end_date": {"$lt": datetime.utcnow()}
            },
            {
                "$set": {"status": "expired"}
            }
        )
        
        return result.modified_count
    
    def format_for_display(self) -> str:
        """Форматувати підписку для відображення"""
        if not self.is_active():
            return "❌ Підписка неактивна"
        
        days = self.days_left()
        text = f"✅ Підписка активна\n"
        text += f"📅 Діє до: {self.end_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Залишилось днів: {days}\n"
        text += f"💰 Вартість: ${self.amount}/{self.currency}\n"
        text += f"🔄 Автопродовження: {'Так ✅' if self.auto_renew else 'Ні ❌'}"
        
        return text
    
    def __repr__(self) -> str:
        return f"<Subscription user_id={self.user_id} status={self.status}>"
    
    def __str__(self) -> str:
        return f"Subscription(user={self.user_id}, status={self.status})"