"""Pydantic schemas for the DriveOps IQ module."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .models import RequestStatus


class RequestCreate(BaseModel):
    """Payload accepted when a technician submits a new DriveOps request."""

    ro_number: str = Field(..., min_length=1, max_length=64)
    vin: str = Field(..., min_length=1, max_length=17)
    customer: str = Field(..., min_length=1, max_length=255)
    insurer: str = Field(..., min_length=1, max_length=255)
    calibration_type: str = Field(..., min_length=1, max_length=128)
    notes: Optional[str] = Field(default=None, max_length=5000)


class RequestResponse(BaseModel):
    """API representation of a DriveOps request."""

    id: UUID
    ro_number: str
    vin: str
    customer: str
    insurer: str
    calibration_type: str
    notes: Optional[str]
    status: RequestStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class RequestCreateResponse(BaseModel):
    """Response body returned after creating a DriveOps request."""

    status: RequestStatus
    message: str
    request: RequestResponse
