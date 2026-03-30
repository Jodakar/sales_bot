import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Настройки SMTP (для timofeyapinfo@gmail.com)
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', 'timofeyapinfo@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'Nbveh2512--')
SMTP_FROM = os.getenv('SMTP_FROM', 'timofeyapinfo@gmail.com')


def send_order_info_to_customer(order_data: dict, customer_email: str, employee_name: str, employee_phone: str, employee_email: str):
    """Отправка информации о заказе клиенту"""
    
    items_html = ""
    for item in order_data.get('items', []):
        items_html += f"""
            <tr>
                <td style="padding:8px;">{item.get('product_name', '—')}</td>
                <td style="padding:8px;">{item.get('quantity', 0)}</td>
                <td style="padding:8px;">{item.get('price', 0):,.0f} ₽</td>
                <td style="padding:8px;">{(item.get('price', 0) * item.get('quantity', 0)):,.0f} ₽</td>
             </tr>
        """
    
    subject = f"Заказ №{order_data.get('order_id')} от {order_data.get('created_at', '')}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
        <h2>📦 Ваш заказ №{order_data.get('order_id')}</h2>
        <p><strong>👤 Клиент:</strong> {order_data.get('customer_name', '—')}</p>
        <p><strong>📞 Телефон:</strong> {order_data.get('customer_phone', '—')}</p>
        <p><strong>📍 Адрес доставки:</strong> {order_data.get('customer_address', '—')}</p>
        <p><strong>🚚 Способ доставки:</strong> {order_data.get('delivery_method', 'Курьер')}</p>
        <p><strong>📝 Комментарий:</strong> {order_data.get('comment', '—')}</p>
        
        <h3>🛍️ Состав заказа:</h3>
        <table border="1" cellpadding="8" cellspacing="0">
            <thead>
                 <tr>
                    <th>Товар</th>
                    <th>Кол-во</th>
                    <th>Цена</th>
                    <th>Сумма</th>
                 </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
            <tfoot>
                 <tr>
                    <td colspan="3"><strong>Итого:</strong></td>
                    <td><strong>{order_data.get('total_amount', 0):,.0f} ₽</strong></td>
                 </tr>
            </tfoot>
        </table>
        
        <hr>
        <p><strong>Реквизиты для оплаты:</strong></p>
        <p>Получатель: ИП Иванов Иван Иванович<br>
        ИНН: 123456789012<br>
        Р/с: 40817810123456789012<br>
        Банк: ПАО Сбербанк<br>
        БИК: 044525225<br>
        К/с: 30101810400000000225<br>
        <strong>Назначение платежа:</strong> Оплата заказа №{order_data.get('order_id')}</p>
        
        <hr>
        <p><strong>Данные сотрудника, оформившего заказ:</strong><br>
        👤 {employee_name}<br>
        📞 {employee_phone}<br>
        📧 {employee_email}</p>
        
        <hr>
        <p>С уважением,<br>
        <strong>TimoFey</strong></p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = customer_email
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True, "Письмо отправлено"
    except Exception as e:
        return False, str(e)


def send_delivery_notification(employee_email: str, employee_name: str, order_id: int, order_data: tuple):
    """Отправка уведомления сотруднику доставки о новом оплаченном заказе"""
    
    order_id_val, customer_name, total_amount = order_data
    
    subject = f"🔔 Новый оплаченный заказ №{order_id_val}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
        <h2>📦 Заказ №{order_id_val} оплачен!</h2>
        <p><strong>👤 Клиент:</strong> {customer_name}</p>
        <p><strong>💰 Сумма:</strong> {total_amount:,.0f} ₽</p>
        <p><strong>📅 Дата оплаты:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        <hr>
        <p>Для просмотра деталей заказа перейдите по ссылке:</p>
        <p><a href="http://127.0.0.1:8001/orders/{order_id_val}">http://127.0.0.1:8001/orders/{order_id_val}</a></p>
        <hr>
        <p>С уважением,<br>
        <strong>TimoFey</strong></p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = employee_email
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)