from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sys
import pandas as pd
from io import BytesIO
from datetime import datetime
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


def get_current_user():
    """Временная заглушка — получить текущего пользователя из токена"""
    return {"employee_id": 2, "full_name": "Мациев Тимофей Александрович", "role": "dev"}


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
                SELECT product_id, name, price, stock, article, category, is_active,
                       manufacturer, supplier, purchase_price, weight, dimensions, description
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


@router.get("/search")
async def search_products(query: str):
    """Поиск товаров по ID, названию, артикулу, производителю"""
    if not query or query.strip() == "":
        return []
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            search_term = f"%{query}%"
            cur.execute("""
                SELECT product_id, name, price, stock, article, category, is_active,
                       manufacturer, supplier, purchase_price, weight, dimensions, description
                FROM products
                WHERE is_active = true
                  AND (product_id::text ILIKE %s
                    OR name ILIKE %s
                    OR article ILIKE %s
                    OR manufacturer ILIKE %s
                    OR supplier ILIKE %s)
                ORDER BY product_id
            """, (search_term, search_term, search_term, search_term, search_term))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            products = [dict(zip(columns, row)) for row in rows]
            return products
    finally:
        conn.close()


@router.get("/export-excel")
async def export_products_to_excel():
    """Выгрузка всех товаров в Excel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT product_id as "ID", article as "Артикул", name as "Название",
                       price as "Цена", stock as "Остаток", manufacturer as "Производитель",
                       supplier as "Поставщик", purchase_price as "Цена закупки",
                       weight as "Вес", dimensions as "Габариты", category as "Категория",
                       description as "Описание"
                FROM products
                WHERE is_active = true
                ORDER BY product_id
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            df = pd.DataFrame(rows, columns=columns)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Товары')
            
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
            )
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
            
            for h in history:
                if h['created_at']:
                    h['created_at'] = h['created_at'].strftime('%d.%m.%Y %H:%M')
            
            return history
    finally:
        conn.close()


@router.post("/")
async def create_product(product: ProductCreate):
    """Создание нового товара"""
    current_user = get_current_user()
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
            
            cur.execute("""
                INSERT INTO product_history (product_id, action_type, changed_by, new_price, new_stock, source)
                VALUES (%s, 'import', %s, %s, %s, 'manual')
            """, (product_id, current_user['full_name'], product.price, product.stock))
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
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
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
            
            cur.execute("""
                INSERT INTO product_history (product_id, action_type, changed_by, 
                    old_price, new_price, old_stock, new_stock, source)
                VALUES (%s, 'update', %s, %s, %s, %s, %s, 'manual')
            """, (product_id, current_user['full_name'], old_price, update.price, old_stock, update.stock))
            
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
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET is_active = false WHERE product_id = %s",
                (product_id,)
            )
            conn.commit()
            
            cur.execute("""
                INSERT INTO product_history (product_id, action_type, changed_by, source)
                VALUES (%s, 'delete', %s, 'manual')
            """, (product_id, current_user['full_name']))
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
    """Импорт товаров из Excel-файла с новыми полями"""
    current_user = get_current_user()
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Неверный формат файла. Поддерживаются .xlsx и .xls"
        )
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(file.file)
        
        # Ожидаемые колонки
        expected_columns = ['ID', 'Артикул', 'Название', 'Цена', 'Остаток', 
                           'Производитель', 'Поставщик', 'Контакт', 'Телефон', 'Email']
        
        # Приводим названия колонок к стандарту
        df.columns = ['ID', 'Артикул', 'Название', 'Цена', 'Остаток', 
                      'Производитель', 'Поставщик', 'Контакт', 'Телефон', 'Email']
        
        added = 0
        updated = 0
        errors = 0
        errors_list = []
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                for index, row in df.iterrows():
                    try:
                        product_id = int(row['ID']) if pd.notna(row['ID']) else None
                        article = str(row['Артикул']) if pd.notna(row['Артикул']) else None
                        name = str(row['Название']) if pd.notna(row['Название']) else None
                        price = float(row['Цена']) if pd.notna(row['Цена']) else 0
                        stock = int(row['Остаток']) if pd.notna(row['Остаток']) else 0
                        manufacturer = str(row['Производитель']) if pd.notna(row['Производитель']) else None
                        supplier = str(row['Поставщик']) if pd.notna(row['Поставщик']) else None
                        
                        if not name:
                            errors += 1
                            errors_list.append(f"Строка {index + 2}: отсутствует название товара")
                            continue
                        
                        if product_id:
                            # Обновляем существующий товар
                            cur.execute("""
                                UPDATE products 
                                SET name = %s, price = %s, stock = %s, article = %s,
                                    manufacturer = %s, supplier = %s, updated_at = CURRENT_TIMESTAMP
                                WHERE product_id = %s AND is_active = true
                                RETURNING product_id
                            """, (name, price, stock, article, manufacturer, supplier, product_id))
                            
                            if cur.fetchone():
                                updated += 1
                                # Записываем в историю
                                cur.execute("""
                                    INSERT INTO product_history (product_id, action_type, changed_by, new_price, new_stock, source)
                                    VALUES (%s, 'import', %s, %s, %s, 'excel')
                                """, (product_id, current_user['full_name'], price, stock))
                            else:
                                # Товара с таким ID нет, добавляем новый
                                cur.execute("""
                                    INSERT INTO products (name, price, stock, article, manufacturer, supplier, is_active)
                                    VALUES (%s, %s, %s, %s, %s, %s, true)
                                    RETURNING product_id
                                """, (name, price, stock, article, manufacturer, supplier))
                                new_id = cur.fetchone()[0]
                                added += 1
                                cur.execute("""
                                    INSERT INTO product_history (product_id, action_type, changed_by, new_price, new_stock, source)
                                    VALUES (%s, 'import', %s, %s, %s, 'excel')
                                """, (new_id, current_user['full_name'], price, stock))
                        else:
                            # Добавляем новый товар
                            cur.execute("""
                                INSERT INTO products (name, price, stock, article, manufacturer, supplier, is_active)
                                VALUES (%s, %s, %s, %s, %s, %s, true)
                                RETURNING product_id
                            """, (name, price, stock, article, manufacturer, supplier))
                            new_id = cur.fetchone()[0]
                            added += 1
                            cur.execute("""
                                INSERT INTO product_history (product_id, action_type, changed_by, new_price, new_stock, source)
                                VALUES (%s, 'import', %s, %s, %s, 'excel')
                            """, (new_id, current_user['full_name'], price, stock))
                        
                        conn.commit()
                    except Exception as e:
                        errors += 1
                        errors_list.append(f"Строка {index + 2}: {str(e)}")
                        conn.rollback()
        finally:
            conn.close()
        
        return {
            "added": added,
            "updated": updated,
            "errors": errors,
            "errors_list": errors_list[:10],
            "message": f"Импорт завершён: добавлено {added}, обновлено {updated}, ошибок {errors}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения файла: {str(e)}")