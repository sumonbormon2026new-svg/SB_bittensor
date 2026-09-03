import importlib.metadata
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException

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
    yield


def create_app(network: str | None = None, mock: bool | None = None) -> FastAPI:
    """Create the FastAPI application, optionally overriding settings.

    Args:
        network: Override the configured Bittensor network.
        mock: Override the configured mock flag.

    Returns:
        A configured FastAPI application.
    """
    app = FastAPI(title="bt-network-api", version=__version__, lifespan=lifespan)

    app.state.network = network or get_network()
    app.state.mock = get_mock() if mock is None else mock
    app.state.subtensor = None

    def get_subtensor() -> bt.SubtensorApi:
        if app.state.subtensor is None:
            app.state.subtensor = bt.SubtensorApi(network=app.state.network, mock=app.state.mock)
        return app.state.subtensor

    def _record(endpoint: str, key: str, status: int, start: float) -> None:
        duration_ms = int((time.time() - start) * 1000)
        try:
            db.log_request(endpoint, key, status, duration_ms)
        except Exception:  # noqa: BLE001
            pass

    @app.get("/")
    def index() -> dict[str, Any]:
        return {
            "name": "bt-network-api",
            "version": __version__,
            "network": app.state.network,
            "mock": app.state.mock,
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
            ],
        }

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/block")
    def block() -> dict[str, Any]:
        start = time.time()
        key = f"block:{app.state.network}"
        cached = db.cache_get("block", key)
        if cached is not None:
            _record("block", key, 200, start)
            return {"block": cached["payload"]["block"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        result = subtensor.block
        db.cache_put("block", key, {"block": result})
        _record("block", key, 200, start)
        return {"block": result, "cached": False}

    @app.get("/subnets")
    def subnets() -> dict[str, Any]:
        start = time.time()
        key = f"subnets:{app.state.network}"
        cached = db.cache_get("subnets", key)
        if cached is not None:
            _record("subnets", key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        info = subtensor.subnets.get_all_subnets_info()
        result = {"count": len(info), "subnets": info}
        db.cache_put("subnets", key, result)
        _record("subnets", key, 200, start)
        return result

    @app.get("/neurons/{netuid}")
    def neurons(netuid: int) -> dict[str, Any]:
        start = time.time()
        key = f"neurons:{netuid}:{app.state.network}"
        cached = db.cache_get("neurons", key)
        if cached is not None:
            _record("neurons", key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        try:
            result = subtensor.neurons.neurons_lite(netuid=netuid)
        except Exception as exc:  # noqa: BLE001
            _record("neurons", key, 404, start)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = {"netuid": netuid, "neurons": result}
        db.cache_put("neurons", key, payload)
        _record("neurons", key, 200, start)
        return payload

    @app.get("/metagraph/{netuid}")
    def metagraph(netuid: int) -> dict[str, Any]:
        start = time.time()
        key = f"metagraph:{netuid}:{app.state.network}"
        cached = db.cache_get("metagraph", key)
        if cached is not None:
            _record("metagraph", key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        try:
            result = subtensor.metagraphs.metagraph(netuid=netuid, lite=True)
        except Exception as exc:  # noqa: BLE001
            _record("metagraph", key, 404, start)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = {"netuid": netuid, "metagraph": result}
        db.cache_put("metagraph", key, payload)
        _record("metagraph", key, 200, start)
        return payload

    @app.get("/delegates")
    def delegates() -> dict[str, Any]:
        start = time.time()
        key = f"delegates:{app.state.network}"
        cached = db.cache_get("delegates", key)
        if cached is not None:
            _record("delegates", key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        identities = subtensor.delegates.get_delegate_identities()
        result = {"count": len(identities), "delegates": identities}
        db.cache_put("delegates", key, result)
        _record("delegates", key, 200, start)
        return result

    @app.get("/staking/{address}")
    def staking(address: str) -> dict[str, Any]:
        start = time.time()
        key = f"staking:{address}:{app.state.network}"
        cached = db.cache_get("staking", key)
        if cached is not None:
            _record("staking", key, 200, start)
            return {**cached["payload"], "cached": True, "at": cached["created_at"]}
        subtensor = get_subtensor()
        try:
            result = subtensor.staking.get_stake_info_for_coldkey(coldkey=address)
        except Exception as exc:  # noqa: BLE001
            _record("staking", key, 404, start)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = {"address": address, "stakes": result}
        db.cache_put("staking", key, payload)
        _record("staking", key, 200, start)
        return payload

    @app.get("/cache/history")
    def cache_history() -> dict[str, Any]:
        records = db.history(limit=20)
        return {"count": len(records), "records": records}

    @app.get("/cache/refresh")
    def cache_refresh() -> dict[str, Any]:
        return {
            "message": "Cache refresh triggered. All subsequent requests will fetch fresh data from the chain.",
        }

    return app
