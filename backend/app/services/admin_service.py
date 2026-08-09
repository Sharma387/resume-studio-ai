"""Administrative service for system configuration, diagnostics, and monitoring."""

import time

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_sync_session
from app.db.models.application import ApplicationModel
from app.db.models.resume import ResumeModel
from app.db.models.user import UserModel
from app.services.development_features import development_features
from app.services.omniroute_service import check_ai_connection

logger = get_logger(__name__)

_START_TIME = time.time()


def get_uptime() -> float:
    return time.time() - _START_TIME


# ── Configuration ──────────────────────────────────────────────────────────


def get_config() -> dict:
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "storage_backend": settings.storage_backend,
        "database_url": _mask_url(settings.database_url),
        "omniroute_api_url": settings.omniroute_api_url,
        "omniroute_api_key_configured": bool(settings.omniroute_api_key),
        "omniroute_model": settings.omniroute_model,
        "omniroute_timeout": settings.omniroute_timeout,
        "omniroute_max_retries": settings.omniroute_max_retries,
        "allow_mock_ai_data": settings.allow_mock_ai_data,
        "jwt_access_expire_minutes": settings.jwt_access_expire_minutes,
        "jwt_refresh_expire_days": settings.jwt_refresh_expire_days,
        "db_pool_size": settings.db_pool_size,
        "db_max_overflow": settings.db_max_overflow,
        "db_pool_timeout": settings.db_pool_timeout,
        "db_echo": settings.db_echo,
    }


def _mask_url(url: str) -> str:
    if not url:
        return ""
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            _, host = rest.split("@", 1)
            return f"{scheme}://****@{host}"
    return url


# ── AI Diagnostics ──────────────────────────────────────────────────────────


async def check_ai_connectivity() -> dict:
    connected = await check_ai_connection()
    return {
        "provider": "OmniRoute",
        "configured_endpoint": settings.omniroute_api_url,
        "configured_model": settings.omniroute_model,
        "reachable": connected,
        "mock_mode": settings.allow_mock_ai_data and settings.debug,
    }


async def test_ai_connection() -> dict:
    from app.services.omniroute_service import OmniRouteError, OmniRouteService

    start = time.time()
    result = {
        "endpoint": settings.omniroute_api_url,
        "model": settings.omniroute_model,
        "reachable": False,
        "response_time_ms": None,
        "http_status": None,
        "error": None,
        "retry_count": 0,
    }

    try:
        srv = OmniRouteService()
        response = await srv.send_prompt(
            "You are a helpful assistant.",
            "Reply only with OK",
        )
        elapsed = (time.time() - start) * 1000
        result["reachable"] = True
        result["response_time_ms"] = round(elapsed, 1)
        result["http_status"] = 200
        result["retry_count"] = 0
        result["content"] = response.strip()
        logger.info("AI connection test succeeded", elapsed_ms=round(elapsed, 1))
    except OmniRouteError as e:
        elapsed = (time.time() - start) * 1000
        result["response_time_ms"] = round(elapsed, 1)
        result["error"] = str(e)
        logger.warning("AI connection test failed", error=str(e))
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        result["response_time_ms"] = round(elapsed, 1)
        result["error"] = f"Unexpected error: {e}"
        logger.error("AI connection test unexpected error", error=str(e))

    return result


async def discover_models() -> list[dict]:
    url = settings.omniroute_api_url.replace("/chat/completions", "/models")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return _dedupe_models(data.get("data", []))
    except Exception as e:
        logger.warning("Model discovery failed", error=str(e))
        return []


def _dedupe_models(models: list[dict]) -> list[dict]:
    """Deterministically deduplicate discovered models by canonical id.

    The upstream model catalog may list the same canonical model id more than
    once (e.g. when aggregated across providers). Keep the first occurrence per
    id so the collection exposed to clients contains each canonical id exactly
    once while distinct provider/model identities are preserved.
    """
    seen: set[str] = set()
    result: list[dict] = []
    for model in models:
        model_id = model.get("id")
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        result.append(
            {
                "id": model_id,
                "object": model.get("object", "model"),
                "owned_by": model.get("owned_by", ""),
            }
        )
    return result


