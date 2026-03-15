# Zerodha

Set:

- `ZERODHA_API_KEY`
- `ZERODHA_API_SECRET`
- optional `ZERODHA_ACCESS_TOKEN` for manual bootstrap

The framework now supports a first-party Zerodha callback flow:

1. Sign in to the operator console.
2. Open `/v1/brokers/zerodha/login`.
3. Complete the Kite login flow.
4. Zerodha redirects to `/v1/brokers/zerodha/callback`.
5. The framework exchanges the `request_token` and stores the broker session in the database.

Inspect the current connection with:

```bash
GET /v1/brokers/zerodha
```

Disconnect with:

```bash
POST /v1/brokers/zerodha/disconnect
```

The adapter is approval-first by design. Paper mode remains the default runtime.
