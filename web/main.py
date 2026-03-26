"""
BackOffice — внутренняя веб-система для сотрудников
Бренд: TimoFey
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Импорт роутеров
from web.routers import products, orders, customers, auth, yoomoney

load_dotenv()

app = FastAPI(title="TimoFey BackOffice", version="1.0.0")

# Статика
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# API роутеры
app.include_router(products.router, prefix="/api/products", tags=["Товары"])
app.include_router(orders.router, prefix="/api/orders", tags=["Заказы"])
app.include_router(customers.router, prefix="/api/customers", tags=["Клиенты"])
app.include_router(auth.router, prefix="/api/auth", tags=["Авторизация"])
app.include_router(yoomoney.router, prefix="/api/yoomoney", tags=["ЮMoney"])


def read_page(filename: str) -> str:
    """Читает HTML файл из папки pages"""
    path = os.path.join(os.path.dirname(__file__), "pages", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return read_page("login.html")


@app.get("/", response_class=HTMLResponse)
async def index():
    return read_page("index.html")


@app.get("/products", response_class=HTMLResponse)
async def products_page():
    return read_page("products.html")


@app.get("/orders", response_class=HTMLResponse)
async def orders_page():
    return read_page("orders.html")


@app.get("/orders/create", response_class=HTMLResponse)
async def create_order_page():
    """Страница создания нового заказа"""
    return read_page("create_order.html")


@app.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail_page(order_id: int):
    html = read_page("order_detail.html")
    return html.replace("{{order_id}}", str(order_id))


@app.get("/customers", response_class=HTMLResponse)
async def customers_page():
    return read_page("customers.html")


@app.get("/customers/{customer_id}", response_class=HTMLResponse)
async def customer_detail_page(customer_id: int):
    """Страница деталей клиента"""
    html = read_page("customer_detail.html")
    return html.replace("{{customer_id}}", str(customer_id))


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "TimoFey BackOffice работает"}