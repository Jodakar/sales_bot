"""Обработчики клиентов (временная заглушка)"""
import logging
from bot.main import send_message

logger = logging.getLogger(__name__)

def handle_customers_list(vk, user_id):
    send_message(vk, user_id, "👥 Функция 'Клиенты' в разработке. Скоро будет доступна!")