import importlib.metadata
from typing import Any

from fastapi import FastAPI, HTTPException

import bittensor as bt

from bt_network_api.settings import get_mock, get_network

try:
    __version__ = importlib.metadata.version("bt-network-api")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"


def create_app(network: str | None = None, mock: bool | None = None) -> FastAPI:
    """Create the FastAPI application, optionally overriding settings.

    Args:
        network: Override the configured Bittensor network.
        mock: Override the configured mock flag.

    Returns:
        A configured FastAPI application.
    """
    app = FastAPI(title="bt-network-api", version=__version__)

    app.state.network = network or get_network()
    app.state.mock = get_mock() if mock is None else mock
    app.state.subtensor = None

    def get_subtensor() -> bt.SubtensorApi:
        """Lazy-initialize the shared SubtensorApi instance."""
        if app.state.subtensor is None:
            app.state.subtensor = bt.SubtensorApi(network=app.state.network, mock=app.state.mock)
        return app.state.subtensor

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
            ],
        }

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/block")
    def block() -> dict[str, Any]:
        subtensor = get_subtensor()
        return {"block": subtensor.block}

    @app.get("/subnets")
    def subnets() -> dict[str, Any]:
        subtensor = get_subtensor()
        info = subtensor.subnets.get_all_subnets_info()
        return {"count": len(info), "subnets": info}

    @app.get("/neurons/{netuid}")
    def neurons(netuid: int) -> dict[str, Any]:
        subtensor = get_subtensor()
        try:
            result = subtensor.neurons.neurons_lite(netuid=netuid)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"netuid": netuid, "neurons": result}

    @app.get("/metagraph/{netuid}")
    def metagraph(netuid: int) -> dict[str, Any]:
        subtensor = get_subtensor()
        try:
            result = subtensor.metagraphs.metagraph(netuid=netuid, lite=True)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"netuid": netuid, "metagraph": result}

    @app.get("/delegates")
    def delegates() -> dict[str, Any]:
        subtensor = get_subtensor()
        identities = subtensor.delegates.get_delegate_identities()
        return {"count": len(identities), "delegates": identities}

    @app.get("/staking/{address}")
    def staking(address: str) -> dict[str, Any]:
        subtensor = get_subtensor()
        try:
            result = subtensor.staking.get_stake_info_for_coldkey(coldkey=address)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"address": address, "stakes": result}


app = create_app()
