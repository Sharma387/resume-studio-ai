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
    # Pin a specific local model, e.g. "deepseek-coder-v2:16b". Empty (the
    # default) picks the smallest installed model, because on a 16GB machine a
    # 9GB model plus its context cache exhausts RAM and swap and generation
    # crawls. Set AI_OLLAMA_MODEL to use a larger, more capable model.
    ollama_model: str = ""
    # Provider order for AI calls, tried in sequence until one succeeds.
    # Supported values: "ollama" (local model), "omniroute" (cloud gateway).
    # Dev default is Ollama-first; production sets "omniroute,ollama".
    ai_provider_order: str = "ollama,omniroute"
    ai_model_auto: bool = True
    ai_probe_timeout: int = 6
    ai_probe_limit: int = 10
    ai_route_cache_ttl: int = 300

    # ── Resume parsing ───────────────────────────────────────────
    # Parse the resume section-by-section (each section is one AI call)
    # instead of one giant call. Local models generate a few tokens/sec,
    # so a single full-resume JSON takes tens of minutes and overruns the
    # model context window, which silently truncates roles and bullets.
    parse_chunked: bool = True
    parse_max_chunk_chars: int = 2600
    # Per-chunk generation cap. A section's JSON runs from ~150 tokens (header)
    # to ~1800 (the certifications block, which is dense), and a cap below that
    # truncates the response mid-JSON and loses the whole section. It is a max,
    # not a target, so small sections still finish as soon as they are done.
    parse_chunk_num_predict: int = 2000
    # Per-chunk ceiling before the chunk counts as failed. A small section
    # should take seconds; a long one here means the model or the box is in
    # trouble, and waiting longer only delays the partial result.
    parse_chunk_timeout: int = 150
    # Hard ceiling for the whole chunked parse. When it is hit, whatever has
    # been parsed so far is merged and returned instead of continuing — a
    # resume must never sit parsing for hours.
    parse_time_budget: int = 480
    # Chunks are retried once, but only while failures look isolated. If this
    # many chunks fail in a row the provider is unhealthy, and retrying each
    # one just multiplies the wait, so the parse gives up early.
    parse_max_consecutive_failures: int = 3
    # Extra AI pass that diffs the parsed output against the source text and
    # reports omissions (best effort; never fails the parse). Off by default:
    # it costs one extra model call per section, which roughly doubles parse
    # time. Turn it on to check fidelity on a resume you suspect is being
    # parsed incompletely.
    parse_verify_completeness: bool = False
    # Fall back to the single-shot whole-resume prompt if chunking yields
    # nothing usable. Only used when chunking produced nothing at all — a
    # partial chunked result is far better than another long call.
    parse_chunk_fallback_single_shot: bool = True

    # ── PDF extraction ──────────────────────────────────────────
    # A PDF whose text layer holds fewer than this many characters is treated
    # as image-only and routed to AI OCR.
    pdf_text_layer_min_chars: int = 200
    pdf_ai_ocr_fallback: bool = True
    pdf_ai_ocr_model: str = "qwen3-vl:8b"
    pdf_ai_ocr_dpi: int = 150
    pdf_ai_ocr_num_predict: int = 4096
    pdf_ai_ocr_timeout: int = 300
    pdf_ai_ocr_probe_timeout: int = 5

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
