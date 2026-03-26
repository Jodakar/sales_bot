# Ежедневный бэкап PostgreSQL
$date = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "C:\Users\PC\Yandex.Disk\backups\postgres"
$dbName = "1c_database"
$dbUser = "postgres"
$dbPassword = "TimPostgres2026"

if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force }

# Удаляем бэкапы старше 30 дней
Get-ChildItem -Path $backupDir -Filter "*.sql" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force

$env:PGPASSWORD = $dbPassword
$backupFile = "$backupDir\backup_$dbName_$date.sql"
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U $dbUser -h localhost -p 5432 -F c -b -v -f $backupFile $dbName
$env:PGPASSWORD = ""

if (Test-Path $backupFile) {
    $size = [math]::Round((Get-Item $backupFile).Length / 1MB, 2)
    Write-Host "✅ Бэкап создан: $backupFile ($size MB)"
} else {
    Write-Host "❌ Ошибка создания бэкапа"
}