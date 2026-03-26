# check_encoding.ps1
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      ПРОВЕРКА КОДИРОВКИ СИСТЕМЫ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Проверка кодировки Windows
Write-Host "1️⃣ WINDOWS (кодовая страница)" -ForegroundColor Yellow
$chcp = chcp
Write-Host "   $chcp" -ForegroundColor White
if ($chcp -like "*65001*") {
    Write-Host "   ✅ UTF-8 (65001) установлена" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ Текущая: $chcp, ожидается 65001" -ForegroundColor Red
}
Write-Host ""

# 2. Проверка PowerShell профиля
Write-Host "2️⃣ POWERSHELL ПРОФИЛЬ" -ForegroundColor Yellow
$profilePath = "$env:USERPROFILE\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
if (Test-Path $profilePath) {
    Write-Host "   ✅ Профиль существует" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ Профиль не найден" -ForegroundColor Yellow
}
Write-Host ""

# 3. Проверка psqlrc.conf
Write-Host "3️⃣ PSQL НАСТРОЙКИ" -ForegroundColor Yellow
$psqlrcPath = "$env:APPDATA\postgresql\psqlrc.conf"
if (Test-Path $psqlrcPath) {
    Write-Host "   ✅ Файл существует: $psqlrcPath" -ForegroundColor Green
    $content = Get-Content $psqlrcPath -Raw
    if ($content -like "*UTF8*") {
        Write-Host "   ✅ Настройка UTF-8 найдена" -ForegroundColor Green
    }
} else {
    Write-Host "   ⚠️ Файл не найден" -ForegroundColor Yellow
}
Write-Host ""

# 4. Проверка PostgreSQL
Write-Host "4️⃣ POSTGRESQL" -ForegroundColor Yellow
cd "C:\Program Files\PostgreSQL\18\bin"
$result = & .\psql -U postgres -d 1c_database -t -c "SELECT name FROM products LIMIT 1;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ PostgreSQL доступен" -ForegroundColor Green
    Write-Host "   Пример данных: $result" -ForegroundColor White
} else {
    Write-Host "   ❌ PostgreSQL недоступен" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      ПРОВЕРКА ЗАВЕРШЕНА" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan