from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import secrets
import hashlib

router = APIRouter()

# Временное хранилище сессий (в памяти)
# В реальном проекте нужно использовать БД или Redis
sessions = {}

# Данные пользователя (временные, потом перенесём в БД)
USERS = {
    "admin": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "name": "Администратор"
    }
}


class LoginData(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/login")
async def login(data: LoginData):
    """Вход в систему"""
    user = USERS.get(data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    if user["password"] != hash_password(data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    # Создаём токен сессии
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "username": data.username,
        "name": user["name"]
    }
    
    return {
        "status": "success",
        "token": token,
        "user": {
            "username": data.username,
            "name": user["name"]
        }
    }


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