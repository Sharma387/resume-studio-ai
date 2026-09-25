import re
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # ── App ─────────────────────────────────────────────────────
    app_name: str = "Resume Studio AI"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Storage paths ───────────────────────────────────────────
    storage_base: str = "storage"
    upload_dir: str = "uploads"

    # ── Upload limits ───────────────────────────────────────────
    max_upload_size: int = 10 * 1024 * 1024  # 10 MB
    allowed_extensions: str = ".pdf,.docx,.txt"
    allowed_mime_types: str = (
        "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
    )

    # ── OmniRoute AI ────────────────────────────────────────────
    omniroute_api_url: str = "http://localhost:20128/v1/chat/completions"
    omniroute_api_key: str = ""
    omniroute_model: str = "kiro/claude-haiku-4.5"
    omniroute_timeout: int = 60
    omniroute_max_retries: int = 1
    allow_mock_ai_data: bool = False
    # ── AI Model Router ─────────────────────────────────────────────
    ollama_api_url: str = "http://localhost:11434/v1/chat/completions"
    # Provider order for AI calls, tried in sequence until one succeeds.
    # Supported values: "ollama" (local model), "omniroute" (cloud gateway).
    # Dev default is Ollama-first; production sets "omniroute,ollama".
    ai_provider_order: str = "ollama,omniroute"
    ai_model_auto: bool = True
    ai_probe_timeout: int = 6
    ai_probe_limit: int = 10
    ai_route_cache_ttl: int = 300

    @property
    def ai_providers(self) -> list[str]:
        """Parsed AI provider list (lowercased, blank entries dropped)."""
        return [p.strip().lower() for p in self.ai_provider_order.split(",") if p.strip()]

    # ── JWT ─────────────────────────────────────────────────────
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    @property
    def jwt_secret_secure(self) -> bool:
        return len(self.jwt_secret_key) >= 32

    # ── PDF defaults ────────────────────────────────────────────
    pdf_left_margin_mm: int = 25
    pdf_right_margin_mm: int = 25
    pdf_top_margin_mm: int = 20
    pdf_bottom_margin_mm: int = 25
    pdf_default_template: str = "executive"

    # ── Framing (designer preview iframes) ─────────────────────
    # CSP frame-ancestors allowed to embed generated preview HTML.
    frame_ancestors: str = "'self' http://localhost:5173 http://127.0.0.1:5173"

    @property
    def frame_ancestors_list(self) -> list[str]:
        """Parse frame_ancestors into a normalized source list.

        Tolerates spaces, commas, or mixed separators so a misconfigured
        value can never silently degrade the CSP to ``'self'``-only.
        """
        tokens = re.split(r"[\s,]+", self.frame_ancestors or "")
        return [t for t in tokens if t]

    # ── Pagination ──────────────────────────────────────────────
    default_page_size: int = 20
    max_page_size: int = 100

    # ── PostgreSQL ──────────────────────────────────────────────
    database_url: str = ""
    storage_backend: str = "json"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_statement_timeout: int = 30000

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_base)

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def allowed_extensions_set(self) -> set[str]:
        return set(self.allowed_extensions.split(","))

    @property
    def allowed_mime_types_set(self) -> set[str]:
        return set(self.allowed_mime_types.split(","))


settings = Settings()
