# export_project.ps1
# Скрипт для полного экспорта всех файлов проекта в один текстовый файл
# Сохраняет структуру папок и содержимое всех файлов

param(
    [string]$ProjectPath = "C:\Users\PC\Yandex.Disk\Проекты\sales_bot",
    [string]$OutputPath = "$env:USERPROFILE\Downloads\sales_bot_export.txt"
)

# Переключаемся в папку проекта
cd $ProjectPath
Write-Host "📁 Сканируем проект: $ProjectPath" -ForegroundColor Cyan

# Расширения файлов для экспорта
$extensions = @(
    "*.py", "*.ps1", "*.sql", "*.html", "*.css", "*.js", 
    "*.json", "*.txt", "*.md", "*.env", "*.gitignore", "*.conf"
)

# Папки для исключения
$excludeFolders = @("venv", "__pycache__", ".git", "logs", "uploads", "node_modules")

# Функция для получения всех файлов
function Get-ProjectFiles {
    $allFiles = @()
    foreach ($ext in $extensions) {
        $files = Get-ChildItem -Path $ProjectPath -Filter $ext -Recurse -File -ErrorAction SilentlyContinue
        $allFiles += $files
    }
    # Удаляем дубликаты и исключаем папки
    $allFiles = $allFiles | Sort-Object FullName -Unique
    $allFiles = $allFiles | Where-Object {
        $exclude = $false
        foreach ($folder in $excludeFolders) {
            if ($_.FullName -like "*\$folder\*") { $exclude = $true }
        }
        -not $exclude
    }
    return $allFiles
}

Write-Host "🔍 Поиск файлов..." -ForegroundColor Yellow
$files = Get-ProjectFiles
Write-Host "✅ Найдено файлов: $($files.Count)" -ForegroundColor Green

# Создаем файл экспорта
$content = @"
================================================================================
ЭКСПОРТ ПРОЕКТА sales_bot
================================================================================
Дата экспорта: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Путь проекта: $ProjectPath
Всего файлов: $($files.Count)
================================================================================

"@

$content | Out-File -FilePath $OutputPath -Encoding UTF8

# Счетчики
$counter = 0
$total = $files.Count

# Обходим все файлы
foreach ($file in $files) {
    $counter++
    $relativePath = $file.FullName.Replace($ProjectPath, "").TrimStart("\")
    $fileSize = "{0:N2}" -f ($file.Length / 1KB)
    
    Write-Host "[$counter/$total] Обрабатываю: $relativePath" -ForegroundColor Gray
    
    $header = @"
`n`n================================================================================
ФАЙЛ: $relativePath
================================================================================
Размер: $fileSize KB
Путь: $($file.FullName)
================================================================================

"@
    
    $header | Out-File -FilePath $OutputPath -Encoding UTF8 -Append
    
    # Читаем содержимое файла
    try {
        $fileContent = Get-Content -Path $file.FullName -Raw -ErrorAction Stop
        $fileContent | Out-File -FilePath $OutputPath -Encoding UTF8 -Append
    } catch {
        $errorMsg = "[ОШИБКА ЧТЕНИЯ: $_]`n"
        $errorMsg | Out-File -FilePath $OutputPath -Encoding UTF8 -Append
    }
}

# Добавляем информацию о структуре папок
Write-Host "`n📁 Добавляем структуру папок..." -ForegroundColor Yellow

$treeContent = @"
`n`n================================================================================
СТРУКТУРА ПАПОК ПРОЕКТА
================================================================================

"@
$treeContent | Out-File -FilePath $OutputPath -Encoding UTF8 -Append

# Создаем дерево папок
$treeOutput = & tree /F /A 2>$null
$treeOutput | Out-File -FilePath $OutputPath -Encoding UTF8 -Append

# Итоговая информация
$footer = @"

`n`n================================================================================
ИТОГОВАЯ ИНФОРМАЦИЯ
================================================================================
Дата завершения: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Всего обработано файлов: $counter
Размер экспорта: {0:N2} MB
================================================================================
"@ -f ((Get-Item $OutputPath).Length / 1MB)

$footer | Out-File -FilePath $OutputPath -Encoding UTF8 -Append

Write-Host "`n✅ ГОТОВО!" -ForegroundColor Green
Write-Host "📄 Файл сохранен: $OutputPath" -ForegroundColor Cyan
Write-Host "📏 Размер файла: {0:N2} MB" -f ((Get-Item $OutputPath).Length / 1MB) -ForegroundColor Yellow

# Открываем файл
Start-Process notepad $OutputPath