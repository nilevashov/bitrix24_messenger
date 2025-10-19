# 🚀 Быстрый запуск Bitrix24-Telegram интеграции

## Что нужно для начала

1. **Telegram Bot Token** - получите у [@BotFather](https://t.me/botfather)
2. **Bitrix24 Portal** - доступ к вашему порталу
3. **Публичный сервер** - для webhook'ов

## ⚡ Автоматическая настройка

Запустите один скрипт для полной настройки:

```bash
cd /home/nilevashov/Desktop/apps/bitrix24-messenger
./scripts/setup-integration.sh
```

Скрипт проведет вас через все этапы настройки и запустит приложение.

## 🔧 Ручная настройка

### 1. Настройте переменные окружения

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export BITRIX_DOMAIN="your-portal.bitrix24.com"
export BITRIX_APP_ID="your_app_id"
export BITRIX_APP_SECRET="your_app_secret"
export WEBHOOK_URL="https://yourdomain.com/api/v1/webhooks"
```

### 2. Настройте Telegram webhook

```bash
python3 scripts/setup-telegram-webhook.py
```

### 3. Настройте Bitrix24 webhook

```bash
python3 scripts/setup-bitrix-webhook.py
```

### 4. Запустите приложение

```bash
python3 -m app.main
```

### 5. Откройте админку

- URL: `http://localhost:8000/admin`
- Логин: `admin`
- Пароль: `admin123`

## 📱 Добавление канала Telegram

1. В админке перейдите на вкладку **Channels**
2. Нажмите **Add Channel**
3. Выберите тип: **Telegram**
4. Введите название и токен бота
5. Нажмите **Add Channel**

## 🏢 Настройка Bitrix24

1. В админке перейдите на вкладку **Bitrix24**
2. Введите домен портала
3. Введите ID приложения
4. Включите OpenLines и Timeline
5. Нажмите **Save Configuration**

## 🧪 Тестирование

```bash
python3 scripts/test-integration.py
```

## 📋 Проверка работы

1. **Отправьте сообщение боту в Telegram**
2. **Проверьте, что сообщение появилось в Bitrix24 OpenLines**
3. **Ответьте на сообщение в Bitrix24**
4. **Проверьте, что ответ пришел в Telegram**

## 🐛 Устранение неполадок

### Проверьте логи
```bash
tail -f logs/app.log
```

### Проверьте статус webhook Telegram
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### Остановите приложение
```bash
kill $(cat logs/app.pid)
```

## 📚 Подробная документация

См. [INTEGRATION_SETUP.md](INTEGRATION_SETUP.md) для подробных инструкций.

---

**Готово!** Ваша интеграция Bitrix24-Telegram настроена и готова к работе! 🎉
