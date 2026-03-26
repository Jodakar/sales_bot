"""
Модуль для работы с базой данных PostgreSQL
"""

import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

load_dotenv()

# Параметры подключения
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', '1c_database')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TimPostgres2026')

# Пул соединений
connection_pool = None


def init_pool(min_conn=1, max_conn=10):
    """Инициализация пула соединений"""
    global connection_pool
    try:
        connection_pool = pool.SimpleConnectionPool(
            min_conn,
            max_conn,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print(f"✅ Пул соединений создан: {min_conn}-{max_conn}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания пула: {e}")
        return False


def get_db_connection():
    """Получение соединения из пула или создание нового"""
    global connection_pool
    if connection_pool is None:
        init_pool()
    try:
        return connection_pool.getconn()
    except Exception as e:
        print(f"❌ Ошибка получения соединения: {e}")
        # Если пул не работает, создаём обычное соединение
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )


def put_db_connection(conn):
    """Возврат соединения в пул"""
    global connection_pool
    if connection_pool and conn:
        connection_pool.putconn(conn)


def close_all_connections():
    """Закрытие всех соединений в пуле"""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        print("✅ Все соединения закрыты")


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Выполнение запроса и возврат результата"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch_one:
                return cur.fetchone()
            if fetch_all:
                return cur.fetchall()
            conn.commit()
            return cur.rowcount
    finally:
        put_db_connection(conn)