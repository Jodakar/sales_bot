"""
Модуль управления клиентами
"""

import logging
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from bot.utils.send_message import send_message
from bot.utils.db import get_all_customers, get_customer_orders

logger = logging.getLogger(__name__)


def get_customers_keyboard():
    """Клавиатура для списка клиентов"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("📋 Все клиенты", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🔍 Поиск по телефону", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🔙 Вернуться в меню", color=VkKeyboardColor.SECONDARY)
    return keyboard


def handle_customers_list(vk, user_id):
    """Показывает список клиентов"""
    customers = get_all_customers()
    
    if not customers:
        send_message(vk, user_id, "👥 Список клиентов пуст", get_customers_keyboard())
        return
    
    customers_text = "👥 *Список клиентов:*\n\n"
    for c in customers:
        customers_text += f"🆔 {c['id']} | {c['name']} | {c['phone']}\n"
        if c.get('last_order_date'):
            customers_text += f"   📅 Последний заказ: {c['last_order_date'].strftime('%d.%m.%Y')}\n"
    
    customers_text += "\n💡 Введите ID клиента для просмотра заказов"
    send_message(vk, user_id, customers_text, get_customers_keyboard())


def handle_customer_detail(vk, user_id, customer_id):
    """Показывает детали клиента и его заказы"""
    try:
        cid = int(customer_id)
    except ValueError:
        send_message(vk, user_id, "❌ Неверный формат ID клиента", get_customers_keyboard())
        return
    
    customers = get_all_customers()
    customer = next((c for c in customers if c['id'] == cid), None)
    
    if not customer:
        send_message(vk, user_id, f"❌ Клиент с ID {cid} не найден", get_customers_keyboard())
        return
    
    orders = get_customer_orders(customer['phone'])
    
    customer_text = f"""
👤 *Клиент: {customer['name']}*
━━━━━━━━━━━━━━━━━━━━━━
📞 Телефон: {customer['phone']}
📍 Адрес: {customer.get('address', 'Не указан')}
📅 Зарегистрирован: {customer['created_at'].strftime('%d.%m.%Y')}
"""
    
    if orders:
        customer_text += "\n📋 *Заказы:*\n"
        for o in orders[:5]:
            status_emoji = "🟡" if o['status'] == 'not_paid' else "🟢" if o['status'] == 'paid' else "✅"
            customer_text += f"{status_emoji} #{o['id']} | {o['total_amount']} ₽ | {o['created_at'].strftime('%d.%m.%Y')}\n"
        if len(orders) > 5:
            customer_text += f"\n... и ещё {len(orders) - 5} заказов"
    else:
        customer_text += "\n📭 Нет заказов"
    
    send_message(vk, user_id, customer_text, get_customers_keyboard())


def handle_customer_by_phone(vk, user_id, phone):
    """Поиск клиента по телефону"""
    customers = get_all_customers()
    
    # Ищем клиента, у которого телефон содержит введённые цифры
    # Очищаем от пробелов и знаков
    search_phone = ''.join(filter(str.isdigit, phone))
    customer = None
    
    for c in customers:
        c_phone = ''.join(filter(str.isdigit, c['phone']))
        if search_phone in c_phone or c_phone in search_phone:
            customer = c
            break
    
    if customer:
        handle_customer_detail(vk, user_id, customer['id'])
    else:
        send_message(vk, user_id, f"❌ Клиент с телефоном {phone} не найден", get_customers_keyboard())


def handle_customers_action(vk, user_id, text):
    """Обработчик действий с клиентами"""
    from bot.main import user_states
    
    if text == "📋 Все клиенты":
        handle_customers_list(vk, user_id)
    
    elif text == "🔍 Поиск по телефону":
        send_message(vk, user_id, "🔍 Введите номер телефона (например, +7 925 123-45-67):")
        user_states[user_id] = "waiting_customer_phone"
    
    elif text == "🔙 Вернуться в меню":
        from bot.handlers.menu import show_main_menu
        show_main_menu(vk, user_id)
    
    return None