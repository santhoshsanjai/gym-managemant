"""Management commands.

python -m app.cli create-admin <username> [--password ...]
python -m app.cli run-reminders
python -m app.cli seed-demo
"""

import argparse
import getpass
import sys

import app.models  # noqa: F401
from app.common.database import SessionLocal


def create_admin(username: str, password: str | None) -> None:
    from sqlalchemy import select

    from app.auth.models import Role, User
    from app.common.security import hash_password

    password = password or getpass.getpass("Password: ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username.lower())):
            sys.exit(f"User '{username}' already exists")
        db.add(User(username=username.lower(), password_hash=hash_password(password), role=Role.admin))
        db.commit()
    print(f"Admin '{username}' created")


def run_reminders() -> None:
    from app.notifications.service import generate_reminders

    with SessionLocal() as db:
        print(f"Created {len(generate_reminders(db))} notification(s)")


def seed_demo() -> None:
    """Small demo dataset for local development. Never run in production."""
    from datetime import timedelta
    from decimal import Decimal

    from sqlalchemy import select

    from app.auth.service import ensure_admin
    from app.common.timeutil import today
    from app.members.schemas import MemberCreate
    from app.members.service import create_member
    from app.packages.models import DurationUnit, Package
    from app.subscriptions.schemas import InlinePayment, SubscriptionCreate
    from app.subscriptions.service import create_subscription
    from app.trainers.models import Trainer

    with SessionLocal() as db:
        admin = ensure_admin(db, "admin", "admin12345")
        if db.scalar(select(Package.id).limit(1)):
            print("Demo data already present")
            return
        pk = [
            Package(
                name="Monthly",
                duration_value=1,
                duration_unit=DurationUnit.months,
                price=Decimal("1500"),
                description="Full gym access for one month",
            ),
            Package(
                name="Quarterly",
                duration_value=3,
                duration_unit=DurationUnit.months,
                price=Decimal("4000"),
                description="Three months, best for beginners",
            ),
            Package(
                name="Annual",
                duration_value=12,
                duration_unit=DurationUnit.months,
                price=Decimal("14000"),
                description="Twelve months with two free PT sessions",
            ),
        ]
        t = Trainer(full_name="Arun Kumar", mobile="9000000001", specialization="Strength", experience_years=6)
        db.add_all(pk + [t])
        db.commit()
        people = [("Priya S", "9000000101", 0), ("Rahul M", "9000000102", -25), ("Divya R", "9000000103", -40)]
        for name, mobile, offset in people:
            m = create_member(
                db, MemberCreate(full_name=name, mobile=mobile, password="member1234", trainer_id=t.id), admin
            )
            create_subscription(
                db,
                SubscriptionCreate(
                    member_id=m.id,
                    package_id=pk[0].id,
                    start_date=today() + timedelta(days=offset),
                    payment=InlinePayment(),
                ),
                admin,
            )
        print("Seeded: admin/admin12345, members 9000000101..103 / member1234")


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    ca = sub.add_parser("create-admin")
    ca.add_argument("username")
    ca.add_argument("--password")
    sub.add_parser("run-reminders")
    sub.add_parser("seed-demo")
    a = p.parse_args()
    if a.cmd == "create-admin":
        create_admin(a.username, a.password)
    elif a.cmd == "run-reminders":
        run_reminders()
    elif a.cmd == "seed-demo":
        seed_demo()


if __name__ == "__main__":
    main()
