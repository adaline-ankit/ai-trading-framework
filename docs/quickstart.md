# Quickstart

```bash
uv sync --extra dev
uv run ai-trading init my-bot --template paper-sandbox
cd my-bot
cp .env.example .env
uv run ai-trading doctor
uv run ai-trading sandbox
uv run ai-trading scan INFY
uv run ai-trading recommend
uv run ai-trading watchlist add SBIN
uv run ai-trading run --reload
```

The default runtime uses demo providers, paper execution, SQLite persistence, and approval-first workflows.

## Product-Style Local Bot Setup

The fastest way to use the framework as a user-facing product is to scaffold a bot project first:

```bash
uv run ai-trading init my-bot --template investor-copilot
cd my-bot
cp .env.example .env
uv run ai-trading doctor
uv run ai-trading status
```

The generated project includes:

- `bot.yaml` for bot capabilities and defaults
- `.env.example` for runtime secrets
- `strategies/` for custom strategy files
- `prompts/` for future AI prompt overrides
- `state/` for local state artifacts

## Local Hosted Stack

Start Postgres plus the app with Docker Compose:

```bash
docker compose up --build
```

Then open `http://127.0.0.1:8000`.

## Paper Trading End-To-End

1. Start the API:

```bash
uv run ai-trading run --reload
```

2. Generate a recommendation:

```bash
curl http://127.0.0.1:8000/v1/scan/INFY?broker=PAPER
```

3. List recommendations and capture the `recommendation_id`:

```bash
curl http://127.0.0.1:8000/v1/recommendations
```

4. Preview the paper order:

```bash
curl -X POST http://127.0.0.1:8000/v1/orders/preview \
  -H "content-type: application/json" \
  -d '{"recommendation_id":"RECOMMENDATION_ID","broker":"PAPER","quantity":2,"order_type":"LIMIT"}'
```

5. Submit the paper order:

```bash
curl -X POST http://127.0.0.1:8000/v1/orders/submit \
  -H "content-type: application/json" \
  -d '{"recommendation_id":"RECOMMENDATION_ID","broker":"PAPER","quantity":2,"order_type":"LIMIT"}'
```

6. Verify positions and replay:

```bash
curl http://127.0.0.1:8000/v1/positions/PAPER
curl http://127.0.0.1:8000/v1/replay/RUN_ID
```
