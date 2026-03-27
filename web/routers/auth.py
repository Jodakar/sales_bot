from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import secrets
import hashlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.db import get_db_connection

router = APIRouter()

# Временное хранилище сессий (в памяти)
# В реальном проекте нужно использовать БД или Redis
sessions = {}


class LoginData(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/login")
async def login(data: LoginData):
    """Вход в систему"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT employee_id, full_name, role, password_hash, is_active 
                FROM employees 
                WHERE login = %s
            """, (data.username,))
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Неверное имя пользователя или пароль"
                )
            
            employee_id, full_name, role, password_hash, is_active = user
            
            # Проверка активности
            if not is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Учётная запись заблокирована"
                )
            
            # Проверка пароля
            if password_hash != hash_password(data.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Неверное имя пользователя или пароль"
                )
            
            # Обновляем last_login
            cur.execute(
                "UPDATE employees SET last_login = CURRENT_TIMESTAMP WHERE employee_id = %s",
                (employee_id,)
            )
            conn.commit()
            
            # Создаём токен сессии
            token = secrets.token_urlsafe(32)
            sessions[token] = {
                "employee_id": employee_id,
                "username": data.username,
                "name": full_name,
                "role": role
            }
            
            return {
                "status": "success",
                "token": token,
                "user": {
                    "employee_id": employee_id,
                    "username": data.username,
                    "name": full_name,
                    "role": role
                }
            }
    finally:
        conn.close()


@router.post("/logout")
async def logout(token: str):
    """Выход из системы"""
    if token in sessions:
        del sessions[token]
    return {"status": "success"}


@router.get("/check")
async def check_auth(token: str):
    """Проверка авторизации"""
    if token in sessions:
        return {
            "authenticated": True,
            "user": sessions[token]
        }
    return {"authenticated": False}