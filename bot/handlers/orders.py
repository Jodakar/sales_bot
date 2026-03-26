"""
Модуль управления заказами
"""

import logging
from datetime import datetime
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from bot.main import send_message, user_states
from bot.utils.db import get_orders, get_order_by_id, update_order_status, delete_order, create_order, get_product_by_id, search_products
from bot.handlers.cart import format_cart, get_cart_keyboard

logger = logging.getLogger(__name__)

# Хранилище временных заказов (в памяти)
temp_orders = {}


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
        items_text.append(f"  • {item['product_name']} x{item['quantity']} = {item['price'] * item['quantity']} ₽")
    
    order_text = f"""
📦 *Заказ #{order['order_id']}*
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
    
    orders_text = "📋 *Список заказов:*\n\n"
    for order in orders[:10]:
        orders_text += f"{get_status_emoji(order['status'])} #{order['order_id']} | {order['customer_name']} | {order['total_amount']} ₽\n"
    
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
        handle_orders_list(vk, user_id)
    elif text == "💰 Не оплачены":
        orders = get_orders({'status': 'not_paid'})
        if orders:
            orders_text = "📋 *Не оплаченные заказы:*\n\n"
            for order in orders:
                orders_text += f"{get_status_emoji(order['status'])} #{order['order_id']} | {order['customer_name']} | {order['total_amount']} ₽\n"
            send_message(vk, user_id, orders_text, get_orders_keyboard())
        else:
            send_message(vk, user_id, "✅ Нет не оплаченных заказов", get_orders_keyboard())
    elif text == "📦 Оплачены":
        orders = get_orders({'status': 'paid'})
        if orders:
            orders_text = "📋 *Оплаченные заказы:*\n\n"
            for order in orders:
                orders_text += f"{get_status_emoji(order['status'])} #{order['order_id']} | {order['customer_name']} | {order['total_amount']} ₽\n"
            send_message(vk, user_id, orders_text, get_orders_keyboard())
        else:
            send_message(vk, user_id, "📭 Нет оплаченных заказов", get_orders_keyboard())
    elif text == "✅ Доставлены":
        orders = get_orders({'status': 'delivered'})
        if orders:
            orders_text = "📋 *Доставленные заказы:*\n\n"
            for order in orders:
                orders_text += f"{get_status_emoji(order['status'])} #{order['order_id']} | {order['customer_name']} | {order['total_amount']} ₽\n"
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


# =====================================================
# НОВЫЙ ЗАКАЗ (пошаговое создание)
# =====================================================

def handle_new_order(vk, user_id):
    """Начинает процесс создания нового заказа"""
    # Устанавливаем состояние
    user_states[user_id] = "new_order"
    
    temp_orders[user_id] = {
        'items': [],
        'step': 'product_id',
        'customer_name': None,
        'customer_phone': None,
        'customer_address': None,
        'comment': None
    }
    send_message(vk, user_id, "🛒 *Создание нового заказа*\n\nВведите ID товара (или название для поиска):")


def handle_new_order_step(vk, user_id, text):
    """Обрабатывает шаги создания заказа"""
    if user_id not in temp_orders:
        handle_new_order(vk, user_id)
        return
    
    order = temp_orders[user_id]
    step = order['step']
    
    if step == 'product_id':
        # Ищем товар по ID или названию
        product = None
        if text.isdigit():
            product = get_product_by_id(int(text))
        
        if not product:
            # Ищем по названию
            products = search_products(text)
            if len(products) == 1:
                product = products[0]
            elif len(products) > 1:
                # Показываем список
                msg = "🔍 *Найдено несколько товаров:*\n\n"
                for p in products[:5]:
                    msg += f"🆔 {p['product_id']} | {p['name']} | {p['price']} ₽ | остаток: {p['stock']}\n"
                msg += "\nВведите ID нужного товара:"
                send_message(vk, user_id, msg)
                return
            else:
                send_message(vk, user_id, "❌ Товар не найден. Введите ID или название:")
                return
        
        if product:
            order['current_product'] = product
            order['step'] = 'quantity'
            send_message(vk, user_id, f"🛍️ *{product['name']}*\n💰 Цена: {product['price']} ₽\n📦 Остаток: {product['stock']} шт.\n\nВведите количество:")
    
    elif step == 'quantity':
        try:
            quantity = int(text)
            if quantity <= 0:
                send_message(vk, user_id, "❌ Количество должно быть больше 0")
                return
            
            product = order['current_product']
            if product['stock'] < quantity:
                send_message(vk, user_id, f"❌ Недостаточно товара. В наличии: {product['stock']} шт.")
                return
            
            # Добавляем в корзину
            order['items'].append({
                'product_id': product['product_id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity
            })
            
            # Показываем корзину
            cart_text, total = format_cart(order['items'])
            keyboard = get_cart_keyboard()
            send_message(vk, user_id, f"✅ Товар добавлен!\n\n{cart_text}", keyboard)
            
            order['step'] = 'continue'
            order['current_product'] = None
            
        except ValueError:
            send_message(vk, user_id, "❌ Введите число (количество):")
    
    elif step == 'continue':
        if text == "➕ Добавить еще товар":
            order['step'] = 'product_id'
            send_message(vk, user_id, "🛒 Введите ID следующего товара:")
        elif text == "✅ Оформить заказ":
            order['step'] = 'customer_name'
            send_message(vk, user_id, "📝 Введите имя клиента:")
        elif text == "🗑️ Очистить корзину":
            order['items'] = []
            send_message(vk, user_id, "🛒 Корзина очищена. Введите ID товара:", get_cart_keyboard())
            order['step'] = 'product_id'
        elif text == "🔙 Вернуться в меню":
            del temp_orders[user_id]
            del user_states[user_id]
            from bot.handlers.menu import show_main_menu
            show_main_menu(vk, user_id)
    
    elif step == 'customer_name':
        order['customer_name'] = text
        order['step'] = 'customer_phone'
        send_message(vk, user_id, "📞 Введите телефон клиента (например, +7 925 123-45-67):")
    
    elif step == 'customer_phone':
        # Очищаем телефон от пробелов и тире
        cleaned_phone = text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        order['customer_phone'] = cleaned_phone
        order['step'] = 'customer_address'
        send_message(vk, user_id, "📍 Введите адрес доставки:")
    
    elif step == 'customer_address':
        order['customer_address'] = text
        order['step'] = 'comment'
        send_message(vk, user_id, "📝 Введите комментарий к заказу (способ доставки, время и т.п.):")
    
    elif step == 'comment':
        order['comment'] = text
        
        # Показываем итог
        cart_text, total = format_cart(order['items'])
        summary = f"""
