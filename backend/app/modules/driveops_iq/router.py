"""API router for the DriveOps IQ module."""

from __future__ import annotations

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from .models import Request, RequestStatus
from .schemas import RequestCreate, RequestCreateResponse, RequestResponse

router = APIRouter(prefix="/driveops", tags=["DriveOps-IQ"])

@router.post(
    "/requests",
    response_model=RequestCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    payload: RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestCreateResponse:
    """Persist a new DriveOps service request."""

    existing_stmt = select(Request).where(Request.ro_number == payload.ro_number)
    existing = await db.execute(existing_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A DriveOps request already exists for this RO number.",
        )

    db_request = Request(
        ro_number=payload.ro_number,
        vin=payload.vin,
        customer=payload.customer,
        insurer=payload.insurer,
        calibration_type=payload.calibration_type,
        notes=payload.notes,
        status=RequestStatus.PENDING_VALIDATION,
    )

    db.add(db_request)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create request due to a uniqueness conflict.",
        )

    await db.refresh(db_request)

    return RequestCreateResponse(
        status=db_request.status,
        message="Request created successfully.",
        request=RequestResponse.model_validate(db_request),
    )


@router.get(
    "/requests",
    response_model=List[RequestResponse],
)
async def list_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RequestResponse]:
    """Return DriveOps requests ordered by recency."""

    stmt = select(Request).order_by(Request.created_at.desc())
    result = await db.execute(stmt)
    requests = result.scalars().all()
    return [RequestResponse.model_validate(req) for req in requests]


@router.get(
    "/requests/{request_id}",
    response_model=RequestResponse,
)
async def get_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestResponse:
    """Fetch a single DriveOps request by its identifier."""

    stmt = select(Request).where(Request.id == str(request_id))
    result = await db.execute(stmt)
    request_obj = result.scalar_one_or_none()
    if request_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DriveOps request not found.",
        )

    return RequestResponse.model_validate(request_obj)
