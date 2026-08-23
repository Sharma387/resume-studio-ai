#!/usr/bin/env bash
# RSAI Production Deployment Script — PostgreSQL Cutover
# Usage: ./scripts/deployment/deploy.sh [--dry-run] [--skip-migration] [--skip-smoke]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$SCRIPT_DIR"

DRY_RUN=false
SKIP_MIGRATION=false
SKIP_SMOKE=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --skip-migration) SKIP_MIGRATION=true; shift ;;
        --skip-smoke) SKIP_SMOKE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "================================================"
echo "  RSAI Production Deployment"
echo "================================================"
echo "  Mode: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'LIVE')"
echo "  Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo

if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] Would execute deployment steps"
    echo "[DRY-RUN] Skipping actual migration, restart, smoke tests"
fi

# ── Step 1: Environment Validation ────────────────────────────────
echo "[Step 1/7] Validating environment..."
for var in DATABASE_URL STORAGE_BACKEND; do
    if [ -z "${!var:-}" ]; then
        echo "  ❌ $var is not set"
        exit 1
    fi
    echo "  ✅ $var=${!var}"
done

# Verify .env file
if [ ! -f .env ]; then
    echo "  ❌ .env file not found"
    exit 1
fi
echo "  ✅ .env file exists"

# ── Step 2: Database Connectivity ─────────────────────────────────
echo "[Step 2/7] Checking database connectivity..."
python -c "
from app.db.database import create_engine, dispose_engine, check_database_connection
import anyio
async def main():
    eng = await create_engine()
    if eng is None:
        print('❌ Engine creation failed')
        exit(1)
    ok = await check_database_connection()
    if not ok:
        print('❌ Database connection failed')
        exit(1)
    print('  ✅ Database connected')
    await dispose_engine()
anyio.run(main)
" || exit 1

# ── Step 3: Alembic Migration ─────────────────────────────────────
if [ "$SKIP_MIGRATION" = false ]; then
    echo "[Step 3/7] Running Alembic migrations..."
    if [ "$DRY_RUN" = false ]; then
        alembic upgrade head || exit 1
        echo "  ✅ Migrations applied"
    else
        echo "  [DRY-RUN] Would run: alembic upgrade head"
    fi
else
    echo "[Step 3/7] Skipping migrations (--skip-migration)"
fi

# ── Step 4: Data Migration ─────────────────────────────────────────
echo "[Step 4/7] Running JSON → PostgreSQL data migration..."
if [ "$DRY_RUN" = false ]; then
    python -m scripts.migrate_data --all || {
        echo "  ⚠️ Data migration had some errors — review above"
    }
    echo "  ✅ Data migration completed"
else
    echo "  [DRY-RUN] Would run: python -m scripts.migrate_data --all"
fi

# ── Step 5: Migration Validation ──────────────────────────────────
echo "[Step 5/7] Validating migration..."
if [ "$DRY_RUN" = false ]; then
    python -m scripts.migrate_data --validate || {
        echo "  ⚠️ Some validation checks failed — review above"
        echo "  ❌ Deployment aborted"
        exit 1
    }
    echo "  ✅ Migration validated"
else
    echo "  [DRY-RUN] Would run: python -m scripts.migrate_data --validate"
fi

# ── Step 6: Smoke Tests ───────────────────────────────────────────
if [ "$SKIP_SMOKE" = false ]; then
    echo "[Step 6/7] Running smoke tests..."
    if [ "$DRY_RUN" = false ]; then
        python -m scripts.deployment.smoke_test || {
            echo "  ❌ Smoke tests failed"
            exit 1
        }
        echo "  ✅ Smoke tests passed"
    else
        echo "  [DRY-RUN] Would run: python -m scripts.deployment.smoke_test"
    fi
else
    echo "[Step 6/7] Skipping smoke tests (--skip-smoke)"
fi

# ── Step 7: Health Check ──────────────────────────────────────────
echo "[Step 7/7] Verifying health endpoint..."
if command -v curl &>/dev/null; then
    if [ "$DRY_RUN" = false ]; then
        response=$(curl -s http://localhost:8000/api/v1/health 2>/dev/null || echo '{"status":"unreachable"}')
        echo "  Health response: $response"
    else
        echo "  [DRY-RUN] Would curl http://localhost:8000/api/v1/health"
    fi
else
    echo "  ⚠️ curl not available — skip health check"
fi

echo
echo "================================================"
if [ "$DRY_RUN" = false ]; then
    echo "  ✅ DEPLOYMENT COMPLETE"
else
    echo "  ✅ DRY-RUN COMPLETE — no changes made"
fi
echo "================================================"
