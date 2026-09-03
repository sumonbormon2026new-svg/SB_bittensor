"""Database layer for bt-network-api.

Uses SQLAlchemy 2.x with SQLite by default. Tables are auto-created on
application startup via the lifespan context manager in ``app.py``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def get_database_url() -> str:
    return os.getenv("BT_API_DATABASE_URL", "sqlite:///./bt_network_api.db")


class Base(DeclarativeBase):
    pass


class CachedQuery(Base):
    """A cached response for a single API query."""

    __tablename__ = "cached_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class RequestLog(Base):
    """An audit log of API requests served."""

    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_database_url()
        connect_args: dict[str, Any] = (
            {"check_same_thread": False} if url.startswith("sqlite") else {}
        )
        _engine = create_engine(url, future=True, connect_args=connect_args)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _SessionLocal


def init_db() -> None:
    Base.metadata.create_all(get_engine())


def serialize_for_json(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, list):
        return [serialize_for_json(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize_for_json(v) for k, v in value.items()}
    return value


def cache_get(endpoint: str, key: str) -> dict[str, Any] | None:
    factory = get_session_factory()
    with factory() as session:
        row = (
            session.query(CachedQuery)
            .filter(CachedQuery.endpoint == endpoint, CachedQuery.key == key)
            .order_by(CachedQuery.id.desc())
            .first()
        )
        if row is None:
            return None
        return {"payload": row.payload, "created_at": row.created_at.isoformat()}


def cache_put(endpoint: str, key: str, payload: Any) -> None:
    factory = get_session_factory()
    with factory() as session:
        session.add(
            CachedQuery(
                endpoint=endpoint, key=key, payload=json.loads(json.dumps(payload, default=str))
            )
        )
        session.commit()


def log_request(endpoint: str, key: str, status_code: int, duration_ms: int) -> None:
    factory = get_session_factory()
    with factory() as session:
        session.add(
            RequestLog(endpoint=endpoint, key=key, status_code=status_code, duration_ms=duration_ms)
        )
        session.commit()


def history(limit: int = 20) -> list[dict[str, Any]]:
    factory = get_session_factory()
    with factory() as session:
        rows = session.query(RequestLog).order_by(RequestLog.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "endpoint": r.endpoint,
                "key": r.key,
                "status_code": r.status_code,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
