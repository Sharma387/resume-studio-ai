# RSAI Production Deployment — PostgreSQL Cutover

## Overview

This document describes the production deployment procedure for switching RSAI from JSON file storage to PostgreSQL.

**Status:** Prepared  
**Default backend:** JSON (unchanged)  
**Target backend:** PostgreSQL (explicit switch required)

---

## Prerequisites

- PostgreSQL 16+ running and accessible
- `DATABASE_URL` configured in `.env`
- Python 3.12+ virtual environment activated
- All dependencies installed: `pip install -r requirements.txt`

---

## Deployment Procedure

### Step 1: Backup

```bash
./scripts/deployment/backup.sh
```

Verify backup output shows both JSON storage and PostgreSQL dump.

### Step 2: Database Migration

```bash
alembic upgrade head
```

Verify: `alembic current` shows `34f537ca05d8` (or later).

### Step 3: Data Migration

```bash
python -m scripts.migrate_data --all
```

### Step 4: Validate Migration

```bash
python -m scripts.migrate_data --validate
```

All tables must show `[OK]`. Expected skipped records:
- `refresh_tokens`: test artifacts referencing deleted users
- `timeline_events`: test artifacts referencing deleted applications

### Step 5: Run Smoke Tests

```bash
STORAGE_BACKEND=postgres DATABASE_URL=... python -m scripts.deployment.smoke_test
```

All 19 smoke tests must pass with `0 failed`.

### Step 6: Switch Feature Flag

Edit `.env`:

```env
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql://rsai:rsai@localhost:5432/rsai
```

### Step 7: Restart Application

```bash
systemctl restart rsai   # or equivalent
```

### Step 8: Verify Health Endpoint

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{"status":"healthy","version":"1.0.0","storage_backend":"postgres","database_connected":true}
```

---

## Rollback Procedure

### Quick Rollback (Minutes)

1. Run: `./scripts/deployment/rollback.sh`
2. This reverts `STORAGE_BACKEND=json` in `.env`
3. Restart the application
4. Verify health endpoint returns `"storage_backend":"json"`

### Full Rollback (Includes Data)

1. Stop the application
2. Restore JSON data: `cp -r backups/*/storage/* storage/`
3. Revert `.env`: `STORAGE_BACKEND=json`
4. Restart application
5. Run: `python -m pytest tests/` — must pass

### Database Rollback

```bash
alembic downgrade -1   # revert last migration
# or
alembic downgrade base  # revert all migrations (destructive)
```

---

## Smoke Tests

Run against PostgreSQL:
```bash
STORAGE_BACKEND=postgres DATABASE_URL=... python -m scripts.deployment.smoke_test
```

Run against JSON:
```bash
python -m scripts.deployment.smoke_test
```

---

## Monitoring

### Health Endpoint

`GET /api/v1/health` returns:
- `status`: always `"healthy"`
- `version`: app version
- `storage_backend`: `"json"` or `"postgres"`
- `database_connected`: `true`/`false` (only when `postgres`)

### Logs

Key log events to monitor:
- `Storage backend selected` — logged on startup
- `Creating async database engine` — engine initialization
- `Database engine initialized for PostgreSQL backend` — successful startup
- `Current migration revision` — current Alembic version
- `Repository selected` — per-repository selection (debug level)

### Prometheus/Grafana (Optional)

Recommended metrics to track:
- `rsai_db_connections` — active connections
- `rsai_migration_version` — current Alembic revision
- `rsai_storage_backend` — active backend (1 for postgres, 0 for json)

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `Database not configured` | `DATABASE_URL` empty or invalid | Check `.env` and environment |
| `column X does not exist` | Alembic migration not applied | Run `alembic upgrade head` |
| `relation Y does not exist` | Alembic migration not applied | Run `alembic upgrade head` |
| `FK violation on insert` | Orphaned data | Skip or create referenced parent |
| `HttpUrl not JSON serializable` | Test data with invalid URLs | Skip corrupt JSON file |
| Engine creation fails | PostgreSQL unreachable | Check `pg_isready`, firewall, credentials |
| Slow queries | Missing indexes | Verify index strategy in schema docs |

---

## Operational Checklist

- [ ] Backup completed before deployment
- [ ] PostgreSQL health confirmed (`pg_isready`)
- [ ] Alembic at latest revision
- [ ] Data migration validated (no unexplained data loss)
- [ ] Smoke tests pass (19/19)
- [ ] Health endpoint verified after restart
- [ ] Application logs show clean startup
- [ ] Rollback tested and verified
- [ ] Monitoring configured (health endpoint, logs)
- [ ] Feature flag documented for operations team
- [ ] JSON backup preserved for minimum 7 days post-cutover
