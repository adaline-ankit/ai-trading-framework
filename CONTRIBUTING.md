# Contributing

Thanks for contributing to `ai-trading-framework`.

## Development Setup

```bash
uv sync --extra dev
```

Or use the repository shortcut:

```bash
make dev
```

Run the local runtime:

```bash
uv run ai-trading run --reload
```

## Validation

Before opening a pull request, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Or run the combined shortcut:

```bash
make check
```

## Contribution Guidelines

- keep non-paper execution approval-first
- do not bypass replay or audit paths when adding execution logic
- preserve plugin boundaries when adding new providers, brokers, or strategies
- document new user-facing features in `README.md` and `docs/`
- add or update tests for behavior changes

## Plugin Contributions

New plugins should integrate through the framework interfaces and, when appropriate, the `ai_trading_framework.plugins` entry-point group.

## Pull Requests

Good pull requests include:

- a clear summary
- user-facing impact
- validation steps
- deployment notes for behavior changes

See the repository PR template for the expected structure.
