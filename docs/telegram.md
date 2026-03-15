# Telegram

Set:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_DEFAULT_CHAT_ID`
- `TELEGRAM_WEBHOOK_SECRET`

The notifier ships with recommendation formatting and `/why`-style explanation support.

## Supported Commands

- `/scan SYMBOL`
- `/analyze SYMBOL`
- `/approve RECOMMENDATION_ID TOKEN`
- `/reject RECOMMENDATION_ID TOKEN`
- `/why SYMBOL_OR_RECOMMENDATION_ID`
- `/risk SYMBOL_OR_RECOMMENDATION_ID`
- `/positions`
- `/portfolio`

## Webhook

Expose:

```text
POST /v1/telegram/webhook/{TELEGRAM_WEBHOOK_SECRET}
```

Example local test:

```bash
curl -X POST http://127.0.0.1:8000/v1/telegram/webhook/change-me \
  -H "content-type: application/json" \
  -d '{"message":{"text":"/scan INFY","chat":{"id":123}}}'
```
