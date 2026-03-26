# ============================================
# УНИВЕРСАЛЬНЫЙ СКРИПТ ПРОВЕРКИ И ВОССТАНОВЛЕНИЯ
# Запуск: powershell -ExecutionPolicy Bypass -File .\check_all.ps1
# ============================================

$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"
$White = "White"
$Gray = "Gray"

$global:postgresRunning = $false
$global:pythonRunning = $false
$global:postgresFixed = $false
$global:pythonFixed = $false

function Write-Header {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $Cyan
    Write-Host "      $($args[0])" -ForegroundColor $Cyan
    Write-Host "========================================" -ForegroundColor $Cyan
}

function Write-OK { param($m) Write-Host "   ✅ $m" -ForegroundColor $Green }
function Write-Error { param($m) Write-Host "   ❌ $m" -ForegroundColor $Red }
function Write-Warning { param($m) Write-Host "   ⚠️ $m" -ForegroundColor $Yellow }
function Write-Info { param($m) Write-Host "   ℹ️ $m" -ForegroundColor $Gray }
function Write-Success { param($m) Write-Host "   🎉 $m" -ForegroundColor $Green }

function Ask-YesNo {
    param($Question)
    do {
        $response = Read-Host "$Question (y/n)"
    } while ($response -notmatch '^[ynYN]$')
    return ($response -eq 'y' -or $response -eq 'Y')
}

Clear-Host

# ============================================
# 1. ПРОВЕРКА ПУТЕЙ И ФАЙЛОВ
# ============================================
Write-Header "1. ПРОВЕРКА СТРУКТУРЫ ПРОЕКТА"

$projectPath = "C:\Users\PC\Yandex.Disk\Проекты\sales_bot"
Write-Host "📁 Папка проекта: $projectPath" -ForegroundColor $White

if (Test-Path $projectPath) {
    Write-OK "Папка проекта найдена"
    cd $projectPath
} else {
    Write-Error "Папка проекта не найдена!"
    exit
}

$requiredFiles = @(
    "bot/main.py", "bot/utils/db.py", "bot/utils/send_message.py",
    "bot/keyboards.py", "bot/handlers/menu.py", "bot/handlers/orders.py",
    "bot/handlers/products.py", "bot/handlers/customers.py", "bot/handlers/reports.py",
    "sync/scheduler.py", "database/schema.sql", "requirements.txt", ".env",
    "start_postgres.ps1"
)

Write-Host ""
Write-Host "📄 Проверка файлов проекта:" -ForegroundColor $White
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-OK "$file"
    } else {
        Write-Error "$file (отсутствует)"
        if ($file -eq "start_postgres.ps1") {
            Write-Info "Создаю start_postgres.ps1..."
            @'
# start_postgres.ps1 - отдельный скрипт для запуска PostgreSQL
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
    Write-Host "❌ Папка данных не найдена: $pgData" -ForegroundColor Red
    Read-Host "Нажмите Enter"
    exit 1
}

Push-Location $pgBin

$testResult = & .\psql -U postgres -d postgres -c "SELECT 1;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PostgreSQL уже работает!" -ForegroundColor Green
    Pop-Location
    Read-Host "Нажмите Enter"
    exit 0
}

