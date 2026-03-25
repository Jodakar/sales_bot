"""
VK Бот для управления продажами
Доступен только одному пользователю (администратору)
"""

import os
import sys
import io
import logging
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from dotenv import load_dotenv

# Импорты из наших модулей
from bot.keyboards import get_main_keyboard
from bot.utils.send_message import send_message
from bot.handlers.menu import show_main_menu

# Принудительно устанавливаем UTF-8 для вывода
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
VK_TOKEN = os.getenv('VK_TOKEN')
GROUP_ID = int(os.getenv('VK_GROUP_ID', 0))
ADMIN_ID = int(os.getenv('VK_ADMIN_ID', 0))

# Хранилище состояний пользователей (временное)
user_states = {}

# Проверка настройки
if not VK_TOKEN or not GROUP_ID or not ADMIN_ID:
    logger.error("Не настроены переменные окружения VK_TOKEN, VK_GROUP_ID, VK_ADMIN_ID")
    exit(1)


def get_main_keyboard():
    """Создаёт главную клавиатуру"""
    from vk_api.keyboard import VkKeyboard, VkKeyboardColor
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
        "👇 Выберите действие в меню ниже"
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


def handle_unknown(vk, user_id):
    """Обработчик неизвестной команды"""
    unknown_text = (
        "❓ Неизвестная команда.\n\n"
        "Пожалуйста, используйте кнопки меню для навигации.\n"
        "Или напишите 'Привет' для отображения главного меню."
    )
    send_message(vk, user_id, unknown_text, get_main_keyboard())


def main():
    """Запуск бота"""
    logger.info("=" * 50)
    logger.info("Запуск VK бота для управления продажами")
    logger.info(f"Группа ID: {GROUP_ID}")
    logger.info(f"Администратор ID: {ADMIN_ID}")
    logger.info("=" * 50)
    
    # Авторизация
    try:
        vk_session = vk_api.VkApi(token=VK_TOKEN)
        vk = vk_session.get_api()
        longpoll = VkBotLongPoll(vk_session, GROUP_ID)
        logger.info("✅ Бот успешно авторизован")
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации: {e}")
        return
    
    logger.info("🚀 Бот запущен. Ожидание сообщений...")
    
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                message = event.object.message
                user_id = message['from_id']
                
                # Проверяем, что сообщение от администратора
                if user_id != ADMIN_ID:
                    logger.warning(f"⚠️ Попытка доступа от {user_id} (не администратор)")
                    send_message(vk, user_id, "⛔ Доступ запрещён. Бот доступен только администратору.")
                    continue
                
                text = message.get('text', '').strip().lower()
                logger.info(f"📨 Сообщение от {user_id}: {text}")
                
                # Обработка состояний (ожидание ввода от пользователя)
                if user_id in user_states:
                    state = user_states[user_id]
                    logger.info(f"📌 Состояние {user_id}: {state}")
                    
                    if state == "waiting_product_id":
                        from bot.handlers.products import handle_search_by_id
                        handle_search_by_id(vk, user_id, text)
                        del user_states[user_id]
                    
                    elif state == "waiting_product_name":
                        from bot.handlers.products import handle_search_by_name
                        handle_search_by_name(vk, user_id, text)
                        del user_states[user_id]
                    
                    elif state == "waiting_new_price":
                        from bot.handlers.products import handle_update_price
                        current_product = user_states.get(f"{user_id}_product")
                        if current_product:
                            handle_update_price(vk, user_id, current_product['id'], text)
                        del user_states[user_id]
                        if f"{user_id}_product" in user_states:
                            del user_states[f"{user_id}_product"]
                    
                    elif state == "waiting_new_stock":
                        from bot.handlers.products import handle_update_stock
                        current_product = user_states.get(f"{user_id}_product")
                        if current_product:
                            handle_update_stock(vk, user_id, current_product['id'], text)
                        del user_states[user_id]
                        if f"{user_id}_product" in user_states:
                            del user_states[f"{user_id}_product"]
                    
                    elif state == "waiting_order_id":
                        from bot.handlers.orders import handle_order_detail
                        handle_order_detail(vk, user_id, text)
                        del user_states[user_id]
                    
                    elif state == "waiting_customer_phone":
                        from bot.handlers.customers import handle_customer_by_phone
                        handle_customer_by_phone(vk, user_id, text)
                        del user_states[user_id]
                    
                    elif state == "waiting_customer_id":
                        from bot.handlers.customers import handle_customer_detail
                        handle_customer_detail(vk, user_id, text)
                        del user_states[user_id]
                    
                    else:
                        # Неизвестное состояние
                        del user_states[user_id]
                        send_message(vk, user_id, "❓ Действие отменено. Начните с главного меню.", get_main_keyboard())
                    
                    continue
                
                # Обработка команд
                if text in ['начать', 'start', 'привет', 'старт', 'меню', 'главное меню']:
                    handle_start(vk, user_id)
                elif text in ['помощь', 'help', 'ℹ️ помощь', '?']:
                    handle_help(vk, user_id)
                elif text in ['🛒 новый заказ', 'новый заказ', 'заказ']:
                    try:
                        from bot.handlers.orders import handle_new_order
                        handle_new_order(vk, user_id)
                    except ImportError:
                        send_message(vk, user_id, "🔄 Функция 'Новый заказ' в разработке. Скоро будет доступна!", get_main_keyboard())
                elif text in ['📦 заказы', 'заказы', 'список заказов']:
                    try:
                        from bot.handlers.orders import handle_orders_list
                        handle_orders_list(vk, user_id)
                    except ImportError:
                        send_message(vk, user_id, "🔄 Функция 'Заказы' в разработке. Скоро будет доступна!", get_main_keyboard())
                elif text in ['📊 товары', 'товары', 'каталог']:
                    try:
                        from bot.handlers.products import handle_products_menu
                        handle_products_menu(vk, user_id)
                    except ImportError:
                        send_message(vk, user_id, "🔄 Функция 'Товары' в разработке. Скоро будет доступна!", get_main_keyboard())
                elif text in ['👥 клиенты', 'клиенты', 'покупатели']:
                    try:
                        from bot.handlers.customers import handle_customers_list
                        handle_customers_list(vk, user_id)
                    except ImportError:
                        send_message(vk, user_id, "🔄 Функция 'Клиенты' в разработке. Скоро будет доступна!", get_main_keyboard())
                elif text in ['📁 отчеты', 'отчеты', 'выгрузки', 'excel']:
                    try:
                        from bot.handlers.reports import handle_reports_menu
                        handle_reports_menu(vk, user_id)
                    except ImportError:
                        send_message(vk, user_id, "🔄 Функция 'Отчеты' в разработке. Скоро будет доступна!", get_main_keyboard())
                elif text.isdigit():
                    # Если ввели число — ищем заказ
                    user_states[user_id] = "waiting_order_id"
                    from bot.handlers.orders import handle_order_detail
                    handle_order_detail(vk, user_id, text)
                else:
                    handle_unknown(vk, user_id)
                    
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка в основном цикле: {e}")
        raise


if __name__ == "__main__":
    main()