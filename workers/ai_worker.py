"""
AI Worker для обробки запитів на генерацію одягу
Працює як окремий процес і обробляє повідомлення з RabbitMQ
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict
from datetime import datetime

# Додаємо кореневу директорію в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import settings
from app.database.mongodb import init_database, get_database
from app.services.queue.rabbitmq import (
    AIGenerationConsumer,
    rabbitmq_connection,
    close_connections
)
from app.services.ai.manager import ai_manager, init_ai_manager
from app.utils.logger import setup_logger

logger = logging.getLogger(__name__)


class AIGenerationWorker:
    """Worker для обробки AI генерацій"""
    
    def __init__(self):
        self.consumer: AIGenerationConsumer = None
        self.db = None
        self.is_running = False
    
    async def initialize(self):
        """Ініціалізація worker"""
        # Підключення до БД
        await init_database()
        self.db = await get_database()
        
        # Ініціалізація AI Manager
        await init_ai_manager()
        
        # Ініціалізація Consumer
        self.consumer = AIGenerationConsumer(callback=self.process_generation)
        await self.consumer.initialize()
        
        logger.info("AI Generation Worker initialized")
    
    async def process_generation(self, task_data: Dict):
        """
        Обробка задачі на генерацію одягу
        
        Args:
            task_data: Дані з RabbitMQ
        """
        task_id = task_data.get('task_id')
        user_id = task_data.get('user_id')
        generation_id = task_data.get('generation_id')
        user_profile = task_data.get('user_profile')
        season = task_data.get('season')
        
        try:
            # Оновлюємо статус в БД - "processing"
            await self.db.generation_history.update_one(
                {'_id': generation_id},
                {
                    '$set': {
                        'status': 'processing',
                        'task_id': task_id,
                        'started_at': datetime.utcnow()
                    }
                }
            )
            
            logger.info(
                f"Starting AI generation",
                extra={
                    "task_id": task_id,
                    "user_id": user_id,
                    "season": season
                }
            )
            
            # Формування промпту для AI
            from app.services.ai.gemini import GeminiProvider
            
            gemini_provider = GeminiProvider()
            prompt = gemini_provider.build_prompt(user_profile, season)
            
            # Генерація через AI Manager
            start_time = datetime.utcnow()
            ai_response = await ai_manager.generate_outfit(prompt, user_profile)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            if ai_response:
                # Успішна генерація
                await self.db.generation_history.update_one(
                    {'_id': generation_id},
                    {
                        '$set': {
                            'status': 'completed',
                            'ai_response': ai_response,
                            'completed_at': datetime.utcnow(),
                            'processing_time': processing_time,
                            'ai_provider': ai_manager.active_provider
                        }
                    }
                )
                
                # Оновлюємо статистику користувача
                await self.db.users.update_one(
                    {'telegram_id': user_id},
                    {
                        '$inc': {'total_generations': 1},
                        '$set': {'last_active': datetime.utcnow()}
                    }
                )
                
                logger.info(
                    f"AI generation completed successfully",
                    extra={
                        "task_id": task_id,
                        "processing_time": processing_time,
                        "user_id": user_id
                    }
                )
                
                # TODO: Відправити повідомлення користувачу через бота
                await self._notify_user(user_id, generation_id, ai_response)
                
            else:
                # Помилка генерації
                raise Exception("AI returned empty response")
        
        except Exception as e:
            logger.error(
                f"AI generation failed: {e}",
                extra={"task_id": task_id, "user_id": user_id}
            )
            
            # Оновлюємо статус в БД - "failed"
            await self.db.generation_history.update_one(
                {'_id': generation_id},
                {
                    '$set': {
                        'status': 'failed',
                        'error_message': str(e),
                        'completed_at': datetime.utcnow()
                    }
                }
            )
            
            # TODO: Повідомити користувача про помилку
            await self._notify_user_error(user_id, generation_id)
    
    def _build_prompt(self, user_profile: Dict, season: str) -> str:
        """
        Формування промпту для AI на основі профілю користувача
        
        Args:
            user_profile: Профіль користувача
            season: Пора року
            
        Returns:
            Промпт для AI
        """
        # Мапінг українських термінів на англійські для AI
        season_map = {
            'winter': 'winter',
            'spring': 'spring',
            'summer': 'summer',
            'autumn': 'autumn',
            'зима': 'winter',
            'весна': 'spring',
            'літо': 'summer',
            'осінь': 'autumn'
        }
        
        body_type_map = {
            'slim': 'slim body type',
            'athletic': 'athletic build',
            'average': 'average build',
            'curvy': 'curvy figure',
            'plus_size': 'plus size'
        }
        
        style_map = {
            'casual': 'casual style',
            'business': 'business/formal style',
            'sport': 'sporty/athletic style',
            'street': 'streetwear style',
            'elegant': 'elegant/classy style'
        }
        
        # Параметри користувача
        height = user_profile.get('height', 170)
        weight = user_profile.get('weight', 70)
        body_type = user_profile.get('body_type', 'average')
        styles = user_profile.get('style_preferences', ['casual'])
        
        # Переклад параметрів
        season_en = season_map.get(season.lower(), 'summer')
        body_type_en = body_type_map.get(body_type, 'average build')
        styles_en = [style_map.get(s, s) for s in styles]
        
        # Формування промпту
        prompt = f"""You are a professional fashion stylist. Create a complete outfit recommendation for a person with the following characteristics:

