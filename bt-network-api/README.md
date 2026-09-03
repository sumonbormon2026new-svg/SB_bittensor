# bt-network-api

A FastAPI REST service exposing Bittensor network data through the
[Bittensor SDK](https://pypi.org/project/bittensor/).

## Features

- Chain status and network data over HTTP
- Mock mode for offline development and testing
- Configurable network, host, and port
- **SQLAlchemy-powered persistent cache** (SQLite by default; PostgreSQL/any DB supported)
- **Request audit log** of every API call
- **API-key authentication** (Bearer token) with per-key query tracking
- **Admin role** to issue / revoke / rotate keys
- Auto-bootstraps a single admin API key on first start (printed once in stdout)

## Endpoints

| Route | Auth | Description |
| --- | --- | --- |
| `GET /` | optional | Service index |
| `GET /health` | none | Liveness check |
| `GET /me` | bearer | Information about the calling API key |
| `GET /block` | bearer | Current chain block number (cached) |
| `GET /subnets` | bearer | All subnet info (cached) |
| `GET /neurons/{netuid}` | bearer | Neurons on a subnet (cached) |
| `GET /metagraph/{netuid}` | bearer | Metagraph of a subnet (cached) |
| `GET /delegates` | bearer | Delegate identities (cached) |
| `GET /staking/{address}` | bearer | Stake info for a coldkey address (cached) |
| `GET /cache/history` | bearer | Last 20 served requests (audit log) |
| `GET /cache/refresh` | bearer | Bypass notice (cache invalidation hook) |
| `GET /admin/keys` | admin | List all API keys (redacted) |
| `POST /admin/keys?name=X` | admin | Issue a new API key (returns raw key once) |
| `POST /admin/keys/{id}/revoke` | admin | Revoke a key |
| `POST /admin/keys/{id}/rotate` | admin | Rotate a key (returns new raw key) |
| `GET /admin/stats` | admin | Aggregate service statistics |

## Install

```bash
pip install bt-network-api
```

## Usage

```bash
# Run the server (defaults to 0.0.0.0:8091)
bt-network-api --host 0.0.0.0 --port 8091

# Or via uvicorn (factory mode — app is created per worker)
uv run uvicorn --factory --app-dir . bt_network_api.app:create_app --host 0.0.0.0 --port 8091
```

On first start, a single admin API key is created and **printed once** to stdout — capture it for use with the admin endpoints.

Verify it is running:

```bash
curl -s http://localhost:8091/health
```

Use an API key:

```bash
curl -H "Authorization: Bearer <API_KEY>" http://localhost:8091/me
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BT_API_NETWORK` | `finney` | Bittensor network name |
| `BT_API_MOCK` | `0` | Use mock data (`1`) instead of the live chain |
| `BT_API_DATABASE_URL` | `sqlite:///./bt_network_api.db` | SQLAlchemy database URL (any DB supported) |
| `BT_API_REQUIRE_AUTH` | `0` | When `1`, all `/` non-`/health` routes require `Authorization: Bearer <key>` |
| `PORT` / `BT_API_PORT` | `8091` | Bind port (Railway sets `PORT` automatically) |

## Database

Uses SQLAlchemy 2.x. Three tables are created on first start:

- `api_keys` — API key registry (prefix, hashed value, name, role, query count, timestamps)
- `cached_queries` — Latest cached response per `(endpoint, key)` pair
- `request_logs` — Audit log of every served request (per-key attribution)

Any SQLAlchemy-compatible database works:

```bash
# PostgreSQL
export BT_API_DATABASE_URL=postgresql://user:pass@host:5432/db
# MySQL
export BT_API_DATABASE_URL=mysql+pymysql://user:pass@host/db
# SQLite (default)
export BT_API_DATABASE_URL=sqlite:////data/bt_network_api.db
```

## Development

```bash
uv run ruff format --check src tests
uv run ruff check src
uv run mypy src/
uv run pytest
uv build
```
