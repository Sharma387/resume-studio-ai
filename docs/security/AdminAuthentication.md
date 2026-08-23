# Admin Authentication & Security

## Role Model

RSAI uses two roles defined in `app/models/user.py`:

| Role | Enum Value | Description |
|---|---|---|
| `UserRole.USER` | `"user"` | Standard authenticated user |
| `UserRole.ADMIN` | `"admin"` | Administrator with access to the Administration Console |

All new users created via `POST /api/v1/auth/register` default to `UserRole.USER`.

## Creating an Administrator

### Via CLI Script

```bash
cd backend
source .venv/bin/activate

# Create a new admin user
python scripts/create_admin.py \
    --email admin@example.com \
    --password "SecurePassword123!" \
    --name "System Administrator"

# Promote an existing user to admin
python scripts/create_admin.py \
    --email existing@example.com \
    --promote
```

### Via Direct API (Development Only)

```python
from app.services.user_service import UserService
svc = UserService()
user = svc.get_by_email("user@example.com")
user.role = "admin"
svc.repo.save(user)
```

## JWT Configuration

| Setting | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | `""` (insecure) | HMAC signing key — minimum 32 characters |
| `JWT_ALGORITHM` | `"HS256"` | Signing algorithm |
| `JWT_ACCESS_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `JWT_REFRESH_EXPIRE_DAYS` | `7` | Refresh token lifetime |

**Security requirement:** `JWT_SECRET_KEY` must be at least 32 characters. The application will **fail to start** in production mode if this requirement is not met.

## Authorization Flow

```
Request with JWT
  ↓
HTTPBearer extracts Authorization header
  ↓
get_current_user() validates token, loads User from repository
  ↓
require_user() ensures user exists (or returns mock in DEBUG mode)
  ↓
require_admin() checks user.role == "admin"
  ↓
Route handler executes
```

## Administration Console

Accessible at `/admin` after login. Only users with `role="admin"` can access any `/api/v1/admin/*` endpoint. Non-admin users receive HTTP 403 Forbidden.

## Security Considerations

| Concern | Mitigation |
|---|---|
| Weak JWT secret | Startup validation enforces 32+ char minimum |
| Empty JWT secret | Production startup fails with clear error |
| Token forgery | HMAC-SHA256 with server-side secret |
| Token replay | 15-minute access token expiry |
| Refresh token theft | SHA-256 hashed storage, rotation on use |
| Privilege escalation | Role checked from database on every request |
| SQL injection | All queries parameterized via SQLAlchemy |
| Password storage | bcrypt hashing |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | No or invalid JWT | Login again, check token expiry |
| `403 Forbidden` on admin pages | User is not admin | Promote via `create_admin.py` |
| `JWT secret key is insecure` | `JWT_SECRET_KEY` < 32 chars | Set a longer secret in `.env` |
| `Admin icon not visible` | User role is not `admin` | Check `GET /api/v1/auth/me` response |
| Mock user in production | `DEBUG=true` in production env | Set `DEBUG=false` in `.env` |
