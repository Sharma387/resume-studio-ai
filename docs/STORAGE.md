# Storage Architecture

## Current (JSON files)

Data is stored as JSON files organized by domain:

```
storage/
├── users/{user_id}.json
├── refresh_tokens/{hash}.json
├── resumes/{resume_id}.json
├── versions/{resume_id}/{version_id}.json
├── matches/{match_id}.json
├── pdfs/{resume_id}.pdf
├── cover_letters/{resume_id}/{letter_id}.json
├── cover_letter_pdfs/{letter_id}.pdf
├── applications/{app_id}.json
├── timeline/{app_id}/{event_id}.json
├── interviews/{app_id}/sessions/{session_id}.json
├── writer_suggestions/{resume_id}/{suggestion_id}.json
└── uploads/{uuid}.{ext}
```

## Future (PostgreSQL)

The repository interfaces in `app/services/repositories/` define the contract:

```python
class UserRepository(ABC):
    def save(user): ...
    def get_by_id(id): ...
    def get_by_email(email): ...

class RefreshTokenRepository(ABC):
    def save(token_hash, user_id, expires_at): ...
    def get_user_id(token_hash): ...
```

Adding PostgreSQL means implementing these interfaces with SQL queries instead of JSON file I/O. Business services (`UserService`, etc.) remain unchanged.

## Migration Path

1. Implement `PostgresUserRepository(UserRepository)`
2. Swap in dependency injection
3. Run data migration script
4. Repeat for each domain
