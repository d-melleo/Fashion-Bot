"""
Statistics Collector - збір та обробка статистики бота
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

from app.database.mongodb import get_database
from app.services.payment.invoice import invoice_manager

logger = logging.getLogger(__name__)


class StatisticsCollector:
    """Клас для збору та обробки статистики"""
    
    @staticmethod
    async def collect_daily_statistics(date: Optional[datetime] = None) -> Dict:
        """
        Зібрати денну статистику
        
        Args:
            date: Дата для статистики (за замовчуванням сьогодні)
            
        Returns:
            Dict зі статистикою
        """
        if not date:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        db = await get_database()
        
        start_date = date
        end_date = date + timedelta(days=1)
        
        # Загальна кількість користувачів
        total_users = await db.users.count_documents({})
        
        # Нові користувачі за день
        new_users = await db.users.count_documents({
            "created_at": {"$gte": start_date, "$lt": end_date}
        })
        
        # Активні користувачі (мали активність за день)
        active_users = await db.users.count_documents({
            "last_active": {"$gte": start_date, "$lt": end_date}
        })
        
        # Активні підписки
        active_subscriptions = await db.subscriptions.count_documents({
            "status": "active",
            "end_date": {"$gt": datetime.utcnow()}
        })
        
        # Користувачі які запитували стиліста
        users_requested_stylist = await db.stylist_requests.count_documents({
            "created_at": {"$gte": start_date, "$lt": end_date}
        })
        
        # Генерації за день
        total_generations = await db.generation_history.count_documents({
            "created_at": {"$gte": start_date, "$lt": end_date},
            "status": "completed"
        })
        
        # Дохід за день
        daily_revenue = await invoice_manager.calculate_total_revenue(
            start_date=start_date,
            end_date=end_date
        )
        
        statistics = {
            "period": "daily",
            "period_date": date,
            "total_users": total_users,
            "new_users": new_users,
            "active_users": active_users,
            "active_subscriptions": active_subscriptions,
            "users_requested_stylist": users_requested_stylist,
            "total_generations": total_generations,
            "total_revenue": daily_revenue,
            "updated_at": datetime.utcnow()
        }
        
        # Зберігаємо в БД
        await db.bot_statistics.update_one(
            {
                "period": "daily",
                "period_date": date
            },
            {"$set": statistics},
            upsert=True
        )
        
        logger.info(f"Daily statistics collected for {date.strftime('%Y-%m-%d')}")
        
        return statistics
    
    @staticmethod
    async def collect_monthly_statistics(
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict:
        """
        Зібрати місячну статистику
        
        Args:
            year: Рік
            month: Місяць
            
        Returns:
            Dict зі статистикою
        """
        now = datetime.utcnow()
        if not year:
            year = now.year
        if not month:
            month = now.month
        
        # Початок та кінець місяця
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        db = await get_database()
        
        # Загальна кількість користувачів
        total_users = await db.users.count_documents({})
        
        # Нові користувачі за місяць
        new_users = await db.users.count_documents({
            "created_at": {"$gte": start_date, "$lt": end_date}
        })
        
        # Активні користувачі за місяць
        active_users = await db.users.count_documents({
            "last_active": {"$gte": start_date, "$lt": end_date}
        })
        
        # Активні підписки
        active_subscriptions = await db.subscriptions.count_documents({
            "status": "active",
            "end_date": {"$gt": datetime.utcnow()}
        })
        
        # Нові підписки за місяць
        new_subscriptions = await db.subscriptions.count_documents({
            "created_at": {"$gte": start_date, "$lt": end_date}
        })
        
        # Запити стиліста
        stylist_requests = await db.stylist_requests.count_documents({
            "created_at": {"$gte": start_date, "$lt": end_date}
        })
        
        # Генерації
        total_generations = await db.generation_history.count_documents({
            "created_at": {"$gte": start_date, "$lt": end_date},
            "status": "completed"
        })
        
        # Дохід
        monthly_revenue = await invoice_manager.calculate_total_revenue(
            start_date=start_date,
            end_date=end_date
        )
        
        statistics = {
            "period": "monthly",
            "period_date": start_date,
            "year": year,
            "month": month,
            "total_users": total_users,
            "new_users": new_users,
            "active_users": active_users,
            "active_subscriptions": active_subscriptions,
            "new_subscriptions": new_subscriptions,
            "users_requested_stylist": stylist_requests,
            "total_generations": total_generations,
            "total_revenue": monthly_revenue,
            "updated_at": datetime.utcnow()
        }
        
        # Зберігаємо в БД
        await db.bot_statistics.update_one(
            {
                "period": "monthly",
                "year": year,
                "month": month
            },
            {"$set": statistics},
            upsert=True
        )
        
        logger.info(f"Monthly statistics collected for {year}-{month:02d}")
        
        return statistics
    
    @staticmethod
    async def get_user_growth(days: int = 30) -> List[Dict]:
        """
        Отримати динаміку росту користувачів
        
        Args:
            days: Кількість днів
            
        Returns:
            Список з даними по днях
        """
        db = await get_database()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        results = await db.users.aggregate(pipeline).to_list(length=None)
        
        return [
            {
                "date": result["_id"],
                "new_users": result["count"]
            }
            for result in results
        ]
    
    @staticmethod
    async def get_revenue_dynamics(days: int = 30) -> List[Dict]:
        """
        Отримати динаміку доходу
        
        Args:
            days: Кількість днів
            
        Returns:
            Список з даними по днях
        """
        db = await get_database()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "status": "paid",
                    "paid_at": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$paid_at"
                        }
                    },
                    "revenue": {"$sum": "$amount"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        results = await db.invoices.aggregate(pipeline).to_list(length=None)
        
        return [
            {
                "date": result["_id"],
                "revenue": float(result["revenue"]),
                "payments_count": result["count"]
            }
            for result in results
        ]
    
    @staticmethod
    async def get_generation_statistics() -> Dict:
        """
        Отримати статистику по генераціям
        
        Returns:
            Dict зі статистикою
        """
        db = await get_database()
        
        # Загальна кількість генерацій
        total_generations = await db.generation_history.count_documents({})
        
        # Успішні генерації
        successful = await db.generation_history.count_documents({"status": "completed"})
        
        # Невдалі генерації
        failed = await db.generation_history.count_documents({"status": "failed"})
        
        # Середній час генерації
        pipeline = [
            {
                "$match": {
                    "status": "completed",
                    "processing_time": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_time": {"$avg": "$processing_time"},
                    "min_time": {"$min": "$processing_time"},
                    "max_time": {"$max": "$processing_time"}
                }
            }
        ]
        
        time_stats = await db.generation_history.aggregate(pipeline).to_list(length=1)
        
        if time_stats:
            avg_time = time_stats[0].get("avg_time", 0)
            min_time = time_stats[0].get("min_time", 0)
            max_time = time_stats[0].get("max_time", 0)
        else:
            avg_time = min_time = max_time = 0
        
        # Розподіл по сезонах
        season_pipeline = [
            {
                "$match": {"status": "completed"}
            },
            {
                "$group": {
                    "_id": "$season",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        season_stats = await db.generation_history.aggregate(season_pipeline).to_list(length=None)
        
        seasons = {
            result["_id"]: result["count"]
            for result in season_stats
        }
        
        return {
            "total_generations": total_generations,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_generations * 100) if total_generations > 0 else 0,
            "avg_processing_time": round(avg_time, 2),
            "min_processing_time": round(min_time, 2),
            "max_processing_time": round(max_time, 2),
            "by_season": seasons
        }
    
    @staticmethod
    async def format_statistics_message(period: str = "monthly") -> str:
        """
        Форматувати статистику для відправки адміну
        
        Args:
            period: Період (daily, monthly)
            
        Returns:
            Відформатоване повідомлення
        """
        if period == "monthly":
            stats = await StatisticsCollector.collect_monthly_statistics()
        else:
            stats = await StatisticsCollector.collect_daily_statistics()
        
        gen_stats = await StatisticsCollector.get_generation_statistics()
        
        message = f"📊 <b>Статистика бота</b>\n"
        message += f"{'='*30}\n\n"
        
        if period == "monthly":
            message += f"📅 <b>Період:</b> {stats['year']}-{stats['month']:02d}\n\n"
        else:
            date_str = stats['period_date'].strftime('%Y-%m-%d')
            message += f"📅 <b>Дата:</b> {date_str}\n\n"
        
        message += f"👥 <b>Користувачі:</b>\n"
        message += f"  • Всього: {stats['total_users']}\n"
        message += f"  • Нових: {stats['new_users']}\n"
        message += f"  • Активних: {stats['active_users']}\n\n"
        
        message += f"💳 <b>Підписки:</b>\n"
        message += f"  • Активних: {stats['active_subscriptions']}\n"
        if period == "monthly":
            message += f"  • Нових: {stats.get('new_subscriptions', 0)}\n"
        message += f"  • Дохід: ${stats['total_revenue']:.2f}\n\n"
        
        message += f"🎨 <b>Генерації:</b>\n"
        message += f"  • За період: {stats['total_generations']}\n"
        message += f"  • Всього: {gen_stats['total_generations']}\n"
        message += f"  • Успішність: {gen_stats['success_rate']:.1f}%\n"
        message += f"  • Середній час: {gen_stats['avg_processing_time']}с\n\n"
        
        message += f"👨‍💼 <b>Стиліст:</b>\n"
        message += f"  • Запитів: {stats['users_requested_stylist']}\n\n"
        
        message += f"🔄 <b>Оновлено:</b> {stats['updated_at'].strftime('%Y-%m-%d %H:%M')}"
        
        return message


# Singleton instance
statistics_collector = StatisticsCollector()


async def collect_and_save_statistics():
    """
    Зібрати та зберегти статистику
    Викликається періодично (наприклад, щодня о 00:00)
    """
    try:
        # Збираємо денну статистику
        await statistics_collector.collect_daily_statistics()
        
        # Перевіряємо чи потрібно зібрати місячну
        now = datetime.utcnow()
        if now.day == 1:  # Перший день місяця
            await statistics_collector.collect_monthly_statistics()
        
        logger.info("Statistics collected successfully")
        
    except Exception as e:
        logger.error(f"Failed to collect statistics: {e}", exc_info=True)