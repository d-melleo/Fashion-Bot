"""
Generation Handler - генерація образів одягу через AI
"""

import logging
from datetime import datetime
from bson import ObjectId

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import GenerationStates
from app.database.mongodb import (
    get_database, get_user_profile, 
    has_active_subscription, can_use_trial, mark_trial_used
)
from app.keyboards.inline import (
    get_season_keyboard, get_generation_confirm_keyboard,
    get_cancel_keyboard, get_subscription_keyboard
)
from app.services.queue.rabbitmq import send_ai_generation_task
from app.config.constants import (
    ERROR_NO_PROFILE, ERROR_NO_SUBSCRIPTION, 
    SUCCESS_GENERATION_STARTED
)
from app.middlewares.subscription import subscription_required

logger = logging.getLogger(__name__)

router = Router(name='generation_router')


@router.callback_query(F.data == "generate_outfit")
@router.message(F.text == "👔 Згенерувати образ")
async def start_generation(event: Message | CallbackQuery, state: FSMContext, telegram_id: int):
    """Початок генерації образу"""
    # Перевіряємо наявність профілю
    profile = await get_user_profile(telegram_id)
    
    if not profile:
        text = ERROR_NO_PROFILE
        
        if isinstance(event, Message):
            await event.answer(text)
        else:
            await event.answer(text, show_alert=True)
        return
    
    # Перевіряємо підписку або trial
    has_sub = await has_active_subscription(telegram_id)
    trial_available = await can_use_trial(telegram_id)
    
    if not has_sub and not trial_available:
        # Немає доступу
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                ERROR_NO_SUBSCRIPTION,
                reply_markup=get_subscription_keyboard(),
                parse_mode="HTML"
            )
            await event.answer()
        else:
            await event.answer(
                ERROR_NO_SUBSCRIPTION,
                reply_markup=get_subscription_keyboard(),
                parse_mode="HTML"
            )
        return
    
    # Показуємо вибір пори року
    text = (
        "🌍 <b>Генерація образу</b>\n\n"
        "Для якої пори року підібрати одяг?"
    )
    
    if trial_available and not has_sub:
        text += "\n\n🎁 <i>Це ваш безкоштовний запит!</i>"
    
    keyboard = get_season_keyboard()
    
    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    
    await state.set_state(GenerationStates.select_season)


@router.callback_query(GenerationStates.select_season, F.data.startswith("season:"))
async def select_season(callback: CallbackQuery, state: FSMContext):
    """Вибір пори року"""
    season = callback.data.split(":")[1]
    
    # Зберігаємо пору року
    await state.update_data(season=season)
    
    # Мапінг сезонів на українську
    season_names = {
        "spring": "весни",
        "summer": "літа",
        "autumn": "осені",
        "winter": "зими"
    }
    
    season_emoji = {
        "spring": "🌸",
        "summer": "☀️",
        "autumn": "🍂",
        "winter": "❄️"
    }
    
    await callback.message.edit_text(
        f"{season_emoji[season]} <b>Підтвердження</b>\n\n"
        f"Згенерувати образ для <b>{season_names[season]}</b>?\n\n"
        f"⏱ Генерація займе 10-30 секунд.",
        reply_markup=get_generation_confirm_keyboard(season),
        parse_mode="HTML"
    )
    
    await state.set_state(GenerationStates.confirm_generation)
    await callback.answer()


@router.callback_query(GenerationStates.confirm_generation, F.data.startswith("confirm_gen:"))
async def confirm_generation(callback: CallbackQuery, state: FSMContext, telegram_id: int):
    """Підтвердження та запуск генерації"""
    season = callback.data.split(":")[1]
    
    # Отримуємо профіль
    profile = await get_user_profile(telegram_id)
    
    if not profile:
        await callback.answer(ERROR_NO_PROFILE, show_alert=True)
        return
    
    # Перевіряємо доступ
    has_sub = await has_active_subscription(telegram_id)
    trial_available = await can_use_trial(telegram_id)
    
    if not has_sub and not trial_available:
        await callback.message.edit_text(
            ERROR_NO_SUBSCRIPTION,
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Створюємо запис генерації в БД
    db = await get_database()
    
    generation_data = {
        "user_id": telegram_id,
        "season": season,
        "status": "pending",
        "ai_provider": "gemini",
        "created_at": datetime.utcnow()
    }
    
    result = await db.generation_history.insert_one(generation_data)
    generation_id = str(result.inserted_id)
    
    # Відправляємо в RabbitMQ
    task_id = await send_ai_generation_task(
        user_id=telegram_id,
        user_profile=dict(profile),
        season=season,
        generation_id=generation_id
    )
    
    if not task_id:
        # Помилка відправки в чергу
        await db.generation_history.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "failed", "error_message": "Failed to queue task"}}
        )
        
        await callback.message.edit_text(
            "❌ <b>Помилка</b>\n\n"
            "Не вдалося розпочати генерацію. Спробуйте пізніше.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Якщо це trial - позначаємо як використаний
    if not has_sub and trial_available:
        await mark_trial_used(telegram_id)
    
    # Повідомляємо користувача
    await callback.message.edit_text(
        f"⏳ <b>Генерація розпочата!</b>\n\n"
        f"Ваш запит обробляється AI.\n"
        f"Зачекайте 10-30 секунд...\n\n"
        f"📊 ID запиту: <code>{generation_id}</code>\n\n"
        f"Ви отримаєте результат в цьому чаті.",
        parse_mode="HTML"
    )
    await callback.answer()
    
    await state.set_state(GenerationStates.processing)
    await state.update_data(generation_id=generation_id)
    
    logger.info(
        f"Generation started",
        extra={
            "user_id": telegram_id,
            "generation_id": generation_id,
            "season": season,
            "task_id": task_id
        }
    )


async def send_generation_result(
    user_id: int,
    generation_id: str,
    ai_response: dict,
    bot
):
    """
    Відправити результат генерації користувачу
    Ця функція викликається з AI Worker після завершення генерації
    
    Args:
        user_id: Telegram ID користувача
        generation_id: ID генерації
        ai_response: Відповідь від AI
        bot: Bot instance
    """
    try:
        response_text = ai_response.get('response', '')
        
        if not response_text:
            # Помилка генерації
            await bot.send_message(
                user_id,
                "❌ <b>Помилка генерації</b>\n\n"
                "На жаль, не вдалося згенерувати образ. Спробуйте ще раз.",
                parse_mode="HTML"
            )
            return
        
        # Форматуємо відповідь
        formatted_response = (
            "✨ <b>Ваш персональний образ готовий!</b>\n\n"
            f"{response_text}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 ID: <code>{generation_id}</code>\n"
            "🤖 Згенеровано AI\n\n"
            "💡 Використайте /history щоб переглянути всі генерації"
        )
        
        # Відправляємо результат
        await bot.send_message(
            user_id,
            formatted_response,
            parse_mode="HTML"
        )
        
        logger.info(f"Generation result sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to send generation result: {e}")


async def send_generation_error(user_id: int, generation_id: str, bot):
    """
    Відправити повідомлення про помилку генерації
    
    Args:
        user_id: Telegram ID користувача
        generation_id: ID генерації
        bot: Bot instance
    """
    try:
        await bot.send_message(
            user_id,
            "❌ <b>Помилка генерації</b>\n\n"
            "На жаль, виникла помилка при генерації образу.\n"
            f"ID запиту: <code>{generation_id}</code>\n\n"
            "Спробуйте ще раз командою /generate",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")