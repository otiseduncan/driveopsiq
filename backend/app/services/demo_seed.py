"""
DriveOps-IQ demo database seeding script.
Creates test users for all system roles when DEMO_MODE is enabled.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.security import get_password_hash
from app.models import User


DEMO_USERS = [
    {
        "email": "superadmin@syfernetics.dev",
        "password": "SyferStackV2!",
        "role": "super_admin",
        "full_name": "Super Admin (Developer)",
    },
    {
        "email": "admin@driveops.dev",
        "password": "Admin123!",
        "role": "admin",
        "full_name": "System Admin",
    },
    {
        "email": "field.manager@driveops.dev",
        "password": "Field123!",
        "role": "manager_field",
        "full_name": "Field Manager",
    },
    {
        "email": "shop.manager@driveops.dev",
        "password": "Shop123!",
        "role": "manager_shop",
        "full_name": "Shop Manager",
    },
    {
        "email": "cmr.shop@driveops.dev",
        "password": "CMRshop123!",
        "role": "cmr_shop",
        "full_name": "Shop CMR",
    },
    {
        "email": "cmr.mobile@driveops.dev",
        "password": "CMRmobile123!",
        "role": "cmr_mobile",
        "full_name": "Mobile CMR Validator",
    },
    {
        "email": "technician@driveops.dev",
        "password": "Tech123!",
        "role": "technician",
        "full_name": "Technician Demo",
    },
]


def _normalize_role(value: str) -> str:
    return value.strip().lower()


def seed_demo_users(db: Session) -> None:
    """Insert or update demo users for testing roles."""
    for demo in DEMO_USERS:
        primary_role = _normalize_role(demo["role"])
        existing = db.query(User).filter(User.email == demo["email"]).first()
        hashed_password = get_password_hash(demo["password"])

        if existing:
            updated_fields: list[str] = []

            if existing.full_name != demo["full_name"]:
                existing.full_name = demo["full_name"]
                updated_fields.append("full_name")

            if existing.roles != primary_role:
                existing.roles = primary_role
                updated_fields.append("roles")

            desired_superuser = primary_role in {"admin", "super_admin"}
            if existing.is_superuser != desired_superuser:
                existing.is_superuser = desired_superuser
                updated_fields.append("is_superuser")

            if not existing.is_active:
                existing.is_active = True
                updated_fields.append("is_active")

            if getattr(existing, "is_verified", False) is False:
                existing.is_verified = True
                updated_fields.append("is_verified")

            existing.hashed_password = hashed_password
            updated_fields.append("hashed_password")

            if updated_fields:
                logger.info(
                    "Updated demo user: %s (%s) fields=%s",
                    demo["email"],
                    primary_role,
                    ", ".join(updated_fields),
                )
            continue

        user = User(
            email=demo["email"],
            hashed_password=hashed_password,
            roles=primary_role,
            full_name=demo["full_name"],
            is_active=True,
            is_superuser=primary_role in {"admin", "super_admin"},
            is_verified=True,
        )
        db.add(user)
        logger.info("Seeded demo user: %s (%s)", demo["email"], primary_role)

    db.commit()
    logger.info("✅ Demo users seeding completed.")
