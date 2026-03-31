from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.db import get_db_connection

router = APIRouter()


class CompanyDetailsCreate(BaseModel):
    company_name: str
    inn: str = None
    bank_account: str = None
    bank_name: str = None
    bik: str = None
    corr_account: str = None


class CompanyDetailsUpdate(BaseModel):
    company_name: str = None
    inn: str = None
    bank_account: str = None
    bank_name: str = None
    bik: str = None
    corr_account: str = None
    is_active: bool = None


def get_current_user():
    return {"employee_id": 2, "full_name": "Мациев Тимофей Александрович", "role": "dev"}


@router.get("/")
async def get_company_details():
    """Получение активных реквизитов компании"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, company_name, inn, bank_account, bank_name, bik, corr_account, is_active, created_at
                FROM company_details
                WHERE is_active = true
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "company_name": row[1],
                "inn": row[2],
                "bank_account": row[3],
                "bank_name": row[4],
                "bik": row[5],
                "corr_account": row[6],
                "is_active": row[7],
                "created_at": row[8].strftime('%d.%m.%Y %H:%M') if row[8] else None
            }
    finally:
        conn.close()


@router.get("/all")
async def get_all_company_details():
    """Получение всех реквизитов компании (для админов)"""
    current_user = get_current_user()
    if current_user['role'] not in ['dev', 'admin']:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, company_name, inn, bank_account, bank_name, bik, corr_account, is_active, created_at
                FROM company_details
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "company_name": row[1],
                    "inn": row[2],
                    "bank_account": row[3],
                    "bank_name": row[4],
                    "bik": row[5],
                    "corr_account": row[6],
                    "is_active": row[7],
                    "created_at": row[8].strftime('%d.%m.%Y %H:%M') if row[8] else None
                })
            return result
    finally:
        conn.close()


@router.post("/")
async def create_company_details(data: CompanyDetailsCreate):
    """Создание новых реквизитов компании (только для разработчика)"""
    current_user = get_current_user()
    if current_user['role'] != 'dev':
        raise HTTPException(status_code=403, detail="Доступ запрещён. Только разработчик")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Деактивируем текущие активные реквизиты
            cur.execute("UPDATE company_details SET is_active = false WHERE is_active = true")
            
            # Создаём новые
            cur.execute("""
                INSERT INTO company_details (company_name, inn, bank_account, bank_name, bik, corr_account, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, true)
                RETURNING id
            """, (data.company_name, data.inn, data.bank_account, data.bank_name, data.bik, data.corr_account))
            new_id = cur.fetchone()[0]
            conn.commit()
            return {"id": new_id, "message": "Реквизиты компании созданы"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.patch("/{details_id}")
async def update_company_details(details_id: int, data: CompanyDetailsUpdate):
    """Обновление реквизитов компании (только для разработчика)"""
    current_user = get_current_user()
    if current_user['role'] != 'dev':
        raise HTTPException(status_code=403, detail="Доступ запрещён. Только разработчик")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            updates = []
            values = []
            
            if data.company_name is not None:
                updates.append("company_name = %s"); values.append(data.company_name)
            if data.inn is not None:
                updates.append("inn = %s"); values.append(data.inn)
            if data.bank_account is not None:
                updates.append("bank_account = %s"); values.append(data.bank_account)
            if data.bank_name is not None:
                updates.append("bank_name = %s"); values.append(data.bank_name)
            if data.bik is not None:
                updates.append("bik = %s"); values.append(data.bik)
            if data.corr_account is not None:
                updates.append("corr_account = %s"); values.append(data.corr_account)
            if data.is_active is not None:
                updates.append("is_active = %s"); values.append(data.is_active)
            
            if not updates:
                return {"message": "Нет данных для обновления"}
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(details_id)
            query = f"UPDATE company_details SET {', '.join(updates)} WHERE id = %s"
            cur.execute(query, values)
            conn.commit()
            return {"message": "Реквизиты компании обновлены"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()