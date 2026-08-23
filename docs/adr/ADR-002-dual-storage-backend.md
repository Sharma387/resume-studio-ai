# ADR-002: Dual Storage Backend (JSON + PostgreSQL)

**Context:** RSAI started with JSON file storage for rapid prototyping. PostgreSQL was added later for production requirements.

**Decision:** Implement both backends behind the Repository Pattern. A `STORAGE_BACKEND` feature flag selects the active backend at startup. JSON repositories are retained for emergency rollback and testing.

**Alternatives considered:** Forced PostgreSQL-only from start (slowed prototyping), database per environment (increased complexity).

**Consequences:** 2x repository implementations needed. JSON backend serves as a rollback path. Testing must validate both backends.
