# 🏗️ Мультитенантная архитектура webhook'ов

## 📋 Проблема

В мультитенантной системе нужно было решить, как определить, какой tenant отправил webhook, когда все используют одинаковые URL'ы.

## ✅ Решение: Определение tenant по содержимому webhook'а

### **Webhook URL'ы (одинаковые для всех tenant'ов):**
```
https://yourdomain.com/api/v1/webhooks/channels/telegram/{channel_webhook_secret}
https://yourdomain.com/api/v1/webhooks/bitrix
```

### **Определение tenant'а:**

#### 1. **Telegram webhook'и:**
- Каждый канал получает собственный `webhook_secret`, который входит в URL
- Сервис находит канал по секрету (`channel_webhook_secret`) и типу
- Если секрет не передан, допускается fallback только при наличии одного активного канала
- Дальнейшая проверка подписи и токена бота доступна как дополнительная защита

#### 2. **Bitrix24 webhook'и:**
- **Метод 1**: По секрету webhook'а (из заголовка `X-Bitrix-Signature`)
- **Метод 2**: По домену из payload'а
- **Метод 3**: Fallback на первый активный tenant

## 🔧 Реализованные изменения:

### **WebhookService:**
- `_resolve_channel_from_webhook()` — определение канала и tenant'а по типу и `webhook_secret`
- `_find_tenant_by_bitrix_webhook()` — поиск tenant'а по webhook'у Bitrix24
- `_route_to_bitrix()` — передача сообщений в OpenLines через BitrixOpenLinesService

### **Webhook роуты:**
- Передача секрета webhook'а в сервис
- Автоматическое определение tenant'а

### **Конфигурация:**
- **Глобальные настройки** (в .env): DATABASE_URL, SECRET_KEY, CORS_ORIGINS
- **Настройки tenant'а** (в БД): bitrix_portal, bitrix_app_id, webhook_secret
- **Настройки канала** (в БД): `bot_token`, `webhook_secret`, `openlines_connector`, `openlines_line_id`

## 🎯 Преимущества:

1. **Простота настройки** - один webhook URL для всех
2. **Масштабируемость** - легко добавлять новых tenant'ов
3. **Безопасность** - каждый tenant имеет свои секреты
4. **Гибкость** - можно настроить разные методы определения tenant'а

## 🚀 Использование:

### **Настройка webhook'а Telegram:**
```bash
# Один URL для всех tenant'ов
https://yourdomain.com/api/v1/webhooks/channels/telegram/{channel_webhook_secret}
```

### **Настройка webhook'а Bitrix24:**
```bash
# Один URL для всех tenant'ов
https://yourdomain.com/api/v1/webhooks/bitrix
```

### **Конфигурация в админке:**
1. Добавить канал Telegram с токеном бота
2. Настроить Bitrix24 с доменом и секретом webhook'а
3. Система автоматически определит tenant по содержимому webhook'а

## 🔮 Будущие улучшения:

1. **Проверка подписи Telegram webhook'а** по токену бота
2. **Кэширование** результатов поиска tenant'а
3. **Логирование** процесса определения tenant'а
4. **Метрики** по успешности определения tenant'а

---

**Результат:** Мультитенантная система с автоматическим определением tenant'а по содержимому webhook'а! 🎉
