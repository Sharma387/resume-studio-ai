# ADR-008: Deployment Strategy

**Context:** RSAI needed automated deployment, rollback, and validation procedures for production releases.

**Decision:** GitHub Actions CI with 5 pipeline jobs (quality, JSON tests, PG tests, DB validation, smoke tests). Deployment via `scripts/deployment/deploy.sh` with dry-run mode. Rollback via `scripts/deployment/rollback.sh` with JSON fallback.

**Alternatives considered:** Docker-only deployment (not yet ready), manual deployment (error-prone).

**Consequences:** Every commit validates both storage backends. Deployment requires passing all 5 CI stages. Rollback changes a single `.env` flag and restarts. PostgreSQL is the only production backend; JSON is retained for emergency rollback.
