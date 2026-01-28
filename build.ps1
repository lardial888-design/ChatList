# Скрипт для создания исполняемого файла
Write-Host "Установка зависимостей..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host "`nСоздание исполняемого файла..." -ForegroundColor Green
python -m PyInstaller --onefile --windowed --name "MinimalPyQtApp" main.py

Write-Host "`nИсполняемый файл создан в папке dist\MinimalPyQtApp.exe" -ForegroundColor Green
Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