Physical Parameters:
- Height: {height} cm
- Weight: {weight} kg
- Body Type: {body_type_en}

Style Preferences: {', '.join(styles_en)}
Season: {season_en}

Please provide:
1. Complete outfit description (top, bottom, shoes, outerwear if needed)
2. Color palette recommendations
3. Fabric/material suggestions appropriate for {season_en}
4. Styling tips and advice
5. Accessory recommendations

Format your response in a clear, structured way in Ukrainian language. Be specific and practical with your recommendations."""

        return prompt
    
    async def _notify_user(self, user_id: int, generation_id: str, ai_response: Dict):
        """
        Повідомити користувача про готовність генерації
        
        Args:
            user_id: Telegram ID користувача
            generation_id: ID генерації
            ai_response: Відповідь AI
        """
        from app.bot import bot
        from app.handlers.user.generation import send_generation_result
        
        try:
            await send_generation_result(user_id, generation_id, ai_response, bot)
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
    
    async def _notify_user_error(self, user_id: int, generation_id: str):
        """Повідомити користувача про помилку"""
        from app.bot import bot
        from app.handlers.user.generation import send_generation_error
        
        try:
            await send_generation_error(user_id, generation_id, bot)
        except Exception as e:
            logger.error(f"Failed to notify user about error {user_id}: {e}")
    
    async def start(self):
        """Запуск worker"""
        self.is_running = True
        
        try:
            await self.initialize()
            
            logger.info("AI Worker started, waiting for tasks...")
            
            # Початок обробки повідомлень
            await self.consumer.start_consuming()
            
            # Тримаємо worker запущеним
            while self.is_running:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Зупинка worker"""
        self.is_running = False
        
        if self.consumer:
            await self.consumer.stop_consuming()
        
        await close_connections()
        logger.info("AI Worker stopped")


async def main():
    """Головна функція worker"""
    # Налаштування логування
    setup_logger(
        log_level=settings.LOG_LEVEL,
        log_file=Path(settings.LOG_FILE_PATH).parent / "ai_worker.log"
    )
    
    logger.info("="*50)
    logger.info("AI Generation Worker Starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Active AI Provider: {settings.ACTIVE_AI_PROVIDER}")
    logger.info("="*50)
    
    # Створення та запуск worker
    worker = AIGenerationWorker()
    
    try:
        await worker.start()
    except Exception as e:
        logger.critical(f"Critical error in worker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker shutdown complete")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)