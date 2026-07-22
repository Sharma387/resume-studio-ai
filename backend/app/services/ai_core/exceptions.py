class AIError(Exception):
    """Base exception for all AI-related errors."""


class AIServiceUnavailable(AIError):
    """Raised when the AI service cannot be reached after retries."""


class AIResponseError(AIError):
    """Raised when the AI returns an invalid or unparseable response."""


class AIMockFallback(AIError):
    """Raised internally when falling back to mock data."""
