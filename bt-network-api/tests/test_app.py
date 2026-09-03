from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import bittensor.core.subtensor as subtensor_module
from bt_network_api.app import create_app


@pytest.fixture()
def client() -> TestClient:
    """A test client backed by a fully mocked SubstrateInterface.

    This mirrors how the Bittensor SDK's own unit tests mock the chain:
    patching ``SubstrateInterface`` means every ``Subtensor``/``SubtensorApi``
    instance talks to a MagicMock instead of a live WebSocket endpoint.
    """
    mock_substrate = MagicMock(autospec=True)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            subtensor_module,
            "SubstrateInterface",
            mock_substrate,
        )
        app = create_app(network="local")
        return TestClient(app)


def test_index(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "bt-network-api"
    assert body["network"] == "local"
    assert "/health" in body["endpoints"]


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_block(client: TestClient) -> None:
    resp = client.get("/block")
    assert resp.status_code == 200
    assert "block" in resp.json()


def test_subnets(client: TestClient) -> None:
    resp = client.get("/subnets")
    assert resp.status_code == 200
    body = resp.json()
    assert "count" in body
    assert "subnets" in body


def test_delegates(client: TestClient) -> None:
    resp = client.get("/delegates")
    assert resp.status_code == 200
    body = resp.json()
    assert "count" in body
    assert "delegates" in body


def test_neurons_not_found(client: TestClient) -> None:
    resp = client.get("/neurons/999999")
    assert resp.status_code == 404


def test_metagraph_not_found(client: TestClient) -> None:
    resp = client.get("/metagraph/999999")
    assert resp.status_code == 404


def test_staking_error(client: TestClient) -> None:
    resp = client.get("/staking/invalid")
    assert resp.status_code == 404