"""
Клавиатуры для бота
"""

from vk_api.keyboard import VkKeyboard, VkKeyboardColor


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


def get_cart_keyboard():
    """Клавиатура для корзины"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("➕ Добавить еще товар", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("✅ Оформить заказ", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("🗑️ Очистить корзину", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("🔙 Вернуться в меню", color=VkKeyboardColor.SECONDARY)
    return keyboard


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