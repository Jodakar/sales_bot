@echo off
cd /d "C:\Users\PC\Yandex.Disk\Проекты\sales_bot"
call venv\Scripts\activate
uvicorn web.main:app --host 127.0.0.1 --port 8000