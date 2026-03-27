-- Создаём роль dev, если её нет
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'employees_role') THEN
        CREATE TYPE employees_role AS ENUM ('dev', 'admin', 'manager');
    END IF;
END $$;

-- Обновляем тип колонки role (если нужно)
ALTER TABLE employees ALTER COLUMN role TYPE VARCHAR(20);

-- Добавляем поле can_edit_managers, если его нет
ALTER TABLE employees ADD COLUMN IF NOT EXISTS can_edit_managers BOOLEAN DEFAULT FALSE;

-- Обновляем существующего администратора на разработчика
UPDATE employees 
SET role = 'dev', 
    can_edit_managers = true,
    can_edit_company_details = true,
    can_upload_excel = true
WHERE login = 'admin';

-- Проверяем
SELECT employee_id, full_name, email, role, login, 
       can_edit_managers, can_edit_company_details, can_upload_excel 
FROM employees;