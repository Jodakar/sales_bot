# 📦 TimoFey — Система автоматизации продаж

**TimoFey** — это внутренняя веб-система (BackOffice) для управления продажами, заказами, товарами и клиентами.  
Система доступна сотрудникам через браузер, а также через VK-бота для мобильной работы.

---

## 🎯 Основные возможности

| Модуль | Описание |
|--------|----------|
| **BackOffice (веб-сайт)** | Управление товарами, заказами, клиентами, отчёты |
| **VK Бот** | Мобильный доступ: создание заказов, просмотр статусов |
| **Авторизация** | Защита паролем (admin/admin123) |
| **PostgreSQL** | Единая база данных |
| **Excel-отчёты** | Выгрузка данных для аналитики |

---

## 🏗️ Архитектура
┌─────────────────────────────────────────────────────────────────┐
│ СОТРУДНИКИ (продавцы, менеджеры) │
│ • Работают в офисе (ноутбук) → BackOffice │
│ • Работают удалённо (телефон) → VK Бот │
└──────────────────────────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ ВНУТРЕННЯЯ СИСТЕМА (BackOffice) │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ВЕБ-САЙТ ДЛЯ СОТРУДНИКОВ │ │
│ │ • Каталог товаров (CRUD) │ │
│ │ • Заказы (список, детали, смена статуса) │ │
│ │ • Клиенты (база, история) │ │
│ │ • Отчёты (Excel) │ │
│ └─────────────────────────────────────────────────────────┘ │
│ │ │
│ ▼ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ POSTGRESQL (общая база) │ │
│ │ • products, orders, order_items, customers │ │
│ │ • invoices, company_details │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

text

---

## 📁 Структура проекта (актуальная)
sales_bot/
├── bot/ # VK бот (мобильный помощник)
│ ├── handlers/ # Обработчики команд
│ ├── keyboards/ # Клавиатуры
│ └── utils/ # db.py, excel.py, sync.py
│
├── web/ # BackOffice (FastAPI)
│ ├── main.py # Точка входа, маршруты
│ ├── pages/ # HTML-страницы
│ │ ├── login.html
│ │ ├── index.html
│ │ ├── products.html
│ │ ├── orders.html
│ │ ├── order_detail.html
│ │ └── customers.html
│ ├── routers/ # API (products, orders, customers, auth)
│ └── static/ # style.css, favicon.ico
│
├── database/ # SQL-скрипты
├── sync/ # Синхронизация, планировщик
├── logs/ # Логи
├── requirements.txt # Python-зависимости
├── .env # Переменные окружения
└── README.md

text

---

## 🚀 Быстрый старт

### 1. Клонировать репозиторий
```bash
git clone https://github.com/Jodakar/sales_bot.git
cd sales_bot
2. Настроить окружение
powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
3. Настроить базу данных PostgreSQL
Создать базу 1c_database

Выполнить скрипты из database/schema.sql

4. Настроить .env файл
text
DB_HOST=localhost
DB_PORT=5432
DB_NAME=1c_database
DB_USER=postgres
DB_PASSWORD=your_password

VK_TOKEN=your_vk_token
VK_GROUP_ID=235801282
VK_ADMIN_ID=704921838
5. Запустить BackOffice (веб-сайт)
powershell
uvicorn web.main:app --reload --host 127.0.0.1 --port 8000
Открыть в браузере: http://127.0.0.1:8000
Логин: admin
Пароль: admin123

6. Запустить VK бота (опционально)
powershell
python -m bot.main
🗄️ Структура базы данных (основные таблицы)
products
Поле	Тип	Описание
product_id	SERIAL	ID товара
name	VARCHAR(255)	Наименование
price	DECIMAL(12,2)	Цена
stock	INTEGER	Остаток
article	VARCHAR(20)	Артикул
is_active	BOOLEAN	Активен
orders
Поле	Тип	Описание
order_id	SERIAL	Номер заказа
customer_name	VARCHAR(100)	Имя клиента
customer_phone	VARCHAR(20)	Телефон
total_amount	DECIMAL(12,2)	Сумма
status	VARCHAR(20)	not_paid / paid / delivered
customers
Поле	Тип	Описание
customer_id	SERIAL	ID клиента
full_name	VARCHAR(100)	ФИО
phone	VARCHAR(20)	Телефон
email	VARCHAR(100)	Email
🤖 VK Бот (мобильный помощник)
Доступен продавцу для работы вне офиса:

Кнопка	Функция
🛒 Новый заказ	Создание заказа
📦 Заказы	Просмотр и фильтрация
📊 Товары	Поиск и редактирование
👥 Клиенты	История заказов
📁 Отчеты	Excel-выгрузки
🔧 Технологический стек
Компонент	Технология
BackOffice	FastAPI, Jinja2, HTML/CSS
VK Бот	vk-api (LongPoll)
База данных	PostgreSQL 18
Работа с Excel	pandas, openpyxl
Планировщик	schedule
Логирование	logging
📝 Статус проекта
Компонент	Статус
PostgreSQL	✅ Работает
VK Бот	✅ Работает
BackOffice (веб)	✅ Работает
Авторизация	✅ Готова
Товары (CRUD)	✅ Готов
Заказы (CRUD, статусы)	✅ Готов
Клиенты	⏳ В разработке
Отчёты Excel	⏳ Планируется
ЮMoney интеграция	⏳ Планируется
📄 Лицензия
MIT License

Последнее обновление: 27.03.2026 | Версия 2.0 | Бренд TimoFey

text

---

## 🔧 ШАГ 3: ОТПРАВИТЬ README НА GITHUB

Если редактировал локально:

```powershell
cd "C:\Users\PC\Yandex.Disk\Проекты\sales_bot"
git add README.md
git commit -m "Обновлён README: описание BackOffice, авторизации, бренда TimoFey"
git push origin main
