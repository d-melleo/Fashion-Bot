"""
Google Gemini AI Provider Implementation
"""

import logging
from typing import Dict, Optional
import asyncio

import google.generativeai as genai

from app.config.settings import settings
from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider"""
    
    def __init__(self):
        super().__init__(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL
        self.temperature = settings.GEMINI_TEMPERATURE
        self.max_tokens = settings.GEMINI_MAX_TOKENS
        
        # Конфігурація Gemini
        genai.configure(api_key=self.api_key)
        
        # Налаштування генерації
        self.generation_config = {
            "temperature": self.temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": self.max_tokens,
        }
        
        # Налаштування безпеки
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
        ]
        
        # Ініціалізація моделі
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
        
        logger.info(f"Gemini provider initialized: {self.model_name}")
    
    async def generate_outfit(self, prompt: str, user_profile: Dict) -> Optional[Dict]:
        """
        Генерація рекомендацій одягу через Gemini
        
        Args:
            prompt: Промпт для AI
            user_profile: Профіль користувача
            
        Returns:
            Dict з відповіддю AI або None при помилці
        """
        try:
            logger.debug(f"Starting Gemini generation")
            
            # Генерація відповіді (виконується в executor для async)
            response = await self._generate_content_async(prompt)
            
            if not response:
                logger.warning("Gemini returned empty response")
                return None
            
            # Формування результату
            result = {
                "provider": "gemini",
                "model": self.model_name,
                "prompt": prompt,
                "response": response,
                "user_profile": {
                    "height": user_profile.get("height"),
                    "weight": user_profile.get("weight"),
                    "body_type": user_profile.get("body_type"),
                    "style_preferences": user_profile.get("style_preferences", [])
                }
            }
            
            logger.info(
                f"Gemini generation successful",
                extra={
                    "model": self.model_name,
                    "response_length": len(response),
                    "response_preview": response[:100] + "..." if len(response) > 100 else response
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}", exc_info=True)
            return None
    
    async def _generate_content_async(self, prompt: str) -> Optional[str]:
        """
        Асинхронна генерація контенту
        Gemini SDK не підтримує async, тому використовуємо executor
        
        Args:
            prompt: Текст промпту
            
        Returns:
            Текст відповіді або None
        """
        try:
            # Виконуємо синхронний виклик в executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._generate_content_sync,
                prompt
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            return None
    
    def _generate_content_sync(self, prompt: str) -> Optional[str]:
        """
        Синхронна генерація контенту
        
        Args:
            prompt: Текст промпту
            
        Returns:
            Текст відповіді або None
        """
        try:
            # Виклик Gemini API
            response = self.model.generate_content(prompt)
            
            # Перевірка чи є текст у відповіді
            if not response or not response.text:
                logger.warning("Gemini returned empty response")
                return None
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def format_outfit_response(self, ai_response: str) -> str:
        """
        Форматування відповіді AI для користувача
        
        Args:
            ai_response: Сира відповідь від AI
            
        Returns:
            Відформатована відповідь
        """
        # Додаємо емодзі та форматування
        formatted = f"👔 **Ваш персональний образ:**\n\n{ai_response}"
        
        # Додаємо footer
        formatted += "\n\n💡 *Рекомендації згенеровані AI на основі вашого профілю*"
        
        return formatted
    
    def build_prompt(self, user_profile: Dict, season: str) -> str:
        """
        Побудова промпту для Gemini на основі профілю користувача
        
        Args:
            user_profile: Профіль користувача
            season: Пора року
            
        Returns:
            Готовий промпт
        """
        # Мапінг українських термінів на англійські
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

Please provide a detailed outfit recommendation in Ukrainian language with the following structure:

1. **Повний образ** - опис всього комплекту (топ, низ, взуття, верхній одяг якщо потрібно)

2. **Кольорова палітра** - які кольори підійдуть найкраще та чому

3. **Матеріали та тканини** - які тканини оптимальні для {season_en} та вашого типу фігури

4. **Поради зі стилю** - як правильно поєднувати речі, на що звернути увагу

5. **Аксесуари** - які аксесуари доповнять образ

Be specific, practical, and consider the season. Write in a friendly, professional tone in Ukrainian. Focus on real, wearable recommendations that suit the person's body type and style preferences."""

        return prompt


# Тестування провайдера
async def test_gemini_provider():
    """Тестова функція для перевірки Gemini"""
    provider = GeminiProvider()
    
    test_profile = {
        "height": 180,
        "weight": 75,
        "body_type": "athletic",
        "style_preferences": ["casual", "sport"]
    }
    
    # Побудова промпту
    test_prompt = provider.build_prompt(test_profile, "summer")
    
    print("=" * 60)
    print("Testing Gemini provider...")
    print("=" * 60)
    print(f"\nPrompt:\n{test_prompt[:200]}...\n")
    
    result = await provider.generate_outfit(test_prompt, test_profile)
    
    if result:
        print("\n" + "=" * 60)
        print("✓ Test successful!")
        print("=" * 60)
        print(f"\nProvider: {result['provider']}")
        print(f"Model: {result['model']}")
        print(f"Response length: {len(result['response'])} characters")
        print(f"\nResponse preview:\n{result['response'][:300]}...")
        print("\n" + "=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ Test failed!")
        print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gemini_provider())