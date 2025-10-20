# Bitrix24-Telegram Integration Setup Guide

Это руководство поможет вам настроить двустороннее общение между Bitrix24 и Telegram.

## 🎯 Что мы настроим

- **Клиент в Telegram** → **Менеджер в Bitrix24**: Сообщения от клиентов в Telegram будут поступать в Bitrix24 OpenLines
- **Менеджер в Bitrix24** → **Клиент в Telegram**: Ответы менеджеров из Bitrix24 будут отправляться клиентам в Telegram

## 🏗️ Архитектура системы

Система использует **мультитенантную архитектуру**:
- **Один сервер** обрабатывает webhook'и для всех клиентов
- **Webhook URL'ы** одинаковые для всех tenant'ов
- **Tenant определяется автоматически** по содержимому webhook'а:
  - **Telegram**: по активным каналам
  - **Bitrix24**: по секрету webhook'а или домену

## 📋 Предварительные требования

1. **Telegram Bot Token**
   - Создайте бота через [@BotFather](https://t.me/botfather)
   - Получите токен бота

2. **Bitrix24 Portal**
   - Доступ к Bitrix24 порталу
   - Права администратора для настройки приложений

3. **Сервер с публичным IP**
   - Для получения webhook'ов от Telegram и Bitrix24

## 🚀 Пошаговая настройка

### Шаг 1: Настройка Telegram бота

1. **Создайте бота в Telegram:**
   ```bash
   # Отправьте команду @BotFather в Telegram
   /newbot
   # Следуйте инструкциям и получите токен
   ```

2. **Настройте webhook для Telegram:**
   ```bash
   cd /home/nilevashov/Desktop/apps/bitrix24-messenger

   # Установите переменные окружения
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_WEBHOOK_SECRET="generated-channel-secret"
   export WEBHOOK_URL="https://yourdomain.com/api/v1/webhooks/channels/telegram/${TELEGRAM_WEBHOOK_SECRET}"

   # Запустите скрипт настройки
   python scripts/setup-telegram-webhook.py
   ```

### Шаг 2: Настройка Bitrix24

1. **Создайте приложение в Bitrix24:**
   - Перейдите в Bitrix24 → Приложения → Разработчикам
   - Создайте новое приложение
   - Укажите права доступа: `crm`, `im`, `imopenlines`, `disk`

2. **Настройте webhook в Bitrix24:**
   ```bash
   # Установите переменные окружения
   export BITRIX_DOMAIN="your-portal.bitrix24.com"
   export BITRIX_APP_ID="your_app_id"
   export BITRIX_APP_SECRET="your_app_secret"
   export WEBHOOK_URL="https://yourdomain.com/api/v1/webhooks/bitrix"
   
   # Запустите скрипт настройки
   python scripts/setup-bitrix-webhook.py
   ```

3. **Настройте webhook события в Bitrix24:**
   - Перейдите в Bitrix24 → Приложения → Webhooks
   - Создайте новый webhook со следующими событиями:
     - `ONIMBOTMESSAGEADD` - Сообщения от операторов
     - `ONIMOPENLINESESSIONSTART` - Начало сессии
     - `ONIMOPENLINESESSIONFINISH` - Завершение сессии
     - `ONCRMLEADADD` - Новые лиды
     - `ONCRMCONTACTADD` - Новые контакты
  - Укажите URL: `https://yourdomain.com/api/v1/webhooks/bitrix`
  - Добавьте события CRM: `ONCRMDEALADD`, `ONCRMDEALUPDATE`, `ONCRMDEALDELETE` — они позволяют коннектору привязывать сделки к контактам для последующего поиска chat_id.
  - ⚠️ Коннектор **не изменяет** сделки в Bitrix24: события используются только для чтения идентификаторов контактов. Убедитесь, что у каждой сделки есть привязанный контакт — тогда старт переписки из карточки сделки корректно найдёт нужный чат.

### Шаг 3: Настройка канала в админке

1. **Запустите приложение:**
   ```bash
   cd /home/nilevashov/Desktop/apps/bitrix24-messenger
   python -m app.main
   ```

2. **Откройте админку:**
   - Перейдите по адресу: `http://localhost:8000/admin`
   - Войдите с учетными данными: `admin` / `admin123`

3. **Добавьте канал Telegram:**
   - Перейдите на вкладку "Channels"
   - Нажмите "Add Channel"
   - Выберите тип: "Telegram"
   - Заполните поля:
     - **Name** — удобное имя канала
     - **bot_token** — токен вашего бота
     - **webhook_secret** — значение `TELEGRAM_WEBHOOK_SECRET` из шага настройки
     - **openlines_connector** — `telegrambot`
     - **openlines_line_id** — идентификатор линии OpenLines (например, `livechat`) 
   - Сохраните канал

### Шаг 4: Настройка Bitrix24 в админке

1. **Настройте Bitrix24 интеграцию:**
   - В админке перейдите на вкладку "Bitrix24"
   - Введите домен портала
   - Введите ID приложения
   - Включите OpenLines и Timeline интеграцию
   - Нажмите "Save Configuration"

### Шаг 5: Тестирование

1. **Запустите тесты интеграции:**
   ```bash
   python scripts/test-integration.py
   ```

2. **Протестируйте общение:**
   - Отправьте сообщение боту в Telegram
   - Проверьте, что сообщение появилось в Bitrix24 OpenLines
   - Ответьте на сообщение в Bitrix24
   - Проверьте, что ответ пришел в Telegram

## 🔧 Конфигурация

### Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# Global system settings (only these go in .env)
DATABASE_URL=postgresql://user:password@localhost:5432/bitrix_messenger
SECRET_KEY=your_global_secret_key
CORS_ORIGINS=*
LOG_LEVEL=INFO

# Webhook URLs (same for all tenants)
WEBHOOK_URL=https://yourdomain.com/api/v1/webhooks

# Tenant-specific settings (configured in admin panel, not .env)
# - Telegram bot tokens (stored in channel.config)
# - Bitrix24 credentials (stored in tenant table)
# - Webhook secrets (stored in tenant.settings)
```

### Настройка OpenLines в Bitrix24

1. **Включите OpenLines:**
   - Перейдите в Bitrix24 → CRM → Открытые линии
   - Создайте новую линию или используйте существующую

2. **Настройте канал Telegram:**
   - В настройках линии добавьте канал Telegram (коннектор `telegrambot`)
   - Укажите тот же токен бота, что и в конфигурации канала
   - Скопируйте идентификатор линии и добавьте его как `openlines_line_id` в конфигурации канала
   - Настройте правила маршрутизации операторов

## 🐛 Устранение неполадок

### Проблемы с Telegram webhook

1. **Проверьте статус webhook:**
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```

2. **Удалите webhook при необходимости:**
   ```bash
   python scripts/setup-telegram-webhook.py delete
   ```

### Проблемы с Bitrix24

1. **Проверьте права приложения:**
   - Убедитесь, что приложение имеет все необходимые права
   - Проверьте, что webhook URL доступен извне

2. **Проверьте логи:**
   ```bash
   tail -f logs/app.log
   ```

### Общие проблемы

1. **Проверьте доступность webhook URL:**
   ```bash
   curl -X POST https://yourdomain.com/api/v1/webhooks/channels/telegram/${TELEGRAM_WEBHOOK_SECRET} \
     -H "Content-Type: application/json" \
     -d '{"test": "message"}'
   ```

2. **Проверьте базу данных:**
   - Убедитесь, что каналы созданы правильно
   - Для стартов чатов из карточек сделок убедитесь, что у контакта уже есть история переписки: при первом сообщении клиента коннектор сохранит `chat_id`, а вебхуки сделок привяжут активные сделки к этому контакту. После этого менеджеры смогут открыть сделку, нажать "Начать чат" и система автоматически подставит нужный Telegram `chat_id`.
   - Проверьте, что токены сохраняются в поле `config`

## 📚 Дополнительные ресурсы

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Bitrix24 REST API](https://dev.1c-bitrix.ru/rest_help/)
- [Bitrix24 OpenLines](https://dev.1c-bitrix.ru/rest_help/imopenlines/index.php)

## 🆘 Поддержка

Если у вас возникли проблемы:

1. Проверьте логи приложения
2. Убедитесь, что все переменные окружения настроены
3. Проверьте доступность webhook URL
4. Убедитесь, что токены и секреты правильные

---

**Готово!** Теперь у вас настроено двустороннее общение между Bitrix24 и Telegram. 🎉
