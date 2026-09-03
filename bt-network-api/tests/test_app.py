from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import async_substrate_interface.sync_substrate as substrate_sync_module
from bt_network_api.app import create_app
from bt_network_api import db as db_mod


@pytest.fixture()
def fresh_db(monkeypatch, tmp_path):
    """Reset SQLAlchemy engine and point at a tmp SQLite DB."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("BT_API_DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("BT_API_REQUIRE_AUTH", "1")
    db_mod._engine = None
    db_mod._SessionLocal = None
    return db_file


@pytest.fixture()
def client(fresh_db):
    mock_substrate = MagicMock(autospec=True)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            substrate_sync_module,
            "SubstrateInterface",
            mock_substrate,
        )
        app = create_app(network="local")
        with TestClient(app) as c:
            yield c


@pytest.fixture()
def admin_key(client: TestClient) -> str:
    """Bootstrap admin key is logged to stdout on lifespan startup.

    Extract it from the log capture or read it directly from the DB.
    """
    keys = db_mod.list_api_keys()
    assert keys, "Expected a bootstrapped admin key"
    raw = db_mod._session_factory_for_test()  # type: ignore[attr-defined]
    return _latest_key_raw()


def _latest_key_raw() -> str:
    factory = db_mod.get_session_factory()
    with factory() as session:
        row = session.query(db_mod.ApiKey).order_by(db_mod.ApiKey.id.desc()).first()
        assert row is not None
        return row.key_hash


@pytest.fixture()
def admin_token(fresh_db) -> str:
    """Pre-create an admin key before the app starts so the bootstrap key isn't used."""
    db_mod.init_db()
    _, raw = db_mod.make_api_key(name="test-admin", is_admin=True)
    return raw


@pytest.fixture()
def authed_client(fresh_db, admin_token):
    mock_substrate = MagicMock(autospec=True)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            substrate_sync_module,
            "SubstrateInterface",
            mock_substrate,
        )
        app = create_app(network="local")
        with TestClient(app) as c:
            c.headers["Authorization"] = f"Bearer {admin_token}"
            yield c, admin_token


# ---------------------------------------------------------------------------
# Public (no-auth) tests
# ---------------------------------------------------------------------------


def test_health_no_auth(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_block_no_auth_required_when_disabled(monkeypatch, tmp_path) -> None:
    """When BT_API_REQUIRE_AUTH=0 (default), the bootstrap admin is still
    returned by _auth, so the index returns 200 without a Bearer token."""
    db_file = tmp_path / "noauth.db"
    monkeypatch.setenv("BT_API_DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("BT_API_REQUIRE_AUTH", "0")
    db_mod._engine = None
    db_mod._SessionLocal = None
    mock_substrate = MagicMock(autospec=True)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(substrate_sync_module, "SubstrateInterface", mock_substrate)
        app = create_app(network="local")
        with TestClient(app) as c:
            r = c.get("/")
            assert r.status_code == 200
            assert "bt-network-api" in r.text


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


def test_index_requires_auth(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 401


def test_index_with_admin_token(authed_client) -> None:
    c, _ = authed_client
    r = c.get("/")
    assert r.status_code == 200
    assert "bt-network-api" in r.text
    assert "Available Endpoints" in r.text


def test_dashboard_with_admin_token(authed_client) -> None:
    c, _ = authed_client
    r = c.get("/dashboard")
    assert r.status_code == 200
    assert "Stake Dashboard" in r.text
    assert "Network Overview" in r.text


def test_me(authed_client) -> None:
    c, _ = authed_client
    r = c.get("/me")
    assert r.status_code == 200
    body = r.json()
    assert body["is_admin"] is True
    assert body["name"] == "test-admin"
    assert body["query_count"] == 1


def test_invalid_token_rejected(authed_client) -> None:
    c, _ = authed_client
    c.headers["Authorization"] = "Bearer wrong-key-here-aaaaaaaaaaaaaaaa"
    r = c.get("/me")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Admin endpoint tests
# ---------------------------------------------------------------------------


def test_admin_list_keys(authed_client) -> None:
    c, _ = authed_client
    r = c.get("/admin/keys")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert any(k["name"] == "test-admin" for k in body["keys"])


def test_admin_create_and_revoke_key(authed_client) -> None:
    c, _ = authed_client
    r = c.post("/admin/keys?name=demo")
    assert r.status_code == 200
    body = r.json()
    new_id = body["id"]
    assert body["name"] == "demo"
    assert "api_key" in body

    revoke = c.post(f"/admin/keys/{new_id}/revoke")
    assert revoke.status_code == 200
    assert revoke.json()["revoked"] is True

    headers = {"Authorization": f"Bearer {body['api_key']}"}
    authed = c.get("/me", headers=headers)
    assert authed.status_code == 401


def test_admin_stats(authed_client) -> None:
    c, _ = authed_client
    r = c.get("/admin/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_api_keys" in body
    assert "active_api_keys" in body
    assert body["total_api_keys"] >= 1
    assert body["active_api_keys"] >= 1


def test_non_admin_cannot_list_keys(monkeypatch, tmp_path) -> None:
    db_file = tmp_path / "nonadmin.db"
    monkeypatch.setenv("BT_API_DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("BT_API_REQUIRE_AUTH", "1")
    db_mod._engine = None
    db_mod._SessionLocal = None
    db_mod.init_db()
    _, admin_raw = db_mod.make_api_key(name="admin", is_admin=True)
    _, user_raw = db_mod.make_api_key(name="user", is_admin=False)
    mock_substrate = MagicMock(autospec=True)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(substrate_sync_module, "SubstrateInterface", mock_substrate)
        app = create_app(network="local")
        with TestClient(app) as c:
            r = c.get(
                "/admin/keys",
                headers={"Authorization": f"Bearer {user_raw}"},
            )
            assert r.status_code == 403


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------


def test_cache_history_empty(authed_client) -> None:
    c, _ = authed_client
    r = c.get("/cache/history")
    assert r.status_code == 200
    body = r.json()
    assert "records" in body


def test_cache_refresh(authed_client) -> None:
    c, _ = authed_client
    r = c.get("/cache/refresh")
    assert r.status_code == 200
    assert "message" in r.json()
