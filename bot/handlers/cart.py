"""
Модуль управления корзиной заказа
"""

import logging
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from bot.main import send_message
from bot.utils.db import get_product_by_id, create_order

logger = logging.getLogger(__name__)

# Хранилище корзин (временное, в памяти)
# В реальном проекте лучше использовать Redis или БД
carts = {}


def get_cart_keyboard():
    """Клавиатура для корзины"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("➕ Добавить еще товар", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("✅ Оформить заказ", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("🗑️ Очистить корзину", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("🔙 Вернуться в меню", color=VkKeyboardColor.SECONDARY)
    return keyboard


def format_cart(cart):
    """Форматирует корзину для отображения"""
    if not cart or len(cart) == 0:
        return "🛒 Корзина пуста"
    
    items_text = []
    total = 0
    
    for i, item in enumerate(cart, 1):
        items_text.append(f"{i}. {item['name']} x{item['quantity']} = {item['quantity'] * item['price']} ₽")
        total += item['quantity'] * item['price']
    
    cart_text = "🛒 *Ваша корзина:*\n\n" + "\n".join(items_text) + f"\n\n💰 *Итого: {total} ₽*"
    return cart_text, total


def add_to_cart(user_id, product_id, quantity=1):
    """Добавляет товар в корзину"""
    product = get_product_by_id(product_id)
    if not product:
        return False, "❌ Товар не найден"
    
    if product['stock'] < quantity:
        return False, f"❌ Недостаточно товара. В наличии: {product['stock']} шт."
    
    if user_id not in carts:
        carts[user_id] = []
    
    # Проверяем, есть ли уже такой товар в корзине
    for item in carts[user_id]:
        if item['product_id'] == product_id:
            item['quantity'] += quantity
            return True, f"✅ Добавлено еще {quantity} шт. товара '{product['name']}'"
    
    # Добавляем новый товар
    carts[user_id].append({
        'product_id': product_id,
        'name': product['name'],
        'price': product['price'],
        'quantity': quantity
    })
    
    return True, f"✅ Товар '{product['name']}' добавлен в корзину, {quantity} шт."


def remove_from_cart(user_id, item_index):
    """Удаляет товар из корзины по индексу"""
    if user_id not in carts:
        return False, "❌ Корзина пуста"
    
    try:
        idx = int(item_index) - 1
        if 0 <= idx < len(carts[user_id]):
            removed = carts[user_id].pop(idx)
            return True, f"✅ Товар '{removed['name']}' удалён из корзины"
        else:
            return False, "❌ Неверный номер товара"
    except:
        return False, "❌ Ошибка: введите номер товара"


def clear_cart(user_id):
    """Очищает корзину"""
    if user_id in carts:
        carts[user_id] = []
    return True, "✅ Корзина очищена"


def get_cart(user_id):
    """Возвращает корзину пользователя"""
    return carts.get(user_id, [])


# =====================================================
# ОБРАБОТЧИКИ
# =====================================================

def handle_add_to_cart(vk, user_id, product_id, quantity=1):
    """Обработчик добавления товара в корзину"""
    success, message = add_to_cart(user_id, product_id, quantity)
    
    if success:
        cart = get_cart(user_id)
        if cart:
            cart_text, total = format_cart(cart)
            send_message(vk, user_id, f"{message}\n\n{cart_text}", get_cart_keyboard())
        else:
            send_message(vk, user_id, message)
    else:
        send_message(vk, user_id, message)


def handle_show_cart(vk, user_id):
    """Показывает корзину"""
    cart = get_cart(user_id)
    if not cart:
        send_message(vk, user_id, "🛒 Корзина пуста. Добавьте товары через раздел 'Товары'.")
        return
    
    cart_text, total = format_cart(cart)
    send_message(vk, user_id, cart_text, get_cart_keyboard())


def handle_cart_action(vk, user_id, text):
    """Обработчик действий с корзиной"""
    if text == "➕ Добавить еще товар":
        send_message(vk, user_id, "🔍 Введите ID товара для добавления:")
        # Сохраняем состояние, что ожидаем ввод ID товара
        # В реальном проекте используйте FSM (конечный автомат)
        return "waiting_product_id"
    
    elif text == "✅ Оформить заказ":
        cart = get_cart(user_id)
        if not cart:
            send_message(vk, user_id, "❌ Корзина пуста. Добавьте товары.")
            return None
        
        send_message(vk, user_id, "📝 Введите имя клиента:")
        return "waiting_customer_name"
    
    elif text == "🗑️ Очистить корзину":
        success, message = clear_cart(user_id)
        send_message(vk, user_id, message)
        return None
    
    elif text == "🔙 Вернуться в меню":
        from bot.handlers.menu import show_main_menu
        show_main_menu(vk, user_id)
        return None
    
    return None


def handle_remove_item(vk, user_id, item_index):
    """Удаляет товар из корзины по номеру"""
    success, message = remove_from_cart(user_id, item_index)
    if success:
        cart = get_cart(user_id)
        if cart:
            cart_text, total = format_cart(cart)
            send_message(vk, user_id, f"{message}\n\n{cart_text}", get_cart_keyboard())
        else:
            send_message(vk, user_id, message)
    else:
        send_message(vk, user_id, message)