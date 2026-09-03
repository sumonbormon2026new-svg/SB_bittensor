"""Database layer for bt-network-api.

Uses SQLAlchemy 2.x with SQLite by default; supports any SQLAlchemy-compatible
database via the ``BT_API_DATABASE_URL`` environment variable.

Tables are auto-created on application startup via the lifespan context manager
in ``app.py``.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def get_database_url() -> str:
    return os.getenv("BT_API_DATABASE_URL", "sqlite:///./bt_network_api.db")


class Base(DeclarativeBase):
    pass


class ApiKey(Base):
    """An API key for authenticating requests to the service."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_prefix: Mapped[str] = mapped_column(String(16), index=True, unique=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CachedQuery(Base):
    """A cached response for a single API query."""

    __tablename__ = "cached_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class RequestLog(Base):
    """An audit log of API requests served."""

    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=True)
    endpoint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _is_sqlite() -> bool:
    return get_database_url().startswith("sqlite")


def get_engine() -> "Any":
    global _engine
    if _engine is None:
        url = get_database_url()
        connect_args: dict[str, Any] = {"check_same_thread": False} if _is_sqlite() else {}
        pool_settings: dict[str, Any] = {}
        if not _is_sqlite():
            pool_settings = {
                "pool_pre_ping": True,
                "pool_size": 5,
                "max_overflow": 10,
            }
        _engine = create_engine(
            url,
            future=True,
            connect_args=connect_args,
            **pool_settings,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _SessionLocal


def init_db() -> None:
    Base.metadata.create_all(get_engine())


# ---------------------------------------------------------------------------
# API key helpers
# ---------------------------------------------------------------------------

_SECRET_LEN = 32


def _make_key() -> tuple[str, str]:
    raw = secrets.token_urlsafe(_SECRET_LEN)
    return raw, raw[:8]


def make_api_key(name: str = "default", is_admin: bool = False) -> tuple[ApiKey, str]:
    """Create a new API key.

    Returns the ORM object and the raw (unhashed) key — show this once to the user.
    """
    raw_key, prefix = _make_key()
    factory = get_session_factory()
    with factory() as session:
        key = ApiKey(
            key_prefix=prefix,
            key_hash=raw_key,
            name=name,
            is_admin=is_admin,
            is_active=True,
        )
        session.add(key)
        session.commit()
        session.refresh(key)
        obj = ApiKey(
            id=key.id,
            key_prefix=key.key_prefix,
            key_hash=key.key_hash,
            name=key.name,
            is_admin=key.is_admin,
            is_active=key.is_active,
            query_count=key.query_count,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
        )
    return obj, raw_key


def verify_api_key(raw_key: str) -> ApiKey | None:
    """Look up an API key by raw value. Returns None if missing or inactive."""
    prefix = raw_key[:8]
    factory = get_session_factory()
    with factory() as session:
        row = session.query(ApiKey).filter_by(key_prefix=prefix).first()
        if row is None or not row.is_active:
            return None
        if row.key_hash != raw_key:
            return None
        row.last_used_at = datetime.now(timezone.utc)
        row.query_count += 1
        session.commit()
        return ApiKey(
            id=row.id,
            key_prefix=row.key_prefix,
            key_hash=row.key_hash,
            name=row.name,
            is_admin=row.is_admin,
            is_active=row.is_active,
            query_count=row.query_count,
            created_at=row.created_at,
            last_used_at=row.last_used_at,
        )


def list_api_keys() -> list[dict[str, Any]]:
    """Return all API keys (sensitive fields redacted)."""
    factory = get_session_factory()
    with factory() as session:
        rows = session.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
        return [
            {
                "id": r.id,
                "key_prefix": r.key_prefix,
                "name": r.name,
                "is_admin": r.is_admin,
                "is_active": r.is_active,
                "query_count": r.query_count,
                "created_at": r.created_at.isoformat(),
                "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
            }
            for r in rows
        ]


def revoke_api_key(key_id: int) -> bool:
    """Soft-revoke an API key by setting is_active=False."""
    factory = get_session_factory()
    with factory() as session:
        row = session.query(ApiKey).filter_by(id=key_id).first()
        if row is None:
            return False
        row.is_active = False
        session.commit()
        return True


def reset_api_key(key_id: int) -> str | None:
    """Rotate an API key. Returns the new raw key, or None if not found."""
    factory = get_session_factory()
    with factory() as session:
        row = session.query(ApiKey).filter_by(id=key_id).first()
        if row is None:
            return None
        new_raw, new_prefix = _make_key()
        row.key_prefix = new_prefix
        row.key_hash = new_raw
        row.last_used_at = None
        row.query_count = 0
        session.commit()
        return new_raw


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def cache_get(endpoint: str, cache_key: str) -> dict[str, Any] | None:
    factory = get_session_factory()
    with factory() as session:
        row = (
            session.query(CachedQuery)
            .filter(CachedQuery.endpoint == endpoint, CachedQuery.key == cache_key)
            .order_by(CachedQuery.id.desc())
            .first()
        )
        if row is None:
            return None
        return {"payload": row.payload, "created_at": row.created_at.isoformat()}


def cache_put(endpoint: str, cache_key: str, payload: Any) -> None:
    factory = get_session_factory()
    with factory() as session:
        session.add(
            CachedQuery(
                endpoint=endpoint,
                key=cache_key,
                payload=json.loads(json.dumps(payload, default=str)),
            )
        )
        session.commit()


# ---------------------------------------------------------------------------
# Request log helpers
# ---------------------------------------------------------------------------


def log_request(
    key_prefix: str | None,
    endpoint: str,
    cache_key: str,
    status_code: int,
    duration_ms: int,
) -> None:
    factory = get_session_factory()
    with factory() as session:
        session.add(
            RequestLog(
                key_prefix=key_prefix,
                endpoint=endpoint,
                key=cache_key,
                status_code=status_code,
                duration_ms=duration_ms,
            )
        )
        session.commit()


def history(limit: int = 20) -> list[dict[str, Any]]:
    factory = get_session_factory()
    with factory() as session:
        rows = session.query(RequestLog).order_by(RequestLog.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "key_prefix": r.key_prefix,
                "endpoint": r.endpoint,
                "key": r.key,
                "status_code": r.status_code,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


def global_stats() -> dict[str, Any]:
    factory = get_session_factory()
    with factory() as session:
        total_requests = session.query(func.count(RequestLog.id)).scalar() or 0
        total_keys = session.query(func.count(ApiKey.id)).scalar() or 0
        active_keys = (
            session.query(func.count(ApiKey.id)).filter(ApiKey.is_active == True).scalar() or 0
        )
        avg_duration = session.query(func.avg(RequestLog.duration_ms)).scalar() or 0
        return {
            "total_requests": total_requests,
            "total_api_keys": total_keys,
            "active_api_keys": active_keys,
            "avg_response_ms": round(float(avg_duration), 2),
        }
