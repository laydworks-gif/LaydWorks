@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Збирання сайту. Для пошуку вкажіть адресу сайту, наприклад https://autopolish.com.ua
echo Порожньо (Enter) = локальна збірка, закрита від індексації.
set /p SITE=Адреса сайту: 
python build.py %SITE% || py build.py %SITE%
pause
