"""
Модуль для работы с API ЮMoney
"""

import hashlib
import hmac
import json
import time
import urllib.parse
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.db import get_db_connection

router = APIRouter()

# Конфигурация из .env
YM_CLIENT_ID = os.getenv("YM_CLIENT_ID", "")
YM_CLIENT_SECRET = os.getenv("YM_CLIENT_SECRET", "")
YM_REDIRECT_URI = os.getenv("YM_REDIRECT_URI", "")
YM_NOTIFICATION_URI = os.getenv("YM_NOTIFICATION_URI", "")


class CreateInvoiceRequest(BaseModel):
    order_id: int
    amount: float
    comment: str = None


class CreateInvoiceResponse(BaseModel):
    invoice_id: int
    payment_url: str
    order_id: int
    amount: float


@router.post("/create-invoice")
async def create_invoice(request: CreateInvoiceRequest):
    """
    Создание счёта для оплаты через ЮMoney
    """
    if not YM_CLIENT_ID or not YM_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="ЮMoney не настроен")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Проверяем заказ
            cur.execute("SELECT order_id, total_amount FROM orders WHERE order_id = %s", (request.order_id,))
            order = cur.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")

            # Проверяем сумму
            if request.amount != order[1]:
                raise HTTPException(status_code=400, detail="Сумма не совпадает с суммой заказа")

            # Генерируем уникальный номер счёта
            invoice_number = f"INV-{request.order_id}-{int(time.time())}"

            # Создаём запись в таблице invoices
            cur.execute("""
                INSERT INTO invoices (order_id, invoice_number, amount, status, created_at)
                VALUES (%s, %s, %s, 'pending', CURRENT_TIMESTAMP)
                RETURNING invoice_id
            """, (request.order_id, invoice_number, request.amount))
            invoice_id = cur.fetchone()[0]
            conn.commit()

            # Формируем URL для оплаты
            # В реальном проекте здесь должен быть запрос к API ЮMoney
            # Пока делаем заглушку
            payment_url = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YM_CLIENT_ID}&formcomment=Оплата заказа&short-dest=Оплата заказа №{request.order_id}&targets=Заказ №{request.order_id}&sum={request.amount}&paymentType=PC&label={invoice_number}"

            return CreateInvoiceResponse(
                invoice_id=invoice_id,
                payment_url=payment_url,
                order_id=request.order_id,
                amount=request.amount
            )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/webhook")
async def yoomoney_webhook(request: Request):
    """
    Webhook для получения уведомлений об оплате от ЮMoney
    """
    try:
        form_data = await request.form()
        notification_type = form_data.get("notification_type")
        operation_id = form_data.get("operation_id")
        amount = form_data.get("amount")
        label = form_data.get("label")  # invoice_number
        sha1_hash = form_data.get("sha1_hash")
        withdraw_amount = form_data.get("withdraw_amount")
        currency = form_data.get("currency")
        datetime_str = form_data.get("datetime")
        sender = form_data.get("sender")
        codepro = form_data.get("codepro")

        # Проверяем подпись
        notification_secret = YM_CLIENT_SECRET
        params = f"{notification_type}&{operation_id}&{amount}&{currency}&{datetime_str}&{sender}&{codepro}&{notification_secret}&{label}"
        calculated_hash = hashlib.sha1(params.encode()).hexdigest()

        if calculated_hash != sha1_hash:
            print(f"Ошибка проверки подписи: {calculated_hash} != {sha1_hash}")
            return {"error": "invalid signature"}

        # Ищем счёт по label
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT invoice_id, order_id, status FROM invoices WHERE invoice_number = %s", (label,))
                invoice = cur.fetchone()
                if not invoice:
                    return {"error": "invoice not found"}

                if notification_type == "p2p-incoming":
                    # Обновляем статус счёта
                    cur.execute("""
                        UPDATE invoices 
                        SET status = 'paid', paid_at = CURRENT_TIMESTAMP, payment_id = %s 
                        WHERE invoice_number = %s
                    """, (operation_id, label))

                    # Обновляем статус заказа
                    cur.execute("""
                        UPDATE orders 
                        SET status = 'paid', payment_confirmed = true 
                        WHERE order_id = %s
                    """, (invoice[1],))

                    conn.commit()
                    print(f"✅ Оплата получена для заказа #{invoice[1]}, сумма: {amount}")

            return {"status": "success"}
        finally:
            conn.close()

    except Exception as e:
        print(f"Ошибка webhook: {e}")
        return {"error": str(e)}


@router.get("/check-payment/{order_id}")
async def check_payment(order_id: int):
    """
    Проверка статуса оплаты заказа
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT i.status, i.paid_at, o.status as order_status
                FROM invoices i
                JOIN orders o ON i.order_id = o.order_id
                WHERE i.order_id = %s
                ORDER BY i.created_at DESC
                LIMIT 1
            """, (order_id,))
            row = cur.fetchone()

            if not row:
                return {"paid": False, "status": "no_invoice"}

            return {
                "paid": row[0] == "paid",
                "invoice_status": row[0],
                "order_status": row[2],
                "paid_at": row[1].isoformat() if row[1] else None
            }
    finally:
        conn.close()