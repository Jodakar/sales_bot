"""
Модуль главного меню
"""

import logging
from bot.main import send_message, get_main_keyboard

logger = logging.getLogger(__name__)


def show_main_menu(vk, user_id):
    """Показывает главное меню"""
    welcome_text = (
        "👋 Главное меню\n\n"
        "📋 Доступные функции:\n"
        "🛒 Новый заказ — создать заказ\n"
        "📦 Заказы — просмотр и фильтрация заказов\n"
        "📊 Товары — просмотр и поиск товаров\n"
        "👥 Клиенты — история заказов по клиентам\n"
        "📁 Отчеты — Excel-выгрузки\n"
        "ℹ️ Помощь — информация\n\n"
        "👇 Выберите действие"
    )
    send_message(vk, user_id, welcome_text, get_main_keyboard())