"""
Модуль синхронизации с 1С
Обновляет данные о товарах и статусах заказов из Excel-файлов
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Добавляем путь для импортов
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.db import get_connection, update_product, update_order_status
from bot.utils.excel import EXPORTS_PATH

logger = logging.getLogger(__name__)


class ExcelHandler(FileSystemEventHandler):
    """Обработчик новых Excel-файлов"""
    
    def on_created(self, event):
        """При создании нового файла"""
        if not event.is_directory and event.src_path.endswith('.xlsx'):
            time.sleep(1)  # Ждём завершения записи
            self.process_file(event.src_path)
    
    def on_modified(self, event):
        """При изменении файла"""
        if not event.is_directory and event.src_path.endswith('.xlsx'):
            self.process_file(event.src_path)
    
    def process_file(self, filepath):
        """Обрабатывает Excel-файл"""
        filename = os.path.basename(filepath)
        logger.info(f"📁 Обнаружен файл: {filename}")
        
        try:
            df = pd.read_excel(filepath)
            
            # Определяем тип файла по имени или структуре
            if 'products' in filename or ('ID_товара' in df.columns or 'id' in df.columns):
                self.sync_products(df, filepath)
            elif 'orders' in filename or ('ID_заказа' in df.columns or 'status' in df.columns):
                self.sync_orders(df, filepath)
            else:
                logger.warning(f"⚠️ Неизвестный тип файла: {filename}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки {filename}: {e}")
    
    def sync_products(self, df, filepath):
        """Синхронизирует товары из Excel"""
        logger.info(f"🔄 Синхронизация товаров из {os.path.basename(filepath)}")
        
        conn = get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            updated = 0
            added = 0
            
            # Определяем колонки
            id_col = 'id' if 'id' in df.columns else 'ID_товара' if 'ID_товара' in df.columns else None
            name_col = 'name' if 'name' in df.columns else 'Наименование' if 'Наименование' in df.columns else None
            price_col = 'price' if 'price' in df.columns else 'Цена' if 'Цена' in df.columns else None
            stock_col = 'stock' if 'stock' in df.columns else 'Остаток' if 'Остаток' in df.columns else None
            
            if not id_col:
                logger.error("❌ Не найдена колонка с ID товара")
                return
            
            for _, row in df.iterrows():
                product_id = row[id_col]
                
                # Проверяем, существует ли товар
                cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Обновляем существующий
                    updates = []
                    params = []
                    if name_col and pd.notna(row[name_col]):
                        updates.append("name = %s")
                        params.append(row[name_col])
                    if price_col and pd.notna(row[price_col]):
                        updates.append("price = %s")
                        params.append(row[price_col])
                    if stock_col and pd.notna(row[stock_col]):
                        updates.append("stock = %s")
                        params.append(row[stock_col])
                    
                    if updates:
                        params.append(product_id)
                        query = f"UPDATE products SET {', '.join(updates)} WHERE id = %s"
                        cursor.execute(query, params)
                        updated += 1
                else:
                    # Добавляем новый
                    if name_col and pd.notna(row[name_col]):
                        cursor.execute(
                            "INSERT INTO products (id, name, price, stock) VALUES (%s, %s, %s, %s)",
                            (product_id, row[name_col], 
                             row[price_col] if price_col and pd.notna(row[price_col]) else 0,
                             row[stock_col] if stock_col and pd.notna(row[stock_col]) else 0)
                        )
                        added += 1
            
            conn.commit()
            logger.info(f"✅ Синхронизация завершена: обновлено {updated}, добавлено {added}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def sync_orders(self, df, filepath):
        """Синхронизирует статусы заказов из Excel"""
        logger.info(f"🔄 Синхронизация статусов заказов из {os.path.basename(filepath)}")
        
        conn = get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            updated = 0
            
            # Определяем колонки
            id_col = 'id' if 'id' in df.columns else 'ID_заказа' if 'ID_заказа' in df.columns else None
            status_col = 'status' if 'status' in df.columns else 'Статус' if 'Статус' in df.columns else None
            
            if not id_col or not status_col:
                logger.error("❌ Не найдены колонки ID заказа или Статус")
                return
            
            for _, row in df.iterrows():
                order_id = row[id_col]
                status = row[status_col]
                
                # Приводим статус к формату БД
                status_map = {
                    'не оплачен': 'not_paid',
                    'оплачен': 'paid',
                    'доставлен': 'delivered'
                }
                status = status_map.get(str(status).lower(), str(status).lower())
                
                cursor.execute(
                    "UPDATE orders SET status = %s WHERE id = %s",
                    (status, order_id)
                )
                if cursor.rowcount > 0:
                    updated += 1
            
            conn.commit()
            logger.info(f"✅ Обновлено статусов заказов: {updated}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации статусов: {e}")
            conn.rollback()
        finally:
            conn.close()


def start_watcher():
    """Запускает наблюдатель за папкой экспорта"""
    exports_path = EXPORTS_PATH
    
    if not os.path.exists(exports_path):
        os.makedirs(exports_path)
        logger.info(f"📁 Создана папка экспорта: {exports_path}")
    
    event_handler = ExcelHandler()
    observer = Observer()
    observer.schedule(event_handler, exports_path, recursive=False)
    observer.start()
    
    logger.info(f"👀 Наблюдение за папкой: {exports_path}")
    return observer


def sync_from_excel(filepath):
    """Запускает синхронизацию из конкретного файла"""
    handler = ExcelHandler()
    handler.process_file(filepath)


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Запускаем наблюдатель
    observer = start_watcher()
    
    try:
        print("🔄 Синхронизация с 1С запущена. Ожидание файлов...")
        print(f"📁 Папка: {EXPORTS_PATH}")
        print("⏹️ Нажмите Ctrl+C для остановки")
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Синхронизация остановлена")
    
    observer.join()