# Contributing

- Use `uv sync --extra dev` to install tooling.
- Run `uv run ruff check .`, `uv run mypy src`, and `uv run pytest` before opening a PR.
- Keep execution approval-first and replay-safe when extending the framework.
- New plugins should register via code or the `ai_trading_framework.plugins` entry-point group.