# ── Database Diagnostics ───────────────────────────────────────────────────


def get_database_status() -> dict:
    status = {
        "backend": settings.storage_backend,
        "migration": None,
        "table_counts": {},
        "pool": {
            "size": settings.db_pool_size,
            "overflow": settings.db_max_overflow,
            "timeout": settings.db_pool_timeout,
        },
    }

    if settings.storage_backend != "postgres" or not settings.database_url:
        return status

    try:
        session = get_sync_session()
        from sqlalchemy import text

        row = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        status["migration"] = row[0] if row else None

        for table, model_cls in [
            ("users", UserModel),
            ("resumes", ResumeModel),
            ("applications", ApplicationModel),
        ]:
            try:
                count = session.query(model_cls).count()
                status["table_counts"][table] = count
            except Exception:
                status["table_counts"][table] = None

        session.close()
    except Exception as e:
        logger.warning("Database diagnostics failed", error=str(e))

    return status


def validate_database() -> dict:
    results = {"valid": True, "checks": []}

    try:
        session = get_sync_session()
        from sqlalchemy import text

        # Check connection
        session.execute(text("SELECT 1"))
        results["checks"].append({"name": "Connection", "status": "ok"})

        # Check alembic version
        row = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        if row:
            results["checks"].append({"name": "Migration", "status": "ok", "detail": row[0]})
        else:
            results["checks"].append({"name": "Migration", "status": "warn", "detail": "No migration version"})

        # Check table counts
        for table in ["users", "resumes", "applications", "cover_letters", "match_results"]:
            try:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                results["checks"].append({"name": f"Table {table}", "status": "ok", "detail": f"{count} rows"})
            except Exception as e:
                results["checks"].append({"name": f"Table {table}", "status": "error", "detail": str(e)[:100]})
                results["valid"] = False

        # Check FK integrity
        fk_queries = [
            (
                "resumes → users",
                "SELECT COUNT(*) FROM resumes r WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = r.user_id)",
            ),
            (
                "applications → users",
                "SELECT COUNT(*) FROM applications a WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.user_id)",
            ),
        ]
        for name, query in fk_queries:
            orphans = session.execute(text(query)).scalar() or 0
            status = "ok" if orphans == 0 else "warn"
            if orphans > 0:
                results["valid"] = False
            results["checks"].append({"name": f"FK {name}", "status": status, "detail": f"{orphans} orphans"})

        session.close()
    except Exception as e:
        results["valid"] = False
        results["checks"].append({"name": "Database", "status": "error", "detail": str(e)[:200]})

    return results


# ── Storage Diagnostics ────────────────────────────────────────────────────


def get_storage_status() -> dict:
    from pathlib import Path

    storage_dir = Path("storage")
    json_files = 0
    dir_sizes = {}
    if storage_dir.exists():
        for subdir in storage_dir.iterdir():
            if subdir.is_dir():
                count = len(list(subdir.glob("**/*.json")))
                dir_sizes[subdir.name] = count
                json_files += count

    return {
        "backend": "postgres",
        "json_files_available_for_migration": json_files,
        "dir_counts": dir_sizes,
    }


# ── Dashboard ──────────────────────────────────────────────────────────────


async def get_dashboard() -> dict:
    ai_status = await check_ai_connectivity()
    db_status = get_database_status()

    return {
        "version": settings.app_version,
        "environment": "production" if not settings.debug else "development",
        "storage_backend": settings.storage_backend,
        "ai_provider": "OmniRoute",
        "ai_model": settings.omniroute_model,
        "ai_connected": ai_status.get("reachable", False),
        "database_connected": settings.storage_backend == "postgres",
        "migration": db_status.get("migration"),
        "uptime_seconds": round(get_uptime(), 1),
        "table_counts": db_status.get("table_counts", {}),
    }


# ── Feature Flags ──────────────────────────────────────────────────────────


def get_features() -> dict:
    return {
        "debug": development_features.debug_enabled,
        "allow_mock_ai_data": settings.allow_mock_ai_data,
        "storage_backend": settings.storage_backend,
        "ai_enabled": bool(settings.omniroute_api_key) or "localhost" in settings.omniroute_api_url,
        "database_enabled": settings.storage_backend == "postgres",
        "mock_mode": development_features.mock_ai,
    }


