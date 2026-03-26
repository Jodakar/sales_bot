# cleanup.ps1
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      ОЧИСТКА СИСТЕМЫ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Удаление временных профилей
Write-Host "[1/5] Удаление временных профилей браузера..." -ForegroundColor Yellow
Remove-Item -Path "$env:USERPROFILE\wb_profile_*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:USERPROFILE\chrome_profile_*" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ Готово" -ForegroundColor Green
Start-Sleep -Seconds 1

# 2. Удаление кэша WebDriver
Write-Host "[2/5] Удаление кэша ChromeDriver..." -ForegroundColor Yellow
Remove-Item -Path "$env:USERPROFILE\.wdm" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ Готово" -ForegroundColor Green
Start-Sleep -Seconds 1

# 3. Очистка кэша Chrome
Write-Host "[3/5] Очистка кэша Chrome..." -ForegroundColor Yellow
Remove-Item -Path "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache\*" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ Готово" -ForegroundColor Green
Start-Sleep -Seconds 1

# 4. Очистка кэша pip
Write-Host "[4/5] Очистка кэша pip..." -ForegroundColor Yellow
pip cache purge 2>&1 | Out-Null
Write-Host "   ✅ Готово" -ForegroundColor Green
Start-Sleep -Seconds 1

# 5. Удаление временных файлов
Write-Host "[5/5] Удаление временных файлов..." -ForegroundColor Yellow
Remove-Item -Path "$env:TEMP\pip-*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\chrome_profile_*" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ Готово" -ForegroundColor Green
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      ОЧИСТКА ЗАВЕРШЕНА" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan