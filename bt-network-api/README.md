# bt-network-api

A FastAPI REST service exposing Bittensor network data through the
[Bittensor SDK](https://pypi.org/project/bittensor/).

## Features

- Chain status and network data over HTTP
- Mock mode for offline development and testing
- Configurable network, host, and port

## Endpoints

| Route | Description |
| --- | --- |
| `GET /` | Service index |
| `GET /health` | Liveness check |
| `GET /block` | Current chain block number |
| `GET /subnets` | All subnet info |
| `GET /neurons/{netuid}` | Neurons on a subnet |
| `GET /metagraph/{netuid}` | Metagraph of a subnet |
| `GET /delegates` | Delegate identities |
| `GET /staking/{address}` | Stake info for a coldkey address |

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

# Or via uvicorn
uv run uvicorn bt_network_api.app:app --host 0.0.0.0 --port 8091
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

## Development

```bash
uv run ruff format --check src tests
uv run ruff check src
uv run mypy src/
uv run pytest
uv build
```