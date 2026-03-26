# Мониторинг доступности BackOffice
$url = "http://127.0.0.1:8000/health"
$logFile = "C:\Users\PC\Yandex.Disk\Проекты\sales_bot\logs\backoffice_monitor.log"
$restartScript = "C:\Users\PC\Yandex.Disk\Проекты\sales_bot\scripts\start_backoffice.vbs"

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
    $status = if ($response.StatusCode -eq 200) { "OK" } else { "ERROR: HTTP $($response.StatusCode)" }
} catch {
    $status = "ERROR: $($_.Exception.Message)"
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "$timestamp - $status"

if ($status -ne "OK") {
    Start-Process wscript.exe -ArgumentList $restartScript -WindowStyle Hidden
    Add-Content -Path $logFile -Value "$timestamp - ПЕРЕЗАПУСК ВЫПОЛНЕН"
}