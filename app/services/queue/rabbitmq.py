"""
RabbitMQ Integration для обробки AI запитів
Producer - відправляє запити в чергу
Consumer - обробляє запити через AI Worker
"""

import json
import logging
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime

import aio_pika
from aio_pika import Message, DeliveryMode, connect_robust
from aio_pika.abc import AbstractRobustConnection, AbstractChannel, AbstractQueue

from app.config.settings import settings

logger = logging.getLogger(__name__)

QUEUE_ARGUMENTS = {
    'x-message-ttl': 600000,  # 10 minutes in milliseconds
    'x-max-length': 1000,     # Maximum number of messages
    'x-overflow': 'reject-publish',  # Reject new messages when queue is full
    'x-queue-type': 'classic',  # Use classic queue type
    'x-ha-policy': 'all'      # Mirror queue across all nodes
}

class RabbitMQConnection:
    """Singleton клас для підключення до RabbitMQ"""
    
    _instance: Optional['RabbitMQConnection'] = None
    _connection: Optional[AbstractRobustConnection] = None
    _channel: Optional[AbstractChannel] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Встановити підключення до RabbitMQ"""
        if self._connection is None or self._connection.is_closed:
            try:
                self._connection = await connect_robust(
                    settings.RABBITMQ_URL,
                    client_properties={"connection_name": "fashion_bot"}
                )
                self._channel = await self._connection.channel()
                await self._channel.set_qos(prefetch_count=1)
                
                logger.info("Connected to RabbitMQ successfully")
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                raise
    
    async def get_channel(self) -> AbstractChannel:
        """Отримати канал RabbitMQ"""
        if self._channel is None or self._channel.is_closed:
            await self.connect()
        return self._channel
    
    async def close(self):
        """Закрити підключення"""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        
        logger.info("RabbitMQ connection closed")


# Singleton instance
rabbitmq_connection = RabbitMQConnection()


class AIGenerationProducer:
    """Producer для відправки AI генерації в чергу"""
    
    QUEUE_NAME = "ai_generation_queue"
    EXCHANGE_NAME = "ai_generation_exchange"
    ROUTING_KEY = "ai.generation"
    
    def __init__(self):
        self.channel: Optional[AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None
    
    async def initialize(self):
        """Ініціалізація producer"""
        self.channel = await rabbitmq_connection.get_channel()
        
        # Створення exchange
        exchange = await self.channel.declare_exchange(
            self.EXCHANGE_NAME,
            aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        
        # Створення черги
        self.queue = await self.channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
            arguments=QUEUE_ARGUMENTS
        )
        
        # Прив'язка черги до exchange
        await self.queue.bind(exchange, routing_key=self.ROUTING_KEY)
        
        logger.info(f"AI Generation Producer initialized: {self.QUEUE_NAME}")
    
    async def send_generation_task(
        self,
        task_id: str,
        user_id: int,
        user_profile: Dict,
        season: str,
        generation_id: str
    ) -> bool:
        """
        Відправити задачу на генерацію в чергу
        
        Args:
            task_id: Унікальний ID задачі
            user_id: Telegram ID користувача
            user_profile: Профіль користувача
            season: Пора року
            generation_id: ID запису генерації в БД
            
        Returns:
            True якщо успішно відправлено
        """
        if not self.channel or not self.queue:
            await self.initialize()
        
        user_profile['_id'] = str(user_profile['_id'])
        user_profile['created_at'] = str(user_profile['created_at'].isoformat())
        user_profile['updated_at'] = str(user_profile['updated_at'].isoformat())
        
        try:
            current_time = datetime.utcnow()
            message_body = {
                "task_id": task_id,
                "user_id": user_id,
                "user_profile": user_profile,
                "season": season,
                "generation_id": generation_id,
                "timestamp": current_time.isoformat(),
            }
            
            message = Message(
                body=json.dumps(message_body, default=str).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                message_id=task_id,
                timestamp=current_time,
                headers={
                    "user_id": user_id,
                    "generation_id": generation_id,
                }
            )
            
            exchange = await self.channel.get_exchange(self.EXCHANGE_NAME)
            await exchange.publish(
                message,
                routing_key=self.ROUTING_KEY
            )
            
            logger.info(
                f"Generation task sent to queue",
                extra={
                    "task_id": task_id,
                    "user_id": user_id,
                    "generation_id": generation_id,
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send generation task: {e}")
            return False
    
    async def get_queue_size(self) -> int:
        """Отримати кількість повідомлень в черзі"""
        if not self.queue:
            await self.initialize()
        
        queue_info = await self.queue.declare(passive=True)
        return queue_info.message_count


class AIGenerationConsumer:
    """Consumer для обробки AI генерації з черги"""
    
    QUEUE_NAME = "ai_generation_queue"
    
    def __init__(self, callback: Callable):
        """
        Args:
            callback: Async функція для обробки повідомлень
                    Повинна приймати Dict з даними задачі
        """
        self.channel: Optional[AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None
        self.callback = callback
        self._consumer_tag: Optional[str] = None
    
    async def initialize(self):
        """Ініціалізація consumer"""
        self.channel = await rabbitmq_connection.get_channel()
        
        # Отримання черги
        self.queue = await self.channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
            arguments=QUEUE_ARGUMENTS
        )
        
        logger.info(f"AI Generation Consumer initialized: {self.QUEUE_NAME}")
    
    async def start_consuming(self):
        """Почати обробку повідомлень з черги"""
        if not self.queue:
            await self.initialize()
        
        async def process_message(message: aio_pika.IncomingMessage):
            """Обробка одного повідомлення"""
            async with message.process():
                try:
                    # Парсинг даних
                    task_data = json.loads(message.body.decode())
                    
                    logger.info(
                        f"Processing generation task",
                        extra={
                            "task_id": task_data.get('task_id'),
                            "user_id": task_data.get('user_id'),
                        }
                    )
                    
                    # Виклик callback для обробки
                    await self.callback(task_data)
                    
                    logger.info(
                        f"Generation task completed",
                        extra={"task_id": task_data.get('task_id')}
                    )
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Повідомлення буде повернуто в чергу
                    raise
        
        # Початок споживання
        self._consumer_tag = await self.queue.consume(process_message)
        logger.info("Started consuming messages from queue")
    
    async def stop_consuming(self):
        """Зупинити обробку повідомлень"""
        if self._consumer_tag and self.queue:
            await self.queue.cancel(self._consumer_tag)
            logger.info("Stopped consuming messages")


class StylistRequestProducer:
    """Producer для запитів до стиліста (опціонально, якщо потрібна черга)"""
    
    QUEUE_NAME = "stylist_requests_queue"
    EXCHANGE_NAME = "stylist_exchange"
    ROUTING_KEY = "stylist.request"
    
    def __init__(self):
        self.channel: Optional[AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None
    
    async def initialize(self):
        """Ініціалізація producer"""
        self.channel = await rabbitmq_connection.get_channel()
        
        exchange = await self.channel.declare_exchange(
            self.EXCHANGE_NAME,
            aio_pika.ExchangeType.FANOUT,  # Broadcast всім стилістам
            durable=True
        )
        
        self.queue = await self.channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
            arguments=QUEUE_ARGUMENTS
        )
        
        await self.queue.bind(exchange)
        
        logger.info(f"Stylist Request Producer initialized: {self.QUEUE_NAME}")
    
    async def send_stylist_request(
        self,
        request_id: str,
        user_id: int,
        user_profile: Dict,
        message: str
    ) -> bool:
        """Відправити запит на стиліста"""
        if not self.channel or not self.queue:
            await self.initialize()
        
        try:
            message_body = {
                "request_id": request_id,
                "user_id": user_id,
                "user_profile": user_profile,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            msg = Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            
            exchange = await self.channel.get_exchange(self.EXCHANGE_NAME)
            await exchange.publish(msg, routing_key="")
            
            logger.info(
                f"Stylist request sent",
                extra={"request_id": request_id, "user_id": user_id}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send stylist request: {e}")
            return False


# Глобальні instances
ai_producer: Optional[AIGenerationProducer] = None
stylist_producer: Optional[StylistRequestProducer] = None


async def init_producers():
    """Ініціалізація всіх producers"""
    global ai_producer, stylist_producer
    
    await rabbitmq_connection.connect()
    
    ai_producer = AIGenerationProducer()
    await ai_producer.initialize()
    
    stylist_producer = StylistRequestProducer()
    await stylist_producer.initialize()
    
    logger.info("All RabbitMQ producers initialized")


async def close_connections():
    """Закрити всі підключення"""
    await rabbitmq_connection.close()
    logger.info("All RabbitMQ connections closed")


# Утилітна функція для відправки задачі
async def send_ai_generation_task(
    user_id: int,
    user_profile: Dict,
    season: str,
    generation_id: str
) -> Optional[str]:
    """
    Зручна функція для відправки задачі на генерацію
    
    Returns:
        task_id якщо успішно, None якщо помилка
    """
    if not ai_producer:
        await init_producers()
    
    task_id = f"gen_{user_id}_{int(datetime.utcnow().timestamp())}"
    
    success = await ai_producer.send_generation_task(
        task_id=task_id,
        user_id=user_id,
        user_profile=user_profile,
        season=season,
        generation_id=generation_id
    )
    
    return task_id if success else None


async def get_queue_stats() -> Dict[str, int]:
    """Отримати статистику черг"""
    if not ai_producer:
        await init_producers()
    
    ai_queue_size = await ai_producer.get_queue_size()
    
    return {
        "ai_generation_queue": ai_queue_size,
    }


# Приклад використання
async def example_usage():
    """Приклад використання RabbitMQ"""
    # Ініціалізація
    await init_producers()
    
    # Відправка задачі
    user_profile = {
        "height": 180,
        "weight": 75,
        "body_type": "athletic",
        "style_preferences": ["casual", "sport"]
    }
    
    task_id = await send_ai_generation_task(
        user_id=123456789,
        user_profile=user_profile,
        season="summer",
        generation_id="gen_12345"
    )
    
    print(f"Task sent with ID: {task_id}")
    
    # Перевірка статистики
    stats = await get_queue_stats()
    print(f"Queue stats: {stats}")
    
    # Закриття підключень
    await close_connections()


if __name__ == "__main__":
    asyncio.run(example_usage())