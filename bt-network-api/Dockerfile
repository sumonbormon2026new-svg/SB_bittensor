FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src

RUN uv sync --frozen

ENV BT_API_NETWORK=finney \
    BT_API_MOCK=0 \
    BT_API_DATABASE_URL=sqlite:////data/bt_network_api.db

EXPOSE 8091

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8091}/health || exit 1

CMD ["sh", "-c", "uv run uvicorn --factory --app-dir . bt_network_api.app:create_app --host 0.0.0.0 --port ${PORT:-8091}"]
