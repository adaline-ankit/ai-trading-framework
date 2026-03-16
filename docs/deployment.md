# Deployment

`ai-trading-framework` is deployable anywhere you can run:

- Python 3.11+
- a public HTTPS endpoint for the API
- Postgres for production state

Railway is one example. It is not a requirement.

## Production Requirements

The production runtime expects:

- FastAPI application entrypoint
- database-backed runtime state
- public URL for Telegram and broker callbacks
- environment-based configuration

## Required Environment Variables

```bash
APP_ENV=prod
PUBLIC_BASE_URL=https://your-domain.example.com
DATABASE_URL=postgresql+psycopg://...
OPENAI_API_KEY=...
TELEGRAM_WEBHOOK_SECRET=...
```

If you use Telegram:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_DEFAULT_CHAT_ID=...
```

If you use Zerodha:

```bash
ZERODHA_API_KEY=...
ZERODHA_API_SECRET=...
```

## Authentication Modes

### Password Bootstrap

```bash
AUTH_MODE=PASSWORD
ADMIN_EMAIL=ops@example.com
ADMIN_PASSWORD=replace-me
ADMIN_DISPLAY_NAME=Primary Operator
```

### OIDC

```bash
AUTH_MODE=OIDC
OIDC_PROVIDER_NAME=your-idp
OIDC_DISCOVERY_URL=...
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_REDIRECT_URI=https://your-domain.example.com/v1/auth/callback/your-idp
OIDC_ALLOWED_DOMAINS=example.com
```

### Hybrid

```bash
AUTH_MODE=HYBRID
ADMIN_EMAIL=ops@example.com
ADMIN_PASSWORD=replace-me
OIDC_PROVIDER_NAME=your-idp
OIDC_DISCOVERY_URL=...
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_REDIRECT_URI=https://your-domain.example.com/v1/auth/callback/your-idp
```

## Docker

Build:

```bash
docker build -f deploy/docker/Dockerfile -t ai-trading-framework .
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -e APP_ENV=prod \
  -e PUBLIC_BASE_URL=http://127.0.0.1:8000 \
  -e DATABASE_URL=sqlite:///./ai_trading_framework.db \
  ai-trading-framework
```

For a local containerized stack, see [docker-compose.yml](../docker-compose.yml).

## Generic Container Platforms

The runtime works on any platform that can:

- run a Docker image
- expose port `8000`
- set environment variables
- attach Postgres

Examples:

- Railway
- Render
- Fly.io
- ECS / Fargate
- Kubernetes
- self-hosted VM

## Healthcheck

Use:

```text
GET /v1/health
```

## Post-Deploy Checklist

1. Sign in to the dashboard.
2. Run a paper scan.
3. Configure Telegram with `POST /v1/telegram/setup`.
4. Verify Telegram webhook status.
5. If using Zerodha, complete the callback flow.
6. Run the paper execution path end to end.
