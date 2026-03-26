from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.db import get_db_connection

router = APIRouter()


class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int


class ProductUpdate(BaseModel):
    price: float = None
    stock: int = None


@router.get("/stats")
async def get_stats():
    """Получение статистики по товарам"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM products WHERE is_active = true")
            count = cur.fetchone()[0]
            return {"count": count}
    finally:
        conn.close()


@router.get("/")
async def get_products():
    """Получение списка всех товаров"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT product_id, name, price, stock, article, category, is_active
                FROM products
                WHERE is_active = true
                ORDER BY product_id
            """)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            products = [dict(zip(columns, row)) for row in rows]
            return products
    finally:
        conn.close()


@router.post("/")
async def create_product(product: ProductCreate):
    """Создание нового товара"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO products (name, price, stock, is_active)
                VALUES (%s, %s, %s, true)
                RETURNING product_id
            """, (product.name, product.price, product.stock))
            product_id = cur.fetchone()[0]
            conn.commit()
            return {"product_id": product_id, "message": "Товар создан"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.patch("/{product_id}")
async def update_product(product_id: int, update: ProductUpdate):
    """Обновление товара (цена/остаток)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            updates = []
            values = []
            if update.price is not None:
                updates.append("price = %s")
                values.append(update.price)
            if update.stock is not None:
                updates.append("stock = %s")
                values.append(update.stock)
            
            if not updates:
                return {"message": "Нет данных для обновления"}
            
            values.append(product_id)
            query = f"UPDATE products SET {', '.join(updates)} WHERE product_id = %s"
            cur.execute(query, values)
            conn.commit()
            return {"message": "Товар обновлён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.delete("/{product_id}")
async def delete_product(product_id: int):
    """Мягкое удаление товара (is_active = false)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET is_active = false WHERE product_id = %s",
                (product_id,)
            )
            conn.commit()
            return {"message": "Товар удалён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()