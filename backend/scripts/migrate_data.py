#!/usr/bin/env python3
"""JSON → PostgreSQL Data Migration Utility.

Usage:
    python -m scripts.migrate_data --help
    python -m scripts.migrate_data --dry-run
    python -m scripts.migrate_data --entity users
    python -m scripts.migrate_data --all
    python -m scripts.migrate_data --validate
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

STORAGE_DIR = Path("storage")


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── Progress tracking ─────────────────────────────────────────────────────────


class Progress:
    def __init__(self, verbose: bool = False):
        self.total = 0
        self.success = 0
        self.errors = 0
        self.skipped = 0
        self.error_details: list[str] = []
        self.verbose = verbose

    def log(self, msg: str):
        if self.verbose:
            print(f"  {msg}")

    def summary(self, entity: str, elapsed: float):
        print(
            f"  [{entity}] {self.success} ok, {self.skipped} skipped, "
            f"{self.errors} errors ({self.total} total) in {elapsed:.2f}s"
        )
        for err in self.error_details[-5:]:
            print(f"    ERROR: {err}")


from sqlalchemy.exc import IntegrityError


# ── Data Loaders ──────────────────────────────────────────────────────────────


def _load_json_files(directory: str) -> list[tuple[str, dict]]:
    """Load all JSON files from a directory, returning (stem, data) pairs."""
    dir_path = STORAGE_DIR / directory
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir()):
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append((f.stem, data))
            except (json.JSONDecodeError, OSError) as e:
                print(f"  WARN: Cannot read {f}: {e}")
    return results


def _load_json_subdirs(base_dir: str, subdir_name: str | None = None) -> list[tuple[str, dict]]:
    """Load JSON files from subdirectories. E.g. storage/cover_letters/{resume_id}/{letter_id}.json"""
    base_path = STORAGE_DIR / base_dir
    if not base_path.exists():
        return []
    results = []
    for sub in sorted(base_path.iterdir()):
        if not sub.is_dir():
            continue
        if subdir_name:
            target = sub / subdir_name
            if not target.exists():
                continue
            for f in sorted(target.iterdir()):
                if f.suffix == ".json":
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        results.append((f.stem, data))
                    except (json.JSONDecodeError, OSError) as e:
                        print(f"  WARN: Cannot read {f}: {e}")
        else:
            for f in sorted(sub.iterdir()):
                if f.suffix == ".json":
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        results.append((f.stem, data))
                    except (json.JSONDecodeError, OSError) as e:
                        print(f"  WARN: Cannot read {f}: {e}")
    return results


def _load_interview_files(subdir: str) -> list[tuple[str, dict]]:
    """Load interview files from storage/interviews/{app_id}/{subdir}/{file_id}.json"""
    base_path = STORAGE_DIR / "interviews"
    if not base_path.exists():
        return []
    results = []
    for app_dir in sorted(base_path.iterdir()):
        if not app_dir.is_dir():
            continue
        target = app_dir / subdir
        if not target.exists():
            continue
        for f in sorted(target.iterdir()):
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    results.append((f.stem, data))
                except (json.JSONDecodeError, OSError) as e:
                    print(f"  WARN: Cannot read {f}: {e}")
    return results


# ── Migration Functions ───────────────────────────────────────────────────────


def migrate_users(dry_run: bool, progress: Progress) -> int:
    from app.models.user import User
    from app.services.repositories.postgres.user_repository import PostgresUserRepository

    repo = PostgresUserRepository()
    records = _load_json_files("users")
    progress.total = len(records)
    for fid, data in records:
        try:
            user = User(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(user)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"users/{fid}: {e}")
    return progress.total


def migrate_refresh_tokens(dry_run: bool, progress: Progress) -> int:
    from app.services.repositories.postgres.token_repository import PostgresRefreshTokenRepository
    repo = PostgresRefreshTokenRepository()

    records = _load_json_files("refresh_tokens")
    progress.total = len(records)
    for fid, data in records:
        try:
            if dry_run:
                progress.success += 1
                continue
            repo.save(
                token_hash=fid,
                user_id=data.get("user_id", ""),
                expires_at=data.get("expires_at", _now()),
            )
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"refresh_tokens/{fid}: {e}")
    return progress.total


def _migrate_with_pydantic(
    entity: str,
    json_dir: str,
    pydantic_cls,
    postgres_repo_cls,
    dry_run: bool,
    progress: Progress,
    subdir: str | None = None,
) -> int:
    repo = postgres_repo_cls()
    if subdir:
        records = _load_json_subdirs(json_dir, subdir)
    else:
        records = _load_json_files(json_dir)
    progress.total = len(records)
    for fid, data in records:
        try:
            obj = pydantic_cls(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(obj)
            progress.success += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"{entity}/{fid}: {e}")
    return progress.total


def _migrate_with_id(
    entity: str,
    json_dir: str,
    pydantic_cls,
    postgres_repo_cls,
    dry_run: bool,
    progress: Progress,
    id_field: str = "id",
) -> int:
    repo = postgres_repo_cls()
    records = _load_json_files(json_dir)
    progress.total = len(records)
    for fid, data in records:
        try:
            obj = pydantic_cls(**data)
            if dry_run:
                progress.success += 1
                continue
            entity_id = getattr(obj, id_field, fid)
            repo.save(entity_id, obj)
            progress.success += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"{entity}/{fid}: {e}")
    return progress.total


def migrate_resumes(dry_run: bool, progress: Progress) -> int:
    from app.models.resume import Resume
    from app.services.repositories.postgres.content_repository import PostgresResumeRepository

    repo = PostgresResumeRepository()
    records = _load_json_files("resumes")
    progress.total = len(records)
    for fid, data in records:
        try:
            resume = Resume(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(fid, resume)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"resumes/{fid}: {e}")
    return progress.total


def migrate_applications(dry_run: bool, progress: Progress) -> int:
    from app.models.application import Application
    from app.services.repositories.postgres.content_repository import PostgresApplicationRepository

    repo = PostgresApplicationRepository()
    records = _load_json_files("applications")
    progress.total = len(records)
    for fid, data in records:
        try:
            app = Application(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(app)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"applications/{fid}: {e}")
    return progress.total


def migrate_cover_letters(dry_run: bool, progress: Progress) -> int:
    from app.models.cover_letter import CoverLetter
    from app.services.repositories.postgres.content_repository import PostgresCoverLetterRepository

    repo = PostgresCoverLetterRepository()
    records = _load_json_subdirs("cover_letters")
    progress.total = len(records)
    for fid, data in records:
        try:
            letter = CoverLetter(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(letter)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"cover_letters/{fid}: {e}")
    return progress.total


def migrate_matches(dry_run: bool, progress: Progress) -> int:
    from app.models.match import MatchResult
    from app.services.repositories.postgres.content_repository import PostgresMatchRepository

    repo = PostgresMatchRepository()
    records = _load_json_files("matches")
    progress.total = len(records)
    for fid, data in records:
        try:
            match = MatchResult(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(fid, match)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"matches/{fid}: {e}")
    return progress.total


def migrate_versions(dry_run: bool, progress: Progress) -> int:
    from app.models.version import ResumeVersion
    from app.services.repositories.postgres.content_repository import PostgresResumeVersionRepository

    repo = PostgresResumeVersionRepository()
    records = _load_json_subdirs("versions")
    progress.total = len(records)
    for fid, data in records:
        try:
            version = ResumeVersion(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(version)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"versions/{fid}: {e}")
    return progress.total


def migrate_suggestions(dry_run: bool, progress: Progress) -> int:
    from app.models.writer import ResumeSuggestion
    from app.services.repositories.postgres.content_repository import PostgresWriterSuggestionRepository

    repo = PostgresWriterSuggestionRepository()
    records = _load_json_subdirs("writer_suggestions")
    progress.total = len(records)
    for fid, data in records:
        try:
            suggestion = ResumeSuggestion(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(suggestion)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"writer_suggestions/{fid}: {e}")
    return progress.total


def migrate_interview_sessions(dry_run: bool, progress: Progress) -> int:
    from app.models.interview import InterviewSession
    from app.services.repositories.postgres.content_repository import PostgresInterviewSessionRepository

    repo = PostgresInterviewSessionRepository()
    records = _load_interview_files("sessions")
    progress.total = len(records)
    for fid, data in records:
        try:
            session = InterviewSession(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(session)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"interview_sessions/{fid}: {e}")
    return progress.total


def migrate_interview_questions(dry_run: bool, progress: Progress) -> int:
    from app.models.interview import InterviewQuestion
    from app.services.repositories.postgres.content_repository import PostgresInterviewQuestionRepository

    repo = PostgresInterviewQuestionRepository()
    records = _load_interview_files("questions")
    progress.total = len(records)
    for fid, data in records:
        try:
            question = InterviewQuestion(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(question)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"interview_questions/{fid}: {e}")
    return progress.total


def migrate_interview_answers(dry_run: bool, progress: Progress) -> int:
    from app.models.interview import InterviewAnswer
    from app.services.repositories.postgres.content_repository import PostgresInterviewAnswerRepository

    repo = PostgresInterviewAnswerRepository()
    records = _load_interview_files("answers")
    progress.total = len(records)
    for fid, data in records:
        try:
            answer = InterviewAnswer(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(answer)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"interview_answers/{fid}: {e}")
    return progress.total


def migrate_readiness(dry_run: bool, progress: Progress) -> int:
    from app.models.interview import ReadinessAssessment
    from app.services.repositories.postgres.content_repository import PostgresReadinessAssessmentRepository

    repo = PostgresReadinessAssessmentRepository()
    records = _load_interview_files("readiness")
    progress.total = len(records)
    for fid, data in records:
        try:
            assessment = ReadinessAssessment(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(assessment)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"readiness/{fid}: {e}")
    return progress.total


def migrate_summaries(dry_run: bool, progress: Progress) -> int:
    from app.models.interview import SessionSummary
    from app.services.repositories.postgres.content_repository import PostgresSessionSummaryRepository

    repo = PostgresSessionSummaryRepository()
    records = _load_interview_files("summaries")
    progress.total = len(records)
    for fid, data in records:
        try:
            summary = SessionSummary(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(summary)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"summaries/{fid}: {e}")
    return progress.total


def migrate_timeline(dry_run: bool, progress: Progress) -> int:
    from app.models.application import TimelineEvent
    from app.services.repositories.postgres.content_repository import PostgresTimelineEventRepository

    repo = PostgresTimelineEventRepository()
    records = _load_json_subdirs("timeline")
    progress.total = len(records)
    for fid, data in records:
        try:
            event = TimelineEvent(**data)
            if dry_run:
                progress.success += 1
                continue
            repo.save(event)
            progress.success += 1
        except IntegrityError:
            progress.skipped += 1
        except Exception as e:
            progress.errors += 1
            progress.error_details.append(f"timeline/{fid}: {e}")
    return progress.total


# ── Migration Order ────────────────────────────────────────────────────────────

MIGRATION_STEPS = [
    ("users", migrate_users, "users"),
    ("refresh_tokens", migrate_refresh_tokens, "refresh_tokens"),
    ("resumes", migrate_resumes, "resumes"),
    ("applications", migrate_applications, "applications"),
    ("cover_letters", migrate_cover_letters, "cover_letters"),
    ("matches", migrate_matches, "matches"),
    ("versions", migrate_versions, "resume_versions"),
    ("suggestions", migrate_suggestions, "writer_suggestions"),
    ("interview_sessions", migrate_interview_sessions, "interview_sessions"),
    ("timeline", migrate_timeline, "timeline_events"),
    ("interview_questions", migrate_interview_questions, "interview_questions"),
    ("interview_answers", migrate_interview_answers, "interview_answers"),
    ("readiness", migrate_readiness, "readiness_assessments"),
    ("summaries", migrate_summaries, "session_summaries"),
]

ENTITY_MAP = {name: (fn, table) for name, fn, table in MIGRATION_STEPS}


def run_migration(entity: str | None, dry_run: bool, verbose: bool):
    from app.db.database import create_engine, dispose_engine
    import anyio

    async def _run():
        engine = await create_engine()
        if engine is None:
            print("ERROR: Cannot connect to database. Set DATABASE_URL.")
            sys.exit(1)

        if entity:
            if entity not in ENTITY_MAP:
                print(f"Unknown entity: {entity}")
                print(f"Available: {', '.join(sorted(ENTITY_MAP))}")
                sys.exit(1)
            steps = [(entity, *ENTITY_MAP[entity])]
        else:
            steps = MIGRATION_STEPS

        total_start = time.time()
        grand_total = 0
        grand_errors = 0

        for name, fn, table in steps:
            progress = Progress(verbose=verbose)
            print(f"\n{'─' * 50}")
            label = f"{'DRY-RUN: ' if dry_run else ''}Migrating {name} → {table}"
            print(f"  {label}")
            start = time.time()
            try:
                fn(dry_run, progress)
            except Exception as e:
                print(f"  ERROR during {name} migration: {e}")
            elapsed = time.time() - start
            progress.summary(name, elapsed)
            grand_total += progress.total
            grand_errors += progress.errors

        await dispose_engine()

        print(f"\n{'═' * 50}")
        print(f"  {'DRY-RUN ' if dry_run else ''}Migration complete")
        print(f"  Total records: {grand_total}")
        print(f"  Total errors:  {grand_errors}")
        print(f"  Total time:    {time.time() - total_start:.2f}s")

    anyio.run(_run)


# ── Validation ─────────────────────────────────────────────────────────────────


def validate_migration(verbose: bool):
    """Compare JSON record count with PostgreSQL record count for all entities."""
    from app.db.database import create_engine, dispose_engine
    import anyio
    from sqlalchemy import text

    async def _validate():
        engine = await create_engine()
        if engine is None:
            print("ERROR: Cannot connect to database.")
            sys.exit(1)

        print(f"\n{'═' * 60}")
        print("  DATA VALIDATION REPORT")
        print(f"{'═' * 60}")

        checks = [
            ("users", "users", "SELECT COUNT(*) FROM users"),
            ("refresh_tokens", "refresh_tokens", "SELECT COUNT(*) FROM refresh_tokens"),
            ("resumes", "resumes", "SELECT COUNT(*) FROM resumes"),
            ("applications", "applications", "SELECT COUNT(*) FROM applications"),
            ("cover_letters", "cover_letters", "SELECT COUNT(*) FROM cover_letters"),
            ("matches", "match_results", "SELECT COUNT(*) FROM match_results"),
            ("versions", "resume_versions", "SELECT COUNT(*) FROM resume_versions"),
            ("suggestions", "writer_suggestions", "SELECT COUNT(*) FROM writer_suggestions"),
            ("interview_sessions", "interview_sessions", "SELECT COUNT(*) FROM interview_sessions"),
            ("interview_questions", "interview_questions", "SELECT COUNT(*) FROM interview_questions"),
            ("interview_answers", "interview_answers", "SELECT COUNT(*) FROM interview_answers"),
            ("readiness", "readiness_assessments", "SELECT COUNT(*) FROM readiness_assessments"),
            ("summaries", "session_summaries", "SELECT COUNT(*) FROM session_summaries"),
            ("timeline", "timeline_events", "SELECT COUNT(*) FROM timeline_events"),
        ]

        all_ok = True
        async with engine.connect() as conn:
            for name, table, query in checks:
                json_count = _count_json_files(name)
                result = await conn.execute(text(query))
                pg_count = result.scalar() or 0
                status = "OK" if json_count == pg_count else "MISMATCH"
                if json_count != pg_count:
                    all_ok = False
                print(f"  {table:30s} JSON:{json_count:5d}  PG:{pg_count:5d}  [{status}]")

            # FK integrity checks
            print(f"\n{'─' * 60}")
            print("  FOREIGN KEY INTEGRITY")
            fk_checks = [
                ("refresh_tokens", "refresh_tokens.user_id → users.id",
                 "SELECT COUNT(*) FROM refresh_tokens r WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = r.user_id)"),
                ("resumes", "resumes.user_id → users.id",
                 "SELECT COUNT(*) FROM resumes r WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = r.user_id)"),
                ("applications", "applications.user_id → users.id",
                 "SELECT COUNT(*) FROM applications a WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.user_id)"),
            ]
            for table, desc, query in fk_checks:
                result = await conn.execute(text(query))
                orphans = result.scalar() or 0
                status = "OK" if orphans == 0 else f"{orphans} ORPHANS"
                if orphans > 0:
                    all_ok = False
                print(f"  {desc:50s} [{status}]")

        await dispose_engine()

        print(f"\n{'═' * 60}")
        if all_ok:
            print("  VALIDATION: ✅ ALL CHECKS PASSED")
        else:
            print("  VALIDATION: ❌ SOME CHECKS FAILED")
        print(f"{'═' * 60}")

    anyio.run(_validate)


def _count_json_files(entity_name: str) -> int:
    """Count JSON files for a given entity name."""
    counts = {
        "users": lambda: len(list((STORAGE_DIR / "users").glob("*.json"))),
        "refresh_tokens": lambda: len(list((STORAGE_DIR / "refresh_tokens").glob("*.json"))),
        "resumes": lambda: len(list((STORAGE_DIR / "resumes").glob("*.json"))),
        "applications": lambda: len(list((STORAGE_DIR / "applications").glob("*.json"))),
        "cover_letters": lambda: sum(1 for _ in (STORAGE_DIR / "cover_letters").rglob("*.json")),
        "matches": lambda: len(list((STORAGE_DIR / "matches").glob("*.json"))),
        "versions": lambda: sum(1 for _ in (STORAGE_DIR / "versions").rglob("*.json")),
        "suggestions": lambda: sum(1 for _ in (STORAGE_DIR / "writer_suggestions").rglob("*.json")),
        "interview_sessions": lambda: sum(1 for _ in (STORAGE_DIR / "interviews").rglob("sessions/*.json")),
        "interview_questions": lambda: sum(1 for _ in (STORAGE_DIR / "interviews").rglob("questions/*.json")),
        "interview_answers": lambda: sum(1 for _ in (STORAGE_DIR / "interviews").rglob("answers/*.json")),
        "readiness": lambda: sum(1 for _ in (STORAGE_DIR / "interviews").rglob("readiness/*.json")),
        "summaries": lambda: sum(1 for _ in (STORAGE_DIR / "interviews").rglob("summaries/*.json")),
        "timeline": lambda: sum(1 for _ in (STORAGE_DIR / "timeline").rglob("*.json")),
    }
    return counts.get(entity_name, lambda: 0)()


# ── CLI ────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON data to PostgreSQL")
    parser.add_argument("--entity", "-e", help="Migrate only one entity")
    parser.add_argument("--all", "-a", action="store_true", help="Migrate all entities")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Count records without inserting")
    parser.add_argument("--validate", "-v", action="store_true", help="Validate migration")
    parser.add_argument("--verbose", action="store_true", help="Detailed logging")

    args = parser.parse_args()

    if args.validate:
        validate_migration(args.verbose)
        return

    if not args.all and not args.entity:
        parser.print_help()
        print("\nUse --all to migrate everything, --entity NAME for one, or --validate to check.")
        return

    run_migration(args.entity, args.dry_run, args.verbose)


if __name__ == "__main__":
    main()
