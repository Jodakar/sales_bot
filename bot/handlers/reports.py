"""Обработчики отчётов (временная заглушка)"""
import logging
from bot.main import send_message

logger = logging.getLogger(__name__)

def handle_reports_menu(vk, user_id):
    send_message(vk, user_id, "📁 Функция 'Отчеты' в разработке. Скоро будет доступна!")