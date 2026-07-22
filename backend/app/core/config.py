from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # ── App ─────────────────────────────────────────────────────
    app_name: str = "Resume Studio AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Storage paths ───────────────────────────────────────────
    storage_base: str = "storage"
    upload_dir: str = "uploads"

    # ── Upload limits ───────────────────────────────────────────
    max_upload_size: int = 10 * 1024 * 1024  # 10 MB
    allowed_extensions: str = ".pdf,.docx,.txt"
    allowed_mime_types: str = "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"

    # ── OmniRoute AI ────────────────────────────────────────────
    omniroute_api_url: str = "http://localhost:20128/v1/chat/completions"
    omniroute_api_key: str = ""
    omniroute_model: str = "kiro/claude-haiku-4.5"
    omniroute_timeout: int = 60
    omniroute_max_retries: int = 1

    # ── JWT ─────────────────────────────────────────────────────
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # ── PDF defaults ────────────────────────────────────────────
    pdf_left_margin_mm: int = 25
    pdf_right_margin_mm: int = 25
    pdf_top_margin_mm: int = 20
    pdf_bottom_margin_mm: int = 25
    pdf_default_template: str = "executive"

    # ── Pagination ──────────────────────────────────────────────
    default_page_size: int = 20
    max_page_size: int = 100

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_base)

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    @property
    def allowed_extensions_set(self) -> set[str]:
        return set(self.allowed_extensions.split(","))

    @property
    def allowed_mime_types_set(self) -> set[str]:
        return set(self.allowed_mime_types.split(","))


settings = Settings()
