"""
Утилита для отправки сообщений
"""

import logging

logger = logging.getLogger(__name__)


def send_message(vk, user_id, message, keyboard=None):
    """Отправляет сообщение пользователю"""
    try:
        keyboard_json = keyboard.get_keyboard() if keyboard else None
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=0,
            keyboard=keyboard_json
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения {user_id}: {e}")
        return False