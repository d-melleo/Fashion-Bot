"""
Inline Keyboards для Telegram Bot
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ========================================
# MAIN MENU
# ========================================

def get_main_menu_keyboard(has_subscription: bool = False, is_stylist: bool = False) -> InlineKeyboardMarkup:
    """Головне меню користувача"""
    builder = InlineKeyboardBuilder()
    
    # Основні функції
    builder.row(
        InlineKeyboardButton(text="👔 Згенерувати образ", callback_data="generate_outfit")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Мій профіль", callback_data="view_profile"),
        InlineKeyboardButton(text="📜 Історія", callback_data="view_history")
    )
    
    # Підписка
    if has_subscription:
        builder.row(
            InlineKeyboardButton(text="✅ Підписка активна", callback_data="subscription_info")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="💳 Оформити підписку", callback_data="subscribe")
        )
    
    # Стиліст
    builder.row(
        InlineKeyboardButton(text="👨‍💼 Запит стиліста", callback_data="request_stylist")
    )
    
    # Web App
    builder.row(
        InlineKeyboardButton(text="🛍️ Каталог одягу", web_app={"url": "https://your-webapp-url.com"})
    )
    
    # Для стилістів
    if is_stylist:
        builder.row(
            InlineKeyboardButton(text="📋 Запити клієнтів", callback_data="stylist_requests")
        )
    
    return builder.as_markup()


# ========================================
# BODY TYPE SELECTION
# ========================================

def get_body_type_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура вибору типу фігури"""
    builder = InlineKeyboardBuilder()
    
    body_types = [
        ("Стрункий", "slim"),
        ("Атлетичний", "athletic"),
        ("Середній", "average"),
        ("Пишний", "curvy"),
        ("Plus Size", "plus_size")
    ]
    
    for text, callback in body_types:
        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"body_type:{callback}")
        )
    
    return builder.as_markup()


# ========================================
# STYLE PREFERENCES
# ========================================

def get_style_preferences_keyboard(selected: list = None) -> InlineKeyboardMarkup:
    """Клавіатура вибору стилю (множинний вибір)"""
    selected = selected or []
    builder = InlineKeyboardBuilder()
    
    styles = [
        ("Casual 👕", "casual"),
        ("Business 👔", "business"),
        ("Sport 🏃", "sport"),
        ("Street 🛹", "street"),
        ("Elegant 🎩", "elegant")
    ]
    
    for text, callback in styles:
        check = "✅ " if callback in selected else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{check}{text}",
                callback_data=f"style:{callback}"
            )
        )
    
    # Кнопка підтвердження
    if selected:
        builder.row(
            InlineKeyboardButton(text="✔️ Підтвердити", callback_data="style:confirm")
        )
    
    return builder.as_markup()


# ========================================
# SEASON SELECTION
# ========================================

def get_season_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура вибору пори року"""
    builder = InlineKeyboardBuilder()
    
    seasons = [
        ("🌸 Весна", "spring"),
        ("☀️ Літо", "summer"),
        ("🍂 Осінь", "autumn"),
        ("❄️ Зима", "winter")
    ]
    
    for text, callback in seasons:
        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"season:{callback}")
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


# ========================================
# PROFILE EDIT MENU
# ========================================

def get_profile_edit_keyboard() -> InlineKeyboardMarkup:
    """Меню редагування профілю"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📏 Змінити зріст", callback_data="edit:height"),
        InlineKeyboardButton(text="⚖️ Змінити вагу", callback_data="edit:weight")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Тип фігури", callback_data="edit:body_type"),
        InlineKeyboardButton(text="👔 Стиль", callback_data="edit:style")
    )
    builder.row(
        InlineKeyboardButton(text="📸 Змінити фото", callback_data="edit:photo")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад до меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


# ========================================
# GENERATION CONFIRMATION
# ========================================

def get_generation_confirm_keyboard(season: str) -> InlineKeyboardMarkup:
    """Підтвердження генерації"""
    builder = InlineKeyboardBuilder()
    
    season_emoji = {
        "spring": "🌸",
        "summer": "☀️",
        "autumn": "🍂",
        "winter": "❄️"
    }
    
    builder.row(
        InlineKeyboardButton(
            text=f"✅ Згенерувати для {season_emoji.get(season, '')}",
            callback_data=f"confirm_gen:{season}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обрати іншу пору", callback_data="generate_outfit"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


# ========================================
# SUBSCRIPTION
# ========================================

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура підписки"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💳 Оплатити $10/місяць", callback_data="pay_subscription")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Детальніше про підписку", callback_data="subscription_info")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


def get_payment_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    """Клавіатура з посиланням на оплату"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💳 Оплатити зараз", url=payment_url)
    )
    builder.row(
        InlineKeyboardButton(text="✅ Я оплатив", callback_data="check_payment")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Скасувати", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


# ========================================
# STYLIST REQUEST
# ========================================

def get_stylist_request_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура запиту стиліста"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✉️ Надіслати запит", callback_data="send_stylist_request")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


def get_stylist_accept_keyboard(user_id: int, request_id: str) -> InlineKeyboardMarkup:
    """Клавіатура для стиліста - прийняти запит"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Прийняти запит", callback_data=f"accept_request:{request_id}")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Переглянути профіль", callback_data=f"view_client:{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Відхилити", callback_data=f"decline_request:{request_id}")
    )
    
    return builder.as_markup()


# ========================================
# HISTORY NAVIGATION
# ========================================

def get_history_navigation_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Навігація по історії генерацій"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки навігації
    nav_buttons = []
    
    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Попередня", callback_data=f"history_page:{current_page-1}")
        )
    
    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="Наступна ➡️", callback_data=f"history_page:{current_page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад до меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


# ========================================
# ADMIN KEYBOARDS
# ========================================

def get_admin_menu_keyboard(role: str) -> InlineKeyboardMarkup:
    """Меню адміністратора"""
    builder = InlineKeyboardBuilder()
    
    if role in ['stylist', 'supervisor', 'owner']:
        builder.row(
            InlineKeyboardButton(text="📋 Запити клієнтів", callback_data="stylist_requests")
        )
    
    if role in ['supervisor', 'owner']:
        builder.row(
            InlineKeyboardButton(text="👥 Керування стилістами", callback_data="manage_stylists"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="view_statistics")
        )
        builder.row(
            InlineKeyboardButton(text="🚫 Заблокувати користувача", callback_data="block_user")
        )
    
    if role == 'owner':
        builder.row(
            InlineKeyboardButton(text="👑 Керування адмінами", callback_data="manage_admins"),
            InlineKeyboardButton(text="🤖 Налаштування AI", callback_data="ai_settings")
        )
        builder.row(
            InlineKeyboardButton(text="💳 Керування підписками", callback_data="manage_subscriptions")
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Головне меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


# ========================================
# CONFIRMATION KEYBOARDS
# ========================================

def get_confirmation_keyboard(action: str, data: str = "") -> InlineKeyboardMarkup:
    """Універсальна клавіатура підтвердження"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Так, підтверджую", callback_data=f"confirm:{action}:{data}"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_action")
    )
    
    return builder.as_markup()


# ========================================
# BACK BUTTON
# ========================================

def get_back_button(callback: str = "back_to_menu") -> InlineKeyboardMarkup:
    """Проста кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=callback)
    )
    return builder.as_markup()


# ========================================
# CANCEL BUTTON
# ========================================

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка скасування"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel")
    )
    return builder.as_markup()