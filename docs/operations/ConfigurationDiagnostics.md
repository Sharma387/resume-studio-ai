# Configuration Diagnostics

## Overview

RSAI provides a built-in configuration diagnostics system that checks all critical subsystems at startup and on-demand through the Administration Console.

## Startup Validation

On every application start, the `lifespan` handler runs diagnostics against:

| Component | Check | Failure Mode |
|---|---|---|
| JWT Secret | Present and >= 32 characters | **Production: startup fails.** Development: warning logged. |
| Development Safety | No dev features active in production | Warning logged |
| Database | Connectivity, migration status | Logged (non-blocking) |
| AI | Endpoint configured, connectivity | Logged (non-blocking) |

## Required Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `JWT_SECRET_KEY` | **Yes** | `""` | Minimum 32 characters. Startup fails if missing/insecure in production. |
| `DATABASE_URL` | For PostgreSQL | `""` | Required when `STORAGE_BACKEND=postgres` |
| `STORAGE_BACKEND` | No | `"json"` | `"json"` or `"postgres"` |

## Accessing Diagnostics

### Administration Console

Navigate to **Admin Console → Configuration** (`/admin/configuration`).

### Direct API

```bash
curl -H "Authorization: Bearer <admin-token>" \
  http://localhost:8000/api/v1/admin/configuration/diagnostics
```

Response:
```json
{
  "jwt": { "configured": true, "secure": true, ... },
  "database": { "configured": true, "connected": true, ... },
  "ai": { "configured": true, "connected": true, "model": "oc/big-pickle" },
  "storage": { "backend": "json", ... },
  "environment": { "debug": false, ... }
}
```

## Troubleshooting

| Symptom | Diagnostics Hint | Fix |
|---|---|---|
| Startup fails with JWT error | `jwt.secure: false` | Set `JWT_SECRET_KEY` to 32+ chars in `.env` |
| Admin console shows DB warning | `database.connected: false` | Start PostgreSQL, configure `DATABASE_URL` |
| AI features return mock data | `ai.mock_mode: true` | Set `ALLOW_MOCK_AI_DATA=false` or `DEBUG=false` |
| Health endpoint shows AI disconnected | `ai.connected: false` | Start OmniRoute server |
| 401 on all requests | `jwt.configured: false` | Set `JWT_SECRET_KEY` |
