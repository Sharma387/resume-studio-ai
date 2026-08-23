"""Enterprise audit logging for all administrative actions.

Audit entries are immutable write-once records.
Stored in PostgreSQL via direct SQL for isolation from ORM caching.
"""

from datetime import UTC, datetime

from sqlalchemy import text

from app.core.logging import get_logger
from app.db.database import get_sync_session

logger = get_logger(__name__)


def log(
    action: str,
    admin_id: str,
    target_user: str | None = None,
    target_object: str | None = None,
    success: bool = True,
    failure_reason: str | None = None,
    details: str | None = None,
) -> None:
    """Create an immutable audit log entry."""
    try:
        session = get_sync_session()
        session.execute(
            text("""
                INSERT INTO audit_log (
                    id, timestamp, admin_id, action, target_user,
                    target_object, success, failure_reason, details
                ) VALUES (
                    gen_random_uuid()::text, :ts, :admin_id, :action, :target_user,
                    :target_object, :success, :failure_reason, :details
                )
            """),
            {
                "ts": datetime.now(UTC).isoformat(),
                "admin_id": admin_id,
                "action": action,
                "target_user": target_user,
                "target_object": target_object,
                "success": success,
                "failure_reason": failure_reason,
                "details": details,
            },
        )
        session.commit()
        session.close()
        logger.info("Audit log entry created", action=action, admin_id=admin_id, target_user=target_user)
    except Exception as e:
        logger.error("Failed to create audit log entry", error=str(e))


def query(
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    admin_id: str | None = None,
    target_user: str | None = None,
) -> dict:
    """Query audit log entries with pagination and filtering."""
    try:
        session = get_sync_session()
        conditions = ["1=1"]
        params: dict = {}

        if action:
            conditions.append("action = :action")
            params["action"] = action
        if admin_id:
            conditions.append("admin_id = :admin_id")
            params["admin_id"] = admin_id
        if target_user:
            conditions.append("target_user = :target_user")
            params["target_user"] = target_user

        where = " AND ".join(conditions)
        count = session.execute(text(f"SELECT COUNT(*) FROM audit_log WHERE {where}"), params).scalar() or 0
        offset = (page - 1) * page_size
        rows = session.execute(
            text(f"SELECT * FROM audit_log WHERE {where} ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"),
            {**params, "limit": page_size, "offset": offset},
        ).fetchall()

        entries = []
        for row in rows:
            entries.append(
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "admin_id": row[2],
                    "action": row[3],
                    "target_user": row[4],
                    "target_object": row[5],
                    "success": row[6],
                    "failure_reason": row[7],
                    "details": row[8],
                }
            )
        session.close()
        return {"entries": entries, "total": count, "page": page, "page_size": page_size}
    except Exception as e:
        logger.error("Failed to query audit log", error=str(e))
        return {"entries": [], "total": 0, "page": page, "page_size": page_size}
