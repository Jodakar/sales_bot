"""
Модуль работы с PostgreSQL
Все операции с базой данных: товары, заказы, клиенты
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime
import logging

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Параметры подключения
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', '1c_database'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def get_connection():
    """Создаёт подключение к базе данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return None


# =====================================================
# РАБОТА С ТОВАРАМИ
# =====================================================

def get_all_products():
    """Возвращает список всех товаров"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, price, stock, description, category, updated_at
                FROM products
                ORDER BY id
            """)
            products = cur.fetchall()
            return products
    except Exception as e:
        logger.error(f"Ошибка получения товаров: {e}")
        return []
    finally:
        conn.close()


def get_product_by_id(product_id):
    """Возвращает товар по ID"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, price, stock, description, category, updated_at
                FROM products
                WHERE id = %s
            """, (product_id,))
            product = cur.fetchone()
            return product
    except Exception as e:
        logger.error(f"Ошибка получения товара {product_id}: {e}")
        return None
    finally:
        conn.close()


def search_products(query):
    """Поиск товаров по названию или категории"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, price, stock, description, category
                FROM products
                WHERE name ILIKE %s OR category ILIKE %s
                ORDER BY price
                LIMIT 50
            """, (f'%{query}%', f'%{query}%'))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка поиска товаров: {e}")
        return []
    finally:
        conn.close()


