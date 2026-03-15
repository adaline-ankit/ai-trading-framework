# Quickstart

```bash
uv sync --extra dev
uv run ai-trading sandbox
uv run ai-trading scan INFY
uv run uvicorn ai_trading_framework.api.app:create_app --factory --reload
```

The default runtime uses demo providers, paper execution, SQLite persistence, and approval-first workflows.
