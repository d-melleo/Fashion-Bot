# workers/config.py
from app.config.settings import settings

WORKER_SETTINGS = {
    'database_url': settings.MONGODB_URL,
    'rabbitmq_url': settings.RABBITMQ_URL,
    'ai_provider': settings.ACTIVE_AI_PROVIDER,
}