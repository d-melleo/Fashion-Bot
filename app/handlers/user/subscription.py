"""
Subscription Handler - обробка підписки та платежів через LiqPay
"""

import logging
from datetime import datetime, timedelta
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.config.settings import settings
from app.database.mongodb import get_database, has_active_subscription, get_user
from app.database.models.subscription import Subscription
from app.services.payment.liqpay import create_subscription_invoice, liqpay_client
import httpx


logger = logging.getLogger(__name__)

router = Router(name='subscription_router')

CURRENCY_API_URL = "https://api.exchangerate.host/convert"
ACCESS_KEY = settings.CURRENCY_CONVERSION_KEY

async def convert_to_usd(amount: float, currency: str) -> float:
    """Конвертувати суму в USD через exchangerate.host"""
    if currency.upper() == settings.SUBSCRIPTION_CURRENCY:
        return amount
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            CURRENCY_API_URL,
            params={
                "from": currency,
                "to": settings.SUBSCRIPTION_CURRENCY,
                "amount": settings.SUBSCRIPTION_PRICE
            }
        )
        data = resp.json()
        return float(data.get("result", amount))

@router.message(Command("subscribe"))
async def process_subscribe(message: Message):
    telegram_id = message.from_user.id
    db = await get_database()

    # Перевірка активної підписки
    active_sub = await has_active_subscription(telegram_id)
    if active_sub:
        sub = await Subscription.get_by_user_id(telegram_id)
        await message.answer(
            f"У вас вже є активна підписка!\n\n{sub.format_for_display()}",
            parse_mode="HTML"
        )
        return

    # Створення інвойсу LiqPay
    order_id = f"sub_{telegram_id}_{int(datetime.utcnow().timestamp())}"
    invoice = await create_subscription_invoice(
        user_id=telegram_id,
        order_id=order_id,
        result_url=None,
        server_url=None
    )
    payment_url = liqpay_client.get_payment_url(invoice)

    # Зберігаємо інвойс в БД
    invoice_data = {
        "order_id": order_id,
        "user_id": telegram_id,
        "amount": invoice.get("amount"),
        "currency": invoice.get("currency"),
        "status": "pending",
        "created_at": datetime.utcnow(),
        "payment_url": payment_url
    }
    await db.invoices.insert_one(invoice_data)

    await message.answer(
        "💳 <b>Оформлення підписки</b>\n\n"
        "Натисніть кнопку нижче, щоб оплатити підписку через LiqPay:",
        reply_markup=None,
        parse_mode="HTML"
    )
    await message.answer(
        f'<a href="{payment_url}">🔗 Оплатити підписку через LiqPay</a>',
        parse_mode="HTML"
    )

    await message.answer(
        "Після оплати натисніть /confirm_payment для перевірки статусу."
    )

@router.message(Command("confirm_payment"))
async def confirm_payment(message: Message):
    telegram_id = message.from_user.id
    db = await get_database()

    # Знаходимо останній інвойс
    invoice = await db.invoices.find_one(
        {"user_id": telegram_id, "status": "pending"},
        sort=[("created_at", -1)]
    )
    if not invoice:
        await message.answer("Немає активних платежів для підтвердження.")
        return

    # Перевіряємо статус платежу через LiqPay
    payment_status = await liqpay_client.check_payment_status(invoice["order_id"])
    status = payment_status.get("status")
    paid_amount = float(payment_status.get("amount", invoice["amount"]))
    paid_currency = payment_status.get("currency", invoice["currency"])
    
    if status.lower() in ["success", "test", "sandbox"]:
        # Конвертуємо в USD
        usd_amount = await convert_to_usd(paid_amount, paid_currency)

        # Оновлюємо інвойс
        await db.invoices.update_one(
            {"_id": invoice["_id"]},
            {"$set": {
                "status": "paid",
                "paid_amount": paid_amount,
                "paid_currency": paid_currency,
                "usd_amount": usd_amount,
                "paid_at": datetime.utcnow()
            }}
        )
        
        # Створюємо підписку (на 30 днів)
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30)
        
        sub = Subscription(
            user_id=telegram_id,
            status="active",
            start_date=start_date,
            end_date=end_date,
            amount=usd_amount,
            currency=settings.SUBSCRIPTION_CURRENCY,
            auto_renew=False
        )
        await sub.save()

        await message.answer(
            "✅ Платіж успішно отримано! Ваша підписка активована.\n\n"
            f"{sub.format_for_display()}\n\n"
            f"🧾 <b>Інвойс:</b>\n"
            f"Сума: {paid_amount} {paid_currency} (~${usd_amount:.2f} {settings.SUBSCRIPTION_CURRENCY})\n"
            f"Order ID: {invoice['order_id']}",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Платіж ще не підтверджено або неуспішний.\n"
            "Будь ласка, спробуйте ще раз через декілька хвилин."
        )