from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from web.routers.auth import sessions


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки активности пользователя"""
    
    async def dispatch(self, request: Request, call_next):
        # Пропускаем страницу логина, статику и health
        if request.url.path in ["/login", "/health"] or request.url.path.startswith("/static"):
            return await call_next(request)
        
        # Проверяем токен
        token = request.cookies.get("token") or request.headers.get("Authorization")
        if token and token in sessions:
            user = sessions[token]
            from bot.utils.db import get_db_connection
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT is_active FROM employees WHERE employee_id = %s", (user["employee_id"],))
                    row = cur.fetchone()
                    if row and not row[0]:
                        return RedirectResponse(url="/login", status_code=303)
            finally:
                conn.close()
        
        return await call_next(request)