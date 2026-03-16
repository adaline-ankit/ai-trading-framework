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

## Multi-Asset Coverage

The framework now models Zerodha as a multi-asset broker instead of just a stock broker.

Current broker capability metadata covers:

- equities
- ETFs
- futures
- options
- commodities
- currencies
- mutual fund workflows

Inspect broker capabilities with:

```bash
GET /v1/brokers/ZERODHA/capabilities
```

## Instrument And Holdings Endpoints

Search the tradable instrument master:

```bash
GET /v1/brokers/zerodha/instruments?query=NIFTY
GET /v1/brokers/zerodha/instruments?exchange=NFO&segment=NFO-FUT
```

Search mutual fund instruments:

```bash
GET /v1/brokers/zerodha/mf/instruments?query=index
```

Inspect holdings:

```bash
GET /v1/brokers/zerodha/holdings
GET /v1/brokers/zerodha/mf/holdings
GET /v1/holdings/ZERODHA
```

These endpoints are useful for:

- building multi-asset operator consoles
- discovering futures and options contracts
- reviewing ETF and equity inventory
- reviewing mutual fund inventory in the same framework runtime

Disconnect with:

```bash
POST /v1/brokers/zerodha/disconnect
```

The adapter is approval-first by design. Paper mode remains the default runtime.

Direct mutual fund order submission is not enabled in this runtime. The framework exposes mutual fund discovery and holdings workflows so developers can automate review, approval, and portfolio workflows around Coin-linked assets without pretending that every asset class behaves like a normal equity order.
