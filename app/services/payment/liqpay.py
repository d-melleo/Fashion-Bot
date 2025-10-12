"""
LiqPay Test API Integration Template
Обробка платежів для підписки на бота
"""

import json
import base64
import hashlib
import logging
from typing import Dict, Optional
from datetime import datetime

import aiohttp
from cryptography.fernet import Fernet

from app.config.settings import settings

logger = logging.getLogger(__name__)


class LiqPayClient:
    """
    Клієнт для роботи з LiqPay API (Test Mode)
    
    Документація: https://www.liqpay.ua/documentation/api/home
    """
    
    API_URL = "https://www.liqpay.ua/api/"
    CHECKOUT_URL = "https://www.liqpay.ua/api/3/checkout"
    
    def __init__(self):
        self.public_key = settings.LIQPAY_PUBLIC_KEY
        self.private_key = settings.LIQPAY_PRIVATE_KEY
        self.test_mode = settings.LIQPAY_TEST_MODE
        self.currency = settings.SUBSCRIPTION_CURRENCY
        self.amount = settings.SUBSCRIPTION_PRICE
    
    def _generate_signature(self, data: str) -> str:
        """
        Генерує підпис для запиту
        
        Args:
            data: Base64 encoded дані
            
        Returns:
            Base64 encoded SHA1 підпис
        """
        sign_string = self.private_key + data + self.private_key
        signature = base64.b64encode(
            hashlib.sha1(sign_string.encode('utf-8')).digest()
        )
        return signature.decode('utf-8')
    
    def _prepare_data(self, params: Dict) -> tuple[str, str]:
        """
        Підготовка даних для запиту
        
        Args:
            params: Параметри платежу
            
        Returns:
            Tuple (data, signature)
        """
        # Додаємо обов'язкові параметри
        params['public_key'] = self.public_key
        
        if self.test_mode:
            params['sandbox'] = 1
        
        # Кодуємо в base64
        data_json = json.dumps(params)
        data = base64.b64encode(data_json.encode('utf-8')).decode('utf-8')
        
        # Генеруємо підпис
        signature = self._generate_signature(data)
        
        return data, signature
    
    async def create_invoice(
        self,
        order_id: str,
        amount: float,
        description: str,
        user_id: int,
        user_email: Optional[str] = None,
        result_url: Optional[str] = None,
        server_url: Optional[str] = None,
    ) -> Dict:
        """
        Створює інвойс для оплати підписки
        
        Args:
            order_id: Унікальний ID замовлення
            amount: Сума платежу
            description: Опис платежу
            user_id: Telegram ID користувача
            user_email: Email користувача (опціонально)
            result_url: URL для редиректу після оплати
            server_url: URL для callback повідомлень
            
        Returns:
            Dict з даними інвойсу
        """
        params = {
            'version': 3,
            'action': 'pay',
            'amount': amount,
            'currency': self.currency,
            'description': description,
            'order_id': order_id,
            'product_description': description,
            'language': 'uk',
        }
        
        # Додаємо опціональні параметри
        if result_url:
            params['result_url'] = result_url
        
        if server_url:
            params['server_url'] = server_url
        
        # Додаємо інформацію про користувача
        params['customer'] = str(user_id)
        
        if user_email:
            params['customer_email'] = user_email
        
        data, signature = self._prepare_data(params)
        
        logger.info(
            f"Creating LiqPay invoice",
            extra={
                "order_id": order_id,
                "amount": amount,
                "user_id": user_id,
                "test_mode": self.test_mode
            }
        )
        
        return {
            'data': data,
            'signature': signature,
            'checkout_url': self.CHECKOUT_URL,
            'order_id': order_id,
            'amount': amount,
            'currency': self.currency,
        }
    
    async def check_payment_status(
        self,
        order_id: str
    ) -> Dict:
        """
        Перевіряє статус платежу
        
        Args:
            order_id: ID замовлення
            
        Returns:
            Dict зі статусом платежу
        """
        params = {
            'version': 3,
            'action': 'status',
            'order_id': order_id,
        }
        
        data, signature = self._prepare_data(params)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_URL}request",
                data={
                    'data': data,
                    'signature': signature
                }
            ) as response:
                result = await response.json()
                
                logger.debug(
                    f"Payment status checked",
                    extra={
                        "order_id": order_id,
                        "status": result.get('status'),
                    }
                )
                
                return result
    
    def parse_callback(self, data: str, signature: str) -> Optional[Dict]:
        """
        Парсить callback від LiqPay
        
        Args:
            data: Base64 encoded дані
            signature: Підпис
            
        Returns:
            Dict з даними callback або None якщо підпис невалідний
        """
        # Перевіряємо підпис
        expected_signature = self._generate_signature(data)
        
        if signature != expected_signature:
            logger.warning("Invalid LiqPay callback signature")
            return None
        
        # Декодуємо дані
        decoded_data = base64.b64decode(data).decode('utf-8')
        callback_data = json.loads(decoded_data)
        
        logger.info(
            f"LiqPay callback received",
            extra={
                "order_id": callback_data.get('order_id'),
                "status": callback_data.get('status'),
            }
        )
        
        return callback_data
    
    def get_payment_url(self, invoice_data: Dict) -> str:
        """
        Генерує URL для оплати
        
        Args:
            invoice_data: Дані інвойсу з create_invoice()
            
        Returns:
            URL для оплати
        """
        return (
            f"{invoice_data['checkout_url']}"
            f"?data={invoice_data['data']}"
            f"&signature={invoice_data['signature']}"
        )
    
    @staticmethod
    def is_payment_successful(callback_data: Dict) -> bool:
        """
        Перевіряє чи платіж успішний
        
        Args:
            callback_data: Дані з callback
            
        Returns:
            True якщо платіж успішний
        """
        return callback_data.get('status') in ['success', 'sandbox']
    
    @staticmethod
    def get_payment_amount(callback_data: Dict) -> float:
        """
        Отримує суму платежу з callback
        
        Args:
            callback_data: Дані з callback
            
        Returns:
            Сума платежу
        """
        return float(callback_data.get('amount', 0))


# Singleton instance
liqpay_client = LiqPayClient()


async def create_subscription_invoice(
    user_id: int,
    order_id: str,
    result_url: Optional[str] = None,
    server_url: Optional[str] = None,
) -> Dict:
    """
    Створює інвойс для підписки на бота
    
    Args:
        user_id: Telegram ID користувача
        order_id: Унікальний ID замовлення
        result_url: URL для редиректу
        server_url: URL для callback
        
    Returns:
        Dict з даними інвойсу
    """
    description = f"Підписка на Fashion Style Bot - {datetime.now().strftime('%B %Y')}"
    
    invoice = await liqpay_client.create_invoice(
        order_id=order_id,
        amount=liqpay_client.amount,
        description=description,
        user_id=user_id,
        result_url=result_url,
        server_url=server_url,
    )
    
    return invoice


async def verify_payment_callback(data: str, signature: str) -> Optional[Dict]:
    """
    Верифікує callback від LiqPay
    
    Args:
        data: Base64 encoded дані
        signature: Підпис
        
    Returns:
        Dict з даними callback або None
    """
    return liqpay_client.parse_callback(data, signature)


# Тестові функції для розробки
async def test_create_invoice():
    """Тестова функція для створення інвойсу"""
    invoice = await create_subscription_invoice(
        user_id=123456789,
        order_id=f"test_{int(datetime.now().timestamp())}",
    )
    
    payment_url = liqpay_client.get_payment_url(invoice)
    print(f"Test payment URL: {payment_url}")
    
    return invoice


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_create_invoice())