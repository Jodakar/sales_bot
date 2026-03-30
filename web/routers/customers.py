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


class CustomerUpdate(BaseModel):
    full_name: str = None
    phone: str = None
    email: str = None
    address: str = None


def get_current_user():
    """Временная заглушка — получить текущего пользователя из токена"""
    return {"employee_id": 2, "full_name": "Мациев Тимофей Александрович", "role": "dev"}


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
                    c.created_at,
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
                customers.append(customer)
            return customers
    finally:
        conn.close()


@router.get("/search")
async def search_customers(query: str):
    """Поиск клиентов по ФИО, телефону, email"""
    if not query or query.strip() == "":
        return []
    
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
                    c.created_at,
                    COUNT(o.order_id) as orders_count
                FROM customers c
                LEFT JOIN orders o ON c.customer_id = o.customer_id
                WHERE c.full_name ILIKE %s 
                   OR c.phone ILIKE %s 
                   OR c.email ILIKE %s
                GROUP BY c.customer_id
                ORDER BY c.full_name
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            customers = []
            for row in rows:
                customer = dict(zip(columns, row))
                if customer['created_at']:
                    customer['created_at'] = customer['created_at'].strftime('%d.%m.%Y')
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
                    customer_id, full_name, phone, email, address, created_at
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
            
            cur.execute("""
                SELECT order_id, total_amount, status, created_at
                FROM orders
                WHERE customer_id = %s
                ORDER BY created_at DESC
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


@router.get("/{customer_id}/history")
async def get_customer_history(customer_id: int):
    """Получение истории изменений клиента"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT history_id, field_name, old_value, new_value, changed_by, created_at
                FROM customer_history
                WHERE customer_id = %s
                ORDER BY created_at DESC
            """, (customer_id,))
            rows = cur.fetchall()
            history = []
            for row in rows:
                history.append({
                    'history_id': row[0],
                    'field_name': row[1],
                    'old_value': row[2],
                    'new_value': row[3],
                    'changed_by': row[4],
                    'created_at': row[5].strftime('%d.%m.%Y %H:%M') if row[5] else None
                })
            return history
    finally:
        conn.close()


@router.post("/")
async def create_customer(customer: CustomerCreate):
    """Создание нового клиента"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if customer.email:
                cur.execute("SELECT customer_id FROM customers WHERE email = %s", (customer.email,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Email уже существует")
            
            cur.execute("""
                INSERT INTO customers (full_name, phone, email, address, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING customer_id
            """, (customer.full_name, customer.phone, customer.email, customer.address))
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
    """Обновление данных клиента с записью в историю"""
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT phone, email, address FROM customers WHERE customer_id = %s", (customer_id,))
            current = cur.fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="Клиент не найден")
            
            old_phone, old_email, old_address = current
            
            updates = []
            values = []
            
            if update.phone is not None:
                updates.append("phone = %s")
                values.append(update.phone if update.phone else None)
                if update.phone != old_phone:
                    cur.execute("""
                        INSERT INTO customer_history (customer_id, field_name, old_value, new_value, changed_by)
                        VALUES (%s, 'phone', %s, %s, %s)
                    """, (customer_id, old_phone, update.phone, current_user['full_name']))
            
            if update.email is not None:
                updates.append("email = %s")
                values.append(update.email if update.email else None)
                if update.email != old_email:
                    cur.execute("""
                        INSERT INTO customer_history (customer_id, field_name, old_value, new_value, changed_by)
                        VALUES (%s, 'email', %s, %s, %s)
                    """, (customer_id, old_email, update.email, current_user['full_name']))
            
            if update.address is not None:
                updates.append("address = %s")
                values.append(update.address if update.address else None)
                if update.address != old_address:
                    cur.execute("""
                        INSERT INTO customer_history (customer_id, field_name, old_value, new_value, changed_by)
                        VALUES (%s, 'address', %s, %s, %s)
                    """, (customer_id, old_address, update.address, current_user['full_name']))
            
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