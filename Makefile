.PHONY: dev format lint typecheck test check build run

dev:
	uv sync --extra dev

format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

test:
	uv run pytest -q

check: lint typecheck test

build:
	uv build

run:
	uv run ai-trading run --reload
