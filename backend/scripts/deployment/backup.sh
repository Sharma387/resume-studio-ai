#!/usr/bin/env bash
# RSAI Backup Script — JSON + PostgreSQL
# Usage: ./scripts/deployment/backup.sh [--dir BACKUP_DIR]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$SCRIPT_DIR"

BACKUP_DIR="${1:-./backups/$(date -u +'%Y%m%d_%H%M%S')}"
mkdir -p "$BACKUP_DIR"

echo "================================================"
echo "  RSAI Backup"
echo "================================================"
echo "  Backup directory: $BACKUP_DIR"
echo

# ── 1. JSON Backup ─────────────────────────────────────────────────
echo "[1/4] Backing up JSON storage..."
if [ -d storage ]; then
    cp -r storage "$BACKUP_DIR/storage"
    echo "  ✅ JSON storage backed up ($(du -sh storage | cut -f1))"
else
    echo "  ⚠️ No storage directory found"
fi

# ── 2. PostgreSQL Backup ────────────────────────────────────────────
echo "[2/4] Backing up PostgreSQL..."
if command -v pg_dump &>/dev/null; then
    pg_dump -h localhost -U rsai -d rsai \
        --format=custom \
        --file="$BACKUP_DIR/rsai_pg.dump" \
        2>/dev/null && \
        echo "  ✅ PostgreSQL backup saved ($(ls -lh "$BACKUP_DIR/rsai_pg.dump" | awk '{print $5}'))" || \
        echo "  ⚠️ PostgreSQL backup failed — check DATABASE_URL"
else
    echo "  ⚠️ pg_dump not available — install postgresql client tools"
fi

# ── 3. Configuration Backup ──────────────────────────────────────────
echo "[3/4] Backing up configuration..."
cp .env "$BACKUP_DIR/env.txt" 2>/dev/null && echo "  ✅ .env backed up" || true
cp .env.example "$BACKUP_DIR/env.example.txt" 2>/dev/null && echo "  ✅ .env.example backed up" || true
alembic history > "$BACKUP_DIR/alembic_history.txt" 2>/dev/null && echo "  ✅ Alembic history saved" || true

# ── 4. Verification ─────────────────────────────────────────────────
echo "[4/4] Verifying backup..."
ls -la "$BACKUP_DIR/"
echo
echo "================================================"
echo "  ✅ BACKUP COMPLETE"
echo "  Directory: $BACKUP_DIR"
echo "================================================"
