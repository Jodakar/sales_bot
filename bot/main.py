"""
VK Бот для управления продажами
Доступен только одному пользователю (администратору)
"""

import os
import logging
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
VK_TOKEN = os.getenv('VK_TOKEN')
GROUP_ID = int(os.getenv('VK_GROUP_ID', 0))
ADMIN_ID = int(os.getenv('VK_ADMIN_ID', 0))

# Проверка настройки
if not VK_TOKEN or not GROUP_ID or not ADMIN_ID:
    logger.error("Не настроены переменные окружения VK_TOKEN, VK_GROUP_ID, VK_ADMIN_ID")
    exit(1)


def get_main_keyboard():
    """Создаёт главную клавиатуру"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🛒 Новый заказ", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("📦 Заказы", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("📊 Товары", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("👥 Клиенты", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("📁 Отчеты", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("ℹ️ Помощь", color=VkKeyboardColor.SECONDARY)
    return keyboard


def send_message(vk, user_id, message, keyboard=None):
    """Отправляет сообщение пользователю"""
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=0,
            keyboard=keyboard.get_keyboard() if keyboard else None
        )
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения {user_id}: {e}")


def handle_start(vk, user_id):
    """Обработчик команды 'начать' или стартового сообщения"""
    welcome_text = (
        "👋 Привет! Я бот для управления продажами.\n\n"
        "📋 Доступные функции:\n"
        "🛒 Новый заказ — создать заказ\n"
        "📦 Заказы — просмотр и фильтрация заказов\n"
        "📊 Товары — просмотр и поиск товаров\n"
        "👥 Клиенты — история заказов по клиентам\n"
        "📁 Отчеты — Excel-выгрузки\n"
        "ℹ️ Помощь — это сообщение\n\n"
        "Выберите действие в меню ниже 👇"
    )
    send_message(vk, user_id, welcome_text, get_main_keyboard())


def handle_help(vk, user_id):
    """Обработчик команды 'помощь'"""
    help_text = (
        "ℹ️ *Помощь по боту*\n\n"
        "🛒 *Новый заказ* — создать заказ на основе разговора с клиентом\n"
        "📦 *Заказы* — просмотр заказов с фильтрацией по статусу и дате\n"
        "📊 *Товары* — поиск товаров, просмотр остатков, редактирование\n"
        "👥 *Клиенты* — история заказов по клиентам\n"
        "📁 *Отчеты* — Excel-выгрузки товаров, заказов, клиентов\n\n"
        "🔧 *Техническая информация*\n"
        "• Синхронизация с 1С: каждые 30 минут\n"
        "• Бэкапы PostgreSQL: ежедневно в 2:00\n"
        "• Все данные хранятся на флешке D:\\postgresql\\data\\\n\n"
        "По всем вопросам обращайтесь к разработчику."
    )
    send_message(vk, user_id, help_text, get_main_keyboard())


def main():
    """Запуск бота"""
    logger.info("Запуск VK бота...")
    logger.info(f"Группа ID: {GROUP_ID}")
    logger.info(f"Администратор ID: {ADMIN_ID}")
    
    # Авторизация
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    
    logger.info("Бот запущен. Ожидание сообщений...")
    
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                message = event.object.message
                user_id = message['from_id']
                
                # Проверяем, что сообщение от администратора
                if user_id != ADMIN_ID:
                    logger.warning(f"Попытка доступа от {user_id} (не администратор)")
                    send_message(vk, user_id, "⛔ Доступ запрещён. Бот доступен только администратору.")
                    continue
                
                text = message.get('text', '').strip()
                logger.info(f"Сообщение от {user_id}: {text}")
                
                # Обработка команд
                if text in ['начать', 'start', 'привет', 'старт']:
                    handle_start(vk, user_id)
                elif text in ['помощь', 'help', 'ℹ️ Помощь']:
                    handle_help(vk, user_id)
                elif text in ['🛒 Новый заказ', 'новый заказ']:
                    from handlers.orders import handle_new_order
                    handle_new_order(vk, user_id)
                elif text in ['📦 Заказы', 'заказы']:
                    from handlers.orders import handle_orders_list
                    handle_orders_list(vk, user_id)
                elif text in ['📊 Товары', 'товары']:
                    from handlers.products import handle_products_menu
                    handle_products_menu(vk, user_id)
                elif text in ['👥 Клиенты', 'клиенты']:
                    from handlers.customers import handle_customers_list
                    handle_customers_list(vk, user_id)
                elif text in ['📁 Отчеты', 'отчеты']:
                    from handlers.reports import handle_reports_menu
                    handle_reports_menu(vk, user_id)
                else:
                    send_message(vk, user_id, "Неизвестная команда. Нажмите на кнопку в меню.", get_main_keyboard())
                    
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка в основном цикле: {e}")
        raise


if __name__ == "__main__":
    main()