def update_product(product_id, price=None, stock=None):
    """Обновляет цену или остаток товара"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            if price is not None:
                cur.execute("UPDATE products SET price = %s WHERE id = %s", (price, product_id))
            if stock is not None:
                cur.execute("UPDATE products SET stock = %s WHERE id = %s", (stock, product_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка обновления товара {product_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# =====================================================
# РАБОТА С ЗАКАЗАМИ
# =====================================================

def create_order(customer_name, customer_phone, customer_address, comment, delivery_method, delivery_time, items):
    """
    Создаёт новый заказ
    items: список словарей [{'product_id': 1, 'quantity': 2, 'price': 100}, ...]
    """
    conn = get_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            # Вычисляем итоговую сумму
            total_amount = sum(item['quantity'] * item['price'] for item in items)
            
            # Создаём заказ
            cur.execute("""
                INSERT INTO orders 
                (customer_name, customer_phone, customer_address, comment, delivery_method, delivery_time, total_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (customer_name, customer_phone, customer_address, comment, delivery_method, delivery_time, total_amount))
            
            order_id = cur.fetchone()[0]
            
            # Добавляем позиции заказа
            for item in items:
                cur.execute("""
                    INSERT INTO order_items 
                    (order_id, product_id, product_name, quantity, price, total)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (order_id, item['product_id'], item['product_name'], item['quantity'], item['price'], item['quantity'] * item['price']))
            
            # Обновляем информацию о клиенте
            cur.execute("""
                INSERT INTO customers (name, phone, address, last_order_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone) DO UPDATE
                SET name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    last_order_date = EXCLUDED.last_order_date
            """, (customer_name, customer_phone, customer_address, datetime.now()))
            
            conn.commit()
            logger.info(f"Создан заказ #{order_id} на сумму {total_amount}")
            return order_id
            
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_orders(filters=None):
    """
    Получает заказы с фильтрацией
    filters: {'status': 'not_paid', 'date_from': '2025-01-01', 'date_to': '2025-12-31'}
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT id, customer_name, customer_phone, customer_address, comment,
                       delivery_method, delivery_time, status, total_amount, created_at
                FROM orders
                WHERE 1=1
            """
            params = []
            
            if filters:
                if filters.get('status'):
                    query += " AND status = %s"
                    params.append(filters['status'])
                if filters.get('date_from'):
                    query += " AND created_at >= %s"
                    params.append(filters['date_from'])
                if filters.get('date_to'):
                    query += " AND created_at <= %s"
                    params.append(filters['date_to'])
            
            query += " ORDER BY created_at DESC"
            
            cur.execute(query, params)
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения заказов: {e}")
        return []
    finally:
        conn.close()


def get_order_by_id(order_id):
    """Получает заказ по ID вместе с позициями"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Получаем заказ
            cur.execute("""
                SELECT id, customer_name, customer_phone, customer_address, comment,
                       delivery_method, delivery_time, status, total_amount, created_at, updated_at
                FROM orders
                WHERE id = %s
            """, (order_id,))
            order = cur.fetchone()
            
            if not order:
                return None
            
            # Получаем позиции
            cur.execute("""
                SELECT id, product_id, product_name, quantity, price, total
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            order['items'] = cur.fetchall()
            
            return order
    except Exception as e:
        logger.error(f"Ошибка получения заказа {order_id}: {e}")
        return None
    finally:
        conn.close()


def update_order_status(order_id, status):
    """Обновляет статус заказа"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
            conn.commit()
            logger.info(f"Заказ #{order_id} обновлён статус: {status}")
            return True
    except Exception as e:
        logger.error(f"Ошибка обновления статуса заказа {order_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_order(order_id):
    """Удаляет заказ (каскадно удалятся и позиции)"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
            conn.commit()
            logger.info(f"Заказ #{order_id} удалён")
            return True
    except Exception as e:
        logger.error(f"Ошибка удаления заказа {order_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# =====================================================
# РАБОТА С КЛИЕНТАМИ
# =====================================================

def get_all_customers():
    """Возвращает список всех клиентов"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, phone, address, last_order_date, created_at
                FROM customers
                ORDER BY name
            """)
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения клиентов: {e}")
        return []
    finally:
        conn.close()


def get_customer_orders(customer_phone):
    """Возвращает заказы клиента по телефону"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, customer_name, total_amount, status, created_at
                FROM orders
                WHERE customer_phone = %s
                ORDER BY created_at DESC
            """, (customer_phone,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения заказов клиента: {e}")
        return []
    finally:
        conn.close()


def update_customer(customer_id, name=None, phone=None, address=None):
    """Обновляет данные клиента"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            if name:
                cur.execute("UPDATE customers SET name = %s WHERE id = %s", (name, customer_id))
            if phone:
                cur.execute("UPDATE customers SET phone = %s WHERE id = %s", (phone, customer_id))
            if address:
                cur.execute("UPDATE customers SET address = %s WHERE id = %s", (address, customer_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка обновления клиента {customer_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# =====================================================
# СТАТИСТИКА И ОТЧЕТЫ
# =====================================================

def get_statistics(date_from=None, date_to=None):
    """Получает статистику по продажам"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total_amount) as total_sales,
                    AVG(total_amount) as avg_order,
                    COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_orders,
                    COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered_orders
                FROM orders
                WHERE 1=1
            """
            params = []
            
            if date_from:
                query += " AND created_at >= %s"
                params.append(date_from)
            if date_to:
                query += " AND created_at <= %s"
                params.append(date_to)
            
            cur.execute(query, params)
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return None
    finally:
        conn.close()


def export_products_to_list():
    """Экспортирует товары в список для Excel"""
    return get_all_products()


def export_orders_to_list(filters=None):
    """Экспортирует заказы в список для Excel"""
    return get_orders(filters)


def export_customers_to_list():
    """Экспортирует клиентов в список для Excel"""
    return get_all_customers()


# =====================================================
# ПРОВЕРКА ПОДКЛЮЧЕНИЯ (для отладки)
# =====================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Проверка модуля db.py")
    print("=" * 50)
    
    # Проверяем подключение
    conn = get_connection()
    if conn:
        print("✅ Подключение к БД успешно")
        conn.close()
    else:
        print("❌ Ошибка подключения к БД")
    
    # Проверяем получение товаров
    products = get_all_products()
    print(f"\n📦 Товары: {len(products)}")
    for p in products[:3]:
        print(f"   {p['id']}. {p['name']} - {p['price']} ₽ (остаток: {p['stock']})")
    
    # Проверяем получение заказов
    orders = get_orders()
    print(f"\n📋 Заказы: {len(orders)}")
    for o in orders[:3]:
        print(f"   #{o['id']} | {o['customer_name']} | {o['total_amount']} ₽ | {o['status']}")
    
    print("\n✅ Проверка завершена")