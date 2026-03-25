"""
Модуль отчётов и Excel-выгрузок
"""

import logging
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from bot.utils.send_message import send_message
from bot.utils.db import get_all_products, get_orders, get_all_customers, get_statistics
from bot.utils.excel import export_products, export_orders, export_customers

logger = logging.getLogger(__name__)


def get_reports_keyboard():
    """Клавиатура для отчётов"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("📦 Товары (Excel)", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("💰 Заказы (Excel)", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("👥 Клиенты (Excel)", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("📊 Статистика (Excel)", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🔙 Вернуться в меню", color=VkKeyboardColor.SECONDARY)
    return keyboard


def handle_reports_menu(vk, user_id):
    """Главное меню отчётов"""
    text = (
        "📊 *Отчёты и выгрузки*\n\n"
        "Выберите тип отчёта:\n"
        "📦 Товары (Excel) — полный каталог товаров\n"
        "💰 Заказы (Excel) — все заказы\n"
        "👥 Клиенты (Excel) — список клиентов\n"
        "📊 Статистика (Excel) — сводка по продажам\n\n"
        "Файлы сохраняются в папку: C:\\Users\\PC\\Yandex.Disk\\exports\\"
    )
    send_message(vk, user_id, text, get_reports_keyboard())


def handle_products_report(vk, user_id):
    """Выгрузка товаров в Excel"""
    send_message(vk, user_id, "🔄 Формирую отчёт по товарам...")
    
    products = get_all_products()
    if not products:
        send_message(vk, user_id, "❌ Нет данных о товарах", get_reports_keyboard())
        return
    
    filepath = export_products(products)
    if filepath:
        send_message(vk, user_id, f"✅ Отчёт по товарам сохранён:\n{filepath}\n\nОткройте файл в папке 'Экспорт'")
    else:
        send_message(vk, user_id, "❌ Ошибка при создании отчёта", get_reports_keyboard())


def handle_orders_report(vk, user_id):
    """Выгрузка заказов в Excel"""
    send_message(vk, user_id, "🔄 Формирую отчёт по заказам...")
    
    orders = get_orders()
    if not orders:
        send_message(vk, user_id, "❌ Нет данных о заказах", get_reports_keyboard())
        return
    
    filepath = export_orders(orders)
    if filepath:
        send_message(vk, user_id, f"✅ Отчёт по заказам сохранён:\n{filepath}")
    else:
        send_message(vk, user_id, "❌ Ошибка при создании отчёта", get_reports_keyboard())


def handle_customers_report(vk, user_id):
    """Выгрузка клиентов в Excel"""
    send_message(vk, user_id, "🔄 Формирую отчёт по клиентам...")
    
    customers = get_all_customers()
    if not customers:
        send_message(vk, user_id, "❌ Нет данных о клиентах", get_reports_keyboard())
        return
    
    filepath = export_customers(customers)
    if filepath:
        send_message(vk, user_id, f"✅ Отчёт по клиентам сохранён:\n{filepath}")
    else:
        send_message(vk, user_id, "❌ Ошибка при создании отчёта", get_reports_keyboard())


def handle_statistics_report(vk, user_id):
    """Выгрузка статистики в Excel"""
    send_message(vk, user_id, "🔄 Формирую статистику...")
    
    stats = get_statistics()
    if not stats:
        send_message(vk, user_id, "❌ Нет данных для статистики", get_reports_keyboard())
        return
    
    # Создаём простой Excel со статистикой
    import pandas as pd
    from datetime import datetime
    import os
    
    # Преобразуем в список словарей для pandas
    data = [{
        'Всего заказов': stats.get('total_orders', 0),
        'Общая сумма продаж': stats.get('total_sales', 0),
        'Средний чек': stats.get('avg_order', 0),
        'Оплаченные заказы': stats.get('paid_orders', 0),
        'Доставленные заказы': stats.get('delivered_orders', 0)
    }]
    
    df = pd.DataFrame(data)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exports_path = os.getenv('EXPORTS_PATH', r'C:\Users\PC\Yandex.Disk\exports')
    os.makedirs(exports_path, exist_ok=True)
    
    filepath = os.path.join(exports_path, f"statistics_{timestamp}.xlsx")
    df.to_excel(filepath, index=False)
    
    send_message(vk, user_id, f"✅ Статистика сохранена:\n{filepath}")


def handle_reports_action(vk, user_id, text):
    """Обработчик действий с отчётами"""
    if text == "📦 Товары (Excel)":
        handle_products_report(vk, user_id)
    elif text == "💰 Заказы (Excel)":
        handle_orders_report(vk, user_id)
    elif text == "👥 Клиенты (Excel)":
        handle_customers_report(vk, user_id)
    elif text == "📊 Статистика (Excel)":
        handle_statistics_report(vk, user_id)
    elif text == "🔙 Вернуться в меню":
        from bot.handlers.menu import show_main_menu
        show_main_menu(vk, user_id)
    
    return None