Write-Host "🚀 Запуск PostgreSQL..." -ForegroundColor Yellow
Write-Host "   Выполняю: .\pg_ctl -D `"$pgData`" start -w -t 30" -ForegroundColor Gray
Write-Host ""

$result = & .\pg_ctl -D $pgData start -w -t 30 2>&1
$exitCode = $LASTEXITCODE

$result | ForEach-Object { Write-Host $_ -ForegroundColor Gray }

Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "✅ PostgreSQL успешно запущен!" -ForegroundColor Green
} else {
    Write-Host "❌ Ошибка запуска (код: $exitCode)" -ForegroundColor Red
}

Pop-Location
Read-Host "Нажмите Enter"
'@ | Out-File -FilePath "start_postgres.ps1" -Encoding UTF8
            Write-OK "Файл start_postgres.ps1 создан"
        }
    }
}

Start-Sleep -Seconds 1

# ============================================
# 2. ПРОВЕРКА И ЗАПУСК POSTGRESQL
# ============================================
Write-Header "2. ПРОВЕРКА POSTGRESQL"

# Проверяем, работает ли PostgreSQL
$pgBin = "C:\Program Files\PostgreSQL\18\bin"
Push-Location $pgBin
$testResult = & .\psql -U postgres -d postgres -c "SELECT 1;" 2>&1
$dbWorking = ($LASTEXITCODE -eq 0)
Pop-Location

if ($dbWorking) {
    $global:postgresRunning = $true
    Write-OK "PostgreSQL работает"
    
    # Получаем статистику
    Push-Location $pgBin
    $products = & .\psql -U postgres -d 1c_database -t -c "SELECT COUNT(*) FROM products;" 2>&1
    $orders = & .\psql -U postgres -d 1c_database -t -c "SELECT COUNT(*) FROM orders;" 2>&1
    Pop-Location
    Write-OK "Товаров в каталоге: $products"
    Write-OK "Заказов в базе: $orders"
} else {
    $global:postgresRunning = $false
    Write-Error "PostgreSQL не работает"
    Write-Info "Запуск PostgreSQL в отдельном окне..."
    
    $startScript = "$projectPath\start_postgres.ps1"
    if (Test-Path $startScript) {
        Write-Info "Открываю окно запуска PostgreSQL..."
        $process = Start-Process powershell -ArgumentList "-NoExit -File `"$startScript`"" -WindowStyle Normal -PassThru
        
        Write-Info "⏳ Ожидание завершения запуска PostgreSQL..."
        Write-Info "   (закройте окно PostgreSQL после запуска)"
        $process.WaitForExit()
        
        Start-Sleep -Seconds 2
        Push-Location $pgBin
        $testResult = & .\psql -U postgres -d postgres -c "SELECT 1;" 2>&1
        $dbWorking = ($LASTEXITCODE -eq 0)
        Pop-Location
        
        if ($dbWorking) {
            Write-OK "PostgreSQL успешно запущен!"
            $global:postgresRunning = $true
            $global:postgresFixed = $true
        } else {
            Write-Error "PostgreSQL не запустился после выполнения скрипта"
        }
    } else {
        Write-Error "Скрипт запуска не найден: $startScript"
    }
}

Start-Sleep -Seconds 1

# ============================================
# 3. ПРОВЕРКА И ЗАПУСК PYTHON ПРОЦЕССОВ
# ============================================
Write-Header "3. ПРОВЕРКА БОТА И ПЛАНИРОВЩИКА"

$python = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($python) {
    $global:pythonRunning = $true
    Write-OK "Найдено процессов Python: $($python.Count)"
    
    $botFound = $false
    $schedulerFound = $false
    foreach ($p in $python) {
        try {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($p.Id)").CommandLine
            if ($cmdLine -like "*bot.main*") { $botFound = $true }
            if ($cmdLine -like "*scheduler*") { $schedulerFound = $true }
        } catch {}
    }
    if ($botFound) { Write-OK "Бот найден" }
    if ($schedulerFound) { Write-OK "Планировщик найден" }
    
} else {
    $global:pythonRunning = $false
    Write-Error "Python процессы не найдены!"
    Write-Info "Запуск бота и планировщика..."
    
    Write-Info "Запуск бота..."
    Start-Process powershell -ArgumentList "-NoExit -Command cd '$projectPath'; python -m bot.main"
    Start-Sleep -Seconds 2
    
    Write-Info "Запуск планировщика..."
    Start-Process powershell -ArgumentList "-NoExit -Command cd '$projectPath'; python sync\scheduler.py"
    Start-Sleep -Seconds 2
    
    $global:pythonRunning = $true
    $global:pythonFixed = $true
    Write-OK "Бот и планировщик запущены"
}

Start-Sleep -Seconds 1

# ============================================
# 4. ПРОВЕРКА КОДИРОВКИ
# ============================================
Write-Header "4. ПРОВЕРКА КОДИРОВКИ"

$chcp = chcp
if ($chcp -like "*65001*") {
    Write-OK "Кодовая страница: UTF-8 (65001)"
} else {
    Write-Warning "Кодовая страница: $chcp"
    Write-Info "Устанавливаю UTF-8..."
    chcp 65001 | Out-Null
    Write-OK "UTF-8 установлена"
}

