# AutoPolish / LaydWorks — Платформа онлайн-запису та Telegram-бот

Платформа онлайн-бронювання детейлінг-послуг для 20 студій з інтерактивним калькулятором вартості та миттєвою передачею заявок у Telegram.

## Структура проекту

- serve.py — веб-сервер та Telegram-бот (чистий Python 3, без сторонніх залежностей).
- sites/ — 20 інтерактивних сайтів студій з каталогом та калькулятором.
- studios/ — каталог даних студій.
- 
equirements.txt — порожній (використовується виключно стандартна бібліотека Python).

## Розгортання на Render (Web Service)

1. **Створення сервісу**:
   - Перейдіть у [Render Dashboard](https://dashboard.render.com).
   - Натисніть **New +** → **Web Service**.
   - Підключіть свій репозиторій laydworks-gif/LaydWorks.

2. **Налаштування збірки**:
   - **Runtime**: Python 3
   - **Build Command**: pip install -r requirements.txt (або залиште порожнім)
   - **Start Command**: python serve.py 

3. **Змінні оточення (Environment Variables)**:
   - AP_SITE = sites
   - AP_PROD = 1
   - TELEGRAM_BOT_TOKEN = <ваш_токен_бота_від_BotFather>
   - TELEGRAM_PASSWORD = <ваш_секретний_пароль_для_start> (мінімум 12 символів)
   - PYTHONUNBUFFERED = 1

Після запуску веб-сервісу надішліть боту в Telegram команду /start <TELEGRAM_PASSWORD>, щоб підключити ваш акаунт для отримання заявок.
