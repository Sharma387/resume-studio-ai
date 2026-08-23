# ADR-005: Administration Console

**Context:** RSAI needed an operational interface for configuration, monitoring, and user management without requiring .env file edits or server log access.

**Decision:** Build a full admin UI as part of the existing React frontend, with dedicated backend admin routes protected by `require_admin`. Admin routes are co-located in the same API service files as non-admin routes to avoid duplication.

**Alternatives considered:** Separate admin dashboard app (added deployment complexity), CLI-only admin tools (poor UX).

**Consequences:** 30 admin API endpoints, 10 admin frontend pages, all protected by role-based access. Adding new admin features follows the same route → service → repository pattern.
