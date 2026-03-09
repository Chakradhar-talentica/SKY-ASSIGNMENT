"""
CheckIn API router.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.config.database import get_db_session
from src.domains.checkin.service import CheckInService
from src.domains.checkin.schemas import StartCheckInRequest, CheckInResponse

router = APIRouter(prefix="/checkin", tags=["Check-in"])


def get_redis(request: Request):
    """Get Redis client from app state."""
    if hasattr(request.app.state, 'redis'):
        return request.app.state.redis
    return None


@router.post("/start", response_model=CheckInResponse, status_code=201)
async def start_checkin(
    request_body: StartCheckInRequest,
    request: Request = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Start the check-in process.

    This will:
    1. Hold the selected seat for 120 seconds
    2. Create a check-in record with status IN_PROGRESS

    The passenger must complete check-in within 120 seconds or the seat
    will be released automatically.
    """
    redis_client = get_redis(request) if request else None
    service = CheckInService(session, redis_client)
    return await service.start_checkin(
        passenger_id=request_body.passenger_id,
        flight_id=request_body.flight_id,
        seat_id=request_body.seat_id
    )


@router.get("/{checkin_id}", response_model=CheckInResponse)
async def get_checkin(
    checkin_id: UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get check-in details.
    """
    redis_client = get_redis(request) if request else None
    service = CheckInService(session, redis_client)
    return await service.get_checkin(checkin_id)


@router.post("/{checkin_id}/complete", response_model=CheckInResponse)
async def complete_checkin(
    checkin_id: UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Complete the check-in process.

    This will:
    1. Confirm the held seat (making it permanently assigned)
    2. Set check-in status to COMPLETED

    Prerequisites:
    - Check-in must be IN_PROGRESS (not WAITING_FOR_PAYMENT)
    - Seat hold must not have expired
    - All excess baggage fees must be paid
    """
    redis_client = get_redis(request) if request else None
    service = CheckInService(session, redis_client)
    return await service.complete_checkin(checkin_id)

