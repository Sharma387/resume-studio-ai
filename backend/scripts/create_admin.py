#!/usr/bin/env python3
"""Admin user bootstrap utility.

Creates a new admin user or promotes an existing user to admin.

Usage:
    python scripts/create_admin.py --email admin@example.com --password "SecurePass123!" --name "System Admin"
    python scripts/create_admin.py --email existing@example.com --promote
"""

import argparse
import sys

from app.models.user import User, UserRole


def main():
    parser = argparse.ArgumentParser(description="Create or promote an admin user")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--password", help="Password (required for new users)")
    parser.add_argument("--name", help="Full name (required for new users)")
    parser.add_argument("--promote", action="store_true", help="Promote existing user to admin")
    args = parser.parse_args()

    # Ensure database engine is initialized for PostgreSQL backend
    import anyio
    from app.core.config import settings
    if settings.storage_backend == "postgres" and settings.database_url:
        from app.db.database import create_engine, get_sync_session
        anyio.run(create_engine)
        get_sync_session()  # verify sync session works

    from app.services.user_service import UserService

    svc = UserService()
    existing = svc.get_by_email(args.email)

    if existing:
        if existing.role == UserRole.ADMIN:
            print(f"User {args.email} is already an administrator.")
            return
        existing.role = UserRole.ADMIN
        svc.repo.save(existing)
        print(f"✅ {args.email} promoted to administrator.")
        return

    if not args.password or not args.name:
        print("Error: --password and --name are required for new users.")
        sys.exit(1)

    try:
        user = svc.create_user(email=args.email, password=args.password, full_name=args.name)
        user.role = UserRole.ADMIN
        svc.repo.save(user)
        print(f"✅ Administrator created: {user.email}")
        print(f"   ID: {user.id}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
