# Railway Example Deployment

Railway is a fast hosted example for the operator runtime. It is not the only supported deployment target.

Railway should host the operator runtime as a stateless FastAPI service backed by Railway Postgres.

## Recommended Production Layout

- `ai-trading-framework` service for the FastAPI runtime
- Railway Postgres for runs, approvals, operator sessions, and broker auth sessions
- Telegram webhook pointed at `https://YOUR-DOMAIN/v1/telegram/webhook/YOUR_SECRET`
- OIDC-enabled operator auth for dashboard and API access

Do not rely on a persistent volume for auth or broker sessions. This framework now stores those records in the database so app instances can be replaced safely during deploys.

## Required Variables

```bash
APP_ENV=prod
PUBLIC_BASE_URL=https://YOUR-DOMAIN
DATABASE_URL=postgresql+psycopg://...
TELEGRAM_WEBHOOK_SECRET=...
OPENAI_API_KEY=...
ZERODHA_API_KEY=...
ZERODHA_API_SECRET=...
```

## Operator Auth Modes

### Password Bootstrap

Use this for an initial admin login or small private deployments.

```bash
AUTH_MODE=PASSWORD
ADMIN_EMAIL=ops@example.com
ADMIN_PASSWORD=replace-me
ADMIN_DISPLAY_NAME=Primary Operator
```

### OIDC

Use this for scalable hosted environments. Railway can be used as an OIDC provider for Railway-user-backed operator access, or you can point the framework at any OIDC-compatible provider.

```bash
AUTH_MODE=OIDC
OIDC_PROVIDER_NAME=railway
OIDC_DISCOVERY_URL=...
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_REDIRECT_URI=https://YOUR-DOMAIN/v1/auth/callback/railway
OIDC_SCOPES=openid profile email
OIDC_ALLOWED_DOMAINS=your-company.com
```

### Hybrid

Use this when you want OIDC as the primary login path and a password fallback for break-glass admin access.

```bash
AUTH_MODE=HYBRID
ADMIN_EMAIL=ops@example.com
ADMIN_PASSWORD=replace-me
OIDC_PROVIDER_NAME=railway
OIDC_DISCOVERY_URL=...
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_REDIRECT_URI=https://YOUR-DOMAIN/v1/auth/callback/railway
```

## Deploy

```bash
railway login
railway link
railway up
```

## Connect Zerodha

1. Sign in to the deployed dashboard or API.
2. Open `/v1/brokers/zerodha/login`.
3. Complete the Kite login flow.
4. Zerodha redirects back to `/v1/brokers/zerodha/callback`.
5. The framework exchanges the `request_token` server-side and stores the broker session in Postgres.

Check the current connection status:

```bash
curl https://YOUR-DOMAIN/v1/brokers/zerodha
```

## Production Smoke Test

```bash
curl https://YOUR-DOMAIN/v1/health
curl -b cookies.txt -c cookies.txt -X POST https://YOUR-DOMAIN/v1/auth/login \
  -H "content-type: application/json" \
  -d '{"email":"ops@example.com","password":"replace-me"}'
curl -b cookies.txt "https://YOUR-DOMAIN/v1/scan/INFY?broker=PAPER"
curl -b cookies.txt https://YOUR-DOMAIN/v1/recommendations
curl -b cookies.txt -X POST https://YOUR-DOMAIN/v1/orders/preview \
  -H "content-type: application/json" \
  -d '{"recommendation_id":"RECOMMENDATION_ID","broker":"PAPER","quantity":1,"order_type":"LIMIT"}'
```

Once Zerodha is connected, the same session can be used for `/v1/orders/submit` against `ZERODHA`.
