"""SQLAlchemy models for the DriveOps IQ module."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, String, Text, UniqueConstraint

from app.core.database import Base


class RequestStatus(str, enum.Enum):
    """Valid workflow states for a DriveOps service request."""

    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    CLAIMED = "claimed"
    ENROUTE = "enroute"
    ONSITE = "onsite"
    COMPLETE = "complete"
    HOLD = "hold"


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp for defaults."""
    return datetime.now(timezone.utc)


class Request(Base):
    """DriveOps IQ service request persisted in the platform database."""

    __tablename__ = "requests"
    __table_args__ = (
        UniqueConstraint("ro_number", name="uq_requests_ro_number"),
    )

    id = Column(String(length=36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ro_number = Column(String(length=64), nullable=False)
    vin = Column(String(length=17), nullable=False)
    customer = Column(String(length=255), nullable=False)
    insurer = Column(String(length=255), nullable=False)
    calibration_type = Column(String(length=128), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(
        Enum(RequestStatus, name="request_status", native_enum=False),
        nullable=False,
        default=RequestStatus.PENDING_VALIDATION,
        server_default=RequestStatus.PENDING_VALIDATION.value,
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<DriveOpsRequest id={self.id} ro={self.ro_number} status={self.status}>"
