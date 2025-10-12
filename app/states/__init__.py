"""
State Machine для Telegram Bot - Індивідуальний підбір одягу
Всі можливі стани бота організовані в групи
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Стани реєстрації та створення профілю"""
    awaiting_height = State()
    awaiting_weight = State()
    awaiting_body_type = State()
    awaiting_style = State()
    awaiting_photo = State()


class ProfileEditStates(StatesGroup):
    """Стани редагування профілю"""
    edit_menu = State()
    edit_height = State()
    edit_weight = State()
    edit_body_type = State()
    edit_style = State()
    edit_photo = State()
    confirm_changes = State()


class GenerationStates(StatesGroup):
    """Стани генерації образу одягу"""
    select_season = State()
    confirm_generation = State()
    processing = State()
    show_result = State()


class PaymentStates(StatesGroup):
    """Стани оплати підписки"""
    subscription_info = State()
    confirm_payment = State()
    awaiting_payment = State()
    payment_processing = State()


class StylistRequestStates(StatesGroup):
    """Стани запиту стиліста"""
    awaiting_message = State()
    confirm_request = State()
    request_sent = State()


class AdminStates(StatesGroup):
    """Стани адміністрування - Supervisor/Owner"""
    # Управління стилістами
    add_stylist_awaiting_id = State()
    add_stylist_confirm = State()
    remove_stylist_awaiting_id = State()
    remove_stylist_confirm = State()
    
    # Управління супервайзерами (тільки Owner)
    add_supervisor_awaiting_id = State()
    add_supervisor_confirm = State()
    remove_supervisor_awaiting_id = State()
    remove_supervisor_confirm = State()
    
    # Управління користувачами
    block_user_awaiting_id = State()
    block_user_confirm = State()
    unblock_user_awaiting_id = State()
    unblock_user_confirm = State()
    
    # Управління підписками (Owner)
    manage_subscription_awaiting_user_id = State()
    manage_subscription_menu = State()
    manage_subscription_duration = State()
    manage_subscription_confirm = State()
    
    # Налаштування AI (Owner)
    ai_settings_menu = State()
    ai_settings_select_provider = State()
    ai_settings_configure = State()
    ai_settings_api_key = State()
    ai_settings_confirm = State()


class StylistStates(StatesGroup):
    """Стани для стиліста при роботі з клієнтами"""
    view_requests = State()
    view_client_profile = State()
    accept_request = State()


# Допоміжні функції для роботи зі станами

def get_all_states() -> list:
    """Отримати всі стани бота"""
    return [
        RegistrationStates,
        ProfileEditStates,
        GenerationStates,
        PaymentStates,
        StylistRequestStates,
        AdminStates,
        StylistStates,
    ]


def get_user_states() -> list:
    """Отримати стани доступні звичайним користувачам"""
    return [
        RegistrationStates,
        ProfileEditStates,
        GenerationStates,
        PaymentStates,
        StylistRequestStates,
    ]


def get_stylist_states() -> list:
    """Отримати стани доступні стилістам"""
    return get_user_states() + [StylistStates]


def get_admin_states() -> list:
    """Отримати всі можливі стани"""
    return get_all_states()


# Експорт для зручного імпорту
__all__ = [
    'RegistrationStates',
    'ProfileEditStates',
    'GenerationStates',
    'PaymentStates',
    'StylistRequestStates',
    'AdminStates',
    'StylistStates',
    'get_all_states',
    'get_user_states',
    'get_stylist_states',
    'get_admin_states',
]