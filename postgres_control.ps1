$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"
$White = "White"

function Show-Menu {
    Clear-Host
    Write-Host "========================================" -ForegroundColor $Cyan
    Write-Host "      POSTGRESQL CONTROL" -ForegroundColor $Cyan
    Write-Host "========================================" -ForegroundColor $Cyan
    Write-Host ""
    
    $proc = Get-Process -Name "postgres" -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Status: RUNNING" -ForegroundColor $Green
    } else {
        Write-Host "Status: STOPPED" -ForegroundColor $Red
    }
    
    Write-Host ""
    Write-Host "Select action:" -ForegroundColor $White
    Write-Host "  1. Stop PostgreSQL" -ForegroundColor $White
    Write-Host "  2. Start PostgreSQL" -ForegroundColor $White
    Write-Host "  3. Restart PostgreSQL" -ForegroundColor $White
    Write-Host "  4. Exit" -ForegroundColor $White
    Write-Host ""
}

function Start-Postgres {
    Write-Host ""
    Write-Host "Starting PostgreSQL..." -ForegroundColor $Yellow
    Push-Location "C:\Program Files\PostgreSQL\18\bin"
    & .\pg_ctl -D "C:\postgresql\data" start
    Pop-Location
    Write-Host "Done." -ForegroundColor $Green
    Read-Host "Press Enter"
}

function Stop-Postgres {
    Write-Host ""
    Write-Host "Stopping PostgreSQL..." -ForegroundColor $Yellow
    Push-Location "C:\Program Files\PostgreSQL\18\bin"
    & .\pg_ctl -D "C:\postgresql\data" stop -m fast
    Pop-Location
    Write-Host "Done." -ForegroundColor $Green
    Read-Host "Press Enter"
}

do {
    Show-Menu
    $choice = Read-Host "Your choice"
    switch ($choice) {
        "1" { Stop-Postgres }
        "2" { Start-Postgres }
        "3" { Stop-Postgres; Start-Postgres }
        "4" { exit }
        default { Write-Host "Invalid choice!"; Start-Sleep -Seconds 1 }
    }
} while ($true)
