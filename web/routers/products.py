from fastapi import APIRouter, HTTPException, UploadFile, File
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


def get_current_user(token: str = None):
    """Временная заглушка для получения текущего пользователя"""
    # TODO: Получать реального пользователя из токена
    return "admin"


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


@router.get("/{product_id}")
async def get_product(product_id: int):
    """Получение детальной информации о товаре"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT product_id, name, price, stock, article, manufacturer, supplier,
                       purchase_price, reserved_stock, weight, dimensions, category, description, is_active
                FROM products
                WHERE product_id = %s AND is_active = true
            """, (product_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Товар не найден")
            
            columns = [desc[0] for desc in cur.description]
            product = dict(zip(columns, row))
            return product
    finally:
        conn.close()


@router.get("/{product_id}/history")
async def get_product_history(product_id: int):
    """Получение истории движения товара"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT history_id, action_type, changed_by, 
                       old_price, new_price, old_stock, new_stock,
                       old_article, new_article, old_manufacturer, new_manufacturer,
                       old_supplier, new_supplier, quantity_sold, source, created_at
                FROM product_history
                WHERE product_id = %s
                ORDER BY created_at DESC
            """, (product_id,))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            history = [dict(zip(columns, row)) for row in rows]
            
            # Форматируем дату
            for h in history:
                if h['created_at']:
                    h['created_at'] = h['created_at'].strftime('%d.%m.%Y %H:%M')
            
            return history
    finally:
        conn.close()


@router.post("/")
async def create_product(product: ProductCreate):
    """Создание нового товара"""
    conn = get_db_connection()
    user = get_current_user()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO products (name, price, stock, is_active)
                VALUES (%s, %s, %s, true)
                RETURNING product_id
            """, (product.name, product.price, product.stock))
            product_id = cur.fetchone()[0]
            conn.commit()
            
            # Записываем в историю
            cur.execute("""
                INSERT INTO product_history (product_id, action_type, changed_by, new_price, new_stock, source)
                VALUES (%s, 'import', %s, %s, %s, 'manual')
            """, (product_id, user, product.price, product.stock))
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
    user = get_current_user()
    try:
        with conn.cursor() as cur:
            # Получаем текущие значения
            cur.execute("SELECT price, stock FROM products WHERE product_id = %s", (product_id,))
            current = cur.fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="Товар не найден")
            
            old_price, old_stock = current
            
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
            
            # Записываем в историю
            cur.execute("""
                INSERT INTO product_history (product_id, action_type, changed_by, 
                    old_price, new_price, old_stock, new_stock, source)
                VALUES (%s, 'update', %s, %s, %s, %s, %s, 'manual')
            """, (product_id, user, old_price, update.price, old_stock, update.stock))
            
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
    user = get_current_user()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET is_active = false WHERE product_id = %s",
                (product_id,)
            )
            conn.commit()
            
            # Записываем в историю
            cur.execute("""
                INSERT INTO product_history (product_id, action_type, changed_by, source)
                VALUES (%s, 'delete', %s, 'manual')
            """, (product_id, user))
            conn.commit()
            
            return {"message": "Товар удалён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.post("/import-excel")
async def import_products_from_excel(
    file: UploadFile = File(...),
):
    """
    Импорт товаров из Excel-файла
    Формат файла: колонки ID, Артикул, Название, Цена, Остаток
    """
    # Проверка расширения
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Неверный формат файла. Поддерживаются .xlsx и .xls\n\nРешение: сохраните файл в формате Excel (.xlsx или .xls)"
        )
    
    # TODO: Реальная логика импорта
    # Пока возвращаем заглушку
    
    return {
        "added": 0,
        "updated": 0,
        "errors": 0,
        "message": "Импорт временно недоступен. Функция в разработке.\n\nПланируется: загрузка Excel, обновление цен и остатков."
    }