def set_feature(key: str, value: str | bool) -> dict:
    allowed = {"allow_mock_ai_data": bool}
    if key not in allowed:
        raise ValueError(f"Cannot modify feature '{key}' at runtime")
    if not isinstance(value, allowed[key]):
        raise TypeError(f"Expected {allowed[key].__name__} for '{key}'")

    value_bool = bool(value)
    if key == "allow_mock_ai_data":
        settings.allow_mock_ai_data = value_bool
        logger.info("Feature flag updated", key=key, value=value_bool)

    return get_features()


# ── Resume Parse Test (read-only, no persistence) ──────────────────────────


async def test_parse_resume(text: str) -> dict:
    import time

    from app.services.ai_core.exceptions import AIServiceUnavailable
    from app.services.parser_service import ParseError, parse_resume

    start = time.time()
    result = {
        "latency_ms": None,
        "success": False,
        "error": None,
        "parsed_resume": None,
    }

    try:
        parsed = await parse_resume(text)
        elapsed = (time.time() - start) * 1000
        result["latency_ms"] = round(elapsed, 1)
        result["success"] = True
        result["parsed_resume"] = parsed.model_dump(mode="json")
    except ParseError as e:
        elapsed = (time.time() - start) * 1000
        result["latency_ms"] = round(elapsed, 1)
        result["error"] = str(e)
    except AIServiceUnavailable as e:
        elapsed = (time.time() - start) * 1000
        result["latency_ms"] = round(elapsed, 1)
        result["error"] = f"AI service unavailable: {e}"
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        result["latency_ms"] = round(elapsed, 1)
        result["error"] = f"Parse failed: {e}"

    return result


# ── AI Snippet Parse Test ─────────────────────────────────────────────────────


_SNIPPET = """John Doe
john.doe@email.com | +1 555-123-4567 | San Francisco, CA

SUMMARY
Experienced software engineer with 5+ years building web applications.

EXPERIENCE
Senior Software Engineer, TechCorp (2021-Present)
- Led team of 5 engineers building microservices architecture
- Reduced API response times by 40%

Software Engineer, StartupX (2018-2021)
- Built core SaaS platform using React and Python

EDUCATION
BS Computer Science, University of California, Berkeley (2014-2018)
GPA: 3.7

SKILLS
Languages: Python, TypeScript, Go
Frameworks: React, FastAPI, Next.js
Tools: Docker, AWS, PostgreSQL
"""


async def test_ai_parse_snippet() -> dict:
    """Test AI parsing with a hardcoded resume snippet. Nothing is persisted."""
    result = await test_parse_resume(_SNIPPET)
    if result["success"] and result.get("parsed_resume"):
        parsed = result["parsed_resume"]
        result["parsed"] = {
            "name": parsed.get("full_name"),
            "email": parsed.get("email"),
            "skills_count": len(parsed.get("skills", [])),
            "experience_count": len(parsed.get("experience", [])),
        }
    else:
        result["parsed"] = None
    result.pop("parsed_resume", None)
    return result


# ── Storage Management ────────────────────────────────────────────────────────


