"""
Middleware для майбутньої інтеграції з API каталогу одягу
Це placeholder для масштабування функціоналу в майбутньому

Можливі інтеграції:
- Інтернет-магазини (ASOS, Zara, H&M API)
- Affiliate мережі (Amazon, Rakuten)
- Custom API власного каталогу
"""

import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import aiohttp
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class BaseCatalogProvider(ABC):
    """
    Базовий клас для провайдерів каталогу одягу
    Всі майбутні інтеграції повинні наслідувати цей клас
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(hours=1)
    
    @abstractmethod
    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Пошук товарів в каталозі
        
        Args:
            query: Пошуковий запит
            category: Категорія товарів
            filters: Додаткові фільтри (ціна, бренд, розмір)
            limit: Максимальна кількість результатів
            
        Returns:
            Список товарів
        """
        pass
    
    @abstractmethod
    async def get_product_details(self, product_id: str) -> Optional[Dict]:
        """
        Отримати деталі конкретного товару
        
        Args:
            product_id: ID товару
            
        Returns:
            Деталі товару або None
        """
        pass
    
    @abstractmethod
    async def get_recommendations(
        self,
        user_profile: Dict,
        season: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Отримати рекомендації на основі профілю користувача
        
        Args:
            user_profile: Профіль користувача (стиль, розмір, тощо)
            season: Пора року
            limit: Кількість рекомендацій
            
        Returns:
            Список рекомендованих товарів
        """
        pass
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Отримати дані з кешу"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                return data
            else:
                del self._cache[key]
        return None
    
    def _save_to_cache(self, key: str, data: Any):
        """Зберегти дані в кеш"""
        self._cache[key] = (data, datetime.now())


class FakeStoreCatalogProvider(BaseCatalogProvider):
    """
    Провайдер для Fake Store API (для розробки та тестування)
    """
    
    BASE_URL = "https://fakestoreapi.com"
    
    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Пошук товарів в Fake Store API"""
        cache_key = f"search_{query}_{category}_{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            async with aiohttp.ClientSession() as session:
                # Якщо вказана категорія
                if category:
                    url = f"{self.BASE_URL}/products/category/{category}"
                else:
                    url = f"{self.BASE_URL}/products"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        products = await response.json()
                        
                        # Фільтрація по запиту (примітивний пошук)
                        if query:
                            query_lower = query.lower()
                            products = [
                                p for p in products
                                if query_lower in p.get('title', '').lower()
                                or query_lower in p.get('description', '').lower()
                            ]
                        
                        # Застосування фільтрів
                        if filters:
                            products = self._apply_filters(products, filters)
                        
                        result = products[:limit]
                        self._save_to_cache(cache_key, result)
                        return result
        except Exception as e:
            logger.error(f"Error searching products: {e}")
        
        return []
    
    async def get_product_details(self, product_id: str) -> Optional[Dict]:
        """Отримати деталі товару"""
        cache_key = f"product_{product_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/products/{product_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        product = await response.json()
                        self._save_to_cache(cache_key, product)
                        return product
        except Exception as e:
            logger.error(f"Error getting product details: {e}")
        
        return None
    
    async def get_recommendations(
        self,
        user_profile: Dict,
        season: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Отримати рекомендації (заглушка для Fake Store)
        В реальній реалізації тут буде логіка підбору
        """
        # Визначаємо категорію на основі профілю
        style = user_profile.get('style_preferences', [])
        
        # Мапінг стилів на категорії
        category_map = {
            'casual': "men's clothing",
            'business': "men's clothing",
            'elegant': "women's clothing",
            'sport': "men's clothing",
        }
        
        category = None
        if style:
            category = category_map.get(style[0])
        
        # Отримуємо товари з обраної категорії
        products = await self.search_products(
            query="",
            category=category,
            limit=limit
        )
        
        return products
    
    def _apply_filters(self, products: List[Dict], filters: Dict) -> List[Dict]:
        """Застосування фільтрів до списку товарів"""
        filtered = products
        
        # Фільтр по ціні
        if 'min_price' in filters:
            filtered = [p for p in filtered if p.get('price', 0) >= filters['min_price']]
        
        if 'max_price' in filters:
            filtered = [p for p in filtered if p.get('price', 0) <= filters['max_price']]
        
        # Фільтр по рейтингу
        if 'min_rating' in filters:
            filtered = [
                p for p in filtered
                if p.get('rating', {}).get('rate', 0) >= filters['min_rating']
            ]
        
        return filtered


class CustomCatalogProvider(BaseCatalogProvider):
    """
    Placeholder для власного API каталогу
    Можна реалізувати в майбутньому
    """
    
    def __init__(self, api_key: str, base_url: str):
        super().__init__(api_key)
        self.base_url = base_url
    
    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        # TODO: Реалізувати інтеграцію з власним API
        logger.warning("CustomCatalogProvider not implemented yet")
        return []
    
    async def get_product_details(self, product_id: str) -> Optional[Dict]:
        # TODO: Реалізувати інтеграцію з власним API
        logger.warning("CustomCatalogProvider not implemented yet")
        return None
    
    async def get_recommendations(
        self,
        user_profile: Dict,
        season: str,
        limit: int = 10
    ) -> List[Dict]:
        # TODO: Реалізувати логіку рекомендацій
        logger.warning("CustomCatalogProvider not implemented yet")
        return []


class CatalogManager:
    """
    Менеджер для роботи з різними провайдерами каталогу
    Дозволяє легко перемикатися між провайдерами
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.providers: Dict[str, BaseCatalogProvider] = {}
        self.active_provider: Optional[str] = None
        
        # Реєстрація доступних провайдерів
        self._register_providers()
    
    def _register_providers(self):
        """Реєстрація всіх доступних провайдерів"""
        # Fake Store для розробки
        self.providers['fakestore'] = FakeStoreCatalogProvider()
        self.active_provider = 'fakestore'
        
        # TODO: Додати інші провайдери
        # self.providers['custom'] = CustomCatalogProvider(api_key, base_url)
    
    def set_active_provider(self, provider_name: str):
        """Встановити активного провайдера"""
        if provider_name in self.providers:
            self.active_provider = provider_name
            logger.info(f"Active catalog provider set to: {provider_name}")
        else:
            logger.error(f"Provider {provider_name} not found")
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Пошук через активного провайдера"""
        if not self.active_provider:
            return []
        
        provider = self.providers[self.active_provider]
        return await provider.search_products(query, category, filters, limit)
    
    async def get_product(self, product_id: str) -> Optional[Dict]:
        """Отримати товар через активного провайдера"""
        if not self.active_provider:
            return None
        
        provider = self.providers[self.active_provider]
        return await provider.get_product_details(product_id)
    
    async def get_recommendations_for_user(
        self,
        user_id: int,
        season: str,
        limit: int = 10
    ) -> List[Dict]:
        """Отримати рекомендації для користувача"""
        if not self.active_provider:
            return []
        
        # Отримуємо профіль користувача з БД
        user_profile = await self.db.user_profiles.find_one({'user_id': user_id})
        if not user_profile:
            return []
        
        provider = self.providers[self.active_provider]
        return await provider.get_recommendations(user_profile, season, limit)


# Singleton instance (буде ініціалізований в bot.py)
catalog_manager: Optional[CatalogManager] = None


def init_catalog_manager(db: AsyncIOMotorDatabase):
    """Ініціалізація менеджера каталогу"""
    global catalog_manager
    catalog_manager = CatalogManager(db)
    logger.info("Catalog manager initialized")


# Приклад використання
async def example_usage():
    """Приклад використання каталогу"""
    from app.database.mongodb import get_database
    
    db = await get_database()
    init_catalog_manager(db)
    
    # Пошук товарів
    products = await catalog_manager.search(
        query="shirt",
        category="men's clothing",
        limit=5
    )
    
    print(f"Found {len(products)} products")
    for product in products:
        print(f"- {product['title']}: ${product['price']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())