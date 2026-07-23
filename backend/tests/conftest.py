"""Global test configuration."""

from app.core.config import settings

# Enable debug mode so auth dependency auto-creates a mock user
settings.debug = True
