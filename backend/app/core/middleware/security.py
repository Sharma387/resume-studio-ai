"""Security headers middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings

PREVIEW_FILE_PREFIX = "/api/v1/resume/preview/file/"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if request.url.path.startswith(PREVIEW_FILE_PREFIX):
            # Generated preview HTML is designed to be embedded in the designer iframe,
            # so allow configured origins instead of blanket DENY. Build the CSP from
            # a normalized source list; fall back to same-origin if misconfigured.
            ancestors = settings.frame_ancestors_list or ["'self'"]
            response.headers["Content-Security-Policy"] = f"frame-ancestors {' '.join(ancestors)}"
        else:
            response.headers["X-Frame-Options"] = "DENY"

        return response
