# ADR-001: Repository Pattern

**Context:** RSAI needed a persistence layer that supports both JSON file storage and PostgreSQL without changing business logic.

**Decision:** Implement the Repository Pattern with abstract interfaces, a factory, and concrete implementations for each storage backend.

**Alternatives considered:** Active Record (tight coupling), Data Mapper (over-engineering for current scale).

**Consequences:** Services never know which backend is active. Adding a new backend requires implementing 14 repository interfaces. Testing is simplified — mock repositories can be injected.
