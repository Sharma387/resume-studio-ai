"""Global test configuration."""

from app.core.config import settings

# Enable debug mode so auth dependency auto-creates a mock user
settings.debug = True

# Tests use JSON backend by default (no PostgreSQL dependency required)
settings.storage_backend = "json"

# Ensure DATABASE_URL is set for admin service connectivity checks
if not settings.database_url:
    settings.database_url = "postgresql://rsai:rsai@localhost:5432/rsai"
