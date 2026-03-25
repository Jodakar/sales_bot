"""
Модуль работы с Excel
Формирование выгрузок в формате Excel для аналитики
"""

import os
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Путь для сохранения Excel-файлов (из .env)
EXPORTS_PATH = os.getenv('EXPORTS_PATH', r'C:\Users\PC\Yandex.Disk\exports')


def ensure_exports_folder():
    """Создаёт папку для экспорта, если её нет"""
    if not os.path.exists(EXPORTS_PATH):
        os.makedirs(EXPORTS_PATH)
        logger.info(f"Создана папка для экспорта: {EXPORTS_PATH}")


def export_to_excel(data, filename_prefix, sheet_name="Sheet1"):
    """
    Экспортирует данные в Excel файл
    data: список словарей или DataFrame
    filename_prefix: префикс имени файла (например, 'products', 'orders')
    sheet_name: название листа
    Возвращает путь к созданному файлу
    """
    ensure_exports_folder()
    
    # Преобразуем в DataFrame, если передан список словарей
    if isinstance(data, list):
        if not data:
            logger.warning("Нет данных для экспорта")
            return None
        df = pd.DataFrame(data)
    else:
        df = data
    
    if df.empty:
        logger.warning("DataFrame пуст")
        return None
    
    # Форматируем дату и время для имени файла
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.xlsx"
    filepath = os.path.join(EXPORTS_PATH, filename)
    
    # Сохраняем в Excel
    df.to_excel(filepath, index=False, sheet_name=sheet_name, engine='openpyxl')
    
    logger.info(f"Экспорт завершён: {filepath}")
    return filepath


# =====================================================
# СПЕЦИАЛЬНЫЕ ВЫГРУЗКИ
# =====================================================

def export_products(products):
    """
    Экспортирует товары в Excel
    products: список товаров из БД (словари с полями: id, name, price, stock, description, category)
    """
    if not products:
        return None
    
    # Преобразуем в DataFrame
    df = pd.DataFrame(products)
    
    # Переименовываем колонки для читаемости
    column_names = {
        'id': 'ID товара',
        'name': 'Наименование',
        'price': 'Цена',
        'stock': 'Остаток',
        'description': 'Описание',
        'category': 'Категория',
        'updated_at': 'Дата обновления'
    }
    
    df = df.rename(columns={k: v for k, v in column_names.items() if k in df.columns})
    
    # Форматируем цену
    if 'Цена' in df.columns:
        df['Цена'] = df['Цена'].apply(lambda x: f"{x:,.2f} ₽".replace(',', ' ') if x else "0 ₽")
    
    # Сортируем по ID
    df = df.sort_values(by='ID товара')
    
    return export_to_excel(df, "products", "Товары")


def export_orders(orders):
    """
    Экспортирует заказы в Excel
    orders: список заказов из БД (словари с полями)
    """
    if not orders:
        return None
    
    df = pd.DataFrame(orders)
    
    # Переименовываем колонки
    column_names = {
        'id': 'ID заказа',
        'customer_name': 'Клиент',
        'customer_phone': 'Телефон',
        'customer_address': 'Адрес',
        'comment': 'Комментарий',
        'delivery_method': 'Способ доставки',
        'delivery_time': 'Время доставки',
        'status': 'Статус',
        'total_amount': 'Сумма',
        'created_at': 'Дата создания'
    }
    
    df = df.rename(columns={k: v for k, v in column_names.items() if k in df.columns})
    
    # Форматируем сумму
    if 'Сумма' in df.columns:
        df['Сумма'] = df['Сумма'].apply(lambda x: f"{x:,.2f} ₽".replace(',', ' ') if x else "0 ₽")
    
    # Сортируем по дате (новые сверху)
    if 'Дата создания' in df.columns:
        df = df.sort_values(by='Дата создания', ascending=False)
    
    return export_to_excel(df, "orders", "Заказы")


