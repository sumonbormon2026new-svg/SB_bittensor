import importlib.metadata
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

import bittensor as bt

from bt_network_api import db
from bt_network_api.settings import get_mock, get_network

try:
    __version__ = importlib.metadata.version("bt-network-api")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    if not db.list_api_keys():
        _, raw = db.make_api_key(name="bootstrap-admin", is_admin=True)
        print(
            f"[bt-network-api] bootstrapped admin API key (shown once): {raw}",
            flush=True,
        )
    yield


def create_app(network: str | None = None, mock: bool | None = None) -> FastAPI:
    """Create the FastAPI application, optionally overriding settings."""
    app = FastAPI(title="bt-network-api", version=__version__, lifespan=lifespan)

    app.state.network = network or get_network()
    app.state.mock = get_mock() if mock is None else mock
    app.state.subtensor = None

    require_auth = os.getenv("BT_API_REQUIRE_AUTH", "0").lower() in ("1", "true", "yes", "on")

    def get_subtensor() -> bt.SubtensorApi:
        if app.state.subtensor is None:
            app.state.subtensor = bt.SubtensorApi(network=app.state.network, mock=app.state.mock)
        return app.state.subtensor

    def _record(
        key_prefix: str | None,
        endpoint: str,
        cache_key: str,
        status: int,
        start: float,
    ) -> None:
        duration_ms = int((time.time() - start) * 1000)
        try:
            db.log_request(key_prefix, endpoint, cache_key, status, duration_ms)
        except Exception:  # noqa: BLE001
            pass

    def _auth(authorization: str | None = Header(default=None)) -> db.ApiKey:
        if not require_auth:
            from datetime import datetime, timezone

            return db.ApiKey(  # type: ignore[abstract]
                id=0,
                key_prefix="anon",
                key_hash="",
                name="anonymous",
                is_active=True,
                is_admin=True,
                query_count=0,
                created_at=datetime.now(timezone.utc),
                last_used_at=None,
            )
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header. Use: Bearer <API_KEY>",
            )
        token = authorization[len("Bearer ") :].strip()
        key = db.verify_api_key(token)
        if key is None:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")
        return key

    def _admin(key: db.ApiKey = Depends(_auth)) -> db.ApiKey:
        if not key.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        return key

    @app.get("/")
    def index(_: db.ApiKey = Depends(_auth)) -> HTMLResponse:
        info = {
            "name": "bt-network-api",
            "version": __version__,
            "network": app.state.network,
            "mock": app.state.mock,
            "auth_required": require_auth,
            "endpoints": [
                "/health",
                "/block",
                "/subnets",
                "/neurons/{netuid}",
                "/metagraph/{netuid}",
                "/delegates",
                "/staking/{address}",
                "/cache/refresh",
                "/cache/history",
                "/me",
                "/admin/keys",
                "/admin/stats",
            ],
        }
        endpoint_rows = "".join(
            f'<tr><td class="endpoint"><code>{ep}</code></td></tr>' for ep in info["endpoints"]
        )
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{info["name"]} v{info["version"]}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 700px; margin: 60px auto; padding: 0 20px; background: #fafafa; color: #222; }}
  h1 {{ font-size: 1.6rem; font-weight: 600; margin-bottom: 4px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 500; margin-bottom: 20px; }}
  .badge-version {{ background: #e8f5e9; color: #2e7d32; }}
  .badge-network {{ background: #e3f2fd; color: #1565c0; }}
  .badge-mock {{ background: {'#fff3e0' if info['mock'] else '#f5f5f5'}; color: {'#e65100' if info['mock'] else '#757575'}; }}
  .badge-auth {{ background: {'#fce4ec' if info['auth_required'] else '#e8f5e9'}; color: {'#c62828' if info['auth_required'] else '#2e7d32'}; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
  th {{ text-align: left; padding: 8px 12px; border-bottom: 2px solid #ddd; font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
  td.endpoint code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9rem; color: #333; }}
  .footer {{ margin-top: 40px; font-size: 0.8rem; color: #999; }}
</style>
</head>
<body>
<h1>{info["name"]}</h1>
<span class="badge badge-version">v{info["version"]}</span>
<span class="badge badge-network">{info["network"]}</span>
<span class="badge badge-mock">mock: {str(info["mock"]).lower()}</span>
<span class="badge badge-auth">auth: {str(info["auth_required"]).lower()}</span>
<table>
  <thead><tr><th>Available Endpoints</th></tr></thead>
  <tbody>{endpoint_rows}</tbody>
</table>
<div class="footer">bt-network-api &mdash; Bittensor network REST API</div>
</body>
</html>"""
        return HTMLResponse(content=html, status_code=200)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/me")
    def me(key: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        return {
            "id": key.id,
            "key_prefix": key.key_prefix,
            "name": key.name,
            "is_admin": key.is_admin,
            "is_active": key.is_active,
            "query_count": key.query_count,
            "created_at": key.created_at.isoformat(),
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        }

    @app.get("/block")
    def block(key: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        start = time.time()
        cache_key = f"block:{app.state.network}"
        cached = db.cache_get("block", cache_key)
        if cached is not None:
            _record(key.key_prefix, "block", cache_key, 200, start)
            return {
                "block": cached["payload"]["block"],
                "cached": True,
                "at": cached["created_at"],
            }
        subtensor = get_subtensor()
        result = subtensor.block
        db.cache_put("block", cache_key, {"block": result})
        _record(key.key_prefix, "block", cache_key, 200, start)
        return {"block": result, "cached": False}

    @app.get("/subnets")
    def subnets(key: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        start = time.time()
        cache_key = f"subnets:{app.state.network}"
        cached = db.cache_get("subnets", cache_key)
        if cached is not None:
            _record(key.key_prefix, "subnets", cache_key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        info = subtensor.subnets.get_all_subnets_info()
        result = {"count": len(info), "subnets": info}
        db.cache_put("subnets", cache_key, result)
        _record(key.key_prefix, "subnets", cache_key, 200, start)
        return result

    @app.get("/neurons/{netuid}")
    def neurons(netuid: int, key: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        start = time.time()
        cache_key = f"neurons:{netuid}:{app.state.network}"
        cached = db.cache_get("neurons", cache_key)
        if cached is not None:
            _record(key.key_prefix, "neurons", cache_key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        try:
            result = subtensor.neurons.neurons_lite(netuid=netuid)
        except Exception as exc:  # noqa: BLE001
            _record(key.key_prefix, "neurons", cache_key, 404, start)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = {"netuid": netuid, "neurons": result}
        db.cache_put("neurons", cache_key, payload)
        _record(key.key_prefix, "neurons", cache_key, 200, start)
        return payload

    @app.get("/metagraph/{netuid}")
    def metagraph(netuid: int, key: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        start = time.time()
        cache_key = f"metagraph:{netuid}:{app.state.network}"
        cached = db.cache_get("metagraph", cache_key)
        if cached is not None:
            _record(key.key_prefix, "metagraph", cache_key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        try:
            result = subtensor.metagraphs.metagraph(netuid=netuid, lite=True)
        except Exception as exc:  # noqa: BLE001
            _record(key.key_prefix, "metagraph", cache_key, 404, start)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = {"netuid": netuid, "metagraph": result}
        db.cache_put("metagraph", cache_key, payload)
        _record(key.key_prefix, "metagraph", cache_key, 200, start)
        return payload

    @app.get("/delegates")
    def delegates(key: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        start = time.time()
        cache_key = f"delegates:{app.state.network}"
        cached = db.cache_get("delegates", cache_key)
        if cached is not None:
            _record(key.key_prefix, "delegates", cache_key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        identities = subtensor.delegates.get_delegate_identities()
        result = {"count": len(identities), "delegates": identities}
        db.cache_put("delegates", cache_key, result)
        _record(key.key_prefix, "delegates", cache_key, 200, start)
        return result

    @app.get("/staking/{address}")
    def staking(address: str, key: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        start = time.time()
        cache_key = f"staking:{address}:{app.state.network}"
        cached = db.cache_get("staking", cache_key)
        if cached is not None:
            _record(key.key_prefix, "staking", cache_key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        try:
            result = subtensor.staking.get_stake_info_for_coldkey(coldkey=address)
        except Exception as exc:  # noqa: BLE001
            _record(key.key_prefix, "staking", cache_key, 404, start)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = {"address": address, "stakes": result}
        db.cache_put("staking", cache_key, payload)
        _record(key.key_prefix, "staking", cache_key, 200, start)
        return payload

    @app.get("/cache/history")
    def cache_history(_: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        records = db.history(limit=20)
        return {"count": len(records), "records": records}

    @app.get("/cache/refresh")
    def cache_refresh(_: db.ApiKey = Depends(_auth)) -> dict[str, Any]:
        return {
            "message": "Cache refresh triggered. All subsequent requests will fetch fresh data from the chain.",
        }

    @app.get("/admin/keys")
    def admin_list_keys(_: db.ApiKey = Depends(_admin)) -> dict[str, Any]:
        keys = db.list_api_keys()
        return {"count": len(keys), "keys": keys}

    @app.post("/admin/keys")
    def admin_create_key(name: str = "default", _: db.ApiKey = Depends(_admin)) -> dict[str, Any]:
        obj, raw = db.make_api_key(name=name, is_admin=False)
        return {
            "id": obj.id,
            "key_prefix": obj.key_prefix,
            "name": obj.name,
            "api_key": raw,
            "warning": "Store this key now. It cannot be retrieved later.",
        }

    @app.post("/admin/keys/{key_id}/revoke")
    def admin_revoke_key(key_id: int, _: db.ApiKey = Depends(_admin)) -> dict[str, Any]:
        ok = db.revoke_api_key(key_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Key not found")
        return {"id": key_id, "revoked": True}

    @app.post("/admin/keys/{key_id}/rotate")
    def admin_rotate_key(key_id: int, _: db.ApiKey = Depends(_admin)) -> dict[str, Any]:
        new_raw = db.reset_api_key(key_id)
        if new_raw is None:
            raise HTTPException(status_code=404, detail="Key not found")
        return {
            "id": key_id,
            "api_key": new_raw,
            "warning": "Store this key now. It cannot be retrieved later.",
        }

    @app.get("/admin/stats")
    def admin_stats(_: db.ApiKey = Depends(_admin)) -> dict[str, Any]:
        return db.global_stats()

    return app
