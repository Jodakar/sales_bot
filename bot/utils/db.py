"""
Модуль для работы с базой данных PostgreSQL
"""

import psycopg2
from psycopg2 import pool, DatabaseError
import os
from dotenv import load_dotenv
import time

load_dotenv()

# Параметры подключения
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', '1c_database')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'TimPostgres2026')

# Пул соединений
connection_pool = None
_max_retries = 3
_retry_delay = 1


def init_pool(min_conn=1, max_conn=5):
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
        connection_pool = None
        return False


def get_db_connection():
    """Получение соединения из пула с повторными попытками"""
    global connection_pool
    
    if connection_pool is None:
        init_pool()
    
    for attempt in range(_max_retries):
        try:
            if connection_pool:
                return connection_pool.getconn()
            else:
                # Если пул не работает, создаём обычное соединение
                return psycopg2.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD
                )
        except Exception as e:
            print(f"⚠️ Попытка {attempt + 1}/{_max_retries}: {e}")
            if attempt < _max_retries - 1:
                time.sleep(_retry_delay)
                # Пробуем пересоздать пул
                init_pool()
            else:
                print(f"❌ Ошибка получения соединения после {_max_retries} попыток")
                raise


def put_db_connection(conn):
    """Возврат соединения в пул (безопасно)"""
    global connection_pool
    if conn and connection_pool:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            print(f"⚠️ Ошибка при возврате соединения: {e}")
            try:
                conn.close()
            except:
                pass


def close_all_connections():
    """Закрытие всех соединений в пуле"""
    global connection_pool
    if connection_pool:
        try:
            connection_pool.closeall()
            print("✅ Все соединения закрыты")
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии пула: {e}")
        finally:
            connection_pool = None


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Выполнение запроса и возврат результата"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch_one:
                return cur.fetchone()
            if fetch_all:
                return cur.fetchall()
            conn.commit()
            return cur.rowcount
    except DatabaseError as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            put_db_connection(conn)