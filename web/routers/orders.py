from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from datetime import datetime
import sys
import os
import shutil
import pandas as pd
from io import BytesIO
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.db import get_db_connection
from bot.utils.email_sender import send_order_info_to_customer as send_email
from bot.utils.email_sender import send_delivery_notification
from bot.utils.email_sender import send_delivery_order_notification

router = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "payments"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class OrderCreate(BaseModel):
    customer_name: str = None
    customer_phone: str = None
    customer_email: str = None
    customer_address: str = None
    comment: str = None
    delivery_method: str = "Курьер"
    items: list = []


class OrderStatusUpdate(BaseModel):
    status: str


class CommentUpdate(BaseModel):
    comment: str


class SendToDeliveryRequest(BaseModel):
    delivery_employee_ids: list[int]


def get_current_user():
    """Временная заглушка — получить текущего пользователя из токена"""
    return {"employee_id": 2, "full_name": "Мациев Тимофей Александрович", "role": "dev"}


@router.get("/stats")
async def get_stats():
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
            orders = []
            for row in rows:
                order = dict(zip(columns, row))
                if order['created_at']:
                    order['created_at'] = order['created_at'].strftime('%d.%m.%Y %H:%M')
                orders.append(order)
            return orders
    finally:
        conn.close()


@router.get("/search")
async def search_orders(query: str = "", status: str = ""):
    """Поиск заказов по запросу и статусу"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            conditions = []
            params = []
            
            if query:
                search_term = f"%{query}%"
                conditions.append("""
                    (o.order_id::text ILIKE %s
                    OR o.customer_name ILIKE %s
                    OR o.customer_phone ILIKE %s
                    OR o.customer_email ILIKE %s
                    OR o.status ILIKE %s
                    OR oi.product_name ILIKE %s
                    OR p.name ILIKE %s
                    OR p.article ILIKE %s)
                """)
                params.extend([search_term] * 8)
            
            if status:
                conditions.append("o.status = %s")
                params.append(status)
            
            if not conditions:
                cur.execute("""
                    SELECT order_id, customer_name, customer_phone, total_amount, status, created_at
                    FROM orders
                    ORDER BY order_id DESC
                """)
            else:
                where_clause = " AND ".join(conditions)
                cur.execute(f"""
                    SELECT DISTINCT o.order_id, o.customer_name, o.customer_phone, o.total_amount, o.status, o.created_at
                    FROM orders o
                    LEFT JOIN order_items oi ON o.order_id = oi.order_id
                    LEFT JOIN products p ON oi.product_id = p.product_id
                    WHERE {where_clause}
                    ORDER BY o.order_id DESC
                """, params)
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            orders = []
            for row in rows:
                order = dict(zip(columns, row))
                if order['created_at']:
                    order['created_at'] = order['created_at'].strftime('%d.%m.%Y %H:%M')
                orders.append(order)
            return orders
    finally:
        conn.close()


@router.get("/{order_id}")
async def get_order(order_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.order_id, o.customer_name, o.customer_phone, o.customer_email, o.customer_address, 
                       o.comment, o.delivery_method, o.status, o.total_amount, o.created_at,
                       e.full_name as created_by_name
                FROM orders o
                LEFT JOIN employees e ON o.created_by = e.employee_id
                WHERE o.order_id = %s
            """, (order_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            columns = [desc[0] for desc in cur.description]
            order = dict(zip(columns, row))
            if order['created_at']:
                order['created_at'] = order['created_at'].strftime('%d.%m.%Y %H:%M')
            
            cur.execute("""
                SELECT item_id, product_id, product_name, quantity, price, total
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            items = cur.fetchall()
            order['items'] = []
            for item in items:
                order['items'].append({
                    'item_id': item[0],
                    'product_id': item[1],
                    'product_name': item[2],
                    'quantity': item[3],
                    'price': float(item[4]),
                    'total': float(item[5]) if item[5] else float(item[3]) * float(item[4])
                })
            return order
    finally:
        conn.close()


@router.post("/")
async def create_order(order: OrderCreate):
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            customer_id = None
            if order.customer_phone:
                cur.execute("SELECT customer_id FROM customers WHERE phone = %s", (order.customer_phone,))
                row = cur.fetchone()
                if row:
                    customer_id = row[0]
            if not customer_id and order.customer_email:
                cur.execute("SELECT customer_id FROM customers WHERE email = %s", (order.customer_email,))
                row = cur.fetchone()
                if row:
                    customer_id = row[0]
            if not customer_id and order.customer_name:
                cur.execute("""
                    INSERT INTO customers (full_name, phone, email, address, created_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING customer_id
                """, (order.customer_name, order.customer_phone, order.customer_email, order.customer_address))
                customer_id = cur.fetchone()[0]
                conn.commit()
            
            cur.execute("""
                INSERT INTO orders (customer_id, customer_name, customer_phone, customer_email, customer_address, 
                                    comment, delivery_method, status, total_amount, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'not_paid', 0, %s)
                RETURNING order_id
            """, (customer_id, order.customer_name, order.customer_phone, order.customer_email, 
                  order.customer_address, order.comment, order.delivery_method, current_user['employee_id']))
            order_id = cur.fetchone()[0]
            
            total_amount = 0
            for item in order.items:
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
                cur.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, item['product_id']))
            
            cur.execute("UPDATE orders SET total_amount = %s WHERE order_id = %s", (total_amount, order_id))
            conn.commit()
            return {"order_id": order_id, "total_amount": total_amount, "message": "Заказ создан"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.post("/{order_id}/confirm-payment")
async def confirm_payment(
    order_id: int,
    file: UploadFile = File(...),
):
    """Подтверждение оплаты с загрузкой файла (PNG, JPEG, PDF) и отправкой уведомлений доставке"""
    current_user = get_current_user()
    
    allowed_extensions = ['.png', '.jpg', '.jpeg', '.pdf']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Неверный формат файла. Поддерживаются: PNG, JPEG, PDF")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"order_{order_id}_{timestamp}{file_ext}"
    file_path = UPLOAD_DIR / new_filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE order_id = %s", (order_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            old_status = row[0]
            if old_status != 'not_paid':
                raise HTTPException(status_code=400, detail="Оплата уже подтверждена или заказ доставлен")
            
            cur.execute("UPDATE orders SET status = 'paid' WHERE order_id = %s", (order_id,))
            
            cur.execute("""
                INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, file_path)
                VALUES (%s, %s, %s, %s, %s)
            """, (order_id, old_status, 'paid', current_user['full_name'], str(file_path)))
            
            cur.execute("""
                SELECT order_id, customer_name, total_amount
                FROM orders
                WHERE order_id = %s
            """, (order_id,))
            order_data = cur.fetchone()
            
            cur.execute("""
                SELECT employee_id, full_name, email
                FROM employees
                WHERE role = 'delivery' AND is_active = true
            """)
            delivery_employees = cur.fetchall()
            
            conn.commit()
            
            notifications_sent = 0
            for emp in delivery_employees:
                try:
                    send_delivery_notification(
                        employee_email=emp[2],
                        employee_name=emp[1],
                        order_id=order_id,
                        order_data=order_data
                    )
                    notifications_sent += 1
                except Exception as e:
                    print(f"Ошибка отправки уведомления {emp[1]}: {e}")
            
            return {
                "message": "Оплата подтверждена",
                "status": "paid",
                "notifications_sent": notifications_sent
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.post("/{order_id}/confirm-delivery")
async def confirm_delivery(order_id: int):
    """Подтверждение доставки (только после оплаты)"""
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE order_id = %s", (order_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            old_status = row[0]
            if old_status != 'paid':
                raise HTTPException(status_code=400, detail="Доставка возможна только после оплаты")
            
            cur.execute("UPDATE orders SET status = 'delivered' WHERE order_id = %s", (order_id,))
            
            cur.execute("""
                INSERT INTO order_status_history (order_id, old_status, new_status, changed_by)
                VALUES (%s, %s, %s, %s)
            """, (order_id, old_status, 'delivered', current_user['full_name']))
            
            conn.commit()
            return {"message": "Доставка подтверждена", "status": "delivered"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.get("/{order_id}/status-history")
async def get_status_history(order_id: int):
    """Получение истории изменения статусов заказа"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT history_id, old_status, new_status, changed_by, file_path, created_at
                FROM order_status_history
                WHERE order_id = %s
                ORDER BY created_at DESC
            """, (order_id,))
            rows = cur.fetchall()
            history = []
            for row in rows:
                history.append({
                    'history_id': row[0],
                    'old_status': row[1],
                    'new_status': row[2],
                    'changed_by': row[3],
                    'file_path': row[4],
                    'created_at': row[5].strftime('%d.%m.%Y %H:%M') if row[5] else None
                })
            return history
    finally:
        conn.close()


@router.post("/{order_id}/send-info")
async def send_order_info_to_customer(order_id: int):
    """Отправка информации о заказе клиенту на email"""
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.order_id, o.customer_name, o.customer_phone, o.customer_email, o.customer_address,
                       o.comment, o.delivery_method, o.total_amount, o.created_at, o.status,
                       e.full_name as employee_name, e.phone as employee_phone, e.email as employee_email
                FROM orders o
                LEFT JOIN employees e ON o.created_by = e.employee_id
                WHERE o.order_id = %s
            """, (order_id,))
            order_row = cur.fetchone()
            if not order_row:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            order_data = {
                'order_id': order_row[0],
                'customer_name': order_row[1],
                'customer_phone': order_row[2],
                'customer_email': order_row[3],
                'customer_address': order_row[4],
                'comment': order_row[5],
                'delivery_method': order_row[6],
                'total_amount': float(order_row[7]),
                'created_at': order_row[8].strftime('%d.%m.%Y %H:%M') if order_row[8] else None,
                'status': order_row[9]
            }
            
            employee_name = order_row[10] or '—'
            employee_phone = order_row[11] or '—'
            employee_email = order_row[12] or '—'
            
            cur.execute("""
                SELECT product_name, quantity, price
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            items = cur.fetchall()
            order_data['items'] = []
            for item in items:
                order_data['items'].append({
                    'product_name': item[0],
                    'quantity': item[1],
                    'price': float(item[2])
                })
            
            if not order_data.get('customer_email'):
                raise HTTPException(status_code=400, detail="У клиента не указан email")
            
            success, message = send_email(order_data, order_data['customer_email'], employee_name, employee_phone, employee_email)
            
            if success:
                return {"status": "success", "message": "Информация отправлена клиенту"}
            else:
                raise HTTPException(status_code=500, detail=f"Ошибка отправки: {message}")
    finally:
        conn.close()


@router.post("/import-statuses")
async def import_order_statuses(
    file: UploadFile = File(...),
):
    """Импорт статусов заказов из Excel-файла"""
    current_user = get_current_user()
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Неверный формат файла. Поддерживаются .xlsx и .xls"
        )
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        df.columns = [col.strip() for col in df.columns]
        
        order_col = None
        status_col = None
        for col in df.columns:
            if 'заказ' in col.lower() or 'id' in col.lower() or 'order' in col.lower():
                order_col = col
            if 'статус' in col.lower() or 'status' in col.lower():
                status_col = col
        
        if not order_col or not status_col:
            raise HTTPException(
                status_code=400,
                detail="Файл должен содержать колонки с номерами заказов и статусами"
            )
        
        updated = 0
        errors = 0
        error_list = []
        
        status_map = {
            'оплачен': 'paid',
            'не оплачен': 'not_paid',
            'доставлен': 'delivered',
            'paid': 'paid',
            'not_paid': 'not_paid',
            'delivered': 'delivered'
        }
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                for index, row in df.iterrows():
                    try:
                        order_val = row[order_col]
                        status_val = row[status_col]
                        
                        if pd.isna(order_val) or pd.isna(status_val):
                            errors += 1
                            error_list.append(f"Строка {index + 2}: пустые значения")
                            continue
                        
                        try:
                            order_id = int(order_val)
                        except (ValueError, TypeError):
                            errors += 1
                            error_list.append(f"Строка {index + 2}: неверный номер заказа '{order_val}'")
                            continue
                        
                        new_status = str(status_val).strip().lower()
                        new_status = status_map.get(new_status, new_status)
                        
                        if new_status not in ['paid', 'not_paid', 'delivered']:
                            errors += 1
                            error_list.append(f"Строка {index + 2}: неверный статус '{status_val}'")
                            continue
                        
                        cur.execute("SELECT status FROM orders WHERE order_id = %s", (order_id,))
                        row_result = cur.fetchone()
                        if not row_result:
                            errors += 1
                            error_list.append(f"Строка {index + 2}: заказ #{order_id} не найден")
                            continue
                        
                        old_status = row_result[0]
                        
                        if old_status != new_status:
                            cur.execute(
                                "UPDATE orders SET status = %s WHERE order_id = %s",
                                (new_status, order_id)
                            )
                            cur.execute("""
                                INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, file_path)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (order_id, old_status, new_status, current_user['full_name'], 'Excel импорт'))
                            updated += 1
                    
                    except Exception as e:
                        errors += 1
                        error_list.append(f"Строка {index + 2}: {str(e)}")
                
                conn.commit()
        finally:
            conn.close()
        
        return {
            "updated": updated,
            "errors": errors,
            "error_list": error_list[:10],
            "message": f"Импорт завершён: обновлено {updated}, ошибок {errors}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения файла: {str(e)}")


