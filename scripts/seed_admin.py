#!/usr/bin/env python3
import os
import sys
from sqlmodel import select

from api.db import create_db_and_tables, get_session
from api.bootstrap import ensure_single_admin_user
from api.models import User
from config.settings import DATABASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD


def mask_url(url: str) -> str:
    if not url:
        return "<empty>"
    try:
        # hide password
        prefix, rest = url.split('://', 1)
        if '@' in rest and ':' in rest.split('@')[0]:
            userpass, host = rest.split('@', 1)
            user = userpass.split(':', 1)[0]
            return f"{prefix}://{user}:***@{host}"
        return url
    except Exception:
        return url


def main() -> None:
    print("DATABASE_URL:", mask_url(DATABASE_URL or ""))
    print("ADMIN_EMAIL set:", bool(ADMIN_EMAIL))

    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("ERROR: ADMIN_EMAIL/ADMIN_PASSWORD not set in environment.")
        sys.exit(1)

    print("Creating tables (if needed)...")
    create_db_and_tables()

    print("Ensuring single admin user...")
    ensure_single_admin_user()

    with get_session() as session:
        count = session.exec(select(User)).all()
        print(f"Users in DB: {len(count)}")
        if len(count) == 0:
            print("No users found. Check DATABASE_URL connectivity and permissions.")
            sys.exit(2)
        admin = session.exec(select(User).where(User.is_master == True)).first()
        if not admin:
            print("No admin user found. Seed step may have been skipped.")
            sys.exit(3)
        print(f"Admin user: {admin.email}")

    print("Done.")


if __name__ == "__main__":
    main()
