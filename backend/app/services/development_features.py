"""Centralised Development Mode management.

Every development-only capability in RSAI is routed through this service.
No module should inspect settings.debug or settings.allow_mock_ai_data directly.
"""

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DevelopmentFeatures:
    """Single source of truth for all development-mode capabilities."""

    @property
    def debug_enabled(self) -> bool:
        return settings.debug

    @property
    def mock_authentication(self) -> bool:
        """Mock authentication requires debug mode."""
        return settings.debug

    @property
    def mock_ai(self) -> bool:
        """Mock AI data requires BOTH debug mode AND allow_mock_ai_data."""
        return settings.debug and settings.allow_mock_ai_data

    @property
    def mock_matching(self) -> bool:
        """Mock ATS matching requires BOTH debug mode AND allow_mock_ai_data."""
        return settings.debug and settings.allow_mock_ai_data

    @property
    def runtime_storage_switch(self) -> bool:
        """Storage backend switching is always available (admin feature)."""
        return True

    @property
    def runtime_feature_flags(self) -> bool:
        """Runtime feature flag changes are available in debug mode for safety."""
        return settings.debug

    # ── Production Safety Audit ─────────────────────────────────────

    def audit_production_safety(self) -> list[str]:
        """Check that no development features are accidentally enabled in production.

        Returns a list of warnings (empty if all checks pass).
        """
        warnings: list[str] = []

        if not self.debug_enabled:
            if self.mock_ai:
                warnings.append("MOCK_AI enabled without DEBUG — unsafe for production")
            if self.mock_matching:
                warnings.append("MOCK_MATCHING enabled without DEBUG — unsafe for production")
            if self.runtime_feature_flags:
                warnings.append("Runtime feature flags enabled without DEBUG — unsafe for production")
        return warnings

    # ── Structured Status ───────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "development_mode": self.debug_enabled,
            "mock_authentication": self.mock_authentication,
            "mock_ai": self.mock_ai,
            "mock_matching": self.mock_matching,
            "runtime_storage_switch": self.runtime_storage_switch,
            "runtime_feature_flags": self.runtime_feature_flags,
            "configured": {
                "debug": settings.debug,
                "allow_mock_ai_data": settings.allow_mock_ai_data,
                "storage_backend": settings.storage_backend,
            },
        }


development_features = DevelopmentFeatures()