$psqlrc = "$env:APPDATA\postgresql\psqlrc.conf"
if (-not (Test-Path $psqlrc)) {
    Write-Info "Создаю настройки psql..."
    New-Item -Path "$env:APPDATA\postgresql" -ItemType Directory -Force | Out-Null
    @"
\encoding UTF8
\pset pager off
"@ | Out-File -FilePath $psqlrc -Encoding UTF8
    Write-OK "Настройки psql созданы"
} else {
    $content = Get-Content $psqlrc -Raw
    if ($content -notlike "*UTF8*") {
        Add-Content -Path $psqlrc -Value "`n\encoding UTF8" -Encoding UTF8
        Write-OK "Настройка UTF-8 добавлена в psql"
    } else {
        Write-OK "psql настроен на UTF-8"
    }
}

Start-Sleep -Seconds 1

# ============================================
# 5. ПРОВЕРКА ЯНДЕКС.ДИСКА
# ============================================
Write-Header "5. ПРОВЕРКА ЯНДЕКС.ДИСКА"

$yandexPath = "C:\Users\PC\Yandex.Disk"
if (Test-Path $yandexPath) {
    Write-OK "Папка Яндекс.Диска: $yandexPath"
    
    $backups = "$yandexPath\backups"
    if (-not (Test-Path $backups)) {
        New-Item -Path $backups -ItemType Directory -Force | Out-Null
        Write-OK "Папка backups создана"
    } else {
        $sqlFiles = (Get-ChildItem $backups -Filter "*.sql" -ErrorAction SilentlyContinue).Count
        Write-OK "Папка backups: $sqlFiles SQL-файлов"
    }
    
    $exports = "$yandexPath\exports"
    if (-not (Test-Path $exports)) {
        New-Item -Path $exports -ItemType Directory -Force | Out-Null
        Write-OK "Папка exports создана"
    } else {
        $xlsxFiles = (Get-ChildItem $exports -Filter "*.xlsx" -ErrorAction SilentlyContinue).Count
        Write-OK "Папка exports: $xlsxFiles Excel-файлов"
    }
} else {
    Write-Error "Яндекс.Диск не найден"
}

Start-Sleep -Seconds 1

# ============================================
# 6. ПРОВЕРКА АВТОЗАГРУЗКИ
# ============================================
Write-Header "6. ПРОВЕРКА АВТОЗАГРУЗКИ"

$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

$scriptsPath = "C:\Scripts"
if (-not (Test-Path $scriptsPath)) {
    New-Item -Path $scriptsPath -ItemType Directory -Force | Out-Null
    Write-OK "Папка C:\Scripts создана"
}

$postgresBat = "$scriptsPath\start_postgres.bat"
if (-not (Test-Path $postgresBat)) {
    @"
@echo off
echo Starting PostgreSQL...
cd "C:\Program Files\PostgreSQL\18\bin"
pg_ctl -D "C:\postgresql\data" start
echo PostgreSQL started!
"@ | Out-File -FilePath $postgresBat -Encoding ASCII
    Write-OK "Создан start_postgres.bat"
}

$shortcuts = @(
    @{Name="sales_bot.lnk"; Target="python.exe"; Args="-m bot.main"; Desc="Бот"},
    @{Name="scheduler.lnk"; Target="python.exe"; Args="sync\scheduler.py"; Desc="Планировщик"},
    @{Name="start_postgres.lnk"; Target=$postgresBat; Args=""; Desc="PostgreSQL"}
)

foreach ($s in $shortcuts) {
    $path = "$startup\$($s.Name)"
    if (-not (Test-Path $path)) {
        Write-Info "Создаю ярлык для $($s.Desc)..."
        $ws = New-Object -ComObject WScript.Shell
        $shortcut = $ws.CreateShortcut($path)
        $shortcut.TargetPath = $s.Target
        if ($s.Args) { $shortcut.Arguments = $s.Args }
        $shortcut.WorkingDirectory = $projectPath
        $shortcut.Save()
        Write-OK "Ярлык создан: $($s.Name)"
    } else {
        Write-OK "$($s.Name)"
    }
}

Start-Sleep -Seconds 1

# ============================================
# 7. АВТОМАТИЧЕСКАЯ ОЧИСТКА СИСТЕМЫ
# ============================================
Write-Header "7. АВТОМАТИЧЕСКАЯ ОЧИСТКА СИСТЕМЫ"

Write-Host "🗑️ Удаление временных файлов..." -ForegroundColor $White

