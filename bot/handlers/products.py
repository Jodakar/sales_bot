"""
Модуль управления товарами
"""

import logging
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from bot.main import send_message
from bot.utils.db import get_all_products, get_product_by_id, search_products, update_product
from bot.utils.excel import export_products

logger = logging.getLogger(__name__)


def get_products_keyboard():
    """Клавиатура для управления товарами"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🔍 Поиск по ID", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🔎 Поиск по названию", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("📋 Весь каталог (Excel)", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🔄 Обновить данные из 1С", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("🔙 Вернуться в меню", color=VkKeyboardColor.SECONDARY)
    return keyboard


def get_product_detail_keyboard(product_id):
    """Клавиатура для деталей товара"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("✏️ Редактировать цену", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("📦 Редактировать остаток", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🔙 К списку товаров", color=VkKeyboardColor.SECONDARY)
    return keyboard


def format_product(product):
    """Форматирует товар для отображения"""
    product_text = f"""
🛍️ *{product['name']}*
━━━━━━━━━━━━━━━━━━━━━━
💰 Цена: {product['price']} ₽
📦 Остаток: {product['stock']} шт.
📂 Категория: {product.get('category', 'Не указана')}
📝 Описание: {product.get('description', 'Нет описания')}
🆔 ID товара: {product['id']}
━━━━━━━━━━━━━━━━━━━━━━
"""
    return product_text


def handle_products_menu(vk, user_id):
    """Главное меню товаров"""
    text = (
        "📊 *Управление товарами*\n\n"
        "Выберите действие:\n"
        "🔍 Поиск по ID — найти товар по номеру\n"
        "🔎 Поиск по названию — найти по ключевым словам\n"
        "📋 Весь каталог (Excel) — выгрузить в Excel\n"
        "🔄 Обновить данные из 1С — синхронизировать с 1С\n\n"
        "Для поиска введите ID или название товара"
    )
    send_message(vk, user_id, text, get_products_keyboard())


def handle_search_by_id(vk, user_id, product_id):
    """Поиск товара по ID"""
    try:
        pid = int(product_id)
        product = get_product_by_id(pid)
        
        if product:
            product_text = format_product(product)
            send_message(vk, user_id, product_text, get_product_detail_keyboard(pid))
        else:
            send_message(vk, user_id, f"❌ Товар с ID {pid} не найден", get_products_keyboard())
    except ValueError:
        send_message(vk, user_id, "❌ Неверный формат ID. Введите число.", get_products_keyboard())


def handle_search_by_name(vk, user_id, query):
    """Поиск товаров по названию"""
    products = search_products(query)
    
    if not products:
        send_message(vk, user_id, f"🔍 По запросу '{query}' ничего не найдено", get_products_keyboard())
        return
    
    # Формируем список товаров
    products_text = f"🔍 *Результаты поиска по запросу '{query}':*\n\n"
    for p in products[:10]:
        products_text += f"🆔 {p['id']} | {p['name']} | {p['price']} ₽ | в наличии: {p['stock']}\n"
    
    if len(products) > 10:
        products_text += f"\n... и ещё {len(products) - 10} товаров"
    
    products_text += "\n\n💡 Введите ID товара для просмотра деталей"
    
    send_message(vk, user_id, products_text, get_products_keyboard())


def handle_show_all_products(vk, user_id):
    """Показывает все товары (Excel)"""
    products = get_all_products()
    
    if not products:
        send_message(vk, user_id, "📭 Каталог пуст", get_products_keyboard())
        return
    
    # Формируем Excel
    filepath = export_products(products)
    
    if filepath:
        # В ВК нельзя отправить файл напрямую через бота, только ссылку
        # Отправляем ссылку на Яндекс.Диск (нужно настроить)
        send_message(vk, user_id, f"📊 Каталог товаров сохранён:\n{filepath}\n\nОткройте файл в папке 'Экспорт'")
    else:
        send_message(vk, user_id, "❌ Ошибка при создании Excel-файла", get_products_keyboard())


def handle_update_price(vk, user_id, product_id, new_price):
    """Обновляет цену товара"""
    try:
        pid = int(product_id)
        price = float(new_price.replace(',', '.'))
        
        success = update_product(pid, price=price)
        
        if success:
            product = get_product_by_id(pid)
            send_message(vk, user_id, f"✅ Цена товара '{product['name']}' обновлена: {price} ₽")
            handle_search_by_id(vk, user_id, pid)
        else:
            send_message(vk, user_id, f"❌ Ошибка обновления цены товара {pid}")
    except ValueError:
        send_message(vk, user_id, "❌ Неверный формат цены. Введите число (например, 1000 или 1999.99)")


def handle_update_stock(vk, user_id, product_id, new_stock):
    """Обновляет остаток товара"""
    try:
        pid = int(product_id)
        stock = int(new_stock)
        
        if stock < 0:
            send_message(vk, user_id, "❌ Остаток не может быть отрицательным")
            return
        
        success = update_product(pid, stock=stock)
        
        if success:
            product = get_product_by_id(pid)
            send_message(vk, user_id, f"✅ Остаток товара '{product['name']}' обновлён: {stock} шт.")
            handle_search_by_id(vk, user_id, pid)
        else:
            send_message(vk, user_id, f"❌ Ошибка обновления остатка товара {pid}")
    except ValueError:
        send_message(vk, user_id, "❌ Неверный формат количества. Введите целое число.")


def handle_products_action(vk, user_id, text, current_product=None):
    """Обработчик действий с товарами"""
    
    if text == "🔍 Поиск по ID":
        send_message(vk, user_id, "🔍 Введите ID товара:")
        return "waiting_product_id"
    
    elif text == "🔎 Поиск по названию":
        send_message(vk, user_id, "🔎 Введите название товара (или часть названия):")
        return "waiting_product_name"
    
    elif text == "📋 Весь каталог (Excel)":
        handle_show_all_products(vk, user_id)
        return None
    
    elif text == "🔄 Обновить данные из 1С":
        send_message(vk, user_id, "🔄 Синхронизация с 1С запущена. Это может занять несколько минут.")
        # Здесь будет вызов модуля синхронизации
        return None
    
    elif text == "✏️ Редактировать цену" and current_product:
        send_message(vk, user_id, f"💰 Введите новую цену для товара (текущая: {current_product['price']} ₽):")
        return "waiting_new_price"
    
    elif text == "📦 Редактировать остаток" and current_product:
        send_message(vk, user_id, f"📦 Введите новый остаток для товара (текущий: {current_product['stock']} шт.):")
        return "waiting_new_stock"
    
    elif text == "🔙 К списку товаров":
        handle_products_menu(vk, user_id)
        return None
    
    elif text == "🔙 Вернуться в меню":
        from bot.handlers.menu import show_main_menu
        show_main_menu(vk, user_id)
        return None
    
    return None