def get_storage_management_status() -> dict:
    """Storage status — PostgreSQL is the only runtime backend."""
    from pathlib import Path

    from alembic.config import Config as AlembicConfig
    from alembic.script import ScriptDirectory

    storage_dir = Path("storage")
    json_files = 0
    dir_counts = {}
    if storage_dir.exists():
        for subdir in storage_dir.iterdir():
            if subdir.is_dir():
                count = len(list(subdir.glob("**/*.json")))
                dir_counts[subdir.name] = count
                json_files += count

    alembic_head = None
    alembic_current = None
    migration_required = None
    try:
        alembic_cfg = AlembicConfig("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        alembic_head = script.get_current_head()
    except Exception:
        pass

    try:
        conn = get_sync_session()
        row = conn.execute(__import__("sqlalchemy").text("SELECT version_num FROM alembic_version")).fetchone()
        alembic_current = row[0] if row else None
        conn.close()
    except Exception:
        pass

    if alembic_head and alembic_current:
        migration_required = alembic_current != alembic_head

    return {
        "backend": "postgres",
        "alembic_current": alembic_current,
        "alembic_head": alembic_head,
        "migration_required": migration_required,
        "pool_size": settings.db_pool_size,
        "pool_overflow": settings.db_max_overflow,
        "json_files_available_for_migration": json_files,
        "dir_counts": dir_counts,
    }


def run_storage_validation() -> dict:
    """Comprehensive validation before switching backends."""
    from alembic.config import Config as AlembicConfig
    from alembic.script import ScriptDirectory

    checks: list[dict] = []
    all_pass = True

    # 1. Database reachable
    if settings.database_url:
        try:
            conn = get_sync_session()
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            conn.close()
            checks.append({"name": "PostgreSQL reachable", "status": "ok"})
        except Exception as e:
            checks.append({"name": "PostgreSQL reachable", "status": "error", "detail": str(e)[:100]})
            all_pass = False
    else:
        checks.append({"name": "PostgreSQL reachable", "status": "warn", "detail": "DATABASE_URL not set"})
        all_pass = False

    # 2. Alembic migration
    try:
        alembic_cfg = AlembicConfig("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()
        if settings.database_url:
            conn = get_sync_session()
            row = conn.execute(__import__("sqlalchemy").text("SELECT version_num FROM alembic_version")).fetchone()
            current = row[0] if row else None
            conn.close()
            if current == head:
                checks.append({"name": "Migration at head", "status": "ok", "detail": head})
            else:
                checks.append(
                    {"name": "Migration at head", "status": "error", "detail": f"Current: {current}, Head: {head}"}
                )
                all_pass = False
        else:
            checks.append(
                {"name": "Migration at head", "status": "warn", "detail": "Cannot check without DB connection"}
            )
    except Exception as e:
        checks.append({"name": "Migration check", "status": "error", "detail": str(e)[:100]})
        all_pass = False

    # 3. Required tables exist
    required_tables = [
        "users",
        "resumes",
        "applications",
        "cover_letters",
        "match_results",
        "resume_versions",
        "writer_suggestions",
        "interview_sessions",
        "timeline_events",
        "application_notes",
        "interview_questions",
        "interview_answers",
        "readiness_assessments",
        "session_summaries",
    ]
    if settings.database_url:
        try:
            conn = get_sync_session()
            from sqlalchemy import text

            existing = set(
                row[0]
                for row in conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).fetchall()
            )
            missing = [t for t in required_tables if t not in existing]
            if missing:
                checks.append(
                    {"name": "Required tables", "status": "error", "detail": f"Missing: {', '.join(missing)}"}
                )
                all_pass = False
            else:
                checks.append({"name": "Required tables", "status": "ok", "detail": f"{len(existing)} tables present"})
            conn.close()
        except Exception as e:
            checks.append({"name": "Required tables", "status": "error", "detail": str(e)[:100]})
            all_pass = False
    else:
        checks.append({"name": "Required tables", "status": "warn", "detail": "Cannot check without DB connection"})

    # 4. Repository factory loads correctly
    try:
        from app.services.repositories.factory import get_user_repository

        repo = get_user_repository()
        checks.append({"name": "Repository factory", "status": "ok", "detail": type(repo).__name__})
    except Exception as e:
        checks.append({"name": "Repository factory", "status": "error", "detail": str(e)[:100]})
        all_pass = False

    return {"valid": all_pass, "checks": checks}


async def switch_storage_backend(target: str) -> dict:
    """Storage backend switching is no longer supported. PostgreSQL is the only runtime backend."""
    raise RuntimeError("Storage backend switching is not supported. PostgreSQL is the only runtime storage backend.")


async def run_migration() -> dict:
    """Run Alembic migration (upgrade head)."""
    from alembic.config import Config as AlembicConfig

    from alembic import command

    try:
        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        return {"success": True, "detail": "Migration completed successfully"}
    except Exception as e:
        logger.error("Migration failed", error=str(e))
        return {"success": False, "detail": str(e)[:200]}


# ── Development Status ────────────────────────────────────────────────────────


def get_development_status() -> dict:
    return development_features.get_status()
