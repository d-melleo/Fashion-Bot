"""
Base AI Provider - абстрактний клас для всіх AI провайдерів
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """
    Базовий клас для AI провайдерів
    
    Всі AI провайдери (Gemini, OpenAI, Claude) повинні наслідувати цей клас
    і реалізовувати всі абстрактні методи
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Ініціалізація провайдера
        
        Args:
            api_key: API ключ для провайдера
        """
        self.api_key = api_key
        self._validate_initialization()
    
    def _validate_initialization(self):
        """Валідація ініціалізації провайдера"""
        if not self.api_key:
            logger.warning(f"{self.__class__.__name__}: API key is not set")
        elif not self.validate_api_key():
            logger.warning(f"{self.__class__.__name__}: API key validation failed")
    
    @abstractmethod
    async def generate_outfit(self, prompt: str, user_profile: Dict) -> Optional[Dict]:
        """
        Генерація рекомендацій одягу
        
        Args:
            prompt: Промпт для AI
            user_profile: Профіль користувача з параметрами
            
        Returns:
            Dict з відповіддю AI або None при помилці
            
        Структура відповіді:
        {
            "provider": str,           # Назва провайдера
            "model": str,              # Назва моделі
            "prompt": str,             # Використаний промпт
            "response": str,           # Текст відповіді
            "user_profile": dict       # Профіль користувача
        }
        """
        pass
    
    @abstractmethod
    def build_prompt(self, user_profile: Dict, season: str) -> str:
        """
        Побудова промпту на основі профілю користувача
        
        Args:
            user_profile: Профіль користувача
            season: Пора року (winter, spring, summer, autumn)
            
        Returns:
            Готовий промпт для AI
        """
        pass
    
    def validate_api_key(self) -> bool:
        """
        Валідація API ключа
        
        Returns:
            True якщо ключ валідний
        """
        return bool(self.api_key and len(self.api_key) > 10)
    
    def format_outfit_response(self, ai_response: str) -> str:
        """
        Форматування відповіді AI для користувача
        
        Args:
            ai_response: Сира відповідь від AI
            
        Returns:
            Відформатована відповідь
        """
        # Базове форматування, може бути перевизначено в дочірніх класах
        formatted = f"👔 **Ваш персональний образ:**\n\n{ai_response}"
        formatted += "\n\n💡 *Рекомендації згенеровані AI*"
        return formatted
    
    def get_provider_name(self) -> str:
        """
        Отримати назву провайдера
        
        Returns:
            Назва класу провайдера
        """
        return self.__class__.__name__.replace("Provider", "").lower()
    
    def get_provider_info(self) -> Dict:
        """
        Отримати інформацію про провайдера
        
        Returns:
            Dict з інформацією
        """
        return {
            "name": self.get_provider_name(),
            "class": self.__class__.__name__,
            "has_api_key": bool(self.api_key),
            "api_key_valid": self.validate_api_key()
        }
    
    async def test_connection(self) -> bool:
        """
        Тестування підключення до AI провайдера
        
        Returns:
            True якщо підключення успішне
        """
        try:
            test_profile = {
                "height": 175,
                "weight": 70,
                "body_type": "average",
                "style_preferences": ["casual"]
            }
            
            test_prompt = "Test prompt for connection"
            result = await self.generate_outfit(test_prompt, test_profile)
            
            return bool(result)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def __repr__(self) -> str:
        """Представлення провайдера"""
        return f"<{self.__class__.__name__} api_key={'***' if self.api_key else 'None'}>"
    
    def __str__(self) -> str:
        """Строкове представлення"""
        return self.get_provider_name()


class AIProviderError(Exception):
    """Базовий exception для помилок AI провайдерів"""
    pass


class APIKeyError(AIProviderError):
    """Exception для помилок API ключа"""
    pass


class GenerationError(AIProviderError):
    """Exception для помилок генерації"""
    pass


class PromptError(AIProviderError):
    """Exception для помилок промпту"""
    pass