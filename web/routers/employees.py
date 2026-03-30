from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import hashlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.db import get_db_connection

router = APIRouter()


class EmployeeCreate(BaseModel):
    full_name: str
    email: str
    phone: str = None
    birth_date: str = None
    role: str = "manager"
    login: str
    password: str
    can_upload_excel: bool = False
    can_edit_company_details: bool = False


class EmployeeUpdate(BaseModel):
    full_name: str = None
    email: str = None
    phone: str = None
    birth_date: str = None
    role: str = None
    can_upload_excel: bool = None
    can_edit_company_details: bool = None
    is_active: bool = None


class PasswordChange(BaseModel):
    new_password: str


def hash_password(password: str) -> str:
    """Хеширование пароля (SHA256)"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_current_user():
    """Временная заглушка — получить текущего пользователя из токена"""
    return {"employee_id": 2, "full_name": "Мациев Тимофей Александрович", "role": "dev"}


@router.get("/search")
async def search_employees(query: str):
    """Поиск сотрудников по ФИО, email, телефону, логину"""
    if not query or query.strip() == "":
        return []
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT employee_id, full_name, email, phone, birth_date, role, login, is_active
                FROM employees
                WHERE full_name ILIKE %s 
                   OR email ILIKE %s 
                   OR phone ILIKE %s 
                   OR login ILIKE %s
                ORDER BY full_name
            """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            employees = []
            for row in rows:
                emp = dict(zip(columns, row))
                if emp['birth_date']:
                    emp['birth_date'] = emp['birth_date'].strftime('%d.%m.%Y')
                employees.append(emp)
            return employees
    finally:
        conn.close()


@router.get("/")
async def get_employees():
    """Получение списка всех сотрудников"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT employee_id, full_name, email, phone, birth_date, role, login, 
                       can_upload_excel, can_edit_company_details, is_active, created_at
                FROM employees
                ORDER BY employee_id
            """)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            employees = []
            for row in rows:
                employee = dict(zip(columns, row))
                if employee['created_at']:
                    employee['created_at'] = employee['created_at'].strftime('%d.%m.%Y %H:%M')
                if employee['birth_date']:
                    employee['birth_date'] = employee['birth_date'].strftime('%d.%m.%Y')
                employees.append(employee)
            return employees
    finally:
        conn.close()


