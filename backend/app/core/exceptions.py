"""Application-wide exception hierarchy."""


class AppError(Exception):
    """Base for all application exceptions."""
    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(self, message: str = "", code: str | None = None, status_code: int | None = None):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422


class AuthenticationError(AppError):
    code = "AUTHENTICATION_ERROR"
    status_code = 401


class AuthorizationError(AppError):
    code = "AUTHORIZATION_ERROR"
    status_code = 403


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409


class StorageError(AppError):
    code = "STORAGE_ERROR"
    status_code = 500


class AIError(AppError):
    code = "AI_ERROR"
    status_code = 503


class PDFGenerationError(AppError):
    code = "PDF_GENERATION_ERROR"
    status_code = 500


class DocumentError(AppError):
    code = "DOCUMENT_ERROR"
    status_code = 400


class RateLimitError(AppError):
    code = "RATE_LIMIT"
    status_code = 429
