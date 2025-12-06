"""
Start Handler - обробка команди /start та реєстрація
"""

import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import RegistrationStates
from app.database.mongodb import get_user_profile, has_active_subscription
from app.keyboards.inline import get_main_menu_keyboard, get_body_type_keyboard, get_cancel_keyboard
from app.config.constants import WELCOME_TEXT, HELP_TEXT

logger = logging.getLogger(__name__)

router = Router(name='start_router')


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: dict, telegram_id: int):
    """
    Обробка команди /start
    
    Якщо користувач новий - починаємо реєстрацію
    Якщо існуючий - показуємо головне меню
    """
    # Скидаємо стан
    await state.clear()
    
    # Перевіряємо чи є профіль
    profile = await get_user_profile(telegram_id)
    
    if not profile:
        # Новий користувач - починаємо реєстрацію
        await message.answer(
            f"👋 <b>Вітаємо, {message.from_user.first_name}!</b>\n\n"
            "Я ваш персональний AI-стиліст! 🎨\n\n"
            "Допоможу підібрати ідеальний образ на основі:\n"
            "  • Ваших параметрів тіла\n"
            "  • Улюбленого стилю\n"
            "  • Пори року\n\n"
            "Давайте створимо ваш профіль! 📝",
            parse_mode="HTML"
        )
        
        await message.answer(
            "📏 <b>Крок 1/5: Зріст</b>\n\n"
            "Введіть ваш зріст в сантиметрах:\n"
            "Наприклад: <code>175</code>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        
        await state.set_state(RegistrationStates.awaiting_height)
        
    else:
        # Існуючий користувач - показуємо меню
        has_sub = await has_active_subscription(telegram_id)
        is_stylist = db_user.get('role') in ['stylist', 'supervisor', 'owner']
        
        await message.answer(
            f"👋 <b>Раді бачити вас знову, {message.from_user.first_name}!</b>\n\n"
            "Що бажаєте зробити сьогодні? 👇",
            reply_markup=await get_main_menu_keyboard(
                has_subscription=has_sub,
                is_stylist=is_stylist
            ),
            parse_mode="HTML"
        )


@router.message(Command("menu"))
@router.callback_query(F.data == "back_to_menu")
async def show_main_menu(event: Message | CallbackQuery, state: FSMContext, 
                        db_user: dict, telegram_id: int):
    """Показати головне меню"""
    # Скидаємо стан
    await state.clear()
    
    has_sub = await has_active_subscription(telegram_id)
    is_stylist = db_user.get('role') in ['stylist', 'supervisor', 'owner']
    
    menu_text = (
        "🏠 <b>Головне меню</b>\n\n"
        "Оберіть потрібну дію з меню нижче:"
    )
    
    keyboard = await get_main_menu_keyboard(
        has_subscription=has_sub,
        is_stylist=is_stylist
    )
    
    if isinstance(event, Message):
        await event.answer(
            menu_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:  # CallbackQuery
        await event.message.edit_text(
            menu_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await event.answer()


@router.message(Command("help"))
async def cmd_help(message: Message, user_role: str):
    """Довідка по командах"""
    
    # Базові команди для всіх
    help_text = (
        "ℹ️ <b>Довідка по командах</b>\n\n"
        "<b>Основні команди:</b>\n"
        "/start - Почати роботу з ботом\n"
        "/menu - Головне меню\n"
        "/profile - Переглянути/редагувати профіль\n"
        "/generate - Згенерувати образ одягу\n"
        "/history - Переглянути історію\n"
        "/subscription - Статус підписки\n"
        "/subscribe - Оформити підписку\n"
        "/help - Ця довідка\n"
        "/cancel - Скасувати поточну операцію\n\n"
    )
    
    # Додаткові команди для стилістів
    if user_role in ['stylist', 'supervisor', 'owner']:
        help_text += (
            "<b>Команди стиліста:</b>\n"
            "/stylist_requests - Переглянути запити клієнтів\n\n"
        )
    
    # Додаткові команди для супервайзерів
    if user_role in ['supervisor', 'owner']:
        help_text += (
            "<b>Команди супервайзера:</b>\n"
            "/add_stylist - Додати стиліста\n"
            "/remove_stylist - Видалити стиліста\n"
            "/list_stylists - Список стилістів\n"
            "/statistics - Статистика бота\n"
            "/block_user - Заблокувати користувача\n\n"
        )
    
    # Додаткові команди для власника
    if user_role == 'owner':
        help_text += (
            "<b>Команди власника:</b>\n"
            "/add_supervisor - Додати супервайзера\n"
            "/manage_subscription - Керування підпискою\n"
            "/ai_settings - Налаштування AI\n"
            "/system_status - Статус системи\n\n"
        )
    
    help_text += (
        "💡 <b>Підказка:</b>\n"
        "Використовуйте кнопки в меню для швидкого доступу до функцій!"
    )
    
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("cancel"))
@router.callback_query(F.data == "cancel")
async def cmd_cancel(event: Message | CallbackQuery, state: FSMContext):
    """Скасування поточної операції"""
    current_state = await state.get_state()
    
    if current_state is None:
        text = "Немає активних операцій для скасування."
    else:
        await state.clear()
        text = "✅ Операцію скасовано.\n\nВикористайте /menu для головного меню."
    
    if isinstance(event, Message):
        await event.answer(text)
    else:  # CallbackQuery
        await event.message.answer(text)
        await event.answer()


@router.callback_query(F.data == "cancel_action")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """Скасування через callback"""
    await cmd_cancel(callback, state)