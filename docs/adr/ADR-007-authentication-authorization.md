# ADR-007: Authentication & Authorization

**Context:** RSAI requires secure user authentication with JWT, refresh token rotation, role-based admin access, and password management.

**Decision:** JWT access tokens (15 min) + refresh tokens (7 days) with SHA-256 hashed storage. Admin access enforced by `require_admin` dependency on every admin endpoint. Password policy (12+ chars, mixed case, digit, special) enforced at change time.

**Alternatives considered:** Session-based auth (not suitable for API), OAuth 2.0 (premature — added to roadmap).

**Consequences:** Stateless authentication via JWT. Refresh token rotation provides automatic revocation. Admin access is enforced at the framework level, not in business logic. Password changes propagate to both backends.
