from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.db import get_db_connection

router = APIRouter()


class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_address: str = None
    comment: str = None
    delivery_method: str = "Курьер"
    items: list  # список {product_id, quantity}


class OrderStatusUpdate(BaseModel):
    status: str  # not_paid, paid, delivered


@router.get("/stats")
async def get_stats():
    """Получение статистики по заказам"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM orders")
            count, total = cur.fetchone()
            return {"count": count, "total": float(total)}
    finally:
        conn.close()


@router.get("/")
async def get_orders():
    """Получение списка всех заказов"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT order_id, customer_name, customer_phone, total_amount, status, created_at
                FROM orders
                ORDER BY order_id DESC
            """)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            orders = [dict(zip(columns, row)) for row in rows]
            
            # Преобразуем дату в строку
            for o in orders:
                if o['created_at']:
                    o['created_at'] = o['created_at'].strftime('%d.%m.%Y %H:%M')
            return orders
    finally:
        conn.close()


@router.get("/{order_id}")
async def get_order(order_id: int):
    """Получение деталей заказа"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT order_id, customer_name, customer_phone, customer_address, comment,
                       delivery_method, status, total_amount, created_at
                FROM orders
                WHERE order_id = %s
            """, (order_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            columns = [desc[0] for desc in cur.description]
            order = dict(zip(columns, row))
            if order['created_at']:
                order['created_at'] = order['created_at'].strftime('%d.%m.%Y %H:%M')
            
            # Получаем позиции заказа
            cur.execute("""
                SELECT item_id, product_name, quantity, price, total
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            items = cur.fetchall()
            order['items'] = [dict(zip(['item_id', 'product_name', 'quantity', 'price', 'total'], item)) for item in items]
            
            return order
    finally:
        conn.close()


@router.post("/")
async def create_order(order: OrderCreate):
    """Создание нового заказа"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Вставляем заказ
            cur.execute("""
                INSERT INTO orders (customer_name, customer_phone, customer_address, comment, delivery_method, status, total_amount)
                VALUES (%s, %s, %s, %s, %s, 'not_paid', 0)
                RETURNING order_id
            """, (order.customer_name, order.customer_phone, order.customer_address, order.comment, order.delivery_method))
            order_id = cur.fetchone()[0]
            
            total_amount = 0
            
            # Вставляем позиции
            for item in order.items:
                # Получаем цену товара
                cur.execute("SELECT name, price FROM products WHERE product_id = %s", (item['product_id'],))
                product = cur.fetchone()
                if not product:
                    continue
                product_name, price = product
                quantity = item['quantity']
                item_total = price * quantity
                total_amount += item_total
                
                cur.execute("""
                    INSERT INTO order_items (order_id, product_id, product_name, quantity, price, total)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (order_id, item['product_id'], product_name, quantity, price, item_total))
                
                # Уменьшаем остаток
                cur.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, item['product_id']))
            
            # Обновляем общую сумму заказа
            cur.execute("UPDATE orders SET total_amount = %s WHERE order_id = %s", (total_amount, order_id))
            conn.commit()
            
            return {"order_id": order_id, "total_amount": total_amount, "message": "Заказ создан"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.patch("/{order_id}/status")
async def update_order_status(order_id: int, update: OrderStatusUpdate):
    """Обновление статуса заказа"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = %s WHERE order_id = %s",
                (update.status, order_id)
            )
            conn.commit()
            return {"message": f"Статус заказа #{order_id} изменён на {update.status}"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.delete("/{order_id}")
async def delete_order(order_id: int):
    """Удаление заказа"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Сначала удаляем позиции (каскадное удаление должно сработать, но для надёжности)
            cur.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
            cur.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
            conn.commit()
            return {"message": f"Заказ #{order_id} удалён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()