Remove-Item -Path "$env:USERPROFILE\wb_profile_*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:USERPROFILE\chrome_profile_*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\chrome_profile_*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\wb_profile_*" -Recurse -Force -ErrorAction SilentlyContinue
Write-OK "Временные профили удалены"

Remove-Item -Path "$env:USERPROFILE\.wdm" -Recurse -Force -ErrorAction SilentlyContinue
Write-OK "Кэш ChromeDriver удалён"

Remove-Item -Path "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Code Cache\*" -Recurse -Force -ErrorAction SilentlyContinue
Write-OK "Кэш Chrome очищен"

pip cache purge 2>&1 | Out-Null
Write-OK "Кэш pip очищен"

Remove-Item -Path "$env:TEMP\pip-*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\python-*" -Recurse -Force -ErrorAction SilentlyContinue
Write-OK "Временные файлы Python удалены"

Remove-Item -Path "$env:USERPROFILE\Downloads\avito_*.xlsx" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:USERPROFILE\Downloads\wb_*.xlsx" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:USERPROFILE\Downloads\avito_parser_*.xlsx" -Force -ErrorAction SilentlyContinue
Write-OK "Старые Excel-файлы удалены"

Clear-RecycleBin -Force -ErrorAction SilentlyContinue
Write-OK "Корзина очищена"

Start-Sleep -Seconds 1

# ============================================
# 8. АВТОМАТИЧЕСКОЕ УДАЛЕНИЕ ЛИШНИХ ПАПОК
# ============================================
Write-Header "8. АВТОМАТИЧЕСКОЕ УДАЛЕНИЕ ЛИШНИХ ПАПОК"

$oldFolders = @(
    @{Path="C:\Users\PC\Yandex.Disk\Проекты\avito_parser"; Desc="Avito парсер (старый)"},
    @{Path="C:\Users\PC\Yandex.Disk\Проекты\wb_parser"; Desc="WB парсер (старый)"},
    @{Path="D:\projects"; Desc="Старая папка проектов"}
)

foreach ($folder in $oldFolders) {
    if (Test-Path $folder.Path) {
        Write-Warning "Удаляю старую папку: $($folder.Path)"
        Remove-Item -Path $folder.Path -Recurse -Force -ErrorAction SilentlyContinue
        Write-OK "Папка удалена: $($folder.Desc)"
    }
}

Start-Sleep -Seconds 1

# ============================================
# 9. ПРОВЕРКА БЭКАПОВ
# ============================================
Write-Header "9. ПРОВЕРКА БЭКАПОВ"

if (Test-Path "$yandexPath\backups") {
    $backups = Get-ChildItem "$yandexPath\backups" -Filter "*.sql" | Sort-Object LastWriteTime -Descending
    if ($backups) {
        Write-OK "Последний бэкап: $($backups[0].Name) ($([math]::Round($backups[0].Length/1024, 2)) KB)"
        Write-OK "Всего бэкапов: $($backups.Count)"
    } else {
        Write-Warning "Бэкапов не найдено"
    }
}

Start-Sleep -Seconds 1

# ============================================
# 10. ИТОГОВЫЙ ОТЧЁТ
# ============================================
Write-Header "ИТОГОВЫЙ ОТЧЁТ"

$allOk = $true
if (-not $global:postgresRunning) { 
    $allOk = $false
    if ($global:postgresFixed) { Write-OK "PostgreSQL: запущен (исправлено)" }
    else { Write-Error "PostgreSQL не запущен" }
}
if (-not $global:pythonRunning) { 
    $allOk = $false
    if ($global:pythonFixed) { Write-OK "Python процессы: запущены (исправлено)" }
    else { Write-Error "Python процессы не найдены" }
}

if ($allOk) {
    Write-Success "ВСЕ КОМПОНЕНТЫ РАБОТАЮТ!"
} else {
    Write-Warning "ЕСТЬ ПРОБЛЕМЫ! Смотрите список выше."
}

Write-Host ""
Write-Host "📋 БЫСТРЫЕ КОМАНДЫ:" -ForegroundColor $White
Write-Host "   • Запуск бота: python -m bot.main" -ForegroundColor $Gray
Write-Host "   • Запуск планировщика: python sync\scheduler.py" -ForegroundColor $Gray
Write-Host "   • Запуск PostgreSQL: .\start_postgres.ps1" -ForegroundColor $Gray
Write-Host ""
Write-Host "✅ Проверка завершена в $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor $Green
Write-Host ""