📦 *ИТОГ ЗАКАЗА*
━━━━━━━━━━━━━━━━━━━━━━
{cart_text}

👤 Клиент: {order['customer_name']}
📞 Телефон: {order['customer_phone']}
📍 Адрес: {order['customer_address']}
📝 Комментарий: {order['comment']}
━━━━━━━━━━━━━━━━━━━━━━
✅ Подтвердите создание заказа
"""
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button("✅ Подтвердить", color=VkKeyboardColor.POSITIVE)
        keyboard.add_button("✏️ Редактировать", color=VkKeyboardColor.SECONDARY)
        keyboard.add_button("🔙 Отмена", color=VkKeyboardColor.NEGATIVE)
        
        send_message(vk, user_id, summary, keyboard)
        order['step'] = 'confirm'
    
    elif step == 'confirm':
        if text == "✅ Подтвердить":
            # Создаём заказ в БД
            items = []
            for item in order['items']:
                items.append({
                    'product_id': item['product_id'],
                    'product_name': item['name'],
                    'quantity': item['quantity'],
                    'price': item['price']
                })
            
            order_id = create_order(
                customer_name=order['customer_name'],
                customer_phone=order['customer_phone'],
                customer_address=order['customer_address'],
                comment=order['comment'],
                delivery_method=None,
                delivery_time=None,
                items=items
            )
            
            if order_id:
                send_message(vk, user_id, f"✅ *Заказ #{order_id} успешно создан!*\n\nБлагодарим за покупку!")
            else:
                send_message(vk, user_id, "❌ Ошибка при создании заказа")
            
            del temp_orders[user_id]
            del user_states[user_id]
            from bot.handlers.menu import show_main_menu
            show_main_menu(vk, user_id)
            
        elif text == "✏️ Редактировать":
            order['step'] = 'product_id'
            send_message(vk, user_id, "✏️ Редактирование заказа. Введите ID товара для добавления:")
        elif text == "🔙 Отмена":
            del temp_orders[user_id]
            del user_states[user_id]
            from bot.handlers.menu import show_main_menu
            show_main_menu(vk, user_id)