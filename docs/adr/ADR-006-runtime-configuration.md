# ADR-006: Runtime Configuration

**Context:** RSAI needed to support runtime configuration changes (model switching, feature flags) without application restarts.

**Decision:** Implement a `ConfigurationService` that writes to `.env` and updates the in-memory `settings` object simultaneously. The `DevelopmentFeatures` service provides a single source of truth for all development-mode capabilities.

**Alternatives considered:** Database-backed configuration (requires schema changes), environment variables only (requires restart).

**Consequences:** Runtime configuration changes persist across restarts. Some changes (storage backend switch) still require restart. The `ConfigurationService` can be backed by PostgreSQL in future without changing callers.
