"""
Модуль управления заказами
"""

import logging
from datetime import datetime
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from bot.main import send_message
from bot.utils.db import get_orders, get_order_by_id, update_order_status, delete_order, create_order
from bot.handlers.cart import get_cart, format_cart, clear_cart

logger = logging.getLogger(__name__)


def get_orders_keyboard():
    """Клавиатура для списка заказов"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("📊 Все заказы", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("💰 Не оплачены", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("📦 Оплачены", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("✅ Доставлены", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("🔙 Вернуться в меню", color=VkKeyboardColor.SECONDARY)
    return keyboard


def format_order(order):
    """Форматирует заказ для отображения"""
    items_text = []
    for item in order.get('items', []):
        items_text.append(f"  • {item['product_name']} x{item['quantity']} = {item['total']} ₽")
    
    order_text = f"""
📦 *Заказ #{order['id']}*
━━━━━━━━━━━━━━━━━━━━━━
👤 Клиент: {order['customer_name']}
📞 Телефон: {order.get('customer_phone', 'Не указан')}
📍 Адрес: {order.get('customer_address', 'Не указан')}
📝 Комментарий: {order.get('comment', 'Нет')}
🚚 Доставка: {order.get('delivery_method', 'Не указана')}
🕐 Время: {order.get('delivery_time', 'Не указано')}
━━━━━━━━━━━━━━━━━━━━━━
🛍️ *Товары:*
{chr(10).join(items_text) if items_text else '  Нет товаров'}
━━━━━━━━━━━━━━━━━━━━━━
💰 *Итого: {order['total_amount']} ₽*
📅 Создан: {order['created_at'].strftime('%d.%m.%Y %H:%M')}
📊 Статус: {get_status_emoji(order['status'])} {order['status']}
"""
    return order_text


def get_status_emoji(status):
    """Возвращает эмодзи для статуса"""
    emojis = {
        'not_paid': '🟡',
        'paid': '🟢',
        'delivered': '✅'
    }
    return emojis.get(status, '⚪')


def get_order_detail_keyboard(order_id, status):
    """Клавиатура для деталей заказа"""
    keyboard = VkKeyboard(one_time=False)
    
    # Кнопки изменения статуса
    if status == 'not_paid':
        keyboard.add_button("🟢 Отметить оплаченным", color=VkKeyboardColor.POSITIVE)
    elif status == 'paid':
        keyboard.add_button("✅ Отметить доставленным", color=VkKeyboardColor.POSITIVE)
    
    keyboard.add_line()
    keyboard.add_button("🗑️ Удалить заказ", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("🔙 К списку заказов", color=VkKeyboardColor.SECONDARY)
    
    return keyboard


def handle_orders_list(vk, user_id):
    """Показывает список заказов"""
    orders = get_orders()
    
    if not orders:
        send_message(vk, user_id, "📭 Нет заказов", get_orders_keyboard())
        return
    
    # Формируем краткий список
    orders_text = "📋 *Список заказов:*\n\n"
    for order in orders[:10]:  # Показываем последние 10
        orders_text += f"{get_status_emoji(order['status'])} #{order['id']} | {order['customer_name']} | {order['total_amount']} ₽\n"
    
    if len(orders) > 10:
        orders_text += f"\n... и ещё {len(orders) - 10} заказов"
    
    orders_text += "\n\n🔍 Введите номер заказа для просмотра деталей"
    
    send_message(vk, user_id, orders_text, get_orders_keyboard())


def handle_order_detail(vk, user_id, order_id):
    """Показывает детали заказа"""
    try:
        order_id = int(order_id)
        order = get_order_by_id(order_id)
        
        if not order:
            send_message(vk, user_id, f"❌ Заказ #{order_id} не найден")
            return
        
        order_text = format_order(order)
        send_message(vk, user_id, order_text, get_order_detail_keyboard(order_id, order['status']))
        
    except ValueError:
        send_message(vk, user_id, "❌ Неверный формат номера заказа")


def handle_order_action(vk, user_id, text, order_id=None):
    """Обработчик действий с заказом"""
    if text == "📊 Все заказы":
        orders = get_orders()
        handle_orders_list(vk, user_id)
    
    elif text == "💰 Не оплачены":
        orders = get_orders({'status': 'not_paid'})
        if orders:
            orders_text = "📋 *Не оплаченные заказы:*\n\n"
            for order in orders:
                orders_text += f"{get_status_emoji(order['status'])} #{order['id']} | {order['customer_name']} | {order['total_amount']} ₽\n"
            send_message(vk, user_id, orders_text, get_orders_keyboard())
        else:
            send_message(vk, user_id, "✅ Нет не оплаченных заказов", get_orders_keyboard())
    
    elif text == "📦 Оплачены":
        orders = get_orders({'status': 'paid'})
        if orders:
            orders_text = "📋 *Оплаченные заказы (ждут доставки):*\n\n"
            for order in orders:
                orders_text += f"{get_status_emoji(order['status'])} #{order['id']} | {order['customer_name']} | {order['total_amount']} ₽\n"
            send_message(vk, user_id, orders_text, get_orders_keyboard())
        else:
            send_message(vk, user_id, "📭 Нет оплаченных заказов", get_orders_keyboard())
    
    elif text == "✅ Доставлены":
        orders = get_orders({'status': 'delivered'})
        if orders:
            orders_text = "📋 *Доставленные заказы:*\n\n"
            for order in orders:
                orders_text += f"{get_status_emoji(order['status'])} #{order['id']} | {order['customer_name']} | {order['total_amount']} ₽\n"
            send_message(vk, user_id, orders_text, get_orders_keyboard())
        else:
            send_message(vk, user_id, "📭 Нет доставленных заказов", get_orders_keyboard())
    
    elif text == "🟢 Отметить оплаченным" and order_id:
        success = update_order_status(order_id, 'paid')
        if success:
            send_message(vk, user_id, f"✅ Заказ #{order_id} отмечен как оплаченный")
            handle_order_detail(vk, user_id, order_id)
        else:
            send_message(vk, user_id, f"❌ Ошибка обновления статуса заказа #{order_id}")
    
    elif text == "✅ Отметить доставленным" and order_id:
        success = update_order_status(order_id, 'delivered')
        if success:
            send_message(vk, user_id, f"✅ Заказ #{order_id} отмечен как доставленный")
            handle_order_detail(vk, user_id, order_id)
        else:
            send_message(vk, user_id, f"❌ Ошибка обновления статуса заказа #{order_id}")
    
    elif text == "🗑️ Удалить заказ" and order_id:
        success = delete_order(order_id)
        if success:
            send_message(vk, user_id, f"🗑️ Заказ #{order_id} удалён")
            handle_orders_list(vk, user_id)
        else:
            send_message(vk, user_id, f"❌ Ошибка удаления заказа #{order_id}")
    
    elif text == "🔙 К списку заказов":
        handle_orders_list(vk, user_id)
    
    elif text == "🔙 Вернуться в меню":
        from bot.handlers.menu import show_main_menu
        show_main_menu(vk, user_id)


def create_order_from_cart(vk, user_id, customer_name, customer_phone, customer_address, comment):
    """Создаёт заказ из корзины"""
    cart = get_cart(user_id)
    if not cart:
        send_message(vk, user_id, "❌ Корзина пуста")
        return False
    
    # Подготавливаем позиции для БД
    items = []
    for item in cart:
        items.append({
            'product_id': item['product_id'],
            'product_name': item['name'],
            'quantity': item['quantity'],
            'price': item['price']
        })
    
    # Создаём заказ
    order_id = create_order(
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address,
        comment=comment,
        delivery_method='Не указан',
        delivery_time=None,
        items=items
    )
    
    if order_id:
        # Очищаем корзину
        clear_cart(user_id)
        send_message(vk, user_id, f"✅ Заказ #{order_id} успешно создан!")
        return True
    else:
        send_message(vk, user_id, "❌ Ошибка создания заказа")
        return False