"""
Seat API router.
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from src.config.database import get_db_session
from src.domains.seats.service import SeatService
from src.domains.seats.schemas import (
    SeatMapResponse, SeatResponse,
    HoldSeatRequest, HoldSeatResponse,
    ReleaseSeatRequest, ConfirmSeatRequest
)

router = APIRouter(tags=["Seats"])


def get_redis(request: Request):
    """Get Redis client from app state."""
    if hasattr(request.app.state, 'redis'):
        return request.app.state.redis
    return None


@router.get("/flights/{flight_id}/seats", response_model=SeatMapResponse)
async def get_seat_map(
    flight_id: UUID,
    seat_class: Optional[str] = Query(None, description="Filter by seat class"),
    request: Request = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get the seat map for a flight.

    Returns all seats with their current status (AVAILABLE, HELD, CONFIRMED).
    This endpoint is cached for performance.
    """
    redis_client = get_redis(request) if request else None
    service = SeatService(session, redis_client)
    return await service.get_seat_map(flight_id, seat_class)


@router.get("/seats/{seat_id}", response_model=SeatResponse)
async def get_seat(
    seat_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get a specific seat by ID.
    """
    service = SeatService(session)
    return await service.get_seat(seat_id)


@router.post("/seats/{seat_id}/hold", response_model=HoldSeatResponse)
async def hold_seat(
    seat_id: UUID,
    request_body: HoldSeatRequest,
    request: Request = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Hold a seat for a passenger.

    The seat will be held for 120 seconds. If not confirmed within this time,
    it will automatically become available again.

    Only AVAILABLE seats can be held.
    """
    redis_client = get_redis(request) if request else None
    service = SeatService(session, redis_client)
    return await service.hold_seat(seat_id, request_body.passenger_id)


@router.post("/seats/{seat_id}/release", response_model=SeatResponse)
async def release_seat(
    seat_id: UUID,
    request_body: ReleaseSeatRequest,
    request: Request = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Release a held seat.

    Only the passenger who holds the seat can release it.
    """
    redis_client = get_redis(request) if request else None
    service = SeatService(session, redis_client)
    return await service.release_seat(seat_id, request_body.passenger_id)


@router.post("/seats/{seat_id}/confirm", response_model=SeatResponse)
async def confirm_seat(
    seat_id: UUID,
    request_body: ConfirmSeatRequest,
    request: Request = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Confirm a held seat.

    Only the passenger who holds the seat can confirm it.
    The seat must be confirmed before the hold expires (120 seconds).

    Once confirmed, the seat cannot change state.
    """
    redis_client = get_redis(request) if request else None
    service = SeatService(session, redis_client)
    return await service.confirm_seat(seat_id, request_body.passenger_id)

