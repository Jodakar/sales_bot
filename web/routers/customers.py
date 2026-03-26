from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.db import get_db_connection

router = APIRouter()


class CustomerCreate(BaseModel):
    full_name: str
    phone: str = None
    email: str = None
    address: str = None
    telegram: str = None
    whatsapp: str = None


class CustomerUpdate(BaseModel):
    full_name: str = None
    phone: str = None
    email: str = None
    address: str = None
    telegram: str = None
    whatsapp: str = None


@router.get("/stats")
async def get_stats():
    """Получение статистики по клиентам"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM customers")
            count = cur.fetchone()[0]
            return {"count": count}
    finally:
        conn.close()


@router.get("/")
async def get_customers():
    """Получение списка всех клиентов с количеством заказов"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.customer_id,
                    c.full_name,
                    c.phone,
                    c.email,
                    c.address,
                    c.telegram,
                    c.whatsapp,
                    c.created_at,
                    c.last_order_date,
                    COUNT(o.order_id) as orders_count
                FROM customers c
                LEFT JOIN orders o ON c.customer_id = o.customer_id
                GROUP BY c.customer_id
                ORDER BY c.customer_id DESC
            """)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            customers = []
            for row in rows:
                customer = dict(zip(columns, row))
                if customer['created_at']:
                    customer['created_at'] = customer['created_at'].strftime('%d.%m.%Y')
                if customer['last_order_date']:
                    customer['last_order_date'] = customer['last_order_date'].strftime('%d.%m.%Y')
                customers.append(customer)
            return customers
    finally:
        conn.close()


@router.get("/{customer_id}")
async def get_customer(customer_id: int):
    """Получение детальной информации о клиенте и его заказах"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    customer_id, full_name, phone, email, address, 
                    telegram, whatsapp, created_at, last_order_date
                FROM customers
                WHERE customer_id = %s
            """, (customer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Клиент не найден")
            
            columns = [desc[0] for desc in cur.description]
            customer = dict(zip(columns, row))
            if customer['created_at']:
                customer['created_at'] = customer['created_at'].strftime('%d.%m.%Y %H:%M')
            if customer['last_order_date']:
                customer['last_order_date'] = customer['last_order_date'].strftime('%d.%m.%Y')
            
            # Получаем заказы клиента
            cur.execute("""
                SELECT order_id, total_amount, status, created_at
                FROM orders
                WHERE customer_id = %s
                ORDER BY order_id DESC
            """, (customer_id,))
            orders = cur.fetchall()
            customer['orders'] = []
            for o in orders:
                customer['orders'].append({
                    'order_id': o[0],
                    'total_amount': float(o[1]),
                    'status': o[2],
                    'created_at': o[3].strftime('%d.%m.%Y %H:%M') if o[3] else None
                })
            
            return customer
    finally:
        conn.close()


@router.post("/")
async def create_customer(customer: CustomerCreate):
    """Создание нового клиента"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO customers (full_name, phone, email, address, telegram, whatsapp, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING customer_id
            """, (customer.full_name, customer.phone, customer.email, 
                  customer.address, customer.telegram, customer.whatsapp))
            customer_id = cur.fetchone()[0]
            conn.commit()
            return {"customer_id": customer_id, "message": "Клиент создан"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.patch("/{customer_id}")
async def update_customer(customer_id: int, update: CustomerUpdate):
    """Обновление данных клиента"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            updates = []
            values = []
            for field, value in update.dict(exclude_unset=True).items():
                updates.append(f"{field} = %s")
                values.append(value)
            
            if not updates:
                return {"message": "Нет данных для обновления"}
            
            values.append(customer_id)
            query = f"UPDATE customers SET {', '.join(updates)} WHERE customer_id = %s"
            cur.execute(query, values)
            conn.commit()
            return {"message": "Клиент обновлён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.delete("/{customer_id}")
async def delete_customer(customer_id: int):
    """Удаление клиента"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Проверяем, есть ли у клиента заказы
            cur.execute("SELECT COUNT(*) FROM orders WHERE customer_id = %s", (customer_id,))
            orders_count = cur.fetchone()[0]
            if orders_count > 0:
                raise HTTPException(status_code=400, detail="Нельзя удалить клиента с заказами")
            
            cur.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))
            conn.commit()
            return {"message": "Клиент удалён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()