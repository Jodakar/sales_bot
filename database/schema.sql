-- =====================================================
-- Схема базы данных для системы продаж
-- PostgreSQL 18
-- =====================================================

-- Удаляем таблицы, если существуют (для чистой установки)
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- =====================================================
-- Таблица customers (клиенты)
-- =====================================================
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    last_order_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE customers IS 'Клиенты';
COMMENT ON COLUMN customers.id IS 'Уникальный ID клиента';
COMMENT ON COLUMN customers.name IS 'Имя клиента';
COMMENT ON COLUMN customers.phone IS 'Телефон (+7...)';
COMMENT ON COLUMN customers.address IS 'Адрес доставки по умолчанию';
COMMENT ON COLUMN customers.last_order_date IS 'Дата последнего заказа';
COMMENT ON COLUMN customers.created_at IS 'Дата создания записи';
COMMENT ON COLUMN customers.updated_at IS 'Дата обновления записи';

-- =====================================================
-- Таблица products (товары)
-- =====================================================
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(12,2) NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    category VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE products IS 'Товары';
COMMENT ON COLUMN products.id IS 'ID товара (из 1С)';
COMMENT ON COLUMN products.name IS 'Наименование товара';
COMMENT ON COLUMN products.price IS 'Цена';
COMMENT ON COLUMN products.stock IS 'Остаток';
COMMENT ON COLUMN products.description IS 'Описание товара';
COMMENT ON COLUMN products.category IS 'Категория товара';
COMMENT ON COLUMN products.updated_at IS 'Дата обновления';

-- =====================================================
-- Таблица orders (заказы)
-- =====================================================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20),
    customer_address TEXT,
    comment TEXT,
    delivery_method VARCHAR(50),
    delivery_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'not_paid',
    total_amount DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE orders IS 'Заказы';
COMMENT ON COLUMN orders.id IS 'ID заказа (уникальный)';
COMMENT ON COLUMN orders.customer_name IS 'Имя клиента';
COMMENT ON COLUMN orders.customer_phone IS 'Телефон';
COMMENT ON COLUMN orders.customer_address IS 'Адрес доставки';
COMMENT ON COLUMN orders.comment IS 'Комментарий к заказу';
COMMENT ON COLUMN orders.delivery_method IS 'Способ доставки';
COMMENT ON COLUMN orders.delivery_time IS 'Желаемое время доставки';
COMMENT ON COLUMN orders.status IS 'Статус: not_paid, paid, delivered';
COMMENT ON COLUMN orders.total_amount IS 'Итоговая сумма заказа';
COMMENT ON COLUMN orders.created_at IS 'Дата создания заказа';
COMMENT ON COLUMN orders.updated_at IS 'Дата обновления заказа';

-- =====================================================
-- Таблица order_items (позиции заказа)
-- =====================================================
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price DECIMAL(12,2) NOT NULL,
    total DECIMAL(12,2) NOT NULL
);

COMMENT ON TABLE order_items IS 'Позиции заказа';
COMMENT ON COLUMN order_items.id IS 'ID записи';
COMMENT ON COLUMN order_items.order_id IS 'ID заказа';
COMMENT ON COLUMN order_items.product_id IS 'ID товара';
COMMENT ON COLUMN order_items.product_name IS 'Наименование товара на момент заказа';
COMMENT ON COLUMN order_items.quantity IS 'Количество';
COMMENT ON COLUMN order_items.price IS 'Цена за единицу';
COMMENT ON COLUMN order_items.total IS 'Итого по позиции';

-- =====================================================
-- Индексы для ускорения запросов
-- =====================================================
CREATE INDEX idx_orders_customer_name ON orders(customer_name);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_customers_phone ON customers(phone);

-- =====================================================
-- Функция автоматического обновления updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для автоматического обновления updated_at
CREATE TRIGGER trigger_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Тестовые данные (для проверки)
-- =====================================================

-- Добавляем тестовые товары
INSERT INTO products (name, price, stock, description, category) VALUES
('Телевизор Samsung 32"', 22318, 10, 'Full HD, Smart TV, Wi-Fi', 'Телевизоры'),
('Смартфон Samsung Galaxy S25', 59999, 5, '256GB, 8GB RAM, 5G', 'Смартфоны'),
('Ноутбук Lenovo ThinkPad', 45000, 3, '16GB RAM, 512GB SSD', 'Ноутбуки'),
('Наушники Sony WH-1000XM5', 29990, 8, 'Беспроводные, шумоподавление', 'Аудио');

-- Добавляем тестового клиента
INSERT INTO customers (name, phone, address) VALUES
('Тим', '+7 925 123-45-67', 'г. Москва, ул. Ленина 1');

-- Добавляем тестовый заказ
INSERT INTO orders (customer_name, customer_phone, customer_address, status, total_amount) VALUES
('Тим', '+7 925 123-45-67', 'г. Москва, ул. Ленина 1', 'paid', 82318);

-- Добавляем позиции заказа
INSERT INTO order_items (order_id, product_id, product_name, quantity, price, total) VALUES
(1, 1, 'Телевизор Samsung 32"', 1, 22318, 22318),
(1, 2, 'Смартфон Samsung Galaxy S25', 1, 59999, 59999);

-- =====================================================
-- Завершение
-- =====================================================
SELECT '✅ База данных успешно создана!' AS status;