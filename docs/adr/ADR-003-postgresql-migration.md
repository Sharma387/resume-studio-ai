# ADR-003: PostgreSQL Migration

**Context:** RSAI migrated from JSON file storage to PostgreSQL for ACID compliance, concurrent access, and queryability.

**Decision:** Incremental migration starting with the most independent entities (users, refresh_tokens). Each repository migrated independently. Data migration utility (`scripts/migrate_data.py`) supports dry-run and validation modes.

**Alternatives considered:** Big-bang migration (too risky), dual-write during migration (too complex).

**Consequences:** 6 Alembic migrations, 15 tables, 22 foreign keys. Migration completed with zero data loss. 96 orphaned test artifacts in JSON storage (harmless).
