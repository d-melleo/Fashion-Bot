"""
MongoDB Connection and Initialization
"""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure


from app.config.settings import settings

logger = logging.getLogger(__name__)

# Global database instance
_db_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def init_database() -> AsyncIOMotorDatabase:
    """
    Ініціалізація підключення до MongoDB
    
    Returns:
        AsyncIOMotorDatabase instance
    """
    global _db_client, _database
    
    try:
        # Створення клієнта
        _db_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            retryWrites=True,
            maxPoolSize=50,
            minPoolSize=10
        )
        
        # Отримання бази даних
        _database = _db_client[settings.MONGO_DATABASE]
        
        # Перевірка підключення
        try:
            await _db_client.admin.command('ping')
        except ServerSelectionTimeoutError as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}")
            raise
        except ConnectionFailure as e:
            logger.error(f"MongoDB Atlas connection failure: {e}")
            raise
        
        # Створення індексів
        await create_indexes()
        
        logger.info(
            f"Successfully connected to MongoDB",
            extra={"database": settings.MONGO_DATABASE}
        )
        
        return _database
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def create_indexes():
    """Створення індексів для оптимізації запитів"""
    if _database is None:
        return
    
    try:
        # Users collection indexes
        await _database.users.create_index("telegram_id", unique=True)
        await _database.users.create_index("role")
        await _database.users.create_index("created_at")
        
        # User profiles indexes
        await _database.user_profiles.create_index("user_id", unique=True)
        
        # Subscriptions indexes
        await _database.subscriptions.create_index("user_id")
        await _database.subscriptions.create_index("status")
        await _database.subscriptions.create_index("end_date")
        
        # Generation history indexes
        await _database.generation_history.create_index("user_id")
        await _database.generation_history.create_index("status")
        await _database.generation_history.create_index("created_at")
        await _database.generation_history.create_index([("user_id", 1), ("created_at", -1)])
        
        # Stylist requests indexes
        await _database.stylist_requests.create_index("user_id")
        await _database.stylist_requests.create_index("stylist_id")
        await _database.stylist_requests.create_index("status")
        
        # Invoices indexes
        await _database.invoices.create_index("user_id")
        await _database.invoices.create_index("invoice_id", unique=True)
        await _database.invoices.create_index("status")
        
        # Admin logs indexes
        await _database.admin_logs.create_index("admin_id")
        await _database.admin_logs.create_index("created_at")
        
        # Statistics indexes
        await _database.bot_statistics.create_index([("period", 1), ("period_date", -1)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")


async def get_database() -> AsyncIOMotorDatabase:
    """
    Отримати instance бази даних
    
    Returns:
        AsyncIOMotorDatabase instance
    """
    if _database is None:
        await init_database()
    
    return _database


async def close_database():
    """Закрити підключення до бази даних"""
    global _db_client, _database
    
    if _db_client:
        _db_client.close()
        _db_client = None
        _database = None
        logger.info("Database connection closed")


# Database helper functions

async def user_exists(telegram_id: int) -> bool:
    """Перевірити чи існує користувач"""
    db = await get_database()
    user = await db.users.find_one({"telegram_id": telegram_id})
    return user is not None


async def get_user(telegram_id: int) -> Optional[dict]:
    """Отримати користувача за Telegram ID"""
    db = await get_database()
    return await db.users.find_one({"telegram_id": telegram_id})


async def create_user(telegram_id: int, username: str = None, 
                    first_name: str = None, last_name: str = None) -> dict:
    """Створити нового користувача"""
    from datetime import datetime
    
    db = await get_database()
    
    user_data = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "role": "user",
        "created_at": datetime.utcnow(),
        "last_active": datetime.utcnow(),
        "is_blocked": False,
        "has_used_trial": False,
        "total_generations": 0,
    }
    
    result = await db.users.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    
    logger.info(f"New user created: {telegram_id}")
    
    return user_data


async def update_user_activity(telegram_id: int):
    """Оновити час останньої активності користувача"""
    from datetime import datetime
    
    db = await get_database()
    await db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"last_active": datetime.utcnow()}}
    )


async def get_user_profile(user_id) -> Optional[dict]:
    """Отримати профіль користувача"""
    db = await get_database()
    return await db.user_profiles.find_one({"user_id": user_id})


async def has_active_subscription(telegram_id: int) -> bool:
    """Перевірити чи має користувач активну підписку"""
    from datetime import datetime
    
    db = await get_database()
    subscription = await db.subscriptions.find_one({
        "user_id": telegram_id,
        "status": "active",
        "end_date": {"$gt": datetime.utcnow()}
    })
    
    return subscription is not None


async def can_use_trial(telegram_id: int) -> bool:
    """Перевірити чи може користувач використати trial"""
    if not settings.ENABLE_TRIAL_REQUEST:
        return False
    
    user = await get_user(telegram_id)
    if not user:
        return False
    
    return not user.get("has_used_trial", False)


async def mark_trial_used(telegram_id: int):
    return
    """Позначити trial як використаний"""
    db = await get_database()
    await db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"has_used_trial": True}}
    )


async def get_user_generations_count(telegram_id: int, period: str = "all") -> int:
    """Отримати кількість генерацій користувача"""
    from datetime import datetime, timedelta
    
    db = await get_database()
    
    query = {
        "user_id": telegram_id,
        "status": "completed"
    }
    
    if period == "today":
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        query["created_at"] = {"$gte": today_start}
    elif period == "week":
        week_start = datetime.utcnow() - timedelta(days=7)
        query["created_at"] = {"$gte": week_start}
    elif period == "month":
        month_start = datetime.utcnow() - timedelta(days=30)
        query["created_at"] = {"$gte": month_start}
    
    return await db.generation_history.count_documents(query)


# Initialization check
async def check_database_connection() -> bool:
    """Перевірити підключення до бази даних"""
    try:
        db = await get_database()
        await db.command('ping')
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False