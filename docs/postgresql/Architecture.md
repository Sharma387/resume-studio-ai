# PostgreSQL Architecture

## Overview

RSAI uses the **Repository Pattern** to abstract storage behind a consistent interface.
This document explains how PostgreSQL fits into the architecture.

## Layer Diagram

```
┌──────────────────────────────────────────┐
│             Routes (API v1)               │
├──────────────────────────────────────────┤
│              Services                     │
├──────────────────────────────────────────┤
│        Repository Interfaces              │
├──────────────────────────────────────────┤
│            Repository Factory            │  ← Feature flag decides
├──────────────────┬───────────────────────┤
│   JSON Repos     │   PostgreSQL Repos    │
│   (current)      │   (Phase 2+)          │
├──────────────────┴───────────────────────┤
│       Storage Service / SQLAlchemy        │
├──────────────────┬───────────────────────┤
│  JSON Files      │  PostgreSQL Database  │
└──────────────────┴───────────────────────┘
```

## Key Design Decisions

### 1. Async SQLAlchemy

- Using `sqlalchemy[asyncio]` with `asyncpg` driver
- Matches FastAPI's async nature
- Engine and session factory are module-level singletons in `app/db/database.py`

### 2. Repository Pattern

- `app/services/repositories/interfaces.py` defines 14 abstract repository classes
- `app/services/repositories/factory.py` returns JSON or PostgreSQL implementation based on `STORAGE_BACKEND` setting
- Services never know which backend is active

### 3. Declarative Base

- `app/db/base.py` defines a single `Base = DeclarativeBase()`
- All future ORM models will inherit from this
- Alembic's `target_metadata` points to `Base.metadata`

### 4. Feature Flag

- Controlled by `STORAGE_BACKEND` in `.env`
- Values: `json` (default) or `postgres`
- Factory checks this on every call

## Database Module (`app/db/`)

| File | Purpose |
|---|---|
| `base.py` | SQLAlchemy `DeclarativeBase` for all ORM models |
| `database.py` | Async engine creation, session factory, lifecycle management |
| `session.py` | FastAPI dependency for getting DB sessions |
| `models/` | SQLAlchemy ORM models (UserModel, RefreshTokenModel, future models) |
