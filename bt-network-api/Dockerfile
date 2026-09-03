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

RUN uv sync

ENV BT_API_NETWORK=finney \
    BT_API_MOCK=0 \
    BT_API_DATABASE_URL=sqlite:////data/bt_network_api.db

EXPOSE 8091

VOLUME ["/data"]

CMD ["uv", "run", "uvicorn", "--factory", "--app-dir", ".", "bt_network_api.app:create_app", "--host", "0.0.0.0", "--port", "8091"]
