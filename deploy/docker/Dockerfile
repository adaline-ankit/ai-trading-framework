FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir uv \
    && uv pip install --system .[dev]

CMD ["sh", "-c", "uvicorn ai_trading_framework.api.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
