# Security Architecture

## Authentication

Resume Studio AI uses JWT-based authentication with short-lived access tokens and long-lived refresh tokens.

### Token Lifecycle

| Token | Lifetime | Storage | Purpose |
|---|---|---|---|
| Access token | 15 minutes | Client memory (not localStorage) | API authorization |
| Refresh token | 7 days | Client storage; SHA-256 hash on server | Obtain new access tokens |

### JWT Structure

```json
{
  "sub": "user_id",
  "jti": "unique_token_id",
  "role": "user | admin",
  "type": "access | refresh",
  "exp": 1234567890
}
```

- Signed with HS256 using a configurable secret key (`JWT_SECRET_KEY`)
- Each token contains a unique `jti` (JWT ID) for tracking and revocation
- Access tokens include the user's role for authorization decisions

### Refresh Token Rotation

When a refresh token is used, the old token is invalidated and a new pair is issued. This prevents replay attacks. If a compromised refresh token is used after the legitimate user has already rotated it, the original token will be rejected.

## Password Security

- Passwords are hashed using **bcrypt** (12 rounds) via the `bcrypt` library
- Passwords must be at least 8 characters
- Password hashes are stored in `storage/users/{user_id}.json`
- No plaintext passwords are ever stored or logged
- Password change requires current password verification

## Authorization Model

### Roles

| Role | Permissions |
|---|---|
| `user` | Access own resources; create/edit/delete own data |
| `admin` | All user permissions + access to admin endpoints |

### Resource Ownership

The `check_resource_owner()` helper verifies that a user can only access their own resources. Admins bypass ownership checks.

```python
from app.services.auth_deps import check_resource_owner

check_resource_owner(resource.user_id, current_user)
```

### Endpoint Protection

| Level | Decorator | Behavior |
|---|---|---|
| Public | None | No authentication required |
| Optional | `get_current_user` | Returns User or None |
| Authenticated | `require_user` | Returns 401 if not authenticated |
| Admin | `require_admin` | Returns 403 if not admin |

## Data Protection

### Storage

- All data stored as JSON files under `storage/`
- No sensitive data is encrypted at rest (JSON file storage — database migration planned)
- Passwords are bcrypt-hashed, not stored in plaintext
- Refresh tokens are SHA-256 hashed before storage

### API Security

- Security headers set by `SecurityHeadersMiddleware`:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- CORS is configured via `CORSMiddleware` (relaxed for development; restrict in production)
- Rate limiting is not yet implemented (planned)

## File Upload Security

| Check | Implementation |
|---|---|
| File extension | Allowed: `.pdf`, `.docx`, `.txt` |
| MIME type | Validated against allowed types |
| File size | Maximum 10MB |
| Storage | Stored under `uploads/` with UUID filenames (no path traversal) |
| Execution | Files are not executable; served only through API |

## AI Security Considerations

- AI prompts are externalized in `prompts/` — no user input is interpolated into system prompts
- AI responses are validated against Pydantic schemas before use
- The AI service has a configurable timeout (default 60s) and retry count (default 1)
- When AI service is unavailable, an explicit error is returned (no silent fallback to mock data unless `ALLOW_MOCK_AI_DATA=true`)
- Mock data mode is disabled by default in production

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET_KEY` | Yes | 256-bit random key for token signing |
| `OMNIROUTE_API_KEY` | No | API key for AI gateway |
| `ALLOW_MOCK_AI_DATA` | No | Enable mock data fallback (default: false) |

## Future Improvements

- Rate limiting per user/IP
- OAuth/SSO (Google, LinkedIn, Microsoft)
- API key authentication for programmatic access
- Encryption at rest for stored files
- Audit logging for all admin actions
- Penetration testing before major release
