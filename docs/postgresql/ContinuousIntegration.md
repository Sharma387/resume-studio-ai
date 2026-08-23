# RSAI Continuous Integration

## Pipeline Architecture

```
                  ┌─────────────────┐
                  │  Push / PR      │
                  │  (main/develop) │
                  └────────┬────────┘
                           │
                    ┌──────┴──────┐
                    │  Code       │
                    │  Quality    │
                    │  (ruff)     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────┴──────┐  ┌──┴────────┐  ┌┴─────────────┐
       │ Tests: JSON │  │ Tests: PG │  │ Database     │
       │ Backend     │  │ Backend   │  │ Validation   │
       └──────┬──────┘  └──────┬────┘  └──────┬───────┘
              │                │               │
              └────────────────┼───────────────┘
                               │
                        ┌──────┴──────┐
                        │  Smoke      │
                        │  Tests (PG) │
                        └──────┬──────┘
                               │
                        ┌──────┴──────┐
                        │  All pass?  │
                        └──────┬──────┘
                          YES  │  NO
                           │   └──→ Upload artifacts
                           │         Fail pipeline
                      ┌────┴────┐
                      │  ✅ CI  │
                      │  Passed │
                      └─────────┘
```

## Workflows

### CI Pipeline (`.github/workflows/ci.yml`)

Triggered on:
- Push to `main` or `develop`
- Pull requests targeting `main`
- Only when `backend/**` or workflow files change

| Job | Backend | Dependencies |
|---|---|---|
| `quality` | None | Runs ruff lint + format check |
| `test-json` | JSON | Full test suite, no DB needed |
| `test-postgres` | PostgreSQL | Full test suite, requires PG service |
| `database-validation` | PostgreSQL | Alembic upgrade→downgrade→upgrade cycle |
| `smoke-tests` | PostgreSQL | 19 smoke tests via `smoke_test.py` |

### Release Pipeline (`.github/workflows/release.yml`)

Triggered on:
- Tag push matching `v*`

| Job | Purpose |
|---|---|
| `pre-release` | Clean repo check, JSON tests, script presence, documentation check |
| `postgres-validation` | Full PG test suite + smoke tests |
| `create-release` | GitHub Release creation with auto-generated notes |

## Required Secrets

| Secret | Description |
|---|---|
| (none) | PostgreSQL runs as a CI service container — no secrets needed |

## Environment Variables

| Variable | CI Value | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://rsai:rsai@localhost:5432/rsai` | PostgreSQL connection |
| `STORAGE_BACKEND` | `json` or `postgres` | Test mode |
| `ALLOW_MOCK_AI_DATA` | `true` | Enables AI mock data for testing |

## PostgreSQL Service Configuration

```yaml
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_USER: rsai
      POSTGRES_PASSWORD: rsai
      POSTGRES_DB: rsai
    ports:
      - 5432:5432
    options: >-
      --health-cmd "pg_isready -U rsai -d rsai"
      --health-interval 5s
      --health-timeout 5s
      --health-retries 10
```

## Running CI Locally

```bash
# Prerequisites
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Code quality
ruff check app/
ruff format app/ --check

# Tests (JSON backend)
python -m pytest tests/

# Tests (PostgreSQL backend)
export DATABASE_URL=postgresql://rsai:rsai@localhost:5432/rsai
export STORAGE_BACKEND=postgres
alembic upgrade head
python -m pytest tests/

# Smoke tests
python -m scripts.deployment.smoke_test
```

## Failure Diagnostics

When a CI job fails:

1. **Test artifacts** — JUnit XML reports are uploaded for all test runs
2. **Alembic history** — captured on PG test failures
3. **Logs** — pytest logs uploaded when available
4. **Smoke test output** — captured on smoke test failures

To diagnose locally:
```bash
# Replicate the failing environment
docker compose up -d postgres
alembic upgrade head
STORAGE_BACKEND=postgres DATABASE_URL=... python -m pytest tests/ -v -k "test_name"
```

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `relation "users" does not exist` | Migrations not run | `alembic upgrade head` |
| `role "rsai" does not exist` | PostgreSQL not configured | Check service container settings |
| Tests timeout in CI | Resource constraints | Increase `job.timeout-minutes` |
| Smoke tests fail | Data not migrated | Run `python -m scripts.migrate_data --all` |
| Ruff check fails | Formatting issues | `ruff format app/` then commit |

## Release Process

```
1. Ensure all CI checks pass on main
2. git tag -a v1.0.0 -m "v1.0.0"
3. git push origin v1.0.0
4. Release pipeline runs automatically
5. Release notes generated from commits
6. GitHub Release created
7. Deployment team notified
```