def export_customers(customers):
    """
    Экспортирует клиентов в Excel
    customers: список клиентов из БД
    """
    if not customers:
        return None
    
    df = pd.DataFrame(customers)
    
    # Переименовываем колонки
    column_names = {
        'id': 'ID клиента',
        'name': 'Имя',
        'phone': 'Телефон',
        'address': 'Адрес',
        'last_order_date': 'Дата последнего заказа',
        'created_at': 'Дата регистрации'
    }
    
    df = df.rename(columns={k: v for k, v in column_names.items() if k in df.columns})
    
    # Сортируем по имени
    df = df.sort_values(by='Имя')
    
    return export_to_excel(df, "customers", "Клиенты")


def export_statistics(statistics):
    """
    Экспортирует статистику продаж в Excel
    statistics: словарь с данными статистики
    """
    if not statistics:
        return None
    
    # Создаём DataFrame из одной строки
    df = pd.DataFrame([statistics])
    
    # Переименовываем колонки
    column_names = {
        'total_orders': 'Всего заказов',
        'total_sales': 'Общая сумма продаж',
        'avg_order': 'Средний чек',
        'paid_orders': 'Оплаченные заказы',
        'delivered_orders': 'Доставленные заказы'
    }
    
    df = df.rename(columns={k: v for k, v in column_names.items() if k in df.columns})
    
    # Форматируем суммы
    if 'Общая сумма продаж' in df.columns:
        df['Общая сумма продаж'] = df['Общая сумма продаж'].apply(lambda x: f"{x:,.2f} ₽".replace(',', ' ') if x else "0 ₽")
    if 'Средний чек' in df.columns:
        df['Средний чек'] = df['Средний чек'].apply(lambda x: f"{x:,.2f} ₽".replace(',', ' ') if x else "0 ₽")
    
    return export_to_excel(df, "statistics", "Статистика")


# =====================================================
# ЭКСПОРТ СТРУКТУРЫ ЗАКАЗА (с позициями)
# =====================================================

def export_order_with_items(order):
    """
    Экспортирует заказ с позициями в отдельный Excel файл
    order: полный заказ с ключом 'items'
    """
    if not order:
        return None
    
    ensure_exports_folder()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"order_{order['id']}_{timestamp}.xlsx"
    filepath = os.path.join(EXPORTS_PATH, filename)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Лист с информацией о заказе
        order_info = pd.DataFrame([{
            'ID заказа': order['id'],
            'Клиент': order['customer_name'],
            'Телефон': order['customer_phone'],
            'Адрес': order['customer_address'],
            'Комментарий': order.get('comment', ''),
            'Способ доставки': order.get('delivery_method', ''),
            'Статус': order['status'],
            'Сумма': f"{order['total_amount']:,.2f} ₽".replace(',', ' '),
            'Дата создания': order['created_at']
        }])
        order_info.to_excel(writer, sheet_name='Информация о заказе', index=False)
        
        # Лист с позициями заказа
        if order.get('items'):
            items_df = pd.DataFrame(order['items'])
            items_df = items_df.rename(columns={
                'product_id': 'ID товара',
                'product_name': 'Наименование',
                'quantity': 'Количество',
                'price': 'Цена',
                'total': 'Сумма'
            })
            items_df['Цена'] = items_df['Цена'].apply(lambda x: f"{x:,.2f} ₽".replace(',', ' ') if x else "0 ₽")
            items_df['Сумма'] = items_df['Сумма'].apply(lambda x: f"{x:,.2f} ₽".replace(',', ' ') if x else "0 ₽")
            items_df.to_excel(writer, sheet_name='Позиции заказа', index=False)
    
    logger.info(f"Экспорт заказа #{order['id']} завершён: {filepath}")
    return filepath


# =====================================================
# ПРОВЕРКА МОДУЛЯ (для отладки)
# =====================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Проверка модуля excel.py")
    print("=" * 50)
    
    ensure_exports_folder()
    
    # Тестовые данные
    test_products = [
        {'id': 1, 'name': 'Телевизор Samsung', 'price': 22318, 'stock': 10, 'description': 'Full HD', 'category': 'Телевизоры'},
        {'id': 2, 'name': 'Смартфон', 'price': 59999, 'stock': 5, 'description': '256GB', 'category': 'Смартфоны'}
    ]
    
    filepath = export_products(test_products)
    if filepath:
        print(f"✅ Экспорт товаров: {filepath}")
    
    print("\n✅ Проверка завершена")