@router.patch("/{order_id}/status")
async def update_order_status(order_id: int, update: OrderStatusUpdate):
    """Старый метод — оставлен для совместимости"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE orders SET status = %s WHERE order_id = %s", (update.status, order_id))
            conn.commit()
            return {"message": f"Статус заказа #{order_id} изменён на {update.status}"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.patch("/{order_id}/comment")
async def update_comment(order_id: int, update: CommentUpdate):
    """Обновление комментария заказа (доступно при любом статусе)"""
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT comment FROM orders WHERE order_id = %s", (order_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            old_comment = row[0] or ''
            
            if old_comment == update.comment:
                return {"message": "Комментарий не изменён"}
            
            cur.execute("UPDATE orders SET comment = %s WHERE order_id = %s", (update.comment, order_id))
            
            cur.execute("""
                INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, file_path)
                VALUES (%s, 'comment_update', 'comment_update', %s, %s)
            """, (order_id, current_user['full_name'], f"Было: {old_comment} → Стало: {update.comment}"))
            
            conn.commit()
            return {"message": "Комментарий обновлён", "comment": update.comment}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.patch("/{order_id}/update")
async def update_order(order_id: int, update: OrderCreate):
    """Обновление заказа (только для статуса not_paid)"""
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE order_id = %s", (order_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            if row[0] != 'not_paid':
                raise HTTPException(status_code=400, detail="Редактирование доступно только для неоплаченных заказов")
            
            cur.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
            total_amount = 0
            for item in update.items:
                cur.execute("SELECT name, price, stock FROM products WHERE product_id = %s", (item['product_id'],))
                product = cur.fetchone()
                if not product:
                    continue
                product_name, price, stock = product
                quantity = item['quantity']
                
                if stock < quantity:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Недостаточно товара '{product_name}'. Доступно: {stock} шт."
                    )
                
                item_total = price * quantity
                total_amount += item_total
                cur.execute("""
                    INSERT INTO order_items (order_id, product_id, product_name, quantity, price, total)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (order_id, item['product_id'], product_name, quantity, price, item_total))
                cur.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, item['product_id']))
            
            cur.execute("""
                UPDATE orders 
                SET comment = %s, 
                    delivery_method = %s, 
                    total_amount = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_id = %s
            """, (update.comment, update.delivery_method, total_amount, order_id))
            
            conn.commit()
            return {"order_id": order_id, "total_amount": total_amount, "message": "Заказ обновлён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.post("/{order_id}/send-to-delivery")
async def send_order_to_delivery(order_id: int, request: SendToDeliveryRequest):
    """Отправка информации о заказе сотрудникам доставки"""
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.order_id, o.customer_name, o.customer_phone, o.customer_email, o.customer_address,
                       o.comment, o.delivery_method, o.total_amount, o.created_at, o.status,
                       e.full_name as employee_name, e.email as employee_email
                FROM orders o
                LEFT JOIN employees e ON o.created_by = e.employee_id
                WHERE o.order_id = %s
            """, (order_id,))
            order_row = cur.fetchone()
            if not order_row:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            if order_row[9] != 'paid':
                raise HTTPException(status_code=400, detail="Отправка в доставку доступна только для оплаченных заказов")
            
            cur.execute("""
                SELECT product_name, quantity, price
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            items = cur.fetchall()
            
            order_data = {
                'order_id': order_row[0],
                'customer_name': order_row[1],
                'customer_phone': order_row[2],
                'customer_email': order_row[3],
                'customer_address': order_row[4],
                'comment': order_row[5],
                'delivery_method': order_row[6],
                'total_amount': float(order_row[7]),
                'created_at': order_row[8].strftime('%d.%m.%Y %H:%M') if order_row[8] else None,
                'status': order_row[9],
                'items': [{'product_name': i[0], 'quantity': i[1], 'price': float(i[2])} for i in items]
            }
            
            employee_name = order_row[10] or '—'
            employee_email = order_row[11] or '—'
            
            if not request.delivery_employee_ids:
                raise HTTPException(status_code=400, detail="Выберите хотя бы одного сотрудника доставки")
            
            placeholders = ','.join(['%s'] * len(request.delivery_employee_ids))
            cur.execute(f"""
                SELECT employee_id, full_name, email
                FROM employees
                WHERE employee_id IN ({placeholders}) AND role = 'delivery' AND is_active = true
            """, request.delivery_employee_ids)
            delivery_employees = cur.fetchall()
            
            if not delivery_employees:
                raise HTTPException(status_code=400, detail="Выбранные сотрудники не найдены или неактивны")
            
            sent_count = 0
            for emp in delivery_employees:
                try:
                    send_delivery_order_notification(
                        employee_email=emp[2],
                        employee_name=emp[1],
                        order_data=order_data,
                        creator_name=employee_name,
                        creator_email=employee_email
                    )
                    sent_count += 1
                except Exception as e:
                    print(f"Ошибка отправки {emp[1]}: {e}")
            
            if employee_email and employee_email != '—':
                try:
                    send_delivery_order_notification(
                        employee_email=employee_email,
                        employee_name=employee_name,
                        order_data=order_data,
                        creator_name=employee_name,
                        creator_email=employee_email,
                        is_copy=True
                    )
                except Exception as e:
                    print(f"Ошибка отправки копии {employee_name}: {e}")
            
            cur.execute("""
                INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, file_path)
                VALUES (%s, 'delivery_notification', 'delivery_notification', %s, %s)
            """, (order_id, current_user['full_name'], f"Уведомление отправлено сотрудникам доставки: {', '.join([e[1] for e in delivery_employees])}"))
            conn.commit()
            
            return {
                "status": "success",
                "message": f"Уведомление отправлено {sent_count} сотрудникам доставки",
                "sent_to": [e[1] for e in delivery_employees]
            }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.delete("/{order_id}")
async def delete_order(order_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
            cur.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
            conn.commit()
            return {"message": f"Заказ #{order_id} удалён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()