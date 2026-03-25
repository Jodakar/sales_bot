"""
Планировщик задач для автоматической синхронизации
"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.db import get_connection
from sync.sync_1c import sync_from_excel, start_watcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def backup_database():
    """Создаёт бэкап базы данных"""
    logger.info("💾 Создание бэкапа PostgreSQL...")
    
    try:
        import subprocess
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.getenv('BACKUPS_PATH', r'C:\Users\PC\Yandex.Disk\backups')
        os.makedirs(backup_path, exist_ok=True)
        
        backup_file = os.path.join(backup_path, f"postgres_backup_{timestamp}.sql")
        
        result = subprocess.run([
            'pg_dump',
            '-U', 'postgres',
            '-d', '1c_database',
            '-f', backup_file
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✅ Бэкап создан: {backup_file}")
        else:
            logger.error(f"❌ Ошибка бэкапа: {result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при создании бэкапа: {e}")


def check_postgresql():
    """Проверяет работу PostgreSQL"""
    conn = get_connection()
    if conn:
        logger.info("✅ PostgreSQL работает")
        conn.close()
        return True
    else:
        logger.error("❌ PostgreSQL не отвечает")
        return False


def sync_with_1c():
    """Запускает синхронизацию с 1С"""
    logger.info("🔄 Запуск синхронизации с 1С...")
    exports_path = os.getenv('EXPORTS_PATH', r'C:\Users\PC\Yandex.Disk\exports')
    
    if os.path.exists(exports_path):
        for file in os.listdir(exports_path):
            if file.endswith(('.xlsx', '.xls')):
                filepath = os.path.join(exports_path, file)
                logger.info(f"📁 Обработка: {file}")
                sync_from_excel(filepath)
    else:
        logger.warning(f"⚠️ Папка экспорта не найдена: {exports_path}")


def main():
    """Запуск планировщика"""
    logger.info("=" * 50)
    logger.info("⏰ ЗАПУСК ПЛАНИРОВЩИКА ЗАДАЧ")
    logger.info("=" * 50)
    
    # Проверка PostgreSQL
    check_postgresql()
    
    # Запускаем наблюдатель за папкой экспорта
    watcher = start_watcher()
    
    # Настраиваем расписание
    schedule.every(30).minutes.do(sync_with_1c)
    schedule.every().day.at("02:00").do(backup_database)
    schedule.every(5).minutes.do(check_postgresql)
    
    logger.info("📋 Расписание задач:")
    logger.info("  • Синхронизация с 1С: каждые 30 минут")
    logger.info("  • Бэкап PostgreSQL: ежедневно в 2:00")
    logger.info("  • Проверка PostgreSQL: каждые 5 минут")
    logger.info("  • Мониторинг папки экспорта: постоянно")
    logger.info("")
    logger.info("⏹️ Нажмите Ctrl+C для остановки")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Планировщик остановлен пользователем")
        watcher.stop()
        watcher.join()


if __name__ == "__main__":
    main()