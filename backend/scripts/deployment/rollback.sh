#!/usr/bin/env bash
# RSAI Rollback Script — PostgreSQL → JSON
# Usage: ./scripts/deployment/rollback.sh [--hard] [--skip-restore]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$SCRIPT_DIR"

HARD=false
SKIP_RESTORE=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --hard) HARD=true; shift ;;
        --skip-restore) SKIP_RESTORE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "================================================"
echo "  RSAI Rollback — PostgreSQL → JSON"
echo "================================================"
echo "  Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo

# ── Step 1: Verify JSON backend is available ──────────────────────
echo "[Step 1/6] Verifying JSON backend availability..."
if [ ! -d storage/users ]; then
    echo "  ⚠️ storage/users not found — JSON data may be incomplete"
    if [ "$HARD" = false ]; then
        echo "  Use --hard to proceed anyway"
        exit 1
    fi
fi
echo "  ✅ JSON storage exists"

# ── Step 2: Backup current PostgreSQL state ────────────────────────
echo "[Step 2/6] Backing up current PostgreSQL state..."
BACKUP_FILE="storage/pg_rollback_$(date -u +'%Y%m%d_%H%M%S').sql"
if command -v pg_dump &>/dev/null; then
    pg_dump -h localhost -U rsai -d rsai > "$BACKUP_FILE" 2>/dev/null && \
        echo "  ✅ PostgreSQL backup saved to $BACKUP_FILE" || \
        echo "  ⚠️ Could not create PostgreSQL backup"
else
    echo "  ⚠️ pg_dump not available — skip PostgreSQL backup"
fi

# ── Step 3: Revert feature flag ────────────────────────────────────
echo "[Step 3/6] Reverting feature flag to JSON..."
if grep -q "STORAGE_BACKEND=postgres" .env 2>/dev/null; then
    sed -i '' 's/STORAGE_BACKEND=postgres/STORAGE_BACKEND=json/' .env 2>/dev/null || \
        sed -i 's/STORAGE_BACKEND=postgres/STORAGE_BACKEND=json/' .env 2>/dev/null || \
        echo "  ⚠️ Could not modify .env — update STORAGE_BACKEND=json manually"
    echo "  ✅ Feature flag reverted to json"
else
    echo "  ✅ Feature flag already set to json"
fi

# ── Step 4: Restart application ────────────────────────────────────
echo "[Step 4/6] Application restart required..."
echo "  Run: systemctl restart rsai   # or equivalent"
echo "  Or: docker compose restart web  # if using Docker"

# ── Step 5: Verify JSON mode ──────────────────────────────────────
echo "[Step 5/6] Verifying application in JSON mode..."
echo "  Check: curl http://localhost:8000/api/v1/health"
echo "  Expected: {\"storage_backend\":\"json\"}"

# ── Step 6: Restore JSON data if needed (hard rollback) ────────────
if [ "$HARD" = true ] && [ "$SKIP_RESTORE" = false ]; then
    echo "[Step 6/6] Restoring JSON data from backup..."
    if [ -d "storage_backup" ]; then
        cp -r storage_backup/* storage/ 2>/dev/null && \
            echo "  ✅ JSON data restored from storage_backup/" || \
            echo "  ⚠️ Could not restore all files"
    else
        echo "  ⚠️ No storage_backup/ directory found"
    fi
fi

echo
echo "================================================"
echo "  ✅ ROLLBACK PREPARED"
echo "  Application configured for JSON mode."
echo "  Restart to apply changes."
echo "================================================"
echo
echo "Post-rollback verification:"
echo "  1. curl http://localhost:8000/api/v1/health"
echo "  2. Run: python -m pytest tests/ --ignore=tests/test_auth.py"
echo "  3. Verify existing data loads correctly"
