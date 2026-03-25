"""Обработчики заказов (временная заглушка)"""
import logging
from bot.main import send_message

logger = logging.getLogger(__name__)

def handle_new_order(vk, user_id):
    send_message(vk, user_id, "🛒 Функция 'Новый заказ' в разработке. Скоро будет доступна!")

def handle_orders_list(vk, user_id):
    send_message(vk, user_id, "📦 Функция 'Заказы' в разработке. Скоро будет доступна!")