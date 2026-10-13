"""One-time, opt-in login credentials for legacy local/demo participants."""
import argparse
import csv
import re
import secrets
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import hash_password
from .database import IS_MEMORY, SessionLocal, init_db
from .models import AuthAccount, User


def provision_dummy_accounts(db: Session) -> list[dict[str, str]]:
    """Stage missing accounts without resetting existing credentials or history."""
    users = db.scalars(select(User).where(~User.auth_account.has()).order_by(User.id))
    reserved = {email.lower() for email in db.scalars(select(AuthAccount.email))}
    reserved.update(email.lower() for email in db.scalars(select(User.email)) if email)
    credentials = []
    for user in users:
        stem = re.sub(r"[^a-z0-9]+", ".", f"{user.first_name}.{user.last_name}".lower()).strip(".")
        stem = stem or "athlete"
        email = f"{stem}@example.com"
        suffix = 2
        while email in reserved:
            email = f"{stem}.{suffix}@example.com"
            suffix += 1
        reserved.add(email)
        password = secrets.token_urlsafe(18)
        user.email = email
        user.auth_account = AuthAccount(email=email, password_hash=hash_password(password))
        credentials.append({
            "userId": user.id, "firstName": user.first_name, "lastName": user.last_name,
            "email": email, "password": password,
        })
    db.flush()
    return credentials


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New private CSV file for generated logins")
    args = parser.parse_args()
    if IS_MEMORY:
        parser.error("Set DATABASE_URL to the existing file database; a separate process cannot update an in-memory app.")
    if args.output.exists():
        parser.error("Output file already exists; choose a new path to avoid overwriting credentials.")
    init_db()
    exported = False
    committed = False
    try:
        with SessionLocal.begin() as db:
            credentials = provision_dummy_accounts(db)
            if credentials:
                with args.output.open("x", newline="", encoding="utf-8") as output:
                    exported = True
                    writer = csv.DictWriter(output, fieldnames=[
                        "userId", "firstName", "lastName", "email", "password",
                    ])
                    writer.writeheader()
                    writer.writerows(credentials)
        committed = True
    finally:
        if exported and not committed:
            args.output.unlink()
    print(f"Created {len(credentials)} dummy login accounts; existing login accounts were unchanged.")
    if exported:
        print(f"Private credentials saved to {args.output.resolve()}. Use only for local/demo data.")


if __name__ == "__main__":
    main()