@router.get("/{employee_id}")
async def get_employee(employee_id: int):
    """Получение детальной информации о сотруднике"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT employee_id, full_name, email, phone, birth_date, role, login, 
                       can_upload_excel, can_edit_company_details, is_active, created_at, created_by
                FROM employees
                WHERE employee_id = %s
            """, (employee_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Сотрудник не найден")
            
            columns = [desc[0] for desc in cur.description]
            employee = dict(zip(columns, row))
            if employee['created_at']:
                employee['created_at'] = employee['created_at'].strftime('%d.%m.%Y %H:%M')
            if employee['birth_date']:
                employee['birth_date'] = employee['birth_date'].strftime('%d.%m.%Y')
            return employee
    finally:
        conn.close()


@router.post("/")
async def create_employee(employee: EmployeeCreate):
    """Создание нового сотрудника (только для разработчика)"""
    current_user = get_current_user()
    if current_user['role'] != 'dev':
        raise HTTPException(status_code=403, detail="Доступ запрещён. Только разработчик может создавать сотрудников")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT employee_id FROM employees WHERE login = %s", (employee.login,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Логин уже существует")
            
            cur.execute("SELECT employee_id FROM employees WHERE email = %s", (employee.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email уже существует")
            
            password_hash = hash_password(employee.password)
            cur.execute("""
                INSERT INTO employees (full_name, email, phone, birth_date, role, login, password_hash,
                                       can_upload_excel, can_edit_company_details, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING employee_id
            """, (employee.full_name, employee.email, employee.phone, employee.birth_date, employee.role,
                  employee.login, password_hash, employee.can_upload_excel,
                  employee.can_edit_company_details, current_user['employee_id']))
            employee_id = cur.fetchone()[0]
            conn.commit()
            return {"employee_id": employee_id, "message": "Сотрудник создан"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.patch("/{employee_id}")
async def update_employee(employee_id: int, update: EmployeeUpdate):
    """Обновление данных сотрудника с проверкой прав"""
    current_user = get_current_user()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM employees WHERE employee_id = %s", (employee_id,))
            target = cur.fetchone()
            if not target:
                raise HTTPException(status_code=404, detail="Сотрудник не найден")
            
            target_role = target[0]
            is_dev = current_user['role'] == 'dev'
            is_admin = current_user['role'] == 'admin'
            is_manager = current_user['role'] == 'manager'
            is_self = current_user['employee_id'] == employee_id
            
            updates = []
            values = []
            
            if is_dev:
                if update.full_name is not None:
                    updates.append("full_name = %s"); values.append(update.full_name)
                if update.phone is not None:
                    updates.append("phone = %s"); values.append(update.phone if update.phone else None)
                if update.birth_date is not None:
                    birth_val = update.birth_date if update.birth_date and update.birth_date.strip() != '' else None
                    updates.append("birth_date = %s"); values.append(birth_val)
                if update.email is not None:
                    updates.append("email = %s"); values.append(update.email)
                if update.role is not None:
                    updates.append("role = %s"); values.append(update.role)
                if update.can_upload_excel is not None:
                    updates.append("can_upload_excel = %s"); values.append(update.can_upload_excel)
                if update.can_edit_company_details is not None:
                    updates.append("can_edit_company_details = %s"); values.append(update.can_edit_company_details)
                if update.is_active is not None:
                    updates.append("is_active = %s"); values.append(update.is_active)
            
            elif is_admin:
                if is_self:
                    if update.phone is not None:
                        updates.append("phone = %s"); values.append(update.phone if update.phone else None)
                    if update.birth_date is not None:
                        birth_val = update.birth_date if update.birth_date and update.birth_date.strip() != '' else None
                        updates.append("birth_date = %s"); values.append(birth_val)
                    if update.email is not None:
                        updates.append("email = %s"); values.append(update.email)
                elif target_role == 'manager':
                    if update.phone is not None:
                        updates.append("phone = %s"); values.append(update.phone if update.phone else None)
                    if update.birth_date is not None:
                        birth_val = update.birth_date if update.birth_date and update.birth_date.strip() != '' else None
                        updates.append("birth_date = %s"); values.append(birth_val)
                    if update.email is not None:
                        updates.append("email = %s"); values.append(update.email)
            
            elif is_manager and is_self:
                if update.phone is not None:
                    updates.append("phone = %s"); values.append(update.phone if update.phone else None)
                if update.birth_date is not None:
                    birth_val = update.birth_date if update.birth_date and update.birth_date.strip() != '' else None
                    updates.append("birth_date = %s"); values.append(birth_val)
                if update.email is not None:
                    updates.append("email = %s"); values.append(update.email)
            
            if not updates:
                return {"message": "Нет данных для обновления или недостаточно прав"}
            
            values.append(employee_id)
            query = f"UPDATE employees SET {', '.join(updates)} WHERE employee_id = %s"
            cur.execute(query, values)
            conn.commit()
            return {"message": "Сотрудник обновлён"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.patch("/{employee_id}/password")
async def change_password(employee_id: int, password_data: PasswordChange):
    """Смена пароля (разработчик может менять всем, остальные только себе)"""
    current_user = get_current_user()
    is_dev = current_user['role'] == 'dev'
    is_self = current_user['employee_id'] == employee_id
    
    if not (is_dev or is_self):
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    
    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не менее 6 символов")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            password_hash = hash_password(password_data.new_password)
            cur.execute("UPDATE employees SET password_hash = %s WHERE employee_id = %s", (password_hash, employee_id))
            conn.commit()
            return {"message": "Пароль изменён"}
    finally:
        conn.close()


@router.delete("/{employee_id}")
async def delete_employee(employee_id: int):
    """Удаление сотрудника (только для разработчика)"""
    current_user = get_current_user()
    if current_user['role'] != 'dev':
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    
    if employee_id == current_user['employee_id']:
        raise HTTPException(status_code=400, detail="Нельзя удалить себя")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
            conn.commit()
            return {"message": "Сотрудник удалён"}
    finally:
        conn.close()