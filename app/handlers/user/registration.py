"""
Registration Handler - реєстрація нових користувачів
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import RegistrationStates
from app.database.mongodb import get_database
from app.keyboards.inline import (
    get_body_type_keyboard,
    get_style_preferences_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard
)
from app.config.constants import (
    MIN_HEIGHT, MAX_HEIGHT, MIN_WEIGHT, MAX_WEIGHT,
    ERROR_INVALID_HEIGHT, ERROR_INVALID_WEIGHT, ERROR_INVALID_PHOTO,
    SUCCESS_PROFILE_CREATED
)

logger = logging.getLogger(__name__)

router = Router(name='registration_router')


@router.message(RegistrationStates.awaiting_height)
async def process_height(message: Message, state: FSMContext):
    """Обробка введення зросту"""
    try:
        height = int(message.text)
        
        if not (MIN_HEIGHT <= height <= MAX_HEIGHT):
            await message.answer(ERROR_INVALID_HEIGHT)
            return
        
        # Зберігаємо зріст
        await state.update_data(height=height)
        
        await message.answer(
            "⚖️ <b>Крок 2/5: Вага</b>\n\n"
            "Введіть вашу вагу в кілограмах:\n"
            "Наприклад: <code>70</code>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        
        await state.set_state(RegistrationStates.awaiting_weight)
        
    except ValueError:
        await message.answer(
            "❌ Будь ласка, введіть ваш зріст числом (наприклад: 175)"
        )


@router.message(RegistrationStates.awaiting_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обробка введення ваги"""
    try:
        weight = int(message.text)
        
        if not (MIN_WEIGHT <= weight <= MAX_WEIGHT):
            await message.answer(ERROR_INVALID_WEIGHT)
            return
        
        # Зберігаємо вагу
        await state.update_data(weight=weight)
        
        await message.answer(
            "👤 <b>Крок 3/5: Тип фігури</b>\n\n"
            "Оберіть ваш тип фігури:",
            reply_markup=get_body_type_keyboard(),
            parse_mode="HTML"
        )
        
        await state.set_state(RegistrationStates.awaiting_body_type)
        
    except ValueError:
        await message.answer(
            "❌ Будь ласка, введіть вашу вагу числом (наприклад: 70)"
        )


@router.callback_query(RegistrationStates.awaiting_body_type, F.data.startswith("body_type:"))
async def process_body_type(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору типу фігури"""
    body_type = callback.data.split(":")[1]
    
    # Зберігаємо тип фігури
    await state.update_data(body_type=body_type)
    
    await callback.message.edit_text(
        "👔 <b>Крок 4/5: Стиль одягу</b>\n\n"
        "Оберіть ваші улюблені стилі (можна кілька):\n"
        "Після вибору натисніть ✔️ Підтвердити",
        reply_markup=get_style_preferences_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(RegistrationStates.awaiting_style)
    await callback.answer()


@router.callback_query(RegistrationStates.awaiting_style, F.data.startswith("style:"))
async def process_style(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору стилю"""
    action = callback.data.split(":")[1]
    
    # Отримуємо поточні вибрані стилі
    data = await state.get_data()
    selected_styles = data.get('style_preferences', [])
    
    if action == "confirm":
        if not selected_styles:
            await callback.answer("❌ Оберіть хоча б один стиль!", show_alert=True)
            return
        
        # Переходимо до фото
        await callback.message.edit_text(
            "📸 <b>Крок 5/5: Фото</b>\n\n"
            "Надішліть своє фото для кращого підбору одягу.\n\n"
            "💡 <i>Це опціонально, можете пропустити цей крок.</i>",
            parse_mode="HTML"
        )
        
        await callback.message.answer(
            "Надішліть фото або використайте /cancel щоб завершити без фото:",
            reply_markup=get_cancel_keyboard()
        )
        
        await state.set_state(RegistrationStates.awaiting_photo)
        await callback.answer()
        
    else:
        # Перемикаємо вибір стилю
        if action in selected_styles:
            selected_styles.remove(action)
        else:
            selected_styles.append(action)
        
        await state.update_data(style_preferences=selected_styles)
        
        # Оновлюємо клавіатуру
        await callback.message.edit_reply_markup(
            reply_markup=get_style_preferences_keyboard(selected_styles)
        )
        await callback.answer()


@router.message(RegistrationStates.awaiting_photo, F.photo)
async def process_photo(message: Message, state: FSMContext, telegram_id: int):
    """Обробка фото"""
    # Отримуємо найбільше фото
    photo = message.photo[-1]
    photo_id = photo.file_id
    
    # Зберігаємо ID фото
    await state.update_data(photo_id=photo_id)
    
    # Завершуємо реєстрацію
    await complete_registration(message, state, telegram_id)


@router.message(RegistrationStates.awaiting_photo, F.text.in_(["/cancel", "❌ Скасувати"]))
async def skip_photo_command(message: Message, state: FSMContext, telegram_id: int):
    """Пропуск фото через команду"""
    await complete_registration(message, state, telegram_id)


@router.callback_query(RegistrationStates.awaiting_photo, F.data == "skip_photo")
async def skip_photo_callback(callback: CallbackQuery, state: FSMContext, telegram_id: int):
    """Пропуск фото через callback"""
    await complete_registration(callback.message, state, telegram_id)
    await callback.answer()


@router.message(RegistrationStates.awaiting_photo)
async def invalid_photo(message: Message):
    """Невірний формат фото"""
    await message.answer(
        "❌ Будь ласка, надішліть фотографію або використайте /cancel щоб пропустити цей крок."
    )


async def complete_registration(message: Message, state: FSMContext, telegram_id: int):
    """Завершення реєстрації"""
    # Отримуємо всі дані
    data = await state.get_data()
    
    # Перевіряємо обов'язкові поля
    required_fields = ['height', 'weight', 'body_type', 'style_preferences']
    for field in required_fields:
        if field not in data:
            await message.answer(
                "❌ Помилка реєстрації. Спробуйте ще раз з /start"
            )
            await state.clear()
            return
    
    # Зберігаємо профіль в БД
    db = await get_database()
    
    profile_data = {
        "user_id": telegram_id,
        "height": data['height'],
        "weight": data['weight'],
        "body_type": data['body_type'],
        "style_preferences": data['style_preferences'],
        "photo_url": data.get('photo_id'),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    try:
        await db.user_profiles.insert_one(profile_data)
        logger.info(f"Profile created for user {telegram_id}")
    except Exception as e:
        logger.error(f"Failed to create profile: {e}")
        await message.answer(
            "❌ Помилка при збереженні профілю. Спробуйте ще раз."
        )
        await state.clear()
        return
    
    # Очищаємо стан
    await state.clear()
    
    # Отримуємо дані для меню
    from app.database.mongodb import has_active_subscription, get_user
    
    has_sub = await has_active_subscription(telegram_id)
    user = await get_user(telegram_id)
    is_stylist = user.get('role') in ['stylist', 'supervisor', 'owner'] if user else False
    
    # Вітаємо користувача
    await message.answer(
        f"✅ <b>{SUCCESS_PROFILE_CREATED}</b>\n\n"
        "Ваш профіль:\n"
        f"📏 Зріст: {data['height']} см\n"
        f"⚖️ Вага: {data['weight']} кг\n"
        f"👤 Тип фігури: {data['body_type']}\n"
        f"👔 Стилі: {', '.join(data['style_preferences'])}\n"
        f"📸 Фото: {'Завантажено ✅' if data.get('photo_id') else 'Не завантажено'}\n\n"
        "🎁 <b>У вас є 1 безкоштовний запит!</b>\n"
        "Спробуйте згенерувати образ прямо зараз! 👇",
        parse_mode="HTML"
    )
    
    await message.answer(
        "🏠 <b>Головне меню</b>\n\n"
        "Оберіть потрібну дію:",
        reply_markup=get_main_menu_keyboard(
            has_subscription=has_sub,
            is_stylist=is_stylist
        ),
        parse_mode="HTML"
    )