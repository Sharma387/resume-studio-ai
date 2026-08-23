# RSAI Administration Console

## Architecture

```
Frontend (React + MUI)                    Backend (FastAPI)
┌─────────────────────────┐              ┌─────────────────────┐
│  AdminLayout            │  HTTP/JSON   │  /api/v1/admin/*    │
│  ├─ DashboardPage       │ ←─────────→  │  admin.py (router)  │
│  ├─ AIConfigPage        │              │  admin_service.py   │
│  ├─ DatabasePage        │              │  auth_deps.py       │
│  ├─ StoragePage         │              │  (require_admin)    │
│  ├─ FeaturesPage        │              └─────────────────────┘
│  ├─ HealthPage          │                      │
│  └─ ParseTestPage       │              ┌───────┴───────┐
└─────────────────────────┘              │  Settings     │
                                         │  OmniRoute    │
                                         │  DB Engine    │
                                         └───────────────┘
```

## API Endpoints

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/admin/dashboard` | Dashboard summary | `require_admin` |
| GET | `/api/v1/admin/config` | Full configuration | `require_admin` |
| GET | `/api/v1/admin/ai` | AI configuration + connectivity | `require_admin` |
| POST | `/api/v1/admin/ai/test` | Test AI connection | `require_admin` |
| GET | `/api/v1/admin/models` | Discover available models | `require_admin` |
| POST | `/api/v1/admin/ai/parse-test` | Test resume parsing | `require_admin` |
| GET | `/api/v1/admin/database` | Database diagnostics | `require_admin` |
| POST | `/api/v1/admin/database/validate` | Validate database integrity | `require_admin` |
| GET | `/api/v1/admin/storage` | Storage diagnostics | `require_admin` |
| GET | `/api/v1/admin/features` | Feature flags | `require_admin` |
| PUT | `/api/v1/admin/features` | Update feature flag | `require_admin` |
| GET | `/api/v1/admin/system` | Aggregated system health | `require_admin` |

## Frontend Routes

| Path | Page | Description |
|---|---|---|
| `/admin` | DashboardPage | Live operational dashboard |
| `/admin/ai` | AIConfigPage | AI configuration, connection test, model discovery |
| `/admin/parse-test` | ParseTestPage | Test resume parsing without persistence |
| `/admin/database` | DatabasePage | Database diagnostics + validation |
| `/admin/storage` | StoragePage | Storage backend diagnostics |
| `/admin/features` | FeaturesPage | Feature flag management |
| `/admin/health` | HealthPage | Aggregated system health |

## Security Model

- All admin endpoints require `require_admin` dependency which checks `user.role == 'admin'`
- Frontend routes are wrapped in `ProtectedRoute` (requires authentication)
- The backend enforces authorization — the frontend guard is a UX layer
- Future: RBAC can extend `require_admin` to check specific permissions

## Configuration Flow

```
.env variables → pydantic Settings → admin_service.get_config()
                  ↓
            Admin API response
                  ↓
            Frontend display
```

Administrators can view all configuration values through the Admin Console. Mutable feature flags (currently `allow_mock_ai_data`) can be toggled at runtime without restarting the application.

## Pages

### Dashboard
- 8 status cards with colour-coded badges
- Table counts section
- Manual refresh button

### AI Configuration
- Current configuration table
- Connection test with latency measurement
- Model discovery table showing available OmniRoute models
- Active model highlighted

### Parse Test
- Text area for pasting resume text
- Parse button triggers AI parsing
- Results show latency, success/failure, parsed JSON
- Nothing is persisted

### Database
- Connection pool configuration display
- Table counts per entity
- Validation runner with per-check status

### Storage
- Current backend display
- JSON file counts per directory

### Feature Flags
- Table of all flags with on/off switches
- Read-only flags clearly marked
- Runtime-mutable flags can be toggled

### System Health
- Four health sections (Application, AI, Database, Storage)
- Each with colour-coded status and detail fields
- Auto-refresh

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| Admin pages return 401 | Not authenticated | Login first |
| Admin pages return 403 | User is not admin | Assign admin role |
| AI test fails | OmniRoute unreachable | Start OmniRoute, check URL |
| Model list empty | OmniRoute unreachable or `/models` not exposed | Check connectivity |
| Database validation fails | Migration not run or FK violations | Run `alembic upgrade head` |
| Feature toggle returns 400 | Key is read-only | Only `allow_mock_ai_data` is mutable |

## Future Roadmap

1. **Dynamic configuration storage** — Move config from `.env` to PostgreSQL for runtime updates
2. **RBAC** — Granular permissions per admin action
3. **Audit log** — Track all admin actions with before/after values
4. **Metrics** — Real-time connection pool monitoring, request rates
5. **Backup/Restore UI** — Trigger and monitor backups from the console
