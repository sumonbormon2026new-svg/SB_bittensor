# bt-network-api

A FastAPI REST service exposing Bittensor network data through the
[Bittensor SDK](https://pypi.org/project/bittensor/).

## Features

- Chain status and network data over HTTP
- Mock mode for offline development and testing
- Configurable network, host, and port
- **SQLAlchemy-powered persistent cache** (SQLite by default) for query results
- **Request audit log** of every API call

## Endpoints

| Route | Description |
| --- | --- |
| `GET /` | Service index |
| `GET /health` | Liveness check |
| `GET /block` | Current chain block number (cached) |
| `GET /subnets` | All subnet info (cached) |
| `GET /neurons/{netuid}` | Neurons on a subnet (cached) |
| `GET /metagraph/{netuid}` | Metagraph of a subnet (cached) |
| `GET /delegates` | Delegate identities (cached) |
| `GET /staking/{address}` | Stake info for a coldkey address (cached) |
| `GET /cache/history` | Last 20 served requests (audit log) |
| `GET /cache/refresh` | Bypass notice (cache invalidation hook) |

## Install

```bash
pip install bt-network-api
```

## Usage

```bash
# Install from source
uv sync --extra dev

# Run the server (defaults to 0.0.0.0:8091)
uv run bt-network-api --host 0.0.0.0 --port 8091

# Or via uvicorn (factory mode — app is created per worker)
uv run uvicorn --factory --app-dir . bt_network_api.app:create_app --host 0.0.0.0 --port 8091
```

Verify it is running:

```bash
curl -s http://localhost:8091/health
```

## Configuration

Environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `BT_API_NETWORK` | `finney` | Bittensor network name |
| `BT_API_MOCK` | `0` | Use mock data (`1`) instead of the live chain |
| `BT_API_DATABASE_URL` | `sqlite:///./bt_network_api.db` | SQLAlchemy database URL (any DB supported) |

## Development

```bash
uv run ruff format --check src tests
uv run ruff check src
uv run mypy src/
uv run pytest
uv build
```