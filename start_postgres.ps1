# start_postgres.ps1 - отдельный скрипт для запуска PostgreSQL
# Запускается из check_all.ps1 в отдельном окне

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      ЗАПУСК POSTGRESQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$pgBin = "C:\Program Files\PostgreSQL\18\bin"
$pgData = "C:\postgresql\data"

Write-Host "📁 Папка данных: $pgData" -ForegroundColor White
Write-Host "📁 Папка с pg_ctl: $pgBin" -ForegroundColor White
Write-Host ""

if (-not (Test-Path $pgData)) {
    Write-Host "❌ Папка данных PostgreSQL не найдена: $pgData" -ForegroundColor Red
    Write-Host ""
    Read-Host "Нажмите Enter для закрытия окна"
    exit 1
}

Push-Location $pgBin

# Проверяем, работает ли PostgreSQL
$testResult = & .\psql -U postgres -d postgres -c "SELECT 1;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PostgreSQL уже работает!" -ForegroundColor Green
    Pop-Location
    Write-Host ""
    Read-Host "Нажмите Enter для закрытия окна"
    exit 0
}

Write-Host "🚀 Запуск PostgreSQL..." -ForegroundColor Yellow
Write-Host "   Выполняю: .\pg_ctl -D `"$pgData`" start -w -t 30" -ForegroundColor Gray
Write-Host ""

$result = & .\pg_ctl -D $pgData start -w -t 30 2>&1
$exitCode = $LASTEXITCODE

# Выводим результат
$result | ForEach-Object {
    Write-Host $_ -ForegroundColor Gray
}

Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "✅ PostgreSQL успешно запущен!" -ForegroundColor Green
} else {
    Write-Host "❌ Ошибка запуска PostgreSQL (код: $exitCode)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Попробуйте запустить вручную:" -ForegroundColor Yellow
    Write-Host "   cd `"$pgBin`"" -ForegroundColor White
    Write-Host "   .\pg_ctl -D `"$pgData`" start" -ForegroundColor White
}

Pop-Location

Write-Host ""
Read-Host "Нажмите Enter для